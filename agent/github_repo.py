"""GitHub repository list, attach, and digest for chat context (ChatGPT-style)."""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .connector_runtime import _now_iso, _raw_connection, load_session, save_session
from .repo_index_scoring import TEXT_EXTENSIONS, pick_scored_paths
from .repo_index_store import (
    build_digest_from_store,
    build_manifest_paths,
    load_preindex_manifest,
    load_report,
    save_chunk,
    save_manifest,
    save_report,
    build_index_report,
    list_chunks,
)
from .scenarios import ROOT_DIR

MAX_DIGEST_CHARS = 48_000
MAX_FILE_BYTES = 24_000
MAX_FILES = 10
SUBTREE_PREFIXES = (".github/", "docs/", "doc/", "src/", "agent/", "api/", "web/", "schemas/")


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "InferenceAtlas-Agent-Demo",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _github_get(token: str, path: str, *, accept: Optional[str] = None) -> Any:
    headers = _github_headers(token)
    if accept:
        headers["Accept"] = accept
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
            if accept and "raw" in accept:
                return raw.decode("utf-8", errors="replace")
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {detail[:400]}") from exc


def _demo_repos() -> List[dict[str, Any]]:
    return [
        {
            "full_name": "inferenceatlas/support-triage-trial",
            "description": "Demo repo — support triage access request (fixture)",
            "private": False,
            "default_branch": "main",
            "indexed": True,
        },
        {
            "full_name": "inferenceatlas/agent-access-review",
            "description": "Demo repo — DecisionPacket examples",
            "private": False,
            "default_branch": "main",
            "indexed": True,
        },
    ]


def _attached_repos(session_id: str) -> Dict[str, dict]:
    data = load_session(session_id)
    return data.get("github_attached", {}) or {}


def _digest_index_meta(digest: str, full_name: str) -> dict[str, Any]:
    readme_found = bool(digest) and "(no README found)" not in digest and "## README" in digest
    tree_lines = [
        ln.strip("- ").strip()
        for ln in digest.splitlines()
        if ln.strip().startswith("- ") and "/" in ln
    ][:120]
    files_included = digest.count("\n### ")
    return {
        "full_name": full_name,
        "indexed": bool(digest) and len(digest) > 200,
        "digest_chars": len(digest),
        "readme_found": readme_found,
        "paths_in_tree": len(tree_lines),
        "files_included": files_included,
        "sample_paths": tree_lines[:6],
    }


def get_repo_index_status(session_id: str, full_name: str) -> dict[str, Any]:
    """Return indexing verification for UI and thinking logs."""
    entry = _attached_repos(session_id).get(full_name.strip(), {})
    digest = entry.get("digest", "")
    meta = _digest_index_meta(digest, full_name)
    meta["attached_at"] = entry.get("attached_at", "")
    meta["preview"] = entry.get("preview", "")[:200]
    return meta


def list_repositories(
    session_id: str,
    *,
    query: str = "",
    per_page: int = 50,
) -> dict[str, Any]:
    """List repos for the signed-in user (searchable)."""
    conn = _raw_connection(session_id, "github")
    if conn.get("status") != "connected":
        return {"ok": False, "message": "Sign in to GitHub first.", "repos": []}

    attached = _attached_repos(session_id)
    q = query.strip().lower()

    if conn.get("mode") in ("demo_session", "demo_oauth") or not conn.get("access_token"):
        repos = _demo_repos()
        if q:
            repos = [r for r in repos if q in r["full_name"].lower() or q in (r.get("description") or "").lower()]
        for r in repos:
            r["indexed"] = r["full_name"] in attached
        return {"ok": True, "repos": repos, "demo": True}

    token = conn["access_token"]
    params = urllib.parse.urlencode(
        {
            "per_page": min(per_page, 100),
            "sort": "updated",
            "affiliation": "owner,collaborator,organization_member",
        }
    )
    data = _github_get(token, f"/user/repos?{params}")
    if not isinstance(data, list):
        return {"ok": False, "message": "Unexpected GitHub response", "repos": []}

    repos: List[dict[str, Any]] = []
    for item in data:
        full_name = item.get("full_name") or ""
        if not full_name:
            continue
        if q and q not in full_name.lower() and q not in (item.get("description") or "").lower():
            continue
        repos.append(
            {
                "full_name": full_name,
                "description": (item.get("description") or "")[:200],
                "private": bool(item.get("private")),
                "default_branch": item.get("default_branch") or "main",
                "updated_at": item.get("updated_at", ""),
                "indexed": full_name in attached,
            }
        )
    return {"ok": True, "repos": repos, "demo": False}


def _parse_full_name(full_name: str) -> Tuple[str, str]:
    parts = full_name.strip().split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid repo name: {full_name}")
    return parts[0], parts[1]


