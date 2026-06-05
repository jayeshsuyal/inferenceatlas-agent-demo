"""UI-facing InferenceAtlas skills — sourced from docs/AGENT_SKILLS.md / agent/skills.py."""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, List, Literal, Optional

from .decision_brief import build_agent_access_decision_brief
from .evidence_receipts import build_evidence_receipt_ledger
from .gate import evaluate_all, evaluate_gate
from .packet_diff import build_packet_diff_report
from .proof_health import build_proof_health_report
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_packet
from .skills import SKILL_CATEGORIES, SKILLS, SkillSpec, _category_title


UISkillMode = Literal["assist", "run"]

# Slash command per registry skill (unique, typed after / in the chat bar).
SLASH_BY_SKILL_ID = {
    "access_request_normalization": "normalize",
    "decision_packet_generation": "packet",
    "policy_gate_evaluation": "gate",
    "proof_debt_extraction": "proof-debt",
    "reviewer_routing": "routing",
    "risk_aware_scenario_differentiation": "scenarios",
    "design_partner_trial_runner": "trial",
    "design_partner_outcome_memo": "trial-memo",
    "design_partner_evidence_replay": "evidence",
    "outcome_memo_generation": "memo",
    "packet_diff_generation": "diff",
    "artifact_integrity_verification": "verify",
    "evidence_receipt_ledger": "receipts",
    "proof_health_drift_detection": "proof-health",
    "sponsor_proof_readiness": "sponsor",
}

# Optional harness shortcut (not a separate registry row).
EXTRA_UI_SKILLS = (
    {
        "id": "full_judge_harness",
        "slash": "judge",
        "name": "Full judge harness",
        "what_it_proves": "One command runs the full public proof path (all scenarios, contract, artifacts).",
        "command": "python3 -m agent.judge",
        "category": "proof_integrity",
        "safety_boundary": "read-only; humans approve",
        "tier": "stable",
    },
)


@dataclass(frozen=True)
class UISkill:
    id: str
    slash: str
    name: str
    what_it_proves: str
    command: str
    category: str
    category_label: str
    safety_boundary: str
    tier: str
    mode: UISkillMode
    prompt: Optional[str] = None
    artifacts: tuple[str, ...] = ()

    @property
    def slash_trigger(self) -> str:
        return f"/{self.slash}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slash": self.slash,
            "slash_trigger": self.slash_trigger,
            "name": self.name,
            "what_it_proves": self.what_it_proves,
            "command": self.command,
            "category": self.category,
            "category_label": self.category_label,
            "safety_boundary": self.safety_boundary,
            "tier": self.tier,
            "mode": self.mode,
            "prompt": self.prompt,
            "artifacts": list(self.artifacts),
        }


def _prompt_for_chat(skill: SkillSpec) -> str:
    """Optional LLM follow-up after harness skills that benefit from narration."""
    if skill.id == "decision_packet_generation":
        return (
            "Summarize the support_triage_agent DecisionPacket for a human reviewer: "
            "what is blocked, what proof is missing, and what scoped validation is allowed. "
            "Do not claim production access was granted."
        )
    if skill.id == "sponsor_proof_readiness":
        return (
            "Explain sponsor proof readiness (Nebius, Tavily, Composio) for this harness: "
            "what adds evidence vs what cannot approve access."
        )
    if skill.id == "design_partner_outcome_memo":
        return (
            "Summarize the design-partner outcome memo: what can move, what stays blocked, "
            "which proof owners are named, and why no access is granted."
        )
    if skill.id == "design_partner_evidence_replay":
        return (
            "Explain Sponsor Evidence Replay: where Tavily, Composio, Nebius, and OpenClaw "
            "attach proof, and why the sponsors cannot change the decision or grant access."
        )
    return (
        f"Explain the output of the {skill.name} harness skill for a hackathon judge. "
        f"Context: {skill.what_it_proves} Safety: {skill.safety_boundary}"
    )


def _ui_skill_from_spec(skill: SkillSpec) -> UISkill:
    slash = SLASH_BY_SKILL_ID[skill.id]
    return UISkill(
        id=skill.id,
        slash=slash,
        name=skill.name,
        what_it_proves=skill.what_it_proves,
        command=skill.command,
        category=skill.category,
        category_label=_category_title(skill.category),
        safety_boundary=skill.safety_boundary,
        tier=skill.tier,
        mode="assist",
        prompt=_prompt_for_chat(skill),
        artifacts=skill.artifacts,
    )


