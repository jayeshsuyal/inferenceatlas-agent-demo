import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.gate import GATE_SCHEMA_VERSION, evaluate_all, evaluate_gate


ROOT = Path(__file__).resolve().parents[1]


class PolicyGateTests(unittest.TestCase):
    def test_admin_code_fix_bot_is_blocked_by_policy(self) -> None:
        result = evaluate_gate("admin_code_fix_bot")

        self.assertEqual(result["schema_version"], GATE_SCHEMA_VERSION)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("Critical/admin/prod-write access", result["reason"])
        self.assertIn("deny_critical_risk_validation", {rule["rule_id"] for rule in result["triggered_rules"]})
        self.assertFalse(result["safety_state"]["production_access"])

    def test_read_only_and_support_can_move_only_with_gates(self) -> None:
        results = evaluate_all()

        self.assertEqual(results["read_only_analytics_agent"]["decision"], "VALIDATION_ALLOWED_WITH_GATES")
        self.assertEqual(results["support_triage_agent"]["decision"], "VALIDATION_ALLOWED_WITH_GATES")
        for scenario_name in ["read_only_analytics_agent", "support_triage_agent"]:
            self.assertFalse(results[scenario_name]["safety_state"]["production_access"])
            self.assertFalse(results[scenario_name]["safety_state"]["external_writes"])
            self.assertTrue(results[scenario_name]["safety_state"]["composio_dry_run"])

    def test_policy_file_is_machine_readable(self) -> None:
        policy = json.loads((ROOT / "policy" / "agent_access.yml").read_text(encoding="utf-8"))

        self.assertEqual(policy["policy_version"], "agent_access_public_policy.v0")
        self.assertIn("deny_production_access", {rule["id"] for rule in policy["rules"]})

    def test_gate_cli_renders_admin_block(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.gate", "--scenario", "admin_code_fix_bot"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("decision: BLOCKED", result.stdout)
        self.assertIn("deny_critical_risk_validation", result.stdout)

    def test_gate_cli_json_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.gate", "--all", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["results"]["admin_code_fix_bot"]["decision"], "BLOCKED")
        self.assertEqual(payload["results"]["support_triage_agent"]["decision"], "VALIDATION_ALLOWED_WITH_GATES")


if __name__ == "__main__":
    unittest.main()
