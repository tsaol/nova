# Amazon Nova Multimodal Embeddings (MME) Demo

这个目录包含 Amazon Nova MME 的 Python 和 Java 示例代码。

## Python 示例

### 文本嵌入
```bash
uv run --with boto3 mme/nova_mme_demo.py
```

### 图片嵌入
```bash
uv run --with boto3 mme/nova_image_embedding_demo.py
```

## Java 示例

### 编译项目
```bash
cd mme
mvn clean compile
```

### 运行文本嵌入示例
```bash
mvn exec:java -Dexec.mainClass="com.example.NovaTextEmbeddingDemo"
```

### 运行图片嵌入示例
```bash
mvn exec:java -Dexec.mainClass="com.example.NovaImageEmbeddingDemo"
```

## 前置条件

### Python
- Python 3.7+
- boto3
- AWS 凭证配置

### Java
- Java 17+
- Maven 3.6+
- AWS 凭证配置

## AWS 配置

确保已配置 AWS 凭证：
```bash
aws configure
```

并在 Bedrock 控制台启用 Nova Multimodal Embeddings 模型：
1. 访问 https://console.aws.amazon.com/bedrock/
2. 选择 'Model access'
3. 启用 'Amazon Nova Multimodal Embeddings'

## 模型信息

- 模型 ID: `amazon.nova-2-multimodal-embeddings-v1:0`
- 区域: `us-east-1`
- 嵌入维度: 1024
- 支持类型: 文本、图片
