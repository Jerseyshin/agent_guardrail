from __future__ import annotations

from typing import Protocol

from agent_guardrail.types import GuardrailContext, LayerResult


class GuardrailLayer(Protocol):
    name: str

    def check(self, context: GuardrailContext) -> LayerResult:
        ...
