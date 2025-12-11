# Bedrock Nova 

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

这是一个展示 Amazon Bedrock Nova 模型功能的综合示例集合，包括图像理解、图像创建、视频理解、视频创建和文本生成。

## 功能特点

- 🖼️ **图像处理**：
  - 图像理解：支持图像分析、问答、分类和摘要
  - 图像创建：根据文本描述生成图像
- 🎥 **视频处理**：
  - 视频理解：支持视频分析、问答和内容摘要
  - 视频创建：支持从文本或图像生成视频
- 📝 **文本生成**：支持流式和非流式文本生成
- 🔢 **多模态嵌入 (MME)**：为文本和图像生成嵌入向量，用于语义搜索和相似度比较

## 前置条件

- 具有 Bedrock 访问权限的 AWS 账户
- Python 3.7+
- Boto3
- 已配置 AWS 凭证

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/bedrock-nova.git
cd bedrock-nova
```

2. 安装依赖：
```bash
pip install boto3
```

3. 配置 AWS 凭证：
```bash
aws configure
```

## 使用方法

### 图像理解
```bash
python3 images/nova_image_understanding.py
```

### 图像创建
```bash
python3 images/nova_image_creation.py
```

### 视频理解
```bash
python3 video/nova_video_understanding.py
```

### 视频创建
```bash
# 从图像创建视频
python3 video/nova_video_creation_by_image.py

# 从文本创建视频
python3 video/nova_video_creation.py
```

### 文本生成
```bash
# 非流式文本生成
python3 text/nova_text_generation.py

# 流式文本生成
python3 text/nova_text_generation_streaming.py
```

### 多模态嵌入 (MME)
```bash
# 文本嵌入
python3 mme/nova_mme_demo.py

# 图像嵌入
python3 mme/nova_image_embedding_demo.py
```

## 技术规格

### 图像理解
- 总负载大小限制：25MB
- 支持的宽高比：1:1 到 1:9、2:3、2:4 及其转置
- 最小尺寸：至少一边 > 896px
- 最大分辨率：8000x8000 像素

#### 图像到令牌转换
| 图像分辨率 | 预估令牌数 |
|-----------|------------|
| 900 x 450  | ~800      |
| 900 x 900  | ~1300     |
| 1400 x 900 | ~1800     |
| 1800 x 900 | ~2400     |
| 1300 x 1300| ~2600     |

### 视频理解
- 每次请求限一个视频
- Base64 负载限制：25MB
- S3 URI 视频大小限制：1GB
- 支持的格式：MP4、MOV、MKV、WebM、FLV、MPEG、MPG、WMV、3GP

#### 视频处理
- 分辨率：所有视频转换为 672x672 方形
- 帧采样：
  - ≤16 分钟：1 FPS
  - >16 分钟：降低采样率，固定 960 帧
- 推荐时长：
  - 低动态视频：<1 小时
  - 高动态视频：<16 分钟

#### 令牌使用
| 视频时长 | 采样帧数 | 采样率 (FPS) | 令牌数 |
|---------|---------|-------------|--------|
| 10 秒    | 10      | 1           | 2,880  |
| 30 秒    | 30      | 1           | 8,640  |
| 16 分钟  | 960     | 1           | 276,480|
| 20 分钟  | 960     | 0.755       | 276,480|
| 30 分钟  | 960     | 0.5         | 276,480|
| 45 分钟  | 960     | 0.35556     | 276,480|
| 1 小时   | 960     | 0.14        | 276,480|
| 1.5 小时 | 960     | 0.096       | 276,480|

## 项目结构

```
bedrock-nova/
├── images/
│   ├── nova_image_creation.py
│   ├── nova_image_understanding.py
│   └── test1.png
├── mme/
│   ├── nova_mme_demo.py
│   └── nova_image_embedding_demo.py
├── text/
│   ├── nova_text_generation.py
│   └── nova_text_generation_streaming.py
├── video/
│   ├── nova_video_creation.py
│   ├── nova_video_creation_by_image.py
│   ├── nova_video_understanding.py
│   └── animals.mp4
├── README.md
└── README_zh.md
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m '添加某个很棒的特性'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。
