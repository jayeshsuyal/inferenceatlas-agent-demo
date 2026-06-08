"""Portkey dry-run adapter contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agent.portkey_adapter import (
    PORTKEY_ADAPTER_SCHEMA_VERSION,
    PORTKEY_GUARDRAIL_DOC_URL,
    PORTKEY_USAGE_LIMIT_DOC_URL,
    build_portkey_adapter_payload,
)
from web.app import app, portkey_downstream_preview


ROOT = Path(__file__).resolve().parents[1]


def test_portkey_adapter_generates_docs_cited_dry_run_contract() -> None:
    payload = build_portkey_adapter_payload(
        fixture="ai_spend_budget_overrun",
        mode="dry-run",
    )

    assert payload["schema_version"] == PORTKEY_ADAPTER_SCHEMA_VERSION
    assert payload["mode"] == "dry-run"
    assert payload["dry_run"] is True
    assert payload["api_call_made"] is False
    assert payload["docs_reference"]["guardrail_webhook"] == PORTKEY_GUARDRAIL_DOC_URL
    assert payload["docs_reference"]["usage_limit_policy"] == PORTKEY_USAGE_LIMIT_DOC_URL
    assert payload["ia_packet_reference"]["packet_id"] == "ia-spend-review-ai_spend_budget_overrun-v0"
    assert payload["packet_truth"]["verdict_class"] == "finance_procurement_review_required"
    assert payload["packet_truth"]["approves_spend"] is False
    assert payload["packet_truth"]["selects_provider"] is False
    assert payload["packet_truth"]["guarantees_savings"] is False
    assert payload["packet_truth"]["requires_human_review"] is True


def test_portkey_guardrail_verdict_tracks_ia_packet_lock() -> None:
    payload = build_portkey_adapter_payload(fixture="ai_spend_budget_overrun")

    guardrail = payload["portkey_guardrail_response"]
    assert guardrail == {
        "verdict": False,
        "data": {
            "ia_packet_id": "ia-spend-review-ai_spend_budget_overrun-v0",
            "ia_revision_id": "rev_47f8ff3775dec3c5",
            "deny_reasons": payload["deny_reasons"],
            "next_human_action": payload["packet_truth"]["next_human_action"],
        },
    }
    assert payload["dry_run_diff"]["proposed_policy_from_packet"]["guardrail_verdict"] is False
    assert payload["invariants"]["raw_agent_intent_trusted"] is False
    assert payload["invariants"]["packet_mutation_allowed"] is False
    assert payload["invariants"]["portkey_api_call_made"] is False
    assert payload["invariants"]["live_mutation_enabled"] is False


def test_portkey_usage_policy_plan_matches_documented_shape() -> None:
    payload = build_portkey_adapter_payload(fixture="ai_spend_budget_overrun")
    request_body = payload["usage_policy_plan"]["request_body"]

    assert sorted(request_body) == [
        "alert_threshold",
        "conditions",
        "credit_limit",
        "group_by",
        "name",
        "periodic_reset",
        "type",
    ]
    assert request_body["conditions"] == [
        {
            "key": "metadata.ia_packet_id",
            "value": "ia-spend-review-ai_spend_budget_overrun-v0",
        },
        {
            "key": "metadata.ia_revision_id",
            "value": "rev_47f8ff3775dec3c5",
        },
    ]
    assert request_body["group_by"] == [{"key": "api_key"}]
    assert request_body["type"] == "cost"
    assert request_body["credit_limit"] == 0
    assert request_body["periodic_reset"] == "monthly"


def test_portkey_adapter_cli_emits_machine_readable_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.portkey_adapter",
            "--fixture",
            "ai_spend_budget_overrun",
            "--mode",
            "dry-run",
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
    assert payload["schema_version"] == PORTKEY_ADAPTER_SCHEMA_VERSION
    assert payload["portkey_guardrail_response"]["verdict"] is False
    assert payload["api_call_made"] is False


def test_portkey_adapter_refuses_live_mode_even_with_explicit_flag() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.portkey_adapter",
            "--fixture",
            "ai_spend_budget_overrun",
            "--mode",
            "live",
            "--i-understand-this-mutates-production",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 2
    assert "live Portkey mutation is disabled" in proc.stderr
    assert proc.stdout == ""


def test_portkey_adapter_api_is_read_only_get_preview() -> None:
    response = portkey_downstream_preview("ai_spend_budget_overrun", mode="dry-run")

    assert response["ok"] is True
    assert response["read_only"] is True
    payload = response["portkey"]
    assert payload["schema_version"] == PORTKEY_ADAPTER_SCHEMA_VERSION
    assert payload["api_call_made"] is False
    assert payload["portkey_guardrail_response"]["verdict"] is False

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", "") == "/api/packets/{fixture}/downstream/portkey"
    )
    assert route.methods == {"GET"}
