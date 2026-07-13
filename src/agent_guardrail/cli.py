from __future__ import annotations

import argparse
import json
import sys

from agent_guardrail.pipeline import InputGuardrail


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check user input with the LLM guardrail.")
    parser.add_argument("text", nargs="*", help="User input text. Reads stdin when omitted.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    raw_text = " ".join(args.text) if args.text else sys.stdin.read()

    guardrail = InputGuardrail()
    result = guardrail.check(raw_text)

    payload = {
        "action": result.action.value,
        "risk_score": result.risk_score,
        "category": result.category,
        "reason": result.reason,
        "matched_layers": list(result.matched_layers),
        "matches": list(result.matches),
        "metadata": result.metadata,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
