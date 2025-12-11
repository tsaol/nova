"""
Amazon Nova Multimodal Embeddings (MME) 基础演示
最简单的文本嵌入示例
"""

import json
import boto3


def main():
    """ Nova MME 使用示例"""
    
    # 1. 创建 Bedrock Runtime 客户端
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",  # Nova MME 目前仅在 us-east-1 可用
    )
    
    # 2. 准备请求
    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": "GENERIC_INDEX",  # 通用索引
            "embeddingDimension": 1024,           # 嵌入维度
            "text": {
                "truncationMode": "END",
                "value": "Hello, World!"
            },
        },
    }
    
    # 3. 调用模型 amazon.nova-embedding-v1:0
    #amazon.nova-2-multimodal-embeddings-v1:0
    print("正在调用 Nova Multimodal Embeddings 模型...")
    response = bedrock_runtime.invoke_model(
        body=json.dumps(request_body),
        modelId="amazon.nova-embedding-v1:0",
        accept="application/json",
        contentType="application/json",
    )
    
    # 4. 解析响应
    response_body = json.loads(response.get("body").read())
    
    # 5. 获取嵌入向量
    embedding = response_body["embeddings"][0]["embedding"]
    
    # 6. 打印结果
    print(f"\n✅ 成功生成嵌入向量！")
    print(f"   向量维度: {len(embedding)}")
    print(f"   前 10 个值: {embedding[:10]}")
    print(f"   嵌入类型: {response_body['embeddings'][0]['embeddingType']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ 错误: {e}")
        print("\n💡 提示:")
        
        if "ValidationException" in error_msg or "invalid" in error_msg.lower():
            print("  ⚠️  模型未启用或不可用")
            print("  1. 访问 Bedrock 控制台: https://console.aws.amazon.com/bedrock/")
            print("  2. 在左侧菜单选择 'Model access'")
            print("  3. 点击 'Manage model access'")
            print("  4. 找到 'Amazon Nova Multimodal Embeddings' 并启用")
            print("  5. 等待几分钟让模型访问生效")
        elif "credentials" in error_msg.lower() or "auth" in error_msg.lower():
            print("  ⚠️  AWS 凭证问题")
            print("  1. 运行: aws configure")
            print("  2. 输入你的 AWS Access Key ID 和 Secret Access Key")
        else:
            print("  1. 确保已在 Bedrock 控制台启用 Nova Multimodal Embeddings 模型")
            print("  2. 确保 AWS 凭证配置正确 (aws configure)")
            print("  3. 确保使用 us-east-1 区域")
            print("  4. 检查你的 IAM 权限是否包含 bedrock:InvokeModel")
