"""UI connectors registry."""

import unittest

from agent.ui_connectors import CONNECTORS, build_connectors_payload


class UIConnectorsTests(unittest.TestCase):
    def test_connector_count(self) -> None:
        self.assertEqual(len(CONNECTORS), 6)
        ids = {c.id for c in CONNECTORS}
        self.assertIn("github", ids)
        self.assertIn("google_drive", ids)

    def test_google_drive_submenu(self) -> None:
        drive = next(c for c in CONNECTORS if c.id == "google_drive")
        self.assertEqual(len(drive.actions), 3)

    def test_payload_intro(self) -> None:
        payload = build_connectors_payload()
        self.assertIn("skills_blurb", payload["intro"])
        self.assertEqual(len(payload["connectors"]), 6)
        for row in payload["connectors"]:
            self.assertIn("layman_summary", row)
            self.assertIn("status", row)


if __name__ == "__main__":
    unittest.main()
