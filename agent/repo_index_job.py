"""Background tier-1 repo indexing jobs (quick attach first, scored deep index async)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .connector_runtime import _raw_connection, load_session, save_session
from .github_repo import (
    _attached_repos,
    _digest_index_meta,
    _fetch_file_content,
    _fetch_tree_paths,
    _github_get,
    _parse_full_name,
)
from .repo_index_scoring import pick_scored_paths
from .repo_index_store import (
    build_digest_from_store,
    build_index_report,
    list_chunks,
    load_manifest,
    save_chunk,
    save_manifest,
    save_report,
)
from .scenarios import ROOT_DIR

JOB_SCHEMA_VERSION = "repo_index_job.v0"
JOB_STORE_DIR = ROOT_DIR / "state" / "repo_index_jobs"
MAX_BACKGROUND_FILES = 120
MAX_BACKGROUND_DIGEST_CHARS = 400_000
CHUNK_FILE_CHARS = 6_000

_jobs_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _job_path(job_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in job_id)
    return JOB_STORE_DIR / f"{safe}.json"


def _save_job(job: dict[str, Any]) -> None:
    JOB_STORE_DIR.mkdir(parents=True, exist_ok=True)
    job["updated_at"] = _utc_now()
    _job_path(str(job["job_id"])).write_text(
        json.dumps(job, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_job(job_id: str) -> Optional[dict[str, Any]]:
    with _jobs_lock:
        if job_id in _jobs:
            return dict(_jobs[job_id])
    path = _job_path(job_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    with _jobs_lock:
        _jobs[job_id] = data
    return data


def get_index_job(job_id: str) -> Optional[dict[str, Any]]:
    job = _load_job(job_id)
    if not job:
        return None
    return {
        "ok": True,
        "job": {
            "job_id": job["job_id"],
            "session_id": job.get("session_id", ""),
            "run_id": job.get("run_id", ""),
            "full_name": job.get("full_name", ""),
            "status": job.get("status", "unknown"),
            "phase": job.get("phase", ""),
            "progress_pct": job.get("progress_pct", 0),
            "files_indexed": job.get("files_indexed", 0),
            "files_total": job.get("files_total", 0),
            "digest_chars": job.get("digest_chars", 0),
            "summary": job.get("summary", ""),
            "report": job.get("report") or {},
            "error": job.get("error", ""),
            "started_at": job.get("started_at", ""),
            "completed_at": job.get("completed_at", ""),
        },
    }


def _already_indexed_paths(full_name: str, base_digest: str) -> set[str]:
    chunks = {str(row.get("path") or "") for row in list_chunks(full_name)}
    legacy = {ln.split("\n### ", 1)[-1].split("\n", 1)[0] for ln in base_digest.split("\n### ")[1:]}
    return {path for path in chunks | legacy if path}


def _pick_background_files(paths: list[str], *, already_indexed: set[str]) -> list[str]:
    ranked = pick_scored_paths(paths, limit=MAX_BACKGROUND_FILES, exclude=already_indexed)
    return [row["path"] for row in ranked]


def _build_repo_summary(full_name: str, report: dict[str, Any]) -> str:
    return str(report.get("narrative") or f"Indexed {full_name}.")


def _run_background_index(job_id: str) -> None:
    job = _load_job(job_id)
    if not job:
        return
    session_id = str(job.get("session_id") or "")
    full_name = str(job.get("full_name") or "")
    run_id = str(job.get("run_id") or "")

    def _update(**fields: Any) -> None:
        with _jobs_lock:
            current = _jobs.get(job_id) or job
            current.update(fields)
            _jobs[job_id] = current
            _save_job(current)

    try:
        _update(status="running", phase="scoping", progress_pct=5)
        conn = _raw_connection(session_id, "github")
        manifest = load_manifest(full_name) or {}
        if conn.get("mode") in ("demo_session", "demo_oauth") or not conn.get("access_token"):
            entry = _attached_repos(session_id).get(full_name, {})
            digest = str(entry.get("digest") or build_digest_from_store(full_name, max_chars=MAX_BACKGROUND_DIGEST_CHARS))
            meta = _digest_index_meta(digest, full_name)
            report = build_index_report(full_name, manifest or {"paths": []}, list_chunks(full_name), job_meta=_load_job(job_id))
            save_report(full_name, report)
            summary = _build_repo_summary(full_name, report)
            _update(
                status="completed",
                phase="done",
                progress_pct=100,
                digest_chars=len(digest),
                summary=summary,
                report=report,
                completed_at=_utc_now(),
            )
            _attach_summary_to_session(session_id, full_name, run_id, summary, digest, meta, report)
            return

        owner, repo = _parse_full_name(full_name)
        token = conn["access_token"]
        meta_repo = _github_get(token, f"/repos/{owner}/{repo}")
        branch = meta_repo.get("default_branch") or "main"
        paths, truncated = _fetch_tree_paths(token, owner, repo, branch)
        entry = _attached_repos(session_id).get(full_name, {})
        base_digest = str(entry.get("digest") or build_digest_from_store(full_name))
        already = _already_indexed_paths(full_name, base_digest)

        targets = _pick_background_files(paths, already_indexed=already)
        files_total = len(targets)
        _update(phase="mining", files_total=files_total, progress_pct=12)

        total_chars = len(base_digest)
        indexed = 0
        for idx, path in enumerate(targets):
            body = _fetch_file_content(token, owner, repo, path)
            if not body.strip() or body.startswith("(file too large"):
                continue
            save_chunk(full_name, path, body[:CHUNK_FILE_CHARS], tier="tier1")
            block = f"\n### {path}\n```\n{body[:CHUNK_FILE_CHARS]}\n```\n"
            if total_chars + len(block) > MAX_BACKGROUND_DIGEST_CHARS:
                break
            total_chars += len(block)
            indexed += 1
            pct = 12 + int((idx + 1) / max(files_total, 1) * 78)
            _update(
                phase="indexing",
                files_indexed=indexed,
                progress_pct=min(pct, 90),
                digest_chars=total_chars,
            )

        _update(phase="summarizing", progress_pct=95)
        manifest = load_manifest(full_name) or {
            "full_name": full_name,
            "default_branch": branch,
            "truncated_tree": truncated,
            "total_paths": len(paths),
            "paths": [],
        }
        manifest.update(
            {
                "index_complete": True,
                "digest_chars": total_chars,
                "truncated_tree": truncated,
                "total_paths": len(paths),
            }
        )
        for row in manifest.get("paths") or []:
            if row.get("path") in already or any(
                str(chunk.get("path")) == row.get("path") for chunk in list_chunks(full_name)
            ):
                row["fetched"] = True
        save_manifest(full_name, manifest)

        full_digest = build_digest_from_store(full_name, max_chars=MAX_BACKGROUND_DIGEST_CHARS)
        meta = _digest_index_meta(full_digest, full_name)
        report = build_index_report(
            full_name,
            manifest,
            list_chunks(full_name),
            job_meta={**(_load_job(job_id) or {}), "status": "completed", "files_indexed": indexed},
        )
        save_report(full_name, report)
        summary = _build_repo_summary(full_name, report)
        _attach_summary_to_session(session_id, full_name, run_id, summary, full_digest, meta, report)
        _update(
            status="completed",
            phase="done",
            progress_pct=100,
            files_indexed=indexed,
            digest_chars=len(full_digest),
            summary=summary,
            report=report,
            completed_at=_utc_now(),
        )
    except Exception as exc:
        _update(status="failed", phase="error", error=str(exc)[:400], completed_at=_utc_now())


def _attach_summary_to_session(
    session_id: str,
    full_name: str,
    run_id: str,
    summary: str,
    digest: str,
    meta: dict[str, Any],
    report: Optional[dict[str, Any]] = None,
) -> None:
    data = load_session(session_id)
    attached = data.setdefault("github_attached", {})
    entry = dict(attached.get(full_name) or {})
    entry.update(
        {
            "full_name": full_name,
            "digest": digest,
            "digest_chars": len(digest),
            "full_index_complete": True,
            "index_summary": summary,
            "index_report": report or {},
            **meta,
        }
    )
    attached[full_name] = entry
    data["github_attached"] = attached
    if run_id:
        contexts = data.setdefault("review_contexts", {})
        ctx = dict(contexts.get(run_id) or {})
        ctx.update(
            {
                "run_id": run_id,
                "repo_full_name": full_name,
                "index_summary": summary,
                "index_report": report or {},
                "index_complete": True,
                "updated_at": _utc_now(),
            }
        )
        contexts[run_id] = ctx
    save_session(session_id, data)


def start_background_full_index(
    session_id: str,
    full_name: str,
    *,
    run_id: str = "",
) -> dict[str, Any]:
    """Kick off async tier-1 scored indexing after quick attach returned."""
    conn = _raw_connection(session_id, "github")
    if conn.get("status") != "connected":
        return {"ok": False, "message": "GitHub not connected."}

    job_id = f"idx-{uuid.uuid4().hex[:12]}"
    job = {
        "schema_version": JOB_SCHEMA_VERSION,
        "job_id": job_id,
        "session_id": session_id,
        "run_id": run_id,
        "full_name": full_name,
        "status": "queued",
        "phase": "queued",
        "progress_pct": 0,
        "files_indexed": 0,
        "files_total": 0,
        "digest_chars": 0,
        "summary": "",
        "report": {},
        "error": "",
        "started_at": _utc_now(),
        "completed_at": "",
        "updated_at": _utc_now(),
    }
    with _jobs_lock:
        _jobs[job_id] = job
    _save_job(job)

    thread = threading.Thread(target=_run_background_index, args=(job_id,), daemon=True)
    thread.start()
    return {"ok": True, "job_id": job_id, "status": "queued"}


def get_session_review_context(session_id: str, run_id: str) -> dict[str, Any]:
    data = load_session(session_id)
    contexts = data.get("review_contexts") or {}
    ctx = contexts.get(run_id) or {}
    repo_name = str(ctx.get("repo_full_name") or "")
    index_job_id = str(ctx.get("index_job_id") or "")
    job = _load_job(index_job_id) if index_job_id else None
    report = ctx.get("index_report") or (job or {}).get("report") or {}
    return {
        "ok": True,
        "run_id": run_id,
        "repo_full_name": repo_name,
        "index_summary": ctx.get("index_summary") or (job or {}).get("summary", ""),
        "index_report": report,
        "index_complete": bool(ctx.get("index_complete")),
        "index_job": (job or {}).get("status"),
        "context": ctx,
    }


def bind_index_job_to_context(session_id: str, run_id: str, job_id: str, repo_full_name: str) -> None:
    data = load_session(session_id)
    contexts = data.setdefault("review_contexts", {})
    ctx = dict(contexts.get(run_id) or {})
    ctx.update(
        {
            "run_id": run_id,
            "repo_full_name": repo_full_name,
            "index_job_id": job_id,
            "updated_at": _utc_now(),
        }
    )
    contexts[run_id] = ctx
    data["review_contexts"] = contexts
    save_session(session_id, data)
