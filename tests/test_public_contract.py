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
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_LEAD = (
    "Before an AI agent receives access to tools, data, spend, or production systems, "
    "a pre-permission proof packet should exist. This document defines the public conformance "
    "contract for that packet: what must be shown, what must stay blocked, what evidence must "
    "remain visible, and how reviewer gates are represented. InferenceAtlas v1 implements a "
    "private canonical engine. This public contract is the minimum proof surface every "
    "agent-access review implementation can be measured against. Private engine, public proof."
)


class PublicContractTests(unittest.TestCase):
    def test_contract_doc_exists_and_opens_with_authority_lead(self) -> None:
        contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")

        self.assertTrue((ROOT / "docs" / "CONTRACT.md").exists())
        self.assertTrue(contract.startswith("# Public Conformance Contract\n\n" + CONTRACT_LEAD))
        for expected in [
            "## Public Packet Contract",
            "## Public Brief Contract",
            "## What Must Be Shown",
            "## What Must Stay Blocked",
            "## Reviewer Gates",
            "## Conformance",
            "## Sponsor Adapter Boundary",
            "## Private Boundary",
            "python3 -m agent.contract --all",
            "python3 -m agent.contract --all --generated-dir examples/generated",
            "Public contract: agent_access_public.v0",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, contract)

    def test_contract_doc_passes_private_boundary(self) -> None:
        contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, contract, msg=f"{forbidden} leaked in docs/CONTRACT.md")

    def test_manifest_exposes_public_contract_doc(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["public_contract_doc"], "docs/CONTRACT.md")
        self.assertEqual(manifest["primary_artifacts"]["public_contract"], "docs/CONTRACT.md")
        self.assertIn("public contract", manifest["private_v1_boundary"]["public_proof_surface"])

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
