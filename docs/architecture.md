# 用户输入安全护栏实现架构

## 1. 模块边界

本实现将用户输入护栏拆成四类模块：

1. **Core**：统一数据结构、动作枚举、配置和流水线编排。
2. **Layers**：L0-L3 各层检测逻辑。
3. **Cache**：精确 hash 缓存和近似恶意指纹缓存。
4. **Detectors**：可替换的模型检测器接口，默认提供本地启发式实现，后续可替换为 ONNX Runtime 实现。

## 2. 检测链路

```text
raw_text
  -> L0 Normalizer
  -> Windowing
  -> L1 RuleDetector
  -> L2 FingerprintCache
  -> L3 ModelDetector
  -> Aggregate window decisions
  -> GuardrailResult
```

## 3. 核心接口

每层都接收 `GuardrailContext`，返回 `LayerResult`：

```python
class GuardrailLayer(Protocol):
    name: str

    def check(self, context: GuardrailContext) -> LayerResult:
        ...
```

最终输出统一为：

```json
{
  "action": "allow|block|gray",
  "risk_score": 0.0,
  "category": "prompt_injection",
  "reason": "matched_rule_or_model_reason",
  "matched_layers": ["L1"],
  "metadata": {}
}
```

## 4. 当前实现范围

当前版本实现：

1. L0：Unicode、URL、HTML、零宽字符、空白、大小写归一化。
2. L1：高置信提示词注入规则和灰区规则。
3. L2：精确 hash 缓存、已知恶意 SimHash 近似匹配。
4. L3：启发式模型检测器，用于本地无依赖验证；接口可替换为真实模型。
5. 端到端 `InputGuardrail` 流水线和测试。

暂不实现：

1. ONNX Runtime 真实模型推理。
2. Redis 缓存。
3. Web API 服务层。
4. 输出侧熔断、RAG 和工具护栏。
