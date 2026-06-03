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
        ]:
            self.assertIn(expected, contract)

    def test_readme_links_cto_build_path(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in [
            "CTO Handoff",
            "Architecture",
            "Live Integration Contract",
        ]:
            self.assertIn(expected, readme)

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
        self.assertIn("docs/JUDGE_REVIEW_GUIDE.md", readme)
        self.assertIn("AGENTS.md", readme)
        self.assertEqual(manifest["agent_reviewer_instructions"], "AGENTS.md")
        self.assertEqual(manifest["reviewer_entrypoint"], "docs/JUDGE_REVIEW_GUIDE.md")
        self.assertIn("python3 -m agent.contract --all", manifest["five_minute_review_commands"])

    def test_judge_review_guide_preserves_private_boundary(self) -> None:
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        for expected in [
            "Five-Minute Path",
            "python3 -m agent.demo",
            "python3 -m agent.contract --all",
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
            "python3 -m agent.demo",
            "python3 -m agent.review --list",
            "python3 -m agent.contract --all",
            "python3 -m unittest discover -s tests",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, agents)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, agents)


if __name__ == "__main__":
    unittest.main()
