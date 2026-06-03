"""Packet Outcome Memo projection for human agent-access decisions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .gate import evaluate_gate
from .proof_health import build_proof_health_report
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_brief, build_scenario_packet
from .sponsor_readiness import build_sponsor_live_readiness


OUTCOME_MEMO_SCHEMA_VERSION = "agent_packet_outcome_memo.v0"
OUTCOME_MEMO_ID = "ia-agent-packet-outcome-memo-public-v0"
DEFAULT_SCENARIO = "support_triage_agent"


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _human_decision(brief: dict[str, Any], gate: dict[str, Any]) -> tuple[str, str]:
    if gate["decision"] == "BLOCKED" or not brief["go_no_go"]["scoped_validation_review"]:
        return (
            "blocked_before_validation",
            "Do not move this agent into validation until the blocked gates are resolved.",
        )
    return (
        "scoped_validation_only",
        "Move this agent into scoped validation only; keep production access and external writes blocked.",
    )


def _can_move(brief: dict[str, Any]) -> list[str]:
    if not brief["go_no_go"]["scoped_validation_review"]:
        return ["No validation movement until blocked policy gates are resolved."]
    allowed = brief["access_envelope"]["allowed_for_validation"]
    if allowed:
        return allowed
    return ["No validation movement until blocked policy gates are resolved."]


def _stays_blocked(brief: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    envelope = brief["access_envelope"]
    blocked_claims = [item["claim"] for item in packet["blocked_claims"]]
    blocked = envelope["blocked_in_validation"] + envelope["blocked_before_production"] + blocked_claims
    lowered = " ".join(item.lower() for item in blocked)
    extras = ["production access grant"]
    if "external write" not in lowered and "write action" not in lowered:
        extras.append("external writes")
    if "permission expansion" not in lowered:
        extras.append("permission expansion without a new packet")
    return _unique(blocked + extras)


def _proof_assignments(packet: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "owner": item["owner"],
            "proof_needed": item["item"],
            "unblocks": item["unblocks"],
            "status": "missing",
        }
        for item in packet["missing_proof"]
    ]


def _reviewer_routes(brief: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "owner": item["owner"],
            "decision_needed": item["gate"],
            "blocks": item["blocks"],
            "required_before": item["required_before"],
        }
        for item in brief["reviewer_gates"]
    ]


def _sponsor_slots() -> list[dict[str, str]]:
    readiness = build_sponsor_live_readiness()
    return [
        {
            "provider": provider["provider"],
            "proof_type": provider["proof_pack_type"],
            "where_it_helps": provider["live_value"],
            "authority": "proof_contributor_not_approval_authority",
        }
        for provider in readiness["providers"]
    ]


def build_packet_outcome_memo(scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    """Build a human decision memo from one public packet and brief."""
    if scenario_name not in SCENARIOS:
        raise KeyError(f"unknown scenario: {scenario_name}")

    packet = build_scenario_packet(scenario_name)
    brief = build_scenario_brief(scenario_name)
    gate = evaluate_gate(scenario_name)
    proof_health = build_proof_health_report(scenario_name)
    decision_code, decision_summary = _human_decision(brief, gate)
    can_move = _can_move(brief)
    stays_blocked = _stays_blocked(brief, packet)

    return {
        "schema_version": OUTCOME_MEMO_SCHEMA_VERSION,
        "outcome_memo_id": OUTCOME_MEMO_ID,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_deterministic",
        "scenario": scenario_name,
        "source_artifacts": {
            "packet": f"examples/generated/{scenario_name}.packet.json",
            "decision_brief": f"examples/generated/{scenario_name}.decision_brief.json",
            "proof_health": f"examples/generated/{scenario_name}.proof_health.json",
        },
        "decision": {
            "code": decision_code,
            "summary": decision_summary,
            "policy_gate": gate["decision"],
            "policy_reason": gate["reason"],
            "production_access": brief["go_no_go"]["production_access"],
            "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
            "external_writes": brief["go_no_go"]["external_writes"],
            "composio_dry_run": brief["go_no_go"]["composio_dry_run"],
        },
        "can_move": can_move,
        "stays_blocked": stays_blocked,
        "proof_debt_assignments": _proof_assignments(packet),
        "reviewer_routes": _reviewer_routes(brief),
        "packet_refresh": {
            "status": proof_health["overall_status"],
            "score": proof_health["overall_score"],
            "next_human_health_check": proof_health["next_human_health_check"],
            "refresh_reason": "Packet assumptions, tool scope, data boundaries, and reviewer gates can drift before access expands.",
        },
        "sponsor_proof_slots": _sponsor_slots(),
        "meeting_close": {
            "decision_sentence": decision_summary,
            "blocked_sentence": "Keep blocked items blocked until named proof owners close the proof debt.",
            "refresh_sentence": f"Refresh the packet at {proof_health['next_human_health_check']} before broader validation.",
        },
        "safety_boundary": {
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_production": False,
            "requires_human_review": True,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def _bullets(values: list[str]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {value}" for value in values]


def render_packet_outcome_memo_markdown(memo: dict[str, Any]) -> str:
    """Render a packet outcome memo as Markdown."""
    decision = memo["decision"]
    refresh = memo["packet_refresh"]
    safety = memo["safety_boundary"]
    lines = [
        f"# Packet Outcome Memo: {memo['scenario']}",
        "",
        "Private engine, public proof.",
        "",
        "This memo converts the DecisionPacket into the human decision a CTO, Security lead, or AI platform owner can act on.",
        "",
        "## Decision",
        "",
        f"- outcome: {decision['code']}",
        f"- summary: {decision['summary']}",
        f"- policy gate: {decision['policy_gate']}",
        f"- production access: {decision['production_access']}",
        f"- scoped validation review: {decision['scoped_validation_review']}",
        f"- external writes: {decision['external_writes']}",
        f"- Composio dry-run: {decision['composio_dry_run']}",
        "",
        "## Can Move",
        "",
        *_bullets(memo["can_move"]),
        "",
        "## Stays Blocked",
        "",
        *_bullets(memo["stays_blocked"]),
        "",
        "## Proof Debt Assignments",
        "",
        "| Owner | Proof Needed | Unblocks | Status |",
        "| --- | --- | --- | --- |",
    ]
    for item in memo["proof_debt_assignments"]:
        lines.append(
            "| {owner} | {proof} | {unblocks} | {status} |".format(
                owner=item["owner"],
                proof=item["proof_needed"],
                unblocks=item["unblocks"],
                status=item["status"],
            )
        )

    lines.extend(
        [
            "",
            "## Reviewer Routes",
            "",
            "| Owner | Decision Needed | Blocks | Required Before |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in memo["reviewer_routes"]:
        lines.append(
            "| {owner} | {decision_needed} | {blocks} | {required_before} |".format(
                owner=item["owner"],
                decision_needed=item["decision_needed"],
                blocks=item["blocks"],
                required_before=item["required_before"],
            )
        )

    lines.extend(
        [
            "",
            "## Packet Refresh",
            "",
            f"- status: {refresh['status']}",
            f"- score: {refresh['score']}",
            f"- next human health check: {refresh['next_human_health_check']}",
            f"- reason: {refresh['refresh_reason']}",
            "",
            "## Sponsor Proof Slots",
            "",
            "| Provider | Proof Type | Where It Helps | Authority |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in memo["sponsor_proof_slots"]:
        lines.append(
            "| {provider} | {proof_type} | {where_it_helps} | {authority} |".format(
                provider=item["provider"],
                proof_type=item["proof_type"],
                where_it_helps=item["where_it_helps"],
                authority=item["authority"],
            )
        )

    close = memo["meeting_close"]
    lines.extend(
        [
            "",
            "## Meeting Close",
            "",
            f"- {close['decision_sentence']}",
            f"- {close['blocked_sentence']}",
            f"- {close['refresh_sentence']}",
            "",
            "## Safety Boundary",
            "",
            f"- approves access: {safety['approves_access']}",
            f"- grants permissions: {safety['grants_permissions']}",
            f"- executes external writes: {safety['executes_external_writes']}",
            f"- mutates production: {safety['mutates_production']}",
            f"- requires human review: {safety['requires_human_review']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_packet_outcome_memo_artifacts(
    scenario_name: str = DEFAULT_SCENARIO,
    output_dir: Path = GENERATED_DIR,
) -> list[Path]:
    """Write packet outcome memo Markdown and JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    memo = build_packet_outcome_memo(scenario_name)
    memo_json = output_dir / f"{scenario_name}.outcome_memo.json"
    memo_md = output_dir / f"{scenario_name}.outcome_memo.md"
    memo_json.write_text(_pretty_json(memo) + "\n", encoding="utf-8")
    memo_md.write_text(render_packet_outcome_memo_markdown(memo), encoding="utf-8")
    return [memo_json, memo_md]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.outcome_memo",
        description="Generate the public InferenceAtlas packet outcome memo artifact.",
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default=DEFAULT_SCENARIO,
        help="Scenario to project into an outcome memo.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory where outcome memo artifacts should be written.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the outcome memo as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing artifacts and print only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    memo = build_packet_outcome_memo(args.scenario)

    if not args.no_write:
        for path in write_packet_outcome_memo_artifacts(args.scenario, args.output_dir):
            print(_relative(path))

    if args.json:
        print(_pretty_json(memo))
    elif args.no_write:
        print(render_packet_outcome_memo_markdown(memo))

    return 0


if __name__ == "__main__":
    sys.exit(main())
