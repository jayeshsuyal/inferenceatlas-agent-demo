"""FastAPI server for the InferenceAtlas Intelligence Agent."""

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
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
from agent.decision_brief import build_agent_access_decision_brief
from agent.mind import init_mind, load_mind, save_mind, step
from agent.mind.project import MIND_RUNTIME_DIR, project_mind
from agent.mind.store import load_all_minds
from agent.renderers import render_decision_brief_markdown, render_packet_markdown
from agent.scenarios import SCENARIOS
from agent.tools import get_catalog_summary
from agent.chat_orchestrator import format_reply_with_manifest, orchestrate_chat
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
from agent.trial import DEFAULT_TRIAL_REQUEST
from agent.trial_evidence_replay import (
    ADAPTER_PROVIDERS,
    DEFAULT_REHEARSAL_EVIDENCE_DIR,
    build_trial_evidence_replay,
    render_trial_evidence_replay_markdown,
)
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
    github_repos: List[str] = Field(default_factory=list)
    drive_file_ids: List[str] = Field(default_factory=list)


class GithubAttachRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    full_name: str = Field(..., min_length=3, max_length=200)


class DriveAttachRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=120)
    file_id: str = Field(..., min_length=2, max_length=120)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
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
        oauth_close_html("github", bool(result.get("ok")), result.get("message", ""))
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
        oauth_close_html("google_drive", bool(result.get("ok")), result.get("message", ""))
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
    _chat_validate()
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
    )

    plain = (
        not orch.skills_used
        and not orch.github_used
        and not orch.drive_used
        and not orch.file_names
        and not orch.engine_source
    )
    try:
        if plain:
            reply = agent.chat(orch.user_message or message)
        else:
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

    return ChatResponse(
        reply=reply,
        session_id=session_id,
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
            _chat_validate()
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
            )
            if plain:
                reply = agent.chat(orch.user_message or message)
            else:
                reply = agent.chat_orchestrated(
                    orch.user_display,
                    orch.llm_message,
                    system_prompt=orch.system_prompt,
                    use_tools=orch.use_tools,
                )
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
                        {"message": message, "reply": reply, "manifest": orch.context_manifest},
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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
