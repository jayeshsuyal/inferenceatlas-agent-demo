import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.sponsor_proof_trace import (
    ALLOWED_VERBS_PER_SPONSOR,
    SPONSOR_ORDER,
    SPONSOR_PROOF_TRACE_SCHEMA_VERSION,
    build_sponsor_proof_trace,
    render_sponsor_proof_trace_markdown,
    write_sponsor_proof_trace_artifacts,
)
from agent.trial import DEFAULT_TRIAL_REQUEST
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class _FakeTavilyClient:
    def search(self, **kwargs):
        return {
            "query": kwargs["query"],
            "results": [
                {
                    "title": "Evidence source",
                    "url": "https://example.com/evidence",
                    "content": "Reviewer-safe evidence candidate.",
                    "score": 0.9,
                }
            ],
        }


class SponsorProofTraceTests(unittest.TestCase):
    def _run_trace(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.sponsor_proof_trace", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_trace_shape_carries_access_and_spend_lanes(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(trace["schema_version"], SPONSOR_PROOF_TRACE_SCHEMA_VERSION)
        self.assertEqual(trace["lane"], "both")
        self.assertEqual(trace["packet_id"], "ia-agent-access-support-triage-v0")
        self.assertTrue(trace["trace_id"].startswith("ia-sponsor-proof-trace-support_triage_trial-"))
        self.assertIsNotNone(trace["access_review_evidence"])
        self.assertIsNotNone(trace["spend_review_evidence"])
        self.assertEqual(trace["access_review_evidence"]["packet_id"], "ia-agent-access-support-triage-v0")
        self.assertEqual(
            trace["spend_review_evidence"]["packet_id"],
            "ia-spend-review-ai_spend_budget_overrun-v0",
        )
        self.assertIn("source_artifacts", trace)
        self.assertEqual(trace["source_artifacts"]["request"], "examples/requests/support_triage_trial.yml")

    def test_access_only_lane_keeps_spend_block_optional(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST, lane="access_review")

        self.assertEqual(trace["lane"], "access_review")
        self.assertIsNotNone(trace["access_review_evidence"])
        self.assertIsNone(trace["spend_review_evidence"])

    def test_sponsor_order_locked(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(tuple(step["sponsor"] for step in trace["sponsor_steps"]), SPONSOR_ORDER)
        self.assertEqual(
            tuple(step["step_verb"] for step in trace["sponsor_steps"]),
            tuple(ALLOWED_VERBS_PER_SPONSOR[sponsor] for sponsor in SPONSOR_ORDER),
        )

    def test_decision_lock_unchanged(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(trace["decision_lock_before"], trace["decision_lock_after"])
        lock = trace["decision_lock_after"]
        self.assertFalse(lock["production_access"])
        self.assertFalse(lock["permission_grants"])
        self.assertFalse(lock["external_writes"])
        self.assertFalse(lock["approval_granted"])
        self.assertFalse(lock["spend_approved"])
        self.assertFalse(lock["provider_winner_selected"])
        self.assertFalse(lock["savings_guaranteed"])
        self.assertFalse(lock["can_sponsor_change_decision"])

    def test_no_sponsor_approves_or_writes(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)

        for step in trace["sponsor_steps"]:
            self.assertEqual(step["step_verb"], ALLOWED_VERBS_PER_SPONSOR[step["sponsor"]])
            self.assertFalse(step["used_live_key"])
            self.assertTrue(step["fallback_used"])
            self.assertFalse(step["would_execute"])
            self.assertFalse(step["can_approve_access"])
            self.assertFalse(step["can_grant_permissions"])
            self.assertFalse(step["can_mutate_external_state"])
            self.assertTrue(step["human_review_required"])

        safety = trace["safety_boundary"]
        self.assertFalse(safety["approves_access"])
        self.assertFalse(safety["grants_permissions"])
        self.assertFalse(safety["executes_external_writes"])
        self.assertFalse(safety["mutates_production"])
        self.assertFalse(safety["approves_spend"])
        self.assertFalse(safety["selects_provider"])
        self.assertFalse(safety["guarantees_savings"])
        self.assertTrue(safety["requires_human_review"])

    def test_nebius_step_summary_stays_packet_grounded_and_non_approving(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)
        nebius_step = next(step for step in trace["sponsor_steps"] if step["sponsor"] == "nebius")
        summary = nebius_step["output_summary"]
        lowered = summary.lower()

        self.assertIn("IA does not approve this request.", summary)
        self.assertIn("Human review is required before any access, spend, or production movement.", summary)
        self.assertIn("Verdict and safety state unchanged.", summary)
        for forbidden in ("approved", "looks fine", "should be ok", "should be okay"):
            self.assertNotIn(forbidden, lowered)

    def test_markdown_is_public_safe_and_skim_ready(self) -> None:
        markdown = render_sponsor_proof_trace_markdown(build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST))

        for expected in [
            "# Sponsor Proof Trace",
            "Private engine, public proof.",
            "Sponsor tools collect proof in locked order.",
            "decision lock unchanged: True",
            "| 1 | tavily | searched | False | True | False | False |",
            "| 2 | composio | planned | False | True | False | False |",
            "| 3 | openclaw | traced | False | True | False | False |",
            "| 4 | nebius | narrated | False | True | False | False |",
            "## Access Evidence",
            "## Spend Evidence",
            "approves spend: False",
        ]:
            self.assertIn(expected, markdown)

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, markdown, msg=f"{forbidden} leaked in sponsor proof trace markdown")

    def test_write_sponsor_proof_trace_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_sponsor_proof_trace_artifacts(DEFAULT_TRIAL_REQUEST, Path(temp_dir))

            self.assertEqual(
                {path.name for path in written},
                {
                    "support_triage_trial.sponsor_proof_trace.md",
                    "support_triage_trial.sponsor_proof_trace.json",
                },
            )
            payload = json.loads(
                (Path(temp_dir) / "support_triage_trial.sponsor_proof_trace.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["schema_version"], SPONSOR_PROOF_TRACE_SCHEMA_VERSION)
            self.assertEqual(payload["decision_lock_before"], payload["decision_lock_after"])

    def test_trace_cli_outputs_paths_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path_result = self._run_trace("examples/requests/support_triage_trial.yml", "--output-dir", temp_dir)
            self.assertEqual(path_result.returncode, 0, msg=path_result.stderr)
            self.assertIn("support_triage_trial.sponsor_proof_trace.md", path_result.stdout)

        markdown_result = self._run_trace("examples/requests/support_triage_trial.yml", "--no-write")
        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Sponsor Proof Trace", markdown_result.stdout)

        json_result = self._run_trace("examples/requests/support_triage_trial.yml", "--no-write", "--json")
        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["schema_version"], SPONSOR_PROOF_TRACE_SCHEMA_VERSION)
        self.assertFalse(payload["safety_boundary"]["approves_access"])

    def test_live_tavily_trace_collects_sources_without_moving_decision_lock(self) -> None:
        with patch("agent.tavily_live_evidence.TAVILY_API_KEY", "unit-test-key"):
            trace = build_sponsor_proof_trace(
                DEFAULT_TRIAL_REQUEST,
                live_tavily=True,
                tavily_client_factory=lambda _key: _FakeTavilyClient(),
            )

        self.assertEqual(trace["decision_lock_before"], trace["decision_lock_after"])
        self.assertIn("live_proof", trace)
        tavily_proof = trace["live_proof"]["tavily"]
        self.assertEqual(tavily_proof["status"], "live_evidence_candidates_fetched")
        self.assertTrue(tavily_proof["live_call_attempted"])
        self.assertTrue(tavily_proof["used_live_key"])
        self.assertFalse(tavily_proof["fallback_used"])
        self.assertTrue(tavily_proof["human_review_required"])
        self.assertFalse(tavily_proof["can_approve_access"])
        self.assertFalse(tavily_proof["can_grant_permissions"])
        self.assertFalse(tavily_proof["can_mutate_external_state"])
        self.assertTrue(all(item["source_urls"] for item in tavily_proof["evidence_candidates"]))
        self.assertTrue(all(item["can_reduce_proof_debt"] is False for item in tavily_proof["evidence_candidates"]))

        steps = {step["sponsor"]: step for step in trace["sponsor_steps"]}
        self.assertTrue(steps["tavily"]["used_live_key"])
        self.assertFalse(steps["tavily"]["fallback_used"])
        self.assertFalse(steps["tavily"]["would_execute"])
        self.assertFalse(steps["tavily"]["can_approve_access"])
        self.assertTrue(steps["composio"]["fallback_used"])
        self.assertTrue(steps["openclaw"]["fallback_used"])
        self.assertTrue(steps["nebius"]["fallback_used"])

        safety = trace["safety_boundary"]
        self.assertFalse(safety["approves_access"])
        self.assertFalse(safety["grants_permissions"])
        self.assertFalse(safety["executes_external_writes"])
        self.assertFalse(safety["mutates_production"])
        self.assertFalse(safety["approves_spend"])
        self.assertTrue(safety["requires_human_review"])

        markdown = render_sponsor_proof_trace_markdown(trace)
        self.assertIn("## Live Proof Collection", markdown)
        self.assertIn("tavily", markdown)
        self.assertIn("human review required: True", markdown)

    def test_composio_dry_run_trace_builds_permission_diff_without_execution(self) -> None:
        trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST, composio_dry_run=True)

        self.assertEqual(trace["decision_lock_before"], trace["decision_lock_after"])
        self.assertIn("dry_run_proof", trace)
        composio_proof = trace["dry_run_proof"]["composio"]
        self.assertEqual(composio_proof["status"], "dry_run_permission_diff_built")
        self.assertTrue(composio_proof["dry_run_requested"])
        self.assertTrue(composio_proof["dry_run_enforced"])
        self.assertFalse(composio_proof["api_call_made"])
        self.assertFalse(composio_proof["composio_execute_allowed"])
        self.assertFalse(composio_proof["used_live_key"])
        self.assertTrue(composio_proof["fallback_used"])
        self.assertTrue(composio_proof["human_review_required"])
        self.assertFalse(composio_proof["can_approve_access"])
        self.assertFalse(composio_proof["can_grant_permissions"])
        self.assertFalse(composio_proof["can_mutate_external_state"])
        self.assertEqual(composio_proof["permission_diff_summary"]["tool_count"], 3)
        self.assertEqual(composio_proof["permission_diff_summary"]["blocked_write_count"], 9)
        self.assertEqual(composio_proof["permission_diff_summary"]["required_proof_count"], 9)
        self.assertTrue(all(item["api_call_made"] is False for item in composio_proof["permission_diffs"]))
        self.assertTrue(all(item["would_execute"] is False for item in composio_proof["permission_diffs"]))

        steps = {step["sponsor"]: step for step in trace["sponsor_steps"]}
        self.assertFalse(steps["composio"]["used_live_key"])
        self.assertTrue(steps["composio"]["fallback_used"])
        self.assertFalse(steps["composio"]["would_execute"])
        self.assertFalse(steps["composio"]["can_approve_access"])
        self.assertFalse(steps["composio"]["can_grant_permissions"])
        self.assertFalse(steps["composio"]["can_mutate_external_state"])

        safety = trace["safety_boundary"]
        self.assertFalse(safety["approves_access"])
        self.assertFalse(safety["grants_permissions"])
        self.assertFalse(safety["executes_external_writes"])
        self.assertFalse(safety["mutates_production"])
        self.assertTrue(safety["requires_human_review"])

        markdown = render_sponsor_proof_trace_markdown(trace)
        self.assertIn("## Dry-Run Proof Collection", markdown)
        self.assertIn("composio", markdown)
        self.assertIn("api call made: False", markdown)
        self.assertIn("execute allowed: False", markdown)


if __name__ == "__main__":
    unittest.main()
