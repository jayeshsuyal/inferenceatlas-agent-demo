"""Core transition F: Mind(t) -> Mind(t+1)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent.decision_brief import build_agent_access_decision_brief
from agent.proof_health import build_proof_health_report
from agent.public_contract import validate_public_review_artifacts
from agent.scenarios import SCENARIOS, build_scenario_packet

from .cortex import apply_patch, propose_patch
from .model import (
    CORTEX_WAKE_THRESHOLD,
    Mind,
    Tension,
)


def init_mind(scenario: str) -> Mind:
    if scenario not in SCENARIOS:
        raise KeyError(f"unknown scenario: {scenario}")
    packet = build_scenario_packet(scenario)
    return Mind(scenario=scenario, tick=0, packet=packet)


def _perceive(mind: Mind) -> List[str]:
    observations = list(mind.internal.get("observations", []))
    mind.internal["observations"] = []
    return observations


def _apply_rules(mind: Mind, observations: List[str]) -> None:
    packet = build_scenario_packet(mind.scenario)
    extra = mind.internal.get("extra_evidence_notes", [])
    if extra:
        notes = list(packet.get("evidence_notes", []))
        for item in extra:
            if item not in notes:
                notes.append(item)
        packet["evidence_notes"] = notes
    if observations:
        notes = list(packet.get("evidence_notes", []))
        for text in observations:
            notes.append(
                {
                    "source": "human_observation",
                    "status": "pending_review",
                    "note": text[:2000],
                }
            )
        packet["evidence_notes"] = notes
        mind.internal["extra_evidence_notes"] = [
            n for n in mind.internal.get("extra_evidence_notes", []) if n in notes
        ]
    mind.packet = packet


def _build_tensions(mind: Mind, proof_health: dict) -> List[Tension]:
    packet = mind.packet
    tensions: List[Tension] = []
    missing = packet.get("missing_proof", [])
    if missing:
        tensions.append(
            Tension(
                id=f"{mind.scenario}-proof-debt",
                type="proof_debt",
                strength=min(1.0, 0.15 * len(missing)),
                target=mind.scenario,
                detail=f"{len(missing)} open proof items",
            )
        )
    score = float(proof_health.get("overall_score", 100))
    if score < 80:
        tensions.append(
            Tension(
                id=f"{mind.scenario}-prediction-error",
                type="prediction_error",
                strength=min(1.0, (80 - score) / 80),
                target="proof_health",
                detail=f"overall_score={score}",
            )
        )
    predictions = mind.internal.setdefault("predictions", {})
    predictions["proof_health_score"] = score
    predictions["overall_status"] = proof_health.get("overall_status", "unknown")
    return tensions


def _predict(mind: Mind) -> dict:
    return build_proof_health_report(mind.scenario)


def _log_transition(mind: Mind, event: str, detail: dict) -> None:
    log = mind.internal.setdefault("transition_log", [])
    log.append(
        {
            "tick": mind.tick,
            "event": event,
            "at": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
    )
    if len(log) > 50:
        mind.internal["transition_log"] = log[-50:]


def step(mind: Mind, *, allow_cortex: bool = True) -> Mind:
    """Apply one state transition."""
    mind = copy.deepcopy(mind)
    mind.tick += 1
    observations = _perceive(mind)
    _apply_rules(mind, observations)
    proof_health = _predict(mind)
    tensions = _build_tensions(mind, proof_health)
    mind.internal["tensions"] = [t.to_dict() for t in tensions]

    cortex_applied = False
    budget = int(mind.internal.get("cortex_budget", 0))
    if (
        allow_cortex
        and budget > 0
        and mind.max_tension_strength() >= CORTEX_WAKE_THRESHOLD
    ):
        patch = propose_patch(mind)
        if patch:
            before = copy.deepcopy(mind.packet)
            mind.packet = apply_patch(mind.packet, patch)
            if mind.packet != before:
                for item in patch.get("ops", []):
                    if patch.get("target") == "evidence_notes" and item.get("op") == "append":
                        extra = mind.internal.setdefault("extra_evidence_notes", [])
                        val = item.get("value")
                        if val and val not in extra:
                            extra.append(val)
                mind.internal["cortex_budget"] = budget - 1
                cortex_applied = True
                _log_transition(mind, "cortex_patch", {"patch": patch})

    brief = build_agent_access_decision_brief(mind.packet)
    errors = validate_public_review_artifacts(mind.packet, brief)
    if errors:
        mind.packet = build_scenario_packet(mind.scenario)
        _apply_rules(mind, [])
        _log_transition(
            mind,
            "contract_rollback",
            {"errors": errors[:5]},
        )
    else:
        _log_transition(
            mind,
            "step_ok",
            {
                "observations": len(observations),
                "tensions": len(tensions),
                "cortex": cortex_applied,
                "max_tension": mind.max_tension_strength(),
            },
        )

    return mind
