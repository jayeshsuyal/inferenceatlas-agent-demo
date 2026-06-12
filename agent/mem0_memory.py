"""Mem0 long-term memory bridge for ReviewRun coach and session context."""

from __future__ import annotations

from typing import Any, Optional

from . import config


def _client():
    if not config.MEM0_ENABLED or not config.MEM0_API_KEY:
        return None
    try:
        from mem0 import MemoryClient
    except ImportError:
        return None
    return MemoryClient(api_key=config.MEM0_API_KEY)


def add_memory(text: str, *, run_id: str = "", metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    client = _client()
    if not client or not text.strip():
        return {"ok": False, "skipped": True}
    payload: dict[str, Any] = {
        "user_id": config.MEM0_USER_ID,
        "metadata": dict(metadata or {}),
    }
    if run_id:
        payload["run_id"] = run_id
    try:
        result = client.add(text.strip(), **payload)
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def search_memories(query: str, *, run_id: str = "", limit: int = 5) -> list[dict[str, Any]]:
    client = _client()
    if not client or not query.strip():
        return []
    filters: dict[str, Any] = {"user_id": config.MEM0_USER_ID}
    if run_id:
        filters["run_id"] = run_id
    try:
        results = client.search(query.strip(), user_id=config.MEM0_USER_ID, limit=limit)
        if isinstance(results, dict):
            return list(results.get("results") or results.get("memories") or [])
        if isinstance(results, list):
            return results
    except Exception:
        return []
    return []


def format_mem0_context_block(query: str, *, run_id: str = "") -> str:
    hits = search_memories(query, run_id=run_id, limit=5)
    if not hits:
        return ""
    lines = ["### Mem0 recalled context (long-term memory)"]
    for row in hits:
        memory = str(row.get("memory") or row.get("text") or row.get("content") or "").strip()
        if memory:
            lines.append(f"- {memory[:500]}")
    return "\n".join(lines)
