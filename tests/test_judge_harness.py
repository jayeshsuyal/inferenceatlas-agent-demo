import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.judge import build_judge_report, render_judge_report_markdown, report_has_failures


ROOT = Path(__file__).resolve().parents[1]


class JudgeHarnessTests(unittest.TestCase):
    def _run_judge(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.judge", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_judge_report_covers_safe_public_contract(self) -> None:
        report = build_judge_report(write_artifacts=False)

        self.assertEqual(report["schema_version"], "agent_judge_harness.v0")
        self.assertEqual(report["mode"], "offline_deterministic")
        self.assertEqual(report["public_contract"]["status"], "ok")
        self.assertFalse(report_has_failures(report))
        self.assertTrue(report["safety"]["all_adapters_non_executing"])
        self.assertTrue(report["safety"]["all_adapters_non_approving"])
        self.assertEqual(report["policy_gate"]["admin_code_fix_bot"]["decision"], "BLOCKED")
        self.assertTrue(report["access_speed_layer"]["all_routes_immediate"])
        self.assertTrue(report["access_speed_layer"]["has_fast_lane"])
        self.assertTrue(report["access_speed_layer"]["has_proof_routed_lane"])
        self.assertTrue(report["access_speed_layer"]["has_blocked_fast_lane"])

    def test_judge_report_names_primary_artifacts(self) -> None:
        report = build_judge_report(write_artifacts=False)
        artifact_paths = {item["path"] for item in report["artifact_checklist"]}

        for expected in [
            "examples/generated/demo_transcript.md",
            "examples/generated/trust_receipt.md",
            "examples/generated/review_room.html",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "examples/generated/review_room.desktop.jpg",
        ]:
            self.assertIn(expected, artifact_paths)

    def test_judge_markdown_is_skim_ready(self) -> None:
        markdown = render_judge_report_markdown(build_judge_report(write_artifacts=False))

        self.assertIn("# InferenceAtlas Judge Harness", markdown)
        self.assertIn("admin_code_fix_bot", markdown)
        self.assertIn("BLOCKED", markdown)
        self.assertIn("examples/generated/review_room.html", markdown)
        self.assertIn("docs/DESIGN_PARTNER_BRIEF.md", markdown)
        self.assertIn("docs/DESIGN_PARTNER_TRIAL_KIT.md", markdown)
        self.assertIn("examples/requests/design_partner_trial.yml", markdown)
        self.assertIn("Private engine, public proof.", markdown)
        self.assertIn("Access Speed Layer", markdown)
        self.assertIn("fast_lane_scoped_validation", markdown)
        self.assertIn("proof_routed_scoped_validation", markdown)
        self.assertIn("blocked_fast", markdown)

    def test_judge_cli_default_renders_markdown(self) -> None:
        result = self._run_judge("--no-write")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("# InferenceAtlas Judge Harness", result.stdout)
        self.assertIn("VALIDATION_ALLOWED_WITH_GATES", result.stdout)
        self.assertIn("admin_code_fix_bot", result.stdout)
        self.assertIn("Access Speed Layer", result.stdout)
        self.assertIn("blocked_fast", result.stdout)
        self.assertIn("proof=permission_diff", result.stdout)
        self.assertIn("human_review_required=True", result.stdout)
        self.assertIn("can_approve_access=False", result.stdout)

    def test_judge_cli_json_is_machine_readable(self) -> None:
        result = self._run_judge("--no-write", "--json")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["public_contract"]["status"], "ok")
        self.assertEqual(report["policy_gate"]["admin_code_fix_bot"]["decision"], "BLOCKED")
        self.assertEqual(report["sponsor_adapters"]["composio"]["proof_pack_types"], ["permission_diff"])
        self.assertTrue(report["sponsor_adapters"]["tavily"]["human_review_required"])
        self.assertEqual(report["access_speed_layer"]["blocked_fast_count"], 1)


if __name__ == "__main__":
    unittest.main()
