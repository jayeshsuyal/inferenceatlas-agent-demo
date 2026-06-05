"""Cost planning via InferenceAtlas-v1 API + deterministic formatting (Option A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .catalog_token_fallback import build_catalog_fallback_plans
from .config import INFERENCEATLAS_V1_URL
from .v1_client import is_v1_configured, plan_llm, v1_health
from .workload_parse import WorkloadSpecs, parse_workload_specs


@dataclass
class AttachmentRoles:
    skills: List[str]
    github: List[str]
    drive: List[str]
    uploads: List[str]


@dataclass
class CostPlanResult:
    ok: bool
    engine_block: str
    source: str  # inferenceatlas-v1 | catalog_fallback
    specs: WorkloadSpecs
    plans: List[dict]
    message: str = ""


def fetch_cost_plans(specs: WorkloadSpecs) -> dict[str, Any]:
    tokens_per_day = specs.tokens_per_day or (specs.tokens_per_month or 0) / 30.0
    if tokens_per_day <= 0:
        tokens_per_day = 5_000_000.0

    if is_v1_configured():
        try:
            return plan_llm(
                tokens_per_day=tokens_per_day,
                model_bucket=specs.model_bucket,
                peak_to_avg=specs.peak_to_avg,
                top_k=specs.top_k,
                traffic_pattern=specs.traffic_pattern,
            )
        except Exception:
            pass
    return build_catalog_fallback_plans(specs)


def _format_roles(roles: AttachmentRoles) -> str:
    lines = ["### Attachment roles (cite explicitly in your answer)"]
    if roles.skills:
        lines.append(
            f"- **Skills** ({', '.join(roles.skills)}): access-review harness only — "
            "use for production/scoped-validation/proof debt if asked; do not override engine prices."
        )
    else:
        lines.append("- **Skills**: none")
    if roles.github:
        lines.append(
            f"- **GitHub** ({', '.join(roles.github)}): product/architecture context only — "
            "mention InferenceAtlas-v1 / rank_configs / Cost Audit if relevant; do not invent repo files."
        )
    else:
        lines.append("- **GitHub**: none")
    if roles.drive:
        lines.append(
            f"- **Drive** ({', '.join(roles.drive)}): strategy/docs context — "
            "not used for unit pricing unless user asks about release strategy."
        )
    else:
        lines.append("- **Drive**: none")
    if roles.uploads:
        lines.append(
            f"- **Uploads** ({', '.join(roles.uploads)}): not spend data — "
            "state clearly if non-billing CSV; do not use for provider ranking."
        )
    else:
        lines.append("- **Uploads**: none")
    return "\n".join(lines)


def _format_compatibility(compatibility: List[dict]) -> List[str]:
    if not compatibility:
        return []
    lines = [
        "",
        "### Provider compatibility (v1 get_provider_compatibility)",
        "",
        "| Provider | Compatible | Reason |",
        "| --- | --- | --- |",
    ]
    for row in compatibility[:16]:
        name = row.get("provider_name") or row.get("provider_id") or "?"
        ok = row.get("compatible", False)
        reason = (row.get("reason") or "")[:80]
        lines.append(f"| {name} | {'yes' if ok else 'no'} | {reason} |")
    return lines


def _format_catalog_ranking(offers: List[dict]) -> List[str]:
    if not offers:
        return []
    lines = [
        "",
        "### Catalog token ranking (v1 rank_catalog_offers — per-token API baselines)",
        "",
        "| Rank | Provider | SKU | $/1M (comparator) | Monthly est. USD | Confidence |",
        "| ---: | --- | --- | ---: | ---: | --- |",
    ]
    for i, o in enumerate(offers[:10], 1):
        lines.append(
            f"| {i} | {o.get('provider', '?')} | {o.get('offering', '?')} | "
            f"{o.get('comparator_price', '?')} | {o.get('monthly_estimate_usd', '?')} | "
            f"{o.get('confidence', '?')} |"
        )
    lines.append(
        "Use this table for **GPT-4o / per-token API** comparisons; deployment plans above are "
        "**GPU/capacity** alternatives from rank_configs."
    )
    return lines


def format_engine_block(
    payload: dict[str, Any],
    specs: WorkloadSpecs,
    roles: AttachmentRoles,
) -> str:
    source = payload.get("source", "unknown")
    plans = payload.get("plans") or []
    tpm = specs.tokens_per_month or (specs.tokens_per_day or 0) * 30
    tpd = specs.tokens_per_day or tpm / 30.0
    engine_bucket = payload.get("engine_model_bucket") or specs.model_bucket
    requested_bucket = payload.get("requested_model_bucket") or specs.model_bucket

    lines = [
        "--- INFERENCEATLAS ENGINE (deterministic — numbers are authoritative) ---",
        "",
        f"Source: **{source}** (v1 `rank_configs` + `rank_catalog_offers` + `get_provider_compatibility`)",
        f"Workload: requested_bucket={requested_bucket}, engine_bucket={engine_bucket}, "
        f"tokens/day={tpd:,.0f}, tokens/month≈{tpm:,.0f}, peak_to_avg={specs.peak_to_avg}",
        "",
    ]

    summary = payload.get("engine_summary") or ""
    if summary:
        lines.extend(["### Engine summary (v1 deterministic)", "", summary, ""])

    lines.extend(
        [
            "### Ranked deployment plans (monthly USD — rank_configs)",
            "",
            "| Rank | Provider | Offering | Billing | GPU | Monthly USD | Score | Risk | Why |",
            "| ---: | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for p in plans[: specs.top_k]:
        prov = p.get("provider_name") or p.get("provider_id") or "?"
        offering = (p.get("offering_id") or "")[:24]
        bill = p.get("billing_mode") or p.get("billing") or "-"
        monthly = p.get("monthly_cost_usd", p.get("monthly_cost", "?"))
        score = p.get("score", "-")
        risk = p.get("risk_total", p.get("risk", {}).get("total_risk") if isinstance(p.get("risk"), dict) else "-")
        why = (p.get("why") or "")[:100]
        rank = p.get("rank", "-")
        gpu = p.get("gpu_type") or p.get("gpu") or ""
        gpus = p.get("gpu_count", "")
        gpu_cell = f"{gpu}×{gpus}" if gpu else "-"
        lines.append(
            f"| {rank} | {prov} | {offering} | {bill} | {gpu_cell} | {monthly} | {score} | {risk} | {why} |"
        )

    if not plans:
        lines.append("| — | (no plans returned) | — | — | — | — | — | — | — |")

    lines.extend(_format_catalog_ranking(payload.get("catalog_token_ranking") or []))
    lines.extend(_format_compatibility(payload.get("provider_compatibility") or []))

    token_px = payload.get("token_pricing")
    if token_px:
        lines.extend(["", "### Token catalog reference (demo CSV fallback only)", "", str(token_px)])

    lines.extend(
        [
            "",
            "### Instructions for the assistant",
            "- Lead with **Engine summary** and **#1 deployment plan** monthly USD.",
            "- For GPT-4o / compare_providers questions: cite **Catalog token ranking** for API baselines "
            "AND **Ranked deployment plans** for infrastructure alternatives.",
            "- Cite **Provider compatibility** when explaining why providers were excluded.",
            "- Compare baseline vs recommendation using **monthly USD**, not input price alone.",
            "- Do **not** change, round differently, or invent prices not in this block.",
            "- Do **not** use Tavily or web search for pricing when this block is present.",
            "",
            _format_roles(roles),
        ]
    )
    return "\n".join(lines)


def build_cost_plan(
    message: str,
    roles: AttachmentRoles,
) -> CostPlanResult:
    specs = parse_workload_specs(message)
    try:
        payload = fetch_cost_plans(specs)
        block = format_engine_block(payload, specs, roles)
        return CostPlanResult(
            ok=bool(payload.get("plans")),
            engine_block=block,
            source=str(payload.get("source", "")),
            specs=specs,
            plans=payload.get("plans") or [],
            message="Engine plan ready",
        )
    except Exception as exc:
        return CostPlanResult(
            ok=False,
            engine_block="",
            source="error",
            specs=specs,
            plans=[],
            message=str(exc),
        )


def v1_status_summary() -> dict[str, Any]:
    if not is_v1_configured():
        return {
            "configured": False,
            "url": "",
            "ok": False,
            "message": "Set INFERENCEATLAS_V1_URL to connect (e.g. http://127.0.0.1:8000)",
        }
    health = v1_health()
    return {
        "configured": True,
        "url": INFERENCEATLAS_V1_URL,
        "ok": health.get("ok", False),
        "message": health.get("message") or "connected",
        "health": health,
    }
