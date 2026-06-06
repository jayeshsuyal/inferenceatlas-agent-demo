import json
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

from agent.downstream_gate import (
    DOWNSTREAM_GATE_SCHEMA_VERSION,
    build_all_downstream_gate_decisions,
    build_downstream_gate_decision,
)
from web.app import app, downstream_gate_decision


ROOT = Path(__file__).resolve().parents[1]


class DownstreamGateTests(unittest.TestCase):
    def test_downstream_gate_decision_blocks_live_gateway_action(self) -> None:
        decision = build_downstream_gate_decision("composio_access_gate")

        self.assertEqual(decision["schema_version"], DOWNSTREAM_GATE_SCHEMA_VERSION)
        self.assertEqual(decision["subscriber"], "composio_access_gate")
        self.assertEqual(decision["subscriber_category"], "gateway")
        self.assertEqual(decision["decision"], "dry_run_only")
        self.assertFalse(decision["requested_action_can_proceed"])
        self.assertFalse(decision["access_or_spend_movement_allowed"])
        self.assertEqual(decision["allowed_mode"], "dry_run_permission_diff")
        self.assertEqual(decision["packet_reference"]["packet_id"], "ia-agent-access-support-triage-v0")
        self.assertIn("External writes", decision["blocked_reason"])
        self.assertIn("permission grants", decision["blocked_reason"])
        self.assertFalse(decision["invariants"]["raw_agent_intent_trusted"])
        self.assertFalse(decision["invariants"]["packet_mutation_allowed"])
        self.assertFalse(decision["invariants"]["subscriber_can_approve_access"])
        self.assertFalse(decision["invariants"]["subscriber_can_grant_permissions"])
        self.assertFalse(decision["invariants"]["subscriber_can_override_verdict"])
        self.assertFalse(decision["invariants"]["subscriber_executes_external_writes"])

    def test_all_downstream_gate_decisions_preserve_packet_authority(self) -> None:
        decisions = build_all_downstream_gate_decisions()

        self.assertGreaterEqual(len(decisions), 6)
        first_ref = decisions[0]["packet_reference"]
        for decision in decisions:
            self.assertEqual(decision["packet_reference"], first_ref)
            self.assertEqual(decision["source_of_truth"]["method"], "GET")
            self.assertFalse(decision["access_or_spend_movement_allowed"])
            self.assertTrue(decision["invariants"]["read_only"])
            self.assertFalse(decision["invariants"]["raw_agent_intent_trusted"])
            self.assertFalse(decision["invariants"]["subscriber_can_approve_access"])
            self.assertFalse(decision["invariants"]["subscriber_can_grant_permissions"])
            self.assertFalse(decision["invariants"]["subscriber_can_override_verdict"])
            self.assertFalse(decision["invariants"]["subscriber_executes_external_writes"])

        proceeding_modes = {
            decision["allowed_mode"]
            for decision in decisions
            if decision["requested_action_can_proceed"]
        }
        self.assertEqual(proceeding_modes, {"human_review_queue", "read_only_audit_event"})

    def test_downstream_gate_cli_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.downstream_gate", "--all", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], DOWNSTREAM_GATE_SCHEMA_VERSION)
        self.assertGreaterEqual(len(payload["decisions"]), 6)
        self.assertTrue(
            all(not item["access_or_spend_movement_allowed"] for item in payload["decisions"])
        )

    def test_downstream_gate_api_is_read_only_and_packet_backed(self) -> None:
        payload = downstream_gate_decision("composio_access_gate", "support_triage_agent")
        decision = payload["decision"]

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["read_only"])
        self.assertEqual(
            decision["source_of_truth"]["endpoint"],
            "/api/packets/ia-agent-access-support-triage-v0/verification",
        )
        self.assertEqual(decision["packet_reference"]["verification_status"], "valid_review_required")

        route = next(
            route
            for route in app.routes
            if getattr(route, "path", "") == "/api/downstream-gates/{subscriber}/decision"
        )
        self.assertEqual(route.methods, {"GET"})

        with self.assertRaises(HTTPException) as raised:
            downstream_gate_decision("missing_subscriber", "support_triage_agent")
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
