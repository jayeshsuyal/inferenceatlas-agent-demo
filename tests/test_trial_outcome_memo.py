import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.trial import DEFAULT_TRIAL_REQUEST
from agent.trial_outcome_memo import (
    TRIAL_OUTCOME_MEMO_SCHEMA_VERSION,
    build_trial_outcome_memo,
    render_trial_outcome_memo_markdown,
    write_trial_outcome_memo_artifacts,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class TrialOutcomeMemoTests(unittest.TestCase):
    def _run_memo(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.trial_outcome_memo", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_trial_outcome_memo_turns_request_into_safe_meeting_decision(self) -> None:
        memo = build_trial_outcome_memo(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(memo["schema_version"], TRIAL_OUTCOME_MEMO_SCHEMA_VERSION)
        self.assertEqual(memo["request_path"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(memo["decision"]["code"], "scoped_validation_only")
        self.assertEqual(memo["decision"]["access_speed_lane"], "proof_routed_scoped_validation")
        self.assertFalse(memo["decision"]["production_access"])
        self.assertTrue(memo["decision"]["scoped_validation_review"])
        self.assertFalse(memo["decision"]["permission_grants"])
        self.assertFalse(memo["decision"]["external_writes"])
        self.assertGreater(len(memo["proof_debt_assignments"]), 0)
        self.assertGreater(len(memo["reviewer_routes"]), 0)
        self.assertIn("production access grant", memo["stays_blocked"])
        self.assertFalse(memo["safety_boundary"]["approves_access"])
        self.assertFalse(memo["safety_boundary"]["grants_permissions"])
        self.assertFalse(memo["safety_boundary"]["executes_external_writes"])
        self.assertFalse(memo["private_boundary"]["private_source_exposed"])

    def test_trial_outcome_memo_markdown_is_skim_ready(self) -> None:
        markdown = render_trial_outcome_memo_markdown(build_trial_outcome_memo(DEFAULT_TRIAL_REQUEST))

        for expected in [
            "# Design Partner Outcome Memo: support_triage_trial",
            "Private engine, public proof.",
            "scoped_validation_only",
            "proof_routed_scoped_validation",
            "production access: False",
            "permission grants: False",
            "GitHub repository allowlist",
            "Security/Legal",
            "examples/generated/support_triage_trial.packet.json",
        ]:
            self.assertIn(expected, markdown)

    def test_write_trial_outcome_memo_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_trial_outcome_memo_artifacts(DEFAULT_TRIAL_REQUEST, Path(temp_dir))
            names = {path.name for path in paths}

            self.assertEqual(
                names,
                {
                    "support_triage_trial.outcome_memo.md",
                    "support_triage_trial.outcome_memo.json",
                },
            )
            payload = json.loads((Path(temp_dir) / "support_triage_trial.outcome_memo.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["decision"]["code"], "scoped_validation_only")

    def test_trial_outcome_memo_cli_outputs_paths_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path_result = self._run_memo("examples/requests/support_triage_trial.yml", "--output-dir", temp_dir)
            self.assertEqual(path_result.returncode, 0, msg=path_result.stderr)
            self.assertIn("support_triage_trial.outcome_memo.md", path_result.stdout)

        markdown_result = self._run_memo("examples/requests/support_triage_trial.yml", "--no-write")
        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Design Partner Outcome Memo", markdown_result.stdout)

        json_result = self._run_memo("examples/requests/support_triage_trial.yml", "--no-write", "--json")
        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["decision"]["code"], "scoped_validation_only")
        self.assertFalse(payload["safety_boundary"]["approves_access"])

    def test_trial_outcome_memo_preserves_private_boundary(self) -> None:
        generated = [
            render_trial_outcome_memo_markdown(build_trial_outcome_memo(DEFAULT_TRIAL_REQUEST)),
            json.dumps(build_trial_outcome_memo(DEFAULT_TRIAL_REQUEST), sort_keys=True),
        ]

        for surface in generated:
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, surface)


if __name__ == "__main__":
    unittest.main()
