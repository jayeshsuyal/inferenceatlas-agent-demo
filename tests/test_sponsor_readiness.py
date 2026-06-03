import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.adapters import ADAPTER_NAMES
from agent.sponsor_readiness import (
    SPONSOR_READINESS_SCHEMA_VERSION,
    build_sponsor_live_readiness,
    render_sponsor_live_readiness_markdown,
    write_sponsor_live_readiness_artifacts,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class SponsorReadinessTests(unittest.TestCase):
    def _run_readiness(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "agent.sponsor_readiness", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_report_names_all_sponsors_without_approval_power(self) -> None:
        report = build_sponsor_live_readiness()

        self.assertEqual(report["schema_version"], SPONSOR_READINESS_SCHEMA_VERSION)
        self.assertEqual(report["mode"], "offline_readiness_contract")
        self.assertEqual({provider["provider"] for provider in report["providers"]}, set(ADAPTER_NAMES))
        self.assertTrue(report["summary"]["all_contracts_ready"])
        self.assertFalse(report["summary"]["default_path_requires_keys"])
        self.assertTrue(report["summary"]["all_non_executing"])
        self.assertTrue(report["summary"]["all_non_approving"])
        self.assertTrue(report["summary"]["all_non_granting"])
        self.assertTrue(report["summary"]["all_non_mutating"])
        self.assertTrue(report["summary"]["human_review_required"])
        self.assertFalse(report["default_public_boundary"]["live_calls_made"])
        self.assertFalse(report["default_public_boundary"]["approves_access"])
        self.assertFalse(report["default_public_boundary"]["grants_permissions"])
        self.assertFalse(report["default_public_boundary"]["executes_external_writes"])
        self.assertFalse(report["default_public_boundary"]["mutates_production"])

    def test_default_report_does_not_inspect_environment(self) -> None:
        report = build_sponsor_live_readiness()

        self.assertFalse(report["environment_inspected"])
        for provider in report["providers"]:
            self.assertFalse(provider["env"]["inspected"])
            self.assertEqual(provider["env"]["configured_vars"], [])
            self.assertEqual(provider["env"]["missing_vars"], [])

    def test_inspect_env_reports_variable_names_only(self) -> None:
        report = build_sponsor_live_readiness(inspect_env=True)

        self.assertTrue(report["environment_inspected"])
        for provider in report["providers"]:
            self.assertTrue(provider["env"]["inspected"])
            self.assertIn("note", provider["env"])
            self.assertNotIn("value", provider["env"])

    def test_markdown_is_public_safe_and_skim_ready(self) -> None:
        markdown = render_sponsor_live_readiness_markdown(build_sponsor_live_readiness())

        for expected in [
            "# Sponsor Live Readiness",
            "Private engine, public proof.",
            "Sponsor tools enrich proof; they do not approve access.",
            "Provider Readiness",
            "composio",
            "tavily",
            "nebius",
            "openclaw",
            "Sponsor tools are proof contributors, not approval authorities.",
        ]:
            self.assertIn(expected, markdown)

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, markdown, msg=f"{forbidden} leaked in sponsor readiness markdown")

    def test_writes_markdown_and_json_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_sponsor_live_readiness_artifacts(output_dir=Path(temp_dir))

            self.assertEqual(
                {path.name for path in written},
                {"sponsor_live_readiness.json", "sponsor_live_readiness.md"},
            )
            payload = json.loads((Path(temp_dir) / "sponsor_live_readiness.json").read_text())
            markdown = (Path(temp_dir) / "sponsor_live_readiness.md").read_text()
            self.assertEqual(payload["schema_version"], SPONSOR_READINESS_SCHEMA_VERSION)
            self.assertIn("Provider Readiness", markdown)

    def test_cli_renders_markdown_and_json_without_writes(self) -> None:
        markdown_result = self._run_readiness("--no-write")
        json_result = self._run_readiness("--no-write", "--json")

        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Sponsor Live Readiness", markdown_result.stdout)
        self.assertIn("all non-approving: True", markdown_result.stdout)

        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertTrue(payload["summary"]["all_contracts_ready"])
        self.assertFalse(payload["default_public_boundary"]["approves_access"])


if __name__ == "__main__":
    unittest.main()