def build_ui_skills() -> List[UISkill]:
    skills = [_ui_skill_from_spec(s) for s in SKILLS]
    for extra in EXTRA_UI_SKILLS:
        skills.append(
            UISkill(
                id=extra["id"],
                slash=extra["slash"],
                name=extra["name"],
                what_it_proves=extra["what_it_proves"],
                command=extra["command"],
                category=extra["category"],
                category_label=_category_title(extra["category"]),
                safety_boundary=extra["safety_boundary"],
                tier=extra["tier"],
                mode="assist",
                prompt=_prompt_for_chat(
                    SkillSpec(
                        id=extra["id"],
                        name=extra["name"],
                        what_it_proves=extra["what_it_proves"],
                        command=extra["command"],
                        artifacts=(),
                        safety_boundary=extra["safety_boundary"],
                        tier="stable",
                        category=extra["category"],
                    )
                ),
                artifacts=(),
            )
        )
    return sorted(skills, key=lambda s: (s.category, s.slash))


def skills_by_category() -> List[tuple[str, str, List[UISkill]]]:
    grouped: dict[str, List[UISkill]] = {cat: [] for cat in SKILL_CATEGORIES}
    extras: List[UISkill] = []
    for skill in build_ui_skills():
        if skill.id == "full_judge_harness":
            extras.append(skill)
        else:
            grouped[skill.category].append(skill)
    out: List[tuple[str, str, List[UISkill]]] = []
    for cat in SKILL_CATEGORIES:
        if grouped[cat]:
            out.append((cat, _category_title(cat), grouped[cat]))
    if extras:
        out.append(("judge_shortcuts", "Judge harness", extras))
    return out


def find_ui_skill_by_id(skill_id: str) -> Optional[UISkill]:
    for skill in build_ui_skills():
        if skill.id == skill_id:
            return skill
    return None


def _executive_review_summary(scenario: str = "support_triage_agent") -> str:
    """Compact facts judges need — avoids dumping full packet markdown into the LLM."""
    packet = build_scenario_packet(scenario)
    brief = build_agent_access_decision_brief(packet)
    gn = brief.get("go_no_go", {})
    lines = [
        f"Scenario: {scenario}",
        f"Decision question: {packet.get('decision_question', '(unknown)')}",
        f"Production access: {gn.get('production_access')}",
        f"Scoped validation review: {gn.get('scoped_validation_review')}",
        f"External writes: {gn.get('external_writes')}",
        f"Composio dry-run only: {gn.get('composio_dry_run')}",
        "Missing proof (top items):",
    ]
    for item in packet.get("missing_proof", [])[:6]:
        lines.append(
            f"  - {item.get('item', '?')} → owner {item.get('owner', '?')}; unblocks: {item.get('unblocks', '')}"
        )
    lines.append("Blocked claims:")
    for claim in packet.get("blocked_claims", [])[:5]:
        lines.append(f"  - {claim}")
    nxt = packet.get("next_validation", {})
    lines.append(f"Next validation: {nxt.get('action', '?')}")
    lines.append(f"Recommended reviewers: {', '.join(_reviewer_names(packet)[:5])}")
    return "\n".join(lines)


def _reviewer_names(packet: dict) -> list[str]:
    names: list[str] = []
    for item in packet.get("reviewer_action_items", []):
        owner = item.get("owner") or item.get("reviewer")
        if owner and owner not in names:
            names.append(str(owner))
    return names


def _read_text(path: Path, max_chars: int = 4500) -> str:
    if not path.is_file():
        return f"(Run `python3 -m agent.judge` to generate {path.relative_to(ROOT_DIR)})"
    text = path.read_text(encoding="utf-8")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n… (truncated for chat context)"


