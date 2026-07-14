from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_guardrail import GuardrailConfig, InputGuardrail
from agent_guardrail.evaluation import evaluate_cases, load_cases
from agent_guardrail.layers.model import TransformersModelDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate guardrail cases.")
    parser.add_argument(
        "--cases",
        default="tests/fixtures/prompt_injection_cases.json",
        help="Path to local evaluation cases.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path for detailed results.",
    )
    parser.add_argument(
        "--use-transformers",
        action="store_true",
        help="Use a real Transformers model for L3.",
    )
    parser.add_argument(
        "--model",
        default="protectai/deberta-v3-base-prompt-injection-v2",
        help="Hugging Face model id or local model directory.",
    )
    parser.add_argument("--cache-dir", default=None, help="Model cache directory.")
    parser.add_argument("--revision", default=None, help="Model revision.")
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Load model from local files only.",
    )
    parser.add_argument("--block-threshold", type=float, default=0.85)
    parser.add_argument("--gray-threshold", type=float, default=0.55)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = GuardrailConfig(
        hf_model_name=args.model,
        model_cache_dir=args.cache_dir,
        model_revision=args.revision,
        model_local_files_only=args.local_files_only,
        block_threshold=args.block_threshold,
        gray_threshold=args.gray_threshold,
    )

    model_detector = None
    if args.use_transformers:
        model_detector = TransformersModelDetector(config)

    guardrail = InputGuardrail(config=config, model_detector=model_detector)
    report = evaluate_cases(guardrail, load_cases(args.cases))

    print_summary(report["summary"])
    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0


def print_summary(summary: dict) -> None:
    print(f"Total: {summary['total']}")
    print(f"Strict action accuracy: {summary['strict_action_accuracy']:.2%}")
    print(f"Policy accuracy: {summary['policy_accuracy']:.2%}")
    print(f"Attack block recall: {summary['attack_block_recall']:.2%}")
    print(f"Attack detection recall: {summary['attack_detection_recall']:.2%}")
    print(
        "Safe block false positive rate: "
        f"{summary['safe_block_false_positive_rate']:.2%}"
    )
    print(f"Safe not-allowed rate: {summary['safe_not_allowed_rate']:.2%}")
    print("By category:")
    for category, values in summary["by_category"].items():
        print(
            f"  - {category}: {values['correct']}/{values['total']} "
            f"({values['accuracy']:.2%})"
        )


if __name__ == "__main__":
    raise SystemExit(main())
