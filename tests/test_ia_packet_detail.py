import json
import unittest
from pathlib import Path

from agent.packet_detail import (
    IA_PACKET_SAFETY_ANCHOR,
    build_ia_packet_detail,
    build_ia_packet_verification,
    render_ia_packet_detail_markdown,
)
from agent.workbench import build_workbench_registry


ROOT = Path(__file__).resolve().parents[1]


class IAPacketDetailTests(unittest.TestCase):
    def test_ia_packet_detail_is_canonical_safe_projection_for_every_fixture(self) -> None:
        registry = build_workbench_registry()

        for fixture in registry["fixtures"]:
            detail = build_ia_packet_detail(fixture["fixture_id"])
            decision = detail["decision"]
            safety = detail["safety_boundary"]

            self.assertEqual(detail["schema_version"], "ia_packet_detail.v0")
            self.assertEqual(detail["product_object"], "IA Packet")
            self.assertEqual(detail["safety_anchor"], IA_PACKET_SAFETY_ANCHOR)
            self.assertFalse(detail["local_verification"]["calls_v1"], msg=fixture["fixture_id"])
            self.assertTrue(detail["local_verification"]["read_only"], msg=fixture["fixture_id"])
            self.assertFalse(decision["production_access"], msg=fixture["fixture_id"])
            self.assertFalse(decision["permission_grants"], msg=fixture["fixture_id"])
            self.assertFalse(decision["external_writes"], msg=fixture["fixture_id"])
            self.assertFalse(decision["approval_granted"], msg=fixture["fixture_id"])
            self.assertFalse(safety["approves_access"], msg=fixture["fixture_id"])
            self.assertFalse(safety["grants_permissions"], msg=fixture["fixture_id"])
            self.assertFalse(safety["executes_external_writes"], msg=fixture["fixture_id"])
            self.assertFalse(safety["mutates_production"], msg=fixture["fixture_id"])
            self.assertFalse(safety["downstream_can_approve"], msg=fixture["fixture_id"])
            self.assertFalse(safety["downstream_can_mutate_packet"], msg=fixture["fixture_id"])
            self.assertFalse(safety["downstream_can_override_verdict"], msg=fixture["fixture_id"])
            trace = detail.get("sponsor_proof_trace") or {}
            if trace:
                self.assertTrue(trace["trace_id"].startswith("ia-sponsor-proof-trace-"), msg=fixture["fixture_id"])
                self.assertEqual(trace["packet_id"], detail["packet_reference"]["packet_id"], msg=fixture["fixture_id"])
                self.assertEqual(trace["sponsor_order"], ["tavily", "composio", "openclaw", "nebius"])
                self.assertTrue(trace["all_fallback_used"], msg=fixture["fixture_id"])
                self.assertTrue(trace["all_non_executing"], msg=fixture["fixture_id"])
                self.assertFalse(trace["approves_access"], msg=fixture["fixture_id"])
                self.assertFalse(trace["approves_spend"], msg=fixture["fixture_id"])
                self.assertFalse(trace["selects_provider"], msg=fixture["fixture_id"])
                self.assertEqual(len(trace["steps"]), 4, msg=fixture["fixture_id"])
                for step in trace["steps"]:
                    self.assertFalse(step["used_live_key"], msg=fixture["fixture_id"])
                    self.assertTrue(step["fallback_used"], msg=fixture["fixture_id"])
                    self.assertFalse(step["would_execute"], msg=fixture["fixture_id"])
                    self.assertFalse(step["can_approve_access"], msg=fixture["fixture_id"])
            self.assertIn(IA_PACKET_SAFETY_ANCHOR, render_ia_packet_detail_markdown(detail))

    def test_downstream_consumers_read_same_packet_reference_without_override_power(self) -> None:
        detail = build_ia_packet_detail("mcp_tool_blast_radius")
        packet_reference = detail["packet_reference"]

        self.assertGreaterEqual(len(detail["downstream_consumers"]), 5)
        categories = {consumer["subscriber_category"] for consumer in detail["downstream_consumers"]}
        self.assertEqual(categories, {"ci", "gateway", "observability", "review", "spend"})

        for consumer in detail["downstream_consumers"]:
            self.assertEqual(consumer["packet_reference"], packet_reference)
            self.assertEqual(consumer["source_of_truth"], "ia_packet.packet_reference")
            self.assertFalse(consumer["can_approve_access"])
            self.assertFalse(consumer["can_grant_permissions"])
            self.assertFalse(consumer["can_mutate_packet"])
            self.assertFalse(consumer["can_override_verdict"])
            self.assertFalse(consumer["executes_external_writes"])

    def test_ia_packet_api_and_static_surface_are_declared(self) -> None:
        from web.app import ia_packet_detail

        payload = ia_packet_detail(fixture="mcp_tool_blast_radius")
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["product_object"], "IA Packet")
        self.assertGreaterEqual(len(payload["output_files"]), 2)

        for expected in [
            'data-tab="packet"',
            'id="packet-view"',
            'id="packet-review-rail"',
            'id="packet-lane-select"',
            'id="packet-fixture-select"',
            'id="btn-load-packet"',
            'id="btn-copy-packet-brief"',
            'id="btn-export-packet"',
            'id="btn-export-portkey-gate"',
            'id="packet-team-card"',
            "Export Portkey gate",
            "IA did not approve. The next human action is named above.",
            "Review in 60 seconds",
            "Request -> Packet -> Sponsor proof -> Downstream gate -> Team lenses -> Export",
            "Team lenses",
        ]:
            self.assertIn(expected, html)

        for expected in [
            "/api/ia-packet",
            'window.location.pathname === "/packet"',
            "const requestedFixtureId = packetSelectedFixtureId();",
            "await loadPacketRegistry(requestedFixtureId);",
            "loadPacketRegistry",
            "renderPacketFixtureOptions",
            "packetSelectedFixtureId",
            "setupPacketReviewRail",
            "markPacketReviewRailLoaded",
            "data-packet-target",
            "renderPacketDetail",
            "renderPacketTeamLenses",
            "Teams reading this packet",
            "Copy IA Packet link",
            "Open IA Packet",
            "packetPortkeyPreviewPath",
            "/downstream/portkey?mode=dry-run",
            "downloadJsonPayload",
            "Portkey dry-run gate JSON exported. No API call made.",
        ]:
            self.assertIn(expected, js)

        self.assertEqual(manifest["ia_packet_surface"], "/packet?fixture=mcp_tool_blast_radius&autorun=1")
        self.assertEqual(manifest["ia_packet_api"], "/api/ia-packet?fixture=mcp_tool_blast_radius")
        self.assertEqual(manifest["ia_packet_switcher"], "all registered Workbench fixtures")
        self.assertEqual(manifest["review_60_packet_url"], "/packet?fixture=mcp_tool_blast_radius&autorun=1")
        self.assertIn("IA Packet detail surface", manifest["private_v1_boundary"]["public_proof_surface"])

    def test_ia_packet_switcher_covers_every_registered_fixture(self) -> None:
        registry = build_workbench_registry()
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")

        self.assertGreaterEqual(len(registry["fixtures"]), 6)
        self.assertIn('id="packet-lane-select"', html)
        self.assertIn('id="packet-fixture-select"', html)
        self.assertIn("applyPacketRegistry", js)
        self.assertIn("findPacketFixture", js)

        for fixture in registry["fixtures"]:
            detail = build_ia_packet_detail(fixture["fixture_id"])
            self.assertEqual(detail["fixture"]["fixture_id"], fixture["fixture_id"])
            self.assertFalse(detail["decision"]["production_access"], msg=fixture["fixture_id"])
            self.assertFalse(detail["local_verification"]["calls_v1"], msg=fixture["fixture_id"])

    def test_packet_verification_endpoint_resolves_every_public_fixture(self) -> None:
        from web.app import packet_verification

        registry = build_workbench_registry()

        for fixture in registry["fixtures"]:
            fixture_id = fixture["fixture_id"]
            detail = build_ia_packet_detail(fixture_id)
            packet_id = detail["packet_reference"]["packet_id"]
            expected = build_ia_packet_verification(fixture_id)

            by_fixture = packet_verification(fixture_id)
            self.assertTrue(by_fixture["ok"], msg=fixture_id)
            self.assertTrue(by_fixture["read_only"], msg=fixture_id)
            self.assertEqual(by_fixture["verification"]["packet_id"], packet_id, msg=fixture_id)
            self.assertFalse(by_fixture["verification"]["production_access"], msg=fixture_id)
            self.assertFalse(by_fixture["verification"]["external_writes"], msg=fixture_id)
            self.assertFalse(by_fixture["verification"]["permission_grants"], msg=fixture_id)
            self.assertFalse(by_fixture["verification"]["approval_granted"], msg=fixture_id)
            self.assertFalse(by_fixture["verification"]["private_boundary"]["private_source_exposed"], msg=fixture_id)

            by_packet_id = packet_verification(packet_id)
            self.assertEqual(by_packet_id["verification"]["packet_id"], expected["packet_id"], msg=fixture_id)
            self.assertEqual(by_packet_id["verification"]["content_hash"], expected["content_hash"], msg=fixture_id)

    def test_packet_review_rail_guides_first_time_reviewer(self) -> None:
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")

        expected_steps = {
            "Request": "packet-summary-card",
            "Packet": "packet-decision-card",
            "Sponsor proof": "packet-sponsor-card",
            "Downstream gate": "packet-downstream-card",
            "Team lenses": "packet-team-card",
            "Export": "packet-export-card",
        }

        self.assertIn("Review in 60 seconds", html)
        self.assertIn("packet-review-rail", html)
        self.assertIn("packet-review-step", html)
        self.assertIn(".packet-review-rail", css)
        self.assertIn(".packet-review-step.ready", css)
        self.assertIn(".team-lens-list", css)
        self.assertIn(".team-lens-row", css)
        self.assertIn("scrollIntoView", js)
        self.assertIn("Sponsors collect proof only", js)
        self.assertIn("Live keys", js)
        self.assertIn("trace ${escapeHtml(trace.trace_id", js)
        self.assertIn("packet ${escapeHtml(trace.packet_id", js)

        for label, target in expected_steps.items():
            self.assertIn(label, html)
            self.assertIn(f'data-packet-target="{target}"', html)


if __name__ == "__main__":
    unittest.main()
