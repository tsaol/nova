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


userLoc = 'Chinese'
userLabels = '{"1":"person wear glasses", "2":"cat is sleeping", "3":"child"}'

# Create a Bedrock Runtime client
client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

# 定义要测试的模型 ID（不同地理区域的 inference profile）
MODEL_IDS = {
    "global": "global.amazon.nova-2-lite-v1:0",
    "us": "us.amazon.nova-2-lite-v1:0",
    "eu": "eu.amazon.nova-2-lite-v1:0",
    "jp": "jp.amazon.nova-2-lite-v1:0"
}

# 定义要测试的 service tiers
SERVICE_TIERS = ["flex", "default", "priority"]

# 定义图片目录
image_dir = "./images"

# 每个模型和 tier 组合的性能统计
tier_stats = {f"{model_type}_{tier}": {
    "model_type": model_type,
    "tier": tier,
    "total_images": 0,
    "successful": 0,
    "failed": 0,
    "latencies_ms": [],
    "input_tokens": [],
    "output_tokens": [],
    "errors": []
} for model_type in MODEL_IDS.keys() for tier in SERVICE_TIERS}

# Define your system prompt(s)
extra_instruction = f"Translation in locale {userLoc} language"

system_list = [{
    "text": "You are a surveillance image analyst. Analyze images and output ONLY valid JSON."
}]

# 获取目录下所有图片文件
image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
image_files = [f for f in Path(image_dir).iterdir() if f.suffix.lower() in image_extensions]

print(f"{'='*80}")
print(f"Service Tier 性能对比测试")
print(f"{'='*80}")
print(f"测试模型: Global (全球) / US (美国) / EU (欧洲) / JP (日本)")
print(f"测试图片数: {len(image_files)}")
print(f"测试 Tiers: {', '.join(SERVICE_TIERS)}")
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")

# 对每个模型类型和 tier 进行测试
for model_type, model_id in MODEL_IDS.items():
    print(f"\n{'='*80}")
    print(f"测试模型类型: {model_type.upper()}")
    print(f"模型 ID: {model_id}")
    print(f"{'='*80}\n")
    
    for tier in SERVICE_TIERS:
        stats_key = f"{model_type}_{tier}"
        print(f"\n{'─'*80}")
        print(f"  Service Tier: {tier.upper()}")
        print(f"  定价: {'0.5x (50% 折扣)' if tier == 'flex' else '1.0x (基准)' if tier == 'default' else '1.75x (75% 溢价)'}")
        print(f"{'─'*80}\n")
        
        tier_stats[stats_key]["total_images"] = len(image_files)
    
        # 遍历处理每张图片
        for idx, image_path in enumerate(image_files, 1):
            print(f"  [{idx}/{len(image_files)}] {image_path.name}", end=" ... ")
            
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
                    "modelId": model_id,
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
                content_text = model_response["output"]["message"]["content"][0]["text"]
                usage = model_response.get("usage", {})
                input_tokens = usage.get("inputTokens", 0)
                output_tokens = usage.get("outputTokens", 0)
                
                # 从 HTTP 响应头获取真实的延迟指标
                http_headers = response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
                latency_ms = int(http_headers.get("x-amzn-bedrock-invocation-latency", 0))
                actual_tier = http_headers.get("x-amzn-bedrock-service-tier", tier)
                
                # 记录统计
                tier_stats[stats_key]["successful"] += 1
                tier_stats[stats_key]["latencies_ms"].append(latency_ms)
                tier_stats[stats_key]["input_tokens"].append(input_tokens)
                tier_stats[stats_key]["output_tokens"].append(output_tokens)
                
                print(f"✓ {latency_ms}ms | tokens(in:{input_tokens} out:{output_tokens}) | tier:{actual_tier}")
                
            except Exception as e:
                tier_stats[stats_key]["failed"] += 1
                tier_stats[stats_key]["errors"].append(str(e))
                print(f"✗ 错误: {str(e)}")
        
        # 打印该 tier 的简要统计
        if tier_stats[stats_key]["latencies_ms"]:
            print(f"\n  {tier.upper()} Tier 统计:")
            print(f"    平均延迟: {mean(tier_stats[stats_key]['latencies_ms']):.0f}ms")
            print(f"    中位数延迟: {median(tier_stats[stats_key]['latencies_ms']):.0f}ms")

