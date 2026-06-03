import json
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_TOUR = ROOT / "docs" / "PRODUCT_TOUR.md"
POSITIONING_SENTENCE = (
    "Every agent demo shows the agent taking action. "
    "InferenceAtlas shows the proof packet before an agent is allowed to act."
)


class ProductTourTests(unittest.TestCase):
    def test_product_tour_is_product_first_review_path(self) -> None:
        tour = PRODUCT_TOUR.read_text(encoding="utf-8")

        for expected in [
            "# Product Tour",
            "Status: public product evaluation path",
            POSITIONING_SENTENCE,
            "Private engine, public proof.",
            "Five-Minute Product Trial",
            "python3 -m agent.judge",
            "python3 -m agent.proof_health",
            "python3 -m agent.sponsor_readiness",
            "python3 -m agent.trial examples/requests/support_triage_trial.yml",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_agent.proof_health.md",
            "Packet Drift",
            "sponsor live-readiness report",
            "What Is Fixed Versus Derived",
            "fixed fixtures make review reproducible; derived outputs make the product claim testable",
            "This public harness does not approve access.",
        ]:
            self.assertIn(expected, tour)

    def test_product_tour_preserves_private_boundary(self) -> None:
        tour = PRODUCT_TOUR.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, tour, msg=f"{forbidden} leaked in docs/PRODUCT_TOUR.md")

    def test_manifest_and_review_surfaces_point_to_product_tour(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["product_tour"], "docs/PRODUCT_TOUR.md")
        self.assertEqual(manifest["primary_artifacts"]["product_tour"], "docs/PRODUCT_TOUR.md")
        self.assertIn("docs/PRODUCT_TOUR.md", manifest["judge_review_path"])
        self.assertIn("docs/PRODUCT_TOUR.md", manifest["product_review_path"])
        self.assertIn("product tour", manifest["private_v1_boundary"]["public_proof_surface"])

        for surface in [readme, agents, guide]:
            self.assertIn("docs/PRODUCT_TOUR.md", surface)


if __name__ == "__main__":
    unittest.main()
