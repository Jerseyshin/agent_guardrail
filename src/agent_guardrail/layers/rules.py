from __future__ import annotations

import re
from dataclasses import dataclass

from agent_guardrail.types import Action, GuardrailContext, LayerResult


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str
    action: Action
    risk_score: float
    category: str = "prompt_injection"


DEFAULT_RULES = (
    Rule(
        name="zh_instruction_override",
        pattern=r"忽略.*(之前|以上|所有|系统).*(指令|规则|设定)",
        action=Action.BLOCK,
        risk_score=0.95,
    ),
    Rule(
        name="en_instruction_override",
        pattern=r"(ignore|disregard).*(previous|prior|above|all).*(instruction|rule|prompt)",
        action=Action.BLOCK,
        risk_score=0.95,
    ),
    Rule(
        name="system_prompt_exfiltration",
        pattern=r"(输出|打印|展示|泄露|复述|reveal|print|show).*(系统提示词|system prompt|developer message)",
        action=Action.BLOCK,
        risk_score=0.95,
    ),
    Rule(
        name="role_jailbreak",
        pattern=r"(你现在是|扮演|act as).*(dan|开发者模式|无限制|无审查|developer mode|unrestricted)",
        action=Action.BLOCK,
        risk_score=0.9,
    ),
    Rule(
        name="safety_bypass",
        pattern=r"(绕过|关闭|禁用|bypass|disable).*(安全|过滤|审计|guardrail|policy|filter)",
        action=Action.GRAY,
        risk_score=0.7,
    ),
    Rule(
        name="chat_template_marker",
        pattern=r"<\|im_start\|>|<\|system\|>|</system>",
        action=Action.GRAY,
        risk_score=0.6,
    ),
)


class RuleDetector:
    name = "L1"

    def __init__(self, rules: tuple[Rule, ...] = DEFAULT_RULES) -> None:
        self._rules = rules
        self._compiled = tuple(
            (rule, re.compile(rule.pattern, re.IGNORECASE | re.DOTALL))
            for rule in rules
        )

    def check(self, context: GuardrailContext) -> LayerResult:
        matches: list[str] = []
        selected: Rule | None = None

        for rule, pattern in self._compiled:
            if pattern.search(context.window_text):
                matches.append(rule.name)
                if selected is None or rule.risk_score > selected.risk_score:
                    selected = rule
                if rule.action == Action.BLOCK:
                    selected = rule
                    break

        if selected is None:
            return LayerResult.unknown(self.name)

        return LayerResult(
            action=selected.action,
            risk_score=selected.risk_score,
            layer=self.name,
            category=selected.category,
            reason=selected.name,
            matches=tuple(matches),
        )
