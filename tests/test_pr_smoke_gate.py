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
        self.assertIn('export OPENAI_API_KEY=""', script)
        self.assertIn('export TAVILY_API_KEY=""', script)
        self.assertIn('export COMPOSIO_API_KEY=""', script)
        self.assertIn('export IA_LIVE_MODE=""', script)
        self.assertIn('export IA_DISABLE_DOTENV="1"', script)
        self.assertIn("bash scripts/run.sh --json", script)
        self.assertIn("agent.judge --no-write --json", script)
        self.assertIn("agent.evidence_receipts --no-write --json", script)
        self.assertIn("agent.downstream_gate --all --json", script)
        self.assertIn("agent.packet_advisor --fixture ai_spend_budget_overrun", script)
        self.assertIn("agent.portkey_adapter --fixture ai_spend_budget_overrun --mode dry-run", script)
        self.assertIn("agent.sponsor_proof_collector examples/requests/support_triage_trial.yml --no-write --composio-dry-run --json", script)
        self.assertIn("agent.trial_evidence_replay", script)
        self.assertIn("schemas/pilot_memo.schema.json", script)
        self.assertIn("agent.pilot_memo examples/requests/support_triage_trial.yml --no-write --json", script)
        self.assertIn("agent.pilot_memo examples/requests/support_triage_trial.yml --no-write --copy", script)
        self.assertIn("bash scripts/review_60.sh --dry-run", script)
        self.assertIn("scripts/walkthrough_smoke.py", script)
        self.assertIn("bash scripts/reviewer_smoke_gate.sh", script)
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
        self.assertIn('OPENAI_API_KEY: ""', workflow)
        self.assertIn('TAVILY_API_KEY: ""', workflow)
        self.assertIn('COMPOSIO_API_KEY: ""', workflow)
        self.assertIn('IA_LIVE_MODE: ""', workflow)
        self.assertIn('IA_DISABLE_DOTENV: "1"', workflow)

    def test_walkthrough_smoke_script_locks_product_surface(self) -> None:
        script = (ROOT / "scripts" / "walkthrough_smoke.py").read_text(encoding="utf-8")
        self.assertIn("sys.path.insert(0, str(ROOT))", script)

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

    def test_reviewer_smoke_script_documents_served_reviewer_journey(self) -> None:
        script_path = ROOT / "scripts" / "reviewer_smoke.py"
        script = script_path.read_text(encoding="utf-8")

        self.assertTrue(script_path.is_file())
        self.assertTrue(os.access(script_path, os.X_OK))
        self.assertIn("Server-backed reviewer smoke", script)
        self.assertIn("/api/ia-packet?fixture=", script)
        self.assertIn("/api/workbench/generate", script)
        self.assertIn("/api/walkthrough", script)
        self.assertIn("/api/packets/ai_spend_budget_overrun/downstream/portkey?mode=dry-run", script)
        self.assertIn("/api/chat", script)
        self.assertIn("/proofgraph", script)
        self.assertIn("ProofGraph visual", script)
        self.assertIn("/api/sponsor-readiness/matrix", script)
        self.assertIn("/api/sponsor-proof-runs", script)
        self.assertIn("/api/mind/init", script)
        self.assertIn("/api/mind/step", script)
        self.assertIn("/api/skills", script)
        self.assertIn("/api/connectors?session_id=", script)
        self.assertIn("EXPECTED_TEAM_LENSES", script)
        self.assertIn("team_lenses.v0", script)
        self.assertIn("renderPacketTeamLenses", script)
        self.assertIn("live_calls_made", script)
        self.assertIn("approves_access", script)
        self.assertIn("mutates_production", script)
        self.assertIn("Reviewer smoke passed", script)

        result = subprocess.run(
            [sys.executable, "scripts/reviewer_smoke.py", "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--base-url", result.stdout)

    def test_reviewer_stress_script_locks_packet_selector_edges(self) -> None:
        script_path = ROOT / "scripts" / "reviewer_stress_smoke.py"
        script = script_path.read_text(encoding="utf-8")

        self.assertTrue(script_path.is_file())
        self.assertTrue(os.access(script_path, os.X_OK))
        self.assertIn("Adversarial reviewer smoke", script)
        self.assertIn("run_smoke", script)
        self.assertIn("/api/packets/", script)
        self.assertIn("/proofgraph", script)
        self.assertIn("/verification", script)
        self.assertIn("mcp_tool_blast_radius", script)
        self.assertIn("ai_spend_budget_overrun", script)
        self.assertIn("miasma_pre_permission_packet", script)
        self.assertIn("does_not_exist", script)
        self.assertIn("composio_dry_run", script)
        self.assertIn("live_tavily", script)
        self.assertIn("tavily_api_key_missing", script)
        self.assertIn("created_records", script)
        self.assertIn("allow_live_read_only_evidence", script)
        self.assertIn("stress-created ledger live-call marker drifted", script)
        self.assertIn("live read-only evidence allowed when configured", script)
        self.assertIn("Reviewer stress passed", script)

        result = subprocess.run(
            [sys.executable, "scripts/reviewer_stress_smoke.py", "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--base-url", result.stdout)

    def test_reviewer_smoke_gate_starts_server_without_live_keys(self) -> None:
        script_path = ROOT / "scripts" / "reviewer_smoke_gate.sh"
        script = script_path.read_text(encoding="utf-8")

        self.assertTrue(script_path.is_file())
        self.assertTrue(os.access(script_path, os.X_OK))
        self.assertIn("set -euo pipefail", script)
        self.assertIn('export NEBIUS_API_KEY=""', script)
        self.assertIn('export OPENAI_API_KEY=""', script)
        self.assertIn('export TAVILY_API_KEY=""', script)
        self.assertIn('export COMPOSIO_API_KEY=""', script)
        self.assertIn('export IA_LIVE_MODE=""', script)
        self.assertIn('export IA_DISABLE_DOTENV="1"', script)
        self.assertIn("-m uvicorn web.app:app", script)
        self.assertIn("scripts/reviewer_smoke.py --base-url", script)
        self.assertIn("scripts/reviewer_stress_smoke.py --base-url", script)
        self.assertIn("IA_REVIEWER_SMOKE_PORT", script)
        self.assertIn("Reviewer smoke gate passed", script)

        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
        self.assertIn('python -m pip install -e ".[web]"', workflow)

    def test_manifest_and_review_docs_expose_pr_smoke_gate(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["pr_smoke_command"], "bash scripts/pr_smoke.sh")
        self.assertEqual(manifest["review_60_command"], "bash scripts/review_60.sh")
        self.assertIn("walkthrough API/static surface", manifest["pr_smoke_scope"])
        self.assertIn("bash scripts/review_60.sh", manifest["product_review_path"])
        self.assertEqual(manifest["review_60_proofgraph_url"], "/proofgraph")
        self.assertIn("bash scripts/review_60.sh", manifest["five_minute_review_commands"])
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
