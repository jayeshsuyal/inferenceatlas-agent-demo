import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.packet_authority import (
    PACKET_AUTHORITY_SNAPSHOT_SCHEMA_VERSION,
    assert_decision_lock_not_weakened,
    build_packet_authority_snapshot,
    derive_decision_lock,
)
from agent.scenarios import SCENARIOS, build_scenario_packet
from agent.verification import build_verification_artifact, verification_has_failures
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS, PUBLIC_PACKET_AUTHORITY_TERMS


ROOT = Path(__file__).resolve().parents[1]


class PacketAuthoritySnapshotTests(unittest.TestCase):
    def test_packet_authority_terms_are_public_boundary_terms(self) -> None:
        self.assertFalse(PUBLIC_PACKET_AUTHORITY_TERMS & set(FORBIDDEN_PRIVATE_V1_TERMS))

    def test_snapshot_is_deterministic_and_hash_backed(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        first = build_packet_authority_snapshot(packet)
        second = build_packet_authority_snapshot(packet)

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], PACKET_AUTHORITY_SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(first["packet_id"], packet["packet_id"])
        self.assertTrue(first["revision_id"].startswith("rev_"))
        self.assertEqual(len(first["revision_id"]), len("rev_") + 16)
        self.assertTrue(first["content_hash"].startswith("sha256:"))
        self.assertEqual(len(first["content_hash"]), len("sha256:") + 64)
        self.assertEqual(first["decision_lock_before"], "scoped_validation_only")
        self.assertEqual(first["decision_lock_after"], "scoped_validation_only")
        self.assertEqual(first["evidence_receipt_ids"], [])
        self.assertIn("safety_state.approval_granted", first["locked_fields"])

    def test_snapshot_revision_changes_when_packet_content_changes(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        changed = copy.deepcopy(packet)
        changed["missing_proof"].append(
            {
                "item": "Finance validates the AI budget baseline",
                "owner": "Procurement/Finance",
                "unblocks": "spend review packet",
            }
        )

        original_snapshot = build_packet_authority_snapshot(packet)
        changed_snapshot = build_packet_authority_snapshot(changed)

        self.assertNotEqual(original_snapshot["revision_id"], changed_snapshot["revision_id"])
        self.assertNotEqual(original_snapshot["content_hash"], changed_snapshot["content_hash"])
        self.assertEqual(original_snapshot["packet_id"], changed_snapshot["packet_id"])

    def test_lock_states_cover_the_three_public_risk_lanes(self) -> None:
        self.assertEqual(derive_decision_lock(build_scenario_packet("support_triage_agent")), "scoped_validation_only")
        self.assertEqual(derive_decision_lock(build_scenario_packet("read_only_analytics_agent")), "read_only_validation")
        self.assertEqual(derive_decision_lock(build_scenario_packet("admin_code_fix_bot")), "blocked")

    def test_snapshot_rejects_decision_lock_weakening(self) -> None:
        with self.assertRaises(ValueError):
            assert_decision_lock_not_weakened("blocked", "scoped_validation_only")

        with self.assertRaises(ValueError):
            build_packet_authority_snapshot(
                build_scenario_packet("support_triage_agent"),
                decision_lock_before="blocked",
            )

    def test_verification_artifacts_never_claim_public_approval(self) -> None:
        for scenario_name in SCENARIOS:
            packet = build_scenario_packet(scenario_name)
            snapshot = build_packet_authority_snapshot(packet)
            artifact = build_verification_artifact(packet, snapshot=snapshot)

            self.assertEqual(artifact["verification_status"], "valid_review_required")
            self.assertFalse(artifact["production_access"])
            self.assertFalse(artifact["external_writes"])
            self.assertFalse(artifact["permission_grants"])
            self.assertFalse(artifact["approval_granted"])
            self.assertFalse(verification_has_failures(artifact))
            self.assertEqual(artifact["packet_id"], packet["packet_id"])
            self.assertEqual(artifact["revision_id"], snapshot["revision_id"])

    def test_snapshot_and_verification_cli_are_machine_readable(self) -> None:
        snapshot_result = subprocess.run(
            [sys.executable, "-m", "agent.packet_authority", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(snapshot_result.returncode, 0, msg=snapshot_result.stderr)
        snapshot = json.loads(snapshot_result.stdout)
        self.assertEqual(snapshot["schema_version"], PACKET_AUTHORITY_SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(snapshot["decision_lock_after"], "scoped_validation_only")

        verify_result = subprocess.run(
            [sys.executable, "-m", "agent.verification", "--all", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(verify_result.returncode, 0, msg=verify_result.stderr)
        payload = json.loads(verify_result.stdout)
        self.assertEqual(len(payload["results"]), len(SCENARIOS))
        self.assertTrue(all(item["verification_status"] == "valid_review_required" for item in payload["results"]))
        self.assertTrue(all(item["production_access"] is False for item in payload["results"]))

    def test_snapshot_and_verification_preserve_private_boundary(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        snapshot = build_packet_authority_snapshot(packet)
        artifact = build_verification_artifact(packet, snapshot=snapshot)
        combined = json.dumps({"snapshot": snapshot, "verification": artifact}, sort_keys=True)

        private_engine_terms = [
            term for term in FORBIDDEN_PRIVATE_V1_TERMS if term not in PUBLIC_PACKET_AUTHORITY_TERMS
        ]
        for forbidden in private_engine_terms:
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
