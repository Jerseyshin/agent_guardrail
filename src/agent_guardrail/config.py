from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuardrailConfig:
    rule_version: str = "2026-07-13.1"
    model_version: str = "heuristic-model.1"
    block_threshold: float = 0.85
    gray_threshold: float = 0.55
    short_text_limit: int = 2000
    window_size: int = 1000
    window_stride: int = 500
    safe_cache_ttl_seconds: int = 300
    tenant_id: str = "default"
    known_malicious_texts: tuple[str, ...] = field(default_factory=tuple)
    hf_model_name: str = "protectai/deberta-v3-base-prompt-injection-v2"
    model_cache_dir: str | None = None
    model_revision: str | None = None
    model_max_length: int = 512
    model_local_files_only: bool = False
    model_trust_remote_code: bool = False
