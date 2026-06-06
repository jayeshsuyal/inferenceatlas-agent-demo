"""Fixture-only Packet Workbench for public review lanes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .packet_authority import build_packet_authority_snapshot_for_scenario, stable_sha256
from .pilot_memo import PILOT_MEMO_SAFETY_ANCHOR, build_pilot_memo, render_copy_review_brief
from .scenarios import ROOT_DIR, SCENARIOS, build_scenario_brief, build_scenario_packet
from .spend import build_spend_review_bundle, load_spend_review_request
from .sponsor_proof_trace import build_sponsor_proof_trace
from .trial import build_trial_bundle
from .verification import build_verification_artifact_for_scenario


WORKBENCH_SCHEMA_VERSION = "packet_workbench.v0"
WORKBENCH_RESULT_SCHEMA_VERSION = "packet_workbench_result.v0"
WORKBENCH_SAFETY_ANCHOR = PILOT_MEMO_SAFETY_ANCHOR

FixtureKind = Literal["scenario", "trial", "spend"]


@dataclass(frozen=True)
class WorkbenchLane:
    lane_id: str
    label: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "lane_id": self.lane_id,
            "label": self.label,
            "description": self.description,
        }


@dataclass(frozen=True)
class WorkbenchFixture:
    fixture_id: str
    lane_id: str
    kind: FixtureKind
    label: str
    description: str
    path: str | None = None
    scenario_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "lane_id": self.lane_id,
            "kind": self.kind,
            "label": self.label,
            "description": self.description,
            "path": self.path,
            "scenario_name": self.scenario_name,
        }


WORKBENCH_LANES: tuple[WorkbenchLane, ...] = (
    WorkbenchLane(
        lane_id="agent_access",
        label="Agent access",
        description="Tool, data, and production-access requests become scoped-validation or blocked decisions.",
    ),
    WorkbenchLane(
        lane_id="ai_spend",
        label="AI spend",
        description="Usage, vendor, and savings questions become Finance and Procurement review packets.",
    ),
    WorkbenchLane(
        lane_id="supply_chain_ci",
        label="Supply-chain / CI",
        description="Install, publish, workflow, and credential-bearing scope becomes pre-permission proof debt.",
    ),
    WorkbenchLane(
        lane_id="mcp_tool_access",
        label="MCP / tool blast radius",
        description="Connector and managed-tool access becomes reviewer-routed blast-radius review.",
    ),
)

WORKBENCH_FIXTURES: tuple[WorkbenchFixture, ...] = (
    WorkbenchFixture(
        fixture_id="support_triage_agent",
        lane_id="agent_access",
        kind="scenario",
        scenario_name="support_triage_agent",
        label="Support triage bot",
        description="GitHub, Slack, and Jira access routed to scoped validation.",
    ),
    WorkbenchFixture(
        fixture_id="read_only_analytics_agent",
        lane_id="agent_access",
        kind="scenario",
        scenario_name="read_only_analytics_agent",
        label="Read-only analytics",
        description="Lower-risk read access relaxes without granting production access.",
    ),
    WorkbenchFixture(
        fixture_id="admin_code_fix_bot",
        lane_id="agent_access",
        kind="scenario",
        scenario_name="admin_code_fix_bot",
        label="Admin code-fix bot",
        description="Admin and production-write scope blocks before validation.",
    ),
    WorkbenchFixture(
        fixture_id="ai_spend_budget_overrun",
        lane_id="ai_spend",
        kind="spend",
        path="examples/requests/ai_spend_budget_overrun.yml",
        label="Q1 budget overrun",
        description="Finance and Procurement review before caps, vendor switches, or savings claims move.",
    ),
    WorkbenchFixture(
        fixture_id="miasma_pre_permission_packet",
        lane_id="supply_chain_ci",
        kind="trial",
        path="examples/requests/miasma_pre_permission_packet.yml",
        label="Miasma pre-permission packet",
        description="Dependency, publish, CI, and credential scope reviewed before it moves.",
    ),
    WorkbenchFixture(
        fixture_id="mcp_tool_blast_radius",
        lane_id="mcp_tool_access",
        kind="trial",
        path="examples/requests/mcp_tool_blast_radius.yml",
        label="MCP tool blast radius",
        description="Connector tools, repo context, files, and chat actions stay dry-run until proof lands.",
    ),
)


def _fixture_by_id(fixture_id: str) -> WorkbenchFixture:
    for fixture in WORKBENCH_FIXTURES:
        if fixture.fixture_id == fixture_id:
            return fixture
    raise KeyError(f"unknown workbench fixture: {fixture_id}")


def _relative_path(path: Path | str | None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = ROOT_DIR / p
    return str(p.relative_to(ROOT_DIR) if p.is_relative_to(ROOT_DIR) else p)


def _canonical_hash(payload: dict[str, Any]) -> str:
    return f"sha256:{stable_sha256(payload)}"


def _stringify_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        label = (
            item.get("claim")
            or item.get("proof_needed")
            or item.get("evidence")
            or item.get("item")
            or item.get("owner")
            or item.get("role")
            or item.get("action")
            or "item"
        )
        detail = item.get("reason") or item.get("owner") or item.get("unblocks") or item.get("review_area") or ""
        return str(label) + (f" - {detail}" if detail else "")
    return str(item)


def _stringify_items(items: list[Any] | tuple[Any, ...], *, limit: int = 8) -> list[str]:
    return [_stringify_item(item) for item in list(items)[:limit]]


def _unique_strings(values: list[str], *, limit: int = 12) -> list[str]:
    seen = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
        if len(output) >= limit:
            break
    return output


def _sponsor_trace_summary(request_path: Path) -> dict[str, Any]:
    trace = build_sponsor_proof_trace(request_path)
    steps = trace["sponsor_steps"]
    return {
        "trace_id": trace["trace_id"],
        "lane": trace["lane"],
        "step_count": len(steps),
        "sponsor_order": [step["sponsor"] for step in steps],
        "decision_lock_unchanged": trace["decision_lock_before"] == trace["decision_lock_after"],
        "all_non_executing": all(not step["would_execute"] for step in steps),
        "all_non_approving": all(not step["can_approve_access"] for step in steps),
        "all_non_granting": all(not step["can_grant_permissions"] for step in steps),
        "all_non_mutating": all(not step["can_mutate_external_state"] for step in steps),
    }


def _copy_brief(
    *,
    title: str,
    fixture: WorkbenchFixture,
    verdict_class: str,
    packet_id: str,
    content_hash: str,
    blocked_claims: list[str],
    missing_proof: list[str],
    reviewer_routing: list[str],
    next_human_action: str,
) -> str:
    blocked = "; ".join(blocked_claims[:2]) or "No unsafe movement allowed by this public harness."
    missing = "; ".join(missing_proof[:2]) or "Human proof remains required."
    reviewers = "; ".join(reviewer_routing[:2]) or "Named reviewers required."
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Fixture `{fixture.fixture_id}` produced packet `{packet_id}` with `{content_hash}`.",
            "",
            f"Verdict class: `{verdict_class}`.",
            f"Blocked claims: {blocked}",
            f"Missing proof: {missing}",
            f"Reviewer routing: {reviewers}",
            f"Next human action: {next_human_action}",
            "",
            WORKBENCH_SAFETY_ANCHOR,
            "",
        ]
    )


def _base_result(
    *,
    fixture: WorkbenchFixture,
    title: str,
    verdict_class: str,
    packet_id: str,
    revision_id: str,
    content_hash: str,
    blocked_claims: list[str],
    missing_proof: list[str],
    reviewer_routing: list[str],
    next_human_action: str,
    requested_systems: list[str],
    source_artifacts: list[str],
    sponsor_trace: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    copy_brief = _copy_brief(
        title=title,
        fixture=fixture,
        verdict_class=verdict_class,
        packet_id=packet_id,
        content_hash=content_hash,
        blocked_claims=blocked_claims,
        missing_proof=missing_proof,
        reviewer_routing=reviewer_routing,
        next_human_action=next_human_action,
    )
    return {
        "schema_version": WORKBENCH_RESULT_SCHEMA_VERSION,
        "ok": True,
        "title": title,
        "fixture": fixture.to_dict(),
        "mode": "offline_deterministic",
        "packet_reference": {
            "packet_id": packet_id,
            "revision_id": revision_id,
            "content_hash": content_hash,
        },
        "local_verification": {
            "read_only": True,
            "source": "local_canonical_json",
            "calls_v1": False,
            "content_hash": content_hash,
        },
        "decision": {
            "verdict_class": verdict_class,
            "production_access": False,
            "permission_grants": False,
            "external_writes": False,
            "approval_granted": False,
            "approves_spend": False,
            "selects_provider": False,
            "guarantees_savings": False,
            "requires_human_review": True,
            "next_human_action": next_human_action,
        },
        "requested_systems": requested_systems,
        "blocked_claims": blocked_claims,
        "missing_proof": missing_proof,
        "reviewer_routing": reviewer_routing,
        "sponsor_proof_trace": sponsor_trace,
        "copy_review_brief": copy_brief,
        "export_label": "Export pilot memo" if fixture.kind == "trial" else "Export workbench result",
        "source_artifacts": source_artifacts,
        "safety_anchor": WORKBENCH_SAFETY_ANCHOR,
        "safety_boundary": {
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_production": False,
            "approves_spend": False,
            "selects_provider": False,
            "guarantees_savings": False,
            "requires_human_review": True,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
        "extra": extra or {},
    }


def _scenario_result(fixture: WorkbenchFixture) -> dict[str, Any]:
    scenario_name = fixture.scenario_name or fixture.fixture_id
    if scenario_name not in SCENARIOS:
        raise KeyError(f"unknown scenario: {scenario_name}")
    packet = build_scenario_packet(scenario_name)
    brief = build_scenario_brief(scenario_name)
    verification = build_verification_artifact_for_scenario(packet, scenario_name)
    return _base_result(
        fixture=fixture,
        title=f"{fixture.label} packet",
        verdict_class=verification["verdict_class"],
        packet_id=verification["packet_id"],
        revision_id=verification["revision_id"],
        content_hash=verification["content_hash"],
        blocked_claims=_stringify_items(packet["blocked_claims"]),
        missing_proof=_stringify_items(packet["missing_proof"]),
        reviewer_routing=_stringify_items(packet["reviewer_action_items"]),
        next_human_action=verification["next_human_action"],
        requested_systems=[item["system"] for item in packet["requested_capability"]],
        source_artifacts=[
            f"examples/generated/{scenario_name}.packet.md",
            f"examples/generated/{scenario_name}.decision_brief.md",
            f"examples/generated/{scenario_name}.verification.json",
        ],
        extra={
            "brief_id": brief["brief_id"],
            "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
        },
    )


def _trial_result(fixture: WorkbenchFixture) -> dict[str, Any]:
    if not fixture.path:
        raise ValueError(f"{fixture.fixture_id} missing request path")
    request_path = ROOT_DIR / fixture.path
    bundle = build_trial_bundle(request_path)
    packet = bundle["packet"]
    report = bundle["report"]
    snapshot = build_packet_authority_snapshot_for_scenario(packet, request_path.stem)
    pilot_memo = build_pilot_memo(request_path)
    sponsor_trace = _sponsor_trace_summary(request_path)
    request_missing_proof = _stringify_items(report["proof_debt"]["request_missing_proof"])
    request_blocked_claims = _stringify_items(report["proof_debt"]["request_unsupported_claims"])
    request_reviewers = [
        f"{role}: request reviewer"
        for role in report["reviewer_routing"]["request_roles"]["required"]
    ]
    derived_reviewers = [
        f"{item['owner']}: {item['decision_needed']}" for item in pilot_memo["reviewer_routing"]
    ]
    result = _base_result(
        fixture=fixture,
        title=f"{fixture.label} packet",
        verdict_class=pilot_memo["verdict_class"],
        packet_id=snapshot["packet_id"],
        revision_id=snapshot["revision_id"],
        content_hash=snapshot["content_hash"],
        blocked_claims=_unique_strings(request_blocked_claims + list(pilot_memo["blocked_claims"])),
        missing_proof=_unique_strings(request_missing_proof + list(pilot_memo["missing_proof"])),
        reviewer_routing=_unique_strings(request_reviewers + derived_reviewers),
        next_human_action=pilot_memo["next_human_action"],
        requested_systems=report["packet_summary"]["requested_systems"],
        source_artifacts=[fixture.path],
        sponsor_trace=sponsor_trace,
        extra={
            "request_readiness": report["request_readiness"],
            "access_speed_lane": report["access_speed_lane"]["lane"],
            "pilot_memo_id": pilot_memo["memo_id"],
        },
    )
    result["copy_review_brief"] = render_copy_review_brief(pilot_memo)
    return result


def _spend_result(fixture: WorkbenchFixture) -> dict[str, Any]:
    if not fixture.path:
        raise ValueError(f"{fixture.fixture_id} missing request path")
    request_path = ROOT_DIR / fixture.path
    request = load_spend_review_request(request_path)
    bundle = build_spend_review_bundle(request, request_path=request_path)
    packet = bundle["packet"]
    content_hash = packet["content_hash"]
    return _base_result(
        fixture=fixture,
        title=f"{fixture.label} spend packet",
        verdict_class=packet["decision"]["verdict_class"],
        packet_id=packet["packet_id"],
        revision_id=f"rev_{content_hash.split(':', 1)[1][:16]}",
        content_hash=content_hash,
        blocked_claims=_stringify_items(packet["blocked_claims"]),
        missing_proof=_stringify_items(packet["required_evidence"]),
        reviewer_routing=_stringify_items(packet["reviewer_owners"]),
        next_human_action=packet["next_human_action"]["action"],
        requested_systems=["Finance", "Procurement", "AI Platform / Engineering"],
        source_artifacts=[fixture.path, *bundle["artifacts"].values()],
        extra={
            "budget_period": packet["requested_finance_decision"]["budget_period"],
            "spend_signal": packet["requested_finance_decision"]["spend_signal"],
        },
    )


def build_workbench_registry() -> dict[str, Any]:
    """Return the fixture-only Workbench registry."""
    return {
        "schema_version": WORKBENCH_SCHEMA_VERSION,
        "title": "Packet Workbench",
        "subtitle": "Choose a lane, choose a registered fixture, and generate the packet without live keys or writes.",
        "mode": "fixture_only",
        "default_fixture_id": "support_triage_agent",
        "lanes": [lane.to_dict() for lane in WORKBENCH_LANES],
        "fixtures": [fixture.to_dict() for fixture in WORKBENCH_FIXTURES],
        "safety_anchor": WORKBENCH_SAFETY_ANCHOR,
        "safety_boundary": {
            "paste_input_enabled": False,
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_production": False,
            "calls_v1": False,
            "requires_human_review": True,
        },
    }


def build_workbench_result(fixture_id: str) -> dict[str, Any]:
    """Generate one normalized Workbench result from a registered public fixture."""
    fixture = _fixture_by_id(fixture_id)
    if fixture.kind == "scenario":
        return _scenario_result(fixture)
    if fixture.kind == "trial":
        return _trial_result(fixture)
    if fixture.kind == "spend":
        return _spend_result(fixture)
    raise ValueError(f"unsupported workbench fixture kind: {fixture.kind}")


def render_workbench_markdown(result: dict[str, Any]) -> str:
    """Render the normalized Workbench result as a meeting-ready Markdown artifact."""
    decision = result["decision"]
    packet_ref = result["packet_reference"]
    lines = [
        f"# {result['title']}",
        "",
        "Private engine, public proof.",
        "",
        f"- fixture: `{result['fixture']['fixture_id']}`",
        f"- lane: `{result['fixture']['lane_id']}`",
        f"- packet_id: `{packet_ref['packet_id']}`",
        f"- revision_id: `{packet_ref['revision_id']}`",
        f"- content_hash: `{packet_ref['content_hash']}`",
        f"- verdict_class: {decision['verdict_class']}",
        f"- production_access: {decision['production_access']}",
        f"- permission_grants: {decision['permission_grants']}",
        f"- external_writes: {decision['external_writes']}",
        "",
        "## Requested Systems",
        "",
        *[f"- {item}" for item in result["requested_systems"]],
        "",
        "## Blocked Claims",
        "",
        *[f"- {item}" for item in result["blocked_claims"]],
        "",
        "## Missing Proof",
        "",
        *[f"- {item}" for item in result["missing_proof"]],
        "",
        "## Reviewer Routing",
        "",
        *[f"- {item}" for item in result["reviewer_routing"]],
        "",
        "## Next Human Action",
        "",
        decision["next_human_action"],
        "",
        "## Safety Anchor",
        "",
        result["safety_anchor"],
        "",
    ]
    return "\n".join(lines)


def workbench_result_to_pretty_json(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True)
