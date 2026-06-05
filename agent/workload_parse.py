"""Parse workload specs from natural-language cost questions."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class WorkloadSpecs:
    tokens_per_month: Optional[float] = None
    tokens_per_day: Optional[float] = None
    model_bucket: str = "4o"
    baseline_model: str = "gpt-4o"
    peak_to_avg: float = 2.5
    top_k: int = 8
    traffic_pattern: str = "steady"
    wants_compare_providers: bool = False


def parse_workload_specs(message: str) -> WorkloadSpecs:
    text = message.strip()
    lower = text.lower()
    specs = WorkloadSpecs(wants_compare_providers="compare_providers" in lower)

    # 500M tokens/month, 500 million tokens per month
    m = re.search(
        r"([\d,.]+)\s*(million|m|b|billion|k|thousand)?\s*tokens?\s*/?\s*month",
        lower,
    )
    if not m:
        m = re.search(
            r"([\d,.]+)\s*(million|m|b|billion|k|thousand)?\s*tokens?\s+per\s+month",
            lower,
        )
    if m:
        specs = _with_tokens(specs, _parse_amount(m.group(1), m.group(2)), per_month=True)

    m = re.search(
        r"([\d,.]+)\s*(million|m|b|billion|k|thousand)?\s*tokens?\s*/?\s*day",
        lower,
    )
    if m:
        specs = _with_tokens(specs, _parse_amount(m.group(1), m.group(2)), per_month=False)

    if "gpt-4o" in lower or "gpt_4o" in lower or "gpt4o" in lower:
        specs = replace(specs, model_bucket="4o", baseline_model="gpt-4o")
    elif "gpt-4" in lower:
        specs = replace(specs, model_bucket="4o", baseline_model="gpt-4")
    elif re.search(r"\b70b\b", lower):
        specs = replace(specs, model_bucket="70b")
    elif re.search(r"\b7b\b", lower):
        specs = replace(specs, model_bucket="7b")

    return specs


def _parse_amount(num: str, unit: Optional[str]) -> float:
    val = float(num.replace(",", ""))
    u = (unit or "").strip().lower()
    if u in ("million", "m"):
        return val * 1_000_000
    if u in ("billion", "b"):
        return val * 1_000_000_000
    if u in ("thousand", "k"):
        return val * 1_000
    return val


def _with_tokens(specs: WorkloadSpecs, amount: float, *, per_month: bool) -> WorkloadSpecs:
    if per_month:
        return replace(specs, tokens_per_month=amount, tokens_per_day=amount / 30.0)
    return replace(specs, tokens_per_day=amount, tokens_per_month=amount * 30.0)


def is_access_review_question(message: str) -> bool:
    """Detect agent-access / harness questions (not cost)."""
    if is_cost_question(message):
        return False
    lower = message.lower()
    patterns = (
        r"should\b.*\b(agent|bot)\b.*\b(get|have|grant|receive)\b",
        r"support triage",
        r"production access",
        r"access review",
        r"github.*slack.*jira",
        r"tool access",
        r"who must approve",
        r"proof gap",
        r"decision packet",
        r"scoped validation",
    )
    return any(re.search(p, lower) for p in patterns)


def is_cost_question(message: str) -> bool:
    lower = message.lower()
    if any(kw in lower for kw in ("compare_providers", "get_catalog_summary", "cheapest", "pricing")):
        return True
    if re.search(r"\bcompare\b.*\bprovider", lower):
        return True
    if re.search(r"\bcost\b.*\btoken", lower) or "tokens/month" in lower or "tokens per month" in lower:
        return True
    if re.search(r"\bgpt-4", lower) and re.search(r"\btoken", lower):
        return True
    return False