def _context_for_skill(skill: UISkill, max_chars: int = 2800) -> str:
    sid = skill.id
    if sid in ("decision_packet_generation", "proof_debt_extraction", "reviewer_routing"):
        base = _executive_review_summary("support_triage_agent")
        if sid == "proof_debt_extraction":
            packet = build_scenario_packet("support_triage_agent")
            debt = [
                f"  - {i.get('item')}: owner={i.get('owner')}; blocks={i.get('blocks', i.get('unblocks', ''))}"
                for i in packet.get("missing_proof", [])
            ]
            return "Proof debt register:\n" + "\n".join(debt) + "\n\n" + base
        if sid == "reviewer_routing":
            packet = build_scenario_packet("support_triage_agent")
            actions = [
                f"  - {a.get('owner', '?')}: {a.get('action', '')} (blocks: {a.get('blocks', '')})"
                for a in packet.get("reviewer_action_items", [])[:8]
            ]
            return "Reviewer routing:\n" + "\n".join(actions) + "\n\n" + base
        return base

    if sid == "policy_gate_evaluation":
        lines = ["Policy gate (all scenarios):"]
        for scenario in SCENARIOS:
            gate = evaluate_gate(scenario)
            safety = gate.get("safety_state", {})
            lines.append(
                f"- {scenario}: {gate.get('decision')} — {gate.get('reason', '')[:120]}"
            )
            lines.append(
                f"    production={safety.get('production_access')}, "
                f"validation={safety.get('scoped_validation_review')}"
            )
        return "\n".join(lines)[:max_chars]

    if sid in ("risk_aware_scenario_differentiation", "packet_diff_generation"):
        report = build_packet_diff_report()
        spread = report.get("scenario_spread", [])
        lines = ["Scenario spread (packet diff):"]
        for row in spread:
            lines.append(
                f"- {row.get('scenario')}: gate={row.get('policy_gate_decision')}, "
                f"production={row.get('production_access')}, "
                f"proof gaps={row.get('missing_proof_count')}, "
                f"movement={row.get('packet_movement')}"
            )
        return "\n".join(lines)[:max_chars]

    if sid == "outcome_memo_generation":
        return _read_text(GENERATED_DIR / "support_triage_agent.outcome_memo.md", max_chars)

    if sid == "evidence_receipt_ledger":
        ledger = build_evidence_receipt_ledger(
            build_scenario_packet("support_triage_agent"),
            "support_triage_agent",
        )
        summary = ledger["summary"]
        finance = ledger["finance_procurement"]
        return "\n".join(
            [
                "Evidence Receipt Ledger:",
                f"- decision lock: {ledger['decision_lock_before']} -> {ledger['decision_lock_after']}",
                f"- receipts: {summary['receipt_count']}",
                f"- tool scope receipts: {summary['tool_scope_receipts']}",
                f"- proof debt receipts: {summary['proof_debt_receipts']}",
                f"- reviewer route receipts: {summary['reviewer_route_receipts']}",
                f"- cost/procurement receipts: {summary['cost_procurement_receipts']}",
                f"- budget owner required: {finance['budget_owner_required']}",
                f"- token/tool spend cap required: {finance['token_or_tool_spend_cap_required']}",
                f"- approval granted: {finance['approval_granted']}",
            ]
        )[:max_chars]

    if sid == "proof_health_drift_detection":
        report = build_proof_health_report("support_triage_agent")
        dims = report.get("dimensions", [])[:4]
        lines = [
            f"Proof health: score={report.get('overall_score')}, status={report.get('overall_status')}",
            "Dimensions:",
        ]
        for d in dims:
            lines.append(f"  - {d.get('name')}: {d.get('score')} ({d.get('status')})")
        return "\n".join(lines)[:max_chars]

    if sid in ("access_request_normalization", "design_partner_trial_runner"):
        return _read_text(GENERATED_DIR / "support_triage_trial_report.md", min(max_chars, 2200))

    if sid == "design_partner_outcome_memo":
        return _read_text(GENERATED_DIR / "support_triage_trial.outcome_memo.md", min(max_chars, 2600))

    if sid == "design_partner_evidence_replay":
        return _read_text(GENERATED_DIR / "support_triage_trial.evidence_replay.md", min(max_chars, 2600))

    if sid == "sponsor_proof_readiness":
        return _read_text(GENERATED_DIR / "sponsor_live_readiness.md", min(max_chars, 2200))

    if sid == "artifact_integrity_verification":
        return (
            "Artifact integrity: deterministic verify_artifacts checks public generated files.\n"
            + _read_text(GENERATED_DIR / "trust_receipt.md", min(max_chars, 1800))
        )

    if sid == "full_judge_harness":
        gates = evaluate_all()
        lines = ["Judge harness summary (live):"]
        for name, gate in gates.items():
            lines.append(f"- {name}: {gate.get('decision')}")
        lines.append(
            "\nTrust receipt excerpt:\n"
            + _read_text(GENERATED_DIR / "trust_receipt.md", 1200)
        )
        return "\n".join(lines)[:max_chars]

    return f"Harness command: {skill.command}"


