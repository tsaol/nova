# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import base64
import boto3
import json
import time
from pathlib import Path
from datetime import datetime
from statistics import mean, median
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 并发配置 - 50 并发请求
CONCURRENCY = 50

userLoc = 'Chinese'
userLabels = '{"1":"person wear glasses", "2":"cat is sleeping", "3":"child"}'

# Create a Bedrock Runtime client
client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

# 只测试美国的 inference profile
MODEL_ID = "us.amazon.nova-2-lite-v1:0"

# 定义要测试的 service tiers
SERVICE_TIERS = ["flex", "default", "priority"]

# 定义图片目录
image_dir = "./images"

# 获取目录下所有图片文件
image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
test_images = [f for f in Path(image_dir).iterdir() if f.suffix.lower() in image_extensions]

if not test_images:
    raise FileNotFoundError(f"没有找到测试图片 ({image_dir})")

print(f"找到 {len(test_images)} 张测试图片: {[img.name for img in test_images]}")

# 线程安全的统计数据 - 按 tier 组织
stats_lock = threading.Lock()
tier_stats = {tier: {
    "tier": tier,
    "total_requests": 0,
    "successful": 0,
    "failed": 0,
    "latencies_ms": [],
    "input_tokens": [],
    "output_tokens": [],
    "errors": defaultdict(int),
    "total_time": 0
} for tier in SERVICE_TIERS}

# 进度计数器
progress_counter = {"count": 0}
progress_lock = threading.Lock()

# Define your system prompt(s)
extra_instruction = f"Translation in locale {userLoc} language"

system_list = [{
    "text": "You are a surveillance image analyst. Analyze images and output ONLY valid JSON."
}]

def process_single_request(tier, image_path, request_id):
    """处理单个请求"""
    try:
        # 读取并编码图片
        with open(image_path, "rb") as image_file:
            binary_data = image_file.read()
            base_64_encoded_data = base64.b64encode(binary_data)
            base64_string = base_64_encoded_data.decode("utf-8")
        
        # 获取图片格式
        image_format = image_path.suffix.lower().replace('.', '')
        if image_format == 'jpg':
            image_format = 'jpeg'
    
        # Define a "user" message
        message_list = [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": base64_string},
                        }
                    },
                    {
                        "text": f"""Analyze this image and output ONLY valid JSON.

## OUTPUT FORMAT (Required)
{{
  "description": "[Concise English description ≤100 chars: natural scene description, avoid unnecessary articles like 'a/an' before person/people/objects]",
  "descriptionExtra": "[{extra_instruction}]",
  "keys": ["matched scene labels from SCENES INPUT only"],
  "risk": "[Safety risk description or empty string]",
  "noDetection": "[Set 'false' if ANY person/animal/vehicle detected, otherwise set 'true']",
  "summary": "[Natural English summary ≤30 chars, conversational tone, capitalize first letter, no punctuation]",
  "summaryExtra": "[{extra_instruction}]"
}}

## CRITICAL RULES
1. Detection: Only count real physical presence, NOT reflections/shadows
   - Reflections on windows → DO NOT count as detection
   - Set noDetection="false" only when real person/animal/vehicle detected
2. keys Matching: Match image against SCENES INPUT descriptions, return corresponding key IDs only
   - If SCENES INPUT is empty or uncertain → return `"keys": []`
   - NEVER create new keys not in SCENES INPUT
3. Language: Keep description/summary in English
4. Style: Use "person" not "a person", be concise and direct

Locale: {userLoc}
SCENES INPUT: {userLabels}

Do NOT ever put escaped Unicode in the output - just use the unescaped native character, for example, do not include sequences such as \u3492.

Examples:
- Image: Man with glasses + INPUT: {{"1":"person wear glasses"}} → keys: ["1"]
- Image: Sleeping cat + INPUT: {{"2":"cat is sleeping", "3":"dog"}} → keys: ["2"]
- Image: Dog playing + INPUT: {{"5":"child"}} → keys: []
"""
                    }
                ],
            }
        ]
        
        # Configure the inference parameters
        inf_params = {"maxTokens": 3000, "topP": 0.8, "temperature": 0.1, "topK": 15}

        native_request = {
            "schemaVersion": "messages-v1",
            "messages": message_list,
            "system": system_list,
            "inferenceConfig": inf_params,
        }
        
        # 构建调用参数
        invoke_params = {
            "modelId": MODEL_ID,
            "body": json.dumps(native_request),
            "accept": "application/json",
            "contentType": "application/json"
        }
        
        # 只有非 default 时才添加 serviceTier 参数
        if tier != "default":
            invoke_params["serviceTier"] = tier
        
        response = client.invoke_model(**invoke_params)
        
        model_response = json.loads(response["body"].read())
        
        # 提取性能指标
        usage = model_response.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        
        # 从 HTTP 响应头获取真实的延迟指标
        http_headers = response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
        latency_ms = int(http_headers.get("x-amzn-bedrock-invocation-latency", 0))
        actual_tier = http_headers.get("x-amzn-bedrock-service-tier", tier)
        
        # 更新进度
        with progress_lock:
            progress_counter["count"] += 1
            if progress_counter["count"] % 50 == 0:
                print(f"  进度: {progress_counter['count']} 请求完成...")
        
        return {
            "success": True,
            "tier": tier,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "actual_tier": actual_tier
        }
        
    except Exception as e:
        # 更新进度
        with progress_lock:
            progress_counter["count"] += 1
            if progress_counter["count"] % 50 == 0:
                print(f"  进度: {progress_counter['count']} 请求完成...")
        
        return {
            "success": False,
            "tier": tier,
            "error": str(e)
        }

