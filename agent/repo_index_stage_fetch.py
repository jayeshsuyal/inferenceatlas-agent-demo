"""Stage-triggered targeted repo path fetches."""

from __future__ import annotations

import threading
from typing import Any, Optional

from .connector_runtime import _raw_connection, load_session, save_session
from .github_repo import _fetch_file_content, _parse_full_name
from .repo_index_scoring import path_matches_patterns, patterns_for_stage, pick_scored_paths
from .repo_index_store import load_manifest, save_chunk, save_manifest, save_report, build_index_report, list_chunks
from .repo_index_search import search_repo_paths

_fetch_lock = threading.Lock()


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_paths_for_run(
    session_id: str,
    run_id: str,
    full_name: str,
    patterns: list[str],
    *,
    tier: str = "tier2",
    limit: int = 12,
) -> dict[str, Any]:
    """Fetch and store paths matching patterns (manifest grep + optional enterprise search)."""
    manifest = load_manifest(full_name) or {"paths": [], "full_name": full_name}
    raw_paths = [str(row.get("path") or "") for row in manifest.get("paths") or []]
    matched = [path for path in raw_paths if path_matches_patterns(path, patterns)]
    if len(matched) < limit:
        search = search_repo_paths(session_id, full_name, patterns, limit=limit)
        for row in search.get("paths") or []:
            path = str(row.get("path") or "")
            if path and path not in matched:
                matched.append(path)
    ranked = pick_scored_paths(matched, limit=limit)
    conn = _raw_connection(session_id, "github")
    fetched: list[str] = []
    if conn.get("mode") in ("demo_session", "demo_oauth") or not conn.get("access_token"):
        for row in ranked:
            chunk = save_chunk(full_name, row["path"], f"(demo — stage fetch placeholder for {row['path']})", tier=tier)
            fetched.append(row["path"])
        _record_stage_fetch(session_id, run_id, full_name, patterns, fetched, tier)
        return {"ok": True, "fetched": fetched, "patterns": patterns, "tier": tier}

    owner, repo = _parse_full_name(full_name)
    token = conn["access_token"]
    for row in ranked:
        body = _fetch_file_content(token, owner, repo, row["path"])
        if body.strip() and not body.startswith("(file too large"):
            save_chunk(full_name, row["path"], body[:6000], tier=tier)
            fetched.append(row["path"])
    _record_stage_fetch(session_id, run_id, full_name, patterns, fetched, tier)
    return {"ok": True, "fetched": fetched, "patterns": patterns, "tier": tier}


def _record_stage_fetch(
    session_id: str,
    run_id: str,
    full_name: str,
    patterns: list[str],
    fetched: list[str],
    tier: str,
) -> None:
    manifest = load_manifest(full_name) or {}
    stage_fetches = list(manifest.get("stage_fetches") or [])
    stage_fetches.append(
        {
            "at": _utc_now(),
            "run_id": run_id,
            "patterns": patterns,
            "fetched": fetched,
            "tier": tier,
        }
    )
    manifest["stage_fetches"] = stage_fetches[-20:]
    for row in manifest.get("paths") or []:
        if row.get("path") in fetched:
            row["fetched"] = True
    save_manifest(full_name, manifest)
    report = build_index_report(full_name, manifest, list_chunks(full_name))
    save_report(full_name, report)

    data = load_session(session_id)
    contexts = data.setdefault("review_contexts", {})
    ctx = dict(contexts.get(run_id) or {})
    ctx["index_report_updated_at"] = _utc_now()
    contexts[run_id] = ctx
    data["review_contexts"] = contexts
    save_session(session_id, data)


def maybe_enqueue_stage_index_fetch(
    session_id: str,
    run_id: str,
    *,
    trigger: str,
    stage: str,
    repo_full_name: str,
) -> None:
    patterns = patterns_for_stage(trigger, stage)
    if not patterns or not repo_full_name:
        return

    def _worker() -> None:
        with _fetch_lock:
            fetch_paths_for_run(session_id, run_id, repo_full_name, patterns)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
