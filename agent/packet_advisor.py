"""Packet-backed advisor shared by CLI and Ask IA."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from .coach_suggestions import build_packet_advisor_suggestions
from .workbench import build_workbench_result


PACKET_ADVISOR_SCHEMA_VERSION = "packet_advisor_answer.v0"
DEFAULT_FIXTURE = "ai_spend_budget_overrun"
DEFAULT_SPEND_SUBSCRIBER = "portkey_model_spend_gate"
SAFETY_TONE_ANCHOR = (
    "IA does not approve this request. Human review is required and unsafe movement stays blocked."
)

AnswerKind = Literal["decision", "proof_status", "reviewer_routing", "safety_status", "unsupported"]

_ANSWER_KINDS: tuple[AnswerKind, ...] = (
    "decision",
    "proof_status",
    "reviewer_routing",
    "safety_status",
    "unsupported",
)

FORBIDDEN_HEDGE_PHRASES = (
    "probably",
    "technically",
    "looks like",
    "seems like",
    "might be okay",
    "should be fine",
)


@dataclass(frozen=True)
class GateResponse:
    """A downstream system's read-only interpretation of one IA Packet."""

    subscriber: str
    subscriber_category: str
    decision: str
    requested_action_can_proceed: bool
    allowed_mode: str
    blocked_reason: str
    safe_next_step: str
    subscriber_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscriber": self.subscriber,
            "subscriber_category": self.subscriber_category,
            "decision": self.decision,
            "requested_action_can_proceed": self.requested_action_can_proceed,
            "allowed_mode": self.allowed_mode,
            "blocked_reason": self.blocked_reason,
            "safe_next_step": self.safe_next_step,
            "subscriber_action": self.subscriber_action,
            "invariants": {
                "read_only": True,
                "raw_agent_intent_trusted": False,
                "can_approve_access": False,
                "can_grant_permissions": False,
                "can_mutate_packet": False,
                "can_override_verdict": False,
                "executes_external_writes": False,
            },
        }


class SubscriberAdapter(Protocol):
    name: str

    def consume(self, result: dict[str, Any]) -> GateResponse:
        """Return a read-only subscriber decision from a normalized packet result."""


SUBSCRIBER_REGISTRY: dict[str, SubscriberAdapter] = {}


def register_subscriber(name: str) -> Callable[[type[SubscriberAdapter]], type[SubscriberAdapter]]:
    def decorator(cls: type[SubscriberAdapter]) -> type[SubscriberAdapter]:
        SUBSCRIBER_REGISTRY[name] = cls()
        return cls

    return decorator


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def route_question(question: str) -> AnswerKind:
    """Route a plain-English question to one bounded packet answer kind."""
    normalized = _normalized(question)
    if not normalized:
        return "unsupported"

    decision_terms = (
        "can portkey",
        "can composio",
        "can ci",
        "can github actions",
        "can this move",
        "can this proceed",
        "can this run",
        "can this deploy",
        "can this execute",
        "allow this",
        "allow spend",
        "approve this",
        "approve spend",
        "execute this",
        "move this",
        "proceed",
    )
    proof_terms = (
        "proof",
        "missing",
        "evidence",
        "require",
        "requires",
        "need",
        "needed",
        "blocked until",
        "proof debt",
        "before changing",
        "before spend",
        "before vendor",
    )
    routing_terms = (
        "who",
        "owner",
        "owners",
        "reviewer",
        "reviewers",
        "routing",
        "route",
        "finance review",
        "procurement review",
        "security review",
        "legal review",
        "what should finance",
        "what should procurement",
    )
    safety_terms = (
        "safe",
        "safety",
        "risk",
        "guardrail",
        "status",
        "production access",
        "external write",
        "writes",
        "grant",
        "grants",
    )

    if _contains_any(normalized, decision_terms):
        return "decision"
    if _contains_any(normalized, proof_terms):
        return "proof_status"
    if _contains_any(normalized, routing_terms):
        return "reviewer_routing"
    if _contains_any(normalized, safety_terms):
        return "safety_status"
    return "unsupported"


