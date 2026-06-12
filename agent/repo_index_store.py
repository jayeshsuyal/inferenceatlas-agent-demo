"""Structured repo index storage: manifest + file chunks + presentation report."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional

from .repo_index_scoring import categorize_path, path_extension, score_path
from .scenarios import ROOT_DIR

INDEX_SCHEMA_VERSION = "repo_index_store.v1"
INDEX_STORE_DIR = ROOT_DIR / "state" / "repo_indexes"
PREINDEX_DIR = ROOT_DIR / "examples" / "repo_indexes"


def _safe_repo_key(full_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "__", full_name.strip().lower())


def _repo_dir(full_name: str, *, preindex: bool = False) -> Path:
    base = PREINDEX_DIR if preindex else INDEX_STORE_DIR
    return base / _safe_repo_key(full_name)


def _chunk_path(repo_dir: Path, path: str) -> Path:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
    return repo_dir / "chunks" / f"{digest}.json"


def load_preindex_manifest(full_name: str) -> Optional[dict[str, Any]]:
    manifest_path = _repo_dir(full_name, preindex=True) / "manifest.json"
    if not manifest_path.is_file():
        return None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def load_manifest(full_name: str) -> Optional[dict[str, Any]]:
    pre = load_preindex_manifest(full_name)
    if pre:
        return pre
    manifest_path = _repo_dir(full_name) / "manifest.json"
    if not manifest_path.is_file():
        return None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def save_manifest(full_name: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    repo_dir = _repo_dir(full_name)
    repo_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(manifest)
    payload["schema_version"] = INDEX_SCHEMA_VERSION
    payload["full_name"] = full_name
    manifest_path = repo_dir / "manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def save_chunk(full_name: str, path: str, content: str, *, tier: str = "tier1") -> dict[str, Any]:
    repo_dir = _repo_dir(full_name)
    chunks_dir = repo_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "path": path,
        "tier": tier,
        "chars": len(content),
        "content": content,
        "category": categorize_path(path),
        "score": score_path(path),
        "extension": path_extension(path),
    }
    _chunk_path(repo_dir, path).write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return record


def load_chunk(full_name: str, path: str) -> Optional[dict[str, Any]]:
    for preindex in (True, False):
        repo_dir = _repo_dir(full_name, preindex=preindex)
        chunk_file = _chunk_path(repo_dir, path)
        if chunk_file.is_file():
            return json.loads(chunk_file.read_text(encoding="utf-8"))
    return None


def list_chunks(full_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preindex in (True, False):
        chunks_dir = _repo_dir(full_name, preindex=preindex) / "chunks"
        if not chunks_dir.is_dir():
            continue
        for file in sorted(chunks_dir.glob("*.json")):
            try:
                row = json.loads(file.read_text(encoding="utf-8"))
                if isinstance(row, dict) and row.get("path"):
                    rows.append(row)
            except (json.JSONDecodeError, OSError):
                continue
        if rows:
            break
    return rows


def build_manifest_paths(raw_paths: list[str], *, truncated: bool = False) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "score": score_path(path),
            "category": categorize_path(path),
            "extension": path_extension(path),
            "fetched": False,
        }
        for path in raw_paths
    ]


def mark_paths_fetched(manifest: dict[str, Any], fetched_paths: set[str]) -> None:
    for row in manifest.get("paths") or []:
        if row.get("path") in fetched_paths:
            row["fetched"] = True


def build_digest_from_store(full_name: str, *, max_chars: int = 48_000) -> str:
    manifest = load_manifest(full_name) or {}
    chunks = list_chunks(full_name)
    lines = [
        f"# GitHub repository: {full_name}",
        f"Branch: {manifest.get('default_branch') or 'main'}",
        f"Index schema: {manifest.get('schema_version') or INDEX_SCHEMA_VERSION}",
        "",
    ]
    if manifest.get("readme_excerpt"):
        lines.extend(["## README", str(manifest["readme_excerpt"]), ""])
    lines.append("## Key file contents")
    total = sum(len(line) for line in lines)
    for chunk in sorted(chunks, key=lambda row: -int(row.get("score") or 0)):
        path = str(chunk.get("path") or "")
        body = str(chunk.get("content") or "").strip()
        if not path or not body:
            continue
        block = f"\n### {path}\n```\n{body[:8000]}\n```\n"
        if total + len(block) > max_chars:
            lines.append(f"\n### {path}\n(truncated — digest size limit)\n")
            break
        lines.append(block)
        total += len(block)
    return "\n".join(lines)[:max_chars]


def save_report(full_name: str, report: Mapping[str, Any]) -> dict[str, Any]:
    repo_dir = _repo_dir(full_name)
    repo_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(report)
    payload["full_name"] = full_name
    payload["schema_version"] = "repo_index_report.v1"
    report_path = repo_dir / "report.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_report(full_name: str) -> Optional[dict[str, Any]]:
    for preindex in (False, True):
        report_path = _repo_dir(full_name, preindex=preindex) / "report.json"
        if report_path.is_file():
            data = json.loads(report_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
    return None


def build_index_report(
    full_name: str,
    manifest: Mapping[str, Any],
    chunks: list[Mapping[str, Any]],
    *,
    job_meta: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Structured presentation payload for UI charts and lists."""
    paths = list(manifest.get("paths") or [])
    categories: dict[str, int] = {}
    fetched_categories: dict[str, int] = {}
    for row in paths:
        cat = str(row.get("category") or "other")
        categories[cat] = categories.get(cat, 0) + 1
    tier_chars = {"tier0": 0, "tier1": 0, "tier2": 0}
    top_paths: list[dict[str, Any]] = []
    for chunk in chunks:
        cat = str(chunk.get("category") or "other")
        fetched_categories[cat] = fetched_categories.get(cat, 0) + 1
        tier = str(chunk.get("tier") or "tier1")
        tier_chars[tier] = tier_chars.get(tier, 0) + int(chunk.get("chars") or 0)
        top_paths.append(
            {
                "path": chunk.get("path"),
                "category": cat,
                "score": chunk.get("score"),
                "chars": chunk.get("chars"),
                "tier": tier,
            }
        )
    top_paths.sort(key=lambda row: (-int(row.get("score") or 0), str(row.get("path") or "")))
    total_paths = int(manifest.get("total_paths") or len(paths))
    fetched_count = len(chunks)
    completeness = round((fetched_count / max(total_paths, 1)) * 100, 1)
    category_chart = [
        {"label": label.replace("_", " ").title(), "count": count, "key": label}
        for label, count in sorted(categories.items(), key=lambda item: -item[1])
    ]
    tier_chart = [
        {"label": "Quick (Tier 0)", "chars": tier_chars.get("tier0", 0), "key": "tier0"},
        {"label": "Core (Tier 1)", "chars": tier_chars.get("tier1", 0), "key": "tier1"},
        {"label": "Stage (Tier 2)", "chars": tier_chars.get("tier2", 0), "key": "tier2"},
    ]
    job = dict(job_meta or {})
    return {
        "full_name": full_name,
        "default_branch": manifest.get("default_branch") or "main",
        "truncated_tree": bool(manifest.get("truncated_tree")),
        "total_paths": total_paths,
        "fetched_files": fetched_count,
        "digest_chars": int(manifest.get("digest_chars") or sum(tier_chars.values())),
        "completeness_pct": completeness,
        "readme_found": bool(manifest.get("readme_found")),
        "index_complete": bool(manifest.get("index_complete")),
        "preindexed": bool(manifest.get("preindexed")),
        "enterprise_search": manifest.get("enterprise_search") or {},
        "category_chart": category_chart,
        "tier_chart": tier_chart,
        "top_paths": top_paths[:24],
        "high_relevance_unfetched": [
            row for row in sorted(paths, key=lambda r: -int(r.get("score") or 0))
            if not row.get("fetched")
        ][:12],
        "stage_fetches": list(manifest.get("stage_fetches") or []),
        "narrative": _report_narrative(full_name, manifest, fetched_count, total_paths, job),
        "job": {
            "status": job.get("status"),
            "phase": job.get("phase"),
            "files_indexed": job.get("files_indexed"),
            "progress_pct": job.get("progress_pct"),
        },
    }


def _report_narrative(
    full_name: str,
    manifest: Mapping[str, Any],
    fetched_count: int,
    total_paths: int,
    job: Mapping[str, Any],
) -> str:
    truncated = " Tree listing was truncated by GitHub; IA expanded key subtrees." if manifest.get("truncated_tree") else ""
    pre = " Used curated demo pre-index." if manifest.get("preindexed") else ""
    return (
        f"IA indexed **{full_name}** for this ReviewRun using tiered, access-review scoring — "
        f"not a blind full-repo scan.{pre}{truncated} "
        f"**{fetched_count}** files were excerpted from **{total_paths}** discovered paths. "
        f"Quick index (Tier 0) returned immediately; core files (Tier 1) were ranked by CI, auth, agent, and manifest signals; "
        f"stage-triggered fetches (Tier 2) deepen proof and coach questions on demand."
    )
