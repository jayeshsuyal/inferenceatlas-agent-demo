import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesignPartnerBriefTests(unittest.TestCase):
    def test_design_partner_brief_exists_and_names_trial_path(self) -> None:
        brief = (ROOT / "docs" / "DESIGN_PARTNER_BRIEF.md").read_text(encoding="utf-8")

        for expected in [
            "Design Partner Brief",
            "One-Afternoon Trial",
            "python3 -m agent.judge",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_agent.proof_health.md",
            "examples/generated/trust_receipt.md",
            "examples/generated/sponsor_live_readiness.md",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.decision_brief.md",
            "policy/agent_access.yml",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "one real internal agent-access workflow",
            "one Trust Receipt",
            "one DecisionPacket",
            "one Agent Access Decision Brief",
            "one Proof Health report",
            "one policy-gate result",
            "one dry-run tool-access plan",
            "one sponsor live-readiness report",
            "one next human validation step",
        ]:
            self.assertIn(expected, brief)

    def test_design_partner_brief_preserves_safety_boundary(self) -> None:
        brief = (ROOT / "docs" / "DESIGN_PARTNER_BRIEF.md").read_text(encoding="utf-8")

        for expected in [
            "Private engine, public proof.",
            "production credentials",
            "live sponsor tokens",
            "customer data in this public repo",
            "private prompts",
            "private v1 source code",
            "write-enabled Composio actions",
            "autonomous approval authority",
            "no access approval",
            "no permission grant",
            "no external write",
            "Composio dry-run by default",
            "human approval remains required",
        ]:
            self.assertIn(expected, brief)

    def test_design_partner_brief_is_in_manifest_and_review_path(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["design_partner_brief"], "docs/DESIGN_PARTNER_BRIEF.md")
        self.assertEqual(manifest["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_brief"], "docs/DESIGN_PARTNER_BRIEF.md")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["primary_artifacts"]["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(manifest["primary_artifacts"]["support_triage_trial_report_markdown"], "examples/generated/support_triage_trial_report.md")
        self.assertIn("docs/DESIGN_PARTNER_BRIEF.md", manifest["judge_review_path"])
        self.assertIn("sponsor live readiness", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("docs/DESIGN_PARTNER_TRIAL_KIT.md", manifest["judge_review_path"])
        self.assertIn("examples/requests/design_partner_trial.yml", manifest["judge_review_path"])
        self.assertIn("examples/requests/support_triage_trial.yml", manifest["judge_review_path"])
        self.assertIn("design partner brief", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("proof health", manifest["private_v1_boundary"]["public_proof_surface"])

    def test_design_partner_brief_does_not_expose_private_schema_names(self) -> None:
        brief = (ROOT / "docs" / "DESIGN_PARTNER_BRIEF.md").read_text(encoding="utf-8")

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, brief)


if __name__ == "__main__":
    unittest.main()
