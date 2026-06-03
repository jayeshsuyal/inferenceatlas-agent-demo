import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.packet_diff import build_packet_diff_report, render_packet_diff_markdown


ROOT = Path(__file__).resolve().parents[1]


class PacketDiffTests(unittest.TestCase):
    def test_packet_diff_proves_scenario_spread(self) -> None:
        report = build_packet_diff_report()

        self.assertEqual(report["schema_version"], "agent_packet_diff.v0")
        self.assertEqual(report["mode"], "offline_deterministic")
        self.assertEqual(
            report["scenario_order"],
            ["support_triage_agent", "read_only_analytics_agent", "admin_code_fix_bot"],
        )
        self.assertTrue(report["summary"]["has_relaxed_read_only_lane"])
        self.assertTrue(report["summary"]["has_proof_routed_lane"])
        self.assertTrue(report["summary"]["has_blocked_critical_lane"])
        self.assertTrue(report["summary"]["all_production_access_blocked"])
        self.assertTrue(report["summary"]["all_external_writes_blocked"])
        self.assertGreaterEqual(report["summary"]["differing_field_count"], 8)

    def test_packet_diff_compares_load_bearing_fields(self) -> None:
        report = build_packet_diff_report()
        fields = {item["path"]: item for item in report["load_bearing_fields"]}

        self.assertEqual(
            fields["approval_posture.write_access"]["values"],
            {
                "support_triage_agent": "blocked_until_rollback_and_off_switch_proof",
                "read_only_analytics_agent": "not_requested",
                "admin_code_fix_bot": "blocked_due_to_admin_and_production_mutation",
            },
        )
        self.assertTrue(fields["approval_posture.write_access"]["differs_across_scenarios"])
        self.assertEqual(
            fields["go_no_go.production_access"]["values"],
            {
                "support_triage_agent": False,
                "read_only_analytics_agent": False,
                "admin_code_fix_bot": False,
            },
        )
        self.assertFalse(fields["go_no_go.production_access"]["differs_across_scenarios"])
        self.assertTrue(fields["policy_gate.decision"]["differs_across_scenarios"])
        self.assertTrue(fields["reviewer_owners"]["differs_across_scenarios"])

    def test_packet_diff_markdown_is_skim_ready(self) -> None:
        markdown = render_packet_diff_markdown(build_packet_diff_report())

        for expected in [
            "# Packet Diff",
            "Private engine, public proof.",
            "relaxes_to_read_only_validation",
            "routes_to_proof_owner_scoped_validation",
            "hardens_to_blocked_before_validation",
            "approval_posture.write_access",
            "policy_gate.decision",
            "all production access blocked: True",
        ]:
            self.assertIn(expected, markdown)

    def test_packet_diff_cli_json_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.packet_diff", "--no-write", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["summary"]["has_blocked_critical_lane"])
        self.assertTrue(payload["summary"]["all_production_access_blocked"])


if __name__ == "__main__":
    unittest.main()
