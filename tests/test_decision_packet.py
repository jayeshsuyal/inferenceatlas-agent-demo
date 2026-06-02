import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from agent.packet import build_support_triage_decision_packet, build_support_triage_trace
from agent.renderers import render_packet_markdown


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "decision_packet.schema.json"
GENERATED_PACKET_PATH = ROOT / "examples" / "generated" / "support_triage_agent.packet.json"


class DecisionPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = build_support_triage_decision_packet()
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_packet_contains_required_schema_fields(self) -> None:
        for field in self.schema["required"]:
            self.assertIn(field, self.packet)

    def test_packet_safety_defaults_block_external_action(self) -> None:
        safety = self.packet["safety_state"]
        self.assertFalse(safety["approval_granted"])
        self.assertFalse(safety["external_writes_enabled"])
        self.assertFalse(safety["packet_state_mutation"])
        self.assertTrue(safety["composio_dry_run"])
        self.assertTrue(safety["requires_human_approval"])

    def test_packet_keeps_blocked_claims_visible(self) -> None:
        blocked_claims = self.packet["blocked_claims"]
        self.assertGreaterEqual(len(blocked_claims), 3)
        joined = " ".join(item["claim"] for item in blocked_claims)
        self.assertIn("Production tool access is approved.", joined)
        self.assertIn("compliance-ready", joined)

    def test_trace_records_review_steps(self) -> None:
        trace = build_support_triage_trace()
        steps = [item["step"] for item in trace]
        self.assertEqual(steps[0], "intake")
        self.assertIn("safety_gate", steps)
        self.assertEqual(steps[-1], "next_validation")

    def test_markdown_renderer_includes_judge_sections(self) -> None:
        rendered = render_packet_markdown(self.packet)
        for heading in [
            "## Verdict",
            "## Requested Capability",
            "## Tool Scope",
            "## Blocked Claims",
            "## Missing Proof",
            "## Reviewer Owners",
            "## Safety State",
        ]:
            self.assertIn(heading, rendered)

    def test_generated_packet_artifact_matches_required_shape(self) -> None:
        generated = json.loads(GENERATED_PACKET_PATH.read_text(encoding="utf-8"))
        for field in self.schema["required"]:
            self.assertIn(field, generated)
        self.assertEqual(generated["schema_version"], "decision_packet.v0")
        self.assertFalse(generated["safety_state"]["approval_granted"])
        self.assertTrue(generated["safety_state"]["composio_dry_run"])

    def test_demo_runs_without_keys(self) -> None:
        env = os.environ.copy()
        for key in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY", "IA_LIVE_MODE"):
            env.pop(key, None)

        result = subprocess.run(
            [sys.executable, "-m", "agent.demo"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Offline DecisionPacket", result.stdout)
        self.assertIn("Approval granted: False", result.stdout)
        self.assertIn("Generated artifacts:", result.stdout)


if __name__ == "__main__":
    unittest.main()
