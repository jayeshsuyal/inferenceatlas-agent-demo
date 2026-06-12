import json
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "AGENTIC_REVIEW_EXPECTED_OUTPUT.md"


class AgenticReviewExpectedOutputTests(unittest.TestCase):
    def test_expected_output_doc_names_agent_review_pass_signals(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for expected in [
            "# Agentic Review Expected Output",
            "Status: public AI reviewer checklist",
            "bash scripts/run.sh",
            "bash scripts/run.sh --json",
            "python3 -m agent.judge --no-write",
            "python3 -m agent.judge --no-write --json",
            "python3 -m agent.skills",
            "python3 -m agent.skills --json",
            "python3 -m agent.packet_diff",
            "python3 -m agent.evidence_receipts",
            "python3 -m agent.packet_authority",
            "python3 -m agent.verification --all",
            "python3 -m agent.outcome_memo",
            "python3 -m agent.proof_health",
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --evidence-dir examples/evidence/support_triage_trial",
            "python3 -m agent.sponsor_proof_trace examples/requests/support_triage_trial.yml",
            "python3 -m agent.verify_artifacts",
            "python3 -m unittest discover -s tests",
            "admin_code_fix_bot",
            "Artifact Integrity Gate",
            "Agent Skills",
            "`17 / 17 stable skills available`",
            "`63 generated artifacts verified`",
            "`summary.registered_skills` is `17`",
            "`summary.stable_skills` is `17`",
            "`summary.available_stable_skills` is `17`",
            "`summary.generated_artifacts_verified` is `63`",
            "`summary.stale_artifacts` is `0`",
            "`summary.unexpected_checked_in_artifacts` is `0`",
            "`0 unexpected checked-in`",
            "Proof Health status is `drifting`",
            "`policy_gate.admin_code_fix_bot.decision` is `BLOCKED`",
            "`proof_health.human_review_required` is `true`",
            "`proof_health.approves_access` is `false`",
            "`packet_diff.has_blocked_critical_lane` is `true`",
            "Evidence Receipt Ledger JSON has `decision_lock_after` unchanged",
            "Packet Authority Snapshot JSON has `decision_lock_after` set to `scoped_validation_only`",
            "every Packet Verification result has `production_access`, `external_writes`, `permission_grants`, and `approval_granted` set to `false`",
            "`packet_outcome_memo.decision_code` is `scoped_validation_only`",
            "`packet_outcome_memo.production_access` is `false`",
            "`design_partner_outcome_memo.decision_code` is `scoped_validation_only`",
            "`design_partner_outcome_memo.production_access` is `false`",
            "`design_partner_evidence_replay.can_sponsor_change_decision` is `false`",
            "`design_partner_evidence_replay.all_non_executing` is `true`",
            "`design_partner_evidence_replay.all_non_granting` is `true`",
            "`sponsor_proof_trace.decision_lock_unchanged` is `true`",
            "`sponsor_proof_trace.all_non_executing` is `true`",
            "`sponsor_proof_trace.approves_access` is `false`",
            "`sponsor_proof_trace.approves_spend` is `false`",
            "`sponsor_proof_trace.selects_provider` is `false`",
            "`sponsor_proof_trace.guarantees_savings` is `false`",
            "`summary.sanitized_evidence_attached` is `true`",
            "`live_evidence_rehearsal.decision_locked` is `true`",
            "`private_boundary.private_source_exposed` is `false`",
            "unit tests pass in the current public suite",
            "Failure Signals",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, doc)

        for stale in ["16 / 16 stable skills available", "58 generated artifacts verified"]:
            self.assertNotIn(stale, doc)

    def test_expected_output_doc_preserves_private_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, doc, msg=f"{forbidden} leaked in agentic review doc")

    def test_manifest_and_review_surfaces_point_to_expected_output_doc(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["agentic_review_expected_output"], "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md")
        self.assertEqual(
            manifest["primary_artifacts"]["agentic_review_expected_output"],
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
        )
        self.assertIn("docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md", manifest["judge_review_path"])
        self.assertIn("docs/AGENT_SKILLS.md", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.skills", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.skills", manifest["five_minute_review_commands"])
        self.assertIn("examples/generated/packet_diff.md", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_agent.evidence_receipts.md", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_agent.evidence_receipts.json", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_agent.snapshot.json", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_agent.verification.json", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.evidence_receipts", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.packet_authority", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.verification --all", manifest["five_minute_review_commands"])
        self.assertIn("examples/generated/support_triage_agent.outcome_memo.md", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_trial.outcome_memo.md", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_trial.evidence_replay.md", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml", manifest["judge_review_path"])
        self.assertIn("examples/evidence/support_triage_trial", manifest["judge_review_path"])
        self.assertIn(
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial",
            manifest["judge_review_path"],
        )
        self.assertIn("python3 -m agent.verify_artifacts", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.verify_artifacts", manifest["five_minute_review_commands"])
        self.assertIn("agentic review expected output", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("agent skills registry", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("packet diff", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("evidence receipt ledger", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("packet authority snapshot", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("packet verification", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("packet outcome memo", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("sponsor evidence replay", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("live evidence rehearsal", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("artifact integrity gate", manifest["private_v1_boundary"]["public_proof_surface"])

        for surface in [agents, guide]:
            self.assertIn("docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md", surface)
            self.assertIn("docs/AGENT_SKILLS.md", surface)
            self.assertIn("python3 -m agent.verify_artifacts", surface)

        self.assertIn("docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md", readme)
        self.assertIn("docs/AGENT_SKILLS.md", readme)
        self.assertIn("docs/COMMAND_REFERENCE.md", readme)


if __name__ == "__main__":
    unittest.main()
