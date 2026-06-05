"""FastAPI server for the InferenceAtlas Intelligence Agent."""

import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
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
from agent.decision_brief import build_agent_access_decision_brief
from agent.mind import init_mind, load_mind, save_mind, step
from agent.mind.project import MIND_RUNTIME_DIR, project_mind
from agent.mind.store import load_all_minds
from agent.packet import build_support_triage_decision_packet
from agent.renderers import render_decision_brief_markdown, render_packet_markdown
from agent.scenarios import SCENARIOS
from agent.tools import compare_providers, get_catalog_summary, tavily_search
from agent.trial import DEFAULT_TRIAL_REQUEST
from agent.trial_evidence_replay import (
    ADAPTER_PROVIDERS,
    DEFAULT_REHEARSAL_EVIDENCE_DIR,
    build_trial_evidence_replay,
    render_trial_evidence_replay_markdown,
)
from agent.ui_skills import (
    build_ui_skills_payload,
    compose_message_with_skills,
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

app = FastAPI(title="InferenceAtlas Agent", version="1.0.0")

_sessions: Dict[str, object] = {}
_lock = threading.Lock()


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


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    output_files: List[dict] = Field(default_factory=list)
    skills_used: List[dict] = Field(default_factory=list)


def _file_ref(file_id: str, label: str) -> dict:
    return {"file_id": file_id, "label": label, "url": f"/api/files/{file_id}"}


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


class CustomEvidenceRehearsalRequest(BaseModel):
    attachment_ids: List[str] = Field(default_factory=list, max_length=8)
    storage_scope: str = Field(default="review_anonymous", max_length=160)


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
        "skills_count": len(build_ui_skills_payload().get("skills", [])),
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
    }


@app.get("/api/skills")
def list_ui_skills() -> dict:
    """InferenceAtlas harness skills for the web UI (+ menu and / slash picker)."""
    return build_ui_skills_payload()


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
    message = body.message.strip()
    skill_ids = [s for s in body.skill_ids if s]
    if not message and not skill_ids:
        raise HTTPException(
            status_code=400,
            detail="Add a question or attach at least one skill",
        )

    deterministic_reply = (
        None if skill_ids or body.attachment_ids else _deterministic_example_reply(message)
    )
    if deterministic_reply is None:
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
        session_id, agent = _get_or_create_session(body.session_id)
    else:
        session_id = body.session_id or str(uuid.uuid4())
    scope = f"chat_{session_id}"
    llm_message = message
    skills_used: List[dict] = []
    if skill_ids:
        position = body.skill_context_position if body.skill_context_position in (
            "prepend",
            "append",
        ) else "prepend"
        llm_message, skills_used = compose_message_with_skills(
            message, skill_ids, position=position
        )
    full_message, attach_warnings = _build_user_message(
        llm_message, scope, body.attachment_ids
    )

    user_display = message
    if not user_display and skills_used:
        user_display = f"[Skills: {', '.join(s['slash_trigger'] for s in skills_used)}]"

    if deterministic_reply is not None:
        reply = deterministic_reply
    else:
        try:
            if skills_used:
                reply = agent.chat_with_skills(user_display, full_message)
            else:
                reply = agent.chat(full_message)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    if skills_used:
        labels = ", ".join(s["slash_trigger"] for s in skills_used)
        reply = (
            f"**Harness review** ({labels}) — answered from deterministic artifacts, "
            f"not live tool calls.\n\n{reply}"
        )

    if attach_warnings:
        reply = reply + "\n\n" + "\n".join(attach_warnings)

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
                {"message": message, "reply": reply, "attachments": body.attachment_ids},
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
            {
                "file_id": "",
                "label": f"Could not save output: {exc}",
                "url": "",
            }
        ]

    try:
        mind_observe(
            MindObserveRequest(scenario="support_triage_agent", text=message),
        )
    except Exception:
        pass

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        output_files=output_files,
        skills_used=skills_used,
    )


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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
