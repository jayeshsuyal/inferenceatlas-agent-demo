"""Contract tests for the keyed sponsor rehearsal gate."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "keyed_sponsor_rehearsal.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("keyed_sponsor_rehearsal", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _fake_run() -> dict:
    return {
        "run_id": "ia-sponsor-proof-run-support_triage_trial-keyed-public-v0",
        "mode": "live_read_only_evidence",
        "status": "completed",
        "packet_reference": {"packet_id": "ia-agent-access-support-triage-v0"},
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
            "live_calls_made": True,
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_production": False,
            "approves_spend": False,
            "selects_provider": False,
            "guarantees_savings": False,
            "requires_human_review": True,
        },
        "live_sponsor_proof": {
            "tavily": {
                "status": "live_evidence_candidates_fetched",
                "live_call_attempted": True,
                "live_call_count": 5,
                "used_live_key": True,
                "fallback_used": False,
                "evidence_candidates": [
                    {"source_urls": ["https://example.com/a", "https://example.com/b"]},
                    {"source_urls": ["https://example.com/c"]},
                ],
            },
            "nebius": {
                "status": "live_reviewer_narration_built",
                "live_call_attempted": True,
                "live_call_count": 1,
                "used_live_key": True,
                "fallback_used": False,
                "required_anchors_present": True,
                "forbidden_phrases_present": [],
                "structured_narration": {
                    "reviewer_summary": "Packet verdict keeps production access blocked for reviewer proof.",
                    "next_human_action": "Security/Legal owner must review the named proof debt.",
                },
            }
        },
        "dry_run_sponsor_proof": {
            "composio": {
                "status": "dry_run_permission_diff_built",
                "api_call_made": False,
                "composio_execute_allowed": False,
                "human_review_required": True,
                "permission_diff_summary": {
                    "tool_count": 3,
                    "blocked_write_count": 9,
                    "api_call_made": False,
                },
            }
        },
    }


def _fake_record(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "record_path": "state/sponsor_proof_runs/keyed.json",
        "safety_lock": {
            "read_only": True,
            "live_calls_made": True,
            "executes_external_writes": False,
            "decision_lock_unchanged": True,
        },
    }


class KeyedSponsorRehearsalTests(unittest.TestCase):
    def test_keyed_rehearsal_succeeds_with_live_read_and_no_writes(self) -> None:
        module = _load_module()
        run = _fake_run()
        record = _fake_record(run["run_id"])

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
            if path.startswith("/api/packets/ai_spend_budget_overrun/downstream/portkey"):
                return {
                    "ok": True,
                    "read_only": True,
                    "portkey": {
                        "mode": "dry-run",
                        "api_call_made": False,
                        "portkey_guardrail_response": {"verdict": False},
                        "usage_policy_plan": {"request_body": {"credit_limit": 0}},
                    },
                }
            if path.startswith("/api/sponsor-proof-runs/"):
                return {"ok": True, "read_only": True, "run": run, "ledger_record": record}
            if path == "/api/sponsor-proof-run-ledger":
                return {
                    "ok": True,
                    "read_only": True,
                    "ledger": {
                        "read_only": True,
                        "record_count": 1,
                        "runs": [record],
                        "safety_summary": {
                            "no_external_writes": True,
                            "all_decision_locks_unchanged": True,
                        },
                    },
                }
            raise AssertionError(f"unexpected GET path: {path}")

        def fake_post(base_url: str, path: str, payload: dict, *, timeout: float) -> dict:
            self.assertEqual(path, "/api/sponsor-proof-runs")
            self.assertIs(payload["live_tavily"], True)
            self.assertIs(payload["live_nebius"], True)
            self.assertIs(payload["composio_dry_run"], True)
            return {"ok": True, "read_only": True, "run": run, "ledger_record": record}

        with patch.object(module, "_json_get", fake_get), patch.object(module, "_json_post", fake_post):
            summary = module.run_keyed_rehearsal("http://unit.test", timeout=1.0)

        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["health"]["llm_provider"], "nebius")
        self.assertEqual(summary["tavily"]["source_url_count"], 3)
        self.assertEqual(summary["nebius"]["status"], "live_reviewer_narration_built")
        self.assertIs(summary["nebius"]["fallback_used"], False)
        self.assertIs(summary["composio"]["api_call_made"], False)
        self.assertIs(summary["portkey"]["api_call_made"], False)
        self.assertIs(summary["run"]["decision_lock_unchanged"], True)
        self.assertIs(summary["run"]["executes_external_writes"], False)
        self.assertIs(summary["private_boundary"]["secrets_printed"], False)
        self.assertIn("No sponsor approved", module.render_summary(summary))

    def test_keyed_rehearsal_fails_closed_when_tavily_key_missing(self) -> None:
        module = _load_module()

        with self.assertRaisesRegex(module.RehearsalFailure, "Tavily key must be configured"):
            module._assert_health(
                {
                    "ok": True,
                    "llm_provider": "nebius",
                    "llm_model": "meta-llama/Llama-3.3-70B-Instruct",
                    "tavily": False,
                    "composio": True,
                    "composio_dry_run": True,
                }
            )

    def test_keyed_rehearsal_script_is_executable_and_secret_safe(self) -> None:
        script = SCRIPT_PATH.read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        command_reference = (ROOT / "docs" / "COMMAND_REFERENCE.md").read_text(encoding="utf-8")

        self.assertTrue(SCRIPT_PATH.is_file())
        self.assertTrue(os.access(SCRIPT_PATH, os.X_OK))
        self.assertIn("Keyed sponsor rehearsal", script)
        self.assertIn("/api/health", script)
        self.assertIn("/api/sponsor-proof-runs", script)
        self.assertIn("/api/sponsor-proof-run-ledger", script)
        self.assertIn("live_tavily", script)
        self.assertIn("live_nebius", script)
        self.assertIn("composio_dry_run", script)
        self.assertIn("secrets_printed", script)
        self.assertIn("api_call_made", script)
        self.assertEqual(
            manifest["keyed_sponsor_rehearsal_command"],
            "python3 scripts/keyed_sponsor_rehearsal.py --base-url http://127.0.0.1:8080",
        )
        self.assertIn("Optional Keyed Sponsor Rehearsal", command_reference)
        self.assertIn(
            "python3 scripts/keyed_sponsor_rehearsal.py --base-url http://127.0.0.1:8080 --json",
            command_reference,
        )
        self.assertIn("never secret values", command_reference)
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
        self.assertIn("--request-path", result.stdout)
        self.assertIn("--json", result.stdout)


if __name__ == "__main__":
    unittest.main()
