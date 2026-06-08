"""Sponsor evidence replay for public design-partner trial requests."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from .scenarios import GENERATED_DIR, ROOT_DIR
from .trial import DEFAULT_TRIAL_REQUEST, build_trial_bundle
from .trial_outcome_memo import build_trial_outcome_memo


TRIAL_EVIDENCE_REPLAY_SCHEMA_VERSION = "design_partner_evidence_replay.v0"
ADAPTER_PROVIDERS = ("tavily", "composio", "nebius", "openclaw")
DEFAULT_REHEARSAL_EVIDENCE_DIR = ROOT_DIR / "examples" / "evidence" / "support_triage_trial"
SENSITIVE_EVIDENCE_KEY_TERMS = (
    "api_key",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)
UNSAFE_TRUE_FIELDS = {
    "approves_access",
    "approval_granted",
    "can_approve_access",
    "can_grant_permissions",
    "can_mutate_external_state",
    "can_reduce_proof_debt",
    "can_reduce_proof_debt_automatically",
    "can_sponsor_change_decision",
    "executes_external_writes",
    "external_writes_enabled",
    "external_writes",
    "grants_permissions",
    "mutates_production",
    "permission_grants",
    "production_access",
    "would_execute",
}
UNSAFE_REHEARSAL_TEXT = (
    "approved",
    "looks fine",
    "should be ok",
    "should be okay",
)


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled", "allowed"}
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value) if value is not None else False


def _assert_rehearsal_safe(value: Any, *, source: str, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = key.lower()
            if any(term in lowered for term in SENSITIVE_EVIDENCE_KEY_TERMS):
                raise ValueError(f"rehearsal evidence contains sensitive key {path}.{key} in {source}")
            if lowered in UNSAFE_TRUE_FIELDS and _truthy(nested):
                raise ValueError(f"rehearsal evidence attempts unsafe field {path}.{key}=true in {source}")
            _assert_rehearsal_safe(nested, source=source, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_rehearsal_safe(nested, source=source, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        for phrase in UNSAFE_REHEARSAL_TEXT:
            if phrase in lowered:
                raise ValueError(f"rehearsal evidence contains unsafe narration phrase {phrase!r} in {source}")


def _load_rehearsal_evidence(evidence_dir: Path | None) -> dict[str, dict[str, Any]]:
    if evidence_dir is None:
        return {}
    if not evidence_dir.is_absolute():
        evidence_dir = ROOT_DIR / evidence_dir
    if not evidence_dir.is_dir():
        raise FileNotFoundError(f"evidence directory not found: {evidence_dir}")

    evidence: dict[str, dict[str, Any]] = {}
    for provider in ADAPTER_PROVIDERS:
        path = evidence_dir / f"{provider}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("provider", provider) != provider:
            raise ValueError(f"{path} provider must be {provider}")
        _assert_rehearsal_safe(payload, source=_relative(path))
        evidence[provider] = payload
    if not evidence:
        raise ValueError(f"evidence directory has no known provider JSON files: {evidence_dir}")
    return evidence


def _count_rehearsal_items(payload: dict[str, Any]) -> int:
    for key in ("evidence_candidates", "permission_diffs", "narrations", "trace_checkpoints"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return 1


def _provider_boundary(provider: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "mode": "offline_dry_run_replay",
        "requires_api_key": False,
        "live_call_made": False,
        "would_execute": False,
        "can_approve_access": False,
        "can_grant_permissions": False,
        "can_mutate_external_state": False,
        "can_reduce_proof_debt_automatically": False,
        "human_review_required": True,
    }


def _tavily_replay(report: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for proof in report["proof_debt"]["derived_missing_proof"]:
        candidates.append(
            {
                "owner": proof["owner"],
                "proof_needed": proof["item"],
                "planned_query": f"{proof['item']} policy evidence",
                "evidence_type": "policy_or_control_evidence",
                "source_urls": [],
                "freshness": "not_fetched_in_offline_mode",
                "unblocks": proof["unblocks"],
                "can_reduce_proof_debt": False,
                "human_review_required": True,
            }
        )
    return {
        **_provider_boundary("tavily"),
        "proof_pack_type": "evidence_candidate_plan",
        "value_added": "Turns missing proof into source-backed evidence slots for human reviewers.",
        "attachments": candidates,
    }


def _composio_replay(packet: dict[str, Any]) -> dict[str, Any]:
    diffs = []
    for tool_name, plan in packet["tool_access_plan"].items():
        diffs.append(
            {
                "tool": tool_name,
                "requested": plan["requested"],
                "validation_allowance": plan["demo_allowance"],
                "blocked_actions": plan["blocked_actions"],
                "required_proof": plan["required_proof"],
                "would_execute": False,
                "writes_default": "blocked",
                "can_grant_permissions": False,
            }
        )
    return {
        **_provider_boundary("composio"),
        "proof_pack_type": "permission_diff",
        "value_added": "Shows requested tool actions, validation-only allowances, blocked actions, and required proof.",
        "attachments": diffs,
    }


def _nebius_replay(memo: dict[str, Any]) -> dict[str, Any]:
    decision = memo["decision"]
    return {
        **_provider_boundary("nebius"),
        "proof_pack_type": "locked_field_narration",
        "value_added": (
            "Drafts reviewer-facing language from locked fields. IA does not approve this request. "
            "Human review is required before any access, spend, or production movement."
        ),
        "attachments": [
            {
                "memo_section": "Decision",
                "draft_purpose": "reviewer_ready_summary",
                "locked_fields": [
                    "decision.code",
                    "decision.production_access",
                    "decision.permission_grants",
                    "decision.external_writes",
                    "safety_boundary",
                ],
                "locked_values": {
                    "decision_code": decision["code"],
                    "production_access": decision["production_access"],
                    "permission_grants": decision["permission_grants"],
                    "external_writes": decision["external_writes"],
                },
                "llm_can_edit": ["summary language", "meeting close wording"],
                "llm_must_not_edit": ["verdict", "blocked scope", "safety boundary"],
                "human_review_required": True,
            }
        ],
    }


def _openclaw_replay(report: dict[str, Any], memo: dict[str, Any]) -> dict[str, Any]:
    lane = report["access_speed_lane"]["lane"]
    decision = memo["decision"]["code"]
    return {
        **_provider_boundary("openclaw"),
        "proof_pack_type": "runtime_trace_plan",
        "value_added": "Shows the runtime trace that would be recorded around the same blocked and dry-run decisions.",
        "attachments": [
            {
                "step": "load_public_trial_request",
                "outcome": report["request_readiness"],
                "policy_decision": "inspect_only",
                "would_execute": False,
            },
            {
                "step": "derive_packet_and_brief",
                "outcome": lane,
                "policy_decision": "pre_permission_review",
                "would_execute": False,
            },
            {
                "step": "emit_outcome_memo",
                "outcome": decision,
                "policy_decision": "human_review_required",
                "would_execute": False,
            },
        ],
    }


def _matches_permission_diff(proof_needed: str, composio: dict[str, Any]) -> list[dict[str, Any]]:
    proof_lower = proof_needed.lower()
    matches = []
    for diff in composio["attachments"]:
        required_proof = [item.lower() for item in diff["required_proof"]]
        if diff["tool"] in proof_lower or any(item in proof_lower for item in required_proof):
            matches.append(
                {
                    "provider": "composio",
                    "proof_type": composio["proof_pack_type"],
                    "support": f"{diff['tool']} permission diff",
                    "human_review_required": True,
                    "can_reduce_proof_debt": False,
                }
            )
    return matches


def _owner_proof_map(memo: dict[str, Any], sponsor_replay: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    mapped = []
    tavily = sponsor_replay["tavily"]
    composio = sponsor_replay["composio"]
    for assignment in memo["proof_debt_assignments"]:
        proof_needed = assignment["proof_needed"]
        tavily_matches = [
            {
                "provider": "tavily",
                "proof_type": tavily["proof_pack_type"],
                "support": candidate["planned_query"],
                "human_review_required": candidate["human_review_required"],
                "can_reduce_proof_debt": candidate["can_reduce_proof_debt"],
                "attached_sanitized_sources": len(candidate.get("source_urls", [])),
            }
            for candidate in tavily["attachments"]
            if candidate["proof_needed"] == proof_needed
        ]
        mapped.append(
            {
                "owner": assignment["owner"],
                "proof_needed": proof_needed,
                "unblocks": assignment["unblocks"],
                "sponsor_support": [
                    *tavily_matches,
                    *_matches_permission_diff(proof_needed, composio),
                    {
                        "provider": "nebius",
                        "proof_type": sponsor_replay["nebius"]["proof_pack_type"],
                        "support": "locked-field reviewer narration for the same proof owner",
                        "human_review_required": True,
                        "can_reduce_proof_debt": False,
                    },
                    {
                        "provider": "openclaw",
                        "proof_type": sponsor_replay["openclaw"]["proof_pack_type"],
                        "support": "runtime trace checkpoint for blocked or dry-run access attempts",
                        "human_review_required": True,
                        "can_reduce_proof_debt": False,
                    },
                ],
            }
        )
    return mapped


def _attach_tavily_evidence(replay: dict[str, Any], payload: dict[str, Any]) -> None:
    by_proof = {
        item.get("proof_needed"): item
        for item in payload.get("evidence_candidates", [])
        if item.get("proof_needed")
    }
    for attachment in replay["attachments"]:
        evidence = by_proof.get(attachment["proof_needed"])
        if not evidence:
            continue
        sources = evidence.get("sources", [])
        attachment["source_urls"] = [source["url"] for source in sources if source.get("url")]
        attachment["freshness"] = evidence.get("freshness", "sanitized_evidence_attached")
        attachment["sanitized_sources"] = sources
        attachment["evidence_attached"] = True


def _attach_composio_evidence(replay: dict[str, Any], payload: dict[str, Any]) -> None:
    by_tool = {
        item.get("tool"): item
        for item in payload.get("permission_diffs", [])
        if item.get("tool")
    }
    for attachment in replay["attachments"]:
        evidence = by_tool.get(attachment["tool"])
        if not evidence:
            continue
        attachment["dry_run_operation_id"] = evidence.get("dry_run_operation_id")
        attachment["requested_scopes"] = evidence.get("requested_scopes", [])
        attachment["sanitized_permission_diff"] = evidence
        attachment["evidence_attached"] = True


def _attach_nebius_evidence(replay: dict[str, Any], payload: dict[str, Any]) -> None:
    narrations = payload.get("narrations", [])
    for attachment in replay["attachments"]:
        attachment["sanitized_reviewer_narration"] = narrations
        attachment["evidence_attached"] = bool(narrations)


def _attach_openclaw_evidence(replay: dict[str, Any], payload: dict[str, Any]) -> None:
    checkpoints = payload.get("trace_checkpoints", [])
    for attachment in replay["attachments"]:
        attachment["sanitized_trace_checkpoints"] = checkpoints
        attachment["evidence_attached"] = bool(checkpoints)


def _attach_rehearsal_evidence(
    sponsor_replay: dict[str, dict[str, Any]],
    rehearsal_evidence: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    replay = copy.deepcopy(sponsor_replay)
    attachers = {
        "tavily": _attach_tavily_evidence,
        "composio": _attach_composio_evidence,
        "nebius": _attach_nebius_evidence,
        "openclaw": _attach_openclaw_evidence,
    }
    for provider, item in replay.items():
        payload = rehearsal_evidence.get(provider)
        item["rehearsal_evidence_attached"] = bool(payload)
        if not payload:
            continue
        item["rehearsal_evidence_summary"] = {
            "schema_version": payload.get("schema_version"),
            "sanitized_from_live_output": payload.get("sanitized_from_live_output", True),
            "item_count": _count_rehearsal_items(payload),
            "source": payload.get("source", "sanitized_provider_fixture"),
        }
        attachers[provider](item, payload)
    return replay


def build_trial_evidence_replay(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    evidence_dir: Path | None = None,
) -> dict[str, Any]:
    """Build an offline sponsor evidence replay for one public trial request."""
    bundle = build_trial_bundle(request_path)
    report = bundle["report"]
    packet = bundle["packet"]
    memo = build_trial_outcome_memo(request_path)
    stem = request_path.stem
    rehearsal_evidence = _load_rehearsal_evidence(evidence_dir)

    sponsor_replay = {
        "tavily": _tavily_replay(report),
        "composio": _composio_replay(packet),
        "nebius": _nebius_replay(memo),
        "openclaw": _openclaw_replay(report, memo),
    }
    sponsor_replay = _attach_rehearsal_evidence(sponsor_replay, rehearsal_evidence)
    owner_map = _owner_proof_map(memo, sponsor_replay)

    return {
        "schema_version": TRIAL_EVIDENCE_REPLAY_SCHEMA_VERSION,
        "evidence_replay_id": f"ia-design-partner-evidence-replay-{stem}-public-v0",
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_dry_run_replay",
        "request_path": report["request_path"],
        "source_artifacts": {
            "trial_report": f"examples/generated/{stem}_report.json",
            "packet": f"examples/generated/{stem}.packet.json",
            "decision_brief": f"examples/generated/{stem}.decision_brief.json",
            "outcome_memo": f"examples/generated/{stem}.outcome_memo.json",
        },
        "decision_lock": {
            "decision_code": memo["decision"]["code"],
            "production_access": memo["decision"]["production_access"],
            "permission_grants": memo["decision"]["permission_grants"],
            "external_writes": memo["decision"]["external_writes"],
            "can_sponsor_change_decision": False,
        },
        "summary": {
            "provider_count": len(sponsor_replay),
            "rehearsal_evidence_provider_count": len(rehearsal_evidence),
            "sanitized_evidence_attached": bool(rehearsal_evidence),
            "decision_locked_after_rehearsal": True,
            "proof_owner_count": len(owner_map),
            "proof_attachment_count": sum(len(item["sponsor_support"]) for item in owner_map),
            "all_non_executing": all(not item["would_execute"] for item in sponsor_replay.values()),
            "all_non_approving": all(not item["can_approve_access"] for item in sponsor_replay.values()),
            "all_non_granting": all(not item["can_grant_permissions"] for item in sponsor_replay.values()),
            "all_non_mutating": all(not item["can_mutate_external_state"] for item in sponsor_replay.values()),
            "all_human_review_required": all(item["human_review_required"] for item in sponsor_replay.values()),
        },
        "live_evidence_rehearsal": {
            "evidence_dir": _relative(evidence_dir) if evidence_dir else None,
            "sanitized_provider_count": len(rehearsal_evidence),
            "providers": sorted(rehearsal_evidence),
            "unsafe_inputs_rejected": True,
            "decision_locked": True,
            "proof_debt_reduction_requires_human_review": True,
        },
        "sponsor_replay": sponsor_replay,
        "owner_proof_map": owner_map,
        "meeting_use": [
            "Start from the Design Partner Outcome Memo decision.",
            "Use Tavily slots to gather source-backed evidence for missing proof.",
            "Use Composio permission diffs to inspect requested tool actions without granting permissions.",
            "Use Nebius only for reviewer-ready narration over locked fields.",
            "Use OpenClaw only to plan runtime trace checkpoints for blocked and dry-run outcomes.",
            "Do not reduce proof debt or expand access until named human reviewers approve it.",
        ],
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


def render_trial_evidence_replay_markdown(replay: dict[str, Any]) -> str:
    """Render the sponsor evidence replay as Markdown."""
    summary = replay["summary"]
    decision = replay["decision_lock"]
    rehearsal = replay["live_evidence_rehearsal"]
    safety = replay["safety_boundary"]
    lines = [
        f"# Sponsor Evidence Replay: {Path(replay['request_path']).stem}",
        "",
        "Private engine, public proof.",
        "",
        "This replay shows where sponsor proof attaches to a design-partner trial decision without changing the verdict or executing live actions.",
        "",
        "## Decision Lock",
        "",
        f"- decision: {decision['decision_code']}",
        f"- production access: {decision['production_access']}",
        f"- permission grants: {decision['permission_grants']}",
        f"- external writes: {decision['external_writes']}",
        f"- sponsors can change decision: {decision['can_sponsor_change_decision']}",
        "",
        "## Summary",
        "",
        f"- providers: {summary['provider_count']}",
        f"- proof owners: {summary['proof_owner_count']}",
        f"- proof attachments: {summary['proof_attachment_count']}",
        f"- all non-executing: {summary['all_non_executing']}",
        f"- all non-approving: {summary['all_non_approving']}",
        f"- all non-granting: {summary['all_non_granting']}",
        f"- all non-mutating: {summary['all_non_mutating']}",
        f"- all human review required: {summary['all_human_review_required']}",
        "",
        "## Provider Replay",
        "",
        "| Provider | Proof Pack | Attachments | Evidence Attached | Can Approve | Would Execute |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for provider, item in replay["sponsor_replay"].items():
        lines.append(
            "| {provider} | {proof} | {count} | {attached} | {approve} | {execute} |".format(
                provider=provider,
                proof=item["proof_pack_type"],
                count=len(item["attachments"]),
                attached=item["rehearsal_evidence_attached"],
                approve=item["can_approve_access"],
                execute=item["would_execute"],
            )
        )

    if rehearsal["sanitized_provider_count"]:
        lines.extend(
            [
                "",
                "## Live Evidence Rehearsal",
                "",
                f"- evidence dir: `{rehearsal['evidence_dir']}`",
                f"- sanitized providers: {rehearsal['sanitized_provider_count']}",
                f"- providers: {', '.join(rehearsal['providers'])}",
                f"- unsafe inputs rejected: {rehearsal['unsafe_inputs_rejected']}",
                f"- decision locked: {rehearsal['decision_locked']}",
                f"- proof debt reduction requires human review: {rehearsal['proof_debt_reduction_requires_human_review']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Owner Proof Map",
            "",
            "| Owner | Proof Needed | Sponsor Support | Unblocks |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in replay["owner_proof_map"]:
        support = "; ".join(
            f"{support['provider']}:{support['proof_type']}"
            for support in item["sponsor_support"]
        )
        lines.append(
            "| {owner} | {proof_needed} | {support} | {unblocks} |".format(
                owner=item["owner"],
                proof_needed=item["proof_needed"],
                support=support,
                unblocks=item["unblocks"],
            )
        )

    lines.extend(["", "## Meeting Use", ""])
    for item in replay["meeting_use"]:
        lines.append(f"- {item}")

    lines.extend(
        [
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
            f"- trial report: `{replay['source_artifacts']['trial_report']}`",
            f"- packet: `{replay['source_artifacts']['packet']}`",
            f"- decision brief: `{replay['source_artifacts']['decision_brief']}`",
            f"- outcome memo: `{replay['source_artifacts']['outcome_memo']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trial_evidence_replay_artifacts(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    output_dir: Path = GENERATED_DIR,
    evidence_dir: Path | None = None,
) -> list[Path]:
    """Write the sponsor evidence replay for one public trial request."""
    output_dir.mkdir(parents=True, exist_ok=True)
    replay = build_trial_evidence_replay(request_path, evidence_dir)
    stem = request_path.stem
    replay_md = output_dir / f"{stem}.evidence_replay.md"
    replay_json = output_dir / f"{stem}.evidence_replay.json"

    replay_md.write_text(render_trial_evidence_replay_markdown(replay), encoding="utf-8")
    replay_json.write_text(_pretty_json(replay) + "\n", encoding="utf-8")
    return [replay_md, replay_json]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.trial_evidence_replay",
        description="Replay dry-run sponsor evidence against a public design-partner trial request.",
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
        help="Print the evidence replay as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing generated evidence replay artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory for generated evidence replay artifacts.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Directory of sanitized provider JSON outputs to rehearse against the locked decision.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request_path = args.request_path
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path
    evidence_dir = args.evidence_dir
    if evidence_dir is not None and not evidence_dir.is_absolute():
        evidence_dir = ROOT_DIR / evidence_dir

    replay = build_trial_evidence_replay(request_path, evidence_dir)
    if not args.no_write:
        paths = write_trial_evidence_replay_artifacts(request_path, args.output_dir, evidence_dir)
        if not args.json:
            for path in paths:
                print(_relative(path))
            return 0

    print(_pretty_json(replay) if args.json else render_trial_evidence_replay_markdown(replay))
    return 0


if __name__ == "__main__":
    sys.exit(main())