print(f"\n{'='*80}")
print(f"Service Tier 并发性能测试")
print(f"{'='*80}")
print(f"测试模型: US (美国) - {MODEL_ID}")
print(f"测试图片: {len(test_images)} 张 ({', '.join([img.name for img in test_images])})")
print(f"并发级别: {CONCURRENCY}")
print(f"测试 Tiers: {', '.join(SERVICE_TIERS)}")
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")

# 对每个 tier 进行测试
for tier in SERVICE_TIERS:
        print(f"\n{'─'*80}")
        print(f"  Service Tier: {tier.upper()}")
        print(f"  定价: {'0.5x (50% 折扣)' if tier == 'flex' else '1.0x (基准)' if tier == 'default' else '1.75x (75% 溢价)'}")
        print(f"{'─'*80}\n")
        
        stats_key = f"{concurrency}_{tier}"
        
        # 重置进度计数器
        with progress_lock:
            progress_counter["count"] = 0
        
        # 创建请求列表 (循环使用5张不同的图片)
        requests = []
        for i in range(concurrency):
            # 使用模运算循环选择图片
            image_to_use = test_images[i % len(test_images)]
            requests.append((tier, image_to_use, f"{image_to_use.name}_{i}"))
        
        total_requests = len(requests)
        tier_stats[stats_key]["total_requests"] = total_requests
    
        print(f"  总请求数: {total_requests}")
        print(f"  开始并发测试...\n")
        
        start_time = time.time()
        
        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(process_single_request, *req) for req in requests]
            
            for future in as_completed(futures):
                result = future.result()
                
                with stats_lock:
                    if result["success"]:
                        tier_stats[stats_key]["successful"] += 1
                        tier_stats[stats_key]["latencies_ms"].append(result["latency_ms"])
                        tier_stats[stats_key]["input_tokens"].append(result["input_tokens"])
                        tier_stats[stats_key]["output_tokens"].append(result["output_tokens"])
                    else:
                        tier_stats[stats_key]["failed"] += 1
                        tier_stats[stats_key]["errors"][result["error"]] += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        tier_stats[stats_key]["total_time"] = total_time
        
        # 打印该 tier 的统计
        print(f"\n  {tier.upper()} Tier 完成:")
        print(f"    总耗时: {total_time:.2f}秒")
        print(f"    成功: {tier_stats[stats_key]['successful']}")
        print(f"    失败: {tier_stats[stats_key]['failed']}")
        if tier_stats[stats_key]["latencies_ms"]:
            latencies = tier_stats[stats_key]['latencies_ms']
            latencies_sorted = sorted(latencies)
            p95_idx = int(len(latencies_sorted) * 0.95)
            p99_idx = int(len(latencies_sorted) * 0.99)
            
            print(f"    平均延迟: {mean(latencies):.0f}ms")
            print(f"    中位数延迟: {median(latencies):.0f}ms")
            print(f"    P95 延迟: {latencies_sorted[p95_idx]}ms")
            print(f"    P99 延迟: {latencies_sorted[p99_idx]}ms")
            print(f"    最快: {min(latencies)}ms")
            print(f"    最慢: {max(latencies)}ms")
        
        # 每轮测试后等待80秒
        if tier != SERVICE_TIERS[-1] or concurrency != CONCURRENCY_LEVELS[-1]:
            print(f"\n  ⏳ 等待 80 秒后继续下一轮测试...")
            time.sleep(80)

