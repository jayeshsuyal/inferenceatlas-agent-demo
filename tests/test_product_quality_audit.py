import json
import unittest
from pathlib import Path

from agent.judge import build_judge_report, render_judge_report_markdown
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "PRODUCT_QUALITY_AUDIT.md"


class ProductQualityAuditTests(unittest.TestCase):
    def test_product_quality_audit_names_premium_spine(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for expected in [
            "# Product Quality Audit",
            "Status: public product-quality guardrail",
            "Private engine, public proof.",
            "Premium Spine",
            "DecisionPacket",
            "Packet Diff",
            "Agent Access Decision Brief",
            "Trust Receipt",
            "Packet Outcome Memo",
            "Artifact Integrity Gate",
            "Review Room",
            "Proof Health",
            "Sponsor Live Readiness",
            "Design Partner Trial Runner",
            "Agentic Review Expected Output",
            "No landing-page drift in this repo lane.",
            "Sponsor tools contribute proof, not approval authority.",
            "production access stays blocked in the public harness.",
            "Design Partner Outcome Memo",
        ]:
            self.assertIn(expected, doc)

    def test_premium_spine_order_is_reviewable(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        expected_order = [
            "README.md",
            "docs/PRODUCT_TOUR.md",
            "docs/PRODUCT_QUALITY_AUDIT.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
            "python3 -m agent.judge",
            "examples/generated/packet_diff.md",
            "examples/generated/support_triage_agent.outcome_memo.md",
            "python3 -m agent.verify_artifacts",
            "examples/generated/review_room.html",
            "examples/generated/trust_receipt.md",
            "examples/generated/support_triage_agent.proof_health.md",
            "examples/generated/sponsor_live_readiness.md",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/generated/support_triage_trial_report.md",
        ]

        positions = [doc.index(item) for item in expected_order]
        self.assertEqual(positions, sorted(positions))

    def test_product_quality_audit_preserves_private_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, doc, msg=f"{forbidden} leaked in docs/PRODUCT_QUALITY_AUDIT.md")

    def test_manifest_and_review_surfaces_point_to_product_quality_audit(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")
        tour = (ROOT / "docs" / "PRODUCT_TOUR.md").read_text(encoding="utf-8")
        expected_output = (ROOT / "docs" / "AGENTIC_REVIEW_EXPECTED_OUTPUT.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["product_quality_audit"], "docs/PRODUCT_QUALITY_AUDIT.md")
        self.assertEqual(
            manifest["primary_artifacts"]["product_quality_audit"],
            "docs/PRODUCT_QUALITY_AUDIT.md",
        )
        self.assertIn("docs/PRODUCT_QUALITY_AUDIT.md", manifest["product_review_path"])
        self.assertIn("docs/PRODUCT_QUALITY_AUDIT.md", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.verify_artifacts", manifest["product_review_path"])
        self.assertIn("product quality audit", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("artifact integrity gate", manifest["private_v1_boundary"]["public_proof_surface"])

        for surface in [readme, agents, guide, tour, expected_output]:
            self.assertIn("docs/PRODUCT_QUALITY_AUDIT.md", surface)
            self.assertIn("python3 -m agent.verify_artifacts", surface)

    def test_judge_harness_names_product_quality_audit(self) -> None:
        report = build_judge_report(write_artifacts=False)
        artifact_paths = {item["path"] for item in report["artifact_checklist"]}
        markdown = render_judge_report_markdown(report)

        self.assertIn("docs/PRODUCT_QUALITY_AUDIT.md", artifact_paths)
        self.assertIn("docs/PRODUCT_QUALITY_AUDIT.md", markdown)


if __name__ == "__main__":
    unittest.main()
