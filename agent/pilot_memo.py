"""Export-ready PilotMemo artifact for design-partner review loops."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .packet_authority import build_packet_authority_snapshot_for_scenario, stable_sha256
from .scenarios import GENERATED_DIR, ROOT_DIR
from .trial import DEFAULT_TRIAL_REQUEST, build_trial_bundle
from .trial_evidence_replay import ADAPTER_PROVIDERS, build_trial_evidence_replay
from .trial_outcome_memo import build_trial_outcome_memo


PILOT_MEMO_SCHEMA_VERSION = "pilot_memo.v0"
PILOT_MEMO_SAFETY_ANCHOR = "IA did not approve. The next human action is named above."
PILOT_MEMO_GENERATED_AT = "2026-06-05T00:00:00Z"

SPONSOR_ROLE_VERBS = {
    "tavily": ("finds", "discovery"),
    "nebius": ("narrates", "narration"),
    "composio": ("simulates", "simulation"),
    "openclaw": ("traces", "observation"),
}


@dataclass(frozen=True)
class PacketRef:
    packet_id: str
    revision_id: str
    content_hash: str
    packet_artifact: str

    def to_dict(self) -> dict[str, str]:
        return {
            "packet_id": self.packet_id,
            "revision_id": self.revision_id,
            "content_hash": self.content_hash,
            "packet_artifact": self.packet_artifact,
        }


@dataclass(frozen=True)
class SponsorContribution:
    provider: str
    verb: str
    role: str
    proof_type: str
    contribution: str
    human_review_required: bool
    can_change_decision: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "verb": self.verb,
            "role": self.role,
            "proof_type": self.proof_type,
            "contribution": self.contribution,
            "human_review_required": self.human_review_required,
            "can_change_decision": self.can_change_decision,
        }


@dataclass(frozen=True)
class ReviewerGate:
    owner: str
    decision_needed: str
    blocks: str
    required_before: str

    def to_dict(self) -> dict[str, str]:
        return {
            "owner": self.owner,
            "decision_needed": self.decision_needed,
            "blocks": self.blocks,
            "required_before": self.required_before,
        }


@dataclass(frozen=True)
class PilotMemo:
    memo_id: str
    packet_reference: PacketRef
    verdict_class: str
    sponsor_contributions: tuple[SponsorContribution, ...]
    reviewer_routing: tuple[ReviewerGate, ...]
    blocked_claims: tuple[str, ...]
    missing_proof: tuple[str, ...]
    next_human_action: str
    artifact_stem: str
    safety_anchor: str = PILOT_MEMO_SAFETY_ANCHOR
    generated_at: str = PILOT_MEMO_GENERATED_AT
    schema_version: str = PILOT_MEMO_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "memo_id": self.memo_id,
            "generated_by": "inferenceatlas-agent-demo",
            "mode": "offline_deterministic",
            "packet_reference": self.packet_reference.to_dict(),
            "verdict_class": self.verdict_class,
            "sponsor_contributions": [item.to_dict() for item in self.sponsor_contributions],
            "reviewer_routing": [item.to_dict() for item in self.reviewer_routing],
            "blocked_claims": list(self.blocked_claims),
            "missing_proof": list(self.missing_proof),
            "next_human_action": self.next_human_action,
            "safety_anchor": self.safety_anchor,
            "generated_at": self.generated_at,
            "export_variants": {
                "copy_review_brief": {
                    "format": "markdown",
                    "artifact": f"examples/generated/{self.artifact_stem}.copy_review_brief.md",
                },
                "export_pilot_memo": {
                    "formats": ["json", "markdown"],
                    "artifacts": [
                        f"examples/generated/{self.artifact_stem}.pilot_memo.json",
                        f"examples/generated/{self.artifact_stem}.pilot_memo.md",
                    ],
                },
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


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _unique(values: list[str]) -> tuple[str, ...]:
    seen = set()
    output = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)


def _without_terminal_punctuation(value: str) -> str:
    return value.rstrip().rstrip(".!?")


def _packet_reference(packet: dict[str, Any], artifact_stem: str) -> PacketRef:
    snapshot = build_packet_authority_snapshot_for_scenario(packet, artifact_stem)
    return PacketRef(
        packet_id=snapshot["packet_id"],
        revision_id=snapshot["revision_id"],
        content_hash=snapshot["content_hash"],
        packet_artifact=f"examples/generated/{artifact_stem}.packet.json",
    )


def _sponsor_contributions(replay: dict[str, Any]) -> tuple[SponsorContribution, ...]:
    by_provider = replay["sponsor_replay"]
    contributions = []
    for provider in ADAPTER_PROVIDERS:
        provider_replay = by_provider[provider]
        verb, role = SPONSOR_ROLE_VERBS[provider]
        contributions.append(
            SponsorContribution(
                provider=provider,
                verb=verb,
                role=role,
                proof_type=provider_replay["proof_pack_type"],
                contribution=provider_replay["value_added"],
                human_review_required=provider_replay["human_review_required"],
                can_change_decision=False,
            )
        )
    return tuple(contributions)


def _reviewer_gates(outcome_memo: dict[str, Any]) -> tuple[ReviewerGate, ...]:
    return tuple(
        ReviewerGate(
            owner=item["owner"],
            decision_needed=item["decision_needed"],
            blocks=item["blocks"],
            required_before=item["required_before"],
        )
        for item in outcome_memo["reviewer_routes"]
    )


def _memo_payload_without_id(
    *,
    packet_reference: PacketRef,
    verdict_class: str,
    sponsor_contributions: tuple[SponsorContribution, ...],
    reviewer_routing: tuple[ReviewerGate, ...],
    blocked_claims: tuple[str, ...],
    missing_proof: tuple[str, ...],
    next_human_action: str,
) -> dict[str, Any]:
    return {
        "schema_version": PILOT_MEMO_SCHEMA_VERSION,
        "packet_reference": packet_reference.to_dict(),
        "verdict_class": verdict_class,
        "sponsor_contributions": [item.to_dict() for item in sponsor_contributions],
        "reviewer_routing": [item.to_dict() for item in reviewer_routing],
        "blocked_claims": list(blocked_claims),
        "missing_proof": list(missing_proof),
        "next_human_action": next_human_action,
        "safety_anchor": PILOT_MEMO_SAFETY_ANCHOR,
        "generated_at": PILOT_MEMO_GENERATED_AT,
    }


def build_pilot_memo(request_path: Path = DEFAULT_TRIAL_REQUEST) -> dict[str, Any]:
    """Build a hash-pinned, export-ready pilot memo from a public trial request."""
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path

    bundle = build_trial_bundle(request_path)
    outcome_memo = build_trial_outcome_memo(request_path)
    replay = build_trial_evidence_replay(request_path)
    packet_reference = _packet_reference(bundle["packet"], request_path.stem)
    sponsor_contributions = _sponsor_contributions(replay)
    reviewer_routing = _reviewer_gates(outcome_memo)
    blocked_claims = _unique([item["claim"] for item in bundle["report"]["proof_debt"]["derived_blocked_claims"]])
    missing_proof = _unique([item["proof_needed"] for item in outcome_memo["proof_debt_assignments"]])
    next_human_action = outcome_memo["next_validation"]["recommended_step"]
    verdict_class = outcome_memo["decision"]["code"]
    payload = _memo_payload_without_id(
        packet_reference=packet_reference,
        verdict_class=verdict_class,
        sponsor_contributions=sponsor_contributions,
        reviewer_routing=reviewer_routing,
        blocked_claims=blocked_claims,
        missing_proof=missing_proof,
        next_human_action=next_human_action,
    )
    digest = stable_sha256(payload)
    memo = PilotMemo(
        memo_id=f"ia-pilot-memo-{request_path.stem}-{digest[:16]}-public-v0",
        packet_reference=packet_reference,
        verdict_class=verdict_class,
        sponsor_contributions=sponsor_contributions,
        reviewer_routing=reviewer_routing,
        blocked_claims=blocked_claims,
        missing_proof=missing_proof,
        next_human_action=next_human_action,
        artifact_stem=request_path.stem,
    )
    return memo.to_dict()


def render_copy_review_brief(memo: dict[str, Any]) -> str:
    """Render the short markdown a buyer can paste into Slack or email."""
    packet = memo["packet_reference"]
    sponsors = ", ".join(
        f"{item['provider']} {item['verb']} {item['role']}" for item in memo["sponsor_contributions"]
    )
    blocked = "; ".join(_without_terminal_punctuation(item) for item in memo["blocked_claims"][:2])
    proof = "; ".join(_without_terminal_punctuation(item) for item in memo["missing_proof"][:2])
    return "\n".join(
        [
            "# Copy Review Brief",
            "",
            f"Pilot memo `{memo['memo_id']}` references packet `{packet['packet_id']}` at `{packet['revision_id']}` "
            f"with `{packet['content_hash']}`.",
            "",
            f"Verdict class: `{memo['verdict_class']}`. Next human action: {memo['next_human_action']}",
            "",
            f"Sponsor proof roles: {sponsors}. Sponsors contribute proof only; they do not approve, grant, execute, or mutate.",
            "",
            f"Blocked claims: {blocked}. Missing proof: {proof}.",
            "",
            memo["safety_anchor"],
            "",
        ]
    )


def render_pilot_memo_markdown(memo: dict[str, Any]) -> str:
    """Render the full export-ready PilotMemo as Markdown."""
    packet = memo["packet_reference"]
    safety = memo["safety_boundary"]
    lines = [
        "# Pilot Memo",
        "",
        "Private engine, public proof.",
        "",
        "This memo packages one packet reference, sponsor proof roles, reviewer routing, blocked claims, and missing proof into a buyer-carried pilot artifact.",
        "",
        "## Packet Reference",
        "",
        f"- memo_id: `{memo['memo_id']}`",
        f"- packet_id: `{packet['packet_id']}`",
        f"- revision_id: `{packet['revision_id']}`",
        f"- content_hash: `{packet['content_hash']}`",
        f"- packet artifact: `{packet['packet_artifact']}`",
        "",
        "## Decision",
        "",
        f"- verdict class: {memo['verdict_class']}",
        f"- next human action: {memo['next_human_action']}",
        f"- safety anchor: {memo['safety_anchor']}",
        "",
        "## Sponsor Contributions",
        "",
        "| Provider | Verb | Role | Proof Type | Human Review | Can Change Decision |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in memo["sponsor_contributions"]:
        lines.append(
            "| {provider} | {verb} | {role} | {proof_type} | {review} | {change} |".format(
                provider=item["provider"],
                verb=item["verb"],
                role=item["role"],
                proof_type=item["proof_type"],
                review=item["human_review_required"],
                change=item["can_change_decision"],
            )
        )

    lines.extend(
        [
            "",
            "## Reviewer Routing",
            "",
            "| Owner | Decision Needed | Blocks | Required Before |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in memo["reviewer_routing"]:
        lines.append(
            "| {owner} | {decision_needed} | {blocks} | {required_before} |".format(
                owner=item["owner"],
                decision_needed=item["decision_needed"],
                blocks=item["blocks"],
                required_before=item["required_before"],
            )
        )

    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {claim}" for claim in memo["blocked_claims"])
    lines.extend(["", "## Missing Proof", ""])
    lines.extend(f"- {proof}" for proof in memo["missing_proof"])
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
            "## Export Variants",
            "",
            f"- copy review brief: `{memo['export_variants']['copy_review_brief']['artifact']}`",
            "- export pilot memo: `examples/generated/support_triage_trial.pilot_memo.json`, `examples/generated/support_triage_trial.pilot_memo.md`",
            "",
        ]
    )
    return "\n".join(lines)


def write_pilot_memo_artifacts(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    output_dir: Path = GENERATED_DIR,
) -> list[Path]:
    """Write the export-ready PilotMemo JSON, Markdown, and copy brief."""
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path
    output_dir.mkdir(parents=True, exist_ok=True)
    memo = build_pilot_memo(request_path)
    stem = request_path.stem
    memo_json = output_dir / f"{stem}.pilot_memo.json"
    memo_md = output_dir / f"{stem}.pilot_memo.md"
    copy_brief_md = output_dir / f"{stem}.copy_review_brief.md"

    memo_json.write_text(_pretty_json(memo) + "\n", encoding="utf-8")
    memo_md.write_text(render_pilot_memo_markdown(memo), encoding="utf-8")
    copy_brief_md.write_text(render_copy_review_brief(memo), encoding="utf-8")
    return [memo_json, memo_md, copy_brief_md]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.pilot_memo",
        description="Export a public design-partner PilotMemo from a trial request.",
    )
    parser.add_argument(
        "request_path",
        nargs="?",
        type=Path,
        default=DEFAULT_TRIAL_REQUEST,
        help="Public trial request YAML file.",
    )
    parser.add_argument("--json", action="store_true", help="Print the PilotMemo as machine-readable JSON.")
    parser.add_argument("--copy", action="store_true", help="Print the short copy-review brief.")
    parser.add_argument("--no-write", action="store_true", help="Skip writing generated memo artifacts.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory for generated PilotMemo artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request_path = args.request_path
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path

    memo = build_pilot_memo(request_path)
    if not args.no_write:
        paths = write_pilot_memo_artifacts(request_path, args.output_dir)
        if not args.json and not args.copy:
            for path in paths:
                print(_relative(path))
            return 0

    if args.json:
        print(_pretty_json(memo))
    elif args.copy:
        print(render_copy_review_brief(memo))
    else:
        print(render_pilot_memo_markdown(memo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
