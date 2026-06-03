import json
import unittest
from pathlib import Path

from agent.packet import (
    ADMIN_CODE_FIX_REQUEST,
    READ_ONLY_ANALYTICS_REQUEST,
    SUPPORT_TRIAGE_REQUEST,
    build_decision_packet,
    build_support_triage_decision_packet,
)
from agent.rules import evaluate_rules


ROOT = Path(__file__).resolve().parents[1]
GENERATED_PACKET_PATH = ROOT / "examples" / "generated" / "support_triage_agent.packet.json"
GENERATED_ANALYTICS_PACKET_PATH = ROOT / "examples" / "generated" / "read_only_analytics_agent.packet.json"
GENERATED_ADMIN_PACKET_PATH = ROOT / "examples" / "generated" / "admin_code_fix_bot.packet.json"


class PacketEngineTests(unittest.TestCase):
    def test_engine_reproduces_support_triage_packet_byte_equal(self) -> None:
        packet = build_decision_packet(SUPPORT_TRIAGE_REQUEST)
        expected = json.loads(GENERATED_PACKET_PATH.read_text(encoding="utf-8"))

        self.assertEqual(packet, expected)

    def test_support_triage_wrapper_calls_rules_engine(self) -> None:
        self.assertEqual(
            build_support_triage_decision_packet(),
            build_decision_packet(SUPPORT_TRIAGE_REQUEST),
        )

    def test_rules_emit_traceable_rule_ids(self) -> None:
        effects = evaluate_rules(SUPPORT_TRIAGE_REQUEST)

        self.assertGreater(len(effects), 0)
        self.assertTrue(all(effect.rule_id for effect in effects))
        self.assertIn("approval_posture", {effect.target for effect in effects})
        self.assertIn("tool_access_plan", {effect.target for effect in effects})

    def test_scenarios_differ_in_load_bearing_fields(self) -> None:
        support = build_decision_packet(SUPPORT_TRIAGE_REQUEST)
        analytics = build_decision_packet(READ_ONLY_ANALYTICS_REQUEST)
        admin = build_decision_packet(ADMIN_CODE_FIX_REQUEST)

        self.assertEqual(analytics["approval_posture"]["write_access"], "not_requested")
        self.assertEqual(support["approval_posture"]["write_access"], "blocked_until_rollback_and_off_switch_proof")
        self.assertEqual(admin["approval_posture"]["write_access"], "blocked_due_to_admin_and_production_mutation")

        self.assertEqual(analytics["approval_posture"]["validation_review"], "allowed")
        self.assertEqual(support["approval_posture"]["validation_review"], "allowed")
        self.assertEqual(admin["approval_posture"]["validation_review"], "blocked_until_security_review")

        self.assertEqual({item["risk_level"] for item in analytics["requested_capability"]}, {"low"})
        self.assertIn("high", {item["risk_level"] for item in support["requested_capability"]})
        self.assertEqual({item["risk_level"] for item in admin["requested_capability"]}, {"critical"})

        analytics_owners = {item["owner"] for item in analytics["reviewer_owners"]}
        support_owners = {item["owner"] for item in support["reviewer_owners"]}
        admin_owners = {item["owner"] for item in admin["reviewer_owners"]}
        self.assertIn("Data/Analytics", analytics_owners)
        self.assertIn("Support Ops", support_owners)
        self.assertIn("Engineering Leadership", admin_owners)
        self.assertNotEqual(analytics_owners, support_owners)
        self.assertNotEqual(admin_owners, support_owners)

        analytics_claims = {item["claim"] for item in analytics["blocked_claims"]}
        admin_claims = {item["claim"] for item in admin["blocked_claims"]}
        self.assertIn("The agent may export rows or mutate dashboards.", analytics_claims)
        self.assertIn("Admin or production write access is approved.", admin_claims)

    def test_generated_scenario_artifacts_match_engine(self) -> None:
        expected = {
            GENERATED_ANALYTICS_PACKET_PATH: build_decision_packet(READ_ONLY_ANALYTICS_REQUEST),
            GENERATED_ADMIN_PACKET_PATH: build_decision_packet(ADMIN_CODE_FIX_REQUEST),
        }
        for path, packet in expected.items():
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), packet)


if __name__ == "__main__":
    unittest.main()
