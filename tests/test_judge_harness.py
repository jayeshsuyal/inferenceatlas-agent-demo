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
        self.assertTrue(report["sponsor_live_readiness"]["all_contracts_ready"])
        self.assertFalse(report["sponsor_live_readiness"]["default_path_requires_keys"])
        self.assertTrue(report["sponsor_live_readiness"]["all_non_executing"])
        self.assertTrue(report["sponsor_live_readiness"]["all_non_approving"])
        self.assertTrue(report["sponsor_live_readiness"]["all_non_granting"])
        self.assertTrue(report["sponsor_live_readiness"]["all_non_mutating"])
        self.assertEqual(report["policy_gate"]["admin_code_fix_bot"]["decision"], "BLOCKED")
        self.assertTrue(report["access_speed_layer"]["all_routes_immediate"])
        self.assertTrue(report["access_speed_layer"]["has_fast_lane"])
        self.assertTrue(report["access_speed_layer"]["has_proof_routed_lane"])
        self.assertTrue(report["access_speed_layer"]["has_blocked_fast_lane"])
        self.assertTrue(report["packet_diff"]["has_relaxed_read_only_lane"])
        self.assertTrue(report["packet_diff"]["has_proof_routed_lane"])
        self.assertTrue(report["packet_diff"]["has_blocked_critical_lane"])
        self.assertTrue(report["packet_diff"]["all_production_access_blocked"])
        self.assertEqual(report["packet_outcome_memo"]["decision_code"], "scoped_validation_only")
        self.assertFalse(report["packet_outcome_memo"]["production_access"])
        self.assertFalse(report["packet_outcome_memo"]["external_writes"])
        self.assertFalse(report["packet_outcome_memo"]["approves_access"])
        self.assertEqual(report["design_partner_trial"]["request_readiness"], "ready_for_scoped_trial")
        self.assertEqual(report["design_partner_trial"]["access_speed_lane"], "proof_routed_scoped_validation")
        self.assertFalse(report["design_partner_trial"]["production_access"])
        self.assertFalse(report["design_partner_trial"]["approves_access"])
        self.assertFalse(report["design_partner_trial"]["grants_permissions"])
        self.assertEqual(report["design_partner_outcome_memo"]["decision_code"], "scoped_validation_only")
        self.assertEqual(report["design_partner_outcome_memo"]["access_speed_lane"], "proof_routed_scoped_validation")
        self.assertFalse(report["design_partner_outcome_memo"]["production_access"])
        self.assertFalse(report["design_partner_outcome_memo"]["permission_grants"])
        self.assertFalse(report["design_partner_outcome_memo"]["external_writes"])
        self.assertFalse(report["design_partner_outcome_memo"]["approves_access"])
        self.assertEqual(report["design_partner_evidence_replay"]["decision_code"], "scoped_validation_only")
        self.assertEqual(report["design_partner_evidence_replay"]["provider_count"], 4)
        self.assertFalse(report["design_partner_evidence_replay"]["production_access"])
        self.assertFalse(report["design_partner_evidence_replay"]["permission_grants"])
        self.assertFalse(report["design_partner_evidence_replay"]["external_writes"])
        self.assertFalse(report["design_partner_evidence_replay"]["can_sponsor_change_decision"])
        self.assertTrue(report["design_partner_evidence_replay"]["all_non_executing"])
        self.assertTrue(report["design_partner_evidence_replay"]["all_non_approving"])
        self.assertTrue(report["design_partner_evidence_replay"]["all_non_granting"])
        self.assertTrue(report["design_partner_evidence_replay"]["all_non_mutating"])
        self.assertEqual(report["proof_health"]["scenario"], "support_triage_agent")
        self.assertEqual(report["proof_health"]["overall_status"], "drifting")
        self.assertEqual(report["proof_health"]["overall_score"], 67)
        self.assertTrue(report["proof_health"]["human_review_required"])
        self.assertFalse(report["proof_health"]["approves_access"])
        self.assertFalse(report["proof_health"]["grants_permissions"])
        self.assertFalse(report["proof_health"]["executes_external_writes"])
        self.assertFalse(report["proof_health"]["mutates_production"])

    def test_judge_report_names_primary_artifacts(self) -> None:
        report = build_judge_report(write_artifacts=False)
        artifact_paths = {item["path"] for item in report["artifact_checklist"]}

        for expected in [
            "docs/PRODUCT_TOUR.md",
            "docs/AGENT_SKILLS.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
            "examples/generated/demo_transcript.md",
            "examples/generated/trust_receipt.md",
            "examples/generated/packet_diff.md",
            "examples/generated/packet_diff.json",
            "examples/generated/support_triage_agent.outcome_memo.md",
            "examples/generated/support_triage_agent.outcome_memo.json",
            "examples/generated/sponsor_live_readiness.md",
            "examples/generated/sponsor_live_readiness.json",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.proof_health.md",
            "examples/generated/support_triage_agent.proof_health.json",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_trial_report.json",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.outcome_memo.json",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "examples/generated/support_triage_trial.evidence_replay.json",
            "examples/generated/review_room.desktop.jpg",
        ]:
            self.assertIn(expected, artifact_paths)

    def test_judge_markdown_is_skim_ready(self) -> None:
        markdown = render_judge_report_markdown(build_judge_report(write_artifacts=False))

        self.assertIn("# InferenceAtlas Judge Harness", markdown)
        self.assertIn("docs/PRODUCT_TOUR.md", markdown)
        self.assertIn("docs/AGENT_SKILLS.md", markdown)
        self.assertIn("docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md", markdown)
        self.assertIn("admin_code_fix_bot", markdown)
        self.assertIn("BLOCKED", markdown)
        self.assertIn("examples/generated/review_room.html", markdown)
        self.assertIn("docs/DESIGN_PARTNER_BRIEF.md", markdown)
        self.assertIn("docs/DESIGN_PARTNER_TRIAL_KIT.md", markdown)
        self.assertIn("examples/requests/design_partner_trial.yml", markdown)
        self.assertIn("Private engine, public proof.", markdown)
        self.assertIn("Access Speed Layer", markdown)
        self.assertIn("Packet Diff", markdown)
        self.assertIn("examples/generated/packet_diff.md", markdown)
        self.assertIn("Packet Outcome Memo", markdown)
        self.assertIn("examples/generated/support_triage_agent.outcome_memo.md", markdown)
        self.assertIn("Sponsor Live Readiness", markdown)
        self.assertIn("examples/generated/sponsor_live_readiness.md", markdown)
        self.assertIn("fast_lane_scoped_validation", markdown)
        self.assertIn("proof_routed_scoped_validation", markdown)
        self.assertIn("blocked_fast", markdown)
        self.assertIn("Design Partner Trial Runner", markdown)
        self.assertIn("Design Partner Outcome Memo", markdown)
        self.assertIn("examples/generated/support_triage_trial.outcome_memo.md", markdown)
        self.assertIn("Sponsor Evidence Replay", markdown)
        self.assertIn("examples/generated/support_triage_trial.evidence_replay.md", markdown)
        self.assertIn("sponsors can change decision: False", markdown)
        self.assertIn("Proof Health", markdown)
        self.assertIn("examples/generated/support_triage_agent.proof_health.md", markdown)
        self.assertIn("examples/requests/support_triage_trial.yml", markdown)

    def test_judge_cli_default_renders_markdown(self) -> None:
        result = self._run_judge("--no-write")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("# InferenceAtlas Judge Harness", result.stdout)
        self.assertIn("VALIDATION_ALLOWED_WITH_GATES", result.stdout)
        self.assertIn("admin_code_fix_bot", result.stdout)
        self.assertIn("Access Speed Layer", result.stdout)
        self.assertIn("Packet Diff", result.stdout)
        self.assertIn("Packet Outcome Memo", result.stdout)
        self.assertIn("Sponsor Live Readiness", result.stdout)
        self.assertIn("all non-approving: True", result.stdout)
        self.assertIn("Design Partner Trial Runner", result.stdout)
        self.assertIn("Design Partner Outcome Memo", result.stdout)
        self.assertIn("Sponsor Evidence Replay", result.stdout)
        self.assertIn("sponsors can change decision: False", result.stdout)
        self.assertIn("all non-granting: True", result.stdout)
        self.assertIn("Proof Health", result.stdout)
        self.assertIn("next human health check", result.stdout)
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
        self.assertTrue(report["sponsor_live_readiness"]["all_contracts_ready"])
        self.assertFalse(report["sponsor_live_readiness"]["default_path_requires_keys"])
        self.assertTrue(report["sponsor_adapters"]["tavily"]["human_review_required"])
        self.assertEqual(report["access_speed_layer"]["blocked_fast_count"], 1)
        self.assertTrue(report["packet_diff"]["has_blocked_critical_lane"])
        self.assertEqual(report["packet_outcome_memo"]["decision_code"], "scoped_validation_only")
        self.assertFalse(report["packet_outcome_memo"]["production_access"])
        self.assertEqual(report["design_partner_trial"]["access_speed_lane"], "proof_routed_scoped_validation")
        self.assertEqual(report["design_partner_outcome_memo"]["decision_code"], "scoped_validation_only")
        self.assertFalse(report["design_partner_outcome_memo"]["production_access"])
        self.assertEqual(report["design_partner_evidence_replay"]["decision_code"], "scoped_validation_only")
        self.assertFalse(report["design_partner_evidence_replay"]["production_access"])
        self.assertFalse(report["design_partner_evidence_replay"]["can_sponsor_change_decision"])
        self.assertTrue(report["design_partner_evidence_replay"]["all_non_executing"])
        self.assertEqual(report["proof_health"]["overall_status"], "drifting")
        self.assertFalse(report["proof_health"]["approves_access"])


if __name__ == "__main__":
    unittest.main()