def _fetch_readme(token: str, owner: str, repo: str) -> str:
    try:
        return _github_get(
            token,
            f"/repos/{owner}/{repo}/readme",
            accept="application/vnd.github.raw",
        )
    except Exception:
        return ""


def _fetch_tree_paths(token: str, owner: str, repo: str, branch: str) -> tuple[List[str], bool]:
    """Return all blob paths and whether GitHub truncated the recursive tree."""
    try:
        ref = _github_get(token, f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        sha = ref.get("object", {}).get("sha")
        if not sha:
            return [], False
        tree = _github_get(token, f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")
        paths: list[str] = []
        for node in tree.get("tree", []):
            p = node.get("path", "")
            if node.get("type") == "blob" and p:
                paths.append(p)
        truncated = bool(tree.get("truncated"))
        if truncated:
            paths.extend(_fetch_subtree_paths(token, owner, repo, sha))
        return sorted(set(paths)), truncated
    except Exception:
        return [], False


def _fetch_subtree_paths(token: str, owner: str, repo: str, root_sha: str) -> List[str]:
    """Best-effort expansion when recursive tree is truncated."""
    extra: list[str] = []
    try:
        root = _github_get(token, f"/repos/{owner}/{repo}/git/trees/{root_sha}")
        for node in root.get("tree", []):
            path = str(node.get("path") or "")
            if node.get("type") != "tree":
                continue
            if not any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in SUBTREE_PREFIXES):
                continue
            sha = node.get("sha")
            if not sha:
                continue
            subtree = _github_get(token, f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")
            for child in subtree.get("tree", []):
                child_path = child.get("path", "")
                if child.get("type") == "blob" and child_path:
                    extra.append(f"{path}/{child_path}" if path else child_path)
    except Exception:
        return []
    return extra


def _fetch_file_content(token: str, owner: str, repo: str, path: str) -> str:
    try:
        meta = _github_get(token, f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path)}")
        if isinstance(meta, list):
            return ""
        if meta.get("size", 0) > MAX_FILE_BYTES:
            return f"(file too large: {meta.get('size')} bytes)\n"
        enc = meta.get("encoding")
        content = meta.get("content", "")
        if enc == "base64" and content:
            raw = base64.b64decode(content)
            return raw.decode("utf-8", errors="replace")
        return ""
    except Exception:
        return ""


def _pick_files(paths: List[str]) -> List[str]:
    ranked = pick_scored_paths(paths, limit=MAX_FILES)
    return [row["path"] for row in ranked]


def _demo_digest(full_name: str) -> str:
    owner, repo = _parse_full_name(full_name)
    trial = ROOT_DIR / "examples" / "requests" / "support_triage_trial.yml"
    brief = ROOT_DIR / "examples" / "generated" / "support_triage_agent.decision_brief.md"
    chunks = [f"# Repository context: {full_name}\n", f"(Demo digest — sign in with live GitHub OAuth for full repo.)\n"]
    if trial.is_file():
        chunks.append("## examples/requests/support_triage_trial.yml\n" + trial.read_text(encoding="utf-8")[:8000])
    if brief.is_file():
        chunks.append("## examples/generated/support_triage_agent.decision_brief.md\n" + brief.read_text(encoding="utf-8")[:8000])
    return "\n\n".join(chunks)[:MAX_DIGEST_CHARS]


def _apply_preindex_if_available(full_name: str) -> Optional[str]:
    pre = load_preindex_manifest(full_name)
    if not pre:
        return None
    save_manifest(full_name, {**pre, "preindexed": True})
    digest = build_digest_from_store(full_name, max_chars=MAX_DIGEST_CHARS)
    if digest:
        report = load_report(full_name) or build_index_report(full_name, pre, list_chunks(full_name))
        save_report(full_name, report)
        return digest
    return None


def build_repo_digest(session_id: str, full_name: str) -> str:
    conn = _raw_connection(session_id, "github")
    owner, repo = _parse_full_name(full_name)

    if conn.get("mode") in ("demo_session", "demo_oauth") or not conn.get("access_token"):
        pre_digest = _apply_preindex_if_available(full_name)
        return pre_digest or _demo_digest(full_name)

    pre_digest = _apply_preindex_if_available(full_name)
    if pre_digest:
        return pre_digest

    token = conn["access_token"]
    meta = _github_get(token, f"/repos/{owner}/{repo}")
    branch = meta.get("default_branch") or "main"
    readme = _fetch_readme(token, owner, repo)
    paths, truncated = _fetch_tree_paths(token, owner, repo, branch)
    pick = _pick_files(paths)

    manifest = {
        "default_branch": branch,
        "truncated_tree": truncated,
        "total_paths": len(paths),
        "readme_found": bool(readme),
        "readme_excerpt": readme[:12000] if readme else "",
        "paths": build_manifest_paths(paths, truncated=truncated),
        "index_complete": False,
    }
    save_manifest(full_name, manifest)

    if readme:
        save_chunk(full_name, "README.md", readme[:12000], tier="tier0")
    for path in pick:
        if path.lower().startswith("readme"):
            continue
        body = _fetch_file_content(token, owner, repo, path)
        if body.strip():
            save_chunk(full_name, path, body[:8000], tier="tier0")

    fetched = {row["path"] for row in list_chunks(full_name)}
    for row in manifest["paths"]:
        if row["path"] in fetched:
            row["fetched"] = True
    manifest["digest_chars"] = len(build_digest_from_store(full_name, max_chars=MAX_DIGEST_CHARS))
    save_manifest(full_name, manifest)
    save_report(full_name, build_index_report(full_name, manifest, list_chunks(full_name)))

    parts = [
        f"# GitHub repository: {full_name}",
        f"Description: {meta.get('description') or '(none)'}",
        f"Default branch: {branch}",
        f"Private: {meta.get('private')}",
        f"URL: {meta.get('html_url', '')}",
        "",
        "## README",
        readme[:12000] if readme else "(no README found)",
        "",
        "## Repository tree (sample paths)",
        "\n".join(f"- {p}" for p in paths[:120]),
        "",
        "## Key file contents",
    ]
    total = sum(len(p) for p in parts)
    for path in pick:
        if path.lower().startswith("readme"):
            continue
        body = _fetch_file_content(token, owner, repo, path)
        if not body.strip():
            continue
        block = f"\n### {path}\n```\n{body[:8000]}\n```\n"
        if total + len(block) > MAX_DIGEST_CHARS:
            parts.append(f"\n### {path}\n(truncated — digest size limit)\n")
            break
        parts.append(block)
        total += len(block)

    return "\n".join(parts)[:MAX_DIGEST_CHARS]


def attach_repository(session_id: str, full_name: str) -> dict[str, Any]:
    """Index a repo into session cache for chat."""
    from .session_metrics import record_connector_index

    conn = _raw_connection(session_id, "github")
    if conn.get("status") != "connected":
        return {"ok": False, "message": "Sign in to GitHub first."}

    try:
        digest = build_repo_digest(session_id, full_name)
    except Exception as exc:
        return {"ok": False, "message": str(exc)}

    data = load_session(session_id)
    attached = data.setdefault("github_attached", {})
    index_meta = _digest_index_meta(digest, full_name)
    attached[full_name] = {
        "full_name": full_name,
        "digest_chars": len(digest),
        "attached_at": _now_iso(),
        "preview": digest[:400].replace("\n", " "),
        **index_meta,
    }
    attached[full_name]["digest"] = digest
    save_session(session_id, data)
    record_connector_index("github", session_id)

    return {
        "ok": True,
        "full_name": full_name,
        "indexed": index_meta["indexed"],
        "preview": digest[:500],
        "digest_chars": len(digest),
        "readme_found": index_meta["readme_found"],
        "paths_in_tree": index_meta["paths_in_tree"],
        "files_included": index_meta["files_included"],
        "sample_paths": index_meta["sample_paths"],
        "message": (
            f"Indexed {full_name}: {len(digest):,} chars"
            f"{', README ✓' if index_meta['readme_found'] else ''}"
            f", {index_meta['files_included']} files"
        ),
    }


def build_github_chat_context(session_id: str, repo_names: List[str]) -> Tuple[str, List[str]]:
    """Build LLM context for selected repos; returns (text, list of full_names used)."""
    used: List[str] = []
    blocks: List[str] = []
    attached = _attached_repos(session_id)

    for name in repo_names[:3]:
        name = name.strip()
        if not name:
            continue
        entry = attached.get(name)
        if entry and entry.get("digest"):
            digest = entry["digest"]
        else:
            result = attach_repository(session_id, name)
            if not result.get("ok"):
                continue
            entry = _attached_repos(session_id).get(name, {})
            digest = entry.get("digest", "")
        if digest:
            blocks.append(f"--- GITHUB REPO: {name} ---\n\n{digest}\n")
            used.append(name)

    if not blocks:
        return "", []

    instructions = (
        "The user attached GitHub repository context below. Answer using this material — "
        "reference files, README, and structure. Do not say you lack tools or functions.\n\n"
    )
    return instructions + "\n".join(blocks), used


GITHUB_CONTEXT_SYSTEM_PROMPT = """You are the InferenceAtlas assistant with attached GitHub repository context.

The user message includes real repository content: README, file tree, and file excerpts.

Rules:
1. Answer from the GitHub context provided. Reference specific files, paths, and README content.
2. Do not claim you cannot access GitHub or need different tools.
3. Be specific: name repos, branches, technologies, and proof-relevant facts for access review if asked.
4. If context is demo/fixture, say so briefly but still answer from the text given.
"""
