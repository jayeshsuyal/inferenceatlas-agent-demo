import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.outcome_memo import build_packet_outcome_memo, render_packet_outcome_memo_markdown


ROOT = Path(__file__).resolve().parents[1]


class PacketOutcomeMemoTests(unittest.TestCase):
    def test_support_triage_outcome_memo_is_scoped_validation_decision(self) -> None:
        memo = build_packet_outcome_memo("support_triage_agent")

        self.assertEqual(memo["schema_version"], "agent_packet_outcome_memo.v0")
        self.assertEqual(memo["scenario"], "support_triage_agent")
        self.assertEqual(memo["decision"]["code"], "scoped_validation_only")
        self.assertEqual(memo["decision"]["policy_gate"], "VALIDATION_ALLOWED_WITH_GATES")
        self.assertTrue(memo["decision"]["scoped_validation_review"])
        self.assertFalse(memo["decision"]["production_access"])
        self.assertFalse(memo["decision"]["external_writes"])
        self.assertEqual(len(memo["proof_debt_assignments"]), 5)
        self.assertGreaterEqual(len(memo["reviewer_routes"]), 4)
        self.assertEqual(memo["packet_refresh"]["status"], "drifting")
        self.assertEqual(memo["packet_refresh"]["next_human_health_check"], "day_30_security_engineering_review")

    def test_admin_outcome_memo_blocks_before_validation(self) -> None:
        memo = build_packet_outcome_memo("admin_code_fix_bot")

        self.assertEqual(memo["decision"]["code"], "blocked_before_validation")
        self.assertEqual(memo["decision"]["policy_gate"], "BLOCKED")
        self.assertFalse(memo["decision"]["scoped_validation_review"])
        self.assertFalse(memo["decision"]["production_access"])
        self.assertFalse(memo["decision"]["external_writes"])
        self.assertIn("No validation movement until blocked policy gates are resolved.", memo["can_move"])

    def test_outcome_memo_keeps_sponsor_tools_non_approving(self) -> None:
        memo = build_packet_outcome_memo()

        self.assertTrue(memo["sponsor_proof_slots"])
        self.assertTrue(
            all(item["authority"] == "proof_contributor_not_approval_authority" for item in memo["sponsor_proof_slots"])
        )
        self.assertFalse(memo["safety_boundary"]["approves_access"])
        self.assertFalse(memo["safety_boundary"]["grants_permissions"])
        self.assertFalse(memo["safety_boundary"]["executes_external_writes"])

    def test_outcome_memo_markdown_is_meeting_ready(self) -> None:
        markdown = render_packet_outcome_memo_markdown(build_packet_outcome_memo())

        for expected in [
            "# Packet Outcome Memo: support_triage_agent",
            "Private engine, public proof.",
            "scoped_validation_only",
            "## Can Move",
            "## Stays Blocked",
            "## Proof Debt Assignments",
            "## Reviewer Routes",
            "day_30_security_engineering_review",
            "proof_contributor_not_approval_authority",
            "approves access: False",
        ]:
            self.assertIn(expected, markdown)

    def test_outcome_memo_cli_json_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.outcome_memo", "--no-write", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"]["code"], "scoped_validation_only")
        self.assertFalse(payload["decision"]["production_access"])


if __name__ == "__main__":
    unittest.main()
