from __future__ import annotations

from agent_guardrail.config import GuardrailConfig
from agent_guardrail.types import Action, GuardrailContext, LayerResult


class HeuristicModelDetector:
    name = "L3"

    def __init__(self, config: GuardrailConfig) -> None:
        self._config = config

    def check(self, context: GuardrailContext) -> LayerResult:
        score, reasons = self._score(context.window_text)

        if score >= self._config.block_threshold:
            action = Action.BLOCK
        elif score >= self._config.gray_threshold:
            action = Action.GRAY
        else:
            action = Action.ALLOW

        return LayerResult(
            action=action,
            risk_score=score,
            layer=self.name,
            reason=",".join(reasons) if reasons else "low_risk",
            matches=tuple(reasons),
        )

    def _score(self, text: str) -> tuple[float, list[str]]:
        score = 0.05
        reasons: list[str] = []

        override_terms = ("忽略", "忘记", "ignore", "disregard", "override")
        instruction_terms = ("指令", "规则", "设定", "instruction", "rule", "prompt")
        secret_terms = ("系统提示词", "system prompt", "developer message", "隐藏规则")
        jailbreak_terms = ("dan", "开发者模式", "developer mode", "unrestricted", "无审查")
        bypass_terms = ("绕过", "bypass", "disable", "过滤", "guardrail", "policy")

        if any(term in text for term in override_terms):
            score += 0.25
            reasons.append("override_intent")
        if any(term in text for term in instruction_terms):
            score += 0.2
            reasons.append("instruction_reference")
        if any(term in text for term in secret_terms):
            score += 0.4
            reasons.append("prompt_exfiltration")
        if any(term in text for term in jailbreak_terms):
            score += 0.35
            reasons.append("jailbreak_role")
        if any(term in text for term in bypass_terms):
            score += 0.25
            reasons.append("safety_bypass")
        if "<|im_start|>" in text or "<|system|>" in text or "</system>" in text:
            score += 0.2
            reasons.append("chat_template_marker")

        return min(score, 0.99), reasons


class TransformersModelDetector:
    name = "L3"

    def __init__(
        self,
        config: GuardrailConfig,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self._config = config
        self._model_name = model_name or config.hf_model_name

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "TransformersModelDetector requires optional dependencies. "
                "Install with: pip install -e .[hf]"
            ) from exc

        self._torch = torch
        load_kwargs = self._load_kwargs()
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name, **load_kwargs)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self._model_name,
            **load_kwargs,
        )
        self._device = self._resolve_device(device)
        self._model.to(self._device)
        self._model.eval()
        self._injection_index = self._find_injection_index()

    def check(self, context: GuardrailContext) -> LayerResult:
        inputs = self._tokenizer(
            context.window_text,
            return_tensors="pt",
            truncation=True,
            max_length=self._config.model_max_length,
        )
        inputs = {key: value.to(self._device) for key, value in inputs.items()}

        with self._torch.no_grad():
            outputs = self._model(**inputs)
            probabilities = self._torch.softmax(outputs.logits, dim=-1)[0]

        risk_score = float(probabilities[self._injection_index].detach().cpu().item())
        if risk_score >= self._config.block_threshold:
            action = Action.BLOCK
        elif risk_score >= self._config.gray_threshold:
            action = Action.GRAY
        else:
            action = Action.ALLOW

        return LayerResult(
            action=action,
            risk_score=risk_score,
            layer=self.name,
            reason="transformers_sequence_classifier",
            matches=(self._model_name,),
            metadata={
                "model_name": self._model_name,
                "cache_dir": self._config.model_cache_dir,
                "injection_index": self._injection_index,
                "local_files_only": self._config.model_local_files_only,
                "revision": self._config.model_revision,
            },
        )

    def _load_kwargs(self) -> dict:
        kwargs = {
            "local_files_only": self._config.model_local_files_only,
            "trust_remote_code": self._config.model_trust_remote_code,
        }
        if self._config.model_cache_dir:
            kwargs["cache_dir"] = self._config.model_cache_dir
        if self._config.model_revision:
            kwargs["revision"] = self._config.model_revision
        return kwargs

    def _resolve_device(self, device: str | None) -> str:
        if device:
            return device
        return "cuda" if self._torch.cuda.is_available() else "cpu"

    def _find_injection_index(self) -> int:
        id2label = getattr(self._model.config, "id2label", {}) or {}
        labels = {int(index): str(label).lower() for index, label in id2label.items()}

        for index, label in labels.items():
            if any(token in label for token in ("injection", "jailbreak", "malicious")):
                return index

        for index, label in labels.items():
            if label in {"1", "label_1"} or label.endswith("_1"):
                return index

        if self._model.config.num_labels == 2:
            return 1

        raise RuntimeError(
            f"Cannot infer injection label for model {self._model_name}. "
            f"id2label={id2label!r}"
        )
