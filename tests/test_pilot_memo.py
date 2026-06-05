import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.packet_authority import build_packet_authority_snapshot_for_scenario
from agent.pilot_memo import (
    PILOT_MEMO_SAFETY_ANCHOR,
    PILOT_MEMO_SCHEMA_VERSION,
    SPONSOR_ROLE_VERBS,
    build_pilot_memo,
    render_copy_review_brief,
    render_pilot_memo_markdown,
    write_pilot_memo_artifacts,
)
from agent.trial import DEFAULT_TRIAL_REQUEST, build_trial_bundle
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class PilotMemoTests(unittest.TestCase):
    def _run_memo(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.pilot_memo", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_pilot_memo_is_export_ready_and_non_approving(self) -> None:
        memo = build_pilot_memo(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(memo["schema_version"], PILOT_MEMO_SCHEMA_VERSION)
        self.assertRegex(memo["memo_id"], r"^ia-pilot-memo-support_triage_trial-[0-9a-f]{16}-public-v0$")
        self.assertEqual(memo["verdict_class"], "scoped_validation_only")
        self.assertEqual(memo["safety_anchor"], PILOT_MEMO_SAFETY_ANCHOR)
        self.assertEqual(memo["next_human_action"], "Run a scoped dry-run pilot review with named repositories, channels, and Jira project.")
        self.assertGreaterEqual(len(memo["blocked_claims"]), 1)
        self.assertGreaterEqual(len(memo["missing_proof"]), 1)
        self.assertGreaterEqual(len(memo["reviewer_routing"]), 1)
        self.assertFalse(memo["safety_boundary"]["approves_access"])
        self.assertFalse(memo["safety_boundary"]["grants_permissions"])
        self.assertFalse(memo["safety_boundary"]["executes_external_writes"])
        self.assertFalse(memo["safety_boundary"]["mutates_production"])
        self.assertTrue(memo["safety_boundary"]["requires_human_review"])
        self.assertFalse(memo["private_boundary"]["private_source_exposed"])

    def test_pilot_memo_references_the_trial_packet_hash(self) -> None:
        bundle = build_trial_bundle(DEFAULT_TRIAL_REQUEST)
        snapshot = build_packet_authority_snapshot_for_scenario(bundle["packet"], DEFAULT_TRIAL_REQUEST.stem)
        memo = build_pilot_memo(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(memo["packet_reference"]["packet_id"], snapshot["packet_id"])
        self.assertEqual(memo["packet_reference"]["revision_id"], snapshot["revision_id"])
        self.assertEqual(memo["packet_reference"]["content_hash"], snapshot["content_hash"])
        self.assertEqual(
            memo["packet_reference"]["packet_artifact"],
            "examples/generated/support_triage_trial.packet.json",
        )

    def test_sponsor_roles_are_proof_contributors_not_actors(self) -> None:
        memo = build_pilot_memo(DEFAULT_TRIAL_REQUEST)
        roles = {item["provider"]: (item["verb"], item["role"]) for item in memo["sponsor_contributions"]}

        self.assertEqual(roles, SPONSOR_ROLE_VERBS)
        for item in memo["sponsor_contributions"]:
            self.assertTrue(item["human_review_required"])
            self.assertFalse(item["can_change_decision"])
            for unsafe in ("applies", "runs", "executes", "dispatches", "triggers", "approves", "grants"):
                self.assertNotEqual(item["verb"], unsafe)

    def test_copy_review_brief_is_short_safe_and_clipboard_ready(self) -> None:
        brief = render_copy_review_brief(build_pilot_memo(DEFAULT_TRIAL_REQUEST))

        self.assertIn("# Copy Review Brief", brief)
        self.assertIn(PILOT_MEMO_SAFETY_ANCHOR, brief)
        self.assertIn("Sponsors contribute proof only", brief)
        self.assertIn("they do not approve, grant, execute, or mutate", brief)
        self.assertIn("sha256:", brief)
        self.assertLessEqual(len(brief.split()), 160)
        self.assertNotIn("..", brief)

    def test_pilot_memo_markdown_is_meeting_ready(self) -> None:
        markdown = render_pilot_memo_markdown(build_pilot_memo(DEFAULT_TRIAL_REQUEST))

        for expected in [
            "# Pilot Memo",
            "Private engine, public proof.",
            "## Packet Reference",
            "support_triage_trial.packet.json",
            "## Sponsor Contributions",
            "tavily",
            "composio",
            "nebius",
            "openclaw",
            "## Reviewer Routing",
            "## Safety Boundary",
            "approves access: False",
            PILOT_MEMO_SAFETY_ANCHOR,
        ]:
            self.assertIn(expected, markdown)

    def test_write_pilot_memo_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_pilot_memo_artifacts(DEFAULT_TRIAL_REQUEST, Path(temp_dir))
            names = {path.name for path in paths}

            self.assertEqual(
                names,
                {
                    "support_triage_trial.pilot_memo.json",
                    "support_triage_trial.pilot_memo.md",
                    "support_triage_trial.copy_review_brief.md",
                },
            )
            payload = json.loads((Path(temp_dir) / "support_triage_trial.pilot_memo.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], PILOT_MEMO_SCHEMA_VERSION)
            self.assertEqual(payload["safety_anchor"], PILOT_MEMO_SAFETY_ANCHOR)

    def test_pilot_memo_cli_outputs_paths_markdown_copy_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path_result = self._run_memo("examples/requests/support_triage_trial.yml", "--output-dir", temp_dir)
            self.assertEqual(path_result.returncode, 0, msg=path_result.stderr)
            self.assertIn("support_triage_trial.pilot_memo.json", path_result.stdout)
            self.assertIn("support_triage_trial.copy_review_brief.md", path_result.stdout)

        markdown_result = self._run_memo("examples/requests/support_triage_trial.yml", "--no-write")
        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Pilot Memo", markdown_result.stdout)

        copy_result = self._run_memo("examples/requests/support_triage_trial.yml", "--no-write", "--copy")
        self.assertEqual(copy_result.returncode, 0, msg=copy_result.stderr)
        self.assertIn("# Copy Review Brief", copy_result.stdout)

        json_result = self._run_memo("examples/requests/support_triage_trial.yml", "--no-write", "--json")
        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["schema_version"], PILOT_MEMO_SCHEMA_VERSION)
        self.assertFalse(payload["safety_boundary"]["approves_access"])

    def test_schema_file_locks_safety_anchor_and_export_contract(self) -> None:
        schema = json.loads((ROOT / "schemas" / "pilot_memo.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema_version"]["const"], PILOT_MEMO_SCHEMA_VERSION)
        self.assertEqual(schema["properties"]["safety_anchor"]["const"], PILOT_MEMO_SAFETY_ANCHOR)
        self.assertIn("copy_review_brief", schema["properties"]["export_variants"]["required"])
        self.assertIn("export_pilot_memo", schema["properties"]["export_variants"]["required"])

    def test_pilot_memo_preserves_private_boundary(self) -> None:
        generated = [
            render_copy_review_brief(build_pilot_memo(DEFAULT_TRIAL_REQUEST)),
            render_pilot_memo_markdown(build_pilot_memo(DEFAULT_TRIAL_REQUEST)),
            json.dumps(build_pilot_memo(DEFAULT_TRIAL_REQUEST), sort_keys=True),
            (ROOT / "schemas" / "pilot_memo.schema.json").read_text(encoding="utf-8"),
        ]

        for surface in generated:
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, surface)


if __name__ == "__main__":
    unittest.main()
