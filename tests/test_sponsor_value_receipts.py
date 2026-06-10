"""Sponsor Value Receipt tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.sponsor_value_receipts import (
    PROVIDER_ORDER,
    SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION,
    SPONSOR_VALUE_RECEIPT_SCHEMA_VERSION,
    build_sponsor_value_receipts,
    render_sponsor_value_receipts_markdown,
    sponsor_value_receipts_have_failures,
    write_sponsor_value_receipts_artifacts,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "sponsor_value_receipts.schema.json"


class SponsorValueReceiptsTests(unittest.TestCase):
    def test_receipts_are_graph_backed_and_safety_locked(self) -> None:
        payload = build_sponsor_value_receipts()

        self.assertEqual(payload["schema_version"], SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION)
        self.assertEqual(payload["headline"], "Sponsors provide proof signals. IA converts them into packet authority.")
        self.assertEqual(payload["summary"]["providers"], list(PROVIDER_ORDER))
        self.assertEqual(payload["summary"]["provider_count"], 5)
        self.assertEqual(payload["summary"]["receipt_count"], 5)
        self.assertEqual(payload["summary"]["proof_node_count"], 80)
        self.assertEqual(payload["summary"]["proof_edge_count"], 141)
        self.assertEqual(payload["packet_reference"]["packet_id"], "ia-agent-access-support-triage-v0")
        self.assertFalse(sponsor_value_receipts_have_failures(payload))

        safety = payload["safety"]
        self.assertTrue(safety["packet_remains_authority"])
        self.assertTrue(safety["all_receipts_require_human_review"])
        self.assertTrue(safety["all_receipts_non_approving"])
        self.assertTrue(safety["all_receipts_non_granting"])
        self.assertTrue(safety["all_receipts_non_executing"])
        self.assertTrue(safety["all_receipts_non_mutating"])
        self.assertTrue(safety["all_receipts_preserve_verdict"])
        self.assertTrue(safety["all_receipts_non_auto_reducing"])

        self.assertEqual([receipt["provider"] for receipt in payload["receipts"]], list(PROVIDER_ORDER))
        for receipt in payload["receipts"]:
            self.assertEqual(receipt["schema_version"], SPONSOR_VALUE_RECEIPT_SCHEMA_VERSION)
            self.assertGreater(receipt["proof_node_count"], 0)
            self.assertTrue(receipt["attached_packet_fields"])
            self.assertIn("IA Packet identity", receipt["ia_authority_boundary"])
            boundary = receipt["safety_boundary"]
            self.assertFalse(boundary["can_approve"])
            self.assertFalse(boundary["can_grant_permissions"])
            self.assertFalse(boundary["can_execute_external_write"])
            self.assertFalse(boundary["can_mutate_packet"])
            self.assertFalse(boundary["can_change_verdict"])
            self.assertFalse(boundary["can_reduce_proof_debt_automatically"])
            self.assertTrue(boundary["requires_human_review"])

    def test_provider_receipts_capture_specific_value(self) -> None:
        payload = build_sponsor_value_receipts()
        by_provider = {receipt["provider"]: receipt for receipt in payload["receipts"]}

        self.assertEqual(by_provider["tavily"]["key_metrics"]["query_count"], 5)
        self.assertFalse(by_provider["tavily"]["key_metrics"]["can_reduce_proof_debt"])
        self.assertEqual(by_provider["composio"]["key_metrics"]["blocked_action_count"], 9)
        self.assertFalse(by_provider["composio"]["key_metrics"]["would_execute"])
        self.assertEqual(by_provider["openclaw"]["key_metrics"]["blocked_event_count"], 9)
        self.assertFalse(by_provider["openclaw"]["key_metrics"]["runtime_write_attempted"])
        self.assertEqual(by_provider["nebius"]["key_metrics"]["locked_field_count"], 4)
        self.assertFalse(by_provider["nebius"]["key_metrics"]["can_change_verdict"])
        self.assertEqual(by_provider["portkey"]["key_metrics"]["webhook_path"], "/api/portkey/guardrail")
        self.assertFalse(by_provider["portkey"]["key_metrics"]["portkey_api_call_made"])
        self.assertFalse(by_provider["portkey"]["key_metrics"]["portkey_policy_mutation_allowed"])

    def test_markdown_is_skim_ready_and_public_safe(self) -> None:
        markdown = render_sponsor_value_receipts_markdown(build_sponsor_value_receipts())

        for expected in [
            "# Sponsor Value Receipts",
            "Private engine, public proof.",
            "Sponsors provide proof signals. IA converts them into packet authority.",
            "| Provider | Role | Contribution | Stayed Blocked | Proof Nodes |",
            "tavily",
            "composio",
            "openclaw",
            "nebius",
            "portkey",
            "packet remains authority: True",
            "all non-approving: True",
            "Provider proof can inform review",
        ]:
            self.assertIn(expected, markdown)

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, markdown)

    def test_schema_locks_receipt_contract(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema_version"]["const"], SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION)
        self.assertEqual(
            schema["properties"]["headline"]["const"],
            "Sponsors provide proof signals. IA converts them into packet authority.",
        )
        self.assertEqual(schema["properties"]["summary"]["properties"]["provider_count"]["const"], 5)
        self.assertEqual(schema["properties"]["summary"]["properties"]["receipt_count"]["const"], 5)
        safety = schema["$defs"]["safety"]["properties"]
        self.assertTrue(safety["packet_remains_authority"]["const"])
        self.assertTrue(safety["all_receipts_non_approving"]["const"])
        self.assertTrue(safety["all_receipts_non_mutating"]["const"])
        receipt_safety = schema["$defs"]["receipt"]["properties"]["safety_boundary"]["properties"]
        self.assertFalse(receipt_safety["can_approve"]["const"])
        self.assertFalse(receipt_safety["can_execute_external_write"]["const"])
        self.assertFalse(receipt_safety["can_mutate_packet"]["const"])
        self.assertFalse(receipt_safety["can_change_verdict"]["const"])

    def test_writes_markdown_and_json_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_sponsor_value_receipts_artifacts(output_dir=Path(temp_dir))
            names = {path.name for path in written}
            payload = json.loads((Path(temp_dir) / "sponsor_value_receipts.json").read_text(encoding="utf-8"))
            markdown = (Path(temp_dir) / "sponsor_value_receipts.md").read_text(encoding="utf-8")

        self.assertEqual(names, {"sponsor_value_receipts.md", "sponsor_value_receipts.json"})
        self.assertEqual(payload["schema_version"], SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION)
        self.assertIn("Sponsor Value Receipts", markdown)

    def test_cli_renders_markdown_and_json_without_writes(self) -> None:
        markdown_result = subprocess.run(
            [sys.executable, "-m", "agent.sponsor_value_receipts", "--no-write"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        json_result = subprocess.run(
            [sys.executable, "-m", "agent.sponsor_value_receipts", "--no-write", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(markdown_result.returncode, 0, msg=markdown_result.stderr)
        self.assertIn("# Sponsor Value Receipts", markdown_result.stdout)
        self.assertIn("all non-mutating: True", markdown_result.stdout)

        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["schema_version"], SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION)
        self.assertTrue(payload["safety"]["packet_remains_authority"])


if __name__ == "__main__":
    unittest.main()
