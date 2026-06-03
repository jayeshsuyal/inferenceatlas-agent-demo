import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.proof_health import (
    PROOF_HEALTH_SCHEMA_VERSION,
    build_proof_health_report,
    render_proof_health_markdown,
    write_proof_health_artifacts,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class ProofHealthTests(unittest.TestCase):
    def _run_proof_health(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.proof_health", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_report_tracks_packet_lifecycle_without_approval_power(self) -> None:
        report = build_proof_health_report()

        self.assertEqual(report["schema_version"], PROOF_HEALTH_SCHEMA_VERSION)
        self.assertEqual(report["mode"], "offline_deterministic")
        self.assertEqual(report["scenario"], "support_triage_agent")
        self.assertEqual(report["overall_status"], "drifting")
        self.assertEqual(report["overall_score"], 67)
        self.assertEqual(report["next_human_health_check"], "day_30_security_engineering_review")
        self.assertTrue(report["proof_health_summary"]["human_review_required"])
        self.assertEqual(
            [item["status"] for item in report["health_timeline"]],
            ["current", "drifting", "stale"],
        )
        self.assertEqual(
            [item["score"] for item in report["health_timeline"]],
            [84, 67, 42],
        )
        self.assertFalse(report["source_review_state"]["production_access"])
        self.assertTrue(report["source_review_state"]["scoped_validation_review"])
        self.assertFalse(report["source_review_state"]["external_writes"])
        self.assertTrue(report["source_review_state"]["composio_dry_run"])
        self.assertFalse(report["safety_boundary"]["approves_access"])
        self.assertFalse(report["safety_boundary"]["grants_permissions"])
        self.assertFalse(report["safety_boundary"]["executes_external_writes"])
        self.assertFalse(report["safety_boundary"]["mutates_production"])
        self.assertTrue(report["safety_boundary"]["requires_human_review"])

    def test_markdown_is_skim_ready_and_public_safe(self) -> None:
        markdown = render_proof_health_markdown(build_proof_health_report())

        for expected in [
            "# Proof Health: support_triage_agent",
            "Private engine, public proof.",
            "Packet Drift Timeline",
            "Drifted Facts",
            "Stale Assumptions",
            "Expired Reviewer Gates",
            "next human health check",
            "Proof Health does not approve access.",
        ]:
            self.assertIn(expected, markdown)

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, markdown, msg=f"{forbidden} leaked in Proof Health markdown")

    def test_writes_markdown_and_json_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_proof_health_artifacts(output_dir=Path(temp_dir))
            written_names = {path.name for path in written}

            self.assertEqual(
                written_names,
                {
                    "support_triage_agent.proof_health.json",
                    "support_triage_agent.proof_health.md",
                },
            )
            payload = json.loads((Path(temp_dir) / "support_triage_agent.proof_health.json").read_text())
            markdown = (Path(temp_dir) / "support_triage_agent.proof_health.md").read_text()

            self.assertEqual(payload["schema_version"], PROOF_HEALTH_SCHEMA_VERSION)
            self.assertIn("Packet Drift Timeline", markdown)

    def test_cli_renders_markdown_and_json_without_writes(self) -> None:
        markdown_result = self._run_proof_health("--no-write")
        json_result = self._run_proof_health("--no-write", "--json")

        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Proof Health: support_triage_agent", markdown_result.stdout)
        self.assertIn("Packet Drift Timeline", markdown_result.stdout)

        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["overall_status"], "drifting")
        self.assertFalse(payload["safety_boundary"]["approves_access"])

    def test_cli_writes_to_custom_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self._run_proof_health("--output-dir", temp_dir)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((Path(temp_dir) / "support_triage_agent.proof_health.json").exists())
            self.assertTrue((Path(temp_dir) / "support_triage_agent.proof_health.md").exists())


if __name__ == "__main__":
    unittest.main()
