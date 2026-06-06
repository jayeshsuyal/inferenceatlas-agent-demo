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
            "bash scripts/run.sh",
            "python3 -m agent.judge",
            "python3 -m agent.skills",
            "ia-skills",
            "python3 -m agent.packet_diff",
            "python3 -m agent.outcome_memo",
            "python3 -m agent.proof_health",
            "python3 -m agent.sponsor_readiness",
            "python3 -m agent.trial examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
            "python3 -m agent.verify_artifacts",
            "ia-verify-artifacts",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "examples/generated/packet_diff.md",
            "examples/generated/support_triage_agent.outcome_memo.md",
            "examples/generated/support_triage_agent.proof_health.md",
            "Artifact Integrity Gate",
            "Agent Skills registry",
            "docs/AGENT_SKILLS.md",
            "Packet Diff",
            "Packet Outcome Memo",
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
        self.assertIn("docs/AGENT_SKILLS.md", manifest["product_review_path"])
        self.assertIn("python3 -m agent.skills", manifest["product_review_path"])
        self.assertIn("python3 -m agent.verify_artifacts", manifest["product_review_path"])
        self.assertIn("python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_trial.evidence_replay.md", manifest["product_review_path"])
        self.assertIn("product tour", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("agent skills registry", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("artifact integrity gate", manifest["private_v1_boundary"]["public_proof_surface"])

        for surface in [agents, guide]:
            self.assertIn("docs/PRODUCT_TOUR.md", surface)
            self.assertIn("docs/AGENT_SKILLS.md", surface)
            self.assertIn("python3 -m agent.verify_artifacts", surface)

        self.assertIn("docs/PRODUCT_TOUR.md", readme)
        self.assertIn("docs/AGENT_SKILLS.md", readme)
        self.assertIn("docs/COMMAND_REFERENCE.md", readme)
        self.assertIn("docs/ARTIFACT_MAP.md", readme)


if __name__ == "__main__":
    unittest.main()
