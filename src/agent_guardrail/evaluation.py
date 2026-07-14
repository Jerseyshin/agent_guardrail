from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from agent_guardrail.pipeline import InputGuardrail
from agent_guardrail.types import Action


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    text: str
    label: str
    expected_action: Action
    category: str
    attack_type: str
    notes: str = ""


def load_cases(path: str | Path) -> list[EvaluationCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases: list[EvaluationCase] = []
    for item in payload:
        cases.append(
            EvaluationCase(
                id=item["id"],
                text=item["text"],
                label=item["label"],
                expected_action=Action(item["expected_action"]),
                category=item["category"],
                attack_type=item["attack_type"],
                notes=item.get("notes", ""),
            )
        )
    return cases


def evaluate_cases(
    guardrail: InputGuardrail,
    cases: Iterable[EvaluationCase],
) -> dict[str, Any]:
    details = []
    totals = {
        "total": 0,
        "correct": 0,
        "policy_correct": 0,
        "attack_total": 0,
        "attack_blocked": 0,
        "attack_detected": 0,
        "safe_total": 0,
        "safe_blocked": 0,
        "safe_not_allowed": 0,
    }
    by_category: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "correct": 0}
    )

    for case in cases:
        result = guardrail.check(case.text)
        correct = result.action == case.expected_action
        policy_correct = (
            (case.label == "malicious" and result.action != Action.ALLOW)
            or (case.label == "safe" and result.action == Action.ALLOW)
        )
        totals["total"] += 1
        totals["correct"] += int(correct)
        totals["policy_correct"] += int(policy_correct)

        if case.label == "malicious":
            totals["attack_total"] += 1
            totals["attack_blocked"] += int(result.action == Action.BLOCK)
            totals["attack_detected"] += int(result.action != Action.ALLOW)
        elif case.label == "safe":
            totals["safe_total"] += 1
            totals["safe_blocked"] += int(result.action == Action.BLOCK)
            totals["safe_not_allowed"] += int(result.action != Action.ALLOW)

        by_category[case.category]["total"] += 1
        by_category[case.category]["correct"] += int(correct)

        details.append(
            {
                "id": case.id,
                "text": case.text,
                "label": case.label,
                "expected_action": case.expected_action.value,
                "actual_action": result.action.value,
                "risk_score": result.risk_score,
                "correct": correct,
                "policy_correct": policy_correct,
                "category": case.category,
                "attack_type": case.attack_type,
                "reason": result.reason,
                "matched_layers": list(result.matched_layers),
                "matches": list(result.matches),
            }
        )

    summary = {
        "total": totals["total"],
        "strict_action_accuracy": _safe_div(totals["correct"], totals["total"]),
        "policy_accuracy": _safe_div(totals["policy_correct"], totals["total"]),
        "attack_block_recall": _safe_div(totals["attack_blocked"], totals["attack_total"]),
        "attack_detection_recall": _safe_div(
            totals["attack_detected"],
            totals["attack_total"],
        ),
        "safe_block_false_positive_rate": _safe_div(
            totals["safe_blocked"],
            totals["safe_total"],
        ),
        "safe_not_allowed_rate": _safe_div(
            totals["safe_not_allowed"],
            totals["safe_total"],
        ),
        "attack_total": totals["attack_total"],
        "safe_total": totals["safe_total"],
        "correct": totals["correct"],
        "policy_correct": totals["policy_correct"],
        "by_category": {
            category: {
                "total": values["total"],
                "correct": values["correct"],
                "accuracy": _safe_div(values["correct"], values["total"]),
            }
            for category, values in sorted(by_category.items())
        },
    }
    return {"summary": summary, "details": details}


def _safe_div(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
