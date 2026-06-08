import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.trial import DEFAULT_TRIAL_REQUEST
from agent.trial_evidence_replay import (
    DEFAULT_REHEARSAL_EVIDENCE_DIR,
    TRIAL_EVIDENCE_REPLAY_SCHEMA_VERSION,
    build_trial_evidence_replay,
    render_trial_evidence_replay_markdown,
    write_trial_evidence_replay_artifacts,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class TrialEvidenceReplayTests(unittest.TestCase):
    def _run_replay(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.trial_evidence_replay", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_replay_attaches_sponsor_proof_without_changing_decision(self) -> None:
        replay = build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(replay["schema_version"], TRIAL_EVIDENCE_REPLAY_SCHEMA_VERSION)
        self.assertEqual(replay["decision_lock"]["decision_code"], "scoped_validation_only")
        self.assertFalse(replay["decision_lock"]["production_access"])
        self.assertFalse(replay["decision_lock"]["permission_grants"])
        self.assertFalse(replay["decision_lock"]["external_writes"])
        self.assertFalse(replay["decision_lock"]["can_sponsor_change_decision"])
        self.assertEqual(replay["summary"]["provider_count"], 4)
        self.assertEqual(
            set(replay["sponsor_replay"]),
            {"tavily", "composio", "nebius", "openclaw"},
        )
        self.assertTrue(replay["summary"]["all_non_executing"])
        self.assertTrue(replay["summary"]["all_non_approving"])
        self.assertTrue(replay["summary"]["all_non_granting"])
        self.assertTrue(replay["summary"]["all_non_mutating"])
        self.assertGreater(replay["summary"]["proof_attachment_count"], 0)
        self.assertFalse(replay["safety_boundary"]["approves_access"])
        self.assertFalse(replay["safety_boundary"]["grants_permissions"])
        self.assertFalse(replay["safety_boundary"]["executes_external_writes"])

    def test_replay_accepts_sanitized_live_evidence_without_unlocking_decision(self) -> None:
        replay = build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, DEFAULT_REHEARSAL_EVIDENCE_DIR)

        self.assertTrue(replay["summary"]["sanitized_evidence_attached"])
        self.assertEqual(replay["summary"]["rehearsal_evidence_provider_count"], 4)
        self.assertTrue(replay["summary"]["decision_locked_after_rehearsal"])
        self.assertFalse(replay["decision_lock"]["production_access"])
        self.assertFalse(replay["decision_lock"]["permission_grants"])
        self.assertFalse(replay["decision_lock"]["external_writes"])
        self.assertFalse(replay["decision_lock"]["can_sponsor_change_decision"])
        self.assertEqual(
            replay["live_evidence_rehearsal"]["providers"],
            ["composio", "nebius", "openclaw", "tavily"],
        )
        self.assertTrue(replay["live_evidence_rehearsal"]["unsafe_inputs_rejected"])
        self.assertTrue(replay["live_evidence_rehearsal"]["proof_debt_reduction_requires_human_review"])
        self.assertTrue(replay["sponsor_replay"]["tavily"]["rehearsal_evidence_attached"])
        self.assertTrue(replay["sponsor_replay"]["composio"]["rehearsal_evidence_attached"])
        self.assertIn("source_urls", replay["sponsor_replay"]["tavily"]["attachments"][0])
        self.assertIn("dry_run_operation_id", replay["sponsor_replay"]["composio"]["attachments"][0])
        nebius_summary = replay["sponsor_replay"]["nebius"]["attachments"][0]["sanitized_reviewer_narration"][0]["summary"]
        self.assertIn("IA does not approve this request.", nebius_summary)
        self.assertIn(
            "Human review is required before any access, spend, or production movement.",
            nebius_summary,
        )
        for forbidden in ("approved", "looks fine", "should be ok", "should be okay"):
            self.assertNotIn(forbidden, nebius_summary.lower())

    def test_replay_markdown_is_skim_ready(self) -> None:
        markdown = render_trial_evidence_replay_markdown(build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST))

        for expected in [
            "# Sponsor Evidence Replay: support_triage_trial",
            "Private engine, public proof.",
            "sponsors can change decision: False",
            "all non-executing: True",
            "all non-approving: True",
            "tavily",
            "composio",
            "nebius",
            "openclaw",
            "GitHub repository allowlist",
            "examples/generated/support_triage_trial.outcome_memo.json",
        ]:
            self.assertIn(expected, markdown)

    def test_rehearsal_markdown_is_skim_ready(self) -> None:
        markdown = render_trial_evidence_replay_markdown(
            build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, DEFAULT_REHEARSAL_EVIDENCE_DIR)
        )

        for expected in [
            "## Live Evidence Rehearsal",
            "evidence dir: `examples/evidence/support_triage_trial`",
            "sanitized providers: 4",
            "unsafe inputs rejected: True",
            "decision locked: True",
            "| tavily | evidence_candidate_plan | 5 | True | False | False |",
        ]:
            self.assertIn(expected, markdown)

    def test_write_trial_evidence_replay_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_trial_evidence_replay_artifacts(DEFAULT_TRIAL_REQUEST, Path(temp_dir))

            self.assertEqual(
                {path.name for path in paths},
                {
                    "support_triage_trial.evidence_replay.md",
                    "support_triage_trial.evidence_replay.json",
                },
            )
            payload = json.loads((Path(temp_dir) / "support_triage_trial.evidence_replay.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["decision_lock"]["decision_code"], "scoped_validation_only")

    def test_write_trial_evidence_replay_artifacts_with_rehearsal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_trial_evidence_replay_artifacts(
                DEFAULT_TRIAL_REQUEST,
                Path(temp_dir),
                DEFAULT_REHEARSAL_EVIDENCE_DIR,
            )

            payload = json.loads((Path(temp_dir) / "support_triage_trial.evidence_replay.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["sanitized_evidence_attached"])
            self.assertFalse(payload["decision_lock"]["can_sponsor_change_decision"])

    def test_replay_cli_outputs_paths_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path_result = self._run_replay("examples/requests/support_triage_trial.yml", "--output-dir", temp_dir)
            self.assertEqual(path_result.returncode, 0, msg=path_result.stderr)
            self.assertIn("support_triage_trial.evidence_replay.md", path_result.stdout)

        markdown_result = self._run_replay("examples/requests/support_triage_trial.yml", "--no-write")
        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Sponsor Evidence Replay", markdown_result.stdout)

        json_result = self._run_replay("examples/requests/support_triage_trial.yml", "--no-write", "--json")
        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertFalse(payload["decision_lock"]["can_sponsor_change_decision"])
        self.assertTrue(payload["summary"]["all_non_approving"])

    def test_replay_cli_accepts_evidence_dir(self) -> None:
        json_result = self._run_replay(
            "examples/requests/support_triage_trial.yml",
            "--no-write",
            "--json",
            "--evidence-dir",
            "examples/evidence/support_triage_trial",
        )

        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertTrue(payload["summary"]["sanitized_evidence_attached"])
        self.assertFalse(payload["decision_lock"]["production_access"])

    def test_replay_rejects_secret_or_write_shaped_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_dir = Path(temp_dir)
            (evidence_dir / "tavily.json").write_text(
                json.dumps(
                    {
                        "provider": "tavily",
                        "api_key": "do-not-accept",
                        "evidence_candidates": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, evidence_dir)

        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_dir = Path(temp_dir)
            (evidence_dir / "composio.json").write_text(
                json.dumps(
                    {
                        "provider": "composio",
                        "permission_diffs": [{"tool": "github", "would_execute": True}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, evidence_dir)

        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_dir = Path(temp_dir)
            (evidence_dir / "nebius.json").write_text(
                json.dumps(
                    {
                        "provider": "nebius",
                        "narrations": [{"summary": "done", "can_reduce_proof_debt": True}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, evidence_dir)

        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_dir = Path(temp_dir)
            (evidence_dir / "nebius.json").write_text(
                json.dumps(
                    {
                        "provider": "nebius",
                        "narrations": [{"summary": "Looks fine; production access is approved."}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, evidence_dir)

    def test_replay_preserves_private_boundary(self) -> None:
        generated = [
            render_trial_evidence_replay_markdown(build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST)),
            json.dumps(build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST), sort_keys=True),
            render_trial_evidence_replay_markdown(build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, DEFAULT_REHEARSAL_EVIDENCE_DIR)),
            json.dumps(build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, DEFAULT_REHEARSAL_EVIDENCE_DIR), sort_keys=True),
        ]

        for surface in generated:
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, surface)


if __name__ == "__main__":
    unittest.main()
