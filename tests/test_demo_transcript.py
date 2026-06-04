import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DemoTranscriptTests(unittest.TestCase):
    def test_transcript_covers_full_judge_path(self) -> None:
        transcript = (ROOT / "examples" / "generated" / "demo_transcript.md").read_text(encoding="utf-8")

        for expected in [
            "python3 -m agent.judge",
            "python3 -m agent.demo",
            "python3 -m agent.review --list",
            "python3 -m agent.contract --all",
            "python3 -m agent.gate --all",
            "python3 -m agent.adapters --all",
            "python3 -m agent.trust",
            "python3 -m agent.review_room",
            "python3 -m agent.trial examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
            "python3 -m unittest discover -s tests",
        ]:
            self.assertIn(expected, transcript)

    def test_transcript_names_review_room_artifacts(self) -> None:
        transcript = (ROOT / "examples" / "generated" / "demo_transcript.md").read_text(encoding="utf-8")

        for expected in [
            "examples/generated/trust_receipt.md",
            "examples/generated/review_room.md",
            "examples/generated/review_room.html",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "examples/generated/review_room.desktop.jpg",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_trial.packet.json",
            "examples/generated/support_triage_trial.decision_brief.json",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.outcome_memo.json",
        ]:
            self.assertIn(expected, transcript)

    def test_transcript_preserves_safety_boundary(self) -> None:
        transcript = (ROOT / "examples" / "generated" / "demo_transcript.md").read_text(encoding="utf-8")

        for expected in [
            "Approval granted: False",
            "External writes enabled: False",
            "Composio dry-run: True",
            "# InferenceAtlas Judge Harness",
            "Access Speed Layer",
            "fast_lane_scoped_validation",
            "blocked_fast",
            "Design Partner Trial Report",
            "Design Partner Outcome Memo",
            "executes external writes: False",
            "can_approve_access=False",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, transcript)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, transcript)


if __name__ == "__main__":
    unittest.main()
