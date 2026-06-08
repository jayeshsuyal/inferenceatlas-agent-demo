"""Durable sponsor proof run ledger tests."""

from __future__ import annotations

from pathlib import Path

from agent.sponsor_proof_collector import build_sponsor_proof_collector_run
from agent.sponsor_run_ledger import (
    SPONSOR_PROOF_RUN_LEDGER_SCHEMA_VERSION,
    SPONSOR_PROOF_RUN_RECORD_SCHEMA_VERSION,
    build_sponsor_proof_run_ledger,
    load_sponsor_proof_run_record,
    sponsor_proof_run_record_summary,
    write_sponsor_proof_run_record,
)
from agent.sponsor_proof_trace import SPONSOR_ORDER
from agent.trial import DEFAULT_TRIAL_REQUEST
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


def test_sponsor_run_ledger_persists_public_run_record(tmp_path: Path) -> None:
    run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST)
    record = write_sponsor_proof_run_record(run, ledger_dir=tmp_path)
    loaded = load_sponsor_proof_run_record(run["run_id"], ledger_dir=tmp_path)

    assert loaded == record
    assert record["schema_version"] == SPONSOR_PROOF_RUN_RECORD_SCHEMA_VERSION
    assert record["run_id"] == run["run_id"]
    assert record["record_path"].endswith(f"{run['run_id']}.json")
    assert record["request"] == {
        "request_path": "examples/requests/support_triage_trial.yml",
        "scenario_name": "support_triage_agent",
        "lane": "both",
        "downstream_fixture": "ai_spend_budget_overrun",
        "subscriber": "portkey_model_spend_gate",
        "question": "Can Portkey allow this spend?",
    }
    assert record["packet_reference"] == run["packet_reference"]
    assert record["trace_reference"] == run["trace_reference"]
    assert [step["sponsor"] for step in record["sponsor_steps"]] == list(SPONSOR_ORDER)
    assert record["fallback_used"] == {
        "tavily": True,
        "composio": True,
        "openclaw": True,
        "nebius": True,
    }
    assert record["live_key_used"] == {
        "tavily": False,
        "composio": False,
        "openclaw": False,
        "nebius": False,
    }
    assert record["output_artifacts"]["run_record_json"].endswith(".json")
    assert record["output_artifacts"]["portkey_preview"] == (
        "embedded:run.downstream_previews.portkey_model_spend_gate"
    )
    assert record["run"] == run


def test_sponsor_run_ledger_safety_lock_is_non_mutating(tmp_path: Path) -> None:
    run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST)
    record = write_sponsor_proof_run_record(run, ledger_dir=tmp_path)
    safety = record["safety_lock"]

    assert safety["read_only"] is True
    assert safety["live_calls_made"] is False
    assert safety["approves_access"] is False
    assert safety["grants_permissions"] is False
    assert safety["executes_external_writes"] is False
    assert safety["mutates_production"] is False
    assert safety["approves_spend"] is False
    assert safety["selects_provider"] is False
    assert safety["guarantees_savings"] is False
    assert safety["requires_human_review"] is True
    assert safety["decision_lock_unchanged"] is True
    assert safety["packet_mutation_allowed"] is False
    assert safety["downstream_can_override_packet"] is False


def test_sponsor_run_ledger_lists_records_without_full_run_duplication(tmp_path: Path) -> None:
    run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST)
    record = write_sponsor_proof_run_record(run, ledger_dir=tmp_path)
    ledger = build_sponsor_proof_run_ledger([record])

    assert ledger["schema_version"] == SPONSOR_PROOF_RUN_LEDGER_SCHEMA_VERSION
    assert ledger["mode"] == "local_durable_read_model"
    assert ledger["read_only"] is True
    assert ledger["record_count"] == 1
    assert ledger["sponsor_order"] == list(SPONSOR_ORDER)
    assert ledger["runs"] == [sponsor_proof_run_record_summary(record)]
    assert "run" not in ledger["runs"][0]
    assert ledger["safety_summary"] == {
        "all_read_only": True,
        "no_live_calls": True,
        "no_approvals": True,
        "no_grants": True,
        "no_external_writes": True,
        "no_production_mutation": True,
        "no_spend_approval": True,
        "no_provider_selection": True,
        "no_savings_guarantee": True,
        "all_require_human_review": True,
        "all_decision_locks_unchanged": True,
    }

    rendered = str(ledger)
    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden not in rendered
