import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.contract import validate_all
from agent.public_contract import (
    PUBLIC_CONTRACT_VERSION,
    validate_public_packet,
    validate_public_review_artifacts,
)
from agent.scenarios import GENERATED_DIR, SCENARIOS, build_scenario_brief, build_scenario_packet


ROOT = Path(__file__).resolve().parents[1]


class PublicContractTests(unittest.TestCase):
    def test_all_in_memory_scenarios_pass_public_contract(self) -> None:
        results = validate_all()

        self.assertEqual(set(results), set(SCENARIOS))
        self.assertTrue(all(errors == [] for errors in results.values()), msg=results)

    def test_all_generated_scenarios_pass_public_contract(self) -> None:
        results = validate_all(generated_dir=GENERATED_DIR)

        self.assertEqual(set(results), set(SCENARIOS))
        self.assertTrue(all(errors == [] for errors in results.values()), msg=results)

    def test_public_review_artifact_pair_requires_matching_ids(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        brief = copy.deepcopy(build_scenario_brief("support_triage_agent"))
        brief["derived_from_packet_id"] = "wrong-packet-id"

        errors = validate_public_review_artifacts(packet, brief)

        self.assertIn("packet.packet_id and brief.derived_from_packet_id: must match", errors)

    def test_validator_rejects_production_access_grant(self) -> None:
        packet = copy.deepcopy(build_scenario_packet("support_triage_agent"))
        packet["approval_posture"]["production_access"] = "approved"
        packet["safety_state"]["approval_granted"] = True

        errors = validate_public_packet(packet)

        self.assertIn("packet.approval_posture.production_access: must be blocked", errors)
        self.assertIn("packet.safety_state.approval_granted: must be false", errors)

    def test_contract_cli_validates_all_scenarios(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.contract", "--all"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"Public contract: {PUBLIC_CONTRACT_VERSION}", result.stdout)
        self.assertIn("- support_triage_agent: OK", result.stdout)
        self.assertIn("- read_only_analytics_agent: OK", result.stdout)
        self.assertIn("- admin_code_fix_bot: OK", result.stdout)

    def test_contract_cli_validates_generated_artifacts_as_json(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agent.contract",
                "--all",
                "--generated-dir",
                str(GENERATED_DIR),
                "--json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["contract_version"], PUBLIC_CONTRACT_VERSION)
        self.assertEqual(payload["results"], {scenario_name: [] for scenario_name in SCENARIOS})


if __name__ == "__main__":
    unittest.main()
