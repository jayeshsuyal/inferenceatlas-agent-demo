"""Optional enterprise code search: GitHub Code Search API and Sourcegraph."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from . import config
from .connector_runtime import _raw_connection
from .github_repo import _github_headers, _parse_full_name


def github_code_search(token: str, full_name: str, query: str, *, per_page: int = 20) -> list[dict[str, Any]]:
    owner, repo = _parse_full_name(full_name)
    q = f"repo:{owner}/{repo} {query}".strip()
    params = urllib.parse.urlencode({"q": q, "per_page": min(per_page, 100)})
    url = f"https://api.github.com/search/code?{params}"
    req = urllib.request.Request(url, headers=_github_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return []
    items = []
    for row in data.get("items") or []:
        path = str(row.get("path") or "")
        if not path:
            continue
        items.append(
            {
                "path": path,
                "score": 90,
                "source": "github_code_search",
                "url": row.get("html_url") or "",
            }
        )
    return items


def sourcegraph_search(
    query: str,
    repo: str,
    *,
    base_url: str,
    token: str = "",
    limit: int = 20,
) -> list[dict[str, Any]]:
    gql = """
    query RepoSearch($query: String!, $limit: Int!) {
      search(query: $query, first: $limit) {
        results { results { ... on FileMatch { file { path url } } } }
      }
    }
    """
    payload = json.dumps(
        {
            "query": gql,
            "variables": {"query": f"repo:{repo} {query}", "limit": limit},
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = base_url.rstrip("/") + "/.api/graphql"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return []
    items = []
    for row in data.get("data", {}).get("search", {}).get("results", {}).get("results") or []:
        file = (row.get("file") or {})
        path = str(file.get("path") or "")
        if path:
            items.append({"path": path, "score": 88, "source": "sourcegraph", "url": file.get("url") or ""})
    return items


def search_repo_paths(
    session_id: str,
    full_name: str,
    patterns: list[str],
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Search indexed repo paths using enabled enterprise connectors."""
    conn = _raw_connection(session_id, "github")
    results: list[dict[str, Any]] = []
    sources: list[str] = []
    query = " OR ".join(patterns[:6])
    token = str(conn.get("access_token") or "")

    if config.GITHUB_CODE_SEARCH_ENABLED and token and conn.get("mode") not in ("demo_session", "demo_oauth"):
        hits = github_code_search(token, full_name, query, per_page=limit)
        results.extend(hits)
        if hits:
            sources.append("github_code_search")

    if config.SOURCEGRAPH_URL:
        hits = sourcegraph_search(
            query,
            full_name,
            base_url=config.SOURCEGRAPH_URL,
            token=config.SOURCEGRAPH_TOKEN,
            limit=limit,
        )
        results.extend(hits)
        if hits:
            sources.append("sourcegraph")

    deduped: dict[str, dict[str, Any]] = {}
    for row in results:
        path = str(row.get("path") or "")
        if path and path not in deduped:
            deduped[path] = row
    ranked = list(deduped.values())[:limit]
    return {
        "ok": True,
        "full_name": full_name,
        "patterns": patterns,
        "sources": sources,
        "paths": ranked,
        "enterprise_enabled": bool(sources),
    }
