# Amazon Bedrock Service Tier 性能对比测试

本目录包含用于测试和对比 Amazon Bedrock 不同 Service Tier 性能的工具。

## 什么是 Service Tier？

Amazon Bedrock 提供四个服务层级用于模型推理，帮助您优化可用性、成本和性能：

### 1. Reserved Tier（预留层）
- 为关键任务应用预留优先计算容量
- 目标 99.5% 正常运行时间
- 需要提前预留，按月计费
- 需要联系 AWS 账户团队获取访问权限

### 2. Priority Tier（优先层）
- 提供最快的响应时间
- 价格为标准定价的 **1.75倍**（75% 溢价）
- 无需预留，请求级别优先处理
- 适合面向客户的关键业务工作流

### 3. Standard Tier（标准层）
- 默认层级，提供一致的性能
- **基准定价**（1.0x）
- 适合日常 AI 任务，如内容生成、文本分析

### 4. Flex Tier（灵活层）
- 成本优化选项，价格为标准定价的 **0.5倍**（50% 折扣）
- 可接受较长的处理时间
- 适合模型评估、内容摘要、代理工作流等对延迟不敏感的工作负载

## 文件说明

### `nova_inference_tier_comparison.py`

对比测试脚本，用于评估不同 Service Tier 的性能差异。

**功能特性：**
- 测试 Flex、Standard（default）、Priority 三个层级
- 批量处理图片目录中的所有图片
- 收集详细的性能指标：
  - API 调用时间
  - Bedrock 服务端延迟
  - Token 使用量（输入/输出）
  - 吞吐量统计
- 生成对比报告和性价比分析

**使用方法：**

```bash
# 1. 准备图片目录
mkdir -p images
# 将测试图片放入 images 目录

# 2. 配置 AWS 凭证
export AWS_REGION=us-west-2

# 3. 运行测试
python nova_inference_tier_comparison.py
```

**配置选项：**

在脚本中可以修改以下参数：

```python
# 模型 ID
MODEL_ID = "global.amazon.nova-2-lite-v1:0"

# 测试的服务层级
SERVICE_TIERS = ["flex", "default", "priority"]

# 图片目录
image_dir = "./images"

# 区域设置
region_name = "us-west-2"
```

## 输出报告

测试完成后会生成详细的对比报告，包括：

### 1. 对比表格
```
Tier         定价            成功     平均时间      平均延迟      吞吐量        平均Token    
--------------------------------------------------------------------------------
flex         0.5x (50%↓)    10       2.34         1234         4.27         1523        
default      1.0x (基准)     10       1.89         987          5.29         1523        
priority     1.75x (75%↑)   10       1.45         756          6.90         1523        
```

### 2. 详细性能指标
- 处理统计（成功率、失败数）
- 时间统计（总耗时、平均、中位数、最快/最慢）
- Bedrock 延迟统计（服务端测量）
- Token 使用统计

### 3. 性能对比分析
- 速度对比（相对于 Standard）
- 性价比分析（速度/价格比）
- 最佳性价比推荐

## 支持的模型

Priority 和 Flex 层级支持的模型包括：
- Amazon Nova 系列（Premier、Pro）
- OpenAI GPT-OSS 系列
- Qwen 系列
- DeepSeek V3.1
- 等等

详细支持列表请参考：[AWS Bedrock Service Tiers 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html)

## 注意事项

1. **配额共享**：Priority、Standard 和 Flex 层级共享同一个按需配额
2. **参数设置**：
   - Standard 层级：不设置 `serviceTier` 参数或设置为 `"default"`
   - Priority 层级：设置 `serviceTier` 为 `"priority"`
   - Flex 层级：设置 `serviceTier` 为 `"flex"`
3. **响应头**：实际使用的层级会在响应头 `x-amzn-bedrock-service-tier` 中返回
4. **CloudWatch 监控**：可以通过 CloudWatch Metrics 查看 `ServiceTier` 和 `ResolvedServiceTier` 指标

## 选择建议

| 场景 | 推荐层级 | 原因 |
|------|---------|------|
| 面向客户的实时应用 | Priority | 最快响应，用户体验最佳 |
| 日常业务处理 | Standard | 性能和成本平衡 |
| 批量处理、离线任务 | Flex | 成本最优，50% 折扣 |
| 关键任务 24x7 | Reserved | 预留容量，保证可用性 |

## 参考资源

- [Amazon Bedrock Service Tiers 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html)
- [Amazon Bedrock 定价](https://aws.amazon.com/bedrock/pricing/)
- [Amazon Bedrock API 参考](https://docs.aws.amazon.com/bedrock/latest/APIReference/)
