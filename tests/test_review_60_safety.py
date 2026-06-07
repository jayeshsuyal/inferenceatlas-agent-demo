import json
import subprocess
import unittest
from pathlib import Path

from agent.workbench import build_workbench_registry, build_workbench_result


ROOT = Path(__file__).resolve().parents[1]


class Review60SafetyTests(unittest.TestCase):
    def test_no_workbench_fixture_unlocks_decision_lock(self) -> None:
        registry = build_workbench_registry()

        for fixture in registry["fixtures"]:
            result = build_workbench_result(fixture["fixture_id"])
            decision = result["decision"]
            safety = result["safety_boundary"]

            self.assertFalse(decision["production_access"], msg=fixture["fixture_id"])
            self.assertFalse(decision["permission_grants"], msg=fixture["fixture_id"])
            self.assertFalse(decision["external_writes"], msg=fixture["fixture_id"])
            self.assertFalse(decision["approval_granted"], msg=fixture["fixture_id"])
            self.assertFalse(safety["approves_access"], msg=fixture["fixture_id"])
            self.assertFalse(safety["grants_permissions"], msg=fixture["fixture_id"])
            self.assertFalse(safety["executes_external_writes"], msg=fixture["fixture_id"])
            self.assertFalse(safety["mutates_production"], msg=fixture["fixture_id"])

    def test_no_workbench_response_calls_v1(self) -> None:
        registry = build_workbench_registry()

        for fixture in registry["fixtures"]:
            result = build_workbench_result(fixture["fixture_id"])
            self.assertFalse(result["local_verification"]["calls_v1"], msg=fixture["fixture_id"])
            self.assertTrue(result["local_verification"]["read_only"], msg=fixture["fixture_id"])

    def test_review_60_terminal_output_lists_safety_invariants(self) -> None:
        result = subprocess.run(
            ["bash", "scripts/review_60.sh", "--dry-run"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("no keys required", result.stdout)
        self.assertIn("dry-run by default", result.stdout)
        self.assertIn("no v1 calls", result.stdout)
        self.assertIn("/workbench?fixture=mcp_tool_blast_radius&autorun=1", result.stdout)
        self.assertIn("Tavily -> Composio -> OpenClaw -> Nebius", result.stdout)

    def test_review_60_surface_is_declared(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "REVIEW_60_PATH.md").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["review_60_command"], "bash scripts/review_60.sh")
        self.assertEqual(
            manifest["review_60_workbench_url"],
            "/workbench?fixture=mcp_tool_blast_radius&autorun=1",
        )
        self.assertIn("bash scripts/review_60.sh", readme)
        self.assertIn("/workbench?fixture=mcp_tool_blast_radius&autorun=1", readme)
        self.assertIn("Copy verification link", js)
        self.assertIn("workbenchShouldAutorun", js)
        self.assertIn("mcp_tool_blast_radius", docs)


if __name__ == "__main__":
    unittest.main()