def select_fixture_for_question(question: str, current_fixture: str = "") -> str:
    """Pick a default public fixture when the UI has not supplied page context."""
    if current_fixture:
        return current_fixture
    normalized = _normalized(question)
    spend_terms = (
        "ai spend",
        "budget",
        "vendor",
        "vendors",
        "portkey",
        "model spend",
        "usage cap",
        "finance",
        "procurement",
        "savings",
    )
    if _contains_any(normalized, spend_terms):
        return "ai_spend_budget_overrun"
    if _contains_any(normalized, ("miasma", "supply chain", "package", "ci credential")):
        return "miasma_pre_permission_packet"
    if _contains_any(normalized, ("mcp", "connector", "google drive", "browser sandbox")):
        return "mcp_tool_blast_radius"
    return DEFAULT_FIXTURE


def select_subscriber_for_question(question: str, subscriber: str = "") -> str:
    """Pick a downstream subscriber from explicit input or buyer-language terms."""
    if subscriber:
        return subscriber
    normalized = _normalized(question)
    if "portkey" in normalized:
        return "portkey_model_spend_gate"
    if "composio" in normalized:
        return "composio_access_gate"
    if "github actions" in normalized or "ci" in normalized or "deploy" in normalized:
        return "github_actions_deploy_gate"
    if "finance" in normalized or "procurement" in normalized or "budget" in normalized:
        return "finance_budget_gate"
    if "security" in normalized or "legal" in normalized:
        return "security_review_queue"
    if "datadog" in normalized or "observability" in normalized or "audit" in normalized:
        return "datadog_audit_event"
    return ""


def should_use_packet_advisor(question: str, *, current_fixture: str = "", subscriber: str = "") -> bool:
    """Return True when Ask IA should use packet truth instead of generic chat/tools."""
    answer_kind = route_question(question)
    normalized = _normalized(question)
    advisor_terms = (
        "packet",
        "portkey",
        "composio",
        "finance",
        "procurement",
        "budget",
        "vendor",
        "spend",
        "proof",
        "review",
        "move",
        "proceed",
        "approve",
    )
    if answer_kind == "unsupported":
        return bool(subscriber or _contains_any(normalized, advisor_terms))
    return bool(current_fixture or subscriber or _contains_any(normalized, advisor_terms))


def _first(items: list[str], fallback: str) -> str:
    return items[0] if items else fallback


def _join_items(items: list[str], *, limit: int = 3) -> str:
    chosen = [item.rstrip(".") for item in items[:limit] if item]
    if not chosen:
        return "No packet evidence is available."
    return "; ".join(chosen) + "."


def _packet_reference(result: dict[str, Any]) -> dict[str, str]:
    ref = result["packet_reference"]
    return {
        "packet_id": ref["packet_id"],
        "revision_id": ref["revision_id"],
        "content_hash": ref["content_hash"],
    }


def _subscriber_label(subscriber: str) -> str:
    labels = {
        "portkey_model_spend_gate": "Portkey",
        "composio_access_gate": "Composio",
        "github_actions_deploy_gate": "CI",
        "finance_budget_gate": "Finance",
        "security_review_queue": "Security review",
        "datadog_audit_event": "Observability",
    }
    return labels.get(subscriber, subscriber.replace("_", " ").title() if subscriber else "Downstream systems")


@register_subscriber("portkey_model_spend_gate")
class PortkeyModelSpendGate:
    name = "portkey_model_spend_gate"

    def consume(self, result: dict[str, Any]) -> GateResponse:
        return GateResponse(
            subscriber=self.name,
            subscriber_category="gateway",
            decision="blocked",
            requested_action_can_proceed=False,
            allowed_mode="none",
            blocked_reason=(
                "IA does not approve spend, provider selection, savings claims, or model-spend "
                "expansion from this packet."
            ),
            safe_next_step="Route invoice, usage, contract, and budget-owner proof before model spend expands.",
            subscriber_action="require a spend cap and Finance/Procurement review before live model spend expands",
        )


@register_subscriber("composio_access_gate")
class ComposioAccessGate:
    name = "composio_access_gate"

    def consume(self, result: dict[str, Any]) -> GateResponse:
        return GateResponse(
            subscriber=self.name,
            subscriber_category="gateway",
            decision="dry_run_only",
            requested_action_can_proceed=False,
            allowed_mode="dry_run_permission_diff",
            blocked_reason="IA does not approve external writes or permission grants from this packet.",
            safe_next_step="Keep Composio in dry-run permission-diff mode until humans approve the packet revision.",
            subscriber_action="keep Composio in dry-run permission-diff mode",
        )


