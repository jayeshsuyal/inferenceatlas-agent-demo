"""Canonical public Agent Skills registry for InferenceAtlas."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .scenarios import ROOT_DIR


SKILLS_SCHEMA_VERSION = "agent_skills_registry.v0"

SkillTier = Literal["stable", "preview", "planned"]

SKILL_CATEGORIES = (
    "agent_access_review",
    "design_partner_pilot",
    "packet_lifecycle",
    "proof_integrity",
    "sponsor_readiness",
)

SKILL_TIERS = ("stable", "preview", "planned")

ALLOWED_SAFETY_BOUNDARIES = frozenset(
    {
        "no secrets accepted; role-level only",
        "no production-access claim; never approves",
        "read-only; humans approve",
        "no complete claim without verified evidence",
        "routing is recommendation; never dispatches",
        "diff is read-only; never mutates packets",
        "memo restates blocked claims; never grants access",
        "health is observational; never auto-refreshes",
        "dry-run by default; no live writes; sponsor cannot grant access",
        "no live integration path; humans review",
        "regeneration is deterministic; proof bytes locked",
    }
)


@dataclass(frozen=True)
class SkillSpec:
    id: str
    name: str
    what_it_proves: str
    command: str
    artifacts: tuple[str, ...]
    safety_boundary: str
    tier: SkillTier
    category: str
    depends_on: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "what_it_proves": self.what_it_proves,
            "command": self.command,
            "artifacts": list(self.artifacts),
            "safety_boundary": self.safety_boundary,
            "tier": self.tier,
            "category": self.category,
            "depends_on": list(self.depends_on),
        }


SKILLS: tuple[SkillSpec, ...] = (
    SkillSpec(
        id="access_request_normalization",
        name="Access Request Normalization",
        what_it_proves="Messy role-level YAML maps to a structured public access-review input.",
        command="python3 -m agent.trial examples/requests/support_triage_trial.yml --json",
        artifacts=(
            "agent/access_request.py",
            "agent/trial.py",
            "examples/requests/support_triage_trial.yml",
        ),
        safety_boundary="no secrets accepted; role-level only",
        tier="stable",
        category="agent_access_review",
    ),
    SkillSpec(
        id="decision_packet_generation",
        name="DecisionPacket Generation",
        what_it_proves="A structured access request becomes a schema-backed packet with scope, proof debt, reviewers, and safety state.",
        command="python3 -m agent.review --scenario support_triage_agent --artifact packet --format json",
        artifacts=(
            "agent/packet.py",
            "schemas/decision_packet.schema.json",
            "examples/generated/support_triage_agent.packet.json",
        ),
        safety_boundary="no production-access claim; never approves",
        tier="stable",
        category="agent_access_review",
        depends_on=("access_request_normalization",),
    ),
    SkillSpec(
        id="policy_gate_evaluation",
        name="Policy Gate Evaluation",
        what_it_proves="Public policy rules block critical, admin, and prod-write scope before validation moves.",
        command="python3 -m agent.gate --all",
        artifacts=(
            "agent/gate.py",
            "policy/agent_access.yml",
        ),
        safety_boundary="read-only; humans approve",
        tier="stable",
        category="agent_access_review",
        depends_on=("decision_packet_generation",),
    ),
    SkillSpec(
        id="proof_debt_extraction",
        name="Proof Debt Extraction",
        what_it_proves="Missing evidence and unsupported claims stay visible as reviewer work.",
        command="python3 -m agent.review --scenario support_triage_agent --artifact packet --format json",
        artifacts=(
            "agent/rules.py",
            "examples/generated/support_triage_agent.packet.json",
        ),
        safety_boundary="no complete claim without verified evidence",
        tier="stable",
        category="agent_access_review",
        depends_on=("decision_packet_generation",),
    ),
    SkillSpec(
        id="reviewer_routing",
        name="Reviewer Routing",
        what_it_proves="Review owners and action items are derived from the packet instead of hidden in prose.",
        command="python3 -m agent.review --scenario support_triage_agent --artifact brief --format json",
        artifacts=(
            "agent/rules.py",
            "examples/generated/support_triage_agent.decision_brief.json",
        ),
        safety_boundary="routing is recommendation; never dispatches",
        tier="stable",
        category="agent_access_review",
        depends_on=("decision_packet_generation",),
    ),
    SkillSpec(
        id="risk_aware_scenario_differentiation",
        name="Risk-Aware Scenario Differentiation",
        what_it_proves="Low, medium/high, and critical requests produce materially different review postures.",
        command="python3 -m agent.review --list",
        artifacts=(
            "agent/scenarios.py",
            "examples/generated/read_only_analytics_agent.packet.json",
            "examples/generated/support_triage_agent.packet.json",
            "examples/generated/admin_code_fix_bot.packet.json",
        ),
        safety_boundary="read-only; humans approve",
        tier="stable",
        category="agent_access_review",
        depends_on=("decision_packet_generation",),
    ),
    SkillSpec(
        id="design_partner_evidence_replay",
        name="Sponsor Evidence Replay",
        what_it_proves="Sponsor proof slots attach to a trial decision while verdict, approvals, grants, writes, and production mutation stay locked.",
        command="python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
        artifacts=(
            "agent/trial_evidence_replay.py",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "examples/generated/support_triage_trial.evidence_replay.json",
        ),
        safety_boundary="dry-run by default; no live writes; sponsor cannot grant access",
        tier="stable",
        category="design_partner_pilot",
        depends_on=(
            "design_partner_outcome_memo",
            "design_partner_trial_runner",
            "sponsor_proof_readiness",
        ),
    ),
    SkillSpec(
        id="design_partner_outcome_memo",
        name="Design Partner Outcome Memo",
        what_it_proves="A trial request becomes a meeting-ready decision with can-move scope, blocked scope, proof owners, and reviewer routes.",
        command="python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
        artifacts=(
            "agent/trial_outcome_memo.py",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.outcome_memo.json",
        ),
        safety_boundary="memo restates blocked claims; never grants access",
        tier="stable",
        category="design_partner_pilot",
        depends_on=(
            "access_request_normalization",
            "decision_packet_generation",
            "design_partner_trial_runner",
            "outcome_memo_generation",
        ),
    ),
    SkillSpec(
        id="design_partner_trial_runner",
        name="Design Partner Trial Runner",
        what_it_proves="A role-level trial request becomes a report, packet, and access brief without live credentials.",
        command="python3 -m agent.trial examples/requests/support_triage_trial.yml",
        artifacts=(
            "agent/trial.py",
            "examples/requests/support_triage_trial.yml",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_trial.packet.json",
            "examples/generated/support_triage_trial.decision_brief.json",
        ),
        safety_boundary="no live integration path; humans review",
        tier="stable",
        category="design_partner_pilot",
        depends_on=("access_request_normalization", "decision_packet_generation"),
    ),
    SkillSpec(
        id="outcome_memo_generation",
        name="Outcome Memo Generation",
        what_it_proves="The packet becomes a concise human decision surface for what can move and what stays blocked.",
        command="python3 -m agent.outcome_memo",
        artifacts=(
            "agent/outcome_memo.py",
            "examples/generated/support_triage_agent.outcome_memo.md",
            "examples/generated/support_triage_agent.outcome_memo.json",
        ),
        safety_boundary="memo restates blocked claims; never grants access",
        tier="stable",
        category="packet_lifecycle",
        depends_on=(
            "decision_packet_generation",
            "policy_gate_evaluation",
            "proof_debt_extraction",
            "reviewer_routing",
        ),
    ),
    SkillSpec(
        id="packet_diff_generation",
        name="Packet Diff Generation",
        what_it_proves="Scenario packets expose load-bearing differences across risk levels.",
        command="python3 -m agent.packet_diff",
        artifacts=(
            "agent/packet_diff.py",
            "examples/generated/packet_diff.md",
            "examples/generated/packet_diff.json",
        ),
        safety_boundary="diff is read-only; never mutates packets",
        tier="stable",
        category="packet_lifecycle",
        depends_on=("decision_packet_generation", "risk_aware_scenario_differentiation"),
    ),
    SkillSpec(
        id="artifact_integrity_verification",
        name="Artifact Integrity Verification",
        what_it_proves="Checked-in proof inventory is compared against deterministic generator output.",
        command="python3 -m agent.verify_artifacts",
        artifacts=(
            "agent/verify_artifacts.py",
            "tests/test_verify_artifacts.py",
        ),
        safety_boundary="regeneration is deterministic; proof bytes locked",
        tier="stable",
        category="proof_integrity",
        depends_on=(
            "decision_packet_generation",
            "design_partner_evidence_replay",
            "design_partner_outcome_memo",
            "design_partner_trial_runner",
            "outcome_memo_generation",
            "packet_diff_generation",
            "proof_health_drift_detection",
            "sponsor_proof_readiness",
        ),
    ),
    SkillSpec(
        id="proof_health_drift_detection",
        name="Proof Health / Drift Detection",
        what_it_proves="Packet assumptions, reviewer gates, and refresh timing are surfaced before access expands.",
        command="python3 -m agent.proof_health",
        artifacts=(
            "agent/proof_health.py",
            "examples/generated/support_triage_agent.proof_health.md",
            "examples/generated/support_triage_agent.proof_health.json",
        ),
        safety_boundary="health is observational; never auto-refreshes",
        tier="stable",
        category="proof_integrity",
        depends_on=("decision_packet_generation", "reviewer_routing"),
    ),
    SkillSpec(
        id="sponsor_proof_readiness",
        name="Sponsor Proof Readiness",
        what_it_proves="Sponsor adapters show where live proof can attach while remaining non-executing.",
        command="python3 -m agent.sponsor_readiness",
        artifacts=(
            "agent/adapters",
            "agent/sponsor_readiness.py",
            "examples/generated/sponsor_live_readiness.md",
            "examples/generated/sponsor_live_readiness.json",
        ),
        safety_boundary="dry-run by default; no live writes; sponsor cannot grant access",
        tier="stable",
        category="sponsor_readiness",
        depends_on=("policy_gate_evaluation",),
    ),
)

COMMAND_MODULE_RE = re.compile(r"^python3\s+-m\s+(?P<module>[a-zA-Z0-9_.]+)(?:\s|$)")


def _module_from_command(command: str) -> str | None:
    match = COMMAND_MODULE_RE.match(command)
    return match.group("module") if match else None


def _artifact_status(artifact: str) -> dict[str, Any]:
    path = ROOT_DIR / artifact
    return {
        "path": artifact,
        "exists": path.exists(),
        "kind": "directory" if path.is_dir() else "file",
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def _command_status(command: str) -> dict[str, Any]:
    module_name = _module_from_command(command)
    if module_name is None:
        return {
            "command": command,
            "module": None,
            "importable": False,
        }
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - surfaced in CLI output and tests.
        return {
            "command": command,
            "module": module_name,
            "importable": False,
            "error": str(exc),
        }
    return {
        "command": command,
        "module": module_name,
        "importable": True,
    }


def skill_status(skill: SkillSpec) -> dict[str, Any]:
    command = _command_status(skill.command)
    artifacts = [_artifact_status(artifact) for artifact in skill.artifacts]
    available = command["importable"] and all(item["exists"] for item in artifacts)
    return {
        **skill.to_dict(),
        "status": "available" if available else "unavailable",
        "command_status": command,
        "artifact_status": artifacts,
    }


def build_skills_report() -> dict[str, Any]:
    skills = [skill_status(skill) for skill in SKILLS]
    stable_skills = [skill for skill in skills if skill["tier"] == "stable"]
    available_stable_skills = [skill for skill in stable_skills if skill["status"] == "available"]
    return {
        "schema_version": SKILLS_SCHEMA_VERSION,
        "mode": "offline_deterministic",
        "generated_by": "inferenceatlas-agent-demo",
        "summary": {
            "registered_skills": len(skills),
            "stable_skills": len(stable_skills),
            "available_stable_skills": len(available_stable_skills),
            "preview_skills": len([skill for skill in skills if skill["tier"] == "preview"]),
            "planned_skills": len([skill for skill in skills if skill["tier"] == "planned"]),
        },
        "skills": skills,
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
        "safety": {
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "human_approval_required": True,
        },
    }


def _skills_by_category() -> dict[str, list[SkillSpec]]:
    grouped: dict[str, list[SkillSpec]] = {category: [] for category in SKILL_CATEGORIES}
    for skill in SKILLS:
        grouped[skill.category].append(skill)
    return grouped


def _category_title(category: str) -> str:
    return category.replace("_", " ").title()


def _mermaid_node_id(skill_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", skill_id)


def render_skills_markdown() -> str:
    lines = [
        "# Agent Skills",
        "",
        "Status: generated public capability registry",
        "Purpose: show which public review skills the harness exposes, what proves each skill, and which safety boundary applies",
        "",
        "Private engine, public proof.",
        "",
        "This document is generated from `agent/skills.py`. Regenerate it with:",
        "",
        "```bash",
        "python3 -m scripts.generate_agent_skills_doc",
        "```",
        "",
        "## Summary",
        "",
        f"- Registered skills: `{len(SKILLS)}`",
        f"- Stable skills: `{len([skill for skill in SKILLS if skill.tier == 'stable'])}`",
        "- Public harness approves access: `false`",
        "- Public harness grants permissions: `false`",
        "- Public harness executes external writes: `false`",
        "",
        "## Skills Matrix",
        "",
    ]

    for category, skills in _skills_by_category().items():
        if not skills:
            continue
        lines.extend(
            [
                f"### {_category_title(category)}",
                "",
                "| Skill | Tier | What it proves | Command | Primary artifacts | Safety boundary |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for skill in skills:
            artifacts = "<br>".join(f"`{artifact}`" for artifact in skill.artifacts)
            lines.append(
                "| {name} | `{tier}` | {proof} | `{command}` | {artifacts} | {safety} |".format(
                    name=skill.name,
                    tier=skill.tier,
                    proof=skill.what_it_proves,
                    command=skill.command,
                    artifacts=artifacts,
                    safety=skill.safety_boundary,
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Dependency DAG",
            "",
            "```mermaid",
            "graph TD",
        ]
    )
    for skill in SKILLS:
        node_id = _mermaid_node_id(skill.id)
        lines.append(f'    {node_id}["{skill.name}"]')
    for skill in SKILLS:
        target_id = _mermaid_node_id(skill.id)
        for dependency in skill.depends_on:
            source_id = _mermaid_node_id(dependency)
            lines.append(f"    {source_id} --> {target_id}")
    lines.extend(
        [
            "```",
            "",
            "## Web UI (InferenceAtlas demo)",
            "",
            "In `python3 -m web`, use **+ Skills** or type **`/`** to attach skill chips",
            "(multi-select, e.g. `/packet` + `/gate`). Ask your question and **Send** —",
            "the LLM answers using concise skill context (packets, briefs, gate results),",
            "not a raw harness dump. API: `GET /api/skills`, `POST /api/chat` with",
            "`skill_ids`. Optional harness: `POST /api/skills/run`.",
            "",
            "## Review Contract",
            "",
            "- Every skill is backed by a public command and public artifact path.",
            "- Every safety boundary is allowlisted in the registry tests.",
            "- Skills may prepare proof, briefs, reports, and review surfaces.",
            "- Skills do not approve access, grant permissions, execute writes, or expose private source.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_skills_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# InferenceAtlas Agent Skills",
        "",
        "Private engine, public proof.",
        "",
        "{available} / {stable} stable skills available - {registered} registered".format(
            available=summary["available_stable_skills"],
            stable=summary["stable_skills"],
            registered=summary["registered_skills"],
        ),
        "",
    ]
    for skill in report["skills"]:
        status = "OK" if skill["status"] == "available" else "FAIL"
        lines.append(
            "[{tier}] {status} {name} - {command}".format(
                tier=skill["tier"],
                status=status,
                name=skill["name"],
                command=skill["command"],
            )
        )
    lines.extend(
        [
            "",
            "Safety: no approvals granted; no external writes; private source exposed: false",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.skills",
        description="List public InferenceAtlas agent review skills.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the skills registry report as machine-readable JSON.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print the generated Agent Skills markdown document.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.markdown:
        sys.stdout.write(render_skills_markdown())
        return 0

    report = build_skills_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_skills_report(report))
    return 0 if report["summary"]["available_stable_skills"] == report["summary"]["stable_skills"] else 1


if __name__ == "__main__":
    sys.exit(main())
