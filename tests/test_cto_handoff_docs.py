import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CtoHandoffDocsTests(unittest.TestCase):
    def test_cto_handoff_docs_exist(self) -> None:
        for path in [
            "docs/CTO_HANDOFF.md",
            "docs/ARCHITECTURE.md",
            "docs/LIVE_INTEGRATION_CONTRACT.md",
        ]:
            self.assertTrue((ROOT / path).exists(), msg=f"missing {path}")

    def test_cto_handoff_names_stable_and_transitional_modules(self) -> None:
        handoff = (ROOT / "docs" / "CTO_HANDOFF.md").read_text(encoding="utf-8")
        for expected in [
            "agent/demo.py",
            "agent/packet.py",
            "agent/decision_brief.py",
            "agent/proof_health.py",
            "agent/renderers.py",
            "agent/config.py",
            "agent/tools.py",
            "What Is Stable",
            "What Is Transitional",
        ]:
            self.assertIn(expected, handoff)

    def test_live_contract_preserves_safety_defaults(self) -> None:
        contract = (ROOT / "docs" / "LIVE_INTEGRATION_CONTRACT.md").read_text(encoding="utf-8")
        for expected in [
            "COMPOSIO_DRY_RUN",
            "would_execute",
            "false",
            "production access is still blocked",
            "live integrations do not auto-approve access",
            "no external writes in the default public path",
            "Proof Health reports drift and reviewer refresh work without approving access",
        ]:
            self.assertIn(expected, contract)

    def test_readme_links_cto_build_path(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in [
            "CTO Handoff",
            "Architecture",
            "Live Integration Contract",
            "Proof Health",
        ]:
            self.assertIn(expected, readme)

    def test_readme_top_fold_frames_public_harness(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        first_screen = "\n".join(readme.splitlines()[:24])
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(readme.splitlines()[0], "# InferenceAtlas — Public Agent-Access Review Harness")
        self.assertIn("Private engine, public proof.", first_screen)
        self.assertIn("python3 -m agent.judge", first_screen)
        self.assertIn("public, no-key review harness", first_screen)
        self.assertIn("not a private v1 code dump", first_screen)
        self.assertIn("tests-passing", first_screen)
        self.assertIn("CI-smoke%20green", first_screen)
        self.assertIn("public%20contract-v0", first_screen)
        self.assertIn("safety-dry--run%20default", first_screen)
        self.assertEqual(manifest["readme_headline"], "InferenceAtlas — Public Agent-Access Review Harness")
        self.assertEqual(
            manifest["readme_badges"],
            ["tests passing", "CI green", "public contract v0", "safety: dry-run default"],
        )

    def test_readme_links_public_contract_without_v1_schema_names(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")

        self.assertIn("Public Conformance Contract", readme)
        self.assertIn("Private engine, public proof.", readme)
        self.assertIn("Private engine, public proof.", contract)
        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, contract)

    def test_readme_and_manifest_point_to_judge_fast_path(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertIn("Judge Fast Path", readme)
        self.assertIn("docs/PRODUCT_TOUR.md", readme)
        self.assertIn("docs/JUDGE_REVIEW_GUIDE.md", readme)
        self.assertIn("AGENTS.md", readme)
        self.assertEqual(manifest["agent_reviewer_instructions"], "AGENTS.md")
        self.assertEqual(manifest["agentic_review_expected_output"], "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md")
        self.assertEqual(manifest["reviewer_entrypoint"], "docs/JUDGE_REVIEW_GUIDE.md")
        self.assertEqual(manifest["product_tour"], "docs/PRODUCT_TOUR.md")
        self.assertEqual(manifest["design_partner_brief"], "docs/DESIGN_PARTNER_BRIEF.md")
        self.assertEqual(manifest["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(manifest["judge_harness_command"], "python3 -m agent.judge")
        self.assertEqual(manifest["judge_harness_json_command"], "python3 -m agent.judge --json")
        self.assertIn("python3 -m agent.judge", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.contract --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.gate --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.adapters --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.trust", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.review_room", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.proof_health", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.trial examples/requests/support_triage_trial.yml", manifest["five_minute_review_commands"])
        self.assertIn("docs/PRODUCT_TOUR.md", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.proof_health.md", manifest["product_review_path"])
        self.assertEqual(manifest["policy_gate_command"], "python3 -m agent.gate --all")
        self.assertEqual(manifest["sponsor_adapter_command"], "python3 -m agent.adapters --all")
        self.assertEqual(
            manifest["design_partner_trial_runner_command"],
            "python3 -m agent.trial examples/requests/support_triage_trial.yml",
        )
        self.assertEqual(manifest["trust_receipt_command"], "python3 -m agent.trust")
        self.assertEqual(manifest["review_room_html_command"], "python3 -m agent.review_room")
        self.assertEqual(manifest["proof_health_command"], "python3 -m agent.proof_health")
        self.assertEqual(manifest["proof_health_json_command"], "python3 -m agent.proof_health --no-write --json")
        self.assertEqual(
            manifest["proof_health_surface"],
            "examples/generated/support_triage_agent.proof_health.md and examples/generated/support_triage_agent.proof_health.json",
        )
        self.assertEqual(manifest["review_room_walkthrough"], "docs/REVIEW_ROOM_WALKTHROUGH.md")
        self.assertEqual(manifest["review_room_screenshot"], "examples/generated/review_room.desktop.jpg")
        self.assertEqual(manifest["primary_artifacts"]["trust_receipt_markdown"], "examples/generated/trust_receipt.md")
        self.assertEqual(manifest["primary_artifacts"]["product_tour"], "docs/PRODUCT_TOUR.md")
        self.assertEqual(manifest["primary_artifacts"]["review_room_html"], "examples/generated/review_room.html")
        self.assertEqual(
            manifest["primary_artifacts"]["proof_health_markdown"],
            "examples/generated/support_triage_agent.proof_health.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["proof_health_json"],
            "examples/generated/support_triage_agent.proof_health.json",
        )
        self.assertEqual(manifest["primary_artifacts"]["review_room_walkthrough"], "docs/REVIEW_ROOM_WALKTHROUGH.md")
        self.assertEqual(manifest["primary_artifacts"]["review_room_screenshot"], "examples/generated/review_room.desktop.jpg")
        self.assertEqual(
            manifest["primary_artifacts"]["agentic_review_expected_output"],
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
        )
        self.assertEqual(manifest["primary_artifacts"]["design_partner_brief"], "docs/DESIGN_PARTNER_BRIEF.md")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["primary_artifacts"]["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_report_markdown"],
            "examples/generated/support_triage_trial_report.md",
        )
        self.assertEqual(manifest["primary_artifacts"]["policy_gate"], "policy/agent_access.yml")
        self.assertEqual(manifest["primary_artifacts"]["sponsor_adapters"], "agent/adapters/")

    def test_judge_review_guide_preserves_private_boundary(self) -> None:
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        for expected in [
            "Five-Minute Path",
            "docs/PRODUCT_TOUR.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
            "python3 -m agent.judge",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "python3 -m agent.demo",
            "python3 -m agent.contract --all",
            "python3 -m agent.gate --all",
            "python3 -m agent.adapters --all",
            "python3 -m agent.trust",
            "python3 -m agent.review_room",
            "python3 -m agent.proof_health",
            "examples/generated/trust_receipt.md",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.proof_health.md",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "examples/generated/review_room.desktop.jpg",
            "policy/agent_access.yml",
            "What This Does Not Expose",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, guide)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, guide)

    def test_agents_file_guides_ai_review_without_secrets(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        for expected in [
            "Agent Reviewer Instructions",
            "Do not request secrets",
            "docs/PRODUCT_TOUR.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
            "python3 -m agent.judge",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "python3 -m agent.demo",
            "python3 -m agent.review --list",
            "python3 -m agent.contract --all",
            "python3 -m agent.gate --all",
            "python3 -m agent.adapters --all",
            "python3 -m agent.trust",
            "python3 -m agent.review_room",
            "python3 -m agent.proof_health",
            "examples/generated/trust_receipt.md",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.proof_health.md",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "examples/generated/review_room.desktop.jpg",
            "policy/agent_access.yml",
            "python3 -m unittest discover -s tests",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, agents)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, agents)


if __name__ == "__main__":
    unittest.main()
