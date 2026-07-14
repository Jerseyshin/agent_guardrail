# Hugging Face 模型推荐

本文列出适合接入当前 `TransformersModelDetector` 的提示词注入/越狱检测模型。所有候选都需要先跑本项目的本地评测集：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model <model-id>
```

如果使用内网镜像源或本地缓存，请参考 `docs/model_cache_and_migration.md`。

## 1. 首选：Llama Prompt Guard 2 86M

模型：

```text
meta-llama/Llama-Prompt-Guard-2-86M
```

推荐理由：

1. 同时面向 prompt injection 和 jailbreak。
2. 86M 版本使用 multilingual base model，更适合中文/多语言输入侧护栏。
3. 官方说明支持 512-token 上下文，长文本需要切片扫描，这与当前项目的窗口化流程匹配。
4. 相比 ProtectAI / Deepset 这类早期 prompt-injection 模型，更贴近 agentic 场景。

适用场景：

1. 中文、中英混合或多语言业务。
2. 更看重召回率和稳健性，而不是极致低延迟。
3. 可以接受 86M 模型的 CPU/GPU 推理开销。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model meta-llama/Llama-Prompt-Guard-2-86M
```

## 2. 低延迟首选：Llama Prompt Guard 2 22M

模型：

```text
meta-llama/Llama-Prompt-Guard-2-22M
```

推荐理由：

1. 22M 参数，推理成本低。
2. 同样是二分类：benign / malicious。
3. 适合放在高并发入口做实时检测。

注意事项：

1. 22M 版本更偏低延迟，中文效果要用本地数据集实测。
2. 如果中文召回不足，优先考虑 86M 版本。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model meta-llama/Llama-Prompt-Guard-2-22M
```

## 3. 英文 prompt injection 基线：ProtectAI DeBERTa v2

模型：

```text
protectai/deberta-v3-base-prompt-injection-v2
```

推荐理由：

1. 专门检测 prompt injection。
2. 兼容 `AutoModelForSequenceClassification`。
3. 有 ONNX 使用路径，适合后续优化。

限制：

1. 官方说明主要适合英文 prompt injection。
2. 不擅长 jailbreak。
3. 对中文和高级混淆需要谨慎评估。
4. 项目状态显示已归档，不应作为唯一生产防线。

适用场景：

1. 英文业务。
2. 作为 baseline 或和 Llama Prompt Guard 做对比。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model protectai/deberta-v3-base-prompt-injection-v2
```

## 4. 更快的 ProtectAI 小模型

模型：

```text
protectai/deberta-v3-small-prompt-injection-v2
```

推荐理由：

1. 比 base 版本更轻。
2. 可以作为低延迟英文检测 baseline。

限制：

1. 英文为主。
2. 不适合作为中文主模型。

## 5. Deepset prompt injection 基线

模型：

```text
deepset/deberta-v3-base-injection
```

推荐理由：

1. 使用 `INJECTION` / `LEGIT` 标签，语义清晰。
2. 适合做 baseline 对比。
3. 模型卡标注了较高 evaluation accuracy。

限制：

1. 官方说明如果在你的系统中过度敏感，需要收集业务正样本再训练。
2. 中文和越狱效果需要本地评测。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model deepset/deberta-v3-base-injection
```

## 6. ONNX 候选

如果未来要进一步压低延迟，可以关注 ONNX 版本：

```text
gravitee-io/Llama-Prompt-Guard-2-22M-onnx
protectai/deberta-v3-base-injection-onnx
```

当前项目的 `TransformersModelDetector` 先走 PyTorch/Transformers 路径。ONNX 可以作为后续独立 detector：

```text
OnnxModelDetector
  -> tokenizer
  -> onnxruntime.InferenceSession
  -> softmax
  -> LayerResult
```

## 7. 推荐评测顺序

建议按下面顺序在本地数据集上跑：

1. `meta-llama/Llama-Prompt-Guard-2-86M`
2. `meta-llama/Llama-Prompt-Guard-2-22M`
3. `protectai/deberta-v3-base-prompt-injection-v2`
4. `deepset/deberta-v3-base-injection`
5. `protectai/deberta-v3-small-prompt-injection-v2`

选择标准：

1. 中文攻击召回率优先看 `zh_localized_attack`。
2. 抗混淆能力优先看 `advanced_obfuscation`。
3. 误拦控制优先看 `safe_boundary`。
4. 高并发入口优先比较 P95 延迟和模型大小。
