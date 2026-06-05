"""Downstream subscriber examples for Packet Authority verification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .packet_authority import DEFAULT_SCENARIO
from .scenarios import ROOT_DIR, SCENARIOS, build_scenario_packet
from .verification import build_verification_artifact_for_scenario


SUBSCRIBER_SCHEMA_VERSION = "packet_authority_subscriber.v0"
PACKET_AUTHORITY_SENTENCE = (
    "InferenceAtlas is the packet authority layer upstream of tools, gateways, "
    "spend controls, CI, and human review."
)
PACKET_AUTHORITY_SHORT_SENTENCE = (
    "The packet authority layer downstream systems trust before AI moves."
)
SUBSCRIBERS_DIR = ROOT_DIR / "examples" / "subscribers"


def _packet_for_selector(scenario_or_packet_id: str) -> tuple[str, dict[str, Any]]:
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        if scenario_or_packet_id in {scenario_name, packet["packet_id"]}:
            return scenario_name, packet
    raise ValueError(f"unknown scenario or packet_id: {scenario_or_packet_id}")


def _authority_ref(verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": verification["packet_id"],
        "snapshot_id": verification["snapshot_id"],
        "revision_id": verification["revision_id"],
        "content_hash": verification["content_hash"],
        "verdict_class": verification["verdict_class"],
        "verification_status": verification["verification_status"],
        "safety_state": dict(verification["safety_state"]),
    }


def _effect(*, action: str, owner: str) -> dict[str, Any]:
    return {
        "subscriber_action": action,
        "owner": owner,
        "can_approve_access": False,
        "can_grant_permissions": False,
        "can_mutate_packet": False,
        "can_override_verdict": False,
        "executes_external_writes": False,
        "requires_human_review": True,
    }


def _base_subscriber(
    *,
    category: str,
    name: str,
    consumer_question: str,
    authority: dict[str, Any],
    effect: dict[str, Any],
    fields_used: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SUBSCRIBER_SCHEMA_VERSION,
        "subscriber_category": category,
        "subscriber": name,
        "category_sentence": PACKET_AUTHORITY_SHORT_SENTENCE,
        "consumer_question": consumer_question,
        "packet_authority": authority,
        "read_only_contract": {
            "method": "GET",
            "endpoint": f"/api/packets/{authority['packet_id']}/verification",
            "source_of_truth": "packet_authority.verification",
        },
        "fields_used": fields_used,
        "subscriber_effect": effect,
    }


def build_subscriber_examples(
    scenario_or_packet_id: str = DEFAULT_SCENARIO,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Build category-folder subscriber examples from the same verification shape."""
    scenario_name, packet = _packet_for_selector(scenario_or_packet_id)
    verification = build_verification_artifact_for_scenario(packet, scenario_name)
    authority = _authority_ref(verification)

    return {
        "gateway": {
            "composio_access_gate.json": _base_subscriber(
                category="gateway",
                name="composio_access_gate",
                consumer_question="Can this tool gateway execute the requested GitHub, Slack, or Jira actions?",
                authority=authority,
                fields_used=[
                    "packet_authority.safety_state.external_writes",
                    "packet_authority.safety_state.permission_grants",
                    "packet_authority.verdict_class",
                ],
                effect=_effect(
                    action="keep Composio in dry-run permission-diff mode",
                    owner="Engineering/Security",
                ),
            ),
            "portkey_model_spend_gate.json": _base_subscriber(
                category="gateway",
                name="portkey_model_spend_gate",
                consumer_question="Can this model gateway allow spend for the workload behind the agent?",
                authority=authority,
                fields_used=[
                    "packet_authority.safety_state.scoped_validation",
                    "packet_authority.safety_state.requires_human_approval",
                    "packet_authority.verification_status",
                ],
                effect=_effect(
                    action="require token/tool spend cap before live model spend expands",
                    owner="Finance/AI Platform",
                ),
            ),
        },
        "ci": {
            "github_actions_deploy_gate.json": _base_subscriber(
                category="ci",
                name="github_actions_deploy_gate",
                consumer_question="Can an automated workflow deploy or modify production using this agent?",
                authority=authority,
                fields_used=[
                    "packet_authority.safety_state.production_access",
                    "packet_authority.safety_state.approval_granted",
                    "packet_authority.verdict_class",
                ],
                effect=_effect(
                    action="block deploy/admin/write jobs until a human-approved packet revision exists",
                    owner="Engineering Leadership",
                ),
            )
        },
        "spend": {
            "finance_budget_gate.json": _base_subscriber(
                category="spend",
                name="finance_budget_gate",
                consumer_question="Can Finance treat this request as approved vendor, token, or tool spend?",
                authority=authority,
                fields_used=[
                    "packet_authority.safety_state.requires_human_approval",
                    "packet_authority.verification_status",
                    "packet_authority.revision_id",
                ],
                effect=_effect(
                    action="route to budget owner with capped scoped-validation envelope",
                    owner="Finance/Procurement",
                ),
            )
        },
        "review": {
            "security_review_queue.json": _base_subscriber(
                category="review",
                name="security_review_queue",
                consumer_question="Which human reviewer queue must inspect this packet before access can move?",
                authority=authority,
                fields_used=[
                    "packet_authority.packet_id",
                    "packet_authority.revision_id",
                    "packet_authority.safety_state.requires_human_approval",
                ],
                effect=_effect(
                    action="open a Security review item against the packet revision",
                    owner="Security",
                ),
            )
        },
        "observability": {
            "datadog_audit_event.json": _base_subscriber(
                category="observability",
                name="datadog_audit_event",
                consumer_question="What packet authority object should be attached to audit telemetry?",
                authority=authority,
                fields_used=[
                    "packet_authority.packet_id",
                    "packet_authority.revision_id",
                    "packet_authority.content_hash",
                    "packet_authority.safety_state",
                ],
                effect=_effect(
                    action="emit read-only audit event with packet hash and blocked safety state",
                    owner="Platform Observability",
                ),
            )
        },
    }


def flatten_subscriber_examples(
    examples: dict[str, dict[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    return [
        payload
        for category in sorted(examples)
        for _filename, payload in sorted(examples[category].items())
    ]


def write_subscriber_examples(
    output_dir: Path = SUBSCRIBERS_DIR,
    *,
    scenario_or_packet_id: str = DEFAULT_SCENARIO,
) -> list[Path]:
    examples = build_subscriber_examples(scenario_or_packet_id)
    written: list[Path] = []
    for category, files in examples.items():
        category_dir = output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in files.items():
            path = category_dir / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            written.append(path)
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.subscribers",
        description="Render downstream subscriber examples for Packet Authority verification.",
    )
    parser.add_argument(
        "scenario_or_packet_id",
        nargs="?",
        default=DEFAULT_SCENARIO,
        help="Scenario name or packet_id to build subscriber examples from.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable subscriber payloads.")
    parser.add_argument("--write", action="store_true", help="Write checked-in subscriber examples.")
    parser.add_argument("--output-dir", type=Path, default=SUBSCRIBERS_DIR, help="Output directory for --write.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write:
        for path in write_subscriber_examples(args.output_dir, scenario_or_packet_id=args.scenario_or_packet_id):
            print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
        return 0

    examples = build_subscriber_examples(args.scenario_or_packet_id)
    if args.json:
        print(json.dumps({"subscribers": flatten_subscriber_examples(examples)}, indent=2, sort_keys=True))
        return 0

    print("# Packet Authority Subscribers")
    print()
    print(PACKET_AUTHORITY_SENTENCE)
    print()
    for category, files in examples.items():
        print(f"- {category}: {', '.join(sorted(files))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
