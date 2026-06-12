"""Structured repo index store and reports."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.repo_index_store import (
    build_index_report,
    build_manifest_paths,
    list_chunks,
    load_preindex_manifest,
    load_report,
    save_chunk,
    save_manifest,
    save_report,
)


class RepoIndexStoreTests(unittest.TestCase):
    def test_preindex_manifest_loads(self) -> None:
        manifest = load_preindex_manifest("inferenceatlas/support-triage-trial")
        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertTrue(manifest.get("preindexed"))

    def test_preindex_report_has_charts(self) -> None:
        report = load_report("inferenceatlas/support-triage-trial")
        self.assertIsNotNone(report)
        assert report is not None
        self.assertIn("category_chart", report)
        self.assertIn("tier_chart", report)
        self.assertIn("completeness_pct", report)

    def test_save_manifest_and_chunks_in_temp_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            with patch("agent.repo_index_store.INDEX_STORE_DIR", store):
                save_manifest("org/demo", {"paths": build_manifest_paths(["README.md", "src/a.py"]), "total_paths": 2})
                save_chunk("org/demo", "README.md", "hello", tier="tier0")
                chunks = list_chunks("org/demo")
                self.assertEqual(len(chunks), 1)
                report = build_index_report("org/demo", load_preindex_manifest("org/demo") or {"paths": build_manifest_paths(["README.md"]), "total_paths": 1}, chunks)
                save_report("org/demo", report)
                saved = json.loads((store / "org__demo" / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["schema_version"], "repo_index_report.v1")


if __name__ == "__main__":
    unittest.main()