@register_subscriber("github_actions_deploy_gate")
class GithubActionsDeployGate:
    name = "github_actions_deploy_gate"

    def consume(self, result: dict[str, Any]) -> GateResponse:
        return GateResponse(
            subscriber=self.name,
            subscriber_category="ci",
            decision="blocked",
            requested_action_can_proceed=False,
            allowed_mode="none",
            blocked_reason="IA does not approve production access, deploys, or production mutation from this packet.",
            safe_next_step="Require a human-approved packet revision before deploy/admin/write jobs.",
            subscriber_action="block deploy/admin/write jobs until a human-approved packet revision exists",
        )


@register_subscriber("finance_budget_gate")
class FinanceBudgetGate:
    name = "finance_budget_gate"

    def consume(self, result: dict[str, Any]) -> GateResponse:
        return GateResponse(
            subscriber=self.name,
            subscriber_category="spend",
            decision="review_required",
            requested_action_can_proceed=False,
            allowed_mode="finance_procurement_review",
            blocked_reason="IA does not approve spend movement until Finance and Procurement review the evidence.",
            safe_next_step=result["decision"]["next_human_action"],
            subscriber_action="route to budget owner with capped scoped-validation envelope",
        )


@register_subscriber("security_review_queue")
class SecurityReviewQueue:
    name = "security_review_queue"

    def consume(self, result: dict[str, Any]) -> GateResponse:
        return GateResponse(
            subscriber=self.name,
            subscriber_category="review",
            decision="route_human_review",
            requested_action_can_proceed=True,
            allowed_mode="human_review_queue",
            blocked_reason="IA does not approve access; it only routes the packet to human reviewers.",
            safe_next_step="Open a human review item against the packet revision.",
            subscriber_action="open a Security review item against the packet revision",
        )


@register_subscriber("datadog_audit_event")
class DatadogAuditEvent:
    name = "datadog_audit_event"

    def consume(self, result: dict[str, Any]) -> GateResponse:
        return GateResponse(
            subscriber=self.name,
            subscriber_category="observability",
            decision="record_read_only_audit_reference",
            requested_action_can_proceed=True,
            allowed_mode="read_only_audit_event",
            blocked_reason="IA does not approve access; observability records the packet reference only.",
            safe_next_step="Attach packet_id, revision_id, and content_hash to audit telemetry.",
            subscriber_action="emit read-only audit event with packet hash and blocked safety state",
        )


def _build_gate_response(result: dict[str, Any], subscriber: str) -> dict[str, Any] | None:
    if not subscriber:
        return None
    adapter = SUBSCRIBER_REGISTRY.get(subscriber)
    if not adapter:
        raise ValueError(f"unknown subscriber: {subscriber}")
    return adapter.consume(result).to_dict()


def _render_answer(
    *,
    result: dict[str, Any],
    answer_kind: AnswerKind,
    question: str,
    subscriber: str,
    gate: dict[str, Any] | None,
) -> str:
    decision = result["decision"]
    fixture = result["fixture"]
    packet = result["packet_reference"]
    subject = _subscriber_label(subscriber)
    blocked = result["blocked_claims"]
    missing = result["missing_proof"]
    reviewers = result["reviewer_routing"]
    next_action = decision["next_human_action"]

    if answer_kind == "decision":
        if gate:
            first = (
                f"{subject} cannot allow this request. "
                f"{gate['blocked_reason']} "
                f"Packet `{packet['packet_id']}` is still `{decision['verdict_class']}`."
            )
            allowed_mode = gate["allowed_mode"]
        else:
            first = (
                f"This request cannot move. Packet `{packet['packet_id']}` is "
                f"`{decision['verdict_class']}` and production access is `{decision['production_access']}`."
            )
            allowed_mode = "review_packet_only"
        body = [
            "## Decision",
            first,
            "",
            f"- fixture: `{fixture['fixture_id']}`",
            f"- allowed mode: `{allowed_mode}`",
            f"- next human action: {next_action}",
        ]
    elif answer_kind == "proof_status":
        body = [
            "## Proof status",
            f"IA requires proof before this packet can move. {_join_items(missing)}",
            "",
            f"- packet_id: `{packet['packet_id']}`",
            f"- first blocked claim: {_first(blocked, 'Unsafe movement stays blocked.')}",
            f"- next human action: {next_action}",
        ]
    elif answer_kind == "reviewer_routing":
        body = [
            "## Reviewer routing",
            f"Route this packet to the named human owners before anything moves. {_join_items(reviewers)}",
            "",
            f"- packet_id: `{packet['packet_id']}`",
            f"- next human action: {next_action}",
        ]
    elif answer_kind == "safety_status":
        body = [
            "## Safety status",
            (
                "The packet is locked to a non-approving state: production access false, "
                "permission grants false, external writes false, and human review true."
            ),
            "",
            f"- packet_id: `{packet['packet_id']}`",
            f"- verdict: `{decision['verdict_class']}`",
            f"- next human action: {next_action}",
        ]
    else:
        body = [
            "## Unsupported packet question",
            (
                "I cannot answer that from this IA Packet. Ask for a decision, proof status, "
                "reviewer routing, or safety status."
            ),
            "",
            f"- packet_id: `{packet['packet_id']}`",
            f"- question: {question.strip() or '(empty)'}",
            f"- next human action: {next_action}",
        ]

    body.extend(["", f"**Safety anchor:** {SAFETY_TONE_ANCHOR}"])
    return "\n".join(body)


