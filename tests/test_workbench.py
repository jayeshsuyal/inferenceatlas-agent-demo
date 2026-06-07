import json
import unittest
from pathlib import Path

from agent.trial import load_trial_request, validate_trial_request
from agent.workbench import (
    WORKBENCH_SAFETY_ANCHOR,
    build_workbench_registry,
    build_workbench_result,
    render_workbench_markdown,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
MCP_REQUEST = ROOT / "examples" / "requests" / "mcp_tool_blast_radius.yml"


class WorkbenchTests(unittest.TestCase):
    def test_workbench_registry_has_fixture_for_every_lane(self) -> None:
        registry = build_workbench_registry()

        self.assertEqual(registry["schema_version"], "packet_workbench.v0")
        self.assertEqual(registry["mode"], "fixture_only")
        self.assertEqual(registry["default_fixture_id"], "mcp_tool_blast_radius")
        self.assertFalse(registry["safety_boundary"]["paste_input_enabled"])
        self.assertFalse(registry["safety_boundary"]["calls_v1"])

        lanes = {lane["lane_id"] for lane in registry["lanes"]}
        fixtures_by_lane = {
            lane_id: [fixture for fixture in registry["fixtures"] if fixture["lane_id"] == lane_id]
            for lane_id in lanes
        }

        self.assertEqual(lanes, {"agent_access", "ai_spend", "supply_chain_ci", "mcp_tool_access"})
        for lane_id, fixtures in fixtures_by_lane.items():
            self.assertTrue(fixtures, msg=f"{lane_id} has no workbench fixture")

    def test_workbench_results_never_approve_grant_write_or_call_v1(self) -> None:
        registry = build_workbench_registry()

        for fixture in registry["fixtures"]:
            result = build_workbench_result(fixture["fixture_id"])
            decision = result["decision"]
            safety = result["safety_boundary"]

            self.assertEqual(result["schema_version"], "packet_workbench_result.v0")
            self.assertTrue(result["local_verification"]["content_hash"].startswith("sha256:"))
            self.assertFalse(result["local_verification"]["calls_v1"])
            self.assertTrue(result["local_verification"]["read_only"])
            self.assertFalse(decision["production_access"])
            self.assertFalse(decision["permission_grants"])
            self.assertFalse(decision["external_writes"])
            self.assertFalse(decision["approval_granted"])
            self.assertFalse(safety["approves_access"])
            self.assertFalse(safety["grants_permissions"])
            self.assertFalse(safety["executes_external_writes"])
            self.assertFalse(safety["mutates_production"])
            self.assertFalse(safety["approves_spend"])
            self.assertFalse(safety["selects_provider"])
            self.assertFalse(safety["guarantees_savings"])
            self.assertIn(WORKBENCH_SAFETY_ANCHOR, result["copy_review_brief"])
            self.assertIn(WORKBENCH_SAFETY_ANCHOR, render_workbench_markdown(result))

    def test_mcp_tool_blast_radius_fixture_validates(self) -> None:
        source_text = MCP_REQUEST.read_text(encoding="utf-8")
        payload = load_trial_request(MCP_REQUEST)
        validation = validate_trial_request(payload, source_text=source_text)

        self.assertEqual(validation["errors"], [])
        self.assertEqual(validation["warnings"], [])
        self.assertIn("Connector gateway", source_text)
        self.assertIn("Browser sandbox", source_text)
        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, source_text, msg=f"{forbidden} leaked in MCP fixture")

    def test_workbench_api_generates_export_ready_result(self) -> None:
        from web.app import WorkbenchGenerateRequest, packet_workbench_generate

        result = packet_workbench_generate(WorkbenchGenerateRequest(fixture_id="mcp_tool_blast_radius"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["fixture"]["lane_id"], "mcp_tool_access")
        self.assertEqual(result["fixture"]["path"], "examples/requests/mcp_tool_blast_radius.yml")
        self.assertFalse(result["local_verification"]["calls_v1"])
        self.assertFalse(result["decision"]["production_access"])
        self.assertIn("Tool owner", " ".join(result["reviewer_routing"]))
        self.assertGreaterEqual(len(result["output_files"]), 2)
        self.assertTrue(all(item["file_id"] for item in result["output_files"]))

    def test_mcp_fixture_uses_connector_specific_next_human_action(self) -> None:
        result = build_workbench_result("mcp_tool_blast_radius")
        action = result["decision"]["next_human_action"]

        self.assertIn("connector allowlist", action)
        self.assertIn("browser sandbox", action)
        self.assertIn("tool-owner approval", action)
        self.assertNotIn("analytics validation", action)
        self.assertIn(action, result["copy_review_brief"])

    def test_workbench_static_ui_is_reachable(self) -> None:
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        tour = (ROOT / "docs" / "PRODUCT_TOUR.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for expected in [
            'data-tab="workbench"',
            'id="workbench-view"',
            'id="workbench-lane-select"',
            'id="workbench-fixture-select"',
            'id="btn-generate-workbench"',
            'id="btn-copy-workbench-brief"',
            'id="btn-export-workbench"',
        ]:
            self.assertIn(expected, html)
        for expected in [
            "/api/workbench",
            "/api/workbench/generate",
            "renderWorkbenchResult",
            "workbenchShouldAutorun",
            "copyWorkbenchBrief",
            "Copy verification link",
            "Open IA Packet",
            "View verification hash",
            'window.location.pathname === "/workbench"',
        ]:
            self.assertIn(expected, js)
        for expected in [".workbench-select", ".workbench-proof-grid"]:
            self.assertIn(expected, css)

        self.assertEqual(manifest["packet_workbench_surface"], "/workbench")
        self.assertEqual(manifest["packet_workbench_api"], "/api/workbench/generate")
        self.assertEqual(manifest["mcp_tool_blast_radius_request"], "examples/requests/mcp_tool_blast_radius.yml")
        self.assertIn("packet workbench", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("MCP tool blast-radius fixture", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("/workbench", tour)
        self.assertIn("examples/requests/mcp_tool_blast_radius.yml", tour)
        self.assertIn("Packet Workbench", readme)


if __name__ == "__main__":
    unittest.main()
