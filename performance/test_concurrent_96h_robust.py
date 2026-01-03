#!/usr/bin/env python3
"""
96小时持续并发性能测试（增强版）
- 支持断点续传
- 自动恢复机制
- 健康检查
- 错误重试
"""

import boto3
import json
import time
import csv
import signal
import sys
import threading
import argparse
import base64
from datetime import datetime, timedelta
from pathlib import Path
import pickle

# ====== 默认配置 ======
DEFAULT_REGION = "us-west-2"
DEFAULT_MODEL = "us.amazon.nova-2-lite-v1:0"
CONCURRENCY_LEVELS = [1, 5, 10]
HOURS_PER_LEVEL = 32
REQUEST_INTERVAL_SECONDS = 60
SERVICE_TIERS = ["flex", "default", "priority"]

# 图片配置
TEST_IMAGE_PATH = Path(__file__).parent / "test_image.png"

# ==================

# 全局变量（在main中初始化）
AWS_REGION = None
MODEL_ID = None
DATA_DIR = None
CSV_FILE = None
STATE_FILE = None
client = None
running = True
TEST_IMAGE_BASE64 = None  # 图片的base64编码

class TestState:
    """测试状态管理"""
    def __init__(self):
        self.current_concurrency_index = 0
        self.level_start_time = None
        self.batch_count = 0
        self.total_start_time = datetime.now()

    def save(self):
        """保存状态到文件"""
        with open(STATE_FILE, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls):
        """从文件加载状态"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return cls()

def signal_handler(sig, frame):
    """处理中断信号"""
    global running
    print("\n\n⚠️  收到中断信号，正在保存状态...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def test_single_request_with_retry(tier, test_id, max_retries=3):
    """带重试的单次请求（使用图片输入）"""
    for attempt in range(max_retries):
        try:
            request_body = {
                "schemaVersion": "messages-v1",
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {
                                    "bytes": TEST_IMAGE_BASE64
                                }
                            }
                        },
                        {
                            "text": f"What do you see in this image? Test ID: {test_id}"
                        }
                    ]
                }],
                "inferenceConfig": {
                    "maxTokens": 100,
                    "temperature": 0.7
                }
            }

            invoke_params = {
                "modelId": MODEL_ID,
                "body": json.dumps(request_body),
                "contentType": "application/json",
                "accept": "application/json"
            }

            if tier != "default":
                invoke_params["serviceTier"] = tier

            start_time = time.time()
            response = client.invoke_model(**invoke_params)
            latency = int((time.time() - start_time) * 1000)

            model_response = json.loads(response["body"].read())
            usage = model_response.get("usage", {})
            http_headers = response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
            server_latency = int(http_headers.get("x-amzn-bedrock-invocation-latency", 0))

            return {
                "success": True,
                "client_latency": latency,
                "server_latency": server_latency,
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
                "attempts": attempt + 1
            }

        except Exception as e:
            error_msg = str(e)

            # 限流错误，等待后重试
            if "ThrottlingException" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 秒
                    print(f"    ⚠️  限流，等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    continue

            # 其他错误
            if attempt < max_retries - 1:
                time.sleep(2)
                continue

            return {
                "success": False,
                "error": error_msg,
                "attempts": max_retries
            }

    return {"success": False, "error": "Max retries exceeded"}

def test_concurrent_batch(tier, concurrency, batch_id):
    """测试一批并发请求"""
    results = []
    lock = threading.Lock()

    def worker(worker_id):
        result = test_single_request_with_retry(tier, f"{tier}_{concurrency}_{batch_id}_{worker_id}")
        with lock:
            results.append(result)

    threads = []
    batch_start_time = time.time()

    for i in range(concurrency):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    batch_time = time.time() - batch_start_time

    # 统计
    successful = [r for r in results if r.get('success')]
    failed = len(results) - len(successful)

    if successful:
        avg_server = sum(r['server_latency'] for r in successful) / len(successful)
        avg_client = sum(r['client_latency'] for r in successful) / len(successful)
        avg_input = sum(r['input_tokens'] for r in successful) / len(successful)
        avg_output = sum(r['output_tokens'] for r in successful) / len(successful)
    else:
        avg_server = avg_client = avg_input = avg_output = 0

    return {
        "successful": len(successful),
        "failed": failed,
        "avg_server_latency": avg_server,
        "avg_client_latency": avg_client,
        "avg_input_tokens": avg_input,
        "avg_output_tokens": avg_output,
        "batch_time": batch_time
    }

def save_to_csv(data):
    """保存数据"""
    file_exists = CSV_FILE.exists()

    with open(CSV_FILE, 'a', newline='') as f:
        fieldnames = ['timestamp', 'concurrency', 'tier', 'successful', 'failed',
                      'avg_server_latency', 'avg_client_latency',
                      'avg_input_tokens', 'avg_output_tokens', 'batch_time']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def health_check():
    """健康检查"""
    try:
        # 检查磁盘空间
        import shutil
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)

        if free_gb < 1:
            print(f"⚠️  磁盘空间不足: {free_gb:.2f}GB")
            return False

        # 检查内存
        with open('/proc/meminfo') as f:
            meminfo = f.read()
            for line in meminfo.split('\n'):
                if 'MemAvailable' in line:
                    mem_available_kb = int(line.split()[1])
                    mem_available_gb = mem_available_kb / (1024**2)
                    if mem_available_gb < 0.5:
                        print(f"⚠️  可用内存不足: {mem_available_gb:.2f}GB")
                        return False

        return True
    except:
        return True  # 检查失败不影响测试

def main():
    """主函数"""
    global AWS_REGION, MODEL_ID, DATA_DIR, CSV_FILE, STATE_FILE, client, TEST_IMAGE_BASE64

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='96小时持续并发性能测试（图片输入）')
    parser.add_argument('--region', default=DEFAULT_REGION, help=f'AWS区域 (默认: {DEFAULT_REGION})')
    parser.add_argument('--model', default=DEFAULT_MODEL, help=f'模型ID (默认: {DEFAULT_MODEL})')
    args = parser.parse_args()

    # 读取并编码测试图片
    if not TEST_IMAGE_PATH.exists():
        print(f"❌ 错误: 测试图片不存在: {TEST_IMAGE_PATH}")
        sys.exit(1)

    with open(TEST_IMAGE_PATH, 'rb') as f:
        image_bytes = f.read()
        TEST_IMAGE_BASE64 = base64.b64encode(image_bytes).decode('utf-8')

    print(f"✅ 已加载测试图片: {TEST_IMAGE_PATH} ({len(image_bytes)} bytes)")

    # 初始化全局变量
    AWS_REGION = args.region
    MODEL_ID = args.model
    DATA_DIR = Path(f"./concurrent_96h_data_{AWS_REGION.replace('-', '_')}")
    DATA_DIR.mkdir(exist_ok=True)

    # CSV文件名包含区域信息（标注为image测试）
    CSV_FILE = DATA_DIR / f"concurrent_96h_image_{AWS_REGION.replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    STATE_FILE = DATA_DIR / "test_state.pkl"

    # 初始化客户端
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    print(f"\n{'='*80}")
    print(f"96小时持续并发性能测试（增强版 - 支持断点续传）")
    print(f"{'='*80}")

    # 尝试恢复状态
    state = TestState.load()

    if state.level_start_time:
        print(f"✅ 检测到之前的测试状态，从中断处继续...")
        print(f"   上次并发级别: {CONCURRENCY_LEVELS[state.current_concurrency_index]}")
        print(f"   上次批次: {state.batch_count}")
    else:
        print(f"🆕 开始新的测试")
        state.total_start_time = datetime.now()

    print(f"开始时间: {state.total_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试区域: {AWS_REGION}")
    print(f"测试模型: {MODEL_ID}")
    print(f"并发级别: {CONCURRENCY_LEVELS}")
    print(f"数据保存: {CSV_FILE}")
    print(f"状态文件: {STATE_FILE}")
    print(f"{'='*80}\n")
    print("✨ 支持断点续传：测试中断后可自动恢复")
    print("⚡ 自动重试：遇到限流自动等待重试")
    print("🔍 健康检查：监控磁盘和内存")
    print("\n按 Ctrl+C 可随时停止测试\n")

    # 从保存的索引开始
    for conc_idx in range(state.current_concurrency_index, len(CONCURRENCY_LEVELS)):
        if not running:
            break

        concurrency = CONCURRENCY_LEVELS[conc_idx]
        state.current_concurrency_index = conc_idx

        # 设置或恢复级别开始时间
        if state.level_start_time is None:
            state.level_start_time = datetime.now()
            state.batch_count = 0

        level_end_time = state.level_start_time + timedelta(hours=HOURS_PER_LEVEL)

        print(f"\n{'#'*80}")
        print(f"# 并发级别: {concurrency}")
        print(f"# 开始时间: {state.level_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# 预计结束: {level_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}\n")

        while running and datetime.now() < level_end_time:
            state.batch_count += 1
            current_time = datetime.now()
            elapsed_hours = (current_time - state.level_start_time).total_seconds() / 3600
            progress = elapsed_hours / HOURS_PER_LEVEL * 100

            # 健康检查（每10批次）
            if state.batch_count % 10 == 0:
                if not health_check():
                    print("⚠️  健康检查失败，暂停10秒...")
                    time.sleep(10)

            print(f"[{current_time.strftime('%H:%M:%S')}] 并发 {concurrency} | "
                  f"批次 #{state.batch_count} | "
                  f"进度: {elapsed_hours:.1f}h/{HOURS_PER_LEVEL}h ({progress:.1f}%)")

            # 测试三个 Tier
            for tier in SERVICE_TIERS:
                result = test_concurrent_batch(tier, concurrency, state.batch_count)

                save_to_csv({
                    'timestamp': current_time.isoformat(),
                    'concurrency': concurrency,
                    'tier': tier,
                    'successful': result['successful'],
                    'failed': result['failed'],
                    'avg_server_latency': result['avg_server_latency'],
                    'avg_client_latency': result['avg_client_latency'],
                    'avg_input_tokens': result['avg_input_tokens'],
                    'avg_output_tokens': result['avg_output_tokens'],
                    'batch_time': result['batch_time']
                })

                status = "✓" if result['failed'] == 0 else f"⚠️ {result['failed']}失败"
                print(f"  {tier:8} {status} {result['avg_server_latency']:4.0f}ms "
                      f"耗时: {result['batch_time']:.1f}s")

            # 保存状态
            state.save()

            # 等待
            sleep_time = REQUEST_INTERVAL_SECONDS - (datetime.now() - current_time).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)

        # 完成当前级别，重置状态
        print(f"\n✅ 并发级别 {concurrency} 完成\n")
        state.level_start_time = None
        state.batch_count = 0
        state.save()

    # 清理状态文件
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    total_time = datetime.now() - state.total_start_time
    print(f"\n{'='*80}")
    print(f"✅ 测试完成")
    print(f"总运行时间: {total_time.total_seconds()/3600:.1f} 小时")
    print(f"数据文件: {CSV_FILE}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断，状态已保存")
    except Exception as e:
        print(f"\n\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 状态已保存，可以重新运行脚本继续测试")
