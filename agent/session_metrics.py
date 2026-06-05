"""Per-session usage counters for paid APIs (.env services)."""

from __future__ import annotations

import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import COMPOSIO_DRY_RUN, LLM_MODEL, LLM_PROVIDER

ROOT_DIR = Path(__file__).resolve().parent.parent
METRICS_DIR = ROOT_DIR / "state" / "web_io" / "session_metrics"
_lock = threading.Lock()
_current_session: ContextVar[Optional[str]] = ContextVar("metrics_session_id", default=None)

MAX_RECENT_EVENTS = 80


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_metrics_session(session_id: str) -> None:
    _current_session.set(session_id)


def clear_metrics_session() -> None:
    _current_session.set(None)


def _metrics_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:80]
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    return METRICS_DIR / f"{safe}.json"


def _empty_metrics(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "demo_llm": {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "tavily": {"calls": 0, "configured": True},
        "composio": {"calls": 0, "dry_run": COMPOSIO_DRY_RUN},
        "v1_http": {"copilot_calls": 0, "plan_llm_calls": 0, "health_calls": 0},
        "github_api": {"index_calls": 0},
        "google_drive_api": {"index_calls": 0},
        "recent_events": [],
    }


def _load(session_id: str) -> dict[str, Any]:
    path = _metrics_path(session_id)
    if not path.exists():
        return _empty_metrics(session_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return _empty_metrics(session_id)


def _save(session_id: str, data: dict[str, Any]) -> None:
    data["updated_at"] = _now_iso()
    _metrics_path(session_id).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _append_event(data: dict[str, Any], event: dict[str, Any]) -> None:
    events: List[dict[str, Any]] = data.setdefault("recent_events", [])
    events.append({"at": _now_iso(), **event})
    if len(events) > MAX_RECENT_EVENTS:
        data["recent_events"] = events[-MAX_RECENT_EVENTS:]


def _mutate(session_id: str, fn) -> None:
    with _lock:
        data = _load(session_id)
        fn(data)
        _save(session_id, data)


def _active_session() -> Optional[str]:
    return _current_session.get()


def record_event(service: str, **fields: Any) -> None:
    sid = _active_session()
    if not sid:
        return

    def _apply(data: dict[str, Any]) -> None:
        _append_event(data, {"service": service, **fields})

    _mutate(sid, _apply)


def record_demo_llm_usage(
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    label: str = "chat",
) -> None:
    sid = _active_session()
    if not sid:
        return

    def _apply(data: dict[str, Any]) -> None:
        bucket = data.setdefault("demo_llm", {})
        bucket["calls"] = int(bucket.get("calls", 0)) + 1
        bucket["prompt_tokens"] = int(bucket.get("prompt_tokens", 0)) + prompt_tokens
        bucket["completion_tokens"] = int(bucket.get("completion_tokens", 0)) + completion_tokens
        if total_tokens:
            bucket["total_tokens"] = int(bucket.get("total_tokens", 0)) + total_tokens
        else:
            bucket["total_tokens"] = int(bucket.get("total_tokens", 0)) + prompt_tokens + completion_tokens
        _append_event(
            data,
            {
                "service": "demo_llm",
                "label": label,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        )

    _mutate(sid, _apply)


def record_tool_call(tool_name: str, *, detail: str = "") -> None:
    sid = _active_session()
    if not sid:
        return
    key = "tavily" if tool_name == "tavily_search" else "composio" if tool_name.startswith("composio") else None
    if not key:
        record_event("tool", tool=tool_name, detail=detail)
        return

    def _apply(data: dict[str, Any]) -> None:
        bucket = data.setdefault(key, {})
        bucket["calls"] = int(bucket.get("calls", 0)) + 1
        _append_event(data, {"service": key, "tool": tool_name, "detail": detail})

    _mutate(sid, _apply)


def record_v1_http(endpoint: str) -> None:
    sid = _active_session()
    if not sid:
        return

    def _apply(data: dict[str, Any]) -> None:
        bucket = data.setdefault("v1_http", {})
        if endpoint == "copilot":
            bucket["copilot_calls"] = int(bucket.get("copilot_calls", 0)) + 1
        elif endpoint == "plan_llm":
            bucket["plan_llm_calls"] = int(bucket.get("plan_llm_calls", 0)) + 1
        else:
            bucket["health_calls"] = int(bucket.get("health_calls", 0)) + 1
        _append_event(data, {"service": "v1_http", "endpoint": endpoint})

    _mutate(sid, _apply)


def record_connector_index(connector: str, session_id: Optional[str] = None) -> None:
    sid = session_id or _active_session()
    if not sid:
        return
    key = "github_api" if connector == "github" else "google_drive_api"
    if key not in ("github_api", "google_drive_api"):
        return

    def _apply(data: dict[str, Any]) -> None:
        bucket = data.setdefault(key, {})
        bucket["index_calls"] = int(bucket.get("index_calls", 0)) + 1
        _append_event(data, {"service": key, "action": "index"})

    _mutate(sid, _apply)


def record_copilot_direct() -> None:
    record_event("v1_copilot", path="direct_reply", demo_llm_skipped=True)


def get_session_metrics(session_id: str) -> dict[str, Any]:
    with _lock:
        data = _load(session_id)
    billable = {
        "demo_llm": data.get("demo_llm", {}),
        "tavily": data.get("tavily", {}),
        "composio": data.get("composio", {}),
        "v1_http": data.get("v1_http", {}),
        "github_api": data.get("github_api", {}),
        "google_drive_api": data.get("google_drive_api", {}),
    }
    return {
        "session_id": session_id,
        "updated_at": data.get("updated_at"),
        "started_at": data.get("started_at"),
        "llm_provider": data.get("llm_provider", LLM_PROVIDER),
        "llm_model": data.get("llm_model", LLM_MODEL),
        "billable": billable,
        "recent_events": data.get("recent_events", []),
        "notes": [
            "demo_llm: Nebius or OpenAI per demo .env (access-review / tool paths only when copilot skips).",
            "v1_http: HTTP calls to InferenceAtlas-v1; v1's own OPENAI/ANTHROPIC usage bills on the v1 server.",
            "composio: dry_run=1 means no live Composio execution charges.",
        ],
    }
