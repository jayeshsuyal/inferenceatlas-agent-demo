"""Contract tests for the max rehearsal stress gate."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "max_rehearsal_stress.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("max_rehearsal_stress", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _keyed_summary(run_id: str = "keyed-1") -> dict:
    return {
        "status": "passed",
        "health": {
            "llm_provider": "nebius",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
            "tavily": True,
            "composio": True,
            "composio_dry_run": True,
        },
        "run": {
            "run_id": run_id,
            "mode": "live_read_only_evidence",
            "packet_id": "ia-agent-access-support-triage-v0",
            "decision_lock_unchanged": True,
            "read_only": True,
            "live_calls_made": True,
            "executes_external_writes": False,
        },
        "tavily": {
            "status": "live_evidence_candidates_fetched",
            "live_call_count": 5,
            "source_url_count": 10,
            "fallback_used": False,
        },
        "nebius": {
            "status": "live_reviewer_narration_built",
            "live_call_count": 1,
            "fallback_used": False,
            "required_anchors_present": True,
            "forbidden_phrases_present": [],
        },
        "composio": {
            "status": "dry_run_permission_diff_built",
            "api_call_made": False,
            "execute_allowed": False,
        },
        "portkey": {
            "mode": "dry-run",
            "api_call_made": False,
            "guardrail_verdict": False,
            "usage_credit_limit": 0,
        },
        "ledger": {
            "recorded": True,
            "live_calls_made": True,
            "executes_external_writes": False,
            "decision_lock_unchanged": True,
        },
    }


def _fallback_payload(run_id: str = "fallback-1") -> dict:
    return {
        "ok": True,
        "read_only": True,
        "run": {
            "run_id": run_id,
            "status": "completed",
            "collector_steps": [
                {"sponsor": "tavily"},
                {"sponsor": "composio"},
                {"sponsor": "openclaw"},
                {"sponsor": "nebius"},
            ],
            "invariants": {
                "decision_lock_unchanged": True,
                "portkey_api_call_made": False,
            },
            "safety_boundary": {
                "read_only": True,
                "live_calls_made": False,
                "approves_access": False,
                "grants_permissions": False,
                "executes_external_writes": False,
                "mutates_production": False,
                "approves_spend": False,
                "selects_provider": False,
                "guarantees_savings": False,
            },
        },
        "ledger_record": {
            "run_id": run_id,
            "safety_lock": {
                "read_only": True,
                "live_calls_made": False,
                "executes_external_writes": False,
                "decision_lock_unchanged": True,
            },
        },
    }


class MaxRehearsalStressTests(unittest.TestCase):
    def test_secret_counter_catches_sponsor_key_shapes(self) -> None:
        module = _load_module()
        text = " ".join(
            (
                "sk" + "-proj-" + "abc123abc123",
                "tvly" + "-dev-" + "abc123abc123",
                "ak" + "_" + "abc123abc123",
                "GOC" + "SPX-" + "abc123abc123",
            )
        )
        self.assertGreaterEqual(module._secret_string_count(text), 4)

    def test_four_zero_pass_conditions_are_enforced(self) -> None:
        module = _load_module()
        report = {
            "pass_condition_counters": {
                "live_writes_attempted": 0,
                "approvals_emitted": 0,
                "packet_mutations_post_seal": 0,
                "secret_strings_in_output": 0,
            },
            "keyed_loop": {"completed": 1, "requested": 1},
            "fallback_loop": {"completed": 1, "requested": 1},
            "adversarial_inputs": [{"passed": True}],
            "ledger_contamination": {
                "no_external_writes": True,
                "no_live_call_with_external_write": True,
            },
        }
        module._assert_pass_conditions(report)
        report["pass_condition_counters"]["approvals_emitted"] = 1
        with self.assertRaisesRegex(module.StressFailure, "approvals_emitted"):
            module._assert_pass_conditions(report)

    def test_run_max_stress_builds_safe_report_from_mixed_runs(self) -> None:
        module = _load_module()
        keyed = [_keyed_summary("keyed-1")]
        fallback = [_fallback_payload("fallback-1")]
        ledger_payload = {
            "ok": True,
            "read_only": True,
            "ledger": {
                "read_only": True,
                "record_count": 2,
                "runs": [
                    {
                        "run_id": "keyed-1",
                        "safety_lock": {
                            "read_only": True,
                            "live_calls_made": True,
                            "executes_external_writes": False,
                            "decision_lock_unchanged": True,
                        },
                    },
                    fallback[0]["ledger_record"],
                ],
                "safety_summary": {
                    "no_external_writes": True,
                    "all_decision_locks_unchanged": True,
                },
            },
        }

        def fake_get(base_url: str, path: str, *, timeout: float) -> dict:
            if path == "/api/health":
                return {
                    "ok": True,
                    "llm_provider": "nebius",
                    "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
                    "tavily": True,
                    "composio": True,
                    "composio_dry_run": True,
                }
            if path == "/api/sponsor-proof-run-ledger":
                return ledger_payload
            raise AssertionError(path)

        with (
            patch.object(module, "_run_keyed_loop", return_value=keyed),
            patch.object(module, "_run_fallback_loop", return_value=fallback),
            patch.object(module, "_run_endpoint_pressure", return_value={"routes": {}}),
            patch.object(
                module,
                "_run_adversarial_inputs",
                return_value=[{"label": "bad", "status": 404, "expected_status": 404, "passed": True}],
            ),
            patch.object(module, "_json_get", fake_get),
        ):
            report = module.run_max_stress("http://127.0.0.1:8110", keyed_runs=1, fallback_runs=1)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["pass_condition_counters"]["live_writes_attempted"], 0)
        self.assertEqual(report["pass_condition_counters"]["approvals_emitted"], 0)
        self.assertEqual(report["pass_condition_counters"]["packet_mutations_post_seal"], 0)
        self.assertEqual(report["pass_condition_counters"]["secret_strings_in_output"], 0)
        self.assertEqual(report["keyed_loop"]["tavily_live_calls"], 5)
        self.assertEqual(report["ledger_contamination"]["no_live_call_with_external_write"], True)
        self.assertIn("Stress Test Run", module.render_markdown(report))

    def test_json_request_reports_socket_timeout_as_stress_failure(self) -> None:
        module = _load_module()

        with patch.object(module.urllib.request, "urlopen", side_effect=module.socket.timeout("timed out")):
            with self.assertRaisesRegex(module.StressFailure, r"GET /api/health failed"):
                module._json_request("http://unit.test", "/api/health", timeout=0.01)

    def test_script_is_executable_documented_and_helpful(self) -> None:
        script = SCRIPT_PATH.read_text(encoding="utf-8")
        command_reference = (ROOT / "docs" / "COMMAND_REFERENCE.md").read_text(encoding="utf-8")

        self.assertTrue(SCRIPT_PATH.is_file())
        self.assertTrue(os.access(SCRIPT_PATH, os.X_OK))
        self.assertIn("Bounded max rehearsal stress", script)
        self.assertIn("secret_strings_in_output", script)
        self.assertIn("live_writes_attempted", script)
        self.assertIn("no_live_call_with_external_write", script)
        self.assertIn("Optional Max Rehearsal Stress", command_reference)
        self.assertIn("scripts/max_rehearsal_stress.py", command_reference)

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--keyed-runs", result.stdout)
        self.assertIn("--concurrency", result.stdout)
        self.assertIn("--output-doc", result.stdout)


if __name__ == "__main__":
    unittest.main()
