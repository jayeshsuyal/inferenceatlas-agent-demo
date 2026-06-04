"""Design-partner outcome memo for public trial requests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .scenarios import GENERATED_DIR, ROOT_DIR
from .trial import DEFAULT_TRIAL_REQUEST, build_trial_bundle


TRIAL_OUTCOME_MEMO_SCHEMA_VERSION = "design_partner_outcome_memo.v0"


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


def _decision(report: dict[str, Any]) -> dict[str, Any]:
    lane = report["access_speed_lane"]
    brief = report["decision_brief_summary"]
    blocked = bool(report["validation"]["errors"]) or lane["lane"] == "blocked_fast"
    if blocked:
        code = "blocked_before_validation"
        summary = "Do not move this agent into validation until the blocked gates are resolved."
    else:
        code = "scoped_validation_only"
        summary = "Move this agent into scoped validation only; keep production access, permission grants, and external writes blocked."

    return {
        "code": code,
        "summary": summary,
        "request_readiness": report["request_readiness"],
        "access_speed_lane": lane["lane"],
        "access_speed_reason": lane["reason"],
        "highest_risk": lane["highest_risk"],
        "recommended_next_step": brief["recommended_next_step"],
        "next_validation": brief["next_validation"],
        "production_access": brief["production_access"],
        "scoped_validation_review": brief["scoped_validation_review"] and not blocked,
        "permission_grants": False,
        "external_writes": False,
    }


def _can_move(report: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    if decision["code"] != "scoped_validation_only":
        return ["No validation movement until blocked policy gates are resolved."]

    return _unique(
        [
            report["decision_brief_summary"]["recommended_next_step"],
            report["access_speed_lane"]["safe_next_step"],
            report["decision_brief_summary"]["next_validation"],
            "Run the validation in dry-run mode with named reviewers and scoped evidence owners.",
        ]
    )


def _stays_blocked(report: dict[str, Any]) -> list[str]:
    blocked_claims = [item["claim"] for item in report["proof_debt"]["derived_blocked_claims"]]
    risk_flags = [
        flag.replace("_", " ")
        for flag in report["requested_risk_flags"]["risk_flags_present"]
    ]
    return _unique(
        [
            "production access grant",
            "permission grants",
            "external writes",
            "admin or broad organization scope",
            "broader validation without a refreshed packet",
            *blocked_claims,
            *risk_flags,
        ]
    )


def _proof_assignments(report: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "owner": item["owner"],
            "proof_needed": item["item"],
            "unblocks": item["unblocks"],
            "status": "missing",
        }
        for item in report["proof_debt"]["derived_missing_proof"]
    ]


def _reviewer_routes(report: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "owner": item["owner"],
            "decision_needed": item["action"],
            "blocks": item["blocks"],
            "required_before": "scoped_validation_or_permission_expansion",
        }
        for item in report["reviewer_routing"]["derived_action_items"]
    ]


def build_trial_outcome_memo(request_path: Path = DEFAULT_TRIAL_REQUEST) -> dict[str, Any]:
    """Build a meeting-ready outcome memo from one public trial request."""
    bundle = build_trial_bundle(request_path)
    report = bundle["report"]
    decision = _decision(report)
    stem = request_path.stem

    return {
        "schema_version": TRIAL_OUTCOME_MEMO_SCHEMA_VERSION,
        "outcome_memo_id": f"ia-design-partner-outcome-memo-{stem}-public-v0",
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_deterministic",
        "request_path": report["request_path"],
        "source_artifacts": {
            "trial_report": f"examples/generated/{stem}_report.json",
            "packet": f"examples/generated/{stem}.packet.json",
            "decision_brief": f"examples/generated/{stem}.decision_brief.json",
        },
        "trial_context": {
            "candidate_agent": report["candidate_agent"],
            "requested_risk_flags": report["requested_risk_flags"],
            "request_readiness": report["request_readiness"],
            "access_speed_lane": report["access_speed_lane"],
        },
        "decision": decision,
        "can_move": _can_move(report, decision),
        "stays_blocked": _stays_blocked(report),
        "proof_debt_assignments": _proof_assignments(report),
        "reviewer_routes": _reviewer_routes(report),
        "next_validation": {
            "recommended_step": report["decision_brief_summary"]["next_validation"],
            "refresh_rule": "Refresh this memo before broader validation, production access, permission expansion, or live external writes.",
            "human_owner": "business_owner_and_required_reviewers",
        },
        "meeting_close": {
            "decision_sentence": decision["summary"],
            "blocked_sentence": "Keep blocked scope blocked until named proof owners close the proof debt.",
            "owner_sentence": "Business owner and required reviewers decide whether scoped validation can proceed.",
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


def render_trial_outcome_memo_markdown(memo: dict[str, Any]) -> str:
    """Render a design-partner outcome memo as Markdown."""
    decision = memo["decision"]
    context = memo["trial_context"]
    safety = memo["safety_boundary"]
    lines = [
        f"# Design Partner Outcome Memo: {Path(memo['request_path']).stem}",
        "",
        "Private engine, public proof.",
        "",
        "This memo converts a public trial request into the meeting decision a CTO, Security lead, or AI platform owner can act on.",
        "",
        "## Request",
        "",
        f"- request: `{memo['request_path']}`",
        f"- candidate agent: {context['candidate_agent']['name']}",
        f"- business owner: {context['candidate_agent']['business_owner']}",
        f"- requested environment: {context['candidate_agent']['requested_environment']}",
        f"- current approval path: {context['candidate_agent']['current_approval_path']}",
        "",
        "## Decision",
        "",
        f"- outcome: {decision['code']}",
        f"- summary: {decision['summary']}",
        f"- access speed lane: {decision['access_speed_lane']}",
        f"- highest risk: {decision['highest_risk']}",
        f"- production access: {decision['production_access']}",
        f"- scoped validation review: {decision['scoped_validation_review']}",
        f"- permission grants: {decision['permission_grants']}",
        f"- external writes: {decision['external_writes']}",
        "",
        "## Can Move",
        "",
        *_bullets(memo["can_move"]),
        "",
        "## Stays Blocked",
        "",
        *_bullets(memo["stays_blocked"]),
        "",
        "## Proof Debt Owners",
        "",
        "| Owner | Proof Needed | Unblocks | Status |",
        "| --- | --- | --- | --- |",
    ]
    for item in memo["proof_debt_assignments"]:
        lines.append(
            "| {owner} | {proof_needed} | {unblocks} | {status} |".format(
                owner=item["owner"],
                proof_needed=item["proof_needed"],
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

    next_validation = memo["next_validation"]
    meeting_close = memo["meeting_close"]
    lines.extend(
        [
            "",
            "## Next Validation",
            "",
            f"- recommended step: {next_validation['recommended_step']}",
            f"- refresh rule: {next_validation['refresh_rule']}",
            f"- human owner: {next_validation['human_owner']}",
            "",
            "## Meeting Close",
            "",
            f"- decision: {meeting_close['decision_sentence']}",
            f"- blocked: {meeting_close['blocked_sentence']}",
            f"- owner: {meeting_close['owner_sentence']}",
            "",
            "## Safety Boundary",
            "",
            f"- approves access: {safety['approves_access']}",
            f"- grants permissions: {safety['grants_permissions']}",
            f"- executes external writes: {safety['executes_external_writes']}",
            f"- mutates production: {safety['mutates_production']}",
            f"- requires human review: {safety['requires_human_review']}",
            "",
            "## Source Artifacts",
            "",
            f"- trial report: `{memo['source_artifacts']['trial_report']}`",
            f"- packet: `{memo['source_artifacts']['packet']}`",
            f"- decision brief: `{memo['source_artifacts']['decision_brief']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trial_outcome_memo_artifacts(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    output_dir: Path = GENERATED_DIR,
) -> list[Path]:
    """Write the design-partner outcome memo for one public trial request."""
    output_dir.mkdir(parents=True, exist_ok=True)
    memo = build_trial_outcome_memo(request_path)
    stem = request_path.stem
    memo_md = output_dir / f"{stem}.outcome_memo.md"
    memo_json = output_dir / f"{stem}.outcome_memo.json"

    memo_md.write_text(render_trial_outcome_memo_markdown(memo), encoding="utf-8")
    memo_json.write_text(_pretty_json(memo) + "\n", encoding="utf-8")
    return [memo_md, memo_json]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.trial_outcome_memo",
        description="Convert a public design-partner trial request into a meeting-ready outcome memo.",
    )
    parser.add_argument(
        "request_path",
        nargs="?",
        type=Path,
        default=DEFAULT_TRIAL_REQUEST,
        help="Public trial request YAML file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the outcome memo as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing generated memo artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory for generated outcome memo artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request_path = args.request_path
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path

    memo = build_trial_outcome_memo(request_path)
    if not args.no_write:
        paths = write_trial_outcome_memo_artifacts(request_path, args.output_dir)
        if not args.json:
            for path in paths:
                print(_relative(path))
            return 0

    print(_pretty_json(memo) if args.json else render_trial_outcome_memo_markdown(memo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
