"""Cost planning via InferenceAtlas-v1 API + deterministic formatting (Option A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


def format_engine_block(
    payload: dict[str, Any],
    specs: WorkloadSpecs,
    roles: AttachmentRoles,
) -> str:
    source = payload.get("source", "unknown")
    plans = payload.get("plans") or []
    tpm = specs.tokens_per_month or (specs.tokens_per_day or 0) * 30
    tpd = specs.tokens_per_day or tpm / 30.0

    lines = [
        "--- INFERENCEATLAS ENGINE (deterministic — numbers are authoritative) ---",
        "",
        f"Source: **{source}** (`rank_configs` / plan_llm pipeline)",
        f"Workload: model_bucket={specs.model_bucket}, tokens/day={tpd:,.0f}, "
        f"tokens/month≈{tpm:,.0f}, peak_to_avg={specs.peak_to_avg}",
        "",
        "### Ranked plans (monthly USD from engine)",
        "",
        "| Rank | Provider | Billing | Monthly USD | $/1M tok (approx) | Why |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for p in plans[: specs.top_k]:
        prov = p.get("provider_id") or p.get("provider") or "?"
        bill = p.get("billing_mode") or p.get("billing") or "-"
        monthly = p.get("monthly_cost_usd", p.get("monthly_cost", "?"))
        cpm = p.get("cost_per_million_tokens", p.get("unit_price_usd", "-"))
        why = (p.get("why") or "")[:120]
        rank = p.get("rank", "-")
        gpu = p.get("gpu_type") or p.get("gpu") or ""
        extra = f" {gpu}" if gpu else ""
        lines.append(
            f"| {rank} | {prov}{extra} | {bill} | {monthly} | {cpm} | {why} |"
        )

    if not plans:
        lines.append("| — | (no plans returned) | — | — | — | — |")

    token_px = payload.get("token_pricing")
    if token_px:
        lines.extend(["", "### Token catalog reference (fallback CSV)", "", str(token_px)])

    lines.extend(
        [
            "",
            "### Instructions for the assistant",
            "- Recommend using the **#1 ranked plan** for cheapest credible capacity at this volume.",
            "- Compare to user's baseline (GPT-4o) using **monthly USD**, not input price alone.",
            "- Do **not** change, round differently, or invent prices not in this table.",
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
