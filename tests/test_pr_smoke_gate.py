import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrSmokeGateTests(unittest.TestCase):
    def test_public_run_script_is_no_write_judge_entrypoint(self) -> None:
        script_path = ROOT / "scripts" / "run.sh"
        script = script_path.read_text(encoding="utf-8")

        self.assertTrue(script_path.is_file())
        self.assertTrue(os.access(script_path, os.X_OK))
        self.assertIn("set -euo pipefail", script)
        self.assertIn('COMPOSIO_DRY_RUN="${COMPOSIO_DRY_RUN:-1}"', script)
        self.assertIn('IA_LIVE_MODE="${IA_LIVE_MODE:-}"', script)
        self.assertIn("-m agent.judge --no-write", script)

    def test_script_is_no_key_product_safety_gate(self) -> None:
        script_path = ROOT / "scripts" / "pr_smoke.sh"
        script = script_path.read_text(encoding="utf-8")

        self.assertTrue(script_path.is_file())
        self.assertTrue(os.access(script_path, os.X_OK))
        self.assertIn("set -euo pipefail", script)
        self.assertIn('export NEBIUS_API_KEY=""', script)
        self.assertIn('export TAVILY_API_KEY=""', script)
        self.assertIn('export COMPOSIO_API_KEY=""', script)
        self.assertIn('export IA_LIVE_MODE=""', script)
        self.assertIn("bash scripts/run.sh --json", script)
        self.assertIn("agent.judge --no-write --json", script)
        self.assertIn("agent.evidence_receipts --no-write --json", script)
        self.assertIn("agent.downstream_gate --all --json", script)
        self.assertIn("agent.trial_evidence_replay", script)
        self.assertIn("schemas/pilot_memo.schema.json", script)
        self.assertIn("agent.pilot_memo examples/requests/support_triage_trial.yml --no-write --json", script)
        self.assertIn("agent.pilot_memo examples/requests/support_triage_trial.yml --no-write --copy", script)
        self.assertIn("scripts/walkthrough_smoke.py", script)
        self.assertIn("agent.verify_artifacts --json", script)
        self.assertIn("unittest discover -s tests", script)
        self.assertIn("git grep -l -E", script)
        self.assertIn("File names only", script)
        self.assertIn("InferenceAtlas PR smoke gate passed.", script)

        for forbidden_prefix in ("sk" + "-proj-", "tvly" + "-", "GOC" + "SPX-", "ak" + "_"):
            self.assertNotIn(forbidden_prefix, script)

    def test_github_smoke_workflow_runs_script_on_prs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertIn("Run public PR smoke gate", workflow)
        self.assertIn("PYTHON=python bash scripts/pr_smoke.sh", workflow)
        self.assertIn('NEBIUS_API_KEY: ""', workflow)
        self.assertIn('TAVILY_API_KEY: ""', workflow)
        self.assertIn('COMPOSIO_API_KEY: ""', workflow)
        self.assertIn('IA_LIVE_MODE: ""', workflow)

    def test_walkthrough_smoke_script_locks_product_surface(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/walkthrough_smoke.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(
            "Walkthrough smoke passed: request -> packet -> sponsor_proof_trace -> sponsor_replay -> review_cycle -> pilot_memo",
            result.stdout,
        )

    def test_manifest_and_review_docs_expose_pr_smoke_gate(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["pr_smoke_command"], "bash scripts/pr_smoke.sh")
        self.assertIn("walkthrough API/static surface", manifest["pr_smoke_scope"])
        self.assertEqual(manifest["verification"]["pr_smoke_gate"], "bash scripts/pr_smoke.sh")
        self.assertIn("bash scripts/pr_smoke.sh", manifest["product_review_path"])
        self.assertIn("bash scripts/pr_smoke.sh", manifest["five_minute_review_commands"])
        self.assertIn("bash scripts/pr_smoke.sh", manifest["judge_review_path"])

        for relative_path in (
            "AGENTS.md",
            "docs/COMMAND_REFERENCE.md",
            "docs/PRODUCT_QUALITY_AUDIT.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
        ):
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("bash scripts/pr_smoke.sh", text)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("bash scripts/run.sh", readme)
        self.assertIn("docs/COMMAND_REFERENCE.md", readme)


if __name__ == "__main__":
    unittest.main()
