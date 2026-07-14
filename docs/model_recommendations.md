# Hugging Face 中文优先模型推荐

本文列出适合接入当前 `TransformersModelDetector` 的提示词注入/越狱检测模型。当前目标是 **中文优先**，因此推荐顺序按中文/多语言能力、攻击召回率、误拦控制和部署成本综合排序。

所有候选都需要先跑本项目的本地评测集：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model <model-id>
```

如果使用内网镜像源或本地缓存，请参考 `docs/model_cache_and_migration.md`。

## 0. 中文优先结论

如果你现在主要做中文用户输入安全护栏，建议先按这个顺序评测：

1. `patronus-studio/wolf-defender-prompt-injection`
2. `devndeploy/bert-prompt-injection-detector`
3. `LLM-Research/Llama-Prompt-Guard-2-86M`（ModelScope）
4. `LLM-Research/Llama-Prompt-Guard-2-22M`（ModelScope）
5. `rogue-security/prompt-injection-jailbreak-sentinel-v2`
6. `protectai/deberta-v3-base-prompt-injection-v2`
7. `deepset/deberta-v3-base-injection`

其中：

1. **当前已测中文召回最强**：`patronus-studio/wolf-defender-prompt-injection`
2. **明确包含中文训练语言的轻量 baseline**：`devndeploy/bert-prompt-injection-detector`
3. **ModelScope 可下载但当前中文集召回不足**：`LLM-Research/Llama-Prompt-Guard-2-86M`
4. **低延迟但当前中文集召回更弱**：`LLM-Research/Llama-Prompt-Guard-2-22M`
4. **中文底座候选**：`rogue-security/prompt-injection-jailbreak-sentinel-v2`，基于 Qwen3-0.6B，但体积和依赖更重
5. **英文 baseline**：ProtectAI / Deepset，仅作为对照，不建议作为中文主模型

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
5. 官方模型卡说明 86M 版本多语言 AUC 明显优于 22M，且 22M 因缺少多语言预训练，在多语言数据上差距更大。

适用场景：

1. 中文、中英混合或多语言业务。
2. 更看重召回率和稳健性，而不是极致低延迟。
3. 可以接受 86M 模型的 CPU/GPU 推理开销。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model meta-llama/Llama-Prompt-Guard-2-86M
```

ModelScope 路径：

```python
from modelscope import snapshot_download

local_dir = snapshot_download(
    "LLM-Research/Llama-Prompt-Guard-2-86M",
    local_dir="models/Llama-Prompt-Guard-2-86M",
)
```

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model models\Llama-Prompt-Guard-2-86M
```

当前本地中文集结果（ModelScope 下载，本地加载，`block_threshold=0.85`）：

| 指标 | 值 |
| :--- | ---: |
| Accuracy | 58.14% |
| Attack block recall | 48.48% |
| Safe block false positive rate | 10.00% |
| 中文本地化攻击 accuracy | 28.57% |

结论：虽然 86M 理论上多语言能力更强，但在当前中文测试集上召回明显不足，暂不建议作为中文主模型。

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
3. 官方模型卡明确提示 22M 的多语言表现弱于 86M，因此它不应作为中文主力模型的第一选择。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model meta-llama/Llama-Prompt-Guard-2-22M
```

ModelScope 路径：

