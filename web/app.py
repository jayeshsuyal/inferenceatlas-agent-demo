"""FastAPI server for the InferenceAtlas Intelligence Agent."""

import copy
import html
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.config import (
    COMPOSIO_API_KEY,
    COMPOSIO_DRY_RUN,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    TAVILY_API_KEY,
)
from agent.coach_suggestions import build_packet_idle_suggestions, suggestions_for_review_run
from agent.decision_brief import build_agent_access_decision_brief
from agent.downstream_gate import build_downstream_gate_decision
from agent.mind import init_mind, load_mind, save_mind, step
from agent.mind.project import MIND_RUNTIME_DIR, project_mind
from agent.mind.store import load_all_minds
from agent.packet import build_support_triage_decision_packet
from agent.packet_detail import (
    build_ia_packet_detail,
    ia_packet_detail_to_pretty_json,
    render_ia_packet_detail_markdown,
    resolve_ia_packet_verification,
)
from agent.pilot_memo import PILOT_MEMO_SAFETY_ANCHOR, build_pilot_memo, render_copy_review_brief
from agent.portkey_adapter import build_portkey_adapter_payload
from agent.portkey_guardrail import (
    PORTKEY_GUARDRAIL_AUTH_ENV,
    PORTKEY_GUARDRAIL_DELIVERY_MODE,
    PORTKEY_GUARDRAIL_DOC_URL,
    PORTKEY_GUARDRAIL_SCHEMA_VERSION,
    PORTKEY_GUARDRAIL_TOKEN_HEADER,
    PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
    PORTKEY_LOCAL_TEST_EVENT_KIND,
    PORTKEY_REHEARSAL_AUTH_ENV,
    PORTKEY_REHEARSAL_MODE_HEADER,
    SAFE_PORTKEY_REQUEST_MODES,
    PortkeyGuardrailAuthError,
    build_portkey_guardrail_event,
    build_portkey_guardrail_response,
    extract_portkey_metadata,
    extract_portkey_requested_mode,
    list_portkey_guardrail_events,
    relative_event_path,
    resolve_portkey_guardrail_event_kind,
    validate_portkey_guardrail_token,
    write_portkey_guardrail_event,
)
from agent.portkey_guardrail_proof_loop import build_portkey_guardrail_proof_loop
from agent.proof_graph import DEFAULT_SCENARIO as DEFAULT_PROOF_GRAPH_SCENARIO
from agent.proof_graph_visual import build_proof_graph_visual, render_review_run_proof_graph_html
from agent.renderers import render_decision_brief_markdown, render_packet_markdown
from agent.review_run import (
    DEFAULT_REVIEW_RUN_STORE_DIR,
    DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
    ReviewRun,
    attach_review_run_proof,
    build_review_run_approval_receipt,
    build_review_run_coach_answer,
    build_review_run_portkey_guardrail_test,
    build_review_run_proofgraph,
    create_review_run,
    generate_proof_resolved_review_run_packet,
    generate_initial_review_run_packet,
    load_review_run_record,
    review_run_record_summary,
    review_run_packet_projection,
    write_review_run_record,
)
from agent.scenarios import ROOT_DIR, SCENARIOS, build_scenario_packet
from agent.subscribers import (
    PACKET_AUTHORITY_SHORT_SENTENCE,
    build_subscriber_examples,
)
from agent.sponsor_proof_trace import build_sponsor_proof_trace
from agent.sponsor_proof_collector import (
    DEFAULT_QUESTION as DEFAULT_SPONSOR_PROOF_COLLECTOR_QUESTION,
    build_sponsor_proof_collector_run,
)
from agent.sponsor_run_ledger import (
    DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR,
    build_sponsor_proof_run_record,
    build_sponsor_proof_run_ledger,
    list_sponsor_proof_run_records,
    load_sponsor_proof_run_record,
    sponsor_proof_run_record_summary,
    write_sponsor_proof_run_record,
)
from agent.sponsor_readiness import build_sponsor_live_readiness
from agent.verification import build_verification_artifact_for_scenario
from agent.workbench import (
    build_workbench_registry,
    build_workbench_result,
    render_workbench_markdown,
    workbench_result_to_pretty_json,
)
from agent.tools import compare_providers, get_catalog_summary, tavily_search
from agent.chat_orchestrator import format_reply_with_manifest, orchestrate_chat
from agent.coach_enrichment import enrich_review_run_coach_answer
from agent.coach_session import DEFAULT_COACH_SESSION_DIR
from agent.repo_index_job import (
    bind_index_job_to_context,
    get_index_job,
    get_session_review_context,
    start_background_full_index,
)
from agent.review_context import (
    get_review_context_bundle,
    list_review_runs_for_session,
    record_flow_event,
)
from agent.session_metrics import (
    clear_metrics_session,
    get_session_metrics,
    record_copilot_direct,
    set_metrics_session,
)
from agent.cost_plan import v1_status_summary
from agent.github_repo import attach_repository, get_repo_index_status, list_repositories
from agent.google_drive_files import (
    attach_drive_file,
    get_drive_index_status,
    list_drive_files,
)
from agent.connector_oauth import (
    demo_sign_in,
    disconnect,
    finish_github_callback,
    finish_google_callback,
    google_access_denied_html,
    oauth_close_html,
    render_popup_html,
    save_user_api_key,
)
from agent.connector_runtime import (
    export_to_connector,
    import_connector_content,
    session_statuses,
    start_connect,
)
from agent.ui_connectors import build_connectors_payload
from agent.trial import DEFAULT_TRIAL_REQUEST, build_trial_report
from agent.trial_evidence_replay import (
    ADAPTER_PROVIDERS,
    DEFAULT_REHEARSAL_EVIDENCE_DIR,
    build_trial_evidence_replay,
    render_trial_evidence_replay_markdown,
)
from agent.trial_outcome_memo import build_trial_outcome_memo
from agent.ui_skills import (
    build_ui_skills_payload,
    find_ui_skill,
    run_ui_skill,
    skill_suggested_questions,
)

from web.files_io import (
    format_attachment_block,
    load_upload,
    register_download,
    resolve_download,
    save_output,
    save_output_registered,
    save_upload,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

SCENARIO_LABELS = {
    "support_triage_agent": {
        "title": "Support triage bot",
        "blurb": "Should a support agent get GitHub, Slack, and Jira access?",
    },
    "read_only_analytics_agent": {
        "title": "Read-only analytics",
        "blurb": "Lower-risk read access to analytics tools.",
    },
    "admin_code_fix_bot": {
        "title": "Admin code-fix bot",
        "blurb": "High-risk production write scope — should stay blocked.",
    },
}

TENSION_LABELS = {
    "proof_debt": "Missing proof for safe access",
    "prediction_error": "Review packet may be going stale",
    "observation_pending": "Your note is queued for next cycle",
}

SUBSCRIBER_CATEGORY_ORDER = ("gateway", "ci", "spend", "review", "observability")

app = FastAPI(title="InferenceAtlas Agent", version="1.0.0")

_sessions: Dict[str, object] = {}
_lock = threading.Lock()
_review_runs: Dict[str, dict] = {}
_review_runs_lock = threading.Lock()
_sponsor_proof_runs: Dict[str, dict] = {}
_sponsor_proof_runs_lock = threading.Lock()
REVIEW_RUN_STORE_DIR = Path(os.environ.get("IA_REVIEW_RUN_STORE_DIR", DEFAULT_REVIEW_RUN_STORE_DIR)).expanduser()
COACH_SESSION_DIR = Path(os.environ.get("IA_COACH_SESSION_DIR", DEFAULT_COACH_SESSION_DIR)).expanduser()
SPONSOR_PROOF_RUN_LEDGER_DIR = Path(
    os.environ.get("IA_SPONSOR_PROOF_RUN_LEDGER_DIR", DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR)
).expanduser()


def _live_deps_available() -> bool:
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


def _get_inference_agent():
    from agent import InferenceAtlasAgent

    return InferenceAtlasAgent()


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=8000)
    session_id: Optional[str] = None
    attachment_ids: List[str] = Field(default_factory=list)
    skill_ids: List[str] = Field(default_factory=list)
    skill_context_position: str = Field(default="prepend")
    github_repos: List[str] = Field(default_factory=list)
    drive_file_ids: List[str] = Field(default_factory=list)
    current_fixture: str = Field(default="", max_length=120)
    chip_entities: Optional[dict[str, Any]] = None


class GithubAttachRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    full_name: str = Field(..., min_length=3, max_length=200)


class DriveAttachRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    file_id: str = Field(..., min_length=2, max_length=120)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    answer: Dict[str, Any] = Field(default_factory=dict)
    output_files: List[dict] = Field(default_factory=list)
    skills_used: List[dict] = Field(default_factory=list)
    github_repos_used: List[str] = Field(default_factory=list)
    drive_files_used: List[str] = Field(default_factory=list)
    thinking_logs: List[str] = Field(default_factory=list)
    context_manifest: List[str] = Field(default_factory=list)
    github_index: List[dict] = Field(default_factory=list)
    use_tools: bool = False
    engine_source: str = ""
    cost_plan_ok: bool = False


def _file_ref(file_id: str, label: str) -> dict:
    return {"file_id": file_id, "label": label, "url": f"/api/files/{file_id}"}


def _generated_file_ref(relative_path: str, label: str, *, mime: str = "text/plain; charset=utf-8") -> dict:
    path = Path(relative_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    file_id = register_download(path, label=label, mime=mime)
    return _file_ref(file_id, label)


def _walkthrough_subscriber_rows(packet_id: str) -> list[dict]:
    examples = build_subscriber_examples(packet_id)
    rows: list[dict] = []
    for category in SUBSCRIBER_CATEGORY_ORDER:
        for payload in examples.get(category, {}).values():
            effect = payload["subscriber_effect"]
            rows.append(
                {
                    "category": category,
                    "subscriber": payload["subscriber"],
                    "consumer_question": payload["consumer_question"],
                    "subscriber_action": effect["subscriber_action"],
                    "owner": effect["owner"],
                    "endpoint": payload["read_only_contract"]["endpoint"],
                    "can_approve_access": effect["can_approve_access"],
                    "can_grant_permissions": effect["can_grant_permissions"],
                    "can_mutate_packet": effect["can_mutate_packet"],
                    "can_override_verdict": effect["can_override_verdict"],
                    "executes_external_writes": effect["executes_external_writes"],
                    "requires_human_review": effect["requires_human_review"],
                }
            )
    return rows


class ResetRequest(BaseModel):
    session_id: str


class MindObserveRequest(BaseModel):
    scenario: str = Field(default="support_triage_agent")
    text: str = Field(..., min_length=1, max_length=8000)


class MindStepRequest(BaseModel):
    scenario: Optional[str] = None
    no_cortex: bool = False


class SkillRunRequest(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=80)


class ConnectorConnectRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    connector_id: str = Field(..., min_length=1, max_length=40)


class ConnectorImportRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    connector_id: str = Field(..., min_length=1, max_length=40)
    action: str = Field(default="files", max_length=40)
    query: str = Field(default="", max_length=500)


class ConnectorExportRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    connector_id: str = Field(..., min_length=1, max_length=40)
    content: str = Field(..., min_length=1, max_length=50000)
    destination: str = Field(default="file", max_length=40)


class CustomEvidenceRehearsalRequest(BaseModel):
    attachment_ids: List[str] = Field(default_factory=list, max_length=8)
    storage_scope: str = Field(default="review_anonymous", max_length=160)


class WorkbenchGenerateRequest(BaseModel):
    fixture_id: str = Field(..., min_length=1, max_length=120)


class SponsorProofRunRequest(BaseModel):
    request_path: str = Field(default="examples/requests/support_triage_trial.yml", max_length=240)
    scenario_name: str = Field(default="support_triage_agent", min_length=1, max_length=120)
    lane: str = Field(default="both", max_length=40)
    downstream_fixture: str = Field(default="ai_spend_budget_overrun", max_length=120)
    subscriber: str = Field(default="portkey_model_spend_gate", max_length=120)
    question: str = Field(default=DEFAULT_SPONSOR_PROOF_COLLECTOR_QUESTION, max_length=800)
    live_tavily: bool = False
    live_nebius: bool = False
    composio_dry_run: bool = False


class ReviewRunCreateRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=160)
    selected_repo: Optional[Dict[str, Any]] = None
    repo_index_summary: Dict[str, Any] = Field(default_factory=dict)
    access_request: str = Field(default="", max_length=10000)


class ReviewRunPacketRequest(BaseModel):
    access_request: str = Field(
        default=DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
        min_length=1,
        max_length=10000,
    )
    sponsor_proof_trace: Optional[Dict[str, Any]] = None


class ReviewRunProofAttachRequest(BaseModel):
    proof_items: List[Dict[str, Any]] = Field(default_factory=list, max_length=8)


class ReviewRunRerunRequest(BaseModel):
    access_request: Optional[str] = Field(default=None, max_length=10000)


class ReviewRunCoachRequest(BaseModel):
    prompt: str = Field(default="", max_length=1200)
    message: Optional[str] = Field(default=None, max_length=1200)
    entities: Optional[dict[str, Any]] = None
    chip_entities: Optional[dict[str, Any]] = None
    reassess_trigger: Optional[str] = Field(default=None, max_length=80)
    session_id: Optional[str] = Field(default=None, max_length=160)
    previous_stage: Optional[str] = Field(default=None, max_length=80)


class ReviewRunIndexStartRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=160)
    full_name: str = Field(..., min_length=3, max_length=200)


class ReviewRunIndexFetchRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=160)
    patterns: List[str] = Field(default_factory=list, max_length=12)


def _rehearsal_provider_rows(replay: dict[str, Any]) -> List[dict]:
    rows: List[dict] = []
    for provider, item in replay["sponsor_replay"].items():
        evidence_summary = item.get("rehearsal_evidence_summary") or {}
        rows.append(
            {
                "provider": provider,
                "proof_pack_type": item["proof_pack_type"],
                "value_added": item["value_added"],
                "attachment_count": len(item.get("attachments", [])),
                "evidence_attached": bool(item.get("rehearsal_evidence_attached")),
                "rehearsal_item_count": evidence_summary.get("item_count", 0),
                "would_execute": bool(item["would_execute"]),
                "can_approve_access": bool(item["can_approve_access"]),
                "can_grant_permissions": bool(item["can_grant_permissions"]),
                "human_review_required": bool(item["human_review_required"]),
            }
        )
    return rows


