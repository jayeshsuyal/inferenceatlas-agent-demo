import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.trial import (
    DEFAULT_TRIAL_REQUEST,
    TRIAL_REPORT_SCHEMA_VERSION,
    build_trial_report,
    load_trial_request,
    render_trial_report_markdown,
    trial_request_to_access_request,
    validate_trial_request,
    write_trial_artifacts,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class TrialRunnerTests(unittest.TestCase):
    def _run_trial(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.trial", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_support_triage_trial_request_parses_to_access_request(self) -> None:
        payload = load_trial_request(DEFAULT_TRIAL_REQUEST)
        access_request = trial_request_to_access_request(payload)

        self.assertEqual(payload["schema_version"], "design_partner_trial_request.v0")
        self.assertEqual(access_request.agent_name, "support triage agent")
        self.assertEqual(access_request.environment, "stage")
        self.assertEqual(
            [tool.system for tool in access_request.requested_tools],
            ["GitHub", "Slack", "Jira"],
        )
        self.assertIn("customer incident context", access_request.data_classes)

    def test_trial_report_routes_sample_without_granting_access(self) -> None:
        report = build_trial_report(DEFAULT_TRIAL_REQUEST)

        self.assertEqual(report["schema_version"], TRIAL_REPORT_SCHEMA_VERSION)
        self.assertEqual(report["request_readiness"], "ready_for_scoped_trial")
        self.assertEqual(report["candidate_agent"]["name"], "support_triage_agent")
        self.assertEqual(report["access_speed_lane"]["lane"], "proof_routed_scoped_validation")
        self.assertFalse(report["decision_brief_summary"]["production_access"])
        self.assertTrue(report["decision_brief_summary"]["scoped_validation_review"])
        self.assertFalse(report["safety"]["public_runner_approves_access"])
        self.assertFalse(report["safety"]["public_runner_grants_permissions"])
        self.assertFalse(report["safety"]["public_runner_executes_external_writes"])
        self.assertEqual(report["validation"]["errors"], [])
        self.assertGreater(report["packet_summary"]["missing_proof_count"], 0)

    def test_template_placeholders_are_warnings_not_runtime_grants(self) -> None:
        template_path = ROOT / "examples" / "requests" / "design_partner_trial.yml"
        text = template_path.read_text(encoding="utf-8")
        payload = load_trial_request(template_path)
        validation = validate_trial_request(payload, source_text=text)

        self.assertEqual(validation["errors"], [])
        self.assertTrue(validation["warnings"])
        self.assertTrue(any("template placeholder" in warning for warning in validation["warnings"]))

    def test_trial_markdown_is_skim_ready(self) -> None:
        markdown = render_trial_report_markdown(build_trial_report(DEFAULT_TRIAL_REQUEST))

        for expected in [
            "# Design Partner Trial Report",
            "Private engine, public proof.",
            "proof_routed_scoped_validation",
            "production access: False",
            "approves access: False",
            "grants permissions: False",
            "GitHub repository allowlist",
            "Security/Legal",
        ]:
            self.assertIn(expected, markdown)

    def test_trial_cli_outputs_markdown_and_json(self) -> None:
        markdown_result = self._run_trial("examples/requests/support_triage_trial.yml")
        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Design Partner Trial Report", markdown_result.stdout)
        self.assertIn("proof_routed_scoped_validation", markdown_result.stdout)

        json_result = self._run_trial("examples/requests/support_triage_trial.yml", "--json")
        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        report = json.loads(json_result.stdout)
        self.assertEqual(report["access_speed_lane"]["lane"], "proof_routed_scoped_validation")
        self.assertFalse(report["safety"]["public_runner_approves_access"])

    def test_write_trial_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_trial_artifacts(DEFAULT_TRIAL_REQUEST, Path(temp_dir))
            names = {path.name for path in paths}

            self.assertEqual(
                names,
                {
                    "support_triage_trial_report.md",
                    "support_triage_trial_report.json",
                    "support_triage_trial.packet.md",
                    "support_triage_trial.packet.json",
                    "support_triage_trial.decision_brief.md",
                    "support_triage_trial.decision_brief.json",
                },
            )
            report = json.loads((Path(temp_dir) / "support_triage_trial_report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(report["written_artifacts"]), 6)

    def test_trial_cli_write_outputs_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self._run_trial(
                "examples/requests/support_triage_trial.yml",
                "--write",
                "--output-dir",
                temp_dir,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("support_triage_trial_report.md", result.stdout)
            self.assertTrue((Path(temp_dir) / "support_triage_trial_report.json").exists())

    def test_trial_surfaces_preserve_private_boundary(self) -> None:
        generated = [
            render_trial_report_markdown(build_trial_report(DEFAULT_TRIAL_REQUEST)),
            json.dumps(build_trial_report(DEFAULT_TRIAL_REQUEST), sort_keys=True),
        ]

        for surface in generated:
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, surface)


if __name__ == "__main__":
    unittest.main()
