import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.evidence_receipts import (
    EVIDENCE_RECEIPT_LEDGER_SCHEMA_VERSION,
    build_evidence_receipt_ledger,
    ledger_has_failures,
    write_evidence_receipt_artifacts,
)
from agent.packet_authority import build_packet_authority_snapshot_for_scenario
from agent.scenarios import SCENARIOS, build_scenario_packet
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RECEIPT_TERMS = {"packet_id"}


class EvidenceReceiptLedgerTests(unittest.TestCase):
    def test_receipt_ledger_is_deterministic_and_lock_preserving(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        first = build_evidence_receipt_ledger(packet, "support_triage_agent")
        second = build_evidence_receipt_ledger(packet, "support_triage_agent")

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], EVIDENCE_RECEIPT_LEDGER_SCHEMA_VERSION)
        self.assertEqual(first["packet_id"], packet["packet_id"])
        self.assertEqual(first["decision_lock_before"], "scoped_validation_only")
        self.assertEqual(first["decision_lock_after"], "scoped_validation_only")
        self.assertFalse(ledger_has_failures(first))
        self.assertGreater(first["summary"]["receipt_count"], 0)
        self.assertEqual(len(first["receipt_ids"]), len(set(first["receipt_ids"])))

    def test_receipts_cover_finance_procurement_for_every_scenario(self) -> None:
        for scenario_name in SCENARIOS:
            ledger = build_evidence_receipt_ledger(build_scenario_packet(scenario_name), scenario_name)

            self.assertEqual(ledger["summary"]["cost_procurement_receipts"], 1)
            self.assertTrue(ledger["finance_procurement"]["budget_owner_required"])
            self.assertTrue(ledger["finance_procurement"]["token_or_tool_spend_cap_required"])
            self.assertFalse(ledger["finance_procurement"]["approval_granted"])
            self.assertTrue(ledger["safety"]["all_require_human_review"])
            self.assertTrue(ledger["safety"]["all_non_approving"])
            self.assertTrue(ledger["safety"]["all_non_granting"])
            self.assertTrue(ledger["safety"]["all_non_executing"])
            self.assertTrue(ledger["safety"]["all_non_mutating"])
            self.assertTrue(ledger["safety"]["all_non_auto_reducing"])

    def test_packet_authority_snapshot_attaches_receipt_ids(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        ledger = build_evidence_receipt_ledger(packet, "support_triage_agent")
        snapshot = build_packet_authority_snapshot_for_scenario(packet, "support_triage_agent")

        self.assertEqual(snapshot["decision_lock_before"], ledger["decision_lock_before"])
        self.assertEqual(snapshot["decision_lock_after"], ledger["decision_lock_after"])
        self.assertEqual(snapshot["evidence_receipt_ids"], ledger["receipt_ids"])
        self.assertEqual(len(snapshot["accepted_evidence"]), ledger["summary"]["receipt_count"])
        self.assertTrue(snapshot["content_hash"].startswith("sha256:"))

    def test_receipt_cli_outputs_machine_readable_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.evidence_receipts", "--no-write", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], EVIDENCE_RECEIPT_LEDGER_SCHEMA_VERSION)
        self.assertEqual(payload["scenario"], "support_triage_agent")
        self.assertTrue(payload["safety"]["decision_lock_preserved"])
        self.assertTrue(payload["finance_procurement"]["budget_owner_required"])

    def test_write_receipt_artifacts_for_all_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_evidence_receipt_artifacts(Path(temp_dir))
            names = {path.name for path in written}

        self.assertEqual(len(written), len(SCENARIOS) * 2)
        for scenario_name in SCENARIOS:
            self.assertIn(f"{scenario_name}.evidence_receipts.md", names)
            self.assertIn(f"{scenario_name}.evidence_receipts.json", names)

    def test_receipts_preserve_private_boundary(self) -> None:
        packet = build_scenario_packet("support_triage_agent")
        ledger = build_evidence_receipt_ledger(packet, "support_triage_agent")
        combined = json.dumps(ledger, sort_keys=True)

        private_engine_terms = [
            term for term in FORBIDDEN_PRIVATE_V1_TERMS if term not in PUBLIC_RECEIPT_TERMS
        ]
        for forbidden in private_engine_terms:
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
