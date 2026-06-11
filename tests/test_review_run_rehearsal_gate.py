"""Final ReviewRun rehearsal gate contract tests."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_run_rehearsal_gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("review_run_rehearsal_gate", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReviewRunRehearsalGateTests(unittest.TestCase):
    def test_script_is_executable_and_documents_final_loop(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        self.assertIn("Final ReviewRun rehearsal gate", script)
        self.assertIn("connect/use demo repo", script)
        self.assertIn("generate packet", script)
        self.assertIn("Ask IA next step", script)
        self.assertIn("attach proof", script)
        self.assertIn("Test Portkey guardrail", script)
        self.assertIn("open ProofGraph", script)
        self.assertIn("export brief", script)
        self.assertIn("/api/review-runs", script)
        self.assertIn("/portkey/guardrail-test", script)
        self.assertIn("/proofgraph?review_run_id=", script)
        self.assertIn("copy_review_brief", script)
        self.assertIn("proof_attachment_changes_verdict", script)
        self.assertIn("portkey_policy_mutation_allowed", script)
        self.assertIn("renderReviewRunCoachSuggestions", script)
        self.assertIn("ask_ia_suggestions_contract", script)
        self.assertIn("Use prepared receipt", script)
        self.assertIn("proof_receipts_contract", script)
        self.assertIn("repo-portkey-runway", script)
        self.assertIn("portkey_runway_contract", script)
        self.assertIn("repo-option-row", script)
        self.assertIn("no_chip_wall", script)
        self.assertIn("no_raw_packet_dump", script)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--base-url", result.stdout)
        self.assertIn("--json", result.stdout)

    def test_report_markdown_is_recording_ready_and_safety_bounded(self) -> None:
        module = _load_module()
        report = {
            "status": "passed",
            "base_url": "http://127.0.0.1:8080",
            "steps": list(module.EXPECTED_STEPS),
            "screenshot_checkpoints": list(module.SCREENSHOT_CHECKPOINTS),
            "browser_rehearsals": list(module.BROWSER_REHEARSALS),
            "review_run": {
                "selected_repo": "inferenceatlas/support-triage-trial",
                "packet_revision_before": "rev_1",
                "packet_revision_after": "rev_2",
                "portkey_state_before": "Block",
                "portkey_state_after": "Allow with policy",
                "guardrail_event_id": "portkey-guardrail-demo",
                "still_blocked_scope": ["repo admin", "org-wide write", "secrets"],
                "copy_review_brief_ready": True,
            },
            "safety": {
                "approval_granted": False,
                "external_writes_enabled": False,
                "portkey_api_call_made": False,
                "portkey_policy_mutation_allowed": False,
                "proof_attachment_changes_verdict": False,
            },
        }

        rendered = module.render_markdown(report)

        self.assertIn("# ReviewRun Final Rehearsal Gate", rendered)
        self.assertIn("Private engine, public proof.", rendered)
        self.assertIn("packet: `rev_1` -> `rev_2`", rendered)
        self.assertIn("Portkey: `Block` -> `Allow with policy`", rendered)
        self.assertIn("- repo_connect", rendered)
        self.assertIn("- repo_selected_indexed", rendered)
        self.assertIn("- proof_workbench", rendered)
        self.assertIn("- rerun_delta", rendered)
        self.assertIn("- portkey_gate", rendered)
        self.assertIn("- proofgraph", rendered)
        self.assertIn("- export_brief", rendered)
        self.assertIn("## Browser Rehearsals", rendered)
        self.assertIn("- desktop browser rehearsal", rendered)
        self.assertIn("- mobile browser rehearsal", rendered)
        self.assertIn("approval granted: `False`", rendered)
        self.assertIn("Portkey policy mutation allowed: `False`", rendered)

    def test_smoke_gate_runs_review_run_rehearsal_gate(self) -> None:
        script = (ROOT / "scripts" / "reviewer_smoke_gate.sh").read_text(encoding="utf-8")

        self.assertIn("scripts/reviewer_smoke.py --base-url", script)
        self.assertIn("scripts/reviewer_stress_smoke.py --base-url", script)
        self.assertIn("scripts/review_run_rehearsal_gate.py --base-url", script)
        self.assertIn("--json", script)


if __name__ == "__main__":
    unittest.main()
