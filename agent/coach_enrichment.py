"""Enrich deterministic ReviewRun coach answers with session, v1 governance, and LLM narration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from . import config
from .coach_narration import narrate_coach_sections
from .coach_session import (
    append_coach_turn,
    coach_session_summary,
    format_coach_session_context,
    record_coach_checkpoint,
)
from .review_run import ReviewRun
from .v1_client import governance_copilot, is_v1_configured

COACH_ENRICHMENT_SCHEMA_VERSION = "coach_enrichment.v0"


def extract_governance_narration(gov: Mapping[str, Any]) -> str:
    """Return user-facing governance prose only (strip deterministic context blocks)."""
    narration = str(gov.get("narration") or "").strip()
    if narration:
        return narration
    reply = str(gov.get("reply") or "").strip()
    if not reply:
        return ""
    for marker in (
        "### IA Governance analysis\n",
        "### IA Governance narrative\n",
    ):
        if marker in reply:
            tail = reply.split(marker, 1)[1]
            tail = tail.split("---\n*", 1)[0].strip()
            if tail:
                return tail
    if "### Governance state" in reply or "### Coach session" in reply:
        return ""
    if reply.startswith("### "):
        return ""
    return reply


def _governance_context_block(run: ReviewRun, answer: Mapping[str, Any], session_context: str) -> str:
    packet = run.packet or {}
    delta = packet.get("review_delta") if isinstance(packet.get("review_delta"), dict) else {}
    payload = {
        "run_id": run.run_id,
        "stage": run.stage,
        "selected_repo": run.selected_repo,
        "verdict": answer.get("verdict"),
        "packet_revision": answer.get("packet_revision"),
        "portkey_state": answer.get("portkey_state"),
        "movement_classes": answer.get("movement_classes"),
        "sections": answer.get("sections"),
        "review_delta": delta,
        "missing_proof": run.missing_proof,
        "attached_proof": run.attached_proof,
        "safety_boundary": answer.get("safety_boundary"),
    }
    return (
        f"{session_context}\n\n"
        "### ReviewRun governance state (authoritative)\n"
        f"{json.dumps(payload, sort_keys=True, default=str)[:10000]}"
    )


def enrich_review_run_coach_answer(
    run: ReviewRun,
    base_answer: dict[str, Any],
    *,
    prompt: str = "",
    chip_entities: Optional[Mapping[str, Any]] = None,
    session_id: str = "",
    store_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Layer session checkpoints, optional v1 governance, and optional LLM narration."""
    entities = dict(chip_entities or {})
    trigger = str(entities.get("reassess_trigger") or entities.get("trigger") or "").strip()
    prompt_kind = str(base_answer.get("prompt_kind") or "")

    if config.COACH_SESSION_ENABLED:
        record_coach_checkpoint(
            run.run_id,
            stage=run.stage,
            revision_id=str(base_answer.get("packet_revision") or ""),
            verdict=str(base_answer.get("verdict") or ""),
            portkey_state=str(base_answer.get("portkey_state") or ""),
            trigger=trigger or prompt_kind or run.stage,
            summary=coach_session_summary(base_answer, trigger=trigger),
            store_dir=store_dir,
        )
        append_coach_turn(
            run.run_id,
            prompt=prompt or trigger or "stage reassessment",
            prompt_kind=prompt_kind,
            stage=run.stage,
            store_dir=store_dir,
        )

    enriched = dict(base_answer)
    enriched["enrichment_schema_version"] = COACH_ENRICHMENT_SCHEMA_VERSION
    session_context = (
        format_coach_session_context(run.run_id, store_dir=store_dir)
        if config.COACH_SESSION_ENABLED
        else ""
    )
    if session_id:
        from .review_context import format_context_for_coach, get_review_context_bundle, record_flow_event

        trigger = str(entities.get("reassess_trigger") or entities.get("trigger") or "").strip()
        previous_stage = str(entities.get("previous_stage") or "").strip()
        repo_name = str((run.selected_repo or {}).get("full_name") or "")
        record_flow_event(
            session_id,
            run.run_id,
            stage=run.stage,
            previous_stage=previous_stage,
            trigger=trigger or prompt_kind or "coach",
            summary=coach_session_summary(base_answer, trigger=trigger),
            repo_full_name=repo_name,
        )
        bundle = get_review_context_bundle(session_id, run.run_id, coach_store_dir=store_dir)
        session_context = format_context_for_coach(bundle)
        if config.MEM0_ENABLED:
            from .mem0_memory import add_memory, format_mem0_context_block

            mem0_block = format_mem0_context_block(prompt or trigger or run.stage, run_id=run.run_id)
            if mem0_block:
                session_context = f"{session_context}\n\n{mem0_block}".strip()
            add_memory(
                coach_session_summary(base_answer, trigger=trigger),
                run_id=run.run_id,
                metadata={"stage": run.stage, "trigger": trigger or prompt_kind, "source": "review_run_coach"},
            )
    enriched["session_context_included"] = bool(session_context)

    providers = [str(base_answer.get("coach_provider") or "review_run_state_coach")]

    if config.COACH_V1_GOVERNANCE and is_v1_configured():
        try:
            gov = governance_copilot(
                message=prompt or "Reassess the current ReviewRun governance state.",
                governance_context=_governance_context_block(run, base_answer, session_context),
            )
            narration = extract_governance_narration(gov)
            if gov.get("ok") and narration:
                enriched["governance_narration"] = narration
                enriched["governance_source"] = str(gov.get("source", "inferenceatlas-v1-governance-copilot"))
                providers.append("v1_governance")
        except Exception as exc:
            enriched["governance_fallback_reason"] = str(exc).splitlines()[0][:180]

    narration_meta = narrate_coach_sections(
        base_answer,
        session_context=session_context,
        user_prompt=prompt,
    )
    enriched.update(narration_meta)
    if narration_meta.get("narration_live"):
        providers.append("demo_llm_narration")

    enriched["coach_provider"] = "+".join(providers)
    display = str(enriched.get("governance_narration") or "").strip()
    if not display and enriched.get("narration_live") and enriched.get("narration"):
        display = str(enriched["narration"]).strip()
    if display:
        enriched["display_narration"] = display
        enriched["reply"] = display
    else:
        sections = enriched.get("sections") or {}
        enriched["reply"] = str(sections.get("current_read") or base_answer.get("reply") or "")
    return enriched
