import json
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

from agent.subscribers import (
    PACKET_AUTHORITY_SENTENCE,
    PACKET_AUTHORITY_SHORT_SENTENCE,
    SUBSCRIBERS_DIR,
    build_subscriber_examples,
)
from web.app import app, packet_verification


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_KEYS = {
    "packet_id",
    "revision_id",
    "content_hash",
    "verdict_class",
    "safety_state",
}
EXPECTED_CATEGORIES = {"gateway", "ci", "spend", "review", "observability"}


class PacketSubscriberTests(unittest.TestCase):
    def _subscriber_payloads(self) -> list[dict]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SUBSCRIBERS_DIR.glob("*/*.json"))
        ]

    def test_verification_endpoint_exposes_packet_authority_shape(self) -> None:
        payload = packet_verification("support_triage_agent")
        verification = payload["verification"]

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["scenario"], "support_triage_agent")
        self.assertEqual(verification["packet_id"], "ia-agent-access-support-triage-v0")
        self.assertEqual(verification["verdict_class"], "scoped_validation_only")
        self.assertTrue(verification["content_hash"].startswith("sha256:"))
        self.assertFalse(verification["safety_state"]["production_access"])
        self.assertFalse(verification["safety_state"]["permission_grants"])
        self.assertFalse(verification["safety_state"]["external_writes"])
        self.assertFalse(verification["safety_state"]["approval_granted"])
        self.assertTrue(verification["safety_state"]["requires_human_approval"])

        by_packet_id = packet_verification(verification["packet_id"])
        self.assertEqual(by_packet_id["verification"], verification)

        with self.assertRaises(HTTPException) as raised:
            packet_verification("missing_packet")
        self.assertEqual(raised.exception.status_code, 404)

    def test_verification_endpoint_is_get_only(self) -> None:
        route = next(
            route
            for route in app.routes
            if getattr(route, "path", "") == "/api/packets/{scenario_or_packet_id}/verification"
        )

        self.assertEqual(route.methods, {"GET"})

    def test_subscriber_examples_match_generator(self) -> None:
        generated = build_subscriber_examples()
        expected_paths = {
            str((SUBSCRIBERS_DIR / category / filename).relative_to(ROOT)): payload
            for category, files in generated.items()
            for filename, payload in files.items()
        }
        checked_in = {
            str(path.relative_to(ROOT)): json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SUBSCRIBERS_DIR.glob("*/*.json"))
        }

        self.assertEqual(checked_in, expected_paths)

    def test_subscribers_cover_categories_and_share_canonical_authority(self) -> None:
        payloads = self._subscriber_payloads()

        self.assertGreaterEqual(len(payloads), 6)
        self.assertEqual({payload["subscriber_category"] for payload in payloads}, EXPECTED_CATEGORIES)

        first_authority = {
            key: payloads[0]["packet_authority"][key]
            for key in AUTHORITY_KEYS
        }
        for payload in payloads:
            authority = payload["packet_authority"]
            self.assertEqual({key: authority[key] for key in AUTHORITY_KEYS}, first_authority)
            self.assertEqual(payload["read_only_contract"]["method"], "GET")
            self.assertEqual(payload["category_sentence"], PACKET_AUTHORITY_SHORT_SENTENCE)

    def test_subscribers_cannot_approve_mutate_or_override_packet(self) -> None:
        for payload in self._subscriber_payloads():
            effect = payload["subscriber_effect"]
            self.assertFalse(effect["can_approve_access"])
            self.assertFalse(effect["can_grant_permissions"])
            self.assertFalse(effect["can_mutate_packet"])
            self.assertFalse(effect["can_override_verdict"])
            self.assertFalse(effect["executes_external_writes"])
            self.assertTrue(effect["requires_human_review"])

    def test_contract_and_manifest_lock_category_sentence(self) -> None:
        contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertIn(PACKET_AUTHORITY_SENTENCE, contract)
        self.assertIn(PACKET_AUTHORITY_SHORT_SENTENCE, contract)
        self.assertEqual(manifest["packet_authority_layer"], PACKET_AUTHORITY_SENTENCE)
        self.assertEqual(manifest["packet_authority_short"], PACKET_AUTHORITY_SHORT_SENTENCE)
        self.assertEqual(manifest["packet_verification_api"], "/api/packets/{scenario_or_packet_id}/verification")
        self.assertEqual(set(manifest["subscriber_categories"]), EXPECTED_CATEGORIES)

    def test_subscriber_cli_is_machine_readable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent.subscribers", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(len(payload["subscribers"]), 6)


if __name__ == "__main__":
    unittest.main()
