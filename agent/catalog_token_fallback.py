"""Deterministic catalog fallback when v1 API is down."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .tools import _load_catalog
from .workload_parse import WorkloadSpecs


def _gpt4o_token_rows() -> Dict[str, float]:
    """Return input/output $/1M for gpt-4o and gpt-4o-mini from catalog."""
    rows = _load_catalog()
    prices: Dict[str, Dict[str, float]] = {}
    for r in rows:
        if (r.get("workload_type") or "").lower() != "llm":
            continue
        key = (r.get("model_key") or "").lower()
        name = (r.get("model_name") or r.get("sku_name") or "").lower()
        try:
            price = float(r.get("unit_price_usd") or 0)
        except (TypeError, ValueError):
            continue
        if "gpt_4o_mini" in key or "gpt-4o mini" in name:
            if "input" in name:
                prices.setdefault("gpt_4o_mini", {})["input"] = price
            elif "output" in name:
                prices.setdefault("gpt_4o_mini", {})["output"] = price
        elif "gpt_4o" in key and "mini" not in key:
            if "input" in name:
                prices.setdefault("gpt_4o", {})["input"] = price
            elif "output" in name:
                prices.setdefault("gpt_4o", {})["output"] = price
    return {
        "gpt_4o": prices.get("gpt_4o", {}),
        "gpt_4o_mini": prices.get("gpt_4o_mini", {}),
    }


def monthly_token_cost(
    tokens_per_month: float,
    input_per_m: float,
    output_per_m: float,
    input_share: float = 0.5,
) -> float:
    tin = tokens_per_month * input_share
    tout = tokens_per_month * (1.0 - input_share)
    return (tin / 1_000_000) * input_per_m + (tout / 1_000_000) * output_per_m


def build_catalog_fallback_plans(specs: WorkloadSpecs) -> dict[str, Any]:
    """Synthetic ranked plans from static CSV (demo fallback only)."""
    prices = _gpt4o_token_rows()
    tpm = specs.tokens_per_month or (specs.tokens_per_day or 0) * 30
    plans: List[dict] = []

    g4 = prices.get("gpt_4o", {})
    mini = prices.get("gpt_4o_mini", {})
    if mini.get("input") and mini.get("output"):
        plans.append(
            {
                "rank": 1,
                "provider_id": "openai",
                "billing_mode": "per_token",
                "model_key": "gpt_4o_mini",
                "monthly_cost_usd": round(
                    monthly_token_cost(tpm, mini["input"], mini["output"]), 2
                ),
                "cost_per_million_tokens": round(
                    (mini["input"] + mini["output"]) / 2, 4
                ),
                "why": "Catalog fallback: GPT-4o mini input/output rows (demo CSV)",
            }
        )
    if g4.get("input") and g4.get("output"):
        plans.append(
            {
                "rank": 2,
                "provider_id": "openai",
                "billing_mode": "per_token",
                "model_key": "gpt_4o",
                "monthly_cost_usd": round(
                    monthly_token_cost(tpm, g4["input"], g4["output"]), 2
                ),
                "cost_per_million_tokens": round((g4["input"] + g4["output"]) / 2, 4),
                "why": "Baseline: full GPT-4o catalog pricing",
            }
        )
    # Together llama from catalog
    rows = _load_catalog()
    for r in rows:
        if (r.get("model_key") or "") == "llama_3_3_70b":
            try:
                p = float(r.get("unit_price_usd") or 0)
            except (TypeError, ValueError):
                continue
            plans.append(
                {
                    "rank": len(plans) + 1,
                    "provider_id": r.get("provider", "together_ai"),
                    "billing_mode": "per_token",
                    "model_key": "llama_3_3_70b",
                    "monthly_cost_usd": round(monthly_token_cost(tpm, p, p), 2),
                    "cost_per_million_tokens": p,
                    "why": "Catalog fallback: Together Llama 3.3 70B row",
                }
            )
            break

    plans.sort(key=lambda x: float(x.get("monthly_cost_usd", 1e18)))
    for i, p in enumerate(plans, 1):
        p["rank"] = i

    return {
        "ok": True,
        "source": "catalog_fallback",
        "plans": plans,
        "token_pricing": prices,
        "tokens_per_month": tpm,
    }
