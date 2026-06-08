"""Canonical sponsor proof trace for the public design-partner flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .adapters import build_adapter_result
from .packet_authority import build_packet_authority_snapshot_for_scenario
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_packet
from .spend import build_spend_review_bundle
from .tavily_live_evidence import ClientFactory, build_tavily_live_evidence
from .trial import DEFAULT_TRIAL_REQUEST


SPONSOR_PROOF_TRACE_SCHEMA_VERSION = "sponsor_proof_trace.v0"
SPONSOR_PROOF_TRACE_GENERATED_AT = "2026-06-05T00:00:00Z"
SPONSOR_ORDER = ("tavily", "composio", "openclaw", "nebius")
ALLOWED_VERBS_PER_SPONSOR = {
    "tavily": "searched",
    "composio": "planned",
    "openclaw": "traced",
    "nebius": "narrated",
}
DEFAULT_SCENARIO = "support_triage_agent"


@dataclass(frozen=True)
class DecisionLock:
    """Fields sponsors must not change."""

    verdict: str
    review_posture: str
    production_access: bool
    permission_grants: bool
    external_writes: bool
    approval_granted: bool
    spend_approved: bool
    provider_winner_selected: bool
    savings_guaranteed: bool
    can_sponsor_change_decision: bool = False


@dataclass(frozen=True)
class AccessEvidenceBlock:
    """Access-review evidence carried by the trace."""

    packet_id: str
    requested_tools: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    missing_proof: tuple[str, ...]
    reviewer_owners: tuple[str, ...]
    production_access: bool
    permission_grants: bool
    external_writes: bool


@dataclass(frozen=True)
class SpendEvidenceBlock:
    """Spend-review evidence carried by the trace."""

    packet_id: str
    requested_budget: str | None
    invoice_evidence_refs: tuple[str, ...]
    blocked_dollar_claims: tuple[str, ...]
    finance_owner: str | None
    procurement_owner: str | None
    approves_spend: bool
    selects_provider: bool
    guarantees_savings: bool


@dataclass(frozen=True)
class SponsorStep:
    """One sponsor contribution attempt in locked order."""

    sponsor: Literal["tavily", "composio", "openclaw", "nebius"]
    step_verb: Literal["searched", "planned", "traced", "narrated"]
    input_hash: str
    output_hash: str
    output_summary: str
    accepted_fields: tuple[str, ...]
    rejected_fields: tuple[str, ...]
    redacted_fields: tuple[str, ...]
    duration_ms: int
    succeeded: bool
    used_live_key: bool
    fallback_used: bool
    would_execute: bool
    can_approve_access: bool
    can_grant_permissions: bool
    can_mutate_external_state: bool
    human_review_required: bool


@dataclass(frozen=True)
class SponsorProofTrace:
    """Canonical per-run artifact for sponsor proof collection."""

    trace_id: str
    content_hash: str
    packet_id: str
    revision_id: str
    scenario_name: str
    lane: Literal["access_review", "spend_review", "both"]
    sponsor_steps: tuple[SponsorStep, ...]
    blocked_actions: tuple[str, ...]
    access_review_evidence: AccessEvidenceBlock | None
    spend_review_evidence: SpendEvidenceBlock | None
    decision_lock_before: DecisionLock
    decision_lock_after: DecisionLock
    fallback_used: dict[str, bool]
    generated_at: str = SPONSOR_PROOF_TRACE_GENERATED_AT
    schema_version: str = SPONSOR_PROOF_TRACE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _public_dict(asdict(self))


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _public_dict(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_public_dict(item) for item in value]
    if isinstance(value, list):
        return [_public_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _public_dict(item) for key, item in value.items()}
    return value


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(_public_dict(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stable_hash(value: Any) -> str:
    return f"sha256:{_stable_digest(value)}"


def _flatten_blocked_actions(packet: dict[str, Any]) -> tuple[str, ...]:
    actions = []
    for tool_name, plan in packet["tool_access_plan"].items():
        for action in plan["blocked_actions"]:
            actions.append(f"{tool_name}: {action}")
    return tuple(actions)


def _decision_lock(packet: dict[str, Any], spend_packet: dict[str, Any]) -> DecisionLock:
    spend_state = spend_packet["safety_state"]
    return DecisionLock(
        verdict=packet["decision"]["verdict"],
        review_posture=packet["decision"]["review_posture"],
        production_access=packet["approval_posture"]["production_access"] == "approved",
        permission_grants=False,
        external_writes=packet["safety_state"]["external_writes_enabled"],
        approval_granted=packet["safety_state"]["approval_granted"],
        spend_approved=spend_state["spend_approved"],
        provider_winner_selected=spend_state["provider_winner_selected"],
        savings_guaranteed=spend_state["savings_guaranteed"],
    )


def _access_evidence(packet: dict[str, Any]) -> AccessEvidenceBlock:
    return AccessEvidenceBlock(
        packet_id=packet["packet_id"],
        requested_tools=tuple(packet["tool_access_plan"].keys()),
        blocked_actions=_flatten_blocked_actions(packet),
        missing_proof=tuple(item["item"] for item in packet["missing_proof"]),
        reviewer_owners=tuple(item["owner"] for item in packet["reviewer_owners"]),
        production_access=packet["approval_posture"]["production_access"] == "approved",
        permission_grants=False,
        external_writes=packet["safety_state"]["external_writes_enabled"],
    )


def _spend_evidence(spend_packet: dict[str, Any]) -> SpendEvidenceBlock:
    owners = {item["owner"]: item for item in spend_packet["reviewer_owners"]}
    invoice_refs = [
        item["evidence"]
        for item in spend_packet["required_evidence"]
        if "invoice" in item["evidence"].lower() or item["owner"] == "Finance"
    ]
    return SpendEvidenceBlock(
        packet_id=spend_packet["packet_id"],
        requested_budget=spend_packet["requested_finance_decision"]["budget_period"],
        invoice_evidence_refs=tuple(invoice_refs),
        blocked_dollar_claims=tuple(item["claim"] for item in spend_packet["blocked_claims"]),
        finance_owner=owners.get("Finance", {}).get("review_area"),
        procurement_owner=owners.get("Procurement", {}).get("review_area"),
        approves_spend=spend_packet["safety_state"]["spend_approved"],
        selects_provider=spend_packet["safety_state"]["provider_winner_selected"],
        guarantees_savings=spend_packet["safety_state"]["savings_guaranteed"],
    )


def _step_io(provider: str, adapter: dict[str, Any], packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if provider == "tavily":
        return (
            {"missing_proof": packet["missing_proof"], "blocked_claims": packet["blocked_claims"]},
            {"evidence_candidates": adapter["evidence_candidates"]},
        )
    if provider == "composio":
        return (
            {"tool_access_plan": packet["tool_access_plan"]},
            {"action_plans": adapter["action_plans"]},
        )
    if provider == "openclaw":
        return (
            {"packet_id": packet["packet_id"], "safety_state": packet["safety_state"]},
            {"trace_steps": adapter["trace_steps"]},
        )
    return (
        {
            "decision": packet["decision"],
            "approval_posture": packet["approval_posture"],
            "safety_state": packet["safety_state"],
        },
        {"narration": adapter["narration"], "locked_fields": adapter["reviewer_narration_contract"]["locked_fields"]},
    )


def _accepted_fields(provider: str) -> tuple[str, ...]:
    return {
        "tavily": ("missing_proof", "blocked_claims"),
        "composio": ("tool_access_plan", "tool_scope"),
        "openclaw": ("packet_id", "safety_state", "sponsor_step_outcomes"),
        "nebius": ("decision.verdict", "decision.review_posture", "safety_state", "blocked_claims"),
    }[provider]


def _rejected_fields(provider: str) -> tuple[str, ...]:
    return {
        "tavily": ("approval_posture", "safety_state", "proof_debt_reduction"),
        "composio": ("approval_granted", "permission_grants", "external_writes"),
        "openclaw": ("approval_granted", "permission_grants", "production_mutation"),
        "nebius": ("verdict_change", "safety_state_change", "policy_gate_override"),
    }[provider]


def _output_summary(provider: str, adapter: dict[str, Any]) -> str:
    if provider == "tavily":
        if adapter.get("status") == "live_evidence_candidates_fetched":
            source_count = sum(len(item.get("source_urls", [])) for item in adapter["evidence_candidates"])
            return (
                f"{source_count} Tavily source candidates fetched across "
                f"{len(adapter['evidence_candidates'])} proof items; no proof debt reduced."
            )
        if adapter.get("live_requested") and adapter.get("fallback_used"):
            return (
                f"{len(adapter['evidence_candidates'])} evidence candidate slots planned after Tavily fallback; "
                "no proof debt reduced."
            )
        return f"{len(adapter['evidence_candidates'])} evidence candidate slots planned; no proof debt reduced."
    if provider == "composio":
        return f"{len(adapter['action_plans'])} dry-run permission plans built; no tool write executed."
    if provider == "openclaw":
        return f"{len(adapter['trace_steps'])} runtime checkpoints traced; blocked/dry-run state preserved."
    return "Reviewer narration prepared from locked packet fields; verdict and safety state unchanged."


def _build_step(
    provider: Literal["tavily", "composio", "openclaw", "nebius"],
    packet: dict[str, Any],
    *,
    scenario_name: str,
    adapter: dict[str, Any] | None = None,
) -> SponsorStep:
    adapter = adapter or build_adapter_result(provider, scenario_name)
    step_input, step_output = _step_io(provider, adapter, packet)
    used_live_key = bool(adapter.get("used_live_key", False))
    fallback_used = bool(adapter.get("fallback_used", not used_live_key))
    return SponsorStep(
        sponsor=provider,
        step_verb=ALLOWED_VERBS_PER_SPONSOR[provider],
        input_hash=_stable_hash(step_input),
        output_hash=_stable_hash(step_output),
        output_summary=_output_summary(provider, adapter),
        accepted_fields=_accepted_fields(provider),
        rejected_fields=_rejected_fields(provider),
        redacted_fields=("api_key", "authorization", "secret", "token"),
        duration_ms=0,
        succeeded=True,
        used_live_key=used_live_key,
        fallback_used=fallback_used,
        would_execute=adapter["would_execute"],
        can_approve_access=adapter["can_approve_access"],
        can_grant_permissions=adapter["can_grant_permissions"],
        can_mutate_external_state=adapter["can_mutate_external_state"],
        human_review_required=adapter["human_review_required"],
    )


def build_sponsor_proof_trace(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    *,
    scenario_name: str = DEFAULT_SCENARIO,
    lane: Literal["access_review", "spend_review", "both"] = "both",
    live_tavily: bool = False,
    tavily_client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Build the canonical sponsor proof trace with deterministic fallback steps."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")
    if lane not in {"access_review", "spend_review", "both"}:
        raise ValueError(f"unknown lane: {lane}")
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path

    packet = build_scenario_packet(scenario_name)
    snapshot = build_packet_authority_snapshot_for_scenario(packet, scenario_name)
    spend_packet = build_spend_review_bundle()["packet"]
    lock = _decision_lock(packet, spend_packet)
    adapters = {
        provider: (
            build_tavily_live_evidence(
                packet,
                scenario_name=scenario_name,
                live_enabled=live_tavily,
                client_factory=tavily_client_factory,
            )
            if provider == "tavily"
            else build_adapter_result(provider, scenario_name)
        )
        for provider in SPONSOR_ORDER
    }
    steps = tuple(
        _build_step(provider, packet, scenario_name=scenario_name, adapter=adapters[provider])
        for provider in SPONSOR_ORDER
    )
    access_block = _access_evidence(packet) if lane in {"access_review", "both"} else None
    spend_block = _spend_evidence(spend_packet) if lane in {"spend_review", "both"} else None
    fallback_used = {step.sponsor: step.fallback_used for step in steps}
    live_proof = {}
    tavily_adapter = adapters["tavily"]
    if tavily_adapter.get("live_requested"):
        live_proof["tavily"] = {
            "schema_version": tavily_adapter["live_evidence_schema_version"],
            "status": tavily_adapter["status"],
            "live_requested": tavily_adapter["live_requested"],
            "live_call_attempted": tavily_adapter["live_call_attempted"],
            "live_call_count": tavily_adapter["live_call_count"],
            "used_live_key": tavily_adapter["used_live_key"],
            "fallback_used": tavily_adapter["fallback_used"],
            "fallback_reason": tavily_adapter["fallback_reason"],
            "evidence_candidates": tavily_adapter["evidence_candidates"],
            "docs_reference": tavily_adapter["docs_reference"],
            "safety_impact": tavily_adapter["safety_impact"],
            "human_review_required": tavily_adapter["human_review_required"],
            "can_approve_access": tavily_adapter["can_approve_access"],
            "can_grant_permissions": tavily_adapter["can_grant_permissions"],
            "can_mutate_external_state": tavily_adapter["can_mutate_external_state"],
        }
        if "live_error" in tavily_adapter:
            live_proof["tavily"]["live_error"] = tavily_adapter["live_error"]

    payload_for_hash = {
        "packet_id": packet["packet_id"],
        "revision_id": snapshot["revision_id"],
        "scenario_name": scenario_name,
        "lane": lane,
        "sponsor_steps": [asdict(step) for step in steps],
        "blocked_actions": _flatten_blocked_actions(packet),
        "access_review_evidence": asdict(access_block) if access_block else None,
        "spend_review_evidence": asdict(spend_block) if spend_block else None,
        "decision_lock_before": asdict(lock),
        "decision_lock_after": asdict(lock),
        "fallback_used": fallback_used,
        "generated_at": SPONSOR_PROOF_TRACE_GENERATED_AT,
        "source_request": _relative(request_path),
    }
    if live_proof:
        payload_for_hash["live_proof"] = live_proof
    digest = _stable_digest(payload_for_hash)
    trace = SponsorProofTrace(
        trace_id=f"ia-sponsor-proof-trace-{request_path.stem}-{digest[:16]}-public-v0",
        content_hash=f"sha256:{digest}",
        packet_id=packet["packet_id"],
        revision_id=snapshot["revision_id"],
        scenario_name=scenario_name,
        lane=lane,
        sponsor_steps=steps,
        blocked_actions=_flatten_blocked_actions(packet),
        access_review_evidence=access_block,
        spend_review_evidence=spend_block,
        decision_lock_before=lock,
        decision_lock_after=lock,
        fallback_used=fallback_used,
    ).to_dict()
    if live_proof:
        trace["live_proof"] = live_proof
    trace["source_artifacts"] = {
        "request": _relative(request_path),
        "packet": f"examples/generated/{request_path.stem}.packet.json",
        "sponsor_readiness": "examples/generated/sponsor_live_readiness.json",
        "sponsor_evidence_replay": f"examples/generated/{request_path.stem}.evidence_replay.json",
        "spend_packet": "examples/generated/ai_spend_budget_overrun.spend_packet.json",
    }
    trace["safety_boundary"] = {
        "approves_access": False,
        "grants_permissions": False,
        "executes_external_writes": False,
        "mutates_production": False,
        "approves_spend": False,
        "selects_provider": False,
        "guarantees_savings": False,
        "requires_human_review": True,
    }
    trace["private_boundary"] = {
        "private_source_exposed": False,
        "principle": "Private engine, public proof.",
    }
    return trace


def render_sponsor_proof_trace_markdown(trace: dict[str, Any]) -> str:
    """Render SponsorProofTrace as compact Markdown."""
    lock = trace["decision_lock_after"]
    safety = trace["safety_boundary"]
    lines = [
        "# Sponsor Proof Trace",
        "",
        "Private engine, public proof.",
        "",
        "Sponsor tools collect proof in locked order. They do not approve, grant, write, spend, or mutate production.",
        "",
        "## Trace Identity",
        "",
        f"- trace_id: `{trace['trace_id']}`",
        f"- packet_id: `{trace['packet_id']}`",
        f"- revision_id: `{trace['revision_id']}`",
        f"- content_hash: `{trace['content_hash']}`",
        f"- scenario: `{trace['scenario_name']}`",
        f"- lane: `{trace['lane']}`",
        "",
        "## Decision Lock",
        "",
        f"- verdict: {lock['verdict']}",
        f"- production access: {lock['production_access']}",
        f"- permission grants: {lock['permission_grants']}",
        f"- external writes: {lock['external_writes']}",
        f"- approval granted: {lock['approval_granted']}",
        f"- spend approved: {lock['spend_approved']}",
        f"- provider winner selected: {lock['provider_winner_selected']}",
        f"- savings guaranteed: {lock['savings_guaranteed']}",
        f"- sponsors can change decision: {lock['can_sponsor_change_decision']}",
        f"- decision lock unchanged: {trace['decision_lock_before'] == trace['decision_lock_after']}",
        "",
        "## Sponsor Steps",
        "",
        "| Order | Sponsor | Verb | Live Key Used | Fallback | Would Execute | Can Approve |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, step in enumerate(trace["sponsor_steps"], start=1):
        lines.append(
            "| {index} | {sponsor} | {verb} | {live} | {fallback} | {execute} | {approve} |".format(
                index=index,
                sponsor=step["sponsor"],
                verb=step["step_verb"],
                live=step["used_live_key"],
                fallback=step["fallback_used"],
                execute=step["would_execute"],
                approve=step["can_approve_access"],
            )
        )

    lines.extend(["", "## Step Summaries", ""])
    for step in trace["sponsor_steps"]:
        lines.append(f"- {step['sponsor']} {step['step_verb']}: {step['output_summary']}")

    live_proof = trace.get("live_proof", {})
    if live_proof:
        lines.extend(["", "## Live Proof Collection", ""])
        for provider, proof in live_proof.items():
            lines.extend(
                [
                    f"- provider: `{provider}`",
                    f"- status: `{proof['status']}`",
                    f"- live call attempted: {proof['live_call_attempted']}",
                    f"- live call count: {proof['live_call_count']}",
                    f"- fallback used: {proof['fallback_used']}",
                    f"- human review required: {proof['human_review_required']}",
                ]
            )
            source_count = sum(len(item.get("source_urls", [])) for item in proof["evidence_candidates"])
            lines.append(f"- source candidates: {source_count}")
            lines.append("")

    access = trace["access_review_evidence"]
    if access:
        lines.extend(
            [
                "",
                "## Access Evidence",
                "",
                f"- requested tools: {', '.join(access['requested_tools'])}",
                f"- blocked actions: {len(access['blocked_actions'])}",
                f"- missing proof: {len(access['missing_proof'])}",
                f"- reviewer owners: {', '.join(access['reviewer_owners'])}",
            ]
        )

    spend = trace["spend_review_evidence"]
    if spend:
        lines.extend(
            [
                "",
                "## Spend Evidence",
                "",
                f"- spend packet: `{spend['packet_id']}`",
                f"- requested budget period: {spend['requested_budget']}",
                f"- invoice evidence refs: {len(spend['invoice_evidence_refs'])}",
                f"- blocked dollar claims: {len(spend['blocked_dollar_claims'])}",
                f"- approves spend: {spend['approves_spend']}",
                f"- selects provider: {spend['selects_provider']}",
                f"- guarantees savings: {spend['guarantees_savings']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            f"- approves access: {safety['approves_access']}",
            f"- grants permissions: {safety['grants_permissions']}",
            f"- executes external writes: {safety['executes_external_writes']}",
            f"- mutates production: {safety['mutates_production']}",
            f"- approves spend: {safety['approves_spend']}",
            f"- selects provider: {safety['selects_provider']}",
            f"- guarantees savings: {safety['guarantees_savings']}",
            f"- requires human review: {safety['requires_human_review']}",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for label, path in trace["source_artifacts"].items():
        lines.append(f"- {label}: `{path}`")
    lines.append("")
    return "\n".join(lines)


def write_sponsor_proof_trace_artifacts(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    output_dir: Path = GENERATED_DIR,
    *,
    scenario_name: str = DEFAULT_SCENARIO,
    lane: Literal["access_review", "spend_review", "both"] = "both",
    live_tavily: bool = False,
) -> list[Path]:
    """Write SponsorProofTrace Markdown and JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = build_sponsor_proof_trace(
        request_path,
        scenario_name=scenario_name,
        lane=lane,
        live_tavily=live_tavily,
    )
    stem = request_path.stem
    trace_md = output_dir / f"{stem}.sponsor_proof_trace.md"
    trace_json = output_dir / f"{stem}.sponsor_proof_trace.json"
    trace_md.write_text(render_sponsor_proof_trace_markdown(trace), encoding="utf-8")
    trace_json.write_text(_pretty_json(trace) + "\n", encoding="utf-8")
    return [trace_md, trace_json]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.sponsor_proof_trace",
        description="Build the canonical sponsor proof trace for a public trial request.",
    )
    parser.add_argument(
        "request_path",
        nargs="?",
        type=Path,
        default=DEFAULT_TRIAL_REQUEST,
        help="Public trial request YAML file.",
    )
    parser.add_argument("--json", action="store_true", help="Print SponsorProofTrace as JSON.")
    parser.add_argument("--no-write", action="store_true", help="Skip writing generated artifacts.")
    parser.add_argument("--output-dir", type=Path, default=GENERATED_DIR, help="Directory for generated artifacts.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default=DEFAULT_SCENARIO)
    parser.add_argument("--lane", choices=("access_review", "spend_review", "both"), default="both")
    parser.add_argument(
        "--live-tavily",
        action="store_true",
        help="Opt in to read-only Tavily evidence collection; requires --no-write or a custom --output-dir.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request_path = args.request_path
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path
    if args.live_tavily and not args.no_write and args.output_dir == GENERATED_DIR:
        print("--live-tavily requires --no-write or a custom --output-dir", file=sys.stderr)
        return 2
    trace = build_sponsor_proof_trace(
        request_path,
        scenario_name=args.scenario,
        lane=args.lane,
        live_tavily=args.live_tavily,
    )
    if not args.no_write:
        paths = write_sponsor_proof_trace_artifacts(
            request_path,
            args.output_dir,
            scenario_name=args.scenario,
            lane=args.lane,
            live_tavily=args.live_tavily,
        )
        if not args.json:
            for path in paths:
                print(_relative(path))
            return 0
    print(_pretty_json(trace) if args.json else render_sponsor_proof_trace_markdown(trace))
    return 0


if __name__ == "__main__":
    sys.exit(main())
