"""Repo index relevance scoring."""

from __future__ import annotations

import unittest

from agent.repo_index_scoring import (
    categorize_path,
    path_matches_patterns,
    patterns_for_stage,
    pick_scored_paths,
    score_path,
)


class RepoIndexScoringTests(unittest.TestCase):
    def test_readme_scores_highest(self) -> None:
        self.assertGreater(score_path("README.md"), score_path("node_modules/foo/bar.py"))

    def test_ci_paths_categorized(self) -> None:
        self.assertEqual(categorize_path(".github/workflows/smoke.yml"), "ci_cd")

    def test_pick_scored_paths_orders_by_score(self) -> None:
        paths = ["README.md", "src/utils.py", ".github/workflows/ci.yml", "node_modules/x/a.js"]
        ranked = pick_scored_paths(paths, limit=3)
        self.assertEqual(ranked[0]["path"], "README.md")
        self.assertTrue(all(row["score"] >= 20 for row in ranked))

    def test_stage_patterns_for_proof(self) -> None:
        patterns = patterns_for_stage("proof_attached")
        self.assertIn("rollback", patterns)
        self.assertTrue(path_matches_patterns(".github/workflows/deploy.yml", patterns))

    def test_skip_vendor_paths(self) -> None:
        self.assertLess(score_path("node_modules/pkg/index.js"), 0)


if __name__ == "__main__":
    unittest.main()
