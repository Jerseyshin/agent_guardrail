from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from agent_guardrail.config import GuardrailConfig
from agent_guardrail.layers.normalizer import TextNormalizer
from agent_guardrail.types import Action, GuardrailContext, LayerResult


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def simhash(text: str, bits: int = 64) -> int:
    tokens = [token for token in text.split(" ") if token]
    if not tokens:
        return 0

    weights = [0] * bits
    for token in tokens:
        digest = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        for index in range(bits):
            if digest & (1 << index):
                weights[index] += 1
            else:
                weights[index] -= 1

    result = 0
    for index, weight in enumerate(weights):
        if weight > 0:
            result |= 1 << index
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


@dataclass(frozen=True)
class CachedDecision:
    action: Action
    risk_score: float
    expires_at: float
    rule_version: str
    model_version: str
    tenant_id: str


class FingerprintCacheLayer:
    name = "L2"

    def __init__(
        self,
        config: GuardrailConfig,
        normalizer: TextNormalizer | None = None,
        malicious_distance_threshold: int = 3,
    ) -> None:
        self._config = config
        self._normalizer = normalizer or TextNormalizer()
        self._malicious_distance_threshold = malicious_distance_threshold
        self._decisions: dict[str, CachedDecision] = {}
        self._known_malicious_hashes: set[str] = set()
        self._known_malicious_fingerprints: set[int] = set()

        for text in config.known_malicious_texts:
            normalized = self._normalizer.normalize(text)
            self.add_known_malicious(normalized)

    def add_known_malicious(self, normalized_text: str) -> None:
        self._known_malicious_hashes.add(stable_hash(normalized_text))
        self._known_malicious_fingerprints.add(simhash(normalized_text))

    def remember(self, normalized_text: str, action: Action, risk_score: float) -> None:
        if action not in (Action.ALLOW, Action.BLOCK):
            return

        ttl = self._config.safe_cache_ttl_seconds
        self._decisions[stable_hash(normalized_text)] = CachedDecision(
            action=action,
            risk_score=risk_score,
            expires_at=time.time() + ttl,
            rule_version=self._config.rule_version,
            model_version=self._config.model_version,
            tenant_id=self._config.tenant_id,
        )

    def check(self, context: GuardrailContext) -> LayerResult:
        text_hash = stable_hash(context.window_text)
        if text_hash in self._known_malicious_hashes:
            return LayerResult(
                action=Action.BLOCK,
                risk_score=0.95,
                layer=self.name,
                reason="known_malicious_hash",
                matches=("known_malicious_hash",),
            )

        cached = self._decisions.get(text_hash)
        if cached and self._is_fresh(cached):
            return LayerResult(
                action=cached.action,
                risk_score=cached.risk_score,
                layer=self.name,
                reason="cached_exact_decision",
                matches=("cached_exact_decision",),
            )

        current_fingerprint = simhash(context.window_text)
        for malicious_fingerprint in self._known_malicious_fingerprints:
            distance = hamming_distance(current_fingerprint, malicious_fingerprint)
            if distance <= self._malicious_distance_threshold:
                return LayerResult(
                    action=Action.GRAY,
                    risk_score=0.7,
                    layer=self.name,
                    reason="near_known_malicious_fingerprint",
                    matches=("near_known_malicious_fingerprint",),
                    metadata={"hamming_distance": distance},
                )

        return LayerResult.unknown(self.name)

    def _is_fresh(self, cached: CachedDecision) -> bool:
        return (
            cached.expires_at >= time.time()
            and cached.rule_version == self._config.rule_version
            and cached.model_version == self._config.model_version
            and cached.tenant_id == self._config.tenant_id
        )
