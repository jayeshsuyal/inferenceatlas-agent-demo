import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.trial import build_trial_report, load_trial_request, validate_trial_request
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
CASE_STUDY = ROOT / "docs" / "case_studies" / "MIASMA_PRE_PERMISSION_PACKET.md"
REQUEST = ROOT / "examples" / "requests" / "miasma_pre_permission_packet.yml"

MIASMA_REQUIRED_FRAMING = [
    "worked example based on publicly reported attack vectors",
    "not a security claim about any specific product or vendor",
    "what InferenceAtlas would ask before this scope was granted",
    "the actual incident exploited the absence of this layer",
]

MIASMA_BANNED_FRAMING = [
    "IA detects",
    "IA prevented",
    "IA blocked Miasma",
    "Miasma protection",
    "supply-chain security tool",
]


class MiasmaCaseStudyTests(unittest.TestCase):
    def test_miasma_case_study_holds_operational_governance_framing(self) -> None:
        text = CASE_STUDY.read_text(encoding="utf-8")
        lowered = text.lower()

        for required in MIASMA_REQUIRED_FRAMING:
            self.assertIn(required, text)
        for banned in MIASMA_BANNED_FRAMING:
            self.assertNotIn(banned.lower(), lowered)

        for source in [
            "https://access.redhat.com/security/vulnerabilities/RHSB-2026-006",
            "https://www.microsoft.com/en-us/security/blog/2026/06/02/preinstall-persistence-inside-red-hat-npm-miasma-credential-stealing-campaign/",
            "https://www.wiz.io/blog/miasma-supply-chain-attack-targeting-redhat-npm-packages",
        ]:
            self.assertIn(source, text)

    def test_miasma_fixture_runs_as_non_approving_public_trial(self) -> None:
        source_text = REQUEST.read_text(encoding="utf-8")
        payload = load_trial_request(REQUEST)
        validation = validate_trial_request(payload, source_text=source_text)
        report = build_trial_report(REQUEST)

        self.assertEqual(validation["errors"], [])
        self.assertEqual(validation["warnings"], [])
        self.assertEqual(report["request_readiness"], "ready_for_scoped_trial")
        self.assertEqual(report["access_speed_lane"]["lane"], "proof_routed_scoped_validation")
        self.assertEqual(report["candidate_agent"]["name"], "dependency_release_review_agent")
        self.assertEqual(
            report["packet_summary"]["requested_systems"],
            ["GitHub", "npm registry", "CI/CD", "Developer workstation"],
        )
        self.assertFalse(report["decision_brief_summary"]["production_access"])
        self.assertFalse(report["safety"]["public_runner_approves_access"])
        self.assertFalse(report["safety"]["public_runner_grants_permissions"])
        self.assertFalse(report["safety"]["public_runner_executes_external_writes"])
        self.assertIn("Security", report["reviewer_routing"]["request_roles"]["required"])
        self.assertIn("Release owner", report["reviewer_routing"]["request_roles"]["required"])

    def test_miasma_trial_cli_outputs_json_without_writes(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.trial", "examples/requests/miasma_pre_permission_packet.yml", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["request_path"], "examples/requests/miasma_pre_permission_packet.yml")
        self.assertFalse(payload["safety"]["public_runner_approves_access"])

    def test_miasma_surfaces_preserve_private_boundary(self) -> None:
        for path in [CASE_STUDY, REQUEST]:
            text = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, text, msg=f"{forbidden} leaked in {path}")

    def test_manifest_and_public_docs_link_miasma_case_study(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        product_tour = (ROOT / "docs" / "PRODUCT_TOUR.md").read_text(encoding="utf-8")
        artifact_map = (ROOT / "docs" / "ARTIFACT_MAP.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["miasma_case_study"], "docs/case_studies/MIASMA_PRE_PERMISSION_PACKET.md")
        self.assertEqual(manifest["miasma_case_study_request"], "examples/requests/miasma_pre_permission_packet.yml")
        self.assertEqual(
            manifest["primary_artifacts"]["miasma_case_study"],
            "docs/case_studies/MIASMA_PRE_PERMISSION_PACKET.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["miasma_case_study_request"],
            "examples/requests/miasma_pre_permission_packet.yml",
        )
        self.assertIn("Miasma pre-permission case study", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("docs/case_studies/MIASMA_PRE_PERMISSION_PACKET.md", manifest["judge_review_path"])
        self.assertIn("examples/requests/miasma_pre_permission_packet.yml", manifest["judge_review_path"])

        for surface in [product_tour, artifact_map, guide]:
            self.assertIn("docs/case_studies/MIASMA_PRE_PERMISSION_PACKET.md", surface)
            self.assertIn("examples/requests/miasma_pre_permission_packet.yml", surface)


if __name__ == "__main__":
    unittest.main()
