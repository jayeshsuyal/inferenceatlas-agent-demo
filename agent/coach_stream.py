"""SSE thinking steps for ReviewRun coach stream."""

from __future__ import annotations

from typing import Any, Mapping

from . import config
from .review_run import ReviewRun
from .v1_client import is_v1_configured

COACH_SECTION_ORDER = (
    ("what_blocks_movement", "What blocks movement"),
    ("next_human_action", "Next human action"),
    ("downstream_impact", "Downstream impact"),
    ("safety", "Safety"),
)


def build_coach_thinking_steps(run: ReviewRun, answer: Mapping[str, Any]) -> list[str]:
    repo = ""
    if isinstance(run.selected_repo, dict):
        repo = str(run.selected_repo.get("full_name") or "").strip()
    repo_label = repo or "selected repo"
    steps = [
        "Reading the current ReviewRun...",
        f"Stage: {run.stage.replace('_', ' ')} · repo: {repo_label}",
    ]
    revision = answer.get("packet_revision")
    if revision:
        steps.append(f"Packet revision: {revision}")
    verdict = answer.get("verdict")
    if verdict and verdict != "not_generated":
        steps.append(f"Verdict: {str(verdict).replace('_', ' ')}")
    portkey = answer.get("portkey_state")
    if portkey:
        steps.append(f"Portkey read: {portkey}")
    steps.append("Mapping movement classes and proof debt...")
    if config.COACH_V1_GOVERNANCE and is_v1_configured():
        steps.append("Calling InferenceAtlas-v1 governance copilot...")
    if config.COACH_LLM_NARRATE and config.LLM_API_KEY:
        steps.append("Drafting coach narration (LLM bones)...")
    steps.append("Decision lock unchanged — IA did not approve or write.")
    return steps


def pick_coach_display_narration(answer: Mapping[str, Any]) -> str:
    """User-facing prose only — never raw governance context dumps."""
    if answer.get("narration_live") and answer.get("narration"):
        return str(answer["narration"]).strip()
    gov = str(answer.get("governance_narration") or "").strip()
    if gov:
        return gov
    return ""
