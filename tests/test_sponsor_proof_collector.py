"""Sponsor proof collector backend contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from agent.nebius_evidence_synthesis import NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR
from agent.nebius_reviewer_narration import NEBIUS_REQUIRED_SAFETY_ANCHOR
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
    SponsorProofRunRequest,
    _sponsor_proof_runs,
    app,
    create_sponsor_proof_run,
    get_sponsor_proof_run,
    sponsor_proof_run_ledger,
)


ROOT = Path(__file__).resolve().parents[1]


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


class _FakeTavilyClient:
    def search(self, **kwargs):
        return {
            "query": kwargs["query"],
            "results": [
                {
                    "title": "Reviewer evidence source",
                    "url": f"https://example.com/{len(kwargs['query'])}",
                    "content": "Evidence candidate for reviewer inspection.",
                    "score": 0.88,
                }
            ],
        }


def _fake_dual_nebius_client() -> SimpleNamespace:
    narration = (
        "{"
        '"reviewer_summary":"IA does not approve this request. The packet remains blocked for live movement until proof is reviewed.",'
        '"decision_lock_sentence":"Human review is required before any access, spend, or production movement. Decision lock unchanged.",'
        '"next_human_action":"Route the packet to the named owners with proof debt attached.",'
        f'"safety_anchor":"{NEBIUS_REQUIRED_SAFETY_ANCHOR}"'
        "}"
    )
    synthesis = (
        "{"
        '"reviewer_summary":"IA collected Tavily source candidates for reviewer inspection while the packet decision remains locked.",'
        '"cited_source_ids":["tavily:1"],'
        '"source_findings":[{"source_id":"tavily:1","finding":"The source is relevant context for the named reviewer.","limitation":"Human review is required before this can affect proof debt."}],'
        '"remaining_proof_gaps":"Owner approval, audit logs, and scoped validation evidence remain missing.",'
        '"next_human_action":"Route the source candidate to the named owners with proof debt attached.",'
        f'"safety_anchor":"{NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR}"'
        "}"
    )

    def create(**kwargs):
        prompt = kwargs["messages"][-1]["content"]
        content = synthesis if "source_index" in prompt else narration
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


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


def test_collector_live_tavily_without_key_keeps_deterministic_fallback() -> None:
    with patch("agent.tavily_live_evidence.TAVILY_API_KEY", ""):
        run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST, live_tavily=True)

    assert run["mode"] == "offline_dry_run"
    assert run["safety_boundary"]["read_only"] is True
    assert run["safety_boundary"]["live_calls_made"] is False
    assert run["safety_boundary"]["approves_access"] is False
    assert run["safety_boundary"]["grants_permissions"] is False
    assert run["safety_boundary"]["executes_external_writes"] is False
    assert run["safety_boundary"]["mutates_production"] is False
    assert run["safety_boundary"]["approves_spend"] is False
    assert run["safety_boundary"]["selects_provider"] is False
    assert run["safety_boundary"]["guarantees_savings"] is False

    tavily_step = next(step for step in run["collector_steps"] if step["sponsor"] == "tavily")
    assert tavily_step["status"] == "completed_fallback"
    assert tavily_step["used_live_key"] is False
    assert tavily_step["fallback_used"] is True
    assert tavily_step["would_execute"] is False
    assert tavily_step["can_approve_access"] is False

    tavily_proof = run["live_sponsor_proof"]["tavily"]
    assert tavily_proof["live_requested"] is True
    assert tavily_proof["live_call_attempted"] is False
    assert tavily_proof["fallback_used"] is True
    assert tavily_proof["fallback_reason"] == "tavily_api_key_missing"
    assert all(candidate["source_urls"] == [] for candidate in tavily_proof["evidence_candidates"])


def test_collector_composio_dry_run_builds_permission_diff_without_live_calls() -> None:
    run = build_sponsor_proof_collector_run(DEFAULT_TRIAL_REQUEST, composio_dry_run=True)

    assert run["mode"] == "offline_dry_run"
    assert run["safety_boundary"]["read_only"] is True
    assert run["safety_boundary"]["live_calls_made"] is False
    assert run["safety_boundary"]["approves_access"] is False
    assert run["safety_boundary"]["grants_permissions"] is False
    assert run["safety_boundary"]["executes_external_writes"] is False
    assert run["safety_boundary"]["mutates_production"] is False
    assert run["safety_boundary"]["approves_spend"] is False
    assert run["safety_boundary"]["selects_provider"] is False
    assert run["safety_boundary"]["guarantees_savings"] is False

    composio_step = next(step for step in run["collector_steps"] if step["sponsor"] == "composio")
    assert composio_step["used_live_key"] is False
    assert composio_step["fallback_used"] is True
    assert composio_step["would_execute"] is False
    assert composio_step["can_approve_access"] is False
    assert composio_step["can_grant_permissions"] is False
    assert composio_step["can_mutate_external_state"] is False

    composio_proof = run["dry_run_sponsor_proof"]["composio"]
    assert composio_proof["status"] == "dry_run_permission_diff_built"
    assert composio_proof["api_call_made"] is False
    assert composio_proof["composio_execute_allowed"] is False
    assert composio_proof["permission_diff_summary"]["tool_count"] == 3
    assert composio_proof["permission_diff_summary"]["blocked_write_count"] == 9
    assert all(diff["execute_action_preview"]["would_call_composio"] is False for diff in composio_proof["permission_diffs"])

    markdown = render_sponsor_proof_collector_markdown(run)
    assert "## Dry-Run Proof Collection" in markdown
    assert "composio status: `dry_run_permission_diff_built`" in markdown
    assert "api call made: False" in markdown


def test_collector_live_nebius_builds_structured_narration_without_deciding() -> None:
    with patch("agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_reviewer_narration.config.LLM_API_KEY", "test-key"
    ):
        run = build_sponsor_proof_collector_run(
            DEFAULT_TRIAL_REQUEST,
            live_nebius=True,
            nebius_client_factory=_fake_nebius_client,
        )

    nebius_step = next(step for step in run["collector_steps"] if step["sponsor"] == "nebius")
    assert nebius_step["status"] == "completed_live"
    assert nebius_step["used_live_key"] is True
    assert nebius_step["fallback_used"] is False
    assert nebius_step["would_execute"] is False
    assert nebius_step["can_approve_access"] is False
    assert nebius_step["can_grant_permissions"] is False
    assert nebius_step["can_mutate_external_state"] is False
    assert run["safety_boundary"]["read_only"] is True
    assert run["safety_boundary"]["live_calls_made"] is True
    assert run["safety_boundary"]["executes_external_writes"] is False
    assert run["invariants"]["decision_lock_unchanged"] is True

    nebius_proof = run["live_sponsor_proof"]["nebius"]
    assert nebius_proof["status"] == "live_reviewer_narration_built"
    assert nebius_proof["live_call_attempted"] is True
    assert nebius_proof["live_call_count"] == 1
    assert nebius_proof["used_live_key"] is True
    assert nebius_proof["fallback_used"] is False
    assert nebius_proof["required_anchors_present"] is True
    assert nebius_proof["forbidden_phrases_present"] == []
    assert NEBIUS_REQUIRED_SAFETY_ANCHOR in nebius_proof["structured_narration"]["safety_anchor"]

    markdown = render_sponsor_proof_collector_markdown(run)
    assert "nebius status: `live_reviewer_narration_built`" in markdown
    assert "required anchors present: True" in markdown
    assert "forbidden phrases present: 0" in markdown


def test_collector_builds_nebius_evidence_synthesis_from_tavily_sources() -> None:
    with patch("agent.tavily_live_evidence.TAVILY_API_KEY", "unit-test-key"), patch(
        "agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"
    ), patch("agent.nebius_reviewer_narration.config.LLM_API_KEY", "test-key"), patch(
        "agent.nebius_evidence_synthesis.config.LLM_PROVIDER", "nebius"
    ), patch(
        "agent.nebius_evidence_synthesis.config.LLM_API_KEY", "test-key"
    ):
        run = build_sponsor_proof_collector_run(
            DEFAULT_TRIAL_REQUEST,
            live_tavily=True,
            live_nebius=True,
            composio_dry_run=True,
            tavily_client_factory=lambda _key: _FakeTavilyClient(),
            nebius_client_factory=_fake_dual_nebius_client,
        )

    synthesis = run["nebius_evidence_synthesis"]
    assert synthesis["status"] == "live_evidence_synthesis_built"
    assert synthesis["live_call_attempted"] is True
    assert synthesis["live_call_count"] == 1
    assert synthesis["fallback_used"] is False
    assert synthesis["source_index_count"] > 0
    assert synthesis["synthesis"]["cited_source_ids"] == ["tavily:1"]
    assert synthesis["synthesis"]["source_findings"][0]["source_id"] == "tavily:1"
    assert synthesis["synthesis"]["safety_anchor"] == NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR
    assert synthesis["invariants"]["source_ids_from_tavily_only"] is True
    assert synthesis["invariants"]["no_new_urls"] is True
    assert synthesis["invariants"]["can_reduce_proof_debt"] is False
    assert synthesis["invariants"]["can_approve_access"] is False
    assert synthesis["invariants"]["can_mutate_packet"] is False
    assert run["invariants"]["decision_lock_unchanged"] is True
    assert run["safety_boundary"]["executes_external_writes"] is False
    assert run["downstream_previews"]["portkey_model_spend_gate"]["api_call_made"] is False

    markdown = render_sponsor_proof_collector_markdown(run)
    assert "## Nebius Evidence Synthesis" in markdown
    assert "status: `live_evidence_synthesis_built`" in markdown
    assert "source ids from Tavily only: True" in markdown
    assert "can reduce proof debt: False" in markdown


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


def test_collector_cli_blocks_composio_dry_run_checked_artifact_writes() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.sponsor_proof_collector",
            "examples/requests/support_triage_trial.yml",
            "--composio-dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 2
    assert "--composio-dry-run require --no-write or a custom --output-dir" in proc.stderr


def test_collector_api_creates_and_returns_local_read_only_runs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = Path(tmpdir) / "state" / "sponsor_proof_runs"
        with patch("web.app.SPONSOR_PROOF_RUN_LEDGER_DIR", ledger_dir):
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
            assert str(ledger_dir).endswith("state/sponsor_proof_runs")

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


def test_collector_api_accepts_live_tavily_opt_in_without_key() -> None:
    with patch("agent.tavily_live_evidence.TAVILY_API_KEY", ""):
        created = create_sponsor_proof_run(SponsorProofRunRequest(live_tavily=True))

    run = created["run"]
    assert created["ok"] is True
    assert created["read_only"] is True
    assert run["mode"] == "offline_dry_run"
    assert run["safety_boundary"]["live_calls_made"] is False
    assert run["safety_boundary"]["executes_external_writes"] is False
    assert run["live_sponsor_proof"]["tavily"]["fallback_reason"] == "tavily_api_key_missing"
    assert created["ledger_record"]["safety_lock"]["live_calls_made"] is False
    assert created["ledger_record"]["safety_lock"]["decision_lock_unchanged"] is True


def test_collector_api_accepts_composio_dry_run_opt_in_without_writes() -> None:
    created = create_sponsor_proof_run(SponsorProofRunRequest(composio_dry_run=True))

    run = created["run"]
    assert created["ok"] is True
    assert created["read_only"] is True
    assert run["mode"] == "offline_dry_run"
    assert run["safety_boundary"]["live_calls_made"] is False
    assert run["safety_boundary"]["executes_external_writes"] is False
    assert run["dry_run_sponsor_proof"]["composio"]["api_call_made"] is False
    assert run["dry_run_sponsor_proof"]["composio"]["composio_execute_allowed"] is False
    assert created["ledger_record"]["safety_lock"]["live_calls_made"] is False
    assert created["ledger_record"]["safety_lock"]["executes_external_writes"] is False
    assert created["ledger_record"]["safety_lock"]["decision_lock_unchanged"] is True


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
