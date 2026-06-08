import json
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs" / "DEMO_RECORDING_SCRIPT.md"


class DemoRecordingScriptTests(unittest.TestCase):
    def test_demo_recording_script_locks_recording_gate_and_talk_track(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")

        for expected in [
            "# Demo Recording Script",
            "Status: public recording checklist",
            "Private engine, public proof.",
            "## Freeze Gate",
            "## 90-Second Talk Track",
            "Every agent demo shows the agent taking action.",
            "AI movement is cross-functional.",
            "/packet?fixture=mcp_tool_blast_radius&autorun=1",
            "IA did not approve. The next human action is named above.",
            "Sponsor tools collect proof; they do not approve, grant, write, spend, select providers, or mutate production.",
            "Portkey export is dry-run in this public demo; no API call is made.",
            "Ask IA explains the packet; it does not replace the packet.",
            "The script has been rehearsed at least twice.",
            "After this gate passes, do not add product features unless a demo-blocking bug appears.",
            "The backup story is the same: one packet, sponsor proof, downstream gate, team review, human export.",
        ]:
            self.assertIn(expected, script)

    def test_demo_recording_script_names_four_packet_backed_ask_ia_prompts(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")

        for expected in [
            "Can this move?",
            "What proof is missing?",
            "Who reviews this?",
            "Can Portkey allow this spend?",
        ]:
            self.assertIn(expected, script)

    def test_demo_recording_script_preserves_safety_and_private_boundary(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, script, msg=f"{forbidden} leaked in demo recording script")

        for forbidden_overclaim in [
            "IA approved",
            "IA grants",
            "IA wrote",
            "IA selected the provider",
            "IA guaranteed savings",
            "Portkey live mutation",
            "Sponsor tools approve",
        ]:
            self.assertNotIn(forbidden_overclaim, script)

    def test_manifest_and_readme_expose_demo_recording_script(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["demo_recording_script"], "docs/DEMO_RECORDING_SCRIPT.md")
        self.assertEqual(manifest["primary_artifacts"]["demo_recording_script"], "docs/DEMO_RECORDING_SCRIPT.md")
        self.assertEqual(manifest["verification"]["demo_recording_script"], "test -s docs/DEMO_RECORDING_SCRIPT.md")
        self.assertIn("demo recording script", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("docs/DEMO_RECORDING_SCRIPT.md", readme)


if __name__ == "__main__":
    unittest.main()
