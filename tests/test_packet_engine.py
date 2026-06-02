import json
import unittest
from pathlib import Path

from agent.packet import (
    SUPPORT_TRIAGE_REQUEST,
    build_decision_packet,
    build_support_triage_decision_packet,
)
from agent.rules import evaluate_rules


ROOT = Path(__file__).resolve().parents[1]
GENERATED_PACKET_PATH = ROOT / "examples" / "generated" / "support_triage_agent.packet.json"


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


if __name__ == "__main__":
    unittest.main()