# 打印对比报告
print(f"\n\n{'='*80}")
print(f"Service Tier 性能对比报告")
print(f"{'='*80}")
print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 创建对比表格
print(f"{'模型':<10} {'Tier':<12} {'定价':<15} {'成功':<8} {'平均延迟':<12} {'中位数延迟':<12} {'平均Token':<12}")
print(f"{'-'*90}")

for model_type in MODEL_IDS.keys():
    for tier in SERVICE_TIERS:
        stats_key = f"{model_type}_{tier}"
        stats = tier_stats[stats_key]
        pricing = "0.5x (50%↓)" if tier == "flex" else "1.0x (基准)" if tier == "default" else "1.75x (75%↑)"
        
        if stats["latencies_ms"]:
            avg_latency = mean(stats["latencies_ms"])
            median_latency = median(stats["latencies_ms"])
            avg_tokens = mean(stats["input_tokens"]) + mean(stats["output_tokens"])
            
            print(f"{model_type:<10} {tier:<12} {pricing:<15} {stats['successful']:<8} {avg_latency:<12.0f} {median_latency:<12.0f} {avg_tokens:<12.0f}")

# 详细统计
print(f"\n{'='*80}")
print(f"详细性能指标")
print(f"{'='*80}\n")

for model_type in MODEL_IDS.keys():
    for tier in SERVICE_TIERS:
        stats_key = f"{model_type}_{tier}"
        stats = tier_stats[stats_key]
        pricing = "0.5x (50% 折扣)" if tier == "flex" else "1.0x (基准)" if tier == "default" else "1.75x (75% 溢价)"
        
        print(f"## {model_type.upper()} - {tier.upper()} Tier - {pricing}")
        print(f"{'─'*80}")
    
    print(f"📊 处理统计:")
    print(f"  总图片数: {stats['total_images']}")
    print(f"  成功: {stats['successful']}")
    print(f"  失败: {stats['failed']}")
    print(f"  成功率: {stats['successful']/stats['total_images']*100:.1f}%")
    
    if stats["latencies_ms"]:
        print(f"\n⚡ Bedrock 延迟统计 (服务端):")
        print(f"  平均延迟: {mean(stats['latencies_ms']):.0f}ms")
        print(f"  中位数: {median(stats['latencies_ms']):.0f}ms")
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
        print(f"\n❌ 错误列表:")
        for i, error in enumerate(stats["errors"], 1):
            print(f"  {i}. {error}")
        
        print()

# 性能对比分析
print(f"{'='*80}")
print(f"性能对比分析")
print(f"{'='*80}\n")

for model_type in MODEL_IDS.keys():
    print(f"\n## {model_type.upper()} 模型对比")
    print(f"{'─'*80}")
    
    stats_keys = [f"{model_type}_{tier}" for tier in SERVICE_TIERS]
    if all(tier_stats[key]["latencies_ms"] for key in stats_keys):
        default_avg = mean(tier_stats[f"{model_type}_default"]["latencies_ms"])
        flex_avg = mean(tier_stats[f"{model_type}_flex"]["latencies_ms"])
        priority_avg = mean(tier_stats[f"{model_type}_priority"]["latencies_ms"])
        
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
            print(f"\n🏆 {model_type.upper()} 最佳性价比: Flex Tier")
        elif best_value == default_value:
            print(f"\n🏆 {model_type.upper()} 最佳性价比: Default Tier")
        else:
            print(f"\n🏆 {model_type.upper()} 最佳性价比: Priority Tier")

print(f"\n{'='*80}")
