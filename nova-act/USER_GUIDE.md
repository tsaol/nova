# Nova Act 使用指南

Amazon Nova Act 是 AWS 的 AI Agent 浏览器自动化服务。

## 快速开始

### 1. 环境准备
```bash
cd /Users/caoliuh/Desktop/Codes/nova
source .venv/bin/activate  # 或使用 uv
```

### 2. 认证方式

#### 方式 A: API Key（免费，适合实验）
```bash
# 从 https://nova.amazon.com/act 获取 API Key
export NOVA_ACT_API_KEY="your-api-key"
```

#### 方式 B: AWS IAM（推荐生产环境）
```bash
# 确保 AWS credentials 已配置
export AWS_DEFAULT_REGION=us-east-1  # Nova Act 仅支持 us-east-1

# 创建 workflow definition
act workflow create --name your-workflow-name
```

### 3. 运行示例
```bash
cd nova-act
python demo_search.py
```

---

## 代码示例

### API Key 认证
```python
from nova_act import NovaAct

with NovaAct(starting_page="https://www.google.com") as nova:
    nova.act("Search for 'AWS Nova Act'")
```

### AWS IAM 认证
```python
from nova_act import NovaAct, workflow

@workflow(workflow_definition_name="my-workflow", model_id="nova-act-latest")
def my_task():
    with NovaAct(starting_page="https://www.amazon.com", headless=False) as nova:
        result = nova.act("Search for 'best selling phones' and return top 3 names")
        print(result)

if __name__ == "__main__":
    my_task()
```

### 提取结构化数据
```python
result = nova.act(
    "Extract product info",
    schema={
        "products": [{
            "name": "str",
            "price": "str",
            "rating": "str"
        }]
    }
)
print(result.parsed_response)
```

---

## CLI 命令

```bash
# 创建 workflow
act workflow create --name demo-search

# 查看 workflows
act workflow list

# 部署 workflow
act workflow deploy --name demo-search --source-dir ./nova-act
```

---

## 最佳实践

1. **拆分任务**: 将复杂操作拆成多个小的 `act()` 调用
2. **简洁 Prompt**: 指令要具体、简短
3. **非 Headless 调试**: 开发时用 `headless=False` 观察浏览器行为
4. **分辨率**: 推荐 1600x900，避免 viewport 错误

---

## 常见问题

### Q: InvalidScreenResolution 错误
A: 确保浏览器窗口足够大，或使用 `headless=False`

### Q: ResourceNotFoundException
A: 确保在 **us-east-1** 区域创建 workflow：
```bash
AWS_DEFAULT_REGION=us-east-1 act workflow create --name xxx
```

### Q: 截图超时
A: 使用 `headless=False` 模式

---

## 参考链接

- [Nova Act 官方文档](https://docs.aws.amazon.com/nova-act/latest/userguide/)
- [Nova Act Playground](https://nova.amazon.com/act)
- [VS Code 扩展](https://marketplace.visualstudio.com/items?itemName=AmazonWebServices.amazon-nova-act-extension)
- [定价](https://aws.amazon.com/nova/pricing/)
