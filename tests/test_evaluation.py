from pathlib import Path
import unittest

from agent_guardrail import InputGuardrail
from agent_guardrail.evaluation import evaluate_cases, load_cases


FIXTURE = Path("tests/fixtures/prompt_injection_cases.json")


class EvaluationTest(unittest.TestCase):
    def test_load_local_prompt_injection_cases(self) -> None:
        cases = load_cases(FIXTURE)

        self.assertEqual(len(cases), 43)
        self.assertEqual(sum(1 for case in cases if case.label == "malicious"), 33)
        self.assertEqual(sum(1 for case in cases if case.label == "safe"), 10)

    def test_evaluate_cases_returns_summary_and_details(self) -> None:
        cases = load_cases(FIXTURE)
        report = evaluate_cases(InputGuardrail(), cases)

        self.assertEqual(report["summary"]["total"], 43)
        self.assertEqual(len(report["details"]), 43)
        self.assertIn("attack_block_recall", report["summary"])
        self.assertIn("attack_detection_recall", report["summary"])
        self.assertIn("safe_block_false_positive_rate", report["summary"])


if __name__ == "__main__":
    unittest.main()
