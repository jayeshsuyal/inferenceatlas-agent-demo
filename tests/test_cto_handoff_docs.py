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


if __name__ == "__main__":
    unittest.main()
