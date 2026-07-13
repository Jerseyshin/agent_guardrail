from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Action(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    GRAY = "gray"
    UNKNOWN = "unknown"


ACTION_RANK = {
    Action.UNKNOWN: 0,
    Action.ALLOW: 1,
    Action.GRAY: 2,
    Action.BLOCK: 3,
}


@dataclass(frozen=True)
class GuardrailContext:
    raw_text: str
    normalized_text: str
    window_text: str
    window_index: int = 0
    window_start: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LayerResult:
    action: Action
    risk_score: float
    layer: str
    category: str = "prompt_injection"
    reason: str = ""
    matches: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def unknown(layer: str) -> "LayerResult":
        return LayerResult(action=Action.UNKNOWN, risk_score=0.0, layer=layer)


@dataclass(frozen=True)
class GuardrailResult:
    action: Action
    risk_score: float
    category: str
    reason: str
    matched_layers: tuple[str, ...]
    matches: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.action == Action.ALLOW
