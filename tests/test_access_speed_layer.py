import json
import unittest
from pathlib import Path

from agent.review_room import render_review_room_html
from agent.trust import (
    build_review_room,
    build_trust_receipt,
    render_review_room_markdown,
    render_trust_receipt_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


class AccessSpeedLayerTests(unittest.TestCase):
    def test_trust_receipt_routes_requests_by_speed_lane(self) -> None:
        receipt = build_trust_receipt()
        layer = receipt["access_speed_layer"]
        by_scenario = {route["scenario"]: route for route in layer["routes"]}

        self.assertEqual(layer["decision_time"], "immediate")
        self.assertTrue(layer["packet_generated_automatically"])
        self.assertTrue(layer["manual_back_and_forth_replaced"])
        self.assertTrue(layer["all_routes_immediate"])
        self.assertTrue(layer["has_fast_lane"])
        self.assertTrue(layer["has_proof_routed_lane"])
        self.assertTrue(layer["has_blocked_fast_lane"])
        self.assertEqual(by_scenario["read_only_analytics_agent"]["lane"], "fast_lane_scoped_validation")
        self.assertEqual(by_scenario["support_triage_agent"]["lane"], "proof_routed_scoped_validation")
        self.assertEqual(by_scenario["admin_code_fix_bot"]["lane"], "blocked_fast")
        self.assertFalse(any(route["production_access"] for route in layer["routes"]))

    def test_review_room_carries_same_access_speed_layer(self) -> None:
        receipt = build_trust_receipt()
        review_room = build_review_room(receipt)

        self.assertEqual(review_room["access_speed_layer"], receipt["access_speed_layer"])

    def test_rendered_surfaces_explain_speed_without_approval_power(self) -> None:
        receipt = build_trust_receipt()
        review_room = build_review_room(receipt)
        surfaces = [
            render_trust_receipt_markdown(receipt),
            render_review_room_markdown(review_room),
            render_review_room_html(review_room),
        ]

        for surface in surfaces:
            self.assertIn("Access Speed Layer", surface)
            self.assertIn("Decision time", surface)
            self.assertIn("fast_lane_scoped_validation", surface)
            self.assertIn("proof_routed_scoped_validation", surface)
            self.assertIn("blocked_fast", surface)
            self.assertIn("critical requests are blocked immediately", surface)
            self.assertNotIn("production_access_granted=true", surface)

    def test_manifest_exposes_access_speed_layer_surface(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(
            manifest["access_speed_layer_surface"],
            "examples/generated/review_room.html and examples/generated/trust_receipt.json",
        )
        self.assertIn("access speed layer", manifest["private_v1_boundary"]["public_proof_surface"])


if __name__ == "__main__":
    unittest.main()
