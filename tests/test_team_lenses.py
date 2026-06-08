import json
import unittest

from agent.packet_detail import build_ia_packet_detail, render_ia_packet_detail_markdown
from agent.team_lenses import TEAM_LENSES_SCHEMA_VERSION, build_team_lenses
from agent.workbench import build_workbench_registry
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


EXPECTED_TEAM_IDS = {
    "product_exec",
    "engineering",
    "security_legal",
    "finance",
    "procurement",
    "ai_platform_ops",
}


class TeamLensTests(unittest.TestCase):
    def test_team_lenses_are_read_only_packet_projections_for_every_fixture(self) -> None:
        for fixture in build_workbench_registry()["fixtures"]:
            with self.subTest(fixture=fixture["fixture_id"]):
                detail = build_ia_packet_detail(fixture["fixture_id"])
                team_lenses = detail["team_lenses"]

                self.assertEqual(detail["team_lenses_schema_version"], TEAM_LENSES_SCHEMA_VERSION)
                self.assertEqual(team_lenses["schema_version"], TEAM_LENSES_SCHEMA_VERSION)
                self.assertEqual(team_lenses["packet_reference"], detail["packet_reference"])
                self.assertEqual(team_lenses["lens_count"], len(EXPECTED_TEAM_IDS))
                self.assertEqual(
                    {lens["team_id"] for lens in team_lenses["lenses"]},
                    EXPECTED_TEAM_IDS,
                )

                guardrails = team_lenses["guardrails"]
                self.assertTrue(guardrails["read_only"])
                self.assertTrue(guardrails["human_confirmation_required"])
                self.assertTrue(guardrails["does_not_approve"])
                self.assertFalse(guardrails["can_assign_work"])
                self.assertFalse(guardrails["can_dispatch_workflow"])
                self.assertFalse(guardrails["can_grant_permissions"])
                self.assertFalse(guardrails["can_mutate_packet"])
                self.assertFalse(guardrails["state_mutated"])

                for lens in team_lenses["lenses"]:
                    self.assertEqual(lens["packet_reference"], detail["packet_reference"])
                    self.assertEqual(lens["source_of_truth"], "ia_packet.packet_reference")
                    self.assertIn(lens["relevance"], {"direct", "context"})
                    self.assertTrue(lens["review_focus"])
                    self.assertTrue(lens["reviewer_owner"])
                    self.assertTrue(lens["next_validation"])
                    self.assertTrue(lens["human_confirmation_required"])
                    self.assertTrue(lens["does_not_approve"])
                    self.assertFalse(lens["can_assign_work"])
                    self.assertFalse(lens["can_dispatch_workflow"])
                    self.assertFalse(lens["can_grant_permissions"])
                    self.assertFalse(lens["can_mutate_packet"])
                    self.assertFalse(lens["state_mutated"])

    def test_team_lens_output_is_deterministic_and_public_boundary_safe(self) -> None:
        detail = build_ia_packet_detail("mcp_tool_blast_radius")

        first = build_team_lenses(detail)
        second = build_team_lenses(detail)
        self.assertEqual(first, second)

        surface = json.dumps(first, sort_keys=True)
        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, surface)

    def test_spend_fixture_has_direct_finance_procurement_and_platform_lenses(self) -> None:
        detail = build_ia_packet_detail("ai_spend_budget_overrun")
        by_id = {lens["team_id"]: lens for lens in detail["team_lenses"]["lenses"]}

        self.assertEqual(by_id["finance"]["relevance"], "direct")
        self.assertEqual(by_id["procurement"]["relevance"], "direct")
        self.assertEqual(by_id["ai_platform_ops"]["relevance"], "direct")
        self.assertIn("Finance", by_id["finance"]["reviewer_owner"])
        self.assertIn("Procurement", by_id["procurement"]["reviewer_owner"])
        self.assertIn("AI Platform", by_id["ai_platform_ops"]["reviewer_owner"])
        self.assertTrue(any("invoice" in item.lower() for item in by_id["finance"]["missing_proof"]))
        self.assertTrue(any("contract" in item.lower() for item in by_id["procurement"]["missing_proof"]))
        self.assertTrue(any("usage" in item.lower() for item in by_id["ai_platform_ops"]["missing_proof"]))

    def test_blast_radius_fixture_has_direct_security_engineering_and_platform_lenses(self) -> None:
        detail = build_ia_packet_detail("mcp_tool_blast_radius")
        by_id = {lens["team_id"]: lens for lens in detail["team_lenses"]["lenses"]}

        self.assertEqual(by_id["security_legal"]["relevance"], "direct")
        self.assertEqual(by_id["engineering"]["relevance"], "direct")
        self.assertEqual(by_id["ai_platform_ops"]["relevance"], "direct")
        self.assertTrue(any("oauth" in item.lower() for item in by_id["security_legal"]["missing_proof"]))
        self.assertTrue(any("repository" in item.lower() for item in by_id["engineering"]["missing_proof"]))
        self.assertTrue(any("connector" in item.lower() for item in by_id["ai_platform_ops"]["missing_proof"]))

    def test_packet_markdown_surfaces_team_lenses_without_new_authority(self) -> None:
        detail = build_ia_packet_detail("miasma_pre_permission_packet")
        markdown = render_ia_packet_detail_markdown(detail)

        self.assertIn("## Team Lenses", markdown)
        self.assertIn("Security / Legal", markdown)
        self.assertIn("Engineering", markdown)
        self.assertIn("AI Platform / Ops", markdown)
        self.assertNotIn("IA approved", markdown)
        self.assertNotIn("state mutated", markdown.lower())


if __name__ == "__main__":
    unittest.main()
