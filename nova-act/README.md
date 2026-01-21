# Nova Act Demo

Amazon Nova Act 浏览器自动化演示项目（AWS IAM 认证）。

## 快速开始

### 1. 激活虚拟环境
```bash
cd /Users/caoliuh/Desktop/Codes/nova
source .venv/bin/activate
```

### 2. 创建 Workflow Definition
```bash
AWS_DEFAULT_REGION=us-east-1 act workflow create --name demo-search
```

### 3. 运行示例
```bash
AWS_DEFAULT_REGION=us-east-1 python nova-act/demo_search.py
```

## 示例文件

| 文件 | 说明 |
|------|------|
| `demo_search.py` | Amazon 商品搜索 |
| `demo_jd.py` | 京东商品搜索 |
| `demo_dreame.py` | Dreame 扫地机器人搜索 |
| `demo_google.py` | Google 搜索 |
| `demo_extract.py` | 结构化数据提取 |

## 注意事项

- Nova Act 仅支持 **us-east-1** 区域
- 使用 `headless=False` 可观察浏览器行为
- 推荐分辨率 1600x900

## 参考文档
- [Nova Act User Guide](https://docs.aws.amazon.com/nova-act/latest/userguide/)
- [USER_GUIDE.md](./USER_GUIDE.md) - 详细使用指南