def _payload_provider(payload: dict[str, Any], filename: str) -> str:
    explicit = str(payload.get("provider", "")).strip().lower()
    if explicit in ADAPTER_PROVIDERS:
        return explicit
    inferred = Path(filename).stem.lower()
    if inferred in ADAPTER_PROVIDERS:
        payload["provider"] = inferred
        return inferred
    raise ValueError(
        f"{filename} must include provider={', '.join(ADAPTER_PROVIDERS)} "
        "or use a provider filename like tavily.json"
    )


def _extract_provider_payloads(filename: str, text: str) -> list[tuple[str, dict[str, Any]]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{filename} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{filename} must contain a JSON object")

    bundled: list[tuple[str, dict[str, Any]]] = []
    for provider in ADAPTER_PROVIDERS:
        nested = payload.get(provider)
        if nested is None:
            continue
        if not isinstance(nested, dict):
            raise ValueError(f"{filename}.{provider} must be a JSON object")
        nested = dict(nested)
        nested.setdefault("provider", provider)
        bundled.append((provider, nested))
    if bundled:
        return bundled

    return [(_payload_provider(payload, filename), payload)]


def _uploaded_evidence_dir(storage_scope: str, attachment_ids: list[str]) -> tuple[Path, list[dict]]:
    if not attachment_ids:
        raise ValueError("Upload at least one sanitized provider JSON file.")

    run_id = str(uuid.uuid4())
    subfolder = f"custom_evidence_rehearsal/{run_id}"
    providers_seen: set[str] = set()
    accepted_files: list[dict] = []
    output_dir: Path | None = None
    for file_id in attachment_ids:
        loaded = load_upload(storage_scope, file_id)
        if not loaded:
            raise ValueError(f"Uploaded evidence file {file_id[:8]} was not found.")
        filename, text = loaded
        for provider, payload in _extract_provider_payloads(filename, text):
            if provider in providers_seen:
                raise ValueError(f"Duplicate uploaded evidence for provider {provider}.")
            providers_seen.add(provider)
            path = save_output(
                scope="review",
                subfolder=subfolder,
                filename=f"{provider}.json",
                content=json.dumps(payload, indent=2, sort_keys=True) + "\n",
                use_timestamp=False,
            )
            output_dir = path.parent
            accepted_files.append(
                {
                    "file_id": file_id,
                    "filename": filename,
                    "provider": provider,
                }
            )
    if output_dir is None:
        raise ValueError("Uploaded evidence did not include a known provider payload.")
    return output_dir, accepted_files


def _get_or_create_session(session_id: Optional[str]) -> Tuple[str, object]:
    with _lock:
        if session_id and session_id in _sessions:
            return session_id, _sessions[session_id]
        new_id = session_id or str(uuid.uuid4())
        agent = _get_inference_agent()
        _sessions[new_id] = agent
        return new_id, agent


def _deterministic_example_reply(message: str) -> Optional[str]:
    """Run known example-card tool plans directly for reliable live demos."""
    normalized = " ".join(message.lower().split())
    if "use get_catalog_summary" in normalized:
        return "## Catalog overview\n\n" + get_catalog_summary()

    if "support triage agent" in normalized or "tool access review" in normalized:
        packet = build_support_triage_decision_packet(mode="live_review_room_demo")
        brief = build_agent_access_decision_brief(packet)
        return "\n\n".join(
            [
                "## Tool access review",
                render_decision_brief_markdown(brief),
                "Composio remains dry-run; no external write was executed.",
            ]
        )

    if "use tavily_search" in normalized and "mistral" in normalized:
        search = tavily_search("site:mistral.ai pricing Mistral Large API official", max_results=2)
        comparison = compare_providers("llm", top_n=5)
        return "\n\n".join(
            [
                "## Mistral pricing live check",
                "### Tavily results",
                search,
                "### Catalog comparison",
                comparison,
                "Composio remains dry-run; no external write was executed.",
            ]
        )

    if "500m tokens/month" in normalized and "compare_providers" in normalized:
        comparison = compare_providers("llm", top_n=5)
        return "\n\n".join(
            [
                "## GPT-4o alternative",
                "Catalog comparison for `llm` workloads:",
                comparison,
                "Use this as a procurement shortlist, not a final savings guarantee.",
            ]
        )

    return None


@app.get("/api/health")
def health() -> dict:
    deps_ok = _live_deps_available()
    catalog = ""
    try:
        catalog = get_catalog_summary()
    except Exception:
        catalog = "Catalog unavailable."
    return {
        "ok": bool(LLM_API_KEY) and deps_ok,
        "skills_api": True,
        "connectors_api": True,
        "skills_count": len(build_ui_skills_payload().get("skills", [])),
        "connectors_count": len(build_connectors_payload().get("connectors", [])),
        "deps_ok": deps_ok,
        "deps_hint": (
            None
            if deps_ok
            else "pip install -r agent/requirements.txt  (or: pip install -e \".[live,web]\")"
        ),
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "tavily": bool(TAVILY_API_KEY),
        "composio": bool(COMPOSIO_API_KEY),
        "composio_dry_run": COMPOSIO_DRY_RUN,
        "catalog": catalog,
        "inferenceatlas_v1": v1_status_summary(),
    }


@app.get("/api/skills")
def list_ui_skills() -> dict:
    """InferenceAtlas harness skills for the web UI (+ menu and / slash picker)."""
    return build_ui_skills_payload()


@app.get("/api/connectors")
def list_ui_connectors(session_id: Optional[str] = Query(None)) -> dict:
    """External integrations for the web UI + menu (Drive, GitHub, Nebius, …)."""
    return build_connectors_payload(session_id)


@app.get("/api/session/metrics")
def session_metrics(session_id: str = Query(..., min_length=1)) -> dict:
    """Live per-session counters for billable .env services."""
    return get_session_metrics(session_id)


@app.get("/api/packets/{scenario_or_packet_id}/verification")
def packet_verification(scenario_or_packet_id: str) -> dict:
    """Read-only Packet Authority verification surface for downstream subscribers."""
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        if scenario_or_packet_id in {scenario_name, packet["packet_id"]}:
            artifact = build_verification_artifact_for_scenario(packet, scenario_name)
            return {
                "ok": True,
                "scenario": scenario_name,
                "read_only": True,
                "verification": artifact,
            }
    try:
        fixture_id, artifact = resolve_ia_packet_verification(scenario_or_packet_id)
        return {
            "ok": True,
            "scenario": fixture_id,
            "fixture": fixture_id,
            "read_only": True,
            "verification": artifact,
        }
    except KeyError:
        pass
    raise HTTPException(status_code=404, detail="unknown scenario or packet_id")


@app.get("/api/downstream-gates/{subscriber}/decision")
def downstream_gate_decision(
    subscriber: str,
    scenario_or_packet_id: str = Query("support_triage_agent"),
) -> dict:
    """Read-only answer for downstream systems asking whether an agent action can proceed."""
    try:
        decision = build_downstream_gate_decision(
            subscriber,
            scenario_or_packet_id=scenario_or_packet_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "read_only": True,
        "decision": decision,
    }


@app.get("/api/packets/{fixture}/downstream/portkey")
def portkey_downstream_preview(
    fixture: str,
    mode: str = Query("dry-run", pattern="^(ready|dry-run)$"),
) -> dict:
    """Read-only Portkey guardrail/policy preview generated from one IA Packet."""
    try:
        payload = build_portkey_adapter_payload(fixture=fixture, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown fixture: {fixture}") from exc
    return {
        "ok": True,
        "read_only": True,
        "portkey": payload,
    }


@app.get("/api/packets/{fixture}/downstream/portkey/proof-loop")
def portkey_guardrail_proof_loop(
    fixture: str,
    requested_mode: str = Query("model_request"),
) -> dict:
    """Read-only Portkey proof loop: webhook verdict plus policy preview."""
    try:
        payload = build_portkey_guardrail_proof_loop(
            fixture=fixture,
            requested_mode=requested_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown fixture: {fixture}") from exc
    return {
        "ok": True,
        "read_only": True,
        "portkey_guardrail_proof_loop": payload,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _portkey_webhook_safety_payload() -> dict[str, bool]:
    return {
        "read_only": True,
        "packet_mutation_allowed": False,
        "portkey_policy_mutation_allowed": False,
        "portkey_api_call_made": False,
        "approves_access": False,
        "approves_spend": False,
        "executes_external_writes": False,
        "mutates_production": False,
        "raw_agent_intent_trusted": False,
    }


def _review_run_portkey_failure_response(
    *,
    reason: str,
    metadata: dict[str, Any],
    requested_mode: str,
    packet_reference: Optional[dict[str, Any]] = None,
    verdict_class: Optional[str] = None,
    next_human_action: str = "Use current ReviewRun packet metadata before Portkey allows movement.",
    elapsed_ms: int = 0,
) -> dict:
    data: dict[str, Any] = {
        "schema_version": PORTKEY_GUARDRAIL_SCHEMA_VERSION,
        "delivery_mode": PORTKEY_GUARDRAIL_DELIVERY_MODE,
        "portkey_surface": "BYO Guardrails webhook",
        "docs_reference": {
            "guardrail_webhook": PORTKEY_GUARDRAIL_DOC_URL,
            "guardrails_overview": PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
            "last_verified": "2026-06-11",
        },
        "generated_at": _utc_now(),
        "elapsed_ms": elapsed_ms,
        "metadata_resolved_by": "ia_review_run_id",
        "review_run_id": metadata.get("ia_review_run_id"),
        "requested_mode": requested_mode or None,
        "reason": reason,
        "deny_reasons": [reason],
        "next_human_action": next_human_action,
        "safety": _portkey_webhook_safety_payload(),
    }
    if packet_reference:
        data["ia_packet_reference"] = packet_reference
    if verdict_class:
        data["verdict_class"] = verdict_class
    return {"verdict": False, "data": data}


def _packet_reference_for_run(run: ReviewRun) -> Optional[dict[str, Any]]:
    packet = run.packet or {}
    packet_id = packet.get("packet_id")
    revision_id = packet.get("revision_id")
    if not packet_id or not revision_id:
        return None
    return {
        "packet_id": str(packet_id),
        "revision_id": str(revision_id),
        "revision_number": int(packet.get("revision_number") or 0),
        "content_hash": packet.get("content_hash"),
        "run_id": run.run_id,
        "source_of_truth": "ReviewRun",
    }


def _build_review_run_portkey_guardrail_response(body: Any, *, elapsed_ms: int = 0) -> Optional[dict]:
    if not isinstance(body, dict):
        return None
    metadata = extract_portkey_metadata(body)
    review_run_id = str(metadata.get("ia_review_run_id") or "").strip()
    if not review_run_id:
        return None

    requested_mode = extract_portkey_requested_mode(metadata)
    if requested_mode not in SAFE_PORTKEY_REQUEST_MODES:
        return _review_run_portkey_failure_response(
            reason="requested_mode_not_packet_scoped",
            metadata=metadata,
            requested_mode=requested_mode,
            elapsed_ms=elapsed_ms,
        )

    try:
        record = load_review_run_record(review_run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError:
        return _review_run_portkey_failure_response(
            reason="invalid_review_run_id",
            metadata=metadata,
            requested_mode=requested_mode,
            elapsed_ms=elapsed_ms,
        )
    if record is None:
        return _review_run_portkey_failure_response(
            reason="review_run_not_found",
            metadata=metadata,
            requested_mode=requested_mode,
            elapsed_ms=elapsed_ms,
        )

    run = ReviewRun.from_dict(record["run"])
    packet_reference = _packet_reference_for_run(run)
    if packet_reference is None:
        return _review_run_portkey_failure_response(
            reason="review_run_packet_not_generated",
            metadata=metadata,
            requested_mode=requested_mode,
            elapsed_ms=elapsed_ms,
        )

    supplied_packet_id = str(metadata.get("ia_packet_id") or "").strip()
    supplied_revision_id = str(metadata.get("ia_revision_id") or "").strip()
    if not supplied_packet_id or not supplied_revision_id:
        return _review_run_portkey_failure_response(
            reason="packet_metadata_missing",
            metadata=metadata,
            requested_mode=requested_mode,
            packet_reference=packet_reference,
            verdict_class=run.packet.get("verdict"),
            elapsed_ms=elapsed_ms,
        )
    if supplied_packet_id != packet_reference["packet_id"]:
        return _review_run_portkey_failure_response(
            reason="packet_id_mismatch",
            metadata=metadata,
            requested_mode=requested_mode,
            packet_reference=packet_reference,
            verdict_class=run.packet.get("verdict"),
            elapsed_ms=elapsed_ms,
        )
    if supplied_revision_id != packet_reference["revision_id"]:
        return _review_run_portkey_failure_response(
            reason="stale_packet_revision",
            metadata=metadata,
            requested_mode=requested_mode,
            packet_reference=packet_reference,
            verdict_class=run.packet.get("verdict"),
            next_human_action="Send the current ReviewRun packet revision before Portkey allows movement.",
            elapsed_ms=elapsed_ms,
        )

    try:
        test = build_review_run_portkey_guardrail_test(run, elapsed_ms=elapsed_ms)
    except ValueError:
        return _review_run_portkey_failure_response(
            reason="review_run_packet_not_generated",
            metadata=metadata,
            requested_mode=requested_mode,
            elapsed_ms=elapsed_ms,
        )

    response = copy.deepcopy(test["portkey_guardrail_response"])
    response["data"]["delivery_mode"] = PORTKEY_GUARDRAIL_DELIVERY_MODE
    response["data"]["metadata_resolved_by"] = "ia_review_run_id"
    response["data"]["review_run_id"] = run.run_id
    response["data"]["requested_mode"] = requested_mode
    return response


@app.post("/api/portkey/guardrail")
async def portkey_guardrail_webhook(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_ia_portkey_guardrail_token: Optional[str] = Header(default=None, alias=PORTKEY_GUARDRAIL_TOKEN_HEADER),
    x_ia_rehearsal_mode: Optional[str] = Header(default=None, alias=PORTKEY_REHEARSAL_MODE_HEADER),
) -> dict:
    """Read-only Portkey BYO Guardrails webhook backed by IA Packet truth."""
    provided_token = x_ia_portkey_guardrail_token or authorization
    try:
        validate_portkey_guardrail_token(
            provided_token=provided_token,
            expected_token=os.getenv(PORTKEY_GUARDRAIL_AUTH_ENV),
        )
    except PortkeyGuardrailAuthError as exc:
        reason = str(exc)
        status = 503 if reason == "portkey_guardrail_token_not_configured" else 401
        raise HTTPException(status_code=status, detail=reason) from exc

    try:
        body = await request.json()
    except Exception:
        body = {}

    event_kind = resolve_portkey_guardrail_event_kind(
        rehearsal_token=x_ia_rehearsal_mode,
        expected_rehearsal_token=os.getenv(PORTKEY_REHEARSAL_AUTH_ENV),
    )

    started = time.perf_counter()
    response = _build_review_run_portkey_guardrail_response(body, elapsed_ms=0)
    if response is None:
        response = build_portkey_guardrail_response(body, elapsed_ms=0)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response["data"]["elapsed_ms"] = elapsed_ms

    event = build_portkey_guardrail_event(
        body=body if isinstance(body, dict) else {},
        response=response,
        elapsed_ms=elapsed_ms,
        kind=event_kind,
    )
    record_path = write_portkey_guardrail_event(
        event,
        ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR,
    )
    response["data"]["guardrail_event"] = {
        "event_id": event["event_id"],
        "record_path": relative_event_path(record_path),
    }
    return response


@app.get("/api/portkey/guardrail/events")
def portkey_guardrail_events() -> dict:
    """Return local read-only Portkey BYO Guardrails proof events."""
    return {
        "ok": True,
        "read_only": True,
        "events": list_portkey_guardrail_events(ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR),
    }


@app.get("/api/sponsor-readiness/matrix")
def sponsor_readiness_matrix(
    scenario: str = Query("support_triage_agent"),
    inspect_env: bool = Query(False),
) -> dict:
    """Read-only sponsor fallback/dry-run/live-capability matrix."""
    try:
        report = build_sponsor_live_readiness(scenario, inspect_env=inspect_env)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "read_only": True,
        "scenario": report["scenario"],
        "environment_inspected": report["environment_inspected"],
        "summary": {
            "provider_count": report["summary"]["provider_count"],
            "all_fallback_available": report["summary"]["all_fallback_available"],
            "all_dry_run_available": report["summary"]["all_dry_run_available"],
            "all_live_capable": report["summary"]["all_live_capable"],
            "any_env_ready_for_live": report["summary"]["any_env_ready_for_live"],
            "any_live_enabled": report["summary"]["any_live_enabled"],
            "all_non_executing": report["summary"]["all_non_executing"],
            "all_non_approving": report["summary"]["all_non_approving"],
            "all_non_granting": report["summary"]["all_non_granting"],
            "all_non_mutating": report["summary"]["all_non_mutating"],
        },
        "matrix": report["readiness_matrix"],
        "private_boundary": report["private_boundary"],
    }


@app.post("/api/review-runs")
def create_review_run_api(body: ReviewRunCreateRequest) -> dict:
    """Create one local ReviewRun with non-approving safety defaults."""
    try:
        run = create_review_run(
            session_id=body.session_id,
            selected_repo=body.selected_repo,
            repo_index_summary=body.repo_index_summary,
            access_request=body.access_request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record = write_review_run_record(run, store_dir=REVIEW_RUN_STORE_DIR)
    run_payload = record["run"]

    with _review_runs_lock:
        _review_runs[run.run_id] = run_payload

    if body.session_id and body.selected_repo:
        repo_name = str((body.selected_repo or {}).get("full_name") or "")
        if repo_name:
            record_flow_event(
                body.session_id,
                run.run_id,
                stage=run.stage,
                previous_stage="repo_not_connected",
                trigger="review_run_created",
                summary=f"ReviewRun created for {repo_name}.",
                repo_full_name=repo_name,
            )

    return {
        "ok": True,
        "read_only": True,
        "run": run_payload,
        "record": review_run_record_summary(record),
    }


def _load_review_run_or_404(run_id: str) -> tuple[ReviewRun, Optional[dict]]:
    with _review_runs_lock:
        run_payload = _review_runs.get(run_id)
    try:
        record = load_review_run_record(run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run_payload is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown review run")
        run_payload = record["run"]
    try:
        return ReviewRun.from_dict(run_payload), record
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/review-runs/{run_id}/packet")
def generate_review_run_packet_api(run_id: str, body: ReviewRunPacketRequest) -> dict:
    """Generate one compact IA Packet from the current ReviewRun."""
    with _review_runs_lock:
        run_payload = _review_runs.get(run_id)
    try:
        record = load_review_run_record(run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run_payload is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown review run")
        run_payload = record["run"]
    try:
        run = ReviewRun.from_dict(run_payload)
        generated = generate_initial_review_run_packet(
            run,
            body.access_request,
            sponsor_proof_trace=body.sponsor_proof_trace,
        )
        record = write_review_run_record(generated, store_dir=REVIEW_RUN_STORE_DIR)
        packet = review_run_packet_projection(generated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_payload = record["run"]
    with _review_runs_lock:
        _review_runs[generated.run_id] = run_payload

    return {
        "ok": True,
        "read_only": True,
        "run": run_payload,
        "record": review_run_record_summary(record),
        "packet": packet,
    }


@app.post("/api/review-runs/{run_id}/proof")
def attach_review_run_proof_api(run_id: str, body: ReviewRunProofAttachRequest) -> dict:
    """Attach human proof to a ReviewRun without changing verdict or downstream state."""
    with _review_runs_lock:
        run_payload = _review_runs.get(run_id)
    try:
        record = load_review_run_record(run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run_payload is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown review run")
        run_payload = record["run"]
    try:
        run = ReviewRun.from_dict(run_payload)
        updated = attach_review_run_proof(run, body.proof_items)
        record = write_review_run_record(updated, store_dir=REVIEW_RUN_STORE_DIR)
        packet = review_run_packet_projection(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_payload = record["run"]
    with _review_runs_lock:
        _review_runs[updated.run_id] = run_payload

    return {
        "ok": True,
        "read_only": True,
        "run": run_payload,
        "record": review_run_record_summary(record),
        "packet": packet,
    }


@app.post("/api/review-runs/{run_id}/rerun")
def rerun_review_run_packet_api(run_id: str, body: ReviewRunRerunRequest = ReviewRunRerunRequest()) -> dict:
    """Generate the updated packet after human proof is attached."""
    with _review_runs_lock:
        run_payload = _review_runs.get(run_id)
    try:
        record = load_review_run_record(run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run_payload is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown review run")
        run_payload = record["run"]
    try:
        run = ReviewRun.from_dict(run_payload)
        updated = generate_proof_resolved_review_run_packet(run, body.access_request)
        record = write_review_run_record(updated, store_dir=REVIEW_RUN_STORE_DIR)
        packet = review_run_packet_projection(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_payload = record["run"]
    with _review_runs_lock:
        _review_runs[updated.run_id] = run_payload

    return {
        "ok": True,
        "read_only": True,
        "run": run_payload,
        "record": review_run_record_summary(record),
        "packet": packet,
        "portkey": updated.portkey_preview,
        "review_delta": packet["review_delta"],
    }


def _build_review_run_coach_response(
    run_id: str,
    body: ReviewRunCoachRequest,
) -> tuple[ReviewRun, dict[str, Any], list[dict[str, Any]]]:
    with _review_runs_lock:
        run_payload = _review_runs.get(run_id)
    try:
        record = load_review_run_record(run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run_payload is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown review run")
        run_payload = record["run"]
    try:
        run = ReviewRun.from_dict(run_payload)
        prompt = body.prompt or body.message or ""
        chip_entities = dict(body.entities or {})
        chip_entities.update(dict(body.chip_entities or {}))
        if body.reassess_trigger:
            chip_entities.setdefault("reassess_trigger", body.reassess_trigger)
        if body.previous_stage:
            chip_entities.setdefault("previous_stage", body.previous_stage)
        base_answer = build_review_run_coach_answer(
            run,
            prompt,
            chip_entities=chip_entities or None,
        )
        answer = enrich_review_run_coach_answer(
            run,
            base_answer,
            prompt=prompt,
            chip_entities=chip_entities or None,
            session_id=str(body.session_id or "").strip(),
            store_dir=COACH_SESSION_DIR,
        )
        suggestions = list(answer.get("suggestions") or suggestions_for_review_run(run))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run, answer, suggestions


@app.post("/api/review-runs/{run_id}/coach")
def coach_review_run_api(run_id: str, body: ReviewRunCoachRequest) -> dict:
    """Answer Ask IA from the current ReviewRun without chat/tool side effects."""
    run, answer, suggestions = _build_review_run_coach_response(run_id, body)
    return {
        "ok": True,
        "read_only": True,
        "run_id": run.run_id,
        "stage": run.stage,
        "reply": answer["reply"],
        "answer": answer,
        "suggestions": suggestions,
    }


@app.post("/api/review-runs/{run_id}/coach/stream")
def coach_review_run_stream_api(run_id: str, body: ReviewRunCoachRequest) -> StreamingResponse:
    """Stream Ask IA thinking and section cards while keeping ReviewRun facts locked."""

    def event_stream():
        from agent.coach_stream import COACH_SECTION_ORDER, build_coach_thinking_steps, pick_coach_display_narration

        try:
            run, answer, suggestions = _build_review_run_coach_response(run_id, body)
            for step in build_coach_thinking_steps(run, answer):
                yield _sse({"type": "thinking", "line": step})

            sections = answer.get("sections") or {}
            current_read = str(sections.get("current_read") or "").strip()
            if current_read:
                yield _sse({"type": "pinned", "current_read": current_read})

            for key, label in COACH_SECTION_ORDER:
                value = sections.get(key)
                if value:
                    yield _sse({"type": "section", "key": key, "label": label, "value": str(value)})

            narration = pick_coach_display_narration(answer)
            if narration:
                for token in narration.split():
                    yield _sse({"type": "narration_chunk", "text": f"{token} "})

            yield _sse(
                {
                    "type": "done",
                    "read_only": True,
                    "run_id": run.run_id,
                    "stage": run.stage,
                    "reply": answer.get("reply", ""),
                    "answer": answer,
                    "suggestions": suggestions,
                }
            )
        except HTTPException as exc:
            yield _sse({"type": "error", "detail": exc.detail})
        except Exception as exc:
            yield _sse({"type": "error", "detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/review-runs/{run_id}/proofgraph")
def get_review_run_proofgraph_api(run_id: str) -> dict:
    """Return the dynamic, read-only ProofGraph projection for one ReviewRun."""
    run, _record = _load_review_run_or_404(run_id)
    graph = build_review_run_proofgraph(run)
    return {
        "ok": True,
        "read_only": True,
        "run_id": run.run_id,
        "stage": run.stage,
        "proofgraph": graph,
    }


@app.get("/api/review-runs/{run_id}/approval-receipt")
def get_review_run_approval_receipt_api(run_id: str) -> dict:
    """Return the portable approval receipt for the current ReviewRun packet."""
    run, _record = _load_review_run_or_404(run_id)
    try:
        receipt = build_review_run_approval_receipt(run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "read_only": True,
        "run_id": run.run_id,
        "stage": run.stage,
        "approval_receipt": receipt,
    }


@app.post("/api/review-runs/{run_id}/portkey/guardrail-test")
def review_run_portkey_guardrail_test_api(run_id: str) -> dict:
    """Run a read-only Portkey guardrail test against the current ReviewRun packet."""
    run, _record = _load_review_run_or_404(run_id)
    start = time.perf_counter()
    try:
        test = build_review_run_portkey_guardrail_test(run, elapsed_ms=0)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    test["elapsed_ms"] = elapsed_ms
    test["portkey_guardrail_response"]["data"]["elapsed_ms"] = elapsed_ms
    event = build_portkey_guardrail_event(
        body=test["portkey_request"],
        response=test["portkey_guardrail_response"],
        elapsed_ms=elapsed_ms,
        kind=PORTKEY_LOCAL_TEST_EVENT_KIND,
    )
    event_path = write_portkey_guardrail_event(
        event,
        ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR,
    )
    event_summary = {
        "event_id": event["event_id"],
        "kind": event["kind"],
        "delivery_mode": event["delivery_mode"],
        "record_path": relative_event_path(event_path),
        "read_only": True,
        "api_call_made": False,
        "policy_mutation_allowed": False,
    }
    test["event_id"] = event["event_id"]
    test["guardrail_event"] = event_summary
    test["portkey_guardrail_response"]["data"]["guardrail_event"] = event_summary
    return {
        "ok": True,
        "read_only": True,
        "run_id": run.run_id,
        "stage": run.stage,
        "portkey_guardrail_test": test,
    }


@app.get("/api/review-runs/{run_id}")
def get_review_run(run_id: str) -> dict:
    """Return a previously created local ReviewRun."""
    with _review_runs_lock:
        run = _review_runs.get(run_id)
    try:
        record = load_review_run_record(run_id, store_dir=REVIEW_RUN_STORE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown review run")
        run = record["run"]
    if record is None:
        record = {
            "schema_version": "review_run_record.v0",
            "run_id": run_id,
            "record_path": "",
            "generated_at": run["updated_at"],
            "mode": "local_durable_read_model",
            "read_only": True,
            "run": run,
            "safety_invariants": run["safety_invariants"],
            "private_boundary": {
                "private_source_exposed": False,
                "principle": "Private engine, public proof.",
            },
        }
    try:
        run_obj = ReviewRun.from_dict(run)
        suggestions = suggestions_for_review_run(run_obj)
    except ValueError:
        suggestions = []
    return {
        "ok": True,
        "read_only": True,
        "run": run,
        "record": review_run_record_summary(record),
        "suggestions": suggestions,
    }


@app.get("/api/sessions/{session_id}/review-runs")
def list_session_review_runs(session_id: str) -> dict:
    """List ReviewRuns linked to this browser session (durable queue for the run rail)."""
    if len(session_id.strip()) < 8:
        raise HTTPException(status_code=400, detail="session_id too short")
    try:
        runs = list_review_runs_for_session(session_id, review_run_store_dir=REVIEW_RUN_STORE_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "read_only": True, "session_id": session_id, "runs": runs}


@app.get("/api/review-runs/{run_id}/context")
def get_review_run_context_api(
    run_id: str,
    session_id: str = Query(..., min_length=8),
) -> dict:
    """Return OpenClaw-style session bundle: flow events, coach checkpoints, index summary."""
    try:
        bundle = get_review_context_bundle(session_id, run_id, coach_store_dir=COACH_SESSION_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return bundle


@app.post("/api/review-runs/{run_id}/repo-index/start")
def start_review_run_repo_index_api(run_id: str, body: ReviewRunIndexStartRequest) -> dict:
    """Start async full-repo indexing after quick attach; binds job to ReviewRun context."""
    _load_review_run_or_404(run_id)
    try:
        started = start_background_full_index(body.session_id, body.full_name.strip(), run_id=run_id)
        if not started.get("ok"):
            raise HTTPException(status_code=400, detail=started.get("message", "index start failed"))
        bind_index_job_to_context(body.session_id, run_id, started["job_id"], body.full_name.strip())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "run_id": run_id, **started}


@app.get("/api/index-jobs/{job_id}")
def get_repo_index_job_api(job_id: str) -> dict:
    result = get_index_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="unknown index job")
    return result


@app.get("/api/sessions/{session_id}/repos/{full_name:path}/index-report")
def get_repo_index_report_api(
    session_id: str,
    full_name: str,
    run_id: str = Query(""),
) -> dict:
    """Structured index presentation: charts, lists, and narrative for Show summary."""
    from agent.connector_runtime import load_session
    from agent.repo_index_store import load_report

    repo = full_name.strip()
    if len(session_id.strip()) < 8 or not repo:
        raise HTTPException(status_code=400, detail="session_id and full_name required")
    report = load_report(repo) or {}
    if not report:
        data = load_session(session_id)
        attached = (data.get("github_attached") or {}).get(repo) or {}
        report = dict(attached.get("index_report") or {})
        if run_id:
            ctx = (data.get("review_contexts") or {}).get(run_id) or {}
            report = dict(ctx.get("index_report") or report)
    if not report:
        raise HTTPException(status_code=404, detail="index report not found")
    return {"ok": True, "read_only": True, "session_id": session_id, "report": report}


@app.post("/api/review-runs/{run_id}/repo-index/fetch")
def fetch_review_run_repo_paths_api(run_id: str, body: ReviewRunIndexFetchRequest) -> dict:
    """Coach/on-demand path fetch — tier-2 stage deepening."""
    from agent.repo_index_stage_fetch import fetch_paths_for_run

    run, _record = _load_review_run_or_404(run_id)
    repo_name = str((run.selected_repo or {}).get("full_name") or "")
    if not repo_name:
        raise HTTPException(status_code=400, detail="ReviewRun has no selected repo")
    patterns = [str(p).strip() for p in body.patterns if str(p).strip()]
    if not patterns:
        raise HTTPException(status_code=400, detail="patterns required")
    try:
        result = fetch_paths_for_run(body.session_id, run_id, repo_name, patterns)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    from agent.repo_index_store import load_report

    return {
        "ok": True,
        "read_only": True,
        "run_id": run_id,
        "repo_full_name": repo_name,
        "report": load_report(repo_name) or {},
        **result,
    }


def _public_request_path(request_path: str) -> Path:
    candidate = Path(request_path.strip() or "examples/requests/support_triage_trial.yml")
    full_path = candidate if candidate.is_absolute() else ROOT_DIR / candidate
    full_path = full_path.resolve()
    requests_dir = (ROOT_DIR / "examples" / "requests").resolve()
    if not full_path.is_relative_to(requests_dir):
        raise ValueError("request_path must stay under examples/requests")
    if not full_path.is_file():
        raise FileNotFoundError(request_path)
    return full_path


@app.post("/api/sponsor-proof-runs")
def create_sponsor_proof_run(body: SponsorProofRunRequest) -> dict:
    """Create one local, read-only sponsor proof collector run."""
    try:
        request_path = _public_request_path(body.request_path)
        run = build_sponsor_proof_collector_run(
            request_path,
            scenario_name=body.scenario_name,
            lane=body.lane,
            downstream_fixture=body.downstream_fixture,
            question=body.question,
            subscriber=body.subscriber,
            live_tavily=body.live_tavily,
            live_nebius=body.live_nebius,
            composio_dry_run=body.composio_dry_run,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"request not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    record = write_sponsor_proof_run_record(run, ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR)

    with _sponsor_proof_runs_lock:
        _sponsor_proof_runs[run["run_id"]] = run

    return {
        "ok": True,
        "read_only": True,
        "run": run,
        "ledger_record": sponsor_proof_run_record_summary(record),
    }


@app.get("/api/sponsor-proof-runs/{run_id}")
def get_sponsor_proof_run(run_id: str) -> dict:
    """Return a previously created local sponsor proof collector run."""
    with _sponsor_proof_runs_lock:
        run = _sponsor_proof_runs.get(run_id)
    try:
        record = load_sponsor_proof_run_record(run_id, ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run is None:
        if record is None:
            raise HTTPException(status_code=404, detail="unknown sponsor proof run")
        run = record["run"]
    if record is None:
        record = sponsor_proof_run_record_summary(
            build_sponsor_proof_run_record(run, ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR)
        )
    else:
        record = sponsor_proof_run_record_summary(record)
    return {
        "ok": True,
        "read_only": True,
        "run": run,
        "ledger_record": record,
    }


@app.get("/api/sponsor-proof-run-ledger")
def sponsor_proof_run_ledger() -> dict:
    """Return the durable local sponsor proof run ledger."""
    return {
        "ok": True,
        "read_only": True,
        "ledger": build_sponsor_proof_run_ledger(
            list_sponsor_proof_run_records(ledger_dir=SPONSOR_PROOF_RUN_LEDGER_DIR)
        ),
    }


@app.post("/api/connectors/connect")
def connector_connect(body: ConnectorConnectRequest) -> dict:
    try:
        return start_connect(body.session_id, body.connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/connectors/status")
def connector_status(
    session_id: str = Query(...),
    connector_id: Optional[str] = Query(None),
) -> dict:
    if connector_id:
        from agent.connector_runtime import get_connection_status

        return {"session_id": session_id, "connection": get_connection_status(session_id, connector_id)}
    return {"session_id": session_id, "connections": session_statuses(session_id)}


@app.get("/api/connectors/oauth/callback/github", response_class=HTMLResponse)
def connector_oauth_callback_github(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
) -> HTMLResponse:
    if error or not code or not state:
        msg = error_description or error or "Authorization was denied or cancelled."
        return HTMLResponse(oauth_close_html("github", False, msg))
    result = finish_github_callback(code, state)
    return HTMLResponse(
        oauth_close_html(
            "github",
            bool(result.get("ok")),
            result.get("message", ""),
            result.get("session_id", ""),
        )
    )


@app.get("/api/connectors/oauth/callback/google_drive", response_class=HTMLResponse)
def connector_oauth_callback_google(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
) -> HTMLResponse:
    if error == "access_denied":
        return HTMLResponse(google_access_denied_html())
    if error or not code or not state:
        msg = error_description or error or "Authorization was denied or cancelled."
        return HTMLResponse(oauth_close_html("google_drive", False, msg))
    result = finish_google_callback(code, state)
    return HTMLResponse(
        oauth_close_html(
            "google_drive",
            bool(result.get("ok")),
            result.get("message", ""),
            result.get("session_id", ""),
        )
    )


@app.get("/api/connectors/oauth/popup/{connector_id}", response_class=HTMLResponse)
def connector_oauth_popup_get(
    connector_id: str,
    session_id: str = Query(...),
) -> HTMLResponse:
    return HTMLResponse(render_popup_html(connector_id, session_id))


@app.post("/api/connectors/oauth/popup/{connector_id}", response_class=HTMLResponse)
async def connector_oauth_popup_post(
    connector_id: str,
    session_id: str = Query(...),
    api_key: Optional[str] = Form(None),
    demo: Optional[str] = Form(None),
    confirm: Optional[str] = Form(None),
) -> HTMLResponse:
    if demo:
        result = demo_sign_in(session_id, connector_id)
        return HTMLResponse(oauth_close_html(connector_id, result.get("ok", False)))
    if connector_id == "openclaw" and confirm:
        result = demo_sign_in(session_id, "openclaw")
        return HTMLResponse(oauth_close_html("openclaw", result.get("ok", False)))
    if api_key:
        result = save_user_api_key(session_id, connector_id, api_key)
        return HTMLResponse(
            oauth_close_html(connector_id, result.get("ok", False))
            if result.get("ok")
            else render_popup_html(connector_id, session_id, error=result.get("message", "Failed"))
        )
    return HTMLResponse(render_popup_html(connector_id, session_id, error="Missing credentials"))


@app.post("/api/connectors/disconnect")
def connector_disconnect(body: ConnectorConnectRequest) -> dict:
    return disconnect(body.session_id, body.connector_id)


@app.get("/api/connectors/github/repos")
def github_list_repos(
    session_id: str = Query(...),
    q: str = Query(""),
) -> dict:
    try:
        return list_repositories(session_id, query=q)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/connectors/github/attach")
def github_attach_repo(body: GithubAttachRequest) -> dict:
    scope = f"chat_{body.session_id}"
    try:
        result = attach_repository(body.session_id, body.full_name.strip())
        if result.get("ok"):
            from agent.github_repo import _attached_repos

            entry = _attached_repos(body.session_id).get(body.full_name.strip(), {})
            digest = entry.get("digest", "")
            if digest:
                safe = body.full_name.strip().replace("/", "_") + ".md"
                fid, name, preview = save_upload(
                    scope=scope,
                    filename=safe,
                    data=digest.encode("utf-8"),
                )
                result["file_id"] = fid
                result["file_name"] = name
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/connectors/github/status")
def github_repo_status(
    session_id: str = Query(...),
    full_name: str = Query(...),
) -> dict:
    return get_repo_index_status(session_id, full_name.strip())


@app.get("/api/connectors/drive/files")
def drive_list_files(
    session_id: str = Query(...),
    q: str = Query(""),
    kind: str = Query("all"),
) -> dict:
    try:
        return list_drive_files(session_id, query=q, kind=kind)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/connectors/drive/attach")
def drive_attach_file(body: DriveAttachRequest) -> dict:
    scope = f"chat_{body.session_id}"
    try:
        result = attach_drive_file(body.session_id, body.file_id.strip())
        if result.get("ok"):
            from agent.google_drive_files import _attached_files

            entry = _attached_files(body.session_id).get(body.file_id.strip(), {})
            digest = entry.get("digest", "")
            if digest:
                safe = (result.get("name") or "drive_file").replace("/", "_")[:80]
                if not safe.endswith((".md", ".txt", ".csv")):
                    safe += ".md"
                fid, name, _preview = save_upload(
                    scope=scope,
                    filename=safe,
                    data=digest.encode("utf-8"),
                )
                result["upload_file_id"] = fid
                result["upload_name"] = name
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/connectors/drive/status")
def drive_file_status(
    session_id: str = Query(...),
    file_id: str = Query(...),
) -> dict:
    return get_drive_index_status(session_id, file_id.strip())


@app.post("/api/connectors/import")
def connector_import(body: ConnectorImportRequest) -> dict:
    scope = f"chat_{body.session_id}"
    try:
        result = import_connector_content(
            body.session_id,
            body.connector_id,
            body.action,
            query=body.query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not result.get("ok"):
        return result
    attachments: List[dict] = []
    for item in result.get("files", []):
        try:
            file_id, safe_name, preview = save_upload(
                scope=scope,
                filename=item.get("name", "import.txt"),
                data=item.get("content", "").encode("utf-8"),
            )
            attachments.append(
                {
                    "file_id": file_id,
                    "name": safe_name,
                    "preview": preview,
                    "source": body.connector_id,
                    "action": body.action,
                }
            )
        except ValueError as exc:
            attachments.append({"error": str(exc), "name": item.get("name")})
    result["attachments"] = attachments
    return result


@app.post("/api/connectors/export")
def connector_export(body: ConnectorExportRequest) -> dict:
    try:
        return export_to_connector(
            body.session_id,
            body.connector_id,
            body.content,
            destination=body.destination,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/skills/run")
def run_ui_skill_endpoint(body: SkillRunRequest) -> dict:
    import subprocess

    try:
        return run_ui_skill(body.skill_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Skill timed out") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/rehearsal/live-evidence")
def run_live_evidence_rehearsal() -> dict:
    """Run sanitized sponsor evidence rehearsal without mutating generated artifacts."""
    try:
        replay = build_trial_evidence_replay(
            DEFAULT_TRIAL_REQUEST,
            DEFAULT_REHEARSAL_EVIDENCE_DIR,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    markdown = render_trial_evidence_replay_markdown(replay)
    json_content = json.dumps(replay, indent=2, sort_keys=True) + "\n"
    scope = "review"
    subfolder = "live_evidence_rehearsal"
    md = save_output_registered(
        scope=scope,
        subfolder=subfolder,
        filename="support_triage_trial.live_evidence_rehearsal.md",
        content=markdown,
        label="Live evidence rehearsal Markdown",
    )
    js = save_output_registered(
        scope=scope,
        subfolder=subfolder,
        filename="support_triage_trial.live_evidence_rehearsal.json",
        content=json_content,
        label="Live evidence rehearsal JSON",
    )
    return {
        "ok": True,
        "title": "Sponsor evidence rehearsal",
        "message": "Live evidence rehearsal complete - sponsor outputs attached, decision stayed locked.",
        "request_path": replay["request_path"],
        "summary": replay["summary"],
        "decision_lock": replay["decision_lock"],
        "live_evidence_rehearsal": replay["live_evidence_rehearsal"],
        "safety_boundary": replay["safety_boundary"],
        "providers": _rehearsal_provider_rows(replay),
        "output_files": [
            _file_ref(md["file_id"], md["label"]),
            _file_ref(js["file_id"], js["label"]),
        ],
    }


@app.post("/api/rehearsal/custom-evidence")
def run_custom_evidence_rehearsal(body: CustomEvidenceRehearsalRequest) -> dict:
    """Run uploaded sanitized provider JSON through the same locked rehearsal engine."""
    try:
        evidence_dir, accepted_files = _uploaded_evidence_dir(
            body.storage_scope,
            body.attachment_ids,
        )
        replay = build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST, evidence_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    markdown = render_trial_evidence_replay_markdown(replay)
    json_content = json.dumps(replay, indent=2, sort_keys=True) + "\n"
    scope = "review"
    subfolder = "custom_evidence_rehearsal"
    md = save_output_registered(
        scope=scope,
        subfolder=subfolder,
        filename="support_triage_trial.uploaded_evidence_rehearsal.md",
        content=markdown,
        label="Uploaded evidence rehearsal Markdown",
    )
    js = save_output_registered(
        scope=scope,
        subfolder=subfolder,
        filename="support_triage_trial.uploaded_evidence_rehearsal.json",
        content=json_content,
        label="Uploaded evidence rehearsal JSON",
    )
    return {
        "ok": True,
        "title": "Uploaded sponsor evidence rehearsal",
        "message": "Uploaded evidence rehearsal complete - sanitized provider outputs attached, decision stayed locked.",
        "request_path": replay["request_path"],
        "accepted_files": accepted_files,
        "summary": replay["summary"],
        "decision_lock": replay["decision_lock"],
        "live_evidence_rehearsal": replay["live_evidence_rehearsal"],
        "safety_boundary": replay["safety_boundary"],
        "providers": _rehearsal_provider_rows(replay),
        "output_files": [
            _file_ref(md["file_id"], md["label"]),
            _file_ref(js["file_id"], js["label"]),
        ],
    }


@app.get("/api/walkthrough")
def design_partner_walkthrough() -> dict:
    """Return the buyer-facing walkthrough over existing public proof artifacts."""
    try:
        trial_report = build_trial_report(DEFAULT_TRIAL_REQUEST)
        outcome_memo = build_trial_outcome_memo(DEFAULT_TRIAL_REQUEST)
        replay = build_trial_evidence_replay(
            DEFAULT_TRIAL_REQUEST,
            DEFAULT_REHEARSAL_EVIDENCE_DIR,
        )
        sponsor_trace = build_sponsor_proof_trace(DEFAULT_TRIAL_REQUEST)
        pilot_memo = build_pilot_memo(DEFAULT_TRIAL_REQUEST)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    packet_reference = pilot_memo["packet_reference"]
    subscriber_rows = _walkthrough_subscriber_rows(packet_reference["packet_id"])
    provider_rows = _rehearsal_provider_rows(replay)
    sponsor_trace_steps = sponsor_trace["sponsor_steps"]
    sponsor_trace_summary = {
        "trace_id": sponsor_trace["trace_id"],
        "packet_id": sponsor_trace["packet_id"],
        "revision_id": sponsor_trace["revision_id"],
        "lane": sponsor_trace["lane"],
        "blast_radius": sponsor_trace["blast_radius"],
        "step_count": len(sponsor_trace_steps),
        "sponsor_order": [step["sponsor"] for step in sponsor_trace_steps],
        "decision_lock_unchanged": sponsor_trace["decision_lock_before"] == sponsor_trace["decision_lock_after"],
        "access_evidence_present": sponsor_trace["access_review_evidence"] is not None,
        "spend_evidence_present": sponsor_trace["spend_review_evidence"] is not None,
        "all_fallback_used": all(step["fallback_used"] for step in sponsor_trace_steps),
        "all_non_executing": all(not step["would_execute"] for step in sponsor_trace_steps),
        "all_non_approving": all(not step["can_approve_access"] for step in sponsor_trace_steps),
        "all_non_granting": all(not step["can_grant_permissions"] for step in sponsor_trace_steps),
        "all_non_mutating": all(not step["can_mutate_external_state"] for step in sponsor_trace_steps),
        "approves_access": sponsor_trace["safety_boundary"]["approves_access"],
        "approves_spend": sponsor_trace["safety_boundary"]["approves_spend"],
        "selects_provider": sponsor_trace["safety_boundary"]["selects_provider"],
        "guarantees_savings": sponsor_trace["safety_boundary"]["guarantees_savings"],
        "requires_human_review": sponsor_trace["safety_boundary"]["requires_human_review"],
        "artifact": "examples/generated/support_triage_trial.sponsor_proof_trace.md",
        "json_artifact": "examples/generated/support_triage_trial.sponsor_proof_trace.json",
        "steps": [
            {
                "sponsor": step["sponsor"],
                "verb": step["step_verb"],
                "summary": step["output_summary"],
                "used_live_key": step["used_live_key"],
                "fallback_used": step["fallback_used"],
                "would_execute": step["would_execute"],
                "can_approve_access": step["can_approve_access"],
                "can_grant_permissions": step["can_grant_permissions"],
                "can_mutate_external_state": step["can_mutate_external_state"],
            }
            for step in sponsor_trace_steps
        ],
    }
    sponsor_roles = [
        {
            "provider": item["provider"],
            "verb": item["verb"],
            "role": item["role"],
            "proof_type": item["proof_type"],
            "human_review_required": item["human_review_required"],
            "can_change_decision": item["can_change_decision"],
        }
        for item in pilot_memo["sponsor_contributions"]
    ]
    files = [
        _generated_file_ref("examples/generated/support_triage_trial.packet.json", "Trial packet JSON"),
        _generated_file_ref("examples/generated/support_triage_trial.outcome_memo.md", "Outcome memo Markdown"),
        _generated_file_ref("examples/generated/support_triage_trial.evidence_replay.md", "Sponsor replay Markdown"),
        _generated_file_ref("examples/generated/support_triage_trial.sponsor_proof_trace.md", "Sponsor Proof Trace Markdown"),
        _generated_file_ref(
            "examples/generated/support_triage_trial.sponsor_proof_trace.json",
            "Sponsor Proof Trace JSON",
            mime="application/json",
        ),
        _generated_file_ref("examples/generated/support_triage_trial.pilot_memo.md", "PilotMemo Markdown"),
        _generated_file_ref(
            "examples/generated/support_triage_trial.pilot_memo.json",
            "PilotMemo JSON",
            mime="application/json",
        ),
        _generated_file_ref("examples/generated/support_triage_trial.copy_review_brief.md", "Copy review brief"),
    ]

    return {
        "ok": True,
        "title": "Design partner walkthrough",
        "subtitle": "One trial request becomes one packet, one SponsorProofTrace, one review cycle, and one buyer-carried PilotMemo.",
        "mode": "offline_deterministic",
        "request_path": trial_report["request_path"],
        "safety_anchor": PILOT_MEMO_SAFETY_ANCHOR,
        "copy_review_brief": render_copy_review_brief(pilot_memo),
        "packet_reference": packet_reference,
        "packet_authority": {
            "headline": PACKET_AUTHORITY_SHORT_SENTENCE,
            "verification_endpoint": f"/api/packets/{packet_reference['packet_id']}/verification",
            "read_only": True,
            "source_of_truth": "packet_authority.verification",
            "subscriber_count": len(subscriber_rows),
            "categories": list(SUBSCRIBER_CATEGORY_ORDER),
        },
        "decision": {
            "verdict_class": pilot_memo["verdict_class"],
            "access_speed_lane": trial_report["access_speed_lane"]["lane"],
            "production_access": False,
            "permission_grants": False,
            "external_writes": False,
            "sponsors_can_change_decision": False,
            "next_human_action": pilot_memo["next_human_action"],
        },
        "steps": [
            {
                "id": "request",
                "label": "Request",
                "title": "Support triage trial request",
                "summary": trial_report["candidate_agent"]["purpose"],
                "primary_fact": trial_report["request_readiness"],
                "artifact": trial_report["request_path"],
                "boundary": "Public sample request; no secrets or private source.",
            },
            {
                "id": "packet",
                "label": "Packet",
                "title": "DecisionPacket forms",
                "summary": trial_report["packet_summary"]["review_posture"],
                "primary_fact": packet_reference["content_hash"],
                "artifact": packet_reference["packet_artifact"],
                "boundary": "Packet state is hash-pinned; production access stays false.",
            },
            {
                "id": "sponsor_proof_trace",
                "label": "Sponsor Proof",
                "title": "Collect sponsor proof",
                "summary": "Tavily -> Composio -> OpenClaw -> Nebius produce one locked SponsorProofTrace across access and spend evidence.",
                "primary_fact": f"{sponsor_trace_summary['step_count']} steps, decision lock unchanged",
                "artifact": sponsor_trace_summary["artifact"],
                "boundary": "Sponsor proof is observational; it cannot approve, grant, write, spend, select providers, or mutate production.",
            },
            {
                "id": "sponsor_replay",
                "label": "Sponsor Replay",
                "title": "Attach sanitized evidence",
                "summary": "Sanitized Tavily, Composio, Nebius, and OpenClaw outputs attach to the same locked decision.",
                "primary_fact": f"{replay['summary']['provider_count']} providers, decision locked",
                "artifact": "examples/generated/support_triage_trial.evidence_replay.md",
                "boundary": "Sponsors cannot approve, grant, execute, mutate, or reduce proof debt automatically.",
            },
            {
                "id": "review_cycle",
                "label": "Review Cycle",
                "title": "Owners receive proof debt",
                "summary": outcome_memo["decision"]["summary"],
                "primary_fact": f"{len(outcome_memo['reviewer_routes'])} reviewer routes",
                "artifact": "examples/generated/support_triage_trial.outcome_memo.md",
                "boundary": "Humans decide scoped validation outside this public harness.",
            },
            {
                "id": "pilot_memo",
                "label": "PilotMemo",
                "title": "Buyer-carried artifact",
                "summary": "Export the memo or copy a short review brief for Security, Finance, and CTO review.",
                "primary_fact": pilot_memo["memo_id"],
                "artifact": "examples/generated/support_triage_trial.pilot_memo.md",
                "boundary": PILOT_MEMO_SAFETY_ANCHOR,
            },
        ],
        "subscriber_rows": subscriber_rows,
        "sponsor_roles": sponsor_roles,
        "sponsor_proof_trace": sponsor_trace_summary,
        "provider_rows": provider_rows,
        "reviewer_routing": pilot_memo["reviewer_routing"],
        "blocked_claims": pilot_memo["blocked_claims"],
        "missing_proof": pilot_memo["missing_proof"],
        "output_files": files,
        "safety_boundary": pilot_memo["safety_boundary"],
        "private_boundary": pilot_memo["private_boundary"],
    }


@app.get("/api/workbench")
def packet_workbench_registry() -> dict:
    """Return the fixture-only Packet Workbench lane registry."""
    return build_workbench_registry()


@app.post("/api/workbench/generate")
def packet_workbench_generate(body: WorkbenchGenerateRequest) -> dict:
    """Generate a local, read-only Workbench packet result from a registered fixture."""
    try:
        result = build_workbench_result(body.fixture_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    fixture_id = result["fixture"]["fixture_id"]
    subfolder = f"workbench/{fixture_id}"
    md = save_output_registered(
        scope="review",
        subfolder=subfolder,
        filename=f"{fixture_id}.workbench.md",
        content=render_workbench_markdown(result),
        label="Workbench result Markdown",
        use_timestamp=False,
    )
    js = save_output_registered(
        scope="review",
        subfolder=subfolder,
        filename=f"{fixture_id}.workbench.json",
        content=workbench_result_to_pretty_json(result) + "\n",
        label="Workbench result JSON",
        use_timestamp=False,
    )
    return {
        **result,
        "output_files": [
            _file_ref(md["file_id"], md["label"]),
            _file_ref(js["file_id"], js["label"]),
        ],
    }


@app.get("/api/ia-packet")
def ia_packet_detail(fixture: str = Query(default="mcp_tool_blast_radius")) -> dict:
    """Return one read-only IA Packet detail surface from a registered public fixture."""
    try:
        detail = build_ia_packet_detail(fixture)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    fixture_id = detail["fixture"]["fixture_id"]
    subfolder = f"ia-packets/{fixture_id}"
    md = save_output_registered(
        scope="review",
        subfolder=subfolder,
        filename=f"{fixture_id}.ia_packet.md",
        content=render_ia_packet_detail_markdown(detail),
        label="IA Packet Markdown",
        use_timestamp=False,
    )
    js = save_output_registered(
        scope="review",
        subfolder=subfolder,
        filename=f"{fixture_id}.ia_packet.json",
        content=ia_packet_detail_to_pretty_json(detail) + "\n",
        label="IA Packet JSON",
        use_timestamp=False,
    )
    try:
        suggestions = build_packet_idle_suggestions(fixture_id)
    except Exception:
        suggestions = []
    return {
        **detail,
        "suggestions": suggestions,
        "output_files": [
            _file_ref(md["file_id"], md["label"]),
            _file_ref(js["file_id"], js["label"]),
        ],
    }


@app.get("/api/examples")
def examples() -> List[dict]:
    return [
        {
            "label": "Catalog overview",
            "description": "See what providers and workload types we track.",
            "message": "Use get_catalog_summary: what does InferenceAtlas track?",
        },
        {
            "label": "Mistral pricing",
            "description": "Live web price check vs our catalog.",
            "message": (
                "Use tavily_search for Mistral Large pricing, then compare_providers "
                "for llm workloads in the catalog."
            ),
        },
        {
            "label": "GPT-4o alternative",
            "description": "Find a cheaper model for heavy token usage.",
            "message": (
                "I run 500M tokens/month on GPT-4o input+output. Use compare_providers "
                "for llm and recommend the cheapest credible alternative."
            ),
        },
        {
            "label": "Tool access review",
            "description": "Classic hackathon scenario — should the bot get tools?",
            "message": (
                "Should our support triage agent get GitHub issues, Slack incident "
                "channels, and Jira ticket creation access?"
            ),
        },
    ]


def _build_user_message(
    message: str,
    scope: str,
    attachment_ids: List[str],
) -> Tuple[str, List[str]]:
    parts = [message.strip()]
    warnings: List[str] = []
    for file_id in attachment_ids[:5]:
        loaded = load_upload(scope, file_id)
        if loaded:
            name, text = loaded
            parts.append(format_attachment_block(name, text))
        else:
            warnings.append(f"Attachment {file_id[:8]}… was not found (re-upload).")
    return "\n".join(parts).strip(), warnings


def _collect_file_blocks(
    scope: str,
    attachment_ids: List[str],
) -> Tuple[List[Tuple[str, str]], List[str]]:
    blocks: List[Tuple[str, str]] = []
    warnings: List[str] = []
    for file_id in attachment_ids[:5]:
        loaded = load_upload(scope, file_id)
        if loaded:
            blocks.append(loaded)
        else:
            warnings.append(f"Attachment {file_id[:8]}… was not found (re-upload).")
    return blocks, warnings


def _chat_validate() -> None:
    if not _live_deps_available():
        raise HTTPException(
            status_code=503,
            detail="Missing Python deps. Run: pip install -r agent/requirements.txt",
        )
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="No LLM API key configured. Set NEBIUS_API_KEY or OPENAI_API_KEY in .env",
        )


def _execute_chat(body: ChatRequest) -> ChatResponse:
    message = body.message.strip()
    skill_ids = [s for s in body.skill_ids if s]
    github_repos = [r.strip() for r in body.github_repos if r.strip()]
    drive_file_ids = [f.strip() for f in body.drive_file_ids if f.strip()]
    if (
        not message
        and not skill_ids
        and not github_repos
        and not drive_file_ids
        and not body.attachment_ids
    ):
        raise HTTPException(
            status_code=400,
            detail="Add a question, skill, GitHub repo, Drive file, or upload",
        )

    session_id, agent = _get_or_create_session(body.session_id)
    set_metrics_session(session_id)
    scope = f"chat_{session_id}"
    file_blocks, file_warnings = _collect_file_blocks(scope, body.attachment_ids)

    position = (
        body.skill_context_position
        if body.skill_context_position in ("prepend", "append")
        else "prepend"
    )
    orch = orchestrate_chat(
        message=message,
        skill_ids=skill_ids,
        skill_position=position,
        session_id=session_id,
        github_repos=github_repos,
        drive_file_ids=drive_file_ids,
        file_blocks=file_blocks,
        attach_warnings=file_warnings,
        current_fixture=body.current_fixture.strip(),
        chip_entities=body.chip_entities,
    )

    plain = (
        not orch.skills_used
        and not orch.github_used
        and not orch.drive_used
        and not orch.file_names
        and not orch.engine_source
        and not orch.direct_reply
        and not orch.harness_injected
    )
    try:
        if orch.direct_reply:
            reply = orch.direct_reply
            record_copilot_direct()
            agent.remember_exchange(orch.user_display, reply)
        elif plain:
            _chat_validate()
            reply = agent.chat(orch.user_message or message)
        else:
            _chat_validate()
            reply = agent.chat_orchestrated(
                orch.user_display,
                orch.llm_message,
                system_prompt=orch.system_prompt,
                use_tools=orch.use_tools,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    reply = format_reply_with_manifest(reply, orch.context_manifest)
    if orch.attach_warnings:
        reply = reply + "\n\n" + "\n".join(orch.attach_warnings)

    output_files: List[dict] = []
    try:
        md = save_output_registered(
            scope=scope,
            filename="assistant_reply.md",
            content=f"# Assistant reply\n\n{reply}\n",
            label="Reply (Markdown)",
        )
        js = save_output_registered(
            scope=scope,
            filename="assistant_reply.json",
            content=json.dumps(
                {
                    "message": message,
                    "reply": reply,
                    "answer": orch.direct_answer,
                    "manifest": orch.context_manifest,
                    "thinking": orch.thinking_steps,
                    "attachments": body.attachment_ids,
                },
                indent=2,
            ),
            label="Reply (JSON)",
        )
        output_files = [
            _file_ref(md["file_id"], md["label"]),
            _file_ref(js["file_id"], js["label"]),
        ]
    except Exception as exc:
        output_files = [
            {"file_id": "", "label": f"Could not save output: {exc}", "url": ""}
        ]

    try:
        mind_observe(
            MindObserveRequest(scenario="support_triage_agent", text=message),
        )
    except Exception:
        pass

    clear_metrics_session()
    return ChatResponse(
        reply=reply,
        session_id=session_id,
        answer=orch.direct_answer,
        output_files=output_files,
        skills_used=orch.skills_used,
        github_repos_used=orch.github_used,
        drive_files_used=orch.drive_used,
        thinking_logs=orch.thinking_steps,
        context_manifest=orch.context_manifest,
        github_index=orch.github_index,
        use_tools=orch.use_tools,
        engine_source=orch.engine_source,
        cost_plan_ok=orch.cost_plan_ok,
    )


@app.post("/api/upload")
async def upload_file(
    channel: str = Form(...),
    session_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
) -> dict:
    if channel not in ("chat", "review"):
        raise HTTPException(status_code=400, detail="channel must be chat or review")
    storage_scope = f"{channel}_{session_id or 'anonymous'}"
    data = await file.read()
    try:
        file_id, safe_name, preview = save_upload(
            scope=storage_scope,
            filename=file.filename or "upload.txt",
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "file_id": file_id,
        "name": safe_name,
        "preview": preview,
        "storage_scope": storage_scope,
    }


@app.get("/api/files/{file_id}")
def download_registered_file(file_id: str) -> FileResponse:
    resolved = resolve_download(file_id)
    if not resolved:
        raise HTTPException(status_code=404, detail="file not found")
    path, _label, mime = resolved
    return FileResponse(path, filename=path.name, media_type=mime)


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    return _execute_chat(body)


@app.post("/api/chat/stream")
def chat_stream(body: ChatRequest) -> StreamingResponse:
    """SSE: thinking log lines, then final reply payload."""

    def event_stream():
        try:
            message = body.message.strip()
            skill_ids = [s for s in body.skill_ids if s]
            github_repos = [r.strip() for r in body.github_repos if r.strip()]
            drive_file_ids = [f.strip() for f in body.drive_file_ids if f.strip()]
            if (
                not message
                and not skill_ids
                and not github_repos
                and not drive_file_ids
                and not body.attachment_ids
            ):
                yield _sse({"type": "error", "detail": "Add a question, skill, repo, Drive file, or upload"})
                return

            session_id, agent = _get_or_create_session(body.session_id)
            set_metrics_session(session_id)
            scope = f"chat_{session_id}"
            file_blocks, file_warnings = _collect_file_blocks(scope, body.attachment_ids)
            position = (
                body.skill_context_position
                if body.skill_context_position in ("prepend", "append")
                else "prepend"
            )
            orch = orchestrate_chat(
                message=message,
                skill_ids=skill_ids,
                skill_position=position,
                session_id=session_id,
                github_repos=github_repos,
                drive_file_ids=drive_file_ids,
                file_blocks=file_blocks,
                attach_warnings=file_warnings,
                current_fixture=body.current_fixture.strip(),
                chip_entities=body.chip_entities,
            )

            for line in orch.thinking_steps:
                yield _sse({"type": "thinking", "line": line})
                time.sleep(0.35)

            plain = (
                not orch.skills_used
                and not orch.github_used
                and not orch.drive_used
                and not orch.file_names
                and not orch.engine_source
                and not orch.direct_reply
                and not orch.harness_injected
            )
            if orch.direct_reply:
                reply = orch.direct_reply
                record_copilot_direct()
                agent.remember_exchange(orch.user_display, reply)
            elif plain:
                _chat_validate()
                reply = agent.chat(orch.user_message or message)
            else:
                _chat_validate()
                reply = agent.chat_orchestrated(
                    orch.user_display,
                    orch.llm_message,
                    system_prompt=orch.system_prompt,
                    use_tools=orch.use_tools,
                )
            clear_metrics_session()
            reply = format_reply_with_manifest(reply, orch.context_manifest)
            if orch.attach_warnings:
                reply = reply + "\n\n" + "\n".join(orch.attach_warnings)

            output_files: List[dict] = []
            try:
                md = save_output_registered(
                    scope=scope,
                    filename="assistant_reply.md",
                    content=f"# Assistant reply\n\n{reply}\n",
                    label="Reply (Markdown)",
                )
                js = save_output_registered(
                    scope=scope,
                    filename="assistant_reply.json",
                    content=json.dumps(
                        {
                            "message": message,
                            "reply": reply,
                            "answer": orch.direct_answer,
                            "manifest": orch.context_manifest,
                        },
                        indent=2,
                    ),
                    label="Reply (JSON)",
                )
                output_files = [
                    _file_ref(md["file_id"], md["label"]),
                    _file_ref(js["file_id"], js["label"]),
                ]
            except Exception as exc:
                output_files = [
                    {"file_id": "", "label": f"Could not save output: {exc}", "url": ""}
                ]

            try:
                mind_observe(
                    MindObserveRequest(scenario="support_triage_agent", text=message),
                )
            except Exception:
                pass

            yield _sse(
                {
                    "type": "done",
                    "reply": reply,
                    "session_id": session_id,
                    "answer": orch.direct_answer,
                    "output_files": output_files,
                    "skills_used": orch.skills_used,
                    "github_repos_used": orch.github_used,
                    "drive_files_used": orch.drive_used,
                    "thinking_logs": orch.thinking_steps,
                    "context_manifest": orch.context_manifest,
                    "github_index": orch.github_index,
                    "use_tools": orch.use_tools,
                    "engine_source": orch.engine_source,
                    "cost_plan_ok": orch.cost_plan_ok,
                }
            )
        except HTTPException as exc:
            yield _sse({"type": "error", "detail": exc.detail})
        except Exception as exc:
            yield _sse({"type": "error", "detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _live_proof_health(mind) -> dict:
    """Derive lifecycle metrics from the persisted packet (not static templates)."""
    missing = mind.packet.get("missing_proof", [])
    evidence = len(mind.packet.get("evidence_notes", []))
    score = max(35.0, min(100.0, 88.0 - 2.5 * len(missing) + 0.5 * min(evidence, 6)))
    status = "healthy" if score >= 80 else "attention" if score >= 60 else "drifting"
    return {"overall_score": round(score, 1), "overall_status": status}


def _snapshot_metrics(mind) -> dict:
    brief = build_agent_access_decision_brief(mind.packet)
    proof_health = _live_proof_health(mind)
    missing = mind.packet.get("missing_proof", [])
    return {
        "tick": mind.tick,
        "open_proof_items": len(missing),
        "proof_health_score": float(proof_health.get("overall_score", 0)),
        "proof_health_status": proof_health.get("overall_status", "unknown"),
        "max_tension": mind.max_tension_strength(),
        "cortex_budget": int(mind.internal.get("cortex_budget", 0)),
        "evidence_count": len(mind.packet.get("evidence_notes", [])),
        "scoped_validation": brief["go_no_go"]["scoped_validation_review"],
        "next_validation": brief["go_no_go"]["next_validation"],
        "recommended_step": brief["decision"]["recommended_next_step"],
        "reason": brief["decision"]["reason"],
    }


def _events_for_tick(mind, tick: int) -> List[dict]:
    log = mind.internal.get("transition_log", [])
    return [e for e in log if e.get("tick") == tick]


def _narrate_events(events: List[dict]) -> List[str]:
    lines: List[str] = []
    for ev in events:
        name = ev.get("event", "")
        detail = ev.get("detail") or {}
        if name == "step_ok":
            obs = detail.get("observations", 0)
            if obs:
                lines.append(f"Ingested {obs} queued note(s) into evidence_notes.")
            lines.append(
                f"Recomputed tensions (max {detail.get('max_tension', 0):.2f}); "
                f"cortex {'applied a patch' if detail.get('cortex') else 'not needed this cycle'}."
            )
        elif name == "cortex_patch":
            lines.append("LLM cortex appended an evidence note (verdict and safety fields stay locked).")
        elif name == "contract_rollback":
            lines.append(
                "Packet failed public contract validation — rolled back to deterministic baseline."
            )
        else:
            lines.append(f"Event: {name}")
    return lines


def _mind_summary(mind) -> dict:
    posture = mind.packet.get("approval_posture", {})
    meta = SCENARIO_LABELS.get(mind.scenario, {"title": mind.scenario, "blurb": ""})
    tensions = mind.internal.get("tensions", [])[:5]
    top = tensions[0] if tensions else {}
    top_type = top.get("type", "")
    prod = posture.get("production_access", "unknown")
    brief = build_agent_access_decision_brief(mind.packet)
    proof_health = _live_proof_health(mind)
    missing = mind.packet.get("missing_proof", [])
    missing_preview = [
        f"{item.get('item', 'proof')}: {item.get('owner', 'unassigned')}"
        for item in missing[:4]
    ]
    tick_events = _events_for_tick(mind, mind.tick)
    artifacts = _register_mind_artifacts(mind.scenario)
    return {
        "scenario": mind.scenario,
        "title": meta["title"],
        "blurb": meta["blurb"],
        "tick": mind.tick,
        "step_label": f"Review cycle #{mind.tick}",
        "tensions": tensions,
        "max_tension": mind.max_tension_strength(),
        "top_tension_label": TENSION_LABELS.get(top_type, top_type or "All clear"),
        "top_tension_strength": top.get("strength", 0),
        "cortex_budget": mind.internal.get("cortex_budget", 0),
        "production_access": prod,
        "access_badge": "Blocked" if prod == "blocked" else str(prod).replace("_", " ").title(),
        "access_class": "blocked" if prod == "blocked" else "review",
        "blocked_explainer": (
            "Production access stays blocked by design until humans approve outside this demo."
            if prod == "blocked"
            else ""
        ),
        "verdict_short": brief["decision"]["verdict"],
        "recommended_step": brief["decision"]["recommended_next_step"],
        "reason": brief["decision"]["reason"],
        "scoped_validation": brief["go_no_go"]["scoped_validation_review"],
        "next_validation": brief["go_no_go"]["next_validation"],
        "open_proof_items": len(missing),
        "missing_proof_preview": missing_preview,
        "proof_label": f"{len(missing)} proof gaps open",
        "proof_health_score": proof_health.get("overall_score"),
        "proof_health_status": proof_health.get("overall_status"),
        "evidence_count": len(mind.packet.get("evidence_notes", [])),
        "last_cycle_lines": _narrate_events(tick_events),
        "artifacts": artifacts,
    }


def _register_mind_artifacts(scenario: str) -> List[dict]:
    refs: List[dict] = []
    for suffix, label in (
        ("decision_brief.md", "Decision brief"),
        ("packet.md", "Decision packet"),
    ):
        path = MIND_RUNTIME_DIR / f"{scenario}.{suffix}"
        if path.is_file():
            file_id = register_download(path, label=f"{label} ({scenario})")
            refs.append(_file_ref(file_id, label))
    return refs


def _baseline_cycle_result(mind) -> dict:
    live = _mind_summary(mind)
    return {
        "scenario": mind.scenario,
        "title": live["title"],
        "delta": [
            f"Scenario loaded at review cycle #{live['tick']}.",
            f"{live['open_proof_items']} proof gaps; production access blocked (expected).",
        ],
        "narrative": live.get("last_cycle_lines") or ["Ready — run a review cycle to advance state."],
        "live": live,
    }


def _cycle_delta(before: dict, after: dict) -> List[str]:
    deltas: List[str] = []
    if after["tick"] != before["tick"]:
        deltas.append(f"Advanced to review cycle #{after['tick']}.")
    if after["open_proof_items"] != before["open_proof_items"]:
        deltas.append(
            f"Open proof gaps: {before['open_proof_items']} → {after['open_proof_items']}."
        )
    if after["evidence_count"] != before["evidence_count"]:
        deltas.append(
            f"Evidence notes: {before['evidence_count']} → {after['evidence_count']}."
        )
    if after["proof_health_score"] != before["proof_health_score"]:
        deltas.append(
            f"Proof health score: {before['proof_health_score']:.0f} → {after['proof_health_score']:.0f}."
        )
    if after["max_tension"] != before["max_tension"]:
        deltas.append(
            f"Max tension: {before['max_tension']:.2f} → {after['max_tension']:.2f}."
        )
    if after["cortex_budget"] != before["cortex_budget"]:
        deltas.append(
            f"AI cortex budget: {before['cortex_budget']} → {after['cortex_budget']}."
        )
    if not deltas:
        deltas.append(
            "Cycle ran: packet contract revalidated; production access unchanged (still blocked)."
        )
    return deltas


@app.get("/api/mind/guide")
def mind_guide() -> dict:
    return {
        "title": "Hackathon access-review walkthrough",
        "subtitle": "Packet before action — live DecisionPacket + brief each cycle",
        "steps": [
            {
                "id": 1,
                "title": "Reset scenarios",
                "action": "btn-mind-init",
                "detail": "Loads three real scenario packets (support triage, read-only analytics, admin bot).",
            },
            {
                "id": 2,
                "title": "Add evidence (optional)",
                "action": "review-evidence",
                "detail": "Paste a note or upload a text file — queued for support_triage_agent on the next cycle.",
            },
            {
                "id": 3,
                "title": "Run review cycle",
                "action": "btn-mind-step",
                "detail": "Applies Mind(t)→Mind(t+1): rules, proof-health tensions, optional LLM evidence patch.",
            },
            {
                "id": 4,
                "title": "Read live results",
                "action": "cycle-feed",
                "detail": "Main panel shows what changed; download packet/brief Markdown artifacts.",
            },
        ],
        "expect_blocked": True,
    }


@app.get("/api/mind")
def mind_status() -> dict:
    minds = load_all_minds()
    if not minds:
        return {"initialized": False, "scenarios": list(SCENARIOS), "minds": []}
    return {
        "initialized": True,
        "scenarios": list(SCENARIOS),
        "minds": [_mind_summary(m) for m in minds.values()],
    }


@app.post("/api/mind/init")
def mind_init() -> dict:
    results: List[dict] = []
    cycle_results: List[dict] = []
    with _lock:
        for scenario in SCENARIOS:
            mind = init_mind(scenario)
            save_mind(mind)
            project_mind(mind, MIND_RUNTIME_DIR)
            live = _mind_summary(mind)
            results.append(live)
            cycle_results.append(_baseline_cycle_result(mind))
    return {
        "ok": True,
        "message": "Reset complete — 3 live scenario packets loaded (cycle 0). Run review cycle next.",
        "scenarios": list(SCENARIOS),
        "minds": results,
        "cycle_results": cycle_results,
    }


@app.post("/api/mind/step")
def mind_step(body: MindStepRequest) -> dict:
    targets = [body.scenario] if body.scenario else list(SCENARIOS)
    if body.scenario and body.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail="unknown scenario")
    results = []
    cycle_results: List[dict] = []
    with _lock:
        for scenario in targets:
            mind = load_mind(scenario) or init_mind(scenario)
            before = _snapshot_metrics(mind)
            mind = step(mind, allow_cortex=not body.no_cortex)
            save_mind(mind)
            project_mind(mind, MIND_RUNTIME_DIR)
            after = _snapshot_metrics(mind)
            live = _mind_summary(mind)
            delta = _cycle_delta(before, after)
            narrative = _narrate_events(_events_for_tick(mind, mind.tick))
            brief_md = render_decision_brief_markdown(
                build_agent_access_decision_brief(mind.packet)
            )
            packet_md = render_packet_markdown(mind.packet)
            brief_reg = save_output_registered(
                scope="mind",
                subfolder=scenario,
                filename=f"cycle_{mind.tick}_brief.md",
                content=brief_md,
                label=f"Cycle {mind.tick} brief",
            )
            packet_reg = save_output_registered(
                scope="mind",
                subfolder=scenario,
                filename=f"cycle_{mind.tick}_packet.md",
                content=packet_md,
                label=f"Cycle {mind.tick} packet",
            )
            live["artifacts"] = _register_mind_artifacts(scenario)
            live["artifacts"].extend(
                [
                    _file_ref(brief_reg["file_id"], brief_reg["label"]),
                    _file_ref(packet_reg["file_id"], packet_reg["label"]),
                ]
            )
            results.append(live)
            cycle_results.append(
                {
                    "scenario": scenario,
                    "title": live["title"],
                    "delta": delta,
                    "narrative": narrative,
                    "live": live,
                }
            )
    message = (
        f"Cycle #{cycle_results[0]['live']['tick'] if cycle_results else '?'} complete — "
        "see Live results in the main panel."
    )
    return {
        "ok": True,
        "message": message,
        "minds": results,
        "cycle_results": cycle_results,
    }


class MindObserveWithFiles(BaseModel):
    scenario: str = Field(default="support_triage_agent")
    text: str = Field(default="", max_length=8000)
    attachment_ids: List[str] = Field(default_factory=list)
    storage_scope: str = Field(default="review_anonymous")


@app.post("/api/mind/observe")
def mind_observe(body: MindObserveRequest) -> dict:
    return _mind_observe_impl(
        body.scenario,
        body.text,
        [],
        f"review_anonymous",
    )


@app.post("/api/mind/observe/full")
def mind_observe_full(body: MindObserveWithFiles) -> dict:
    if body.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail="unknown scenario")
    text, _warnings = _build_user_message(
        body.text, body.storage_scope, body.attachment_ids
    )
    if not text.strip():
        raise HTTPException(status_code=400, detail="Provide a note or attachment")
    return _mind_observe_impl(body.scenario, text, body.attachment_ids, body.storage_scope)


def _mind_observe_impl(
    scenario: str,
    text: str,
    attachment_ids: List[str],
    storage_scope: str,
) -> dict:
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail="unknown scenario")
    note = text.strip()
    if not note:
        raise HTTPException(status_code=400, detail="Empty observation")
    with _lock:
        mind = load_mind(scenario) or init_mind(scenario)
        obs = mind.internal.setdefault("observations", [])
        obs.append(note)
        save_mind(mind)
    return {
        "ok": True,
        "scenario": scenario,
        "queued_observations": len(obs),
        "message": (
            f"Queued for {SCENARIO_LABELS.get(scenario, {}).get('title', scenario)}. "
            "Run review cycle to ingest into evidence_notes."
        ),
        "attachments": len(attachment_ids),
    }


@app.post("/api/reset")
def reset(body: ResetRequest) -> dict:
    with _lock:
        agent = _sessions.pop(body.session_id, None)
    if agent:
        agent.reset()
    return {"ok": True, "session_id": body.session_id}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/walkthrough")
def walkthrough_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/workbench")
def workbench_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/packet")
def packet_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def _receipt_html_escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _receipt_scope_text(items: Any) -> str:
    values = [str(item) for item in items or [] if str(item).strip()]
    return ", ".join(values) if values else "none"


def _receipt_status_label(value: Any) -> str:
    return str(value or "verification_pending").replace("_", " ").title()


def _render_review_run_approval_receipt_html(receipt: dict[str, Any], run: ReviewRun) -> str:
    ref = receipt.get("packet_reference") or {}
    movement = receipt.get("movement") or {}
    approval_summary = receipt.get("approval_summary") or {}
    portkey = receipt.get("portkey") or {}
    safety = receipt.get("safety_boundary") or {}
    approvals = receipt.get("approvals") or []
    run_id = str(ref.get("run_id") or run.run_id)
    receipt_id = str(receipt.get("receipt_id") or "receipt pending")
    status = str(receipt.get("status") or "verification_pending")
    status_label = _receipt_status_label(status)
    repo_name = str((run.selected_repo or {}).get("full_name") or "selected repo")
    packet_id = str(ref.get("packet_id") or "not generated")
    revision_id = str(ref.get("revision_id") or "not generated")
    content_hash = str(ref.get("content_hash") or "missing")
    allowed_scope = _receipt_scope_text(movement.get("allowed_scope"))
    review_scope = _receipt_scope_text(movement.get("review_required_scope"))
    blocked_scope = _receipt_scope_text(movement.get("still_blocked_scope"))
    receipt_hash = str(receipt.get("receipt_hash") or "missing")
    portkey_state = str(portkey.get("state") or "Block")
    portkey_event_id = str(portkey.get("event_id") or "not recorded")
    api_mutation = bool(portkey.get("api_call_made"))
    policy_mutation = bool(portkey.get("policy_mutation_allowed"))
    approval_state = str(approval_summary.get("human_approval_state") or "unknown").replace("_", " ")
    app_path = f"/?review=receipt&run={run_id}&screen=packet_rerun"
    api_path = str(receipt.get("verification_path") or f"/api/review-runs/{run_id}/approval-receipt")
    copy_receipt = "\n".join(
        [
            f"Portable approval receipt: {receipt_id}",
            f"Status: {status_label}",
            f"Run: {run_id}",
            f"Packet: {packet_id}",
            f"Revision: {revision_id}",
            f"Content hash: {content_hash}",
            f"Receipt hash: {receipt_hash}",
            f"Human approval state: {approval_state}",
            f"Allowed scope: {allowed_scope}",
            f"Review required: {review_scope}",
            f"Still blocked: {blocked_scope}",
            f"Portkey state: {portkey_state}",
            f"Verify: /approval-receipt/{run_id}",
            "Safety: humans approved scoped movement; IA did not approve, grant, write, or mutate Portkey policy.",
        ]
    )
    copy_pr = "\n".join(
        [
            f"IA receipt: {receipt_id}",
            f"Packet: {packet_id}",
            f"Revision: {revision_id}",
            f"Receipt status: {status_label}",
            f"Approved scope: {allowed_scope}",
            f"Still blocked: {blocked_scope}",
            f"Verify: /approval-receipt/{run_id}",
            "Safety: humans approved scoped movement; IA did not approve, grant, write, or mutate Portkey policy.",
        ]
    )
    mutation_state = "none" if not api_mutation and not policy_mutation else "review required"
    approval_rows = "\n".join(
        f"""
              <tr>
                <th>{_receipt_html_escape(item.get("label") or item.get("role_id") or "Reviewer")}</th>
                <td>
                  <strong>{_receipt_html_escape(_receipt_status_label(item.get("approval_state")))}</strong>
                  <span>{_receipt_html_escape(item.get("scope") or "Scope not recorded")}</span>
                </td>
              </tr>
        """
        for item in approvals
    ) or """
              <tr>
                <th>No approvals</th>
                <td><strong>Missing</strong><span>ReviewRun has not recorded human approval proof yet.</span></td>
              </tr>
    """
    safety_rows = "\n".join(
        f"""
              <tr class="{'bad' if bool(value) and key.startswith('ia_') else 'good'}">
                <th>{_receipt_html_escape(key.replace("_", " "))}</th>
                <td><strong>{_receipt_html_escape(str(bool(value)).lower())}</strong></td>
              </tr>
        """
        for key, value in (
            ("ia_approved", safety.get("ia_approved")),
            ("ia_grants_permissions", safety.get("ia_grants_permissions")),
            ("ia_executes_external_writes", safety.get("ia_executes_external_writes")),
            ("ia_mutates_portkey_policy", safety.get("ia_mutates_portkey_policy")),
            ("downstream_must_enforce_scope", safety.get("downstream_must_enforce_scope")),
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>InferenceAtlas Receipt Verification</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #020204;
      --surface: rgba(255, 255, 255, 0.052);
      --surface-strong: rgba(255, 255, 255, 0.082);
      --line: rgba(255, 255, 255, 0.13);
      --line-soft: rgba(255, 255, 255, 0.075);
      --text: rgba(255, 255, 255, 0.94);
      --muted: rgba(255, 255, 255, 0.58);
      --faint: rgba(255, 255, 255, 0.36);
      --green: #75d99c;
      --amber: #e7bd58;
      --red: #ff8989;
      --mono: "SFMono-Regular", "SF Mono", Consolas, "Liberation Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 13px;
      letter-spacing: 0;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0) 18rem),
        linear-gradient(135deg, #09090c 0%, #020204 46%, #000 100%);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.032) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.026) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.74), transparent 72%);
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 22px 0 40px;
    }}
    a, button {{
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 11px;
      color: var(--text);
      background: rgba(255, 255, 255, 0.06);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
      font: inherit;
      font-size: 12px;
      font-weight: 750;
      text-decoration: none;
      cursor: pointer;
    }}
    button:hover, a:hover {{ border-color: rgba(255,255,255,0.3); background: rgba(255,255,255,0.08); }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{
      font-size: 20px;
      line-height: 1.2;
      font-weight: 760;
      letter-spacing: 0;
    }}
    h2 {{
      font-size: 13px;
      line-height: 1.25;
      font-weight: 760;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      min-height: 42px;
      margin-bottom: 12px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }}
    .mark {{
      width: 22px;
      height: 22px;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 5px;
      background: linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.035));
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);
    }}
    .brand strong {{
      display: block;
      font-size: 13px;
      line-height: 1.2;
    }}
    .brand span, .crumb, .label, .audit-table th, .rail-label {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 760;
      letter-spacing: 0;
    }}
    .receipt-console {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.095), rgba(255,255,255,0.028)),
        rgba(0,0,0,0.52);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 24px 80px rgba(0,0,0,0.48);
      overflow: hidden;
    }}
    .object-header {{
      display: grid;
      gap: 12px;
      padding: 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.026);
    }}
    .crumb {{
      font-family: var(--mono);
      overflow-wrap: anywhere;
    }}
    .title-row {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
    }}
    .subtitle {{
      margin-top: 5px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      max-width: 760px;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      white-space: nowrap;
      border: 1px solid rgba(117, 217, 156, 0.34);
      border-radius: 999px;
      padding: 5px 9px;
      color: var(--green);
      background: rgba(117, 217, 156, 0.08);
      font-size: 11px;
      font-weight: 820;
    }}
    .status-dot {{
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: var(--green);
      box-shadow: 0 0 14px rgba(117,217,156,0.62);
    }}
    .fact-strip {{
      display: grid;
      grid-template-columns: 1.1fr 1fr 1fr 1.25fr 0.8fr;
      border-top: 1px solid var(--line-soft);
    }}
    .strip-item {{
      min-width: 0;
      padding: 10px 12px;
      border-right: 1px solid var(--line-soft);
    }}
    .strip-item:last-child {{ border-right: 0; }}
    .label {{
      display: block;
      margin-bottom: 5px;
      text-transform: uppercase;
    }}
    .value {{
      display: block;
      overflow-wrap: anywhere;
      font-size: 13px;
      line-height: 1.3;
      font-weight: 720;
    }}
    .mono {{
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 650;
    }}
    .good {{ color: var(--green); }}
    .review {{ color: var(--amber); }}
    .bad {{ color: var(--red); }}
    .console-body {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 286px;
      gap: 0;
    }}
    .audit-stack {{
      min-width: 0;
      border-right: 1px solid var(--line);
    }}
    .audit-panel {{
      padding: 15px 16px;
      border-bottom: 1px solid var(--line-soft);
    }}
    .audit-panel:last-child {{ border-bottom: 0; }}
    .section-heading {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 10px;
    }}
    .section-heading p {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      text-align: right;
    }}
    .audit-table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      overflow: hidden;
      background: rgba(255,255,255,0.032);
    }}
    .audit-table tr + tr {{ border-top: 1px solid var(--line-soft); }}
    .audit-table th {{
      width: 180px;
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
      text-transform: uppercase;
      background: rgba(255,255,255,0.026);
    }}
    .audit-table td {{
      padding: 10px 12px;
      color: var(--text);
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    .audit-table strong {{
      display: block;
      font-size: 13px;
      line-height: 1.35;
      font-weight: 720;
    }}
    .audit-table td span {{
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    .audit-table .good strong {{ color: var(--green); }}
    .audit-table .review strong {{ color: var(--amber); }}
    .audit-table .bad strong {{ color: var(--red); }}
    .anchor {{
      margin-top: 10px;
      color: rgba(255,255,255,0.7);
      font-size: 12px;
      line-height: 1.55;
    }}
    .utility-rail {{
      min-width: 0;
      padding: 16px;
      background: rgba(0,0,0,0.18);
    }}
    .rail-card {{
      display: grid;
      gap: 10px;
      padding: 12px;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      background: rgba(255,255,255,0.035);
    }}
    .rail-card + .rail-card {{ margin-top: 12px; }}
    .rail-row {{
      display: grid;
      gap: 3px;
      padding-bottom: 9px;
      border-bottom: 1px solid var(--line-soft);
    }}
    .rail-row:last-child {{ padding-bottom: 0; border-bottom: 0; }}
    .rail-value {{
      overflow-wrap: anywhere;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.35;
      color: var(--text);
    }}
    .actions {{
      display: grid;
      gap: 8px;
    }}
    .actions a, .actions button {{
      width: 100%;
      text-align: center;
    }}
    #copy-status {{
      min-height: 18px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    textarea {{
      position: fixed;
      top: 0;
      left: 0;
      width: 1px;
      height: 1px;
      opacity: 0;
      overflow: hidden;
      clip-path: inset(50%);
    }}
    footer {{
      margin-top: 12px;
      color: var(--faint);
      font-size: 11px;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }}
    @media (min-width: 900px) {{
      .utility-rail {{
        position: sticky;
        top: 0;
        align-self: start;
      }}
    }}
    @media (max-width: 860px) {{
      main {{ width: min(100vw - 16px, 1180px); padding-top: 12px; }}
      .topbar {{ align-items: flex-start; flex-direction: column; }}
      .title-row {{ display: grid; }}
      .fact-strip {{ grid-template-columns: 1fr; }}
      .strip-item {{ border-right: 0; border-bottom: 1px solid var(--line-soft); }}
      .strip-item:last-child {{ border-bottom: 0; }}
      .console-body {{ grid-template-columns: 1fr; }}
      .audit-stack {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .section-heading {{ display: grid; gap: 5px; }}
      .section-heading p {{ text-align: left; }}
      .audit-table th {{ width: 126px; }}
      h1 {{ font-size: 18px; }}
    }}
    @media (max-width: 520px) {{
      main {{ width: min(100vw - 12px, 1180px); }}
      .object-header, .audit-panel, .utility-rail {{ padding: 12px; }}
      .audit-table th, .audit-table td {{ display: block; width: 100%; }}
      .audit-table td {{ padding-top: 0; }}
      .audit-table th {{ padding-bottom: 5px; }}
      .audit-table tr + tr {{ border-top: 1px solid var(--line-soft); }}
      a, button {{ min-height: 36px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="topbar">
      <div class="brand">
        <span class="mark" aria-hidden="true"></span>
        <span>
          <strong>InferenceAtlas</strong>
          <span>Portable approval receipt</span>
        </span>
      </div>
      <a href="{_receipt_html_escape(app_path)}">Back to ReviewRun</a>
    </header>
    <section class="receipt-console" aria-label="Approval receipt verification">
      <div class="object-header">
        <div class="crumb">ReviewRun / Receipt / {_receipt_html_escape(receipt_id)}</div>
        <div class="title-row">
          <div>
            <h1>Approval receipt</h1>
            <p class="subtitle">Humans approve scoped movement. IA records the packet-backed receipt. Downstream systems verify it before movement.</p>
          </div>
          <span class="status-pill"><span class="status-dot" aria-hidden="true"></span>{_receipt_html_escape(status_label)}</span>
        </div>
        <div class="fact-strip" aria-label="Receipt summary">
          <div class="strip-item">
            <span class="label">Status</span>
            <strong class="value good">{_receipt_html_escape(status_label)}</strong>
          </div>
          <div class="strip-item">
            <span class="label">Packet</span>
            <strong class="value mono">{_receipt_html_escape(revision_id)}</strong>
          </div>
          <div class="strip-item">
            <span class="label">Portkey</span>
            <strong class="value good">{_receipt_html_escape(portkey_state)}</strong>
          </div>
          <div class="strip-item">
            <span class="label">Scope</span>
            <strong class="value">{_receipt_html_escape(allowed_scope)}</strong>
          </div>
          <div class="strip-item">
            <span class="label">Mutations</span>
            <strong class="value {'bad' if mutation_state != 'none' else 'good'}">{_receipt_html_escape(mutation_state)}</strong>
          </div>
        </div>
      </div>
      <div class="console-body">
        <div class="audit-stack">
          <section class="audit-panel">
            <div class="section-heading">
              <h2>Packet Reference</h2>
              <p>{_receipt_html_escape(repo_name)}</p>
            </div>
            <table class="audit-table">
              <tbody>
                <tr><th>Run</th><td><strong class="mono">{_receipt_html_escape(run_id)}</strong></td></tr>
                <tr><th>Packet</th><td><strong class="mono">{_receipt_html_escape(packet_id)}</strong></td></tr>
                <tr><th>Revision</th><td><strong class="mono">{_receipt_html_escape(revision_id)}</strong></td></tr>
                <tr><th>Content hash</th><td><strong class="mono">{_receipt_html_escape(content_hash)}</strong></td></tr>
                <tr><th>Receipt hash</th><td><strong class="mono">{_receipt_html_escape(receipt_hash)}</strong></td></tr>
              </tbody>
            </table>
          </section>
          <section class="audit-panel">
            <div class="section-heading">
              <h2>Movement Scope</h2>
              <p>Scope travels with the receipt; blocked claims stay blocked.</p>
            </div>
            <table class="audit-table">
              <tbody>
                <tr class="good"><th>Allowed</th><td><strong>{_receipt_html_escape(allowed_scope)}</strong></td></tr>
                <tr class="review"><th>Review required</th><td><strong>{_receipt_html_escape(review_scope)}</strong></td></tr>
                <tr class="bad"><th>Still blocked</th><td><strong>{_receipt_html_escape(blocked_scope)}</strong></td></tr>
                <tr><th>Human scope</th><td><strong>{_receipt_html_escape(approval_state)}</strong></td></tr>
              </tbody>
            </table>
          </section>
          <section class="audit-panel">
            <div class="section-heading">
              <h2>Human Approval Record</h2>
              <p>{_receipt_html_escape(str(approval_summary.get("recorded_count", 0)))} recorded, {_receipt_html_escape(str(approval_summary.get("missing_count", 0)))} missing.</p>
            </div>
            <table class="audit-table">
              <tbody>{approval_rows}</tbody>
            </table>
          </section>
          <section class="audit-panel">
            <div class="section-heading">
              <h2>Portkey Consumption</h2>
              <p>Portkey consumes packet metadata; IA does not push policy.</p>
            </div>
            <table class="audit-table">
              <tbody>
                <tr class="good"><th>State</th><td><strong>{_receipt_html_escape(portkey_state)}</strong></td></tr>
                <tr><th>Event id</th><td><strong class="mono">{_receipt_html_escape(portkey_event_id)}</strong></td></tr>
                <tr class="{'bad' if api_mutation else 'good'}"><th>API mutation</th><td><strong>{_receipt_html_escape(str(api_mutation).lower())}</strong></td></tr>
                <tr class="{'bad' if policy_mutation else 'good'}"><th>Policy mutation</th><td><strong>{_receipt_html_escape(str(policy_mutation).lower())}</strong></td></tr>
              </tbody>
            </table>
          </section>
          <section class="audit-panel">
            <div class="section-heading">
              <h2>Safety Boundary</h2>
              <p>IA never approves access, grants permissions, writes externally, or mutates Portkey policy.</p>
            </div>
            <table class="audit-table">
              <tbody>{safety_rows}</tbody>
            </table>
            <p class="anchor">{_receipt_html_escape(receipt.get("safety_anchor") or "")}</p>
          </section>
        </div>
        <aside class="utility-rail" aria-label="Receipt utilities">
          <div class="rail-card">
            <div class="rail-row">
              <span class="rail-label">Receipt</span>
              <strong class="rail-value">{_receipt_html_escape(receipt_id)}</strong>
            </div>
            <div class="rail-row">
              <span class="rail-label">Packet revision</span>
              <strong class="rail-value">{_receipt_html_escape(revision_id)}</strong>
            </div>
            <div class="rail-row">
              <span class="rail-label">Receipt hash</span>
              <strong class="rail-value">{_receipt_html_escape(receipt_hash)}</strong>
            </div>
          </div>
          <div class="rail-card">
            <span class="rail-label">Carry it</span>
            <div class="actions">
              <button type="button" data-copy-source="copy-receipt">Copy receipt</button>
              <button type="button" data-copy-source="copy-pr">Copy PR snippet</button>
              <a href="{_receipt_html_escape(api_path)}">Open API JSON</a>
            </div>
            <p id="copy-status" role="status" aria-live="polite"></p>
          </div>
        </aside>
      </div>
      </section>
    <footer>Read-only verification page. API path: {_receipt_html_escape(api_path)}. Content hash: {_receipt_html_escape(content_hash)}.</footer>
  </main>
  <textarea id="copy-receipt" readonly>{_receipt_html_escape(copy_receipt)}</textarea>
  <textarea id="copy-pr" readonly>{_receipt_html_escape(copy_pr)}</textarea>
  <script>
    document.querySelectorAll("[data-copy-source]").forEach((button) => {{
      button.addEventListener("click", async () => {{
        const source = document.getElementById(button.dataset.copySource);
        const status = document.getElementById("copy-status");
        const text = source ? source.value : "";
        let copied = false;
        try {{
          if (navigator.clipboard && navigator.clipboard.writeText) {{
            await navigator.clipboard.writeText(text);
            copied = true;
          }}
        }} catch (_) {{
          copied = false;
        }}
        if (!copied && source) {{
          source.focus();
          source.select();
          try {{ copied = document.execCommand("copy"); }} catch (_) {{ copied = false; }}
        }}
        if (status) status.textContent = copied ? "Copied. Scope unchanged." : "Clipboard unavailable.";
      }});
    }});
  </script>
</body>
</html>"""


@app.get("/approval-receipt/{run_id}", response_class=HTMLResponse)
def approval_receipt_index(run_id: str) -> HTMLResponse:
    run, _record = _load_review_run_or_404(run_id)
    try:
        receipt = build_review_run_approval_receipt(run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(_render_review_run_approval_receipt_html(receipt, run))


@app.get("/proofgraph", response_class=HTMLResponse)
def proofgraph_index(
    fixture: str = Query(DEFAULT_PROOF_GRAPH_SCENARIO, description="Public access scenario to visualize."),
    review_run_id: Optional[str] = Query(None, description="Local ReviewRun id to visualize."),
) -> HTMLResponse:
    fixture_id = fixture if isinstance(fixture, str) else DEFAULT_PROOF_GRAPH_SCENARIO
    run_id = review_run_id if isinstance(review_run_id, str) and review_run_id.strip() else None
    if run_id:
        run, _record = _load_review_run_or_404(run_id)
        return HTMLResponse(render_review_run_proof_graph_html(build_review_run_proofgraph(run)))
    try:
        html_page = build_proof_graph_visual(fixture_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HTMLResponse(html_page)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
