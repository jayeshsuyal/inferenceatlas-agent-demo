import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent.judge import build_judge_report, report_has_failures
from agent.spend import (
    DEFAULT_SPEND_REQUEST,
    DEFAULT_SPEND_REQUEST_PATH,
    FINANCE_RECEIPT_SCHEMA_VERSION,
    PROCUREMENT_MEMO_SCHEMA_VERSION,
    SPEND_REVIEW_SCHEMA_VERSION,
    SPEND_SCENARIO_ID,
    build_finance_evidence_receipt,
    build_procurement_review_memo,
    build_spend_review_bundle,
    build_spend_review_packet,
    load_spend_review_request,
    render_finance_receipt_markdown,
    render_procurement_memo_markdown,
    render_spend_review_packet_markdown,
    spend_review_has_forbidden_claims,
    write_spend_review_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


class SpendLaneTests(unittest.TestCase):
    def test_public_spend_request_fixture_loads_to_default_request(self) -> None:
        request = load_spend_review_request(DEFAULT_SPEND_REQUEST_PATH)

        self.assertEqual(request, DEFAULT_SPEND_REQUEST)
        self.assertEqual(request.scenario_id, SPEND_SCENARIO_ID)
        self.assertEqual(
            set(request.data_classes),
            {
                "vendor_invoice_evidence",
                "per_team_usage_metrics",
                "contract_terms",
                "budget_owner_attestation",
            },
        )

    def test_request_fixture_generates_canonical_spend_artifacts(self) -> None:
        request = load_spend_review_request(DEFAULT_SPEND_REQUEST_PATH)
        packet = build_spend_review_packet(request)
        finance = build_finance_evidence_receipt(packet)
        procurement = build_procurement_review_memo(packet)

        self.assertEqual(
            packet,
            json.loads((ROOT / "examples/generated/ai_spend_budget_overrun.spend_packet.json").read_text()),
            "Fixture must produce the canonical spend packet, not a divergent artifact.",
        )
        self.assertEqual(
            finance,
            json.loads((ROOT / "examples/generated/ai_spend_budget_overrun.finance_receipt.json").read_text()),
            "Fixture must produce the canonical finance receipt, not a divergent artifact.",
        )
        self.assertEqual(
            procurement,
            json.loads((ROOT / "examples/generated/ai_spend_budget_overrun.procurement_memo.json").read_text()),
            "Fixture must produce the canonical procurement memo, not a divergent artifact.",
        )

    def test_spend_packet_is_finance_procurement_review_not_optimizer(self) -> None:
        packet = build_spend_review_packet()

        self.assertEqual(packet["schema_version"], SPEND_REVIEW_SCHEMA_VERSION)
        self.assertEqual(packet["scenario"], SPEND_SCENARIO_ID)
        self.assertEqual(packet["decision"]["verdict_class"], "finance_procurement_review_required")
        self.assertFalse(packet["spend_posture"]["live_spend_approved"])
        self.assertFalse(packet["spend_posture"]["provider_winner_selected"])
        self.assertFalse(packet["spend_posture"]["savings_guaranteed"])
        self.assertTrue(packet["safety_state"]["requires_human_approval"])
        self.assertGreaterEqual(len(packet["required_evidence"]), 4)
        self.assertGreaterEqual(len(packet["blocked_claims"]), 4)

    def test_finance_and_procurement_outputs_are_non_approving(self) -> None:
        packet = build_spend_review_packet()
        finance = build_finance_evidence_receipt(packet)
        procurement = build_procurement_review_memo(packet)

        self.assertEqual(finance["schema_version"], FINANCE_RECEIPT_SCHEMA_VERSION)
        self.assertEqual(procurement["schema_version"], PROCUREMENT_MEMO_SCHEMA_VERSION)
        self.assertEqual(finance["packet_id"], packet["packet_id"])
        self.assertEqual(procurement["packet_id"], packet["packet_id"])
        for safety in (finance["safety_boundary"], procurement["safety_boundary"]):
            self.assertFalse(safety["approves_spend"])
            self.assertFalse(safety["guarantees_savings"])
            self.assertFalse(safety["selects_provider"])
            self.assertFalse(safety["executes_external_writes"])
            self.assertTrue(safety["requires_human_review"])

    def test_spend_surfaces_do_not_make_unsafe_dollar_or_provider_claims(self) -> None:
        packet = build_spend_review_packet()
        finance = build_finance_evidence_receipt(packet)
        procurement = build_procurement_review_memo(packet)
        surfaces = [
            DEFAULT_SPEND_REQUEST_PATH.read_text(encoding="utf-8"),
            json.dumps(packet, sort_keys=True),
            json.dumps(finance, sort_keys=True),
            json.dumps(procurement, sort_keys=True),
            render_spend_review_packet_markdown(packet),
            render_finance_receipt_markdown(finance),
            render_procurement_memo_markdown(procurement),
        ]
        combined = "\n".join(surfaces)

        self.assertNotIn("$", combined)
        self.assertNotIn("will save", combined.lower())
        self.assertNotIn("best provider", combined.lower())
        self.assertNotIn("final winner", combined.lower())
        self.assertTrue(spend_review_has_forbidden_claims("IA will save $500,000"))
        self.assertTrue(spend_review_has_forbidden_claims("IA reduced spend by $500,000"))
        self.assertTrue(spend_review_has_forbidden_claims("This guarantees ROI."))
        self.assertTrue(spend_review_has_forbidden_claims("This provides 40% cost reduction."))
        self.assertTrue(spend_review_has_forbidden_claims("The best provider is final winner."))

    def test_spend_artifacts_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_spend_review_artifacts(Path(temp_dir))
            names = {path.name for path in written}

        self.assertEqual(len(written), 6)
        self.assertEqual(
            names,
            {
                "ai_spend_budget_overrun.spend_packet.md",
                "ai_spend_budget_overrun.spend_packet.json",
                "ai_spend_budget_overrun.finance_receipt.md",
                "ai_spend_budget_overrun.finance_receipt.json",
                "ai_spend_budget_overrun.procurement_memo.md",
                "ai_spend_budget_overrun.procurement_memo.json",
            },
        )

    def test_spend_cli_outputs_machine_readable_bundle(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.spend", "--no-write", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scenario"], SPEND_SCENARIO_ID)
        self.assertEqual(payload["request_path"], "examples/requests/ai_spend_budget_overrun.yml")
        self.assertFalse(payload["safety"]["approves_spend"])
        self.assertFalse(payload["safety"]["guarantees_savings"])
        self.assertFalse(payload["safety"]["selects_provider"])

    def test_spend_cli_accepts_public_request_fixture(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agent.spend",
                "examples/requests/ai_spend_budget_overrun.yml",
                "--no-write",
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
        self.assertEqual(payload["scenario"], SPEND_SCENARIO_ID)
        self.assertEqual(payload["packet"]["scenario"], SPEND_SCENARIO_ID)
        self.assertEqual(payload["request_path"], "examples/requests/ai_spend_budget_overrun.yml")
        self.assertFalse(payload["safety"]["approves_spend"])

    def test_judge_report_includes_spend_lane_safely(self) -> None:
        report = build_judge_report(write_artifacts=False)
        spend = report["ai_spend_review"]

        self.assertFalse(report_has_failures(report))
        self.assertEqual(spend["scenario"], SPEND_SCENARIO_ID)
        self.assertEqual(spend["verdict_class"], "finance_procurement_review_required")
        self.assertFalse(spend["approves_spend"])
        self.assertFalse(spend["guarantees_savings"])
        self.assertFalse(spend["selects_provider"])


if __name__ == "__main__":
    unittest.main()
