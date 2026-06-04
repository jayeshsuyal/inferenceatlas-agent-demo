import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.verify_artifacts import render_verify_report, verify_artifacts


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "examples" / "generated"


class VerifyArtifactsTests(unittest.TestCase):
    def test_checked_in_generated_artifacts_are_fresh(self) -> None:
        report = verify_artifacts()

        self.assertEqual(report["schema_version"], "artifact_integrity_report.v0")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["summary"]["generated_artifacts_verified"], 33)
        self.assertEqual(report["summary"]["stale_artifacts"], 0)
        self.assertEqual(report["summary"]["static_assets_checked"], 2)
        self.assertEqual(report["summary"]["missing_static_assets"], 0)
        self.assertEqual(report["summary"]["unexpected_checked_in_artifacts"], 0)

    def test_verifier_catches_stale_artifact_with_first_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_dir = Path(temp_dir) / "generated"
            shutil.copytree(GENERATED, actual_dir)
            stale_path = actual_dir / "support_triage_agent.packet.md"
            stale_path.write_text(
                stale_path.read_text(encoding="utf-8").replace(
                    "Do not approve production tool access yet.",
                    "Approve production tool access now.",
                    1,
                ),
                encoding="utf-8",
            )

            report = verify_artifacts(actual_dir)
            rendered = render_verify_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["stale_artifacts"], 1)
        self.assertIn("x STALE: examples/generated/support_triage_agent.packet.md", rendered)
        self.assertIn("examples/generated/support_triage_agent.packet.md", rendered)
        self.assertIn("First difference", rendered)
        self.assertIn("Regenerate with:", rendered)

    def test_verifier_catches_missing_static_review_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_dir = Path(temp_dir) / "generated"
            shutil.copytree(GENERATED, actual_dir)
            (actual_dir / "review_room.desktop.jpg").unlink()

            report = verify_artifacts(actual_dir)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["missing_static_assets"], 1)
        self.assertEqual(
            report["failures"]["missing_static_assets"][0]["path"],
            "examples/generated/review_room.desktop.jpg",
        )

    def test_verifier_catches_invalid_static_review_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_dir = Path(temp_dir) / "generated"
            shutil.copytree(GENERATED, actual_dir)
            screenshot = actual_dir / "review_room.desktop.jpg"
            screenshot.unlink()
            screenshot.mkdir()

            report = verify_artifacts(actual_dir)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["missing_static_assets"], 1)
        self.assertEqual(report["failures"]["missing_static_assets"][0]["status"], "invalid")
        self.assertEqual(
            report["failures"]["missing_static_assets"][0]["path"],
            "examples/generated/review_room.desktop.jpg",
        )

    def test_verifier_catches_unexpected_checked_in_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_dir = Path(temp_dir) / "generated"
            shutil.copytree(GENERATED, actual_dir)
            (actual_dir / "old_removed_artifact.json").write_text("{}\n", encoding="utf-8")

            report = verify_artifacts(actual_dir)
            rendered = render_verify_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["unexpected_checked_in_artifacts"], 1)
        self.assertEqual(
            report["unexpected_checked_in_artifacts"],
            ["examples/generated/old_removed_artifact.json"],
        )
        self.assertIn(
            "x UNEXPECTED CHECKED-IN ARTIFACT: examples/generated/old_removed_artifact.json",
            rendered,
        )

    def test_verifier_reports_missing_actual_directory_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_dir = Path(temp_dir) / "missing-generated"

            report = verify_artifacts(actual_dir)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["stale_artifacts"], 33)
        self.assertEqual(report["summary"]["missing_static_assets"], 2)

    def test_verify_artifacts_cli_json_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.verify_artifacts", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["summary"]["stale_artifacts"], 0)

    def test_verify_artifacts_cli_text_is_skim_ready(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.verify_artifacts"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("# Artifact Integrity Gate", result.stdout)
        self.assertIn("Packet artifacts (6 files): OK", result.stdout)
        self.assertIn("Design Partner Trial (6 files): OK", result.stdout)
        self.assertIn("Total: 33 generated artifacts verified", result.stdout)
        self.assertIn("0 unexpected checked-in", result.stdout)


if __name__ == "__main__":
    unittest.main()
