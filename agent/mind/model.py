"""Mind state model — primary artifact for the transition engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


MIND_SCHEMA_VERSION = "mind.v0"
DEFAULT_CORTEX_BUDGET = 10
CORTEX_WAKE_THRESHOLD = 0.75

# Fields the cortex may patch (append-only evidence).
PATCH_ALLOWED_TARGETS = frozenset({"evidence_notes"})

# Fields that must never change via cortex (from agent/adapters nebius contract).
PATCH_LOCKED_TOP_LEVEL = frozenset(
    {
        "verdict",
        "blocked_claims",
        "safety_state",
        "policy_gate_status",
        "approval_posture",
        "missing_proof",
        "decision",
        "tool_access_plan",
        "tool_scope",
        "data_scope",
        "reviewer_owners",
        "reviewer_action_items",
        "next_validation",
        "source_status",
    }
)


@dataclass
class Tension:
    id: str
    type: str
    strength: float
    target: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "strength": round(self.strength, 4),
            "target": self.target,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tension":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            strength=float(data["strength"]),
            target=str(data["target"]),
            detail=str(data.get("detail", "")),
        )


@dataclass
class Mind:
    scenario: str
    tick: int
    packet: Dict[str, Any]
    internal: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.internal.setdefault("schema_version", MIND_SCHEMA_VERSION)
        self.internal.setdefault("tensions", [])
        self.internal.setdefault("predictions", {})
        self.internal.setdefault("transition_log", [])
        self.internal.setdefault("observations", [])
        self.internal.setdefault("extra_evidence_notes", [])
        self.internal.setdefault("cortex_budget", DEFAULT_CORTEX_BUDGET)

    def to_dict(self) -> dict:
        return {
            "schema_version": MIND_SCHEMA_VERSION,
            "scenario": self.scenario,
            "tick": self.tick,
            "packet": self.packet,
            "internal": self.internal,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Mind":
        return cls(
            scenario=str(data["scenario"]),
            tick=int(data.get("tick", 0)),
            packet=dict(data["packet"]),
            internal=dict(data.get("internal", {})),
        )

    def top_tensions(self, n: int = 3) -> List[Tension]:
        tensions = [Tension.from_dict(t) for t in self.internal.get("tensions", [])]
        tensions.sort(key=lambda t: t.strength, reverse=True)
        return tensions[:n]

    def max_tension_strength(self) -> float:
        tensions = self.internal.get("tensions", [])
        if not tensions:
            return 0.0
        return max(float(t["strength"]) for t in tensions)
