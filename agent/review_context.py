"""OpenClaw-style centralized ReviewRun session + flow context (durable, per session)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .coach_session import format_coach_session_context, load_coach_session
from .connector_runtime import load_session, save_session

FLOW_STAGE_ORDER = (
    "repo_not_connected",
    "repo_connected",
    "repo_selected",
    "repo_indexed",
    "request_entered",
    "packet_generating",
    "packet_generated",
    "proof_attached",
    "packet_regenerated",
    "ready_to_export",
    "portkey_tested",
)

MAX_FLOW_EVENTS = 40


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stage_rank(stage: str) -> int:
    try:
        return FLOW_STAGE_ORDER.index(stage)
    except ValueError:
        return -1


def validate_flow_transition(previous_stage: str, next_stage: str) -> dict[str, Any]:
    """Lightweight flow validation — warns on large backward jumps, not hard blocks."""
    prev_rank = _stage_rank(previous_stage)
    next_rank = _stage_rank(next_stage)
    if prev_rank < 0 or next_rank < 0:
        return {"ok": True, "warning": "", "skipped": True}
    if next_rank < prev_rank - 1:
        return {
            "ok": True,
            "warning": f"Flow moved backward from {previous_stage} to {next_stage}.",
            "skipped": False,
        }
    if next_rank > prev_rank + 2:
        return {
            "ok": True,
            "warning": f"Flow jumped from {previous_stage} to {next_stage} without intermediate steps.",
            "skipped": False,
        }
    return {"ok": True, "warning": "", "skipped": False}


def record_flow_event(
    session_id: str,
    run_id: str,
    *,
    stage: str,
    previous_stage: str = "",
    trigger: str = "",
    summary: str = "",
    repo_full_name: str = "",
) -> dict[str, Any]:
    validation = validate_flow_transition(previous_stage, stage) if previous_stage else {"ok": True, "warning": ""}
    data = load_session(session_id)
    contexts = data.setdefault("review_contexts", {})
    ctx = dict(contexts.get(run_id) or {})
    events = list(ctx.get("flow_events") or [])
    event = {
        "at": _utc_now(),
        "stage": stage,
        "previous_stage": previous_stage,
        "trigger": trigger or stage,
        "summary": " ".join(str(summary or "").split())[:400],
        "validation_warning": validation.get("warning") or "",
    }
    events.append(event)
    ctx.update(
        {
            "run_id": run_id,
            "stage": stage,
            "previous_stage": previous_stage,
            "repo_full_name": repo_full_name or ctx.get("repo_full_name") or "",
            "flow_events": events[-MAX_FLOW_EVENTS:],
            "last_validation": validation,
            "updated_at": _utc_now(),
        }
    )
    contexts[run_id] = ctx
    data["review_contexts"] = contexts
    save_session(session_id, data)
    return {"event": event, "validation": validation}


def get_review_context_bundle(
    session_id: str,
    run_id: str,
    *,
    coach_store_dir: Optional[Any] = None,
) -> dict[str, Any]:
    data = load_session(session_id)
    ctx = (data.get("review_contexts") or {}).get(run_id) or {}
    coach_session = load_coach_session(run_id, store_dir=coach_store_dir)
    coach_text = format_coach_session_context(run_id, store_dir=coach_store_dir)
    repo_name = str(ctx.get("repo_full_name") or "")
    attached = (data.get("github_attached") or {}).get(repo_name) or {}
    return {
        "ok": True,
        "run_id": run_id,
        "session_id": session_id,
        "stage": ctx.get("stage") or "",
        "repo_full_name": repo_name,
        "index_summary": ctx.get("index_summary") or attached.get("index_summary") or "",
        "index_complete": bool(ctx.get("index_complete") or attached.get("full_index_complete")),
        "index_job_id": ctx.get("index_job_id") or "",
        "flow_events": ctx.get("flow_events") or [],
        "last_validation": ctx.get("last_validation") or {},
        "coach_session": coach_session,
        "coach_context_markdown": coach_text,
    }


def format_context_for_coach(bundle: Mapping[str, Any]) -> str:
    lines = [
        "### ReviewRun session context (OpenClaw-style — framing only)",
        f"- Active stage: {bundle.get('stage') or 'unknown'}",
        f"- Repo: {bundle.get('repo_full_name') or 'none'}",
        f"- Index complete: {bundle.get('index_complete')}",
    ]
    validation = bundle.get("last_validation") or {}
    if validation.get("warning"):
        lines.append(f"- Flow note: {validation['warning']}")
    for event in (bundle.get("flow_events") or [])[-5:]:
        warn = event.get("validation_warning")
        suffix = f" ⚠ {warn}" if warn else ""
        lines.append(
            f"- [{event.get('at', '?')}] {event.get('previous_stage') or 'start'} → "
            f"{event.get('stage')}: {event.get('summary') or event.get('trigger')}{suffix}"
        )
    summary = str(bundle.get("index_summary") or "").strip()
    if summary:
        lines.extend(["", "### Repository index summary", summary[:2500]])
    lines.extend(["", bundle.get("coach_context_markdown") or ""])
    return "\n".join(lines).strip()
