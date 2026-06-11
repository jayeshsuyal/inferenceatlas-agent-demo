"""ReviewRun API contract tests."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from agent.connector_oauth import demo_sign_in
from agent.portkey_guardrail import list_portkey_guardrail_events

from web.app import (
    GithubAttachRequest,
    ReviewRunCoachRequest,
    ReviewRunCreateRequest,
    ReviewRunPacketRequest,
    ReviewRunProofAttachRequest,
    ReviewRunRerunRequest,
    _review_runs,
    attach_review_run_proof_api,
    coach_review_run_api,
    app,
    create_review_run_api,
    generate_review_run_packet_api,
    get_review_run_proofgraph_api,
    github_attach_repo,
    github_list_repos,
    get_review_run,
    proofgraph_index,
    portkey_guardrail_webhook,
    review_run_portkey_guardrail_test_api,
    rerun_review_run_packet_api,
)


class _FakePortkeyRequest:
    def __init__(self, body: dict) -> None:
        self._body = body

    async def json(self) -> dict:
        return self._body


def _portkey_review_run_body(
    *,
    run_id: str,
    packet_id: str,
    revision_id: str,
    requested_mode: str = "scoped_validation",
) -> dict:
    metadata = {
        "ia_review_run_id": run_id,
        "ia_packet_id": packet_id,
        "ia_revision_id": revision_id,
        "ia_requested_mode": requested_mode,
        "ia_source_of_truth": "ReviewRun",
    }
    return {
        "eventType": "beforeRequestHook",
        "provider": "openai",
        "requestType": "chatComplete",
        "metadata": metadata,
        "request": {
            "metadata": metadata,
            "model": "packet-gated-model",
            "messages": [{"role": "user", "content": "Can this ReviewRun packet move?"}],
        },
    }


def _post_portkey_webhook(body: dict, *, token: str = "demo-token", rehearsal_token: str | None = None) -> dict:
    return asyncio.run(
        portkey_guardrail_webhook(
            request=_FakePortkeyRequest(body),
            authorization=f"Bearer {token}",
            x_ia_portkey_guardrail_token=None,
            x_ia_rehearsal_mode=rehearsal_token,
        )
    )


class ReviewRunApiTests(TestCase):
    def test_review_run_api_creates_and_reads_durable_run(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                            "oauth_token": "ghp_1234567890abcdefSECRET",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 4},
                    )
                )

                self.assertIs(created["ok"], True)
                self.assertIs(created["read_only"], True)
                run = created["run"]
                self.assertEqual(run["stage"], "repo_selected")
                self.assertEqual(run["selected_repo"]["full_name"], "acme/demo-support-incidents")
                self.assertEqual(run["selected_repo"]["oauth_token"], "[redacted]")
                self.assertIs(run["repo_index_summary"]["selected_repo_only"], True)
                self.assertEqual(run["repo_index_summary"]["indexed_repo_count"], 1)
                self.assertIs(run["safety_invariants"]["approval_granted"], False)
                self.assertIs(run["safety_invariants"]["external_writes_enabled"], False)
                self.assertEqual(created["record"]["run_id"], run["run_id"])
                self.assertIs(created["record"]["read_only"], True)

                _review_runs.clear()
                fetched = get_review_run(run["run_id"])
                self.assertIs(fetched["ok"], True)
                self.assertIs(fetched["read_only"], True)
                self.assertEqual(fetched["run"], run)
                self.assertEqual(fetched["record"]["stage"], "repo_selected")
                self.assertTrue(list(store_dir.glob("*.json")))

    def test_review_run_api_generates_compact_packet_from_selected_repo(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                generated = generate_review_run_packet_api(
                    created["run"]["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )

                self.assertIs(generated["ok"], True)
                self.assertIs(generated["read_only"], True)
                run = generated["run"]
                packet = generated["packet"]
                self.assertEqual(run["stage"], "packet_generated")
                self.assertEqual(run["packet"]["source_run_id"], run["run_id"])
                self.assertEqual(run["packet"]["revision_number"], 1)
                self.assertEqual(packet["schema_version"], "review_run_packet.v0")
                self.assertEqual(packet["packet_reference"]["run_id"], run["run_id"])
                self.assertEqual(packet["packet_reference"]["source_of_truth"], "ReviewRun")
                self.assertEqual(packet["compact_output"]["allowed"], ["read issues"])
                self.assertEqual(packet["compact_output"]["review_required"], ["comment"])
                self.assertEqual(
                    packet["compact_output"]["blocked"],
                    ["create labels", "repo admin", "org-wide write", "secrets"],
                )
                self.assertEqual(packet["source_inputs"]["selected_repo"], "acme/demo-support-incidents")
                self.assertFalse(packet["safety_boundary"]["approval_granted"])
                self.assertFalse(packet["safety_boundary"]["external_writes"])
                self.assertFalse(packet["safety_boundary"]["portkey_api_call_made"])
                proof_lenses = packet["proof_resolution"]["owner_lenses"]
                self.assertEqual(proof_lenses["schema_version"], "review_run_proof_lenses.v0")
                self.assertEqual(proof_lenses["packet_reference"], packet["packet_reference"])
                self.assertEqual(proof_lenses["active_lane"], "agent_access_review")
                self.assertEqual(
                    {lens["lens_id"] for lens in proof_lenses["lenses"] if lens["active"]},
                    {"support_ops", "engineering", "security"},
                )
                self.assertEqual(
                    {lens["lens_id"] for lens in proof_lenses["lenses"] if not lens["active"]},
                    {"finance_procurement", "legal"},
                )
                self.assertTrue(proof_lenses["guardrails"]["does_not_approve"])
                self.assertFalse(proof_lenses["guardrails"]["proof_attachment_changes_verdict"])
                for lens in proof_lenses["lenses"]:
                    self.assertIn("does not approve", lens["safety_note"])
                    for item in lens["prepared_proof_items"]:
                        self.assertFalse(item["approves_access"])
                        self.assertFalse(item["grants_permissions"])
                        self.assertFalse(item["mutates_downstream_policy"])

                fetched = get_review_run(run["run_id"])
                self.assertEqual(fetched["run"]["stage"], "packet_generated")
                self.assertEqual(fetched["run"]["packet"], run["packet"])

                second = generate_review_run_packet_api(
                    run["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                self.assertEqual(second["run"]["packet"]["revision_id"], run["packet"]["revision_id"])

                with self.assertRaises(HTTPException) as changed:
                    generate_review_run_packet_api(
                        run["run_id"],
                        ReviewRunPacketRequest(access_request="support-triage-bot now needs repo admin"),
                    )
                self.assertEqual(changed.exception.status_code, 400)
                self.assertIn("raw agent request cannot change", changed.exception.detail)

    def test_review_run_proofgraph_api_tracks_full_review_loop(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                            "access_token": "ghp_1234567890abcdefSECRET",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                run_id = created["run"]["run_id"]

                waiting = get_review_run_proofgraph_api(run_id)
                self.assertTrue(waiting["read_only"])
                self.assertEqual(waiting["stage"], "repo_selected")
                self.assertEqual(waiting["proofgraph"]["graph_state"], "waiting_for_packet")
                self.assertEqual(waiting["proofgraph"]["generated_from_run_id"], run_id)
                self.assertEqual(waiting["proofgraph"]["portkey_state"], "No packet")
                self.assertTrue(waiting["proofgraph"]["zero_writes"])

                generated = generate_review_run_packet_api(
                    run_id,
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                rev1 = get_review_run_proofgraph_api(run_id)
                self.assertEqual(rev1["proofgraph"]["graph_state"], "packet_generated")
                self.assertEqual(
                    rev1["proofgraph"]["packet_reference"]["revision_id"],
                    generated["run"]["packet"]["revision_id"],
                )
                self.assertEqual(rev1["proofgraph"]["selected_repo"], "acme/demo-support-incidents")
                self.assertEqual(rev1["proofgraph"]["portkey_state"], "Block")
                self.assertNotIn("ghp_1234567890abcdefSECRET", str(rev1["proofgraph"]))
                rev1_hash = rev1["proofgraph"]["content_hash"]

                _review_runs.clear()
                reloaded = get_review_run_proofgraph_api(run_id)
                self.assertEqual(reloaded["proofgraph"]["content_hash"], rev1_hash)

                proofed = attach_review_run_proof_api(
                    run_id,
                    ReviewRunProofAttachRequest(
                        proof_items=[
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                            {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
                            {"id": "environment_boundary", "label": "Environment boundary"},
                        ]
                    ),
                )
                proof_graph = get_review_run_proofgraph_api(run_id)["proofgraph"]
                self.assertEqual(proof_graph["graph_state"], "proof_attached_rerun_required")
                self.assertEqual(
                    proof_graph["packet_reference"]["revision_id"],
                    generated["run"]["packet"]["revision_id"],
                )
                self.assertEqual(proof_graph["proof_counts"]["attached"], 3)
                self.assertEqual(proof_graph["proof_counts"]["missing"], 0)
                self.assertEqual(proofed["run"]["stage"], "proof_attached")

                rerun = rerun_review_run_packet_api(
                    run_id,
                    ReviewRunRerunRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                rev2 = get_review_run_proofgraph_api(run_id)["proofgraph"]
                self.assertEqual(rev2["graph_state"], "updated_packet_ready")
                self.assertEqual(rev2["portkey_state"], "Allow with policy")
                self.assertEqual(
                    rev2["packet_reference"]["previous_revision_id"],
                    generated["run"]["packet"]["revision_id"],
                )
                self.assertEqual(rev2["packet_reference"]["revision_id"], rerun["run"]["packet"]["revision_id"])
                self.assertTrue(rev2["revision_changed"])
                self.assertNotEqual(rev1_hash, rev2["content_hash"])

                body = proofgraph_index(review_run_id=run_id).body.decode("utf-8")
                self.assertIn("InferenceAtlas ReviewRun ProofGraph", body)
                self.assertIn(f"Generated from run_id <span class=\"run-id\">{run_id}</span>", body)
                self.assertIn("Allow with policy", body)
                self.assertIn("zero writes", body)

                with self.assertRaises(HTTPException) as bad:
                    get_review_run_proofgraph_api("../escape")
                self.assertEqual(bad.exception.status_code, 400)

                with self.assertRaises(HTTPException) as missing:
                    get_review_run_proofgraph_api("ia-review-run-missing")
                self.assertEqual(missing.exception.status_code, 404)

    def test_review_run_portkey_guardrail_test_tracks_packet_revision_delta(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            ledger_dir = store_dir / "ledger"
            with (
                patch("web.app.REVIEW_RUN_STORE_DIR", store_dir),
                patch("web.app.SPONSOR_PROOF_RUN_LEDGER_DIR", ledger_dir),
            ):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                run_id = created["run"]["run_id"]

                with self.assertRaises(HTTPException) as before_packet:
                    review_run_portkey_guardrail_test_api(run_id)
                self.assertEqual(before_packet.exception.status_code, 400)
                self.assertIn("no generated packet", before_packet.exception.detail)

                generated = generate_review_run_packet_api(
                    run_id,
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                rev1 = review_run_portkey_guardrail_test_api(run_id)
                rev1_test = rev1["portkey_guardrail_test"]
                self.assertIs(rev1["read_only"], True)
                self.assertEqual(rev1_test["schema_version"], "review_run_portkey_guardrail_test.v0")
                self.assertEqual(rev1_test["stage"], "packet_generated")
                self.assertEqual(rev1_test["portkey_state"], "Block")
                self.assertIs(rev1_test["verdict"], False)
                self.assertEqual(
                    rev1_test["packet_reference"]["revision_id"],
                    generated["run"]["packet"]["revision_id"],
                )
                self.assertIn("blocked_scope:create labels", rev1_test["deny_reasons"])
                self.assertIs(rev1_test["invariants"]["portkey_api_call_made"], False)
                self.assertIs(rev1_test["invariants"]["portkey_policy_mutation_allowed"], False)
                self.assertTrue(rev1_test["event_id"].startswith("portkey-guardrail-"))

                attach_review_run_proof_api(
                    run_id,
                    ReviewRunProofAttachRequest(
                        proof_items=[
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                            {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
                            {"id": "environment_boundary", "label": "Environment boundary"},
                        ]
                    ),
                )
                rerun = rerun_review_run_packet_api(
                    run_id,
                    ReviewRunRerunRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                rev2 = review_run_portkey_guardrail_test_api(run_id)
                rev2_test = rev2["portkey_guardrail_test"]
                self.assertEqual(rev2_test["stage"], "ready_to_export")
                self.assertEqual(rev2_test["portkey_state"], "Allow with policy")
                self.assertIs(rev2_test["verdict"], True)
                self.assertEqual(rev2_test["deny_reasons"], [])
                self.assertEqual(
                    rev2_test["packet_reference"]["revision_id"],
                    rerun["run"]["packet"]["revision_id"],
                )
                self.assertEqual(
                    rev2_test["allowed_scope"],
                    ["read issues", "comment", "create labels in selected repo"],
                )
                self.assertEqual(rev2_test["still_blocked_scope"], ["repo admin", "org-wide write", "secrets"])
                self.assertIs(rev2_test["invariants"]["packet_remains_authority"], True)
                self.assertIs(rev2_test["invariants"]["approval_granted"], False)
                self.assertIs(rev2_test["invariants"]["external_writes"], False)

                events = list_portkey_guardrail_events(ledger_dir=ledger_dir)
                self.assertEqual(len(events), 2)
                self.assertEqual({event["verdict"] for event in events}, {False, True})

    def test_portkey_webhook_consumes_current_review_run_packet_revision(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            ledger_dir = store_dir / "ledger"
            with (
                patch("web.app.REVIEW_RUN_STORE_DIR", store_dir),
                patch("web.app.SPONSOR_PROOF_RUN_LEDGER_DIR", ledger_dir),
                patch.dict(os.environ, {"PORTKEY_GUARDRAIL_TOKEN": "demo-token"}, clear=False),
            ):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                run_id = created["run"]["run_id"]
                generated = generate_review_run_packet_api(
                    run_id,
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                rev1_packet = generated["run"]["packet"]
                rev1_body = _portkey_review_run_body(
                    run_id=run_id,
                    packet_id=rev1_packet["packet_id"],
                    revision_id=rev1_packet["revision_id"],
                )

                rev1 = _post_portkey_webhook(rev1_body)
                self.assertIs(rev1["verdict"], False)
                self.assertEqual(rev1["data"]["delivery_mode"], "live_guardrail_webhook")
                self.assertEqual(rev1["data"]["metadata_resolved_by"], "ia_review_run_id")
                self.assertEqual(rev1["data"]["review_run_id"], run_id)
                self.assertEqual(rev1["data"]["reason"], "packet_not_ready_for_portkey_movement")
                self.assertEqual(
                    rev1["data"]["ia_packet_reference"]["revision_id"],
                    rev1_packet["revision_id"],
                )

                attach_review_run_proof_api(
                    run_id,
                    ReviewRunProofAttachRequest(
                        proof_items=[
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                            {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
                            {"id": "environment_boundary", "label": "Environment boundary"},
                        ]
                    ),
                )
                rerun = rerun_review_run_packet_api(
                    run_id,
                    ReviewRunRerunRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                rev2_packet = rerun["run"]["packet"]

                stale = _post_portkey_webhook(rev1_body)
                self.assertIs(stale["verdict"], False)
                self.assertEqual(stale["data"]["reason"], "stale_packet_revision")
                self.assertEqual(
                    stale["data"]["ia_packet_reference"]["revision_id"],
                    rev2_packet["revision_id"],
                )

                rev2 = _post_portkey_webhook(
                    _portkey_review_run_body(
                        run_id=run_id,
                        packet_id=rev2_packet["packet_id"],
                        revision_id=rev2_packet["revision_id"],
                    )
                )
                self.assertIs(rev2["verdict"], True)
                self.assertEqual(rev2["data"]["reason"], "packet_allows_scoped_review_with_policy")
                self.assertEqual(rev2["data"]["requested_mode"], "scoped_validation")
                self.assertEqual(rev2["data"]["ia_packet_reference"]["source_of_truth"], "ReviewRun")
                self.assertFalse(rev2["data"]["safety"]["portkey_api_call_made"])
                self.assertFalse(rev2["data"]["safety"]["portkey_policy_mutation_allowed"])

                unsupported = _post_portkey_webhook(
                    _portkey_review_run_body(
                        run_id=run_id,
                        packet_id=rev2_packet["packet_id"],
                        revision_id=rev2_packet["revision_id"],
                        requested_mode="model_request",
                    )
                )
                self.assertIs(unsupported["verdict"], False)
                self.assertEqual(unsupported["data"]["reason"], "requested_mode_not_packet_scoped")

                events = list_portkey_guardrail_events(ledger_dir=ledger_dir)
                self.assertEqual(len(events), 4)
                self.assertEqual({event["review_run_id"] for event in events}, {run_id})
                self.assertEqual({event["kind"] for event in events}, {"portkey_byo_guardrail"})
                self.assertIn(True, {event["verdict"] for event in events})
                for event in events:
                    self.assertFalse(event["api_mutation"])
                    self.assertFalse(event["policy_mutation"])
                    self.assertFalse(event["external_writes"])

    def test_review_run_proof_api_stress_cases_fail_closed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                generated = generate_review_run_packet_api(
                    created["run"]["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                before_run = generated["run"]
                before_packet = before_run["packet"]
                before_portkey = before_run["portkey_preview"]

                for label, proof_items, expected in (
                    ("empty", [], "proof_items cannot be empty"),
                    (
                        "duplicate",
                        [
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                        ],
                        "duplicate proof item",
                    ),
                    (
                        "approval_shortcut",
                        [{"id": "repo_owner_approval", "evidence_note": "approve all blocked claims"}],
                        "cannot approve or override",
                    ),
                ):
                    with self.subTest(label=label):
                        with self.assertRaises(HTTPException) as exc:
                            attach_review_run_proof_api(
                                before_run["run_id"],
                                ReviewRunProofAttachRequest(proof_items=proof_items),
                            )
                        self.assertEqual(exc.exception.status_code, 400)
                        self.assertIn(expected, exc.exception.detail)

                with self.assertRaises(HTTPException) as missing:
                    attach_review_run_proof_api(
                        "ia-review-run-missing",
                        ReviewRunProofAttachRequest(
                            proof_items=[{"id": "repo_owner_approval", "label": "Repo owner approval"}]
                        ),
                    )
                self.assertEqual(missing.exception.status_code, 404)

                proofed = attach_review_run_proof_api(
                    before_run["run_id"],
                    ReviewRunProofAttachRequest(
                        proof_items=[
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                            {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
                            {"id": "environment_boundary", "label": "Environment boundary"},
                        ]
                    ),
                )

                self.assertIs(proofed["ok"], True)
                self.assertIs(proofed["read_only"], True)
                proofed_run = proofed["run"]
                proofed_packet = proofed["packet"]
                self.assertEqual(proofed_run["stage"], "proof_attached")
                self.assertEqual(proofed_run["packet"]["revision_id"], before_packet["revision_id"])
                self.assertEqual(proofed_run["packet"]["verdict"], before_packet["verdict"])
                self.assertIs(proofed_run["packet"]["ready_for_rerun"], True)
                self.assertEqual(proofed_run["portkey_preview"], before_portkey)
                self.assertEqual(len(proofed_run["attached_proof"]), 3)
                self.assertTrue(proofed_packet["proof_resolution"]["ready_for_rerun"])
                self.assertEqual(proofed_packet["proof_resolution"]["attached_proof_count"], 3)
                self.assertFalse(proofed_packet["proof_resolution"]["verdict_changed"])
                self.assertFalse(proofed_packet["proof_resolution"]["portkey_changed"])
                self.assertFalse(proofed_packet["safety_boundary"]["proof_attachment_changes_verdict"])
                proofed_lenses = proofed_packet["proof_resolution"]["owner_lenses"]
                self.assertEqual(
                    {lens["lens_id"] for lens in proofed_lenses["lenses"] if lens["active"]},
                    {"support_ops", "engineering", "security"},
                )
                for lens in proofed_lenses["lenses"]:
                    if lens["active"]:
                        self.assertEqual(len(lens["missing_proof"]), 0)
                        self.assertEqual(len(lens["attached_proof"]), 1)
                self.assertFalse(proofed_lenses["guardrails"]["proof_attachment_changes_verdict"])

                fetched = get_review_run(before_run["run_id"])
                self.assertEqual(fetched["run"]["stage"], "proof_attached")
                self.assertTrue(fetched["run"]["packet"]["ready_for_rerun"])

                with self.assertRaises(HTTPException) as repeated_proof:
                    attach_review_run_proof_api(
                        before_run["run_id"],
                        ReviewRunProofAttachRequest(
                            proof_items=[{"id": "repo_owner_approval", "label": "Repo owner approval"}]
                        ),
                    )
                self.assertEqual(repeated_proof.exception.status_code, 400)
                self.assertIn("proof attachment requires generated packet state", repeated_proof.exception.detail)

                with self.assertRaises(HTTPException) as rerun_without_rerun_api:
                    generate_review_run_packet_api(
                        before_run["run_id"],
                        ReviewRunPacketRequest(
                            access_request="support-triage-bot needs to read issues, comment, and create labels."
                        ),
                    )
                self.assertEqual(rerun_without_rerun_api.exception.status_code, 400)
                self.assertIn("packet generation requires repo_selected", rerun_without_rerun_api.exception.detail)

    def test_review_run_rerun_api_creates_updated_packet_delta(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                generated = generate_review_run_packet_api(
                    created["run"]["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )

                with self.assertRaises(HTTPException) as before_proof:
                    rerun_review_run_packet_api(
                        generated["run"]["run_id"],
                        ReviewRunRerunRequest(
                            access_request="support-triage-bot needs to read issues, comment, and create labels."
                        ),
                    )
                self.assertEqual(before_proof.exception.status_code, 400)
                self.assertIn("rerun requires proof_attached", before_proof.exception.detail)

                proofed = attach_review_run_proof_api(
                    generated["run"]["run_id"],
                    ReviewRunProofAttachRequest(
                        proof_items=[
                            {"id": "repo_owner_approval", "label": "Repo owner approval"},
                            {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
                            {"id": "environment_boundary", "label": "Environment boundary"},
                        ]
                    ),
                )

                with self.assertRaises(HTTPException) as changed_request:
                    rerun_review_run_packet_api(
                        generated["run"]["run_id"],
                        ReviewRunRerunRequest(access_request="support-triage-bot now wants repo admin"),
                    )
                self.assertEqual(changed_request.exception.status_code, 400)
                self.assertIn("raw agent request cannot change before rerun", changed_request.exception.detail)

                rerun = rerun_review_run_packet_api(
                    generated["run"]["run_id"],
                    ReviewRunRerunRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )

                self.assertIs(rerun["ok"], True)
                self.assertIs(rerun["read_only"], True)
                updated_run = rerun["run"]
                packet = rerun["packet"]
                delta = rerun["review_delta"]
                self.assertEqual(updated_run["stage"], "ready_to_export")
                self.assertEqual(updated_run["packet"]["previous_revision_id"], proofed["run"]["packet"]["revision_id"])
                self.assertNotEqual(updated_run["packet"]["revision_id"], proofed["run"]["packet"]["revision_id"])
                self.assertEqual(updated_run["packet"]["revision_number"], 2)
                self.assertEqual(updated_run["packet"]["verdict"], "ready_with_gates")
                self.assertFalse(updated_run["packet"]["ready_for_rerun"])
                self.assertEqual(packet["decision"]["verdict_class"], "ready_with_gates")
                self.assertFalse(packet["decision"]["requires_human_review"])
                self.assertEqual(packet["compact_output"]["allowed"], ["read issues", "comment", "create labels in selected repo"])
                self.assertEqual(packet["compact_output"]["blocked"], ["repo admin", "org-wide write", "secrets"])
                self.assertTrue(packet["review_delta"]["same_request"])
                self.assertTrue(packet["review_delta"]["packet_changed"])
                self.assertEqual(delta["packet_revision_before"], proofed["run"]["packet"]["revision_id"])
                self.assertEqual(delta["packet_revision_after"], updated_run["packet"]["revision_id"])
                self.assertEqual(delta["portkey_before"], "Block")
                self.assertEqual(delta["portkey_after"], "Allow with policy")
                self.assertEqual(delta["still_blocked"], ["repo admin", "org-wide write", "secrets"])
                self.assertEqual(rerun["portkey"]["state"], "Allow with policy")
                self.assertTrue(rerun["portkey"]["portkey_guardrail_response"]["verdict"])
                self.assertFalse(rerun["portkey"]["api_call_made"])
                self.assertFalse(rerun["portkey"]["policy_mutation_allowed"])

                with self.assertRaises(HTTPException) as repeated:
                    rerun_review_run_packet_api(
                        generated["run"]["run_id"],
                        ReviewRunRerunRequest(
                            access_request="support-triage-bot needs to read issues, comment, and create labels."
                        ),
                    )
                self.assertEqual(repeated.exception.status_code, 400)
                self.assertIn("rerun requires proof_attached", repeated.exception.detail)

    def test_review_run_coach_api_stress_prompts_are_state_anchored(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                run_id = created["run"]["run_id"]

                greeting = coach_review_run_api(run_id, ReviewRunCoachRequest(prompt="hey"))
                self.assertTrue(greeting["ok"])
                self.assertTrue(greeting["read_only"])
                self.assertEqual(greeting["answer"]["schema_version"], "review_run_coach_answer.v0")
                self.assertEqual(greeting["stage"], "repo_selected")
                self.assertLessEqual(len(greeting["suggestions"]), 3)
                self.assertEqual(greeting["suggestions"][0]["schema_version"], "coach_suggestion.v0")
                self.assertEqual(greeting["suggestions"][0]["entities"]["run_id"], run_id)
                self.assertEqual(greeting["suggestions"][0]["entities"]["stage"], "repo_selected")
                self.assertEqual(greeting["suggestions"][0]["entities"]["subscriber"], "cto")
                self.assertEqual(greeting["answer"]["prompt_kind"], "greeting")
                self.assertIn("No packet exists yet", greeting["answer"]["sections"]["current_read"])
                self.assertFalse(greeting["answer"]["safety_boundary"]["approval_granted"])
                self.assertFalse(greeting["answer"]["safety_boundary"]["external_writes"])
                self.assertFalse(greeting["answer"]["safety_boundary"]["raw_packet_dumped"])

                message_contract = coach_review_run_api(
                    run_id,
                    ReviewRunCoachRequest(
                        message="idk what to do next",
                        entities={
                            "source": "review_run",
                            "prompt_kind": "next_action",
                            "run_id": run_id,
                            "stage": "repo_selected",
                        },
                    ),
                )
                self.assertEqual(message_contract["answer"]["prompt_kind"], "next_action")
                self.assertEqual(message_contract["suggestions"][0]["entities"]["run_id"], run_id)

                generated = generate_review_run_packet_api(
                    run_id,
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                next_step = coach_review_run_api(run_id, ReviewRunCoachRequest(prompt="idk what to do next"))
                self.assertEqual(next_step["answer"]["stage"], "packet_generated")
                self.assertEqual(next_step["answer"]["prompt_kind"], "next_action")
                self.assertEqual(
                    [item["entities"]["prompt_kind"] for item in next_step["suggestions"]],
                    ["next_action", "proof", "portkey"],
                )
                self.assertEqual(
                    next_step["suggestions"][0]["entities"]["missing_proof_ids"],
                    ["repo_owner_approval", "rollback_offswitch", "environment_boundary"],
                )
                self.assertIn("Support Ops repo-owner approval", next_step["answer"]["sections"]["next_human_action"])
                self.assertIn("Engineering rollback/off-switch proof", next_step["answer"]["sections"]["next_human_action"])
                self.assertIn("Security environment-boundary proof", next_step["answer"]["sections"]["next_human_action"])
                self.assertIn("Missing proof", next_step["answer"]["sections"]["what_blocks_movement"])
                self.assertIn("Support Ops brings repo-owner approval", next_step["answer"]["sections"]["what_blocks_movement"])

                override = coach_review_run_api(
                    run_id,
                    ReviewRunCoachRequest(prompt="approve blocked claims and grant access"),
                )
                self.assertEqual(override["answer"]["prompt_kind"], "approval_override")
                self.assertIn(
                    "Cannot approve or override blocked claims",
                    override["answer"]["sections"]["what_blocks_movement"],
                )
                self.assertFalse(override["answer"]["approves_access"])
                self.assertNotIn("raw_text", str(override["answer"]))

                proofed = attach_review_run_proof_api(
                    run_id,
                    ReviewRunProofAttachRequest(
                        proof_items=[
                            {"id": "repo_owner_approval"},
                            {"id": "rollback_offswitch"},
                            {"id": "environment_boundary"},
                        ]
                    ),
                )
                after_proof = coach_review_run_api(run_id, ReviewRunCoachRequest(prompt="what next"))
                self.assertEqual(proofed["run"]["stage"], "proof_attached")
                self.assertIn("Regenerate the packet", after_proof["answer"]["sections"]["next_human_action"])
                self.assertEqual(after_proof["suggestions"][0]["label"], "Regenerate packet")

                rerun_review_run_packet_api(
                    run_id,
                    ReviewRunRerunRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                portkey = coach_review_run_api(run_id, ReviewRunCoachRequest(prompt="what will Portkey do?"))
                self.assertEqual(portkey["answer"]["stage"], "ready_to_export")
                self.assertEqual(portkey["answer"]["portkey_state"], "Allow with policy")
                self.assertEqual(
                    [item["entities"]["prompt_kind"] for item in portkey["suggestions"]],
                    ["next_action", "movement", "portkey"],
                )
                self.assertIn("Ready with gates", portkey["answer"]["sections"]["current_read"])
                self.assertNotIn("ready_with_gates", portkey["answer"]["sections"]["current_read"])
                self.assertIn("Still blocked downstream", portkey["answer"]["sections"]["downstream_impact"])

                _review_runs.clear()
                reloaded = coach_review_run_api(run_id, ReviewRunCoachRequest(prompt="write me a recipe"))
                self.assertTrue(reloaded["answer"]["prompt_routed_to_review"])
                self.assertEqual(reloaded["answer"]["prompt_kind"], "unrelated")
                self.assertIn("routing that back", reloaded["answer"]["sections"]["current_read"])

    def test_review_run_rerun_api_rejects_partial_proof(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                generated = generate_review_run_packet_api(
                    created["run"]["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                attach_review_run_proof_api(
                    generated["run"]["run_id"],
                    ReviewRunProofAttachRequest(
                        proof_items=[{"id": "repo_owner_approval", "label": "Repo owner approval"}]
                    ),
                )

                with self.assertRaises(HTTPException) as partial:
                    rerun_review_run_packet_api(
                        generated["run"]["run_id"],
                        ReviewRunRerunRequest(
                            access_request="support-triage-bot needs to read issues, comment, and create labels."
                        ),
                    )
                self.assertEqual(partial.exception.status_code, 400)
                self.assertIn("rerun requires all missing proof", partial.exception.detail)

    def test_review_run_api_rejects_request_without_repo(self) -> None:
        with self.assertRaises(HTTPException) as exc:
            create_review_run_api(ReviewRunCreateRequest(access_request="read issues"))

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("selected_repo is required", exc.exception.detail)

    def test_review_run_api_bad_or_unknown_run_ids_fail_closed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                with self.assertRaises(HTTPException) as bad:
                    get_review_run("../escape")
                self.assertEqual(bad.exception.status_code, 400)

                with self.assertRaises(HTTPException) as missing:
                    get_review_run("ia-review-run-missing")
                self.assertEqual(missing.exception.status_code, 404)

    def test_review_run_api_routes_are_create_and_read_only(self) -> None:
        post_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs")
        get_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}")
        packet_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}/packet")
        proof_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}/proof")
        rerun_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}/rerun")
        coach_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}/coach")
        proofgraph_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}/proofgraph")

        self.assertEqual(post_route.methods, {"POST"})
        self.assertEqual(get_route.methods, {"GET"})
        self.assertEqual(packet_route.methods, {"POST"})
        self.assertEqual(proof_route.methods, {"POST"})
        self.assertEqual(rerun_route.methods, {"POST"})
        self.assertEqual(coach_route.methods, {"POST"})
        self.assertEqual(proofgraph_route.methods, {"GET"})

    def test_demo_github_repo_select_creates_safe_review_run(self) -> None:
        session_id = "review-run-root-demo-flow"
        demo_sign_in(session_id, "github")

        repos = github_list_repos(session_id=session_id, q="triage")
        self.assertTrue(repos["ok"])
        self.assertTrue(repos["demo"])
        selected = repos["repos"][0]

        attached = github_attach_repo(
            GithubAttachRequest(session_id=session_id, full_name=selected["full_name"])
        )
        self.assertTrue(attached["ok"])
        self.assertGreater(attached["digest_chars"], 100)

        created = create_review_run_api(
            ReviewRunCreateRequest(
                session_id=session_id,
                selected_repo={
                    "provider": "github",
                    "full_name": selected["full_name"],
                    "source": "demo_repo",
                },
                repo_index_summary={
                    "status": "indexed",
                    "indexed_repo_count": 1,
                    "digest_chars": attached["digest_chars"],
                    "readme_found": attached["readme_found"],
                    "files_included": attached["files_included"],
                    "paths_in_tree": attached["paths_in_tree"],
                    "sample_paths": attached["sample_paths"],
                },
            )
        )

        run = created["run"]
        self.assertTrue(created["read_only"])
        self.assertEqual(run["stage"], "repo_selected")
        self.assertEqual(run["selected_repo"]["full_name"], selected["full_name"])
        self.assertEqual(run["repo_index_summary"]["status"], "indexed")
        self.assertEqual(run["repo_index_summary"]["indexed_repo_count"], 1)
        self.assertFalse(run["access_request"])
        self.assertFalse(run["safety_invariants"]["approval_granted"])
        self.assertFalse(run["safety_invariants"]["external_writes_enabled"])
