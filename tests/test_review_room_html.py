from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from agent.review_room import render_review_room_html, write_review_room_html
from agent.trust import build_review_room


ROOT = Path(__file__).resolve().parents[1]


class _HtmlCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.attrs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        for key, value in attrs:
            if value is not None:
                self.attrs.append((key, value))


class ReviewRoomHtmlTests(unittest.TestCase):
    def test_rendered_html_contains_review_room_sections(self) -> None:
        html = render_review_room_html(build_review_room())

        self.assertIn("InferenceAtlas Agent Access Review Room", html)
        self.assertIn("Scenario Matrix", html)
        self.assertIn("Policy Gate", html)
        self.assertIn("Sponsor Adapter Status", html)
        self.assertIn("Permission Envelope", html)
        self.assertIn("Private engine, public proof.", html)

    def test_rendered_html_has_no_external_assets(self) -> None:
        html = render_review_room_html(build_review_room())
        parser = _HtmlCollector()
        parser.feed(html)

        self.assertIn("style", parser.tags)
        self.assertNotIn("script", parser.tags)
        for key, value in parser.attrs:
            if key in {"src", "href"}:
                self.assertFalse(value.startswith(("http://", "https://", "//")), msg=value)

    def test_write_review_room_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_review_room_html(Path(temp_dir))

            self.assertEqual(path.name, "review_room.html")
            self.assertIn("admin_code_fix_bot", path.read_text(encoding="utf-8"))

    def test_review_room_cli_writes_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-m", "agent.review_room", "--output-dir", temp_dir],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            html_path = Path(temp_dir) / "review_room.html"
            self.assertTrue(html_path.exists())
            self.assertIn("review_room.html", result.stdout)


if __name__ == "__main__":
    unittest.main()
