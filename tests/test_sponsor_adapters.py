import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.adapters import ADAPTER_NAMES, build_adapter_result, build_all_adapter_results


ROOT = Path(__file__).resolve().parents[1]


class SponsorAdapterTests(unittest.TestCase):
    def test_all_adapters_are_dry_run_and_non_approving(self) -> None:
        results = build_all_adapter_results("support_triage_agent")

        self.assertEqual(set(results), set(ADAPTER_NAMES))
        for result in results.values():
            self.assertFalse(result["requires_api_key"])
            self.assertFalse(result["live_mode_enabled"])
            self.assertFalse(result["would_execute"])
            self.assertFalse(result["can_approve_access"])
            self.assertFalse(result["can_grant_permissions"])
            self.assertFalse(result["can_mutate_external_state"])
            self.assertTrue(result["blocked_from_approving_access"])
            self.assertTrue(result["human_review_required"])
            self.assertTrue(result["proof_pack"]["human_review_required"])
            self.assertIn("approve access", result["proof_pack"]["cannot_do"])

    def test_composio_maps_tool_plans_to_dry_run_actions(self) -> None:
        result = build_adapter_result("composio", "support_triage_agent")

        self.assertEqual(result["status"], "dry_run_planned")
        self.assertTrue(result["action_plans"])
        self.assertTrue(all(plan["would_execute"] is False for plan in result["action_plans"]))
        self.assertTrue(all(plan["dry_run_invocation"]["would_execute"] is False for plan in result["action_plans"]))
        self.assertTrue(all(plan["allowed_for_validation"] for plan in result["action_plans"]))
        blocked_actions = {action for plan in result["action_plans"] for action in plan["blocked_actions"]}
        self.assertIn("ticket creation", blocked_actions)
        self.assertEqual(result["proof_pack"]["proof_type"], "permission_diff")

    def test_tavily_candidates_cannot_reduce_proof_debt_offline(self) -> None:
        result = build_adapter_result("tavily", "admin_code_fix_bot")

        self.assertEqual(result["status"], "evidence_candidates_planned")
        self.assertTrue(result["evidence_candidates"])
        self.assertTrue(all(candidate["source_urls"] == [] for candidate in result["evidence_candidates"]))
        self.assertTrue(all(candidate["can_reduce_proof_debt"] is False for candidate in result["evidence_candidates"]))
        self.assertTrue(all(candidate["human_review_required"] is True for candidate in result["evidence_candidates"]))
        self.assertTrue(all(candidate["cannot_grant_access"] is True for candidate in result["evidence_candidates"]))
        self.assertIn("policy_or_control_evidence", {candidate["evidence_type"] for candidate in result["evidence_candidates"]})
        self.assertEqual(result["proof_pack"]["proof_type"], "evidence_candidate_plan")

    def test_nebius_cannot_own_verdicts(self) -> None:
        result = build_adapter_result("nebius", "read_only_analytics_agent")

        self.assertIn("verdict", result["llm_must_not_edit"])
        self.assertIn("safety_state", result["llm_must_not_edit"])
        self.assertIn("verdict", result["reviewer_narration_contract"]["locked_fields"])
        self.assertTrue(result["reviewer_narration_contract"]["human_review_required"])
        self.assertEqual(result["proof_pack"]["proof_type"], "locked_field_narration")

    def test_openclaw_trace_contract_captures_policy_decisions(self) -> None:
        result = build_adapter_result("openclaw", "support_triage_agent")

        self.assertEqual(result["status"], "trace_contract_planned")
        self.assertTrue(result["trace_steps"])
        self.assertTrue(all(step["would_execute"] is False for step in result["trace_steps"]))
        self.assertTrue(all("policy_decision" in step for step in result["trace_steps"]))
        self.assertIn("blocked attempts", result["runtime_trace_contract"]["must_preserve"])
        self.assertEqual(result["proof_pack"]["proof_type"], "runtime_trace_plan")

    def test_adapters_cli_json_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.adapters", "--all", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload["results"]), set(ADAPTER_NAMES))
        self.assertFalse(payload["results"]["composio"]["would_execute"])
        self.assertEqual(payload["results"]["composio"]["proof_pack"]["proof_type"], "permission_diff")

    def test_adapters_cli_human_output_names_providers(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.adapters", "--all"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("composio", result.stdout)
        self.assertIn("proof=permission_diff", result.stdout)
        self.assertIn("would_execute=False", result.stdout)


if __name__ == "__main__":
    unittest.main()
