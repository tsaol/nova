#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Flex Tier 使用示例

Flex Tier 特点：
- 价格：标准价格的 50%（0.5x）
- 使用方法：在调用 invoke_model 时添加 serviceTier="flex" 参数
"""

import boto3
import json

# 创建 Bedrock Runtime 客户端
client = boto3.client("bedrock-runtime", region_name="us-west-2")

# 准备请求
prompt = "What is Amazon Bedrock?"

request_body = {
    "schemaVersion": "messages-v1",
    "messages": [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ],
    "inferenceConfig": {
        "maxTokens": 512,
        "temperature": 0.7
    }
}

print("=" * 60)
print("使用 Flex Tier (0.5x 价格 - 50% 折扣)")
print("=" * 60)

# 使用 Flex Tier - 只需添加 serviceTier="flex" 参数
response = client.invoke_model(
    modelId="us.amazon.nova-2-lite-v1:0",
    body=json.dumps(request_body),
    contentType="application/json",
    accept="application/json",
    serviceTier="flex"  # 关键参数：指定使用 flex tier
)

# 解析响应
result = json.loads(response["body"].read())
response_text = result['output']['message']['content'][0]['text']

print(f"\n响应内容:")
print(f"{response_text}\n")

# 验证实际使用的 Service Tier
# 从 HTTP 响应头中获取 X-Amzn-Bedrock-Service-Tier
headers = response["ResponseMetadata"]["HTTPHeaders"]
actual_tier = headers.get("x-amzn-bedrock-service-tier")

print("=" * 60)
print("验证实际使用的 Service Tier")
print("=" * 60)
print(f"请求的 Tier: flex")
print(f"实际使用的 Tier: {actual_tier}")

if actual_tier == "flex":
    print("✅ 确认：成功使用 Flex Tier (价格节省 50%)")
else:
    print(f"⚠️  注意：实际使用的是 {actual_tier} tier，而不是 flex tier")

print("\n" + "=" * 60)
print("Flex Tier 使用说明")
print("=" * 60)
print("""
✅ 适用场景：
- 批量数据处理
- 离线任务
- 非实时内容生成
- 开发测试

💰 成本优势：
- 价格为标准价格的 50%
- 适合大规模批量处理，可显著降低成本

📝 使用方法：
response = client.invoke_model(
    modelId="us.amazon.nova-2-lite-v1:0",
    body=json.dumps(request_body),
    serviceTier="flex"  # 添加此参数
)

🔍 如何验证实际使用的 Tier：
从响应头中读取 X-Amzn-Bedrock-Service-Tier：

headers = response["ResponseMetadata"]["HTTPHeaders"]
actual_tier = headers.get("x-amzn-bedrock-service-tier")
print(f"实际使用的 Tier: {actual_tier}")

如果返回 "flex"，说明成功使用了 Flex Tier
""")