def skill_suggested_questions(skill_ids: List[str]) -> List[str]:
    """Short prompts shown in the UI when skills are attached."""
    hints: List[str] = []
    ids = set(skill_ids)
    if ids & {"decision_packet_generation", "proof_debt_extraction", "reviewer_routing"}:
        hints.append("What blocks production access for support triage?")
    if "policy_gate_evaluation" in ids:
        hints.append("Which scenarios does the policy gate block vs allow validation?")
    if ids & {"packet_diff_generation", "risk_aware_scenario_differentiation"}:
        hints.append("How do the three scenarios differ on proof and production access?")
    if "evidence_receipt_ledger" in ids:
        hints.append("Which receipts prove the packet still needs human and finance review?")
    if "full_judge_harness" in ids:
        hints.append("Summarize the full judge proof path for a hackathon judge.")
    if ids & {"design_partner_outcome_memo", "design_partner_evidence_replay"}:
        hints.append("How does the design-partner trial move forward without sponsor tools taking over?")
    if not hints:
        hints.append("Summarize what these skills prove and what humans must still approve.")
    return hints[:3]


def build_skill_context_for_chat(
    skill_ids: List[str],
    *,
    max_per_skill: int = 2800,
    max_total: int = 9000,
) -> tuple[str, List[dict]]:
    """Build LLM context blocks for selected assist skills."""
    blocks: List[str] = []
    used: List[dict] = []
    total = 0
    for skill_id in skill_ids:
        skill = find_ui_skill_by_id(skill_id)
        if not skill:
            continue
        ctx = _context_for_skill(skill, max_chars=max_per_skill)
        block = (
            f"### {skill.slash_trigger} — {skill.name}\n"
            f"{skill.what_it_proves}\n\n"
            f"{ctx}"
        )
        if total + len(block) > max_total:
            block = block[: max(0, max_total - total)] + "\n… (context truncated)"
        blocks.append(block)
        used.append(skill.to_dict())
        total += len(block)
        if total >= max_total:
            break
    return "\n\n".join(blocks), used


def compose_message_with_skills(
    user_message: str,
    skill_ids: List[str],
    *,
    position: str = "prepend",
) -> tuple[str, List[dict]]:
    """Wrap user text with selected skill context for the LLM."""
    message = user_message.strip()
    context, used = build_skill_context_for_chat(skill_ids)
    if not used:
        return message, []

    names = ", ".join(s["slash_trigger"] for s in used)
    wrapper = (
        f"Attached skills: {names}\n\n"
        f"--- HARNESS FACTS (authoritative) ---\n\n{context}\n\n"
        f"--- QUESTION ---\n\n"
    )

    if position == "append":
        if not message:
            message = "Summarize the harness facts above for a hackathon judge."
        return f"{message}\n\n{wrapper}{message}", used
    if not message:
        message = (
            "Give an executive summary: production access, scoped validation, "
            "top proof gaps, and who must approve next."
        )
    return f"{wrapper}{message}", used


def find_ui_skill(query: str) -> Optional[UISkill]:
    q = query.strip().lstrip("/").lower()
    if not q:
        return None
    for skill in build_ui_skills():
        if q == skill.slash or q == skill.id.replace("_", "-"):
            return skill
        if q in skill.name.lower():
            return skill
    return None


def _parse_registry_command(command: str) -> List[str]:
    parts = shlex.split(command)
    if not parts or parts[0] != "python3" or len(parts) < 3 or parts[1] != "-m":
        raise ValueError(f"command not allowed: {command}")
    return [sys.executable, "-m", parts[2], *parts[3:]]


def run_ui_skill(skill_id: str, *, timeout_sec: int = 120) -> dict[str, Any]:
    skill = next((s for s in build_ui_skills() if s.id == skill_id), None)
    if not skill:
        raise KeyError(f"unknown skill: {skill_id}")
    if skill.mode != "run":
        raise ValueError(f"skill {skill_id} is not runnable")

    argv = _parse_registry_command(skill.command)
    proc = subprocess.run(
        argv,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    output = stdout if stdout else stderr
    if stdout and stderr:
        output = f"{stdout}\n\n--- stderr ---\n{stderr}"

    return {
        "ok": proc.returncode == 0,
        "skill": skill.to_dict(),
        "exit_code": proc.returncode,
        "output": output[:24000],
        "command": skill.command,
        "artifacts": list(skill.artifacts),
        "safety_boundary": skill.safety_boundary,
    }


def build_ui_skills_payload() -> dict[str, Any]:
    skills = build_ui_skills()
    return {
        "schema_version": "inferenceatlas_ui_skills.v0",
        "source": "docs/AGENT_SKILLS.md",
        "registry_command": "python3 -m agent.skills",
        "count": len(skills),
        "skills": [s.to_dict() for s in skills],
        "categories": [
            {"id": cat_id, "label": label, "skills": [s.to_dict() for s in items]}
            for cat_id, label, items in skills_by_category()
        ],
        "help": "Type / or + to attach skills as chips, then ask your question — the LLM answers using skill context.",
    }
