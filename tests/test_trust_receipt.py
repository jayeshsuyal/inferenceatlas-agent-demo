import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.scenarios import SCENARIOS
from agent.trust import (
    REVIEW_ROOM_SCHEMA_VERSION,
    TRUST_RECEIPT_SCHEMA_VERSION,
    build_review_room,
    build_trust_receipt,
)


ROOT = Path(__file__).resolve().parents[1]


class TrustReceiptTests(unittest.TestCase):
    def test_trust_receipt_covers_all_scenarios(self) -> None:
        receipt = build_trust_receipt()

        self.assertEqual(receipt["schema_version"], TRUST_RECEIPT_SCHEMA_VERSION)
        self.assertEqual(
            {item["scenario"] for item in receipt["scenario_matrix"]},
            set(SCENARIOS),
        )
        self.assertTrue(receipt["safety_state"]["all_scenarios_production_blocked"])
        self.assertFalse(receipt["safety_state"]["production_access_granted"])
        self.assertTrue(receipt["safety_state"]["composio_dry_run"])

    def test_trust_receipt_proves_verdict_spread(self) -> None:
        receipt = build_trust_receipt()
        by_scenario = {item["scenario"]: item for item in receipt["scenario_matrix"]}

        self.assertTrue(by_scenario["read_only_analytics_agent"]["scoped_validation_review"])
        self.assertTrue(by_scenario["support_triage_agent"]["scoped_validation_review"])
        self.assertFalse(by_scenario["admin_code_fix_bot"]["scoped_validation_review"])
        self.assertEqual(by_scenario["admin_code_fix_bot"]["highest_risk"], "critical")
        self.assertEqual(by_scenario["read_only_analytics_agent"]["highest_risk"], "low")

    def test_trust_receipt_has_hash_and_private_boundary(self) -> None:
        receipt = build_trust_receipt()

        self.assertEqual(len(receipt["trust_receipt_hash"]), 16)
        self.assertFalse(receipt["private_boundary"]["private_source_exposed"])
        self.assertIn("Private engine, public proof.", receipt["private_boundary"]["principle"])
        self.assertIn("production access grant", receipt["permission_envelope"]["never_allowed_in_public_demo"])

    def test_review_room_points_to_trust_receipt(self) -> None:
        receipt = build_trust_receipt()
        review_room = build_review_room(receipt)

        self.assertEqual(review_room["schema_version"], REVIEW_ROOM_SCHEMA_VERSION)
        self.assertEqual(review_room["derived_from_trust_receipt_id"], receipt["trust_receipt_id"])
        self.assertEqual(review_room["trust_receipt_hash"], receipt["trust_receipt_hash"])
        self.assertIn("python3 -m agent.trust", review_room["copy_paste_commands"])
        self.assertEqual(review_room["public_contract_status"]["status"], "ok")

    def test_trust_cli_writes_machine_readable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-m", "agent.trust", "--output-dir", temp_dir],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            receipt = json.loads((Path(temp_dir) / "trust_receipt.json").read_text(encoding="utf-8"))
            review_room = json.loads((Path(temp_dir) / "review_room.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_version"], TRUST_RECEIPT_SCHEMA_VERSION)
            self.assertEqual(review_room["derived_from_trust_receipt_id"], receipt["trust_receipt_id"])

    def test_trust_cli_can_print_json_without_writing(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.trust", "--print-json", "trust_receipt"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], TRUST_RECEIPT_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
