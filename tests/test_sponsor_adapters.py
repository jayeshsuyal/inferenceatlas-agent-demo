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

    def test_composio_maps_tool_plans_to_dry_run_actions(self) -> None:
        result = build_adapter_result("composio", "support_triage_agent")

        self.assertEqual(result["status"], "dry_run_planned")
        self.assertTrue(result["action_plans"])
        self.assertTrue(all(plan["would_execute"] is False for plan in result["action_plans"]))
        blocked_actions = {action for plan in result["action_plans"] for action in plan["blocked_actions"]}
        self.assertIn("ticket creation", blocked_actions)

    def test_tavily_candidates_cannot_reduce_proof_debt_offline(self) -> None:
        result = build_adapter_result("tavily", "admin_code_fix_bot")

        self.assertEqual(result["status"], "evidence_candidates_planned")
        self.assertTrue(result["evidence_candidates"])
        self.assertTrue(all(candidate["source_urls"] == [] for candidate in result["evidence_candidates"]))
        self.assertTrue(all(candidate["can_reduce_proof_debt"] is False for candidate in result["evidence_candidates"]))

    def test_nebius_cannot_own_verdicts(self) -> None:
        result = build_adapter_result("nebius", "read_only_analytics_agent")

        self.assertIn("verdict", result["llm_must_not_edit"])
        self.assertIn("safety_state", result["llm_must_not_edit"])

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
        self.assertIn("would_execute=False", result.stdout)


if __name__ == "__main__":
    unittest.main()