def build_packet_advisor_answer(
    *,
    fixture: str = DEFAULT_FIXTURE,
    question: str = "",
    subscriber: str = "",
) -> dict[str, Any]:
    """Build one packet-backed answer for CLI, API, or Ask IA."""
    result = build_workbench_result(fixture)
    answer_kind = route_question(question)
    selected_subscriber = select_subscriber_for_question(question, subscriber)
    gate = _build_gate_response(result, selected_subscriber)
    rendered_text = _render_answer(
        result=result,
        answer_kind=answer_kind,
        question=question,
        subscriber=selected_subscriber,
        gate=gate,
    )
    lowered = rendered_text.lower()
    forbidden = [phrase for phrase in FORBIDDEN_HEDGE_PHRASES if phrase in lowered]
    suggestions = build_packet_advisor_suggestions(
        {
            "fixture": result["fixture"],
            "packet_reference": _packet_reference(result),
            "missing_proof": list(result["missing_proof"]),
            "decision": result["decision"],
            "blocked_claims": list(result["blocked_claims"]),
            "reviewer_routing": list(result["reviewer_routing"]),
        }
    )

    return {
        "schema_version": PACKET_ADVISOR_SCHEMA_VERSION,
        "answer_kind": answer_kind,
        "supported": answer_kind != "unsupported",
        "question": question,
        "fixture": result["fixture"],
        "subscriber": selected_subscriber or None,
        "packet_reference": _packet_reference(result),
        "verdict_class": result["decision"]["verdict_class"],
        "decision": result["decision"],
        "safety": result["safety_boundary"],
        "blocked_claims": list(result["blocked_claims"]),
        "missing_proof": list(result["missing_proof"]),
        "reviewer_routing": list(result["reviewer_routing"]),
        "next_human_action": result["decision"]["next_human_action"],
        "downstream_gate": gate,
        "rendered_text": rendered_text,
        "suggestions": suggestions,
        "tone_invariants": {
            "contains_does_not_approve": "does not approve" in lowered,
            "contains_human_review": "human review" in lowered,
            "contains_stays_blocked": "stays blocked" in lowered,
            "forbidden_hedges": forbidden,
        },
        "invariants": {
            "read_only": True,
            "calls_v1": result["local_verification"]["calls_v1"],
            "raw_agent_intent_trusted": False,
            "packet_mutation_allowed": False,
            "approves_access": result["safety_boundary"]["approves_access"],
            "approves_spend": result["safety_boundary"]["approves_spend"],
            "grants_permissions": result["safety_boundary"]["grants_permissions"],
            "executes_external_writes": result["safety_boundary"]["executes_external_writes"],
            "requires_human_review": result["safety_boundary"]["requires_human_review"],
        },
    }


def render_packet_advisor_markdown(answer: dict[str, Any]) -> str:
    return str(answer["rendered_text"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.packet_advisor",
        description="Answer packet, proof, routing, and subscriber-gate questions from one IA Packet.",
    )
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="Workbench fixture id to answer from.")
    parser.add_argument("--subscriber", default="", help="Optional downstream subscriber gate name.")
    parser.add_argument("--question", default="", help="Plain-English question to route against the packet.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable packet advisor JSON.")
    parser.add_argument("--explain", action="store_true", help="Print JSON after the rendered answer.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        answer = build_packet_advisor_answer(
            fixture=args.fixture,
            question=args.question,
            subscriber=args.subscriber,
        )
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(answer, indent=2, sort_keys=True))
        return 0

    print(render_packet_advisor_markdown(answer))
    if args.explain:
        print()
        print(json.dumps(answer, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
