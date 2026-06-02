"""Structured input contract for deterministic agent-access reviews."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Environment = Literal["dev", "stage", "prod"]


@dataclass(frozen=True)
class ToolRequest:
    """One requested tool/system and the actions the agent wants to perform."""

    system: str
    requested_actions: tuple[str, ...]
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class AccessRequest:
    """Stable input to the DecisionPacket rules engine."""

    agent_name: str
    purpose: str
    environment: Environment
    requested_tools: tuple[ToolRequest, ...]
    data_classes: tuple[str, ...]
    raw_prompt: str
