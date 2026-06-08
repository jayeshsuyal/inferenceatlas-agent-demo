"""Backend sponsor proof collector run over packet-authority surfaces.

The collector is intentionally narrow: it orchestrates existing public proof
surfaces and returns one deterministic run object. It does not call live sponsor
APIs, approve access, approve spend, grant permissions, write to downstream
systems, or mutate packets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Literal

from .packet_advisor import DEFAULT_SPEND_SUBSCRIBER, build_packet_advisor_answer
from .packet_authority import build_packet_authority_snapshot_for_scenario
from .portkey_adapter import DEFAULT_FIXTURE as DEFAULT_DOWNSTREAM_FIXTURE
from .portkey_adapter import build_portkey_adapter_payload
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_packet
from .sponsor_proof_trace import DEFAULT_SCENARIO, SPONSOR_ORDER, build_sponsor_proof_trace
from .trial import DEFAULT_TRIAL_REQUEST
from .trial_outcome_memo import build_trial_outcome_memo


SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION = "sponsor_proof_collector_run.v0"
SPONSOR_PROOF_COLLECTOR_GENERATED_AT = "2026-06-07T00:00:00Z"
DEFAULT_QUESTION = "Can Portkey allow this spend?"

Lane = Literal["access_review", "spend_review", "both"]


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _public_dict(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_public_dict(item) for item in value]
    if isinstance(value, list):
        return [_public_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _public_dict(item) for key, item in value.items()}
    return value


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(_public_dict(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_request_path(request_path: Path) -> Path:
    return request_path if request_path.is_absolute() else ROOT_DIR / request_path


def _collector_steps(trace: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for order, step in enumerate(trace["sponsor_steps"], start=1):
        steps.append(
            {
                "order": order,
                "sponsor": step["sponsor"],
                "status": "completed_fallback" if step["fallback_used"] else "completed_live",
                "verb": step["step_verb"],
                "output_summary": step["output_summary"],
                "output_hash": step["output_hash"],
                "accepted_fields": list(step["accepted_fields"]),
                "rejected_fields": list(step["rejected_fields"]),
                "redacted_fields": list(step["redacted_fields"]),
                "used_live_key": step["used_live_key"],
                "fallback_used": step["fallback_used"],
                "would_execute": step["would_execute"],
                "can_approve_access": step["can_approve_access"],
                "can_grant_permissions": step["can_grant_permissions"],
                "can_mutate_external_state": step["can_mutate_external_state"],
                "human_review_required": step["human_review_required"],
            }
        )
    return steps


def _safety_boundary(trace: dict[str, Any], portkey: dict[str, Any]) -> dict[str, bool]:
    trace_safety = trace["safety_boundary"]
    portkey_invariants = portkey["invariants"]
    return {
        "read_only": True,
        "live_calls_made": any(step["used_live_key"] for step in trace["sponsor_steps"]),
        "approves_access": trace_safety["approves_access"],
        "grants_permissions": trace_safety["grants_permissions"],
        "executes_external_writes": trace_safety["executes_external_writes"],
        "mutates_production": trace_safety["mutates_production"],
        "approves_spend": portkey_invariants["approves_spend"],
        "selects_provider": portkey_invariants["selects_provider"],
        "guarantees_savings": portkey_invariants["guarantees_savings"],
        "requires_human_review": trace_safety["requires_human_review"],
    }


def _invariants(trace: dict[str, Any], steps: list[dict[str, Any]], portkey: dict[str, Any]) -> dict[str, bool]:
    return {
        "sponsor_order_locked": tuple(step["sponsor"] for step in steps) == SPONSOR_ORDER,
        "decision_lock_unchanged": trace["decision_lock_before"] == trace["decision_lock_after"],
        "fallback_shape_available": all(step["fallback_used"] for step in steps),
        "raw_agent_intent_trusted": False,
        "packet_mutation_allowed": False,
        "external_writes_enabled": False,
        "portkey_api_call_made": portkey["api_call_made"],
        "downstream_can_override_packet": False,
    }


def build_sponsor_proof_collector_run(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    *,
    scenario_name: str = DEFAULT_SCENARIO,
    lane: Lane = "both",
    downstream_fixture: str = DEFAULT_DOWNSTREAM_FIXTURE,
    question: str = DEFAULT_QUESTION,
    subscriber: str = DEFAULT_SPEND_SUBSCRIBER,
    live_tavily: bool = False,
) -> dict[str, Any]:
    """Build one deterministic sponsor proof collector run.

    The run is an orchestration artifact: SponsorProofTrace supplies sponsor
    proof, Packet Advisor supplies the human-facing answer, and Portkey adapter
    supplies the downstream dry-run preview.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")
    if lane not in {"access_review", "spend_review", "both"}:
        raise ValueError(f"unknown lane: {lane}")

    request_path = _resolve_request_path(request_path)
    trace = build_sponsor_proof_trace(
        request_path,
        scenario_name=scenario_name,
        lane=lane,
        live_tavily=live_tavily,
    )
    packet_snapshot = build_packet_authority_snapshot_for_scenario(
        build_scenario_packet(scenario_name),
        scenario_name,
    )
    advisor = build_packet_advisor_answer(
        fixture=downstream_fixture,
        subscriber=subscriber,
        question=question,
    )
    portkey = build_portkey_adapter_payload(fixture=downstream_fixture, mode="dry-run")
    outcome_memo = build_trial_outcome_memo(request_path)
    steps = _collector_steps(trace)
    safety = _safety_boundary(trace, portkey)
    invariants = _invariants(trace, steps, portkey)

    run_hash_input = {
        "schema_version": SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION,
        "trace_id": trace["trace_id"],
        "trace_hash": trace["content_hash"],
        "packet": {
            "packet_id": packet_snapshot["packet_id"],
            "revision_id": packet_snapshot["revision_id"],
            "content_hash": packet_snapshot["content_hash"],
        },
        "advisor_packet": advisor["packet_reference"],
        "portkey_packet": portkey["ia_packet_reference"],
        "scenario_name": scenario_name,
        "lane": lane,
        "question": question,
        "subscriber": subscriber,
        "downstream_fixture": downstream_fixture,
    }
    if live_tavily:
        run_hash_input["live_tavily"] = trace.get("live_proof", {}).get("tavily", {})
    digest = _stable_digest(run_hash_input)

    run = {
        "schema_version": SPONSOR_PROOF_COLLECTOR_SCHEMA_VERSION,
        "run_id": f"ia-sponsor-proof-run-{request_path.stem}-{digest[:16]}-public-v0",
        "content_hash": f"sha256:{digest}",
        "generated_at": SPONSOR_PROOF_COLLECTOR_GENERATED_AT,
        "mode": "live_read_only_evidence" if safety["live_calls_made"] else "offline_dry_run",
        "status": "completed",
        "run_type": "agentic_proof_collection",
        "collector_claim": (
            "The collector gathers sponsor proof and downstream previews; "
            "the IA Packet remains the authority."
        ),
        "request_path": _relative(request_path),
        "scenario_name": scenario_name,
        "lane": lane,
        "packet_reference": {
            "packet_id": packet_snapshot["packet_id"],
            "revision_id": packet_snapshot["revision_id"],
            "content_hash": packet_snapshot["content_hash"],
            "source": "packet_authority_snapshot",
        },
        "trace_reference": {
            "trace_id": trace["trace_id"],
            "content_hash": trace["content_hash"],
            "source": "sponsor_proof_trace",
        },
        "collector_steps": steps,
        "sponsor_proof_trace": trace,
        "packet_advisor_answer": advisor,
        "downstream_previews": {
            "portkey_model_spend_gate": portkey,
        },
        "decision": {
            "next_human_action": outcome_memo["decision"]["recommended_next_step"],
            "meeting_decision": outcome_memo["decision"]["summary"],
            "can_move": list(outcome_memo["can_move"]),
            "stays_blocked": list(outcome_memo["stays_blocked"]),
        },
        "safety_boundary": safety,
        "invariants": invariants,
        "source_surfaces": {
            "request": _relative(request_path),
            "sponsor_proof_trace": "agent.sponsor_proof_trace",
            "packet_advisor": "agent.packet_advisor",
            "portkey_adapter": "agent.portkey_adapter",
            "trial_outcome_memo": "agent.trial_outcome_memo",
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }
    if live_tavily:
        run["live_sponsor_proof"] = {
            "tavily": trace.get("live_proof", {}).get("tavily", {}),
        }
    return run


def render_sponsor_proof_collector_markdown(run: dict[str, Any]) -> str:
    """Render the collector run as compact Markdown."""
    packet = run["packet_reference"]
    safety = run["safety_boundary"]
    portkey = run["downstream_previews"]["portkey_model_spend_gate"]
    decision = run["decision"]
    lines = [
        "# Sponsor Proof Collector Run",
        "",
        "Private engine, public proof.",
        "",
        "The collector gathers proof; it does not approve, grant, write, spend, select providers, or mutate production.",
        "",
        "## Run",
        "",
        f"- run_id: `{run['run_id']}`",
        f"- mode: `{run['mode']}`",
        f"- status: `{run['status']}`",
        f"- scenario: `{run['scenario_name']}`",
        f"- lane: `{run['lane']}`",
        f"- packet_id: `{packet['packet_id']}`",
        f"- revision_id: `{packet['revision_id']}`",
        f"- content_hash: `{packet['content_hash']}`",
        "",
        "## Sponsor Collection",
        "",
        "| Order | Sponsor | Verb | Status | Live Key Used | Fallback | Would Execute | Can Approve |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for step in run["collector_steps"]:
        lines.append(
            "| {order} | {sponsor} | {verb} | {status} | {live} | {fallback} | {execute} | {approve} |".format(
                order=step["order"],
                sponsor=step["sponsor"],
                verb=step["verb"],
                status=step["status"],
                live=step["used_live_key"],
                fallback=step["fallback_used"],
                execute=step["would_execute"],
                approve=step["can_approve_access"],
            )
        )

    live_proof = run.get("live_sponsor_proof", {})
    tavily_proof = live_proof.get("tavily") if live_proof else None
    if tavily_proof:
        source_count = sum(len(item.get("source_urls", [])) for item in tavily_proof["evidence_candidates"])
        lines.extend(
            [
                "",
                "## Live Proof Collection",
                "",
                f"- tavily status: `{tavily_proof['status']}`",
                f"- live call attempted: {tavily_proof['live_call_attempted']}",
                f"- live call count: {tavily_proof['live_call_count']}",
                f"- fallback used: {tavily_proof['fallback_used']}",
                f"- source candidates: {source_count}",
                f"- human review required: {tavily_proof['human_review_required']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Downstream Preview",
            "",
            f"- Portkey mode: `{portkey['mode']}`",
            f"- Portkey API call made: {portkey['api_call_made']}",
            f"- Portkey guardrail verdict: {portkey['portkey_guardrail_response']['verdict']}",
            f"- usage policy credit_limit: {portkey['usage_policy_plan']['request_body']['credit_limit']}",
            "",
            "## Decision",
            "",
            f"- meeting decision: {decision['meeting_decision']}",
            f"- next human action: {decision['next_human_action']}",
            "",
            "## Safety Boundary",
            "",
            f"- read only: {safety['read_only']}",
            f"- live calls made: {safety['live_calls_made']}",
            f"- approves access: {safety['approves_access']}",
            f"- grants permissions: {safety['grants_permissions']}",
            f"- executes external writes: {safety['executes_external_writes']}",
            f"- mutates production: {safety['mutates_production']}",
            f"- approves spend: {safety['approves_spend']}",
            f"- selects provider: {safety['selects_provider']}",
            f"- guarantees savings: {safety['guarantees_savings']}",
            f"- requires human review: {safety['requires_human_review']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_sponsor_proof_collector_artifacts(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    output_dir: Path = GENERATED_DIR,
    *,
    scenario_name: str = DEFAULT_SCENARIO,
    lane: Lane = "both",
    downstream_fixture: str = DEFAULT_DOWNSTREAM_FIXTURE,
    question: str = DEFAULT_QUESTION,
    subscriber: str = DEFAULT_SPEND_SUBSCRIBER,
    live_tavily: bool = False,
) -> list[Path]:
    """Write SponsorProofCollector Markdown and JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    request_path = _resolve_request_path(request_path)
    run = build_sponsor_proof_collector_run(
        request_path,
        scenario_name=scenario_name,
        lane=lane,
        downstream_fixture=downstream_fixture,
        question=question,
        subscriber=subscriber,
        live_tavily=live_tavily,
    )
    stem = request_path.stem
    markdown_path = output_dir / f"{stem}.sponsor_proof_collector.md"
    json_path = output_dir / f"{stem}.sponsor_proof_collector.json"
    markdown_path.write_text(render_sponsor_proof_collector_markdown(run), encoding="utf-8")
    json_path.write_text(_pretty_json(run) + "\n", encoding="utf-8")
    return [markdown_path, json_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.sponsor_proof_collector",
        description="Build one deterministic sponsor proof collector run from public packet surfaces.",
    )
    parser.add_argument(
        "request_path",
        nargs="?",
        type=Path,
        default=DEFAULT_TRIAL_REQUEST,
        help="Public trial request YAML file.",
    )
    parser.add_argument("--json", action="store_true", help="Print the collector run as JSON.")
    parser.add_argument("--no-write", action="store_true", help="Skip writing generated artifacts.")
    parser.add_argument("--output-dir", type=Path, default=GENERATED_DIR, help="Directory for generated artifacts.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default=DEFAULT_SCENARIO)
    parser.add_argument("--lane", choices=("access_review", "spend_review", "both"), default="both")
    parser.add_argument("--downstream-fixture", default=DEFAULT_DOWNSTREAM_FIXTURE)
    parser.add_argument("--subscriber", default=DEFAULT_SPEND_SUBSCRIBER)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--live-tavily",
        action="store_true",
        help="Opt in to read-only Tavily evidence collection; requires --no-write or a custom --output-dir.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    request_path = _resolve_request_path(args.request_path)
    if args.live_tavily and not args.no_write and args.output_dir == GENERATED_DIR:
        print("--live-tavily requires --no-write or a custom --output-dir", file=sys.stderr)
        return 2
    try:
        run = build_sponsor_proof_collector_run(
            request_path,
            scenario_name=args.scenario,
            lane=args.lane,
            downstream_fixture=args.downstream_fixture,
            question=args.question,
            subscriber=args.subscriber,
            live_tavily=args.live_tavily,
        )
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not args.no_write:
        paths = write_sponsor_proof_collector_artifacts(
            request_path,
            args.output_dir,
            scenario_name=args.scenario,
            lane=args.lane,
            downstream_fixture=args.downstream_fixture,
            question=args.question,
            subscriber=args.subscriber,
            live_tavily=args.live_tavily,
        )
        if not args.json:
            for path in paths:
                print(_relative(path))
            return 0
    print(_pretty_json(run) if args.json else render_sponsor_proof_collector_markdown(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
