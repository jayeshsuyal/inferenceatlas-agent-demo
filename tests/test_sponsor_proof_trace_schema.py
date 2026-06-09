"""SponsorProofTrace public schema and authority-boundary tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent.nebius_reviewer_narration import NEBIUS_REQUIRED_SAFETY_ANCHOR
from agent.sponsor_proof_trace import (
    ALLOWED_VERBS_PER_SPONSOR,
    SPONSOR_ORDER,
    SPONSOR_PROOF_TRACE_SCHEMA_VERSION,
    build_sponsor_proof_trace,
)
from agent.trial import DEFAULT_TRIAL_REQUEST
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "sponsor_proof_trace.schema.json"
GENERATED_TRACE_PATH = ROOT / "examples" / "generated" / "support_triage_trial.sponsor_proof_trace.json"

BASELINE_REQUIRED_FIELDS = {
    "schema_version",
    "trace_id",
    "content_hash",
    "packet_id",
    "revision_id",
    "scenario_name",
    "lane",
    "sponsor_steps",
    "blocked_actions",
    "access_review_evidence",
    "spend_review_evidence",
    "decision_lock_before",
    "decision_lock_after",
    "fallback_used",
    "generated_at",
    "source_artifacts",
    "safety_boundary",
    "private_boundary",
}

LOCKED_FALSE_FIELDS = (
    "production_access",
    "permission_grants",
    "external_writes",
    "approval_granted",
    "spend_approved",
    "provider_winner_selected",
    "savings_guaranteed",
    "can_sponsor_change_decision",
)

SAFETY_FALSE_FIELDS = (
    "approves_access",
    "grants_permissions",
    "executes_external_writes",
    "mutates_production",
    "approves_spend",
    "selects_provider",
    "guarantees_savings",
)


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_generated() -> dict:
    return json.loads(GENERATED_TRACE_PATH.read_text(encoding="utf-8"))


def _assert_required_fields(payload: dict, required: set[str]) -> None:
    missing = required - set(payload)
    assert not missing, f"missing required fields: {sorted(missing)}"


def _assert_standard_invariants(trace: dict) -> None:
    _assert_required_fields(trace, BASELINE_REQUIRED_FIELDS)
    assert trace["schema_version"] == SPONSOR_PROOF_TRACE_SCHEMA_VERSION
    assert re.fullmatch(r"ia-sponsor-proof-trace-.+-[0-9a-f]{16}-public-v0", trace["trace_id"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", trace["content_hash"])
    assert re.fullmatch(r"rev_[0-9a-f]{16}", trace["revision_id"])
    assert trace["lane"] in {"access_review", "spend_review", "both"}
    assert tuple(step["sponsor"] for step in trace["sponsor_steps"]) == SPONSOR_ORDER
    assert trace["decision_lock_before"] == trace["decision_lock_after"]
    assert set(trace["fallback_used"]) == set(SPONSOR_ORDER)

    for field in LOCKED_FALSE_FIELDS:
        assert trace["decision_lock_before"][field] is False
        assert trace["decision_lock_after"][field] is False

    for field in SAFETY_FALSE_FIELDS:
        assert trace["safety_boundary"][field] is False
    assert trace["safety_boundary"]["requires_human_review"] is True
    assert trace["private_boundary"] == {
        "private_source_exposed": False,
        "principle": "Private engine, public proof.",
    }

    for step in trace["sponsor_steps"]:
        assert step["step_verb"] == ALLOWED_VERBS_PER_SPONSOR[step["sponsor"]]
        assert step["would_execute"] is False
        assert step["can_approve_access"] is False
        assert step["can_grant_permissions"] is False
        assert step["can_mutate_external_state"] is False
        assert step["human_review_required"] is True
        assert {"api_key", "authorization", "secret", "token"}.issubset(step["redacted_fields"])


def _fake_nebius_client() -> SimpleNamespace:
    content = (
        "{"
        '"reviewer_summary":"IA does not approve this request. The packet remains blocked for live movement until proof is reviewed.",'
        '"decision_lock_sentence":"Human review is required before any access, spend, or production movement. Decision lock unchanged.",'
        '"next_human_action":"Route the packet to the named owners with proof debt attached.",'
        f'"safety_anchor":"{NEBIUS_REQUIRED_SAFETY_ANCHOR}"'
        "}"
    )
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                )
            )
        )
    )


def test_schema_file_locks_public_trace_contract() -> None:
    schema = _load_schema()

    assert schema["properties"]["schema_version"]["const"] == SPONSOR_PROOF_TRACE_SCHEMA_VERSION
    assert set(schema["required"]) == BASELINE_REQUIRED_FIELDS
    assert schema["properties"]["lane"]["enum"] == ["access_review", "spend_review", "both"]
    assert schema["properties"]["sponsor_steps"]["minItems"] == 4

    step_schema = schema["$defs"]["sponsor_step"]["properties"]
    assert step_schema["sponsor"]["enum"] == list(SPONSOR_ORDER)
    assert step_schema["step_verb"]["enum"] == [
        ALLOWED_VERBS_PER_SPONSOR[sponsor] for sponsor in SPONSOR_ORDER
    ]
    assert step_schema["would_execute"]["const"] is False
    assert step_schema["can_approve_access"]["const"] is False
    assert step_schema["can_grant_permissions"]["const"] is False
    assert step_schema["can_mutate_external_state"]["const"] is False
    assert step_schema["human_review_required"]["const"] is True

    safety_schema = schema["$defs"]["safety_boundary"]["properties"]
    for field in SAFETY_FALSE_FIELDS:
        assert safety_schema[field]["const"] is False
    assert safety_schema["requires_human_review"]["const"] is True
    assert schema["$defs"]["private_boundary"]["properties"]["principle"]["const"] == (
        "Private engine, public proof."
    )


def test_generated_sponsor_trace_matches_schema_required_shape() -> None:
    generated = _load_generated()

    _assert_standard_invariants(generated)
    assert generated["source_artifacts"]["request"] == "examples/requests/support_triage_trial.yml"
    assert generated["source_artifacts"]["packet"] == "examples/generated/support_triage_trial.packet.json"
    assert generated["source_artifacts"]["sponsor_readiness"] == "examples/generated/sponsor_live_readiness.json"
    assert generated["source_artifacts"]["spend_packet"] == (
        "examples/generated/ai_spend_budget_overrun.spend_packet.json"
    )


def test_default_trace_keeps_decision_lock_and_sponsor_authority() -> None:
    trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)

    _assert_standard_invariants(trace)
    assert trace["fallback_used"] == {
        "tavily": True,
        "composio": True,
        "openclaw": True,
        "nebius": True,
    }
    assert "live_proof" not in trace
    assert "dry_run_proof" not in trace


def test_live_and_dry_run_extensions_keep_same_standard_boundary() -> None:
    with patch("agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_reviewer_narration.config.LLM_API_KEY", "test-key"
    ):
        trace = build_sponsor_proof_trace(
            DEFAULT_TRIAL_REQUEST,
            live_nebius=True,
            composio_dry_run=True,
            nebius_client_factory=_fake_nebius_client,
        )

    _assert_standard_invariants(trace)

    nebius = trace["live_proof"]["nebius"]
    assert nebius["status"] == "live_reviewer_narration_built"
    assert nebius["live_call_count"] == 1
    assert nebius["used_live_key"] is True
    assert nebius["fallback_used"] is False
    assert nebius["can_approve_access"] is False
    assert nebius["can_grant_permissions"] is False
    assert nebius["can_mutate_external_state"] is False
    assert nebius["required_anchors_present"] is True
    assert nebius["forbidden_phrases_present"] == []

    composio = trace["dry_run_proof"]["composio"]
    assert composio["status"] == "dry_run_permission_diff_built"
    assert composio["dry_run_enforced"] is True
    assert composio["api_call_made"] is False
    assert composio["composio_execute_allowed"] is False
    assert composio["used_live_key"] is False
    assert composio["fallback_used"] is True
    assert composio["can_approve_access"] is False
    assert composio["can_grant_permissions"] is False
    assert composio["can_mutate_external_state"] is False


def test_schema_public_boundary_does_not_expose_private_terms() -> None:
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")

    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden not in schema_text


def test_pr_smoke_checks_sponsor_proof_trace_schema() -> None:
    smoke_text = (ROOT / "scripts" / "pr_smoke.sh").read_text(encoding="utf-8")

    assert "schemas/sponsor_proof_trace.schema.json" in smoke_text
