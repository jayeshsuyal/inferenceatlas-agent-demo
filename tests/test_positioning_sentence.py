import json
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
POSITIONING_SENTENCE = (
    "Every agent demo shows the agent taking action. "
    "InferenceAtlas shows the proof packet before an agent is allowed to act."
)

CANONICAL_TEXT_SURFACES = [
    "README.md",
    "AGENTS.md",
    "docs/JUDGE_REVIEW_GUIDE.md",
    "docs/DESIGN_PARTNER_BRIEF.md",
]

SAFETY_ANCHORS = [
    "does not approve access",
    "does not grant",
    "production access stays blocked",
    "humans need to review",
    "not an approval",
    '"approves_access": false',
]


class PositioningSentenceTests(unittest.TestCase):
    def test_positioning_sentence_appears_verbatim_in_canonical_surfaces(self) -> None:
        for relative_path in CANONICAL_TEXT_SURFACES:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(POSITIONING_SENTENCE, text, msg=f"missing positioning sentence in {relative_path}")

        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["thesis_sentence"], POSITIONING_SENTENCE)

    def test_positioning_sentence_is_readme_top_fold(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        first_screen = "\n".join(readme.splitlines()[:16])

        self.assertIn("Private engine, public proof.", first_screen)
        self.assertIn(POSITIONING_SENTENCE, first_screen)
        self.assertLess(first_screen.index("Private engine, public proof."), first_screen.index(POSITIONING_SENTENCE))

    def test_positioning_surfaces_keep_safety_anchor(self) -> None:
        surfaces = CANONICAL_TEXT_SURFACES + ["AI_JUDGE_MANIFEST.json"]

        for relative_path in surfaces:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertTrue(
                any(anchor in text for anchor in SAFETY_ANCHORS),
                msg=f"missing safety anchor in positioning surface {relative_path}",
            )

    def test_positioning_surfaces_preserve_private_boundary(self) -> None:
        surfaces = CANONICAL_TEXT_SURFACES + ["AI_JUDGE_MANIFEST.json", "docs/CONTRACT.md"]

        for relative_path in surfaces:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, text, msg=f"{forbidden} leaked in {relative_path}")

    def test_manifest_safety_defaults_stay_conservative(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertFalse(manifest["safety"]["approves_access"])
        self.assertFalse(manifest["safety"]["grants_permissions"])
        self.assertFalse(manifest["safety"]["external_writes_default"])
        self.assertTrue(manifest["safety"]["composio_dry_run_default"])
        self.assertTrue(manifest["safety"]["requires_human_approval"])


if __name__ == "__main__":
    unittest.main()
