"""Sponsor proof collector backend contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException

from agent.portkey_adapter import PORTKEY_ADAPTER_SCHEMA_VERSION
from agent.sponsor_proof_collector import (
    SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION,
    build_sponsor_proof_collector_run,
    render_sponsor_proof_collector_markdown,
    write_sponsor_proof_collector_artifacts,
)
from agent.sponsor_proof_trace import SPONSOR_ORDER
from agent.trial import DEFAULT_TRIAL_REQUEST
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS
from web.app import (
    SPONSOR_PROOF_RUN_LEDGER_DIR,
    SponsorProofRunRequest,
    _sponsor_proof_runs,
    app,
    create_sponsor_proof_run,
    get_sponsor_proof_run,
    sponsor_proof_run_ledger,
)


ROOT = Path(__file__).resolve().parents[1]


def test_collector_run_wraps_trace_advisor_and_portkey_preview() -> None:
    run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST)

    assert run["schema_version"] == SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION
    assert run["run_id"].startswith("ia-sponsor-proof-run-support_triage_trial-")
    assert run["mode"] == "offline_dry_run"
    assert run["status"] == "completed"
    assert run["run_type"] == "agentic_proof_collection"
    assert run["collector_claim"] == (
        "The collector gathers sponsor proof and downstream previews; "
        "the IA Packet remains the authority."
    )

    assert run["packet_reference"] == {
        "packet_id": "ia-agent-access-support-triage-v0",
        "revision_id": "rev_965302783cee8688",
        "content_hash": "sha256:965302783cee86882b5ceaf5c7b25aace54bcee9071a645191421d82c1f4131d",
        "source": "packet_authority_snapshot",
    }
    assert run["trace_reference"]["trace_id"] == run["sponsor_proof_trace"]["trace_id"]
    assert run["trace_reference"]["content_hash"] == run["sponsor_proof_trace"]["content_hash"]
    assert run["packet_advisor_answer"]["schema_version"] == "packet_advisor_answer.v0"
    assert run["packet_advisor_answer"]["subscriber"] == "portkey_model_spend_gate"
    assert run["packet_advisor_answer"]["downstream_gate"]["requested_action_can_proceed"] is False

    portkey = run["downstream_previews"]["portkey_model_spend_gate"]
    assert portkey["schema_version"] == PORTKEY_ADAPTER_SCHEMA_VERSION
    assert portkey["mode"] == "dry-run"
    assert portkey["api_call_made"] is False
    assert portkey["portkey_guardrail_response"]["verdict"] is False
    assert portkey["usage_policy_plan"]["request_body"]["credit_limit"] == 0


def test_collector_invariants_lock_sponsor_order_and_no_mutation() -> None:
    run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST)

    assert tuple(step["sponsor"] for step in run["collector_steps"]) == SPONSOR_ORDER
    assert run["invariants"] == {
        "sponsor_order_locked": True,
        "decision_lock_unchanged": True,
        "fallback_shape_available": True,
        "raw_agent_intent_trusted": False,
        "packet_mutation_allowed": False,
        "external_writes_enabled": False,
        "portkey_api_call_made": False,
        "downstream_can_override_packet": False,
    }

    for step in run["collector_steps"]:
        assert step["status"] == "completed_fallback"
        assert step["used_live_key"] is False
        assert step["fallback_used"] is True
        assert step["would_execute"] is False
        assert step["can_approve_access"] is False
        assert step["can_grant_permissions"] is False
        assert step["can_mutate_external_state"] is False
        assert step["human_review_required"] is True

    safety = run["safety_boundary"]
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


def test_collector_markdown_is_public_safe_and_skim_ready() -> None:
    markdown = render_sponsor_proof_collector_markdown(
        build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST)
    )

    for expected in [
        "# Sponsor Proof Collector Run",
        "Private engine, public proof.",
        "The collector gathers proof; it does not approve, grant, write, spend, select providers, or mutate production.",
        "| 1 | tavily | searched | completed_fallback | False | True | False | False |",
        "| 2 | composio | planned | completed_fallback | False | True | False | False |",
        "| 3 | openclaw | traced | completed_fallback | False | True | False | False |",
        "| 4 | nebius | narrated | completed_fallback | False | True | False | False |",
        "Portkey API call made: False",
        "Portkey guardrail verdict: False",
        "requires human review: True",
    ]:
        assert expected in markdown

    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden not in markdown


def test_write_collector_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        written = write_sponsor_proof_collector_artifacts(DEFAULT_TRIAL_REQUEST, Path(temp_dir))

        assert {path.name for path in written} == {
            "support_triage_trial.sponsor_proof_collector.md",
            "support_triage_trial.sponsor_proof_collector.json",
        }
        payload = json.loads(
            (Path(temp_dir) / "support_triage_trial.sponsor_proof_collector.json").read_text(
                encoding="utf-8"
            )
        )
        assert payload["schema_version"] == SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION
        assert payload["invariants"]["decision_lock_unchanged"] is True


def test_collector_cli_outputs_markdown_and_json() -> None:
    markdown_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.sponsor_proof_collector",
            "examples/requests/support_triage_trial.yml",
            "--no-write",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert markdown_proc.returncode == 0, markdown_proc.stderr
    assert "# Sponsor Proof Collector Run" in markdown_proc.stdout

    json_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.sponsor_proof_collector",
            "examples/requests/support_triage_trial.yml",
            "--no-write",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert json_proc.returncode == 0, json_proc.stderr
    payload = json.loads(json_proc.stdout)
    assert payload["schema_version"] == SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION
    assert payload["downstream_previews"]["portkey_model_spend_gate"]["api_call_made"] is False


def test_collector_api_creates_and_returns_local_read_only_runs() -> None:
    created = create_sponsor_proof_run(SponsorProofRunRequest())

    assert created["ok"] is True
    assert created["read_only"] is True
    assert created["run"]["schema_version"] == SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION
    assert created["run"]["safety_boundary"]["live_calls_made"] is False
    assert created["run"]["downstream_previews"]["portkey_model_spend_gate"]["api_call_made"] is False
    assert created["ledger_record"]["run_id"] == created["run"]["run_id"]
    assert created["ledger_record"]["packet_reference"] == created["run"]["packet_reference"]
    assert created["ledger_record"]["safety_lock"]["read_only"] is True
    assert created["ledger_record"]["safety_lock"]["decision_lock_unchanged"] is True

    _sponsor_proof_runs.clear()
    fetched = get_sponsor_proof_run(created["run"]["run_id"])
    assert fetched["ok"] is True
    assert fetched["read_only"] is True
    assert fetched["run"] == created["run"]
    assert fetched["ledger_record"]["run_id"] == created["run"]["run_id"]

    ledger = sponsor_proof_run_ledger()
    assert ledger["ok"] is True
    assert ledger["read_only"] is True
    assert ledger["ledger"]["read_only"] is True
    assert ledger["ledger"]["record_count"] >= 1
    assert any(item["run_id"] == created["run"]["run_id"] for item in ledger["ledger"]["runs"])
    assert ledger["ledger"]["safety_summary"]["no_live_calls"] is True
    assert ledger["ledger"]["safety_summary"]["no_external_writes"] is True
    assert str(SPONSOR_PROOF_RUN_LEDGER_DIR).endswith("state/sponsor_proof_runs")

    post_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/sponsor-proof-runs")
    get_route = next(
        route for route in app.routes if getattr(route, "path", "") == "/api/sponsor-proof-runs/{run_id}"
    )
    ledger_route = next(
        route for route in app.routes if getattr(route, "path", "") == "/api/sponsor-proof-run-ledger"
    )
    assert post_route.methods == {"POST"}
    assert get_route.methods == {"GET"}
    assert ledger_route.methods == {"GET"}


def test_collector_api_rejects_paths_outside_public_requests() -> None:
    try:
        create_sponsor_proof_run(
            SponsorProofRunRequest(request_path="README.md")
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "examples/requests" in exc.detail
    else:
        raise AssertionError("expected HTTPException for non-request path")