```python
from modelscope import snapshot_download

local_dir = snapshot_download(
    "LLM-Research/Llama-Prompt-Guard-2-22M",
    local_dir="models/Llama-Prompt-Guard-2-22M",
)
```

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model models\Llama-Prompt-Guard-2-22M
```

当前本地中文集结果（ModelScope 下载，本地加载，`block_threshold=0.85`）：

| 指标 | 值 |
| :--- | ---: |
| Accuracy | 39.53% |
| Attack block recall | 21.21% |
| Safe block false positive rate | 0.00% |
| 中文本地化攻击 accuracy | 14.29% |

结论：22M 误拦低，但中文攻击召回太低，不适合作为中文主模型。

## 3. 中文/多语言强候选：Wolf Defender

模型：

```text
patronus-studio/wolf-defender-prompt-injection
```

推荐理由：

1. 模型卡说明它是 Multilingual ModernBERT-based 分类器。
2. 上下文长度为 2048 tokens，比 Llama Prompt Guard 2 的 512-token 上限更适合长输入。
3. 训练增强包含 Unicode、Base64、HTML、标签包装、间距扰动等混淆方式。
4. 训练数据中包含 Mandarin 翻译/样本，适合纳入中文评测。
5. Apache-2.0 许可证，商业使用更省心。

限制：

1. 模型卡也说明其主动评测主要集中在英文和德文，Mandarin 有训练但未充分主动测试。
2. 约 0.3B 参数，延迟和资源开销高于 22M/86M 小分类器。
3. 必须用我们的中文本地数据集实测误拦率。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model patronus-studio/wolf-defender-prompt-injection
```

## 4. 明确包含中文训练语言的 baseline

模型：

```text
devndeploy/bert-prompt-injection-detector
```

推荐理由：

1. 基于 `bert-base-multilingual-cased` 微调。
2. 模型卡写明训练语言包含 Chinese、Japanese、Korean 等 11+ 语言。
3. MIT 许可证。
4. 适合做中文/多语言 baseline，尤其适合和 Llama Prompt Guard 2 86M 对比。

限制：

1. 下载量和社区验证相对较少。
2. 模型卡也提示不同语言表现会变化，必须本地评测。
3. 对新型攻击和业务上下文的泛化能力未知。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model devndeploy/bert-prompt-injection-detector
```

## 5. 中文底座候选：Sentinel v2 / Qwen3

模型：

```text
rogue-security/prompt-injection-jailbreak-sentinel-v2
```

推荐理由：

1. 基于 Qwen3-0.6B，中文语义能力天然比英文 DeBERTa 更值得期待。
2. 面向 prompt injection 和 jailbreak 双任务。
3. 模型卡说明支持更长上下文，并有 GGUF 量化版本。

限制：

1. 0.6B 参数，部署成本明显高于分类小模型。
2. 许可证为 Elastic license，需要确认是否满足你的内网/商用合规要求。
3. 可能需要 `transformers >= 4.51.0`，内网依赖版本要提前验证。
4. 由于是 Qwen 架构，首次接入要确认 `AutoModelForSequenceClassification` 标签和输出是否完全兼容当前 detector。

示例：

```powershell
$env:PYTHONPATH='src'
python scripts/evaluate_cases.py --use-transformers --model rogue-security/prompt-injection-jailbreak-sentinel-v2
```

## 6. 英文 prompt injection 基线：ProtectAI DeBERTa v2

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

## 7. 更快的 ProtectAI 小模型

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

## 8. Deepset prompt injection 基线

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

## 9. ONNX 候选

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

## 10. 推荐评测顺序

建议按下面顺序在本地数据集上跑：

1. `patronus-studio/wolf-defender-prompt-injection`
2. `devndeploy/bert-prompt-injection-detector`
3. `LLM-Research/Llama-Prompt-Guard-2-86M`（ModelScope）
4. `LLM-Research/Llama-Prompt-Guard-2-22M`（ModelScope）
5. `rogue-security/prompt-injection-jailbreak-sentinel-v2`
6. `protectai/deberta-v3-base-prompt-injection-v2`
7. `deepset/deberta-v3-base-injection`
8. `protectai/deberta-v3-small-prompt-injection-v2`

选择标准：

1. 中文攻击召回率优先看 `zh_localized_attack`。
2. 抗混淆能力优先看 `advanced_obfuscation`。
3. 误拦控制优先看 `safe_boundary`。
4. 高并发入口优先比较 P95 延迟和模型大小。
