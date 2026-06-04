"""Thin HTTP client for InferenceAtlas-v1 FastAPI (Option A gateway)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .config import INFERENCEATLAS_V1_TIMEOUT, INFERENCEATLAS_V1_URL


def is_v1_configured() -> bool:
    return bool(INFERENCEATLAS_V1_URL)


def _base_url() -> str:
    return INFERENCEATLAS_V1_URL.rstrip("/")


def _request(
    method: str,
    path: str,
    *,
    body: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> Any:
    if not is_v1_configured():
        raise RuntimeError("INFERENCEATLAS_V1_URL is not set")
    url = f"{_base_url()}{path}"
    data = None
    headers = {"Accept": "application/json", "User-Agent": "InferenceAtlas-Agent-Demo"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout or INFERENCEATLAS_V1_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"InferenceAtlas-v1 HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"InferenceAtlas-v1 unreachable at {url}: {exc}") from exc


def v1_health() -> dict[str, Any]:
    """Ping v1 — tries /api/health then /health."""
    if not is_v1_configured():
        return {"ok": False, "message": "INFERENCEATLAS_V1_URL not set"}
    for path in ("/api/health", "/health", "/"):
        try:
            data = _request("GET", path, timeout=5)
            return {"ok": True, "path": path, "data": data}
        except Exception as exc:
            last = str(exc)
    return {"ok": False, "message": last}


def normalize_plans(payload: Any) -> List[dict[str, Any]]:
    """Accept list or {plans: [...]} style responses."""
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        for key in ("plans", "results", "ranked_plans", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [p for p in val if isinstance(p, dict)]
        if "rank" in payload or "monthly_cost_usd" in payload:
            return [payload]
    return []


def plan_llm(
    *,
    tokens_per_day: float,
    model_bucket: str = "4o",
    peak_to_avg: float = 2.5,
    top_k: int = 8,
    traffic_pattern: str = "steady",
) -> dict[str, Any]:
    """
    POST /api/v1/plan/llm — rank_configs pipeline on v1.
    Tries a few body key variants for API version drift.
    """
    bodies = [
        {
            "tokens_per_day": tokens_per_day,
            "model_bucket": model_bucket,
            "peak_to_avg": peak_to_avg,
            "top_k": top_k,
            "traffic_pattern": traffic_pattern,
        },
        {
            "tokens_per_day": tokens_per_day,
            "model": model_bucket,
            "peak_to_avg": peak_to_avg,
            "top_k": top_k,
        },
    ]
    paths = ("/api/v1/plan/llm", "/api/v1/plan/llm/")
    last_err: Optional[Exception] = None
    for path in paths:
        for body in bodies:
            try:
                data = _request("POST", path, body=body)
                plans = normalize_plans(data)
                return {
                    "ok": True,
                    "source": "inferenceatlas-v1",
                    "path": path,
                    "request": body,
                    "plans": plans,
                    "raw": data if isinstance(data, dict) else {"plans": plans},
                }
            except Exception as exc:
                last_err = exc
    raise RuntimeError(str(last_err or "plan_llm failed"))