# 打印对比报告
print(f"\n\n{'='*80}")
print(f"Service Tier 并发性能对比报告")
print(f"{'='*80}")
print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 按并发级别分组显示对比表格
for concurrency in CONCURRENCY_LEVELS:
    print(f"\n## 并发级别: {concurrency}")
    print(f"{'─'*80}")
    print(f"{'Tier':<12} {'定价':<15} {'成功率':<10} {'平均延迟':<12} {'P95延迟':<12} {'P99延迟':<12}")
    print(f"{'-'*80}")
    
    for tier in SERVICE_TIERS:
        stats_key = f"{concurrency}_{tier}"
        stats = tier_stats[stats_key]
        pricing = "0.5x (50%↓)" if tier == "flex" else "1.0x (基准)" if tier == "default" else "1.75x (75%↑)"
        
        if stats["latencies_ms"]:
            success_rate = stats['successful'] / stats['total_requests'] * 100
            avg_latency = mean(stats["latencies_ms"])
            latencies_sorted = sorted(stats["latencies_ms"])
            p95_idx = int(len(latencies_sorted) * 0.95)
            p99_idx = int(len(latencies_sorted) * 0.99)
            p95_latency = latencies_sorted[p95_idx]
            p99_latency = latencies_sorted[p99_idx]
            
            print(f"{tier:<12} {pricing:<15} {success_rate:<10.1f}% {avg_latency:<12.0f} {p95_latency:<12} {p99_latency:<12}")

# 详细统计
print(f"\n{'='*80}")
print(f"详细性能指标")
print(f"{'='*80}\n")

