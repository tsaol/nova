"""
Amazon Nova Multimodal Embeddings (MME) - 图片嵌入 API 演示
展示如何使用 Nova MME API 获取图片的嵌入向量
"""

import base64
import json
import boto3


def main():
    """Nova MME 图片嵌入 API 使用示例"""
    
    # 1. 创建 Bedrock Runtime 客户端
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )
    
    # 2. 加载图片并转换为 base64
    image_path = "images/test1.png"
    print(f"正在加载图片: {image_path}")
    
    with open(image_path, "rb") as image_file:
        binary_data = image_file.read()
        image_base64 = base64.b64encode(binary_data).decode("utf-8")
    
    # 3. 构建请求体 - 图片嵌入
    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": "GENERIC_INDEX",  # 嵌入用途
            "embeddingDimension": 1024,           # 向量维度
            "image": {
                "format": "png",                  # 图片格式
                "source": {
                    "bytes": image_base64         # base64 编码的图片
                }
            }
        }
    }
    
    # 4. 调用 Nova MME 模型
    print("正在调用 Nova Multimodal Embeddings 模型...")
    response = bedrock_runtime.invoke_model(
        body=json.dumps(request_body),
        modelId="amazon.nova-2-multimodal-embeddings-v1:0",
        accept="application/json",
        contentType="application/json",
    )
    
    # 5. 解析响应
    response_body = json.loads(response.get("body").read())
    embedding = response_body["embeddings"][0]["embedding"]
    
    # 6. 输出结果
    print(f"\n✅ 成功生成图片嵌入向量！")
    print(f"   向量维度: {len(embedding)}")
    print(f"   嵌入类型: {response_body['embeddings'][0]['embeddingType']}")
    print(f"   前 10 个值: {embedding[:10]}")


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
        elif "credentials" in error_msg.lower() or "auth" in error_msg.lower():
            print("  ⚠️  AWS 凭证问题")
            print("  1. 运行: aws configure")
            print("  2. 输入你的 AWS Access Key ID 和 Secret Access Key")
        elif "FileNotFoundError" in str(type(e)):
            print("  ⚠️  图片文件路径问题")
            print("  1. 确保在 mme 目录下运行此脚本")
            print("  2. 或修改 image_path 变量为正确的路径")
        else:
            print("  1. 确保已在 Bedrock 控制台启用 Nova Multimodal Embeddings 模型")
            print("  2. 确保 AWS 凭证配置正确")
            print("  3. 确保使用 us-east-1 区域")
