"""Contract tests for the Portkey BYO Guardrail probe script."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "portkey_guardrail_probe.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("portkey_guardrail_probe", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _fake_guardrail_response() -> dict:
    return {
        "verdict": False,
        "data": {
            "schema_version": "portkey_byo_guardrail.v0",
            "delivery_mode": "live_guardrail_webhook",
            "elapsed_ms": 4,
            "fixture": "ai_spend_budget_overrun",
            "requested_mode": "model_request",
            "verdict_class": "finance_procurement_review_required",
            "ia_packet_reference": {
                "packet_id": "ia-spend-review-ai_spend_budget_overrun-v0",
                "revision_id": "rev_demo",
                "content_hash": "sha256:demo",
            },
            "guardrail_event": {
                "event_id": "portkey-guardrail-demo-12345678",
                "record_path": "state/portkey_guardrail_events/demo.json",
            },
            "safety": {
                "read_only": True,
                "packet_mutation_allowed": False,
                "portkey_policy_mutation_allowed": False,
                "portkey_api_call_made": False,
                "approves_access": False,
                "approves_spend": False,
                "executes_external_writes": False,
                "mutates_production": False,
                "raw_agent_intent_trusted": False,
            },
        },
    }


class PortkeyGuardrailProbeTests(unittest.TestCase):
    def test_probe_posts_portkey_shaped_payload_and_records_event(self) -> None:
        module = _load_module()
        captured: dict[str, object] = {}

        def fake_json_request(
            base_url: str,
            path: str,
            *,
            method: str = "GET",
            payload: dict | None = None,
            headers: dict | None = None,
            timeout: float,
        ) -> tuple[int, object, float]:
            if path == "/api/portkey/guardrail":
                captured["base_url"] = base_url
                captured["method"] = method
                captured["payload"] = payload
                captured["headers"] = headers
                return 200, _fake_guardrail_response(), 8.4
            if path == "/api/portkey/guardrail/events":
                return (
                    200,
                    {
                        "ok": True,
                        "read_only": True,
                        "events": [
                            {
                                "event_id": "portkey-guardrail-demo-12345678",
                                "verdict": False,
                                "read_only": True,
                            }
                        ],
                    },
                    2.1,
                )
            raise AssertionError(path)

        with patch.dict(os.environ, {"PORTKEY_GUARDRAIL_TOKEN": "demo-token"}, clear=False):
            with patch.object(module, "_json_request", fake_json_request):
                summary = module.run_portkey_guardrail_probe("http://unit.test", timeout=1.0)

        payload = captured["payload"]
        headers = captured["headers"]
        assert isinstance(payload, dict)
        assert isinstance(headers, dict)
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(payload["eventType"], "beforeRequestHook")
        self.assertEqual(payload["requestType"], "chatComplete")
        self.assertEqual(payload["metadata"]["ia_fixture"], "ai_spend_budget_overrun")
        self.assertEqual(payload["metadata"]["ia_requested_mode"], "model_request")
        self.assertIn("Authorization", headers)
        self.assertNotIn("demo-token", str(summary))
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["probe"]["actual_verdict"], False)
        self.assertEqual(summary["guardrail_event"]["recorded"], True)
        self.assertEqual(summary["safety"]["portkey_api_call_made"], False)
        self.assertEqual(summary["safety"]["secrets_printed"], False)
        self.assertIn("packet-backed verdict only", module.render_summary(summary))

    def test_probe_requires_token_and_expected_verdict(self) -> None:
        module = _load_module()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(module.PortkeyProbeFailure, "PORTKEY_GUARDRAIL_TOKEN"):
                module.run_portkey_guardrail_probe("http://unit.test")

        def fake_json_request(
            base_url: str,
            path: str,
            *,
            method: str = "GET",
            payload: dict | None = None,
            headers: dict | None = None,
            timeout: float,
        ) -> tuple[int, object, float]:
            if path == "/api/portkey/guardrail":
                return 200, _fake_guardrail_response(), 1.0
            if path == "/api/portkey/guardrail/events":
                return 200, {"read_only": True, "events": []}, 1.0
            raise AssertionError(path)

        with patch.dict(os.environ, {"PORTKEY_GUARDRAIL_TOKEN": "demo-token"}, clear=False):
            with patch.object(module, "_json_request", fake_json_request):
                with self.assertRaisesRegex(module.PortkeyProbeFailure, "verdict"):
                    module.run_portkey_guardrail_probe("http://unit.test", expect_verdict=True)

    def test_script_is_executable_documented_and_secret_safe(self) -> None:
        script = SCRIPT_PATH.read_text(encoding="utf-8")
        command_reference = (ROOT / "docs" / "COMMAND_REFERENCE.md").read_text(encoding="utf-8")

        self.assertTrue(SCRIPT_PATH.is_file())
        self.assertTrue(os.access(SCRIPT_PATH, os.X_OK))
        self.assertIn("Portkey BYO Guardrails", script)
        self.assertIn("beforeRequestHook", script)
        self.assertIn("Authorization", script)
        self.assertIn("secrets_printed", script)
        self.assertIn("Optional Portkey BYO Guardrail Probe", command_reference)
        self.assertIn("PORTKEY_GUARDRAIL_TOKEN", command_reference)
        self.assertIn("scripts/portkey_guardrail_probe.py", command_reference)
        for forbidden_prefix in ("sk" + "-proj-", "tvly" + "-", "GOC" + "SPX-", "ak" + "_"):
            self.assertNotIn(forbidden_prefix, script)

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--base-url", result.stdout)
        self.assertIn("--fixture", result.stdout)
        self.assertIn("--requested-mode", result.stdout)
        self.assertIn("--expect-verdict", result.stdout)


if __name__ == "__main__":
    unittest.main()