for concurrency in CONCURRENCY_LEVELS:
    print(f"\n{'='*80}")
    print(f"并发级别: {concurrency}")
    print(f"{'='*80}\n")
    
    for tier in SERVICE_TIERS:
        stats_key = f"{concurrency}_{tier}"
        stats = tier_stats[stats_key]
        pricing = "0.5x (50% 折扣)" if tier == "flex" else "1.0x (基准)" if tier == "default" else "1.75x (75% 溢价)"
        
        print(f"## {tier.upper()} Tier - {pricing}")
        print(f"{'─'*80}")
        
        print(f"📊 处理统计:")
        print(f"  总请求数: {stats['total_requests']}")
        print(f"  成功: {stats['successful']}")
        print(f"  失败: {stats['failed']}")
        print(f"  成功率: {stats['successful']/stats['total_requests']*100:.1f}%")
        print(f"  总耗时: {stats['total_time']:.2f}秒")
        
        if stats["latencies_ms"]:
            latencies_sorted = sorted(stats["latencies_ms"])
            p95_idx = int(len(latencies_sorted) * 0.95)
            p99_idx = int(len(latencies_sorted) * 0.99)
            
            print(f"\n⚡ Bedrock 延迟统计 (服务端):")
            print(f"  平均延迟: {mean(stats['latencies_ms']):.0f}ms")
            print(f"  中位数: {median(stats['latencies_ms']):.0f}ms")
            print(f"  P95: {latencies_sorted[p95_idx]}ms")
            print(f"  P99: {latencies_sorted[p99_idx]}ms")
            print(f"  最快: {min(stats['latencies_ms'])}ms")
            print(f"  最慢: {max(stats['latencies_ms'])}ms")
        
        if stats["input_tokens"]:
            print(f"\n🔤 Token 统计:")
            print(f"  输入 Token - 平均: {mean(stats['input_tokens']):.0f}")
            print(f"  输入 Token - 总计: {sum(stats['input_tokens'])}")
            print(f"  输出 Token - 平均: {mean(stats['output_tokens']):.0f}")
            print(f"  输出 Token - 总计: {sum(stats['output_tokens'])}")
            print(f"  总 Token: {sum(stats['input_tokens']) + sum(stats['output_tokens'])}")
        
        if stats["errors"]:
            print(f"\n❌ 错误统计:")
            for error_msg, count in stats["errors"].items():
                print(f"  [{count}次] {error_msg}")
        
        print()

# 性能对比分析
print(f"{'='*80}")
print(f"性能对比分析")
print(f"{'='*80}\n")

for concurrency in CONCURRENCY_LEVELS:
    print(f"\n## 并发级别: {concurrency}")
    print(f"{'─'*80}")
    
    stats_keys = [f"{concurrency}_{tier}" for tier in SERVICE_TIERS]
    if all(tier_stats[key]["latencies_ms"] for key in stats_keys):
        default_avg = mean(tier_stats[f"{concurrency}_default"]["latencies_ms"])
        flex_avg = mean(tier_stats[f"{concurrency}_flex"]["latencies_ms"])
        priority_avg = mean(tier_stats[f"{concurrency}_priority"]["latencies_ms"])
        
        print(f"⚡ Bedrock 延迟对比 (相对于 Default):")
        print(f"  Flex:     {flex_avg:.0f}ms ({(flex_avg/default_avg-1)*100:+.1f}%)")
        print(f"  Default:  {default_avg:.0f}ms (基准)")
        print(f"  Priority: {priority_avg:.0f}ms ({(priority_avg/default_avg-1)*100:+.1f}%)")
        
        print(f"\n💰 性价比分析 (速度/价格):")
        # 延迟越低越好，所以用 1/latency
        flex_value = (1000/flex_avg) / 0.5
        default_value = (1000/default_avg) / 1.0
        priority_value = (1000/priority_avg) / 1.75
        
        print(f"  Flex:     {flex_value:.2f} (性价比指数)")
        print(f"  Default:  {default_value:.2f} (性价比指数)")
        print(f"  Priority: {priority_value:.2f} (性价比指数)")
        
        best_value = max(flex_value, default_value, priority_value)
        if best_value == flex_value:
            print(f"\n🏆 最佳性价比: Flex Tier")
        elif best_value == default_value:
            print(f"\n🏆 最佳性价比: Default Tier")
        else:
            print(f"\n🏆 最佳性价比: Priority Tier")
        
        print(f"\n📈 并发性能观察:")
        print(f"  在 {concurrency} 并发下，Priority Tier 的优势:")
        if priority_avg < default_avg:
            improvement = (1 - priority_avg/default_avg) * 100
            print(f"  - 比 Default 快 {improvement:.1f}%")
            print(f"  - 在高负载场景下，Priority 可以提供更稳定的低延迟")
        else:
            print(f"  - 在当前负载下，Priority 优势不明显")

print(f"\n{'='*80}")
