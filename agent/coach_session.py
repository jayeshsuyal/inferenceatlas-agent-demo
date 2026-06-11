"""OpenClaw-style durable coach session: stage checkpoints + turn transcript per ReviewRun."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .scenarios import ROOT_DIR

COACH_SESSION_SCHEMA_VERSION = "coach_session.v0"
DEFAULT_COACH_SESSION_DIR = ROOT_DIR / "state" / "coach_sessions"
MAX_CHECKPOINTS = 24
MAX_TURNS = 32


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _session_path(run_id: str, store_dir: Path) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(run_id))
    return store_dir / f"{safe}.json"


def _empty_session(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": COACH_SESSION_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "checkpoints": [],
        "turns": [],
    }


def load_coach_session(run_id: str, *, store_dir: Optional[Path] = None) -> dict[str, Any]:
    base = store_dir or DEFAULT_COACH_SESSION_DIR
    path = _session_path(run_id, base)
    if not path.is_file():
        return _empty_session(run_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return _empty_session(run_id)
    data.setdefault("checkpoints", [])
    data.setdefault("turns", [])
    return data


def save_coach_session(session: dict[str, Any], *, store_dir: Optional[Path] = None) -> Path:
    base = store_dir or DEFAULT_COACH_SESSION_DIR
    base.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = _utc_now()
    path = _session_path(str(session["run_id"]), base)
    path.write_text(json.dumps(session, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def record_coach_checkpoint(
    run_id: str,
    *,
    stage: str,
    revision_id: str = "",
    verdict: str = "",
    portkey_state: str = "",
    trigger: str = "",
    summary: str = "",
    store_dir: Optional[Path] = None,
) -> dict[str, Any]:
    session = load_coach_session(run_id, store_dir=store_dir)
    checkpoint = {
        "at": _utc_now(),
        "stage": stage,
        "revision_id": revision_id,
        "verdict": verdict,
        "portkey_state": portkey_state,
        "trigger": trigger or stage,
        "summary": " ".join(str(summary or "").split())[:400],
    }
    checkpoints = list(session.get("checkpoints") or [])
    if checkpoints and checkpoints[-1].get("stage") == stage and checkpoints[-1].get("revision_id") == revision_id:
        checkpoints[-1] = checkpoint
    else:
        checkpoints.append(checkpoint)
    session["checkpoints"] = checkpoints[-MAX_CHECKPOINTS:]
    save_coach_session(session, store_dir=store_dir)
    return checkpoint


def append_coach_turn(
    run_id: str,
    *,
    prompt: str,
    prompt_kind: str = "",
    stage: str = "",
    store_dir: Optional[Path] = None,
) -> None:
    session = load_coach_session(run_id, store_dir=store_dir)
    turns = list(session.get("turns") or [])
    turns.append(
        {
            "at": _utc_now(),
            "prompt": " ".join(str(prompt or "").split())[:500],
            "prompt_kind": prompt_kind,
            "stage": stage,
        }
    )
    session["turns"] = turns[-MAX_TURNS:]
    save_coach_session(session, store_dir=store_dir)


def format_coach_session_context(run_id: str, *, store_dir: Optional[Path] = None) -> str:
    session = load_coach_session(run_id, store_dir=store_dir)
    lines = ["### Coach session (checkpoints + turns — framing only)"]
    for item in (session.get("checkpoints") or [])[-6:]:
        lines.append(
            f"- [{item.get('at', '?')}] stage={item.get('stage')} "
            f"rev={item.get('revision_id') or 'n/a'} "
            f"verdict={item.get('verdict') or 'n/a'} "
            f"portkey={item.get('portkey_state') or 'n/a'} "
            f"trigger={item.get('trigger') or 'n/a'}: {item.get('summary') or ''}"
        )
    for item in (session.get("turns") or [])[-4:]:
        lines.append(
            f"- turn [{item.get('at', '?')}] stage={item.get('stage')} "
            f"kind={item.get('prompt_kind')}: {item.get('prompt')}"
        )
    if len(lines) == 1:
        lines.append("- (no prior coach checkpoints for this ReviewRun)")
    return "\n".join(lines)


def coach_session_summary(answer: Mapping[str, Any], *, trigger: str = "") -> str:
    sections = answer.get("sections") or {}
    return (
        f"{sections.get('current_read', '')} "
        f"Next: {sections.get('next_human_action', '')} "
        f"Trigger: {trigger or answer.get('prompt_kind', '')}"
    ).strip()[:400]
