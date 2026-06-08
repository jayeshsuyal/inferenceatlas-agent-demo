import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "demo_rehearsal.py"


class DemoRehearsalGateTests(unittest.TestCase):
    def test_demo_rehearsal_gate_passes_with_no_live_keys(self) -> None:
        env = os.environ.copy()
        for key in [
            "NEBIUS_API_KEY",
            "OPENAI_API_KEY",
            "TAVILY_API_KEY",
            "COMPOSIO_API_KEY",
            "GITHUB_OAUTH_CLIENT_SECRET",
            "GOOGLE_OAUTH_CLIENT_SECRET",
        ]:
            env[key] = ""
        env["COMPOSIO_DRY_RUN"] = "1"
        env["IA_DISABLE_DOTENV"] = "1"
        env["IA_LIVE_MODE"] = ""

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema_version"], "demo_rehearsal_gate.v0")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(
            report["cold_start_url"],
            "http://127.0.0.1:8080/packet?fixture=mcp_tool_blast_radius&autorun=1",
        )
        self.assertTrue(report["no_live_keys_required"])
        self.assertFalse(report["external_writes_enabled"])
        self.assertFalse(report["approval_granted"])
        self.assertTrue(report["recording_ready_when_rehearsed_twice"])

        prompts = report["checks"]["packet_coach_prompts"]
        self.assertEqual(
            [item["question"] for item in prompts],
            [
                "Can this move?",
                "What proof is missing?",
                "Who reviews this?",
                "Can Portkey allow this spend?",
            ],
        )
        self.assertEqual(prompts[-1]["subscriber"], "portkey_model_spend_gate")

        portkey = report["checks"]["portkey_dry_run"]
        self.assertEqual(portkey["mode"], "dry-run")
        self.assertFalse(portkey["api_call_made"])
        self.assertFalse(portkey["guardrail_verdict"])
        self.assertEqual(portkey["credit_limit"], 0)

        sponsor = report["checks"]["sponsor_proof_run"]
        self.assertEqual(sponsor["mode"], "offline_dry_run")
        self.assertEqual(sponsor["steps"], ["tavily", "composio", "openclaw", "nebius"])
        self.assertFalse(sponsor["live_calls_made"])
        self.assertEqual(
            sponsor["fallback_used"],
            {"tavily": True, "composio": True, "openclaw": True, "nebius": True},
        )

    def test_demo_rehearsal_gate_is_exposed_without_expanding_product_scope(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        recording_script = (ROOT / "docs" / "DEMO_RECORDING_SCRIPT.md").read_text(encoding="utf-8")
        command_reference = (ROOT / "docs" / "COMMAND_REFERENCE.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["demo_rehearsal_gate_command"], "python3 scripts/demo_rehearsal.py --json")
        self.assertEqual(manifest["primary_artifacts"]["demo_rehearsal_gate"], "scripts/demo_rehearsal.py")
        self.assertEqual(manifest["verification"]["demo_rehearsal_gate"], "python3 scripts/demo_rehearsal.py --json")
        self.assertIn("demo rehearsal gate", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("python3 scripts/demo_rehearsal.py --json", recording_script)
        self.assertIn("## Demo Rehearsal Gate", command_reference)

        combined_public_text = "\n".join([recording_script, command_reference, SCRIPT.read_text(encoding="utf-8")])
        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, combined_public_text, msg=f"{forbidden} leaked in rehearsal gate")


if __name__ == "__main__":
    unittest.main()
