import json
import unittest
from pathlib import Path

from agent.decision_brief import build_agent_access_decision_brief
from agent.packet import build_support_triage_decision_packet
from agent.renderers import render_decision_brief_markdown


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "agent_access_decision_brief.schema.json"
GENERATED_BRIEF_PATH = ROOT / "examples" / "generated" / "support_triage_agent.decision_brief.json"


class AgentAccessDecisionBriefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = build_support_triage_decision_packet()
        self.brief = build_agent_access_decision_brief(self.packet)
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_brief_contains_required_schema_fields(self) -> None:
        for field in self.schema["required"]:
            self.assertIn(field, self.brief)

    def test_brief_derives_from_packet_without_granting_access(self) -> None:
        self.assertEqual(self.brief["derived_from_packet_id"], self.packet["packet_id"])
        self.assertFalse(self.brief["go_no_go"]["production_access"])
        self.assertTrue(self.brief["go_no_go"]["scoped_validation_review"])
        self.assertFalse(self.brief["go_no_go"]["external_writes"])
        self.assertTrue(self.brief["go_no_go"]["composio_dry_run"])

    def test_runtime_permission_boundary_names_the_product_difference(self) -> None:
        boundary = self.brief["runtime_permission_boundary"]
        self.assertEqual(
            boundary["runtime_permission_prompt_answers"],
            "Can the agent perform this specific action now?",
        )
        self.assertEqual(
            boundary["inferenceatlas_decision_brief_answers"],
            "Should this agent be eligible for this class of access at all, and what proof is required first?",
        )
        self.assertIn("pre-permission governance review", boundary["why_this_is_different"])

    def test_access_eligibility_blocks_production_for_each_tool(self) -> None:
        systems = {item["system"] for item in self.brief["access_eligibility"]}
        self.assertEqual(systems, {"GitHub", "Jira", "Slack"})
        for item in self.brief["access_eligibility"]:
            self.assertEqual(item["eligibility"], "candidate_for_scoped_validation_review")
            self.assertEqual(item["production_status"], "blocked")
            self.assertTrue(item["required_proof"])

    def test_risk_register_contains_expected_access_risks(self) -> None:
        risks = {item["risk"] for item in self.brief["risk_register"]}
        self.assertIn("excessive agency", risks)
        self.assertIn("sensitive information exposure", risks)
        self.assertIn("prompt injection via tool content", risks)
        self.assertIn("unauthorized write actions", risks)
        self.assertIn("missing audit trail", risks)

    def test_sponsor_readiness_preserves_dry_run_default(self) -> None:
        self.assertIn("dry-run by default", self.brief["sponsor_readiness"]["composio"])
        self.assertTrue(self.brief["safety_state"]["composio_dry_run"])
        self.assertFalse(self.brief["safety_state"]["external_writes_enabled"])

    def test_markdown_renderer_includes_reviewer_brief_sections(self) -> None:
        rendered = render_decision_brief_markdown(self.brief)
        for heading in [
            "## Decision",
            "## Go / No-Go",
            "## Runtime Permission Boundary",
            "## Access Eligibility",
            "## Access Envelope",
            "## Risk Register",
            "## Reviewer Gates",
            "## Sponsor Readiness",
            "## Safety State",
        ]:
            self.assertIn(heading, rendered)
        self.assertIn("Should this agent be eligible for this class of access at all", rendered)

    def test_generated_brief_artifact_matches_required_shape(self) -> None:
        generated = json.loads(GENERATED_BRIEF_PATH.read_text(encoding="utf-8"))
        for field in self.schema["required"]:
            self.assertIn(field, generated)
        self.assertEqual(generated["schema_version"], "agent_access_decision_brief.v0")
        self.assertEqual(generated["decision"]["verdict"], "Do not grant production access.")
        self.assertFalse(generated["go_no_go"]["production_access"])
        self.assertTrue(generated["go_no_go"]["scoped_validation_review"])
        self.assertTrue(generated["safety_state"]["composio_dry_run"])


if __name__ == "__main__":
    unittest.main()
