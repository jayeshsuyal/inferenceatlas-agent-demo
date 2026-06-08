"""Read-only team-lens projection for IA Packet review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TEAM_LENSES_SCHEMA_VERSION = "team_lenses.v0"
TEAM_LENS_SOURCE_OF_TRUTH = "ia_packet.packet_reference"
TEAM_LENS_SAFETY_NOTE = (
    "This lens reads the IA Packet only; it does not approve, assign, dispatch, "
    "grant, write, or mutate state."
)


@dataclass(frozen=True)
class TeamLensDefinition:
    team_id: str
    label: str
    review_focus: str
    keywords: tuple[str, ...]


TEAM_LENS_DEFINITIONS: tuple[TeamLensDefinition, ...] = (
    TeamLensDefinition(
        team_id="product_exec",
        label="Product / Exec",
        review_focus="Business posture, top blocker, decision readiness, and next human validation.",
        keywords=(
            "business",
            "customer",
            "decision",
            "handoff",
            "owner",
            "product",
            "release owner",
            "support ops",
            "workflow",
        ),
    ),
    TeamLensDefinition(
        team_id="engineering",
        label="Engineering",
        review_focus="Runtime scope, repository boundaries, rollback proof, quality, latency, and implementation risk.",
        keywords=(
            "bigquery",
            "code",
            "dependency",
            "engineering",
            "github",
            "jira",
            "latency",
            "lockfile",
            "looker",
            "quality",
            "repository",
            "rollback",
            "workflow",
        ),
    ),
    TeamLensDefinition(
        team_id="security_legal",
        label="Security / Legal",
        review_focus="Data boundary, retention, credentials, secrets, privacy, compliance posture, and legal review.",
        keywords=(
            "compliance",
            "credential",
            "customer-data",
            "data governance",
            "dpa",
            "legal",
            "logging",
            "oauth",
            "privacy",
            "retention",
            "sandbox",
            "secret",
            "security",
        ),
    ),
    TeamLensDefinition(
        team_id="finance",
        label="Finance",
        review_focus="Budget baseline, invoices, usage evidence, spend caps, savings claims, and budget-owner proof.",
        keywords=(
            "budget",
            "cap",
            "cost",
            "credit",
            "finance",
            "invoice",
            "savings",
            "spend",
            "usage",
        ),
    ),
    TeamLensDefinition(
        team_id="procurement",
        label="Procurement",
        review_focus="Vendor terms, contract evidence, renewal exposure, renegotiation path, and provider-change proof.",
        keywords=(
            "contract",
            "minimum",
            "procurement",
            "provider",
            "renegotiation",
            "renewal",
            "terms",
        ),
    ),
    TeamLensDefinition(
        team_id="ai_platform_ops",
        label="AI Platform / Ops",
        review_focus="Agent/tool runtime, gateways, model route, fallback behavior, sponsor proof, and audit trace.",
        keywords=(
            "ai platform",
            "audit",
            "browser",
            "composio",
            "connector",
            "fallback",
            "gateway",
            "mcp",
            "model",
            "nebius",
            "openclaw",
            "platform",
            "portkey",
            "runtime",
            "tavily",
            "tool",
            "trace",
        ),
    ),
)


def _matches(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _select_items(items: list[str], keywords: tuple[str, ...], *, limit: int) -> list[str]:
    selected = [item for item in items if _matches(item, keywords)]
    return selected[:limit]


def _fallback_items(items: list[str], *, limit: int) -> list[str]:
    return [item for item in items[:limit] if item]


def _reviewer_owner(reviewers: list[str], definition: TeamLensDefinition) -> str:
    for reviewer in reviewers:
        if _matches(reviewer, definition.keywords):
            return reviewer
    if definition.team_id == "product_exec" and reviewers:
        return reviewers[0]
    return "Named human reviewer"


def _requested_systems(systems: list[str], definition: TeamLensDefinition) -> list[str]:
    return [system for system in systems if _matches(system, definition.keywords)]


def _next_validation(
    *,
    definition: TeamLensDefinition,
    missing_proof: list[str],
    blocked_claims: list[str],
    default_action: str,
) -> str:
    if missing_proof:
        return f"{definition.label} reviews this proof before the packet can move: {missing_proof[0]}"
    if blocked_claims:
        return f"{definition.label} keeps this claim blocked until packet evidence changes: {blocked_claims[0]}"
    if definition.team_id == "product_exec":
        return default_action
    return f"{definition.label} confirms whether this packet creates a required review gate for their team."


def _build_lens(detail: dict[str, Any], definition: TeamLensDefinition) -> dict[str, Any]:
    blocked_claims = _select_items(detail["blocked_claims"], definition.keywords, limit=3)
    missing_proof = _select_items(detail["missing_proof"], definition.keywords, limit=4)
    requested_systems = _requested_systems(detail["requested_systems"], definition)

    if definition.team_id == "product_exec":
        blocked_claims = blocked_claims or _fallback_items(detail["blocked_claims"], limit=2)
        missing_proof = missing_proof or _fallback_items(detail["missing_proof"], limit=2)

    relevance = "direct" if blocked_claims or missing_proof or requested_systems else "context"
    reviewer_owner = _reviewer_owner(detail["reviewer_routing"], definition)

    return {
        "team_id": definition.team_id,
        "label": definition.label,
        "packet_reference": dict(detail["packet_reference"]),
        "source_of_truth": TEAM_LENS_SOURCE_OF_TRUTH,
        "review_focus": definition.review_focus,
        "relevance": relevance,
        "reviewer_owner": reviewer_owner,
        "requested_systems": requested_systems,
        "allowed_claims": [
            "Packet state is visible for human review.",
            "Missing proof and blocked claims are visible as review inputs.",
        ],
        "blocked_claims": blocked_claims,
        "missing_proof": missing_proof,
        "next_validation": _next_validation(
            definition=definition,
            missing_proof=missing_proof,
            blocked_claims=blocked_claims,
            default_action=detail["decision"]["next_human_action"],
        ),
        "evidence_refs": [
            "ia_packet.blocked_claims",
            "ia_packet.missing_proof",
            "ia_packet.reviewer_routing",
        ],
        "source_refs": list(detail["source_artifacts"]),
        "human_confirmation_required": True,
        "does_not_approve": True,
        "can_assign_work": False,
        "can_dispatch_workflow": False,
        "can_grant_permissions": False,
        "can_mutate_packet": False,
        "state_mutated": False,
        "safety_note": TEAM_LENS_SAFETY_NOTE,
    }


def build_team_lenses(detail: dict[str, Any]) -> dict[str, Any]:
    """Build read-only team lenses from one IA Packet detail object."""
    lenses = [_build_lens(detail, definition) for definition in TEAM_LENS_DEFINITIONS]
    packet_reference = dict(detail["packet_reference"])
    return {
        "schema_version": TEAM_LENSES_SCHEMA_VERSION,
        "packet_reference": packet_reference,
        "source_of_truth": TEAM_LENS_SOURCE_OF_TRUTH,
        "lens_count": len(lenses),
        "lenses": lenses,
        "guardrails": {
            "read_only": True,
            "human_confirmation_required": True,
            "does_not_approve": True,
            "can_assign_work": False,
            "can_dispatch_workflow": False,
            "can_grant_permissions": False,
            "can_mutate_packet": False,
            "state_mutated": False,
        },
        "safety_note": TEAM_LENS_SAFETY_NOTE,
    }
