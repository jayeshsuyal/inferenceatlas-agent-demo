"""Portkey guardrail proof-loop read model tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agent.portkey_guardrail_proof_loop import (
    PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION,
    build_portkey_guardrail_proof_loop,
    render_portkey_guardrail_proof_loop_markdown,
)
from web.app import app, portkey_guardrail_proof_loop


ROOT = Path(__file__).resolve().parents[1]


def test_portkey_guardrail_proof_loop_blocks_spend_from_packet_truth() -> None:
    payload = build_portkey_guardrail_proof_loop(
        fixture="ai_spend_budget_overrun",
        requested_mode="model_request",
        generated_at="2026-06-09T00:00:00Z",
    )

    assert payload["schema_version"] == PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION
    assert payload["delivery_mode"] == "live_guardrail_webhook"
    assert payload["portkey_call"]["method"] == "POST"
    assert payload["portkey_call"]["path"] == "/api/portkey/guardrail"
    assert payload["portkey_call"]["auth_required"] is True
    assert payload["portkey_call"]["response_verdict"] is False
    assert payload["portkey_call"]["event_recording"]["webhook_records_event"] is True
    assert payload["portkey_call"]["event_recording"]["preview_written_to_ledger"] is False

    assert payload["ia_packet_reference"]["packet_id"] == "ia-spend-review-ai_spend_budget_overrun-v0"
    assert payload["packet_truth"]["verdict"] is False
    assert payload["packet_truth"]["verdict_class"] == "finance_procurement_review_required"
    assert payload["packet_truth"]["reason"] == "requested_mode_not_packet_scoped"
    assert payload["packet_truth"]["deny_reasons"]
    assert payload["packet_truth"]["next_human_action"]

    assert payload["portkey_policy_preview"]["api_call_made"] is False
    assert payload["portkey_policy_preview"]["usage_policy_plan"]["request_body"]["credit_limit"] == 0
    assert payload["portkey_policy_preview"]["dry_run_diff"]["proposed_policy_from_packet"][
        "guardrail_verdict"
    ] is False

    invariants = payload["invariants"]
    assert invariants["read_only"] is True
    assert invariants["raw_agent_intent_trusted"] is False
    assert invariants["packet_mutation_allowed"] is False
    assert invariants["portkey_policy_mutation_allowed"] is False
    assert invariants["portkey_api_call_made"] is False
    assert invariants["auth_required"] is True
    assert invariants["no_token_fails_safe"] is True
    assert invariants["packet_remains_authority"] is True


def test_portkey_guardrail_proof_loop_can_show_scoped_validation_allowed_without_approval() -> None:
    payload = build_portkey_guardrail_proof_loop(
        fixture="read_only_analytics_agent",
        requested_mode="read_only_validation",
        generated_at="2026-06-09T00:00:00Z",
    )

    assert payload["packet_truth"]["verdict"] is True
    assert payload["packet_truth"]["verdict_class"] == "read_only_validation"
    assert payload["packet_truth"]["reason"] == "packet_allows_scoped_validation_only"
    assert payload["packet_truth"]["deny_reasons"] == []
    assert payload["safety"]["approves_access"] is False
    assert payload["safety"]["executes_external_writes"] is False
    assert payload["invariants"]["portkey_api_call_made"] is False
    assert payload["invariants"]["portkey_policy_mutation_allowed"] is False


def test_portkey_guardrail_proof_loop_api_is_read_only_get() -> None:
    response = portkey_guardrail_proof_loop("ai_spend_budget_overrun", requested_mode="model_request")

    assert response["ok"] is True
    assert response["read_only"] is True
    payload = response["portkey_guardrail_proof_loop"]
    assert payload["schema_version"] == PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION
    assert payload["portkey_call"]["auth_required"] is True
    assert payload["invariants"]["preview_does_not_write_ledger"] is True

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", "") == "/api/packets/{fixture}/downstream/portkey/proof-loop"
    )
    assert route.methods == {"GET"}


def test_portkey_guardrail_proof_loop_cli_and_markdown_are_safe() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.portkey_guardrail_proof_loop",
            "--fixture",
            "ai_spend_budget_overrun",
            "--requested-mode",
            "model_request",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION
    assert payload["portkey_call"]["response_verdict"] is False
    assert payload["invariants"]["portkey_api_call_made"] is False
    assert payload["private_boundary"]["private_source_exposed"] is False

    rendered = render_portkey_guardrail_proof_loop_markdown(payload)
    assert "Portkey Guardrail Proof Loop" in rendered
    assert "IA returned a packet-backed verdict only" in rendered
    assert "Portkey API call made: False" in rendered
    assert "sk-proj-" not in rendered
    assert "tvly-" not in rendered
    assert "ak_" not in rendered
