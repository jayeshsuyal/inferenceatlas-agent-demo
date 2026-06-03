import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.review import render_review


ROOT = Path(__file__).resolve().parents[1]


class ReviewCliTests(unittest.TestCase):
    def _run_review(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.review", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_lists_available_scenarios(self) -> None:
        result = self._run_review("--list")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("support_triage_agent", result.stdout)
        self.assertIn("read_only_analytics_agent", result.stdout)
        self.assertIn("admin_code_fix_bot", result.stdout)

    def test_default_renders_support_triage_brief_markdown(self) -> None:
        result = self._run_review()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("# Agent Access Decision Brief: Support Triage Agent", result.stdout)
        self.assertIn("scoped validation review: True", result.stdout)
        self.assertIn("Do not grant production access.", result.stdout)

    def test_admin_scenario_renders_blocked_validation_brief(self) -> None:
        result = self._run_review("--scenario", "admin_code_fix_bot")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("# Agent Access Decision Brief: Admin Code Fix Bot", result.stdout)
        self.assertIn("scoped validation review: False", result.stdout)
        self.assertIn("blocked_until_security_review", result.stdout)

    def test_read_only_packet_json_is_machine_readable(self) -> None:
        result = self._run_review(
            "--scenario",
            "read_only_analytics_agent",
            "--artifact",
            "packet",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        packet = json.loads(result.stdout)
        self.assertEqual(packet["packet_id"], "ia-agent-access-read-only-analytics-v0")
        self.assertEqual(packet["approval_posture"]["write_access"], "not_requested")
        self.assertFalse(packet["safety_state"]["external_writes_enabled"])

    def test_render_review_helper_matches_cli_semantics(self) -> None:
        rendered = render_review("admin_code_fix_bot", artifact="packet", output_format="json")
        packet = json.loads(rendered)

        self.assertEqual(packet["approval_posture"]["validation_review"], "blocked_until_security_review")


if __name__ == "__main__":
    unittest.main()
