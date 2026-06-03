import json
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "AGENTIC_REVIEW_EXPECTED_OUTPUT.md"


class AgenticReviewExpectedOutputTests(unittest.TestCase):
    def test_expected_output_doc_names_agent_review_pass_signals(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for expected in [
            "# Agentic Review Expected Output",
            "Status: public AI reviewer checklist",
            "python3 -m agent.judge --no-write",
            "python3 -m agent.judge --no-write --json",
            "python3 -m agent.proof_health",
            "python3 -m unittest discover -s tests",
            "admin_code_fix_bot",
            "Proof Health status is `drifting`",
            "`policy_gate.admin_code_fix_bot.decision` is `BLOCKED`",
            "`proof_health.human_review_required` is `true`",
            "`proof_health.approves_access` is `false`",
            "`private_boundary.private_source_exposed` is `false`",
            "unit tests pass in the current public suite",
            "Failure Signals",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, doc)

    def test_expected_output_doc_preserves_private_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, doc, msg=f"{forbidden} leaked in agentic review doc")

    def test_manifest_and_review_surfaces_point_to_expected_output_doc(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["agentic_review_expected_output"], "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md")
        self.assertEqual(
            manifest["primary_artifacts"]["agentic_review_expected_output"],
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
        )
        self.assertIn("docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md", manifest["judge_review_path"])
        self.assertIn("agentic review expected output", manifest["private_v1_boundary"]["public_proof_surface"])

        for surface in [agents, readme, guide]:
            self.assertIn("docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md", surface)


if __name__ == "__main__":
    unittest.main()
