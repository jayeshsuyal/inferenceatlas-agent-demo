"""Read-only downstream gate decisions backed by Packet Authority verification."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .packet_authority import DEFAULT_SCENARIO
from .scenarios import SCENARIOS, build_scenario_packet
from .subscribers import PACKET_AUTHORITY_SHORT_SENTENCE, build_subscriber_examples, flatten_subscriber_examples
from .verification import build_verification_artifact_for_scenario


DOWNSTREAM_GATE_SCHEMA_VERSION = "packet_authority_downstream_gate.v0"
DEFAULT_SUBSCRIBER = "composio_access_gate"


def _verification_for_selector(scenario_or_packet_id: str) -> tuple[str, dict[str, Any]]:
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        if scenario_or_packet_id in {scenario_name, packet["packet_id"]}:
            return scenario_name, build_verification_artifact_for_scenario(packet, scenario_name)
    raise ValueError(f"unknown scenario or packet_id: {scenario_or_packet_id}")


def _subscriber_for_name(subscriber: str, scenario_or_packet_id: str) -> dict[str, Any]:
    examples = flatten_subscriber_examples(build_subscriber_examples(scenario_or_packet_id))
    for payload in examples:
        if payload["subscriber"] == subscriber:
            return payload
    raise ValueError(f"unknown downstream subscriber: {subscriber}")


def _packet_reference(verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": verification["packet_id"],
        "revision_id": verification["revision_id"],
        "content_hash": verification["content_hash"],
        "verdict_class": verification["verdict_class"],
        "verification_status": verification["verification_status"],
    }


def _decision_for(subscriber: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    category = subscriber["subscriber_category"]
    name = subscriber["subscriber"]

    if category == "observability":
        return {
            "decision": "record_read_only_audit_reference",
            "requested_action_can_proceed": True,
            "allowed_mode": "read_only_audit_event",
            "blocked_reason": None,
            "safe_next_step": "Attach packet_id, revision_id, and content_hash to audit telemetry.",
        }

    if category == "review":
        return {
            "decision": "route_human_review",
            "requested_action_can_proceed": True,
            "allowed_mode": "human_review_queue",
            "blocked_reason": None,
            "safe_next_step": "Open a human review item against the packet revision.",
        }

    if name == "composio_access_gate":
        return {
            "decision": "dry_run_only",
            "requested_action_can_proceed": False,
            "allowed_mode": "dry_run_permission_diff",
            "blocked_reason": (
                "External writes and permission grants are false for this packet; "
                "the gateway may only produce a dry-run permission diff."
            ),
            "safe_next_step": "Collect allowlist and rollback proof, then re-run human review.",
        }

    if category == "ci":
        return {
            "decision": "blocked",
            "requested_action_can_proceed": False,
            "allowed_mode": "none",
            "blocked_reason": (
                "Production access and approval_granted are false for this packet; "
                "CI cannot deploy or mutate production from raw agent intent."
            ),
            "safe_next_step": "Require a human-approved packet revision before deploy/admin/write jobs.",
        }

    if category == "spend" or "spend" in name:
        return {
            "decision": "blocked",
            "requested_action_can_proceed": False,
            "allowed_mode": "none",
            "blocked_reason": (
                "Human approval is required and the packet does not approve spend, "
                "provider selection, or savings claims."
            ),
            "safe_next_step": "Route to Finance and Procurement with invoice, usage, and contract proof.",
        }

    return {
        "decision": "blocked",
        "requested_action_can_proceed": False,
        "allowed_mode": "none",
        "blocked_reason": (
            "The packet verification status is review-required and no downstream subscriber "
            "may trust raw agent intent."
        ),
        "safe_next_step": "Use the packet next_human_action before any live movement.",
    }


def build_downstream_gate_decision(
    subscriber: str = DEFAULT_SUBSCRIBER,
    *,
    scenario_or_packet_id: str = DEFAULT_SCENARIO,
) -> dict[str, Any]:
    """Build the decision a downstream system gets before allowing an agent action."""
    scenario_name, verification = _verification_for_selector(scenario_or_packet_id)
    subscriber_payload = _subscriber_for_name(subscriber, scenario_or_packet_id)
    effect = subscriber_payload["subscriber_effect"]
    decision = _decision_for(subscriber_payload, verification)

    return {
        "schema_version": DOWNSTREAM_GATE_SCHEMA_VERSION,
        "scenario": scenario_name,
        "packet_authority": PACKET_AUTHORITY_SHORT_SENTENCE,
        "subscriber": subscriber_payload["subscriber"],
        "subscriber_category": subscriber_payload["subscriber_category"],
        "consumer_question": subscriber_payload["consumer_question"],
        "source_of_truth": subscriber_payload["read_only_contract"],
        "packet_reference": _packet_reference(verification),
        "safety_state": verification["safety_state"],
        "requested_action_can_proceed": decision["requested_action_can_proceed"],
        "access_or_spend_movement_allowed": False,
        "decision": decision["decision"],
        "allowed_mode": decision["allowed_mode"],
        "blocked_reason": decision["blocked_reason"],
        "safe_next_step": decision["safe_next_step"],
        "next_human_action": verification["next_human_action"],
        "blocked_claims": verification["blocked_claims"],
        "missing_proof": verification["missing_proof"],
        "reviewer_owners": verification["reviewer_owners"],
        "subscriber_effect": effect,
        "invariants": {
            "read_only": True,
            "method": "GET",
            "raw_agent_intent_trusted": False,
            "packet_mutation_allowed": False,
            "subscriber_can_approve_access": effect["can_approve_access"],
            "subscriber_can_grant_permissions": effect["can_grant_permissions"],
            "subscriber_can_override_verdict": effect["can_override_verdict"],
            "subscriber_executes_external_writes": effect["executes_external_writes"],
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def build_all_downstream_gate_decisions(
    scenario_or_packet_id: str = DEFAULT_SCENARIO,
) -> list[dict[str, Any]]:
    examples = flatten_subscriber_examples(build_subscriber_examples(scenario_or_packet_id))
    return [
        build_downstream_gate_decision(payload["subscriber"], scenario_or_packet_id=scenario_or_packet_id)
        for payload in examples
    ]


def render_downstream_gate_decision_markdown(decision: dict[str, Any]) -> str:
    blocked_reason = decision["blocked_reason"] or "None. This is a read-only review/audit route."
    packet = decision["packet_reference"]
    return "\n".join(
        [
            "# Downstream Gate Decision",
            "",
            "Private engine, public proof.",
            "",
            f"- subscriber: `{decision['subscriber']}`",
            f"- category: `{decision['subscriber_category']}`",
            f"- decision: {decision['decision']}",
            f"- requested action can proceed: {decision['requested_action_can_proceed']}",
            f"- access or spend movement allowed: {decision['access_or_spend_movement_allowed']}",
            f"- allowed mode: {decision['allowed_mode']}",
            f"- blocked reason: {blocked_reason}",
            f"- packet_id: `{packet['packet_id']}`",
            f"- revision_id: `{packet['revision_id']}`",
            f"- content_hash: `{packet['content_hash']}`",
            f"- verdict_class: {packet['verdict_class']}",
            f"- source of truth: `{decision['source_of_truth']['endpoint']}`",
            f"- next human action: {decision['next_human_action']}",
            "",
        ]
    )


def render_downstream_gate_decisions_markdown(decisions: list[dict[str, Any]]) -> str:
    lines = [
        "# Downstream Gate Decisions",
        "",
        "Private engine, public proof.",
        "",
        "Downstream systems ask IA whether a requested agent action can proceed. IA answers from the packet, not raw agent intent.",
        "",
        "| Subscriber | Decision | Requested Action | Allowed Mode |",
        "| --- | --- | --- | --- |",
    ]
    for decision in decisions:
        lines.append(
            "| {subscriber} | {decision} | {proceed} | {mode} |".format(
                subscriber=decision["subscriber"],
                decision=decision["decision"],
                proceed=decision["requested_action_can_proceed"],
                mode=decision["allowed_mode"],
            )
        )
    lines.extend(
        [
            "",
            f"- all access/spend movement blocked: {all(not item['access_or_spend_movement_allowed'] for item in decisions)}",
            f"- all decisions read-only: {all(item['invariants']['read_only'] for item in decisions)}",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.downstream_gate",
        description="Return read-only downstream gate decisions from Packet Authority verification.",
    )
    parser.add_argument("subscriber", nargs="?", default=DEFAULT_SUBSCRIBER, help="Subscriber name to evaluate.")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO, help="Scenario name or packet_id.")
    parser.add_argument("--all", action="store_true", help="Return decisions for every subscriber example.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.all:
            decisions = build_all_downstream_gate_decisions(args.scenario)
            if args.json:
                print(
                    json.dumps(
                        {
                            "schema_version": DOWNSTREAM_GATE_SCHEMA_VERSION,
                            "decisions": decisions,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
            else:
                print(render_downstream_gate_decisions_markdown(decisions))
            return 0

        decision = build_downstream_gate_decision(args.subscriber, scenario_or_packet_id=args.scenario)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(decision, indent=2, sort_keys=True))
    else:
        print(render_downstream_gate_decision_markdown(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
