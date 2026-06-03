import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewRoomWalkthroughTests(unittest.TestCase):
    def test_walkthrough_points_to_visual_review_room(self) -> None:
        walkthrough = (ROOT / "docs" / "REVIEW_ROOM_WALKTHROUGH.md").read_text(encoding="utf-8")

        for expected in [
            "Review Room Walkthrough",
            "examples/generated/review_room.html",
            "examples/generated/review_room.desktop.jpg",
            "Scenario Matrix",
            "Policy Gate Status",
            "Sponsor Adapter Status",
            "Private Boundary",
            "Private engine, public proof",
        ]:
            self.assertIn(expected, walkthrough)

    def test_walkthrough_preserves_private_boundary(self) -> None:
        walkthrough = (ROOT / "docs" / "REVIEW_ROOM_WALKTHROUGH.md").read_text(encoding="utf-8")

        for expected in [
            "Do not show API keys",
            "private v1 source",
            "live sponsor tokens",
            "deterministic packet, policy gate, blocked claims, and safety state remain the authority",
        ]:
            self.assertIn(expected, walkthrough)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, walkthrough)

    def test_screenshot_artifact_is_jpeg(self) -> None:
        screenshot = ROOT / "examples" / "generated" / "review_room.desktop.jpg"

        self.assertTrue(screenshot.exists())
        self.assertGreater(screenshot.stat().st_size, 1024)
        self.assertEqual(screenshot.read_bytes()[:3], b"\xff\xd8\xff")

    def test_manifest_points_to_walkthrough_and_screenshot(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["review_room_walkthrough"], "docs/REVIEW_ROOM_WALKTHROUGH.md")
        self.assertEqual(manifest["review_room_screenshot"], "examples/generated/review_room.desktop.jpg")
        self.assertEqual(manifest["primary_artifacts"]["review_room_walkthrough"], "docs/REVIEW_ROOM_WALKTHROUGH.md")
        self.assertEqual(manifest["primary_artifacts"]["review_room_screenshot"], "examples/generated/review_room.desktop.jpg")


if __name__ == "__main__":
    unittest.main()
