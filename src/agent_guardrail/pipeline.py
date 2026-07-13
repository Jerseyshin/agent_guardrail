from __future__ import annotations

from agent_guardrail.config import GuardrailConfig
from agent_guardrail.layers.cache import FingerprintCacheLayer
from agent_guardrail.layers.model import HeuristicModelDetector
from agent_guardrail.layers.normalizer import TextNormalizer
from agent_guardrail.layers.rules import RuleDetector
from agent_guardrail.types import ACTION_RANK, Action, GuardrailContext, GuardrailResult, LayerResult


class InputGuardrail:
    def __init__(
        self,
        config: GuardrailConfig | None = None,
        normalizer: TextNormalizer | None = None,
        rule_detector: RuleDetector | None = None,
        cache_layer: FingerprintCacheLayer | None = None,
        model_detector: HeuristicModelDetector | None = None,
    ) -> None:
        self.config = config or GuardrailConfig()
        self.normalizer = normalizer or TextNormalizer()
        self.rules = rule_detector or RuleDetector()
        self.cache = cache_layer or FingerprintCacheLayer(self.config, self.normalizer)
        self.model = model_detector or HeuristicModelDetector(self.config)

    def check(self, raw_text: str, metadata: dict | None = None) -> GuardrailResult:
        normalized_text = self.normalizer.normalize(raw_text)
        windows = self._windows(normalized_text)
        window_results: list[GuardrailResult] = []

        for index, (start, window_text) in enumerate(windows):
            context = GuardrailContext(
                raw_text=raw_text,
                normalized_text=normalized_text,
                window_text=window_text,
                window_index=index,
                window_start=start,
                metadata=metadata or {},
            )
            result = self._check_window(context)
            window_results.append(result)

            if result.action == Action.BLOCK:
                break

        final = self._aggregate(window_results)
        if final.action in (Action.ALLOW, Action.BLOCK):
            self.cache.remember(normalized_text, final.action, final.risk_score)
        return final

    def _check_window(self, context: GuardrailContext) -> GuardrailResult:
        layer_results: list[LayerResult] = []

        rule_result = self.rules.check(context)
        layer_results.append(rule_result)
        if rule_result.action == Action.BLOCK:
            return self._from_layer_results(layer_results, context)

        cache_result = self.cache.check(context)
        layer_results.append(cache_result)
        if cache_result.action in (Action.ALLOW, Action.BLOCK):
            return self._from_layer_results(layer_results, context)

        model_result = self.model.check(context)
        layer_results.append(model_result)
        return self._from_layer_results(layer_results, context)

    def _from_layer_results(
        self,
        layer_results: list[LayerResult],
        context: GuardrailContext,
    ) -> GuardrailResult:
        decisive = max(
            layer_results,
            key=lambda item: (ACTION_RANK[item.action], item.risk_score),
        )
        action = decisive.action if decisive.action != Action.UNKNOWN else Action.ALLOW
        risk_score = max(result.risk_score for result in layer_results)
        matched_layers = tuple(
            result.layer for result in layer_results if result.action != Action.UNKNOWN
        )
        matches = tuple(
            match for result in layer_results for match in result.matches
        )

        return GuardrailResult(
            action=action,
            risk_score=risk_score,
            category=decisive.category,
            reason=decisive.reason or "no_risk_detected",
            matched_layers=matched_layers,
            matches=matches,
            metadata={
                "window_index": context.window_index,
                "window_start": context.window_start,
                "rule_version": self.config.rule_version,
                "model_version": self.config.model_version,
            },
        )

    def _aggregate(self, results: list[GuardrailResult]) -> GuardrailResult:
        decisive = max(
            results,
            key=lambda item: (ACTION_RANK[item.action], item.risk_score),
        )
        matched_layers = tuple(
            layer for result in results for layer in result.matched_layers
        )
        matches = tuple(match for result in results for match in result.matches)
        return GuardrailResult(
            action=decisive.action,
            risk_score=max(result.risk_score for result in results),
            category=decisive.category,
            reason=decisive.reason,
            matched_layers=matched_layers,
            matches=matches,
            metadata={
                "windows_checked": len(results),
                "decisive_window_index": decisive.metadata.get("window_index"),
                "decisive_window_start": decisive.metadata.get("window_start"),
                "rule_version": self.config.rule_version,
                "model_version": self.config.model_version,
            },
        )

    def _windows(self, normalized_text: str) -> list[tuple[int, str]]:
        if len(normalized_text) <= self.config.short_text_limit:
            return [(0, normalized_text)]

        windows: list[tuple[int, str]] = []
        start = 0
        while start < len(normalized_text):
            window = normalized_text[start : start + self.config.window_size]
            if window:
                windows.append((start, window))
            if start + self.config.window_size >= len(normalized_text):
                break
            start += self.config.window_stride
        return windows
