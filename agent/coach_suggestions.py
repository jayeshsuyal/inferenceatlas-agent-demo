"""Contextual Ask IA coach chips: short labels, full messages, pinned entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping, Optional

if TYPE_CHECKING:
    from .review_run import ReviewRun

COACH_SUGGESTION_SCHEMA_VERSION = "coach_suggestion.v0"
MAX_LABEL_LEN = 28
MAX_SUGGESTIONS = 3

SPEND_FIXTURES = frozenset({"ai_spend_budget_overrun"})
MCP_FIXTURES = frozenset({"mcp_tool_blast_radius"})


@dataclass(frozen=True)
class ReviewRunSuggestionContext:
    run_id: str
    stage: str
    repo_full_name: str = ""
    verdict: str = "not_generated"
    packet_id: str = ""
    revision_id: str = ""
    missing_proof: tuple[dict[str, str], ...] = ()
    attached_proof_ids: frozenset[str] = frozenset()
    portkey_state: str = "Block"
    movement_blocked: tuple[str, ...] = ()
    last_prompt_kind: str = ""


def normalize_label(text: str, *, max_len: int = MAX_LABEL_LEN) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def _chip(
    *,
    label: str,
    message: str,
    source: str,
    prompt_kind: str,
    **entities: Any,
) -> dict[str, Any]:
    payload = {
        "source": source,
        "prompt_kind": prompt_kind,
        **{key: value for key, value in entities.items() if value not in (None, "", [])},
    }
    return {
        "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
        "label": normalize_label(label),
        "message": message.strip(),
        "entities": payload,
    }


def _dedupe_suggestions(
    suggestions: list[dict[str, Any]],
    *,
    max_count: int = MAX_SUGGESTIONS,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in suggestions:
        entities = item.get("entities") or {}
        key = str(entities.get("prompt_kind") or item.get("message") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max_count:
            break
    return out


def _unresolved_missing_proof(
    missing_proof: tuple[dict[str, str], ...],
    attached_proof_ids: frozenset[str],
) -> list[dict[str, str]]:
    unresolved: list[dict[str, str]] = []
    for item in missing_proof:
        proof_id = str(item.get("id") or "").strip()
        if proof_id and proof_id in attached_proof_ids:
            continue
        unresolved.append(
            {
                "id": proof_id or str(item.get("label") or "proof"),
                "label": str(item.get("label") or proof_id or "proof").strip(),
            }
        )
    return unresolved


def review_run_context_from_run(run: ReviewRun) -> ReviewRunSuggestionContext:
    packet = run.packet or {}
    missing: list[dict[str, str]] = []
    for item in run.missing_proof or []:
        if not isinstance(item, Mapping):
            continue
        missing.append(
            {
                "id": str(item.get("id") or "").strip(),
                "label": str(item.get("label") or item.get("id") or "").strip(),
            }
        )
    attached: set[str] = set()
    for item in run.attached_proof or []:
        if isinstance(item, Mapping):
            proof_id = str(item.get("id") or "").strip()
            if proof_id:
                attached.add(proof_id)
    movement = run.movement_classes or {}
    blocked = tuple(
        str(item).strip()
        for item in list(movement.get("blocked") or [])
        if str(item).strip()
    )
    repo = (run.selected_repo or {}).get("full_name") or (run.selected_repo or {}).get("name") or ""
    portkey_state = "Block"
    preview = run.portkey_preview or {}
    if isinstance(preview, Mapping):
        portkey_state = str(preview.get("guardrail_state") or preview.get("state") or "Block")
    return ReviewRunSuggestionContext(
        run_id=run.run_id,
        stage=run.stage,
        repo_full_name=str(repo),
        verdict=str(packet.get("verdict") or "not_generated"),
        packet_id=str(packet.get("packet_id") or ""),
        revision_id=str(packet.get("revision_id") or ""),
        missing_proof=tuple(missing),
        attached_proof_ids=frozenset(attached),
        portkey_state=portkey_state,
        movement_blocked=blocked,
    )


def build_review_run_suggestions(ctx: ReviewRunSuggestionContext) -> list[dict[str, Any]]:
    repo = ctx.repo_full_name or "the selected repo"
    base = {
        "run_id": ctx.run_id,
        "repo_full_name": ctx.repo_full_name,
        "stage": ctx.stage,
        "packet_id": ctx.packet_id,
        "revision_id": ctx.revision_id,
    }
    unresolved = _unresolved_missing_proof(ctx.missing_proof, ctx.attached_proof_ids)
    suggestions: list[dict[str, Any]] = []

    if ctx.stage == "repo_not_connected":
        suggestions.append(
            _chip(
                label="Use demo repo",
                message="Walk me through using the demo repo to start a ReviewRun without OAuth.",
                source="review_run",
                prompt_kind="connect",
                **base,
            )
        )
    elif ctx.stage == "repo_selected":
        suggestions.append(
            _chip(
                label="Review access",
                message=f"What will IA review when I generate the packet for {repo}?",
                source="review_run",
                prompt_kind="movement",
                **base,
            )
        )
        suggestions.append(
            _chip(
                label="What scopes?",
                message=f"What tool scopes and movement classes should I expect for {repo} before the packet exists?",
                source="review_run",
                prompt_kind="current_read",
                **base,
            )
        )
    elif ctx.stage == "request_entered":
        suggestions.append(
            _chip(
                label="Generate packet",
                message=f"Generate the IA Packet for {repo} and tell me the expected verdict posture.",
                source="review_run",
                prompt_kind="movement",
                **base,
            )
        )
    elif ctx.stage in {"packet_generated", "sponsor_proof_collected", "portkey_previewed"}:
        if unresolved:
            first = unresolved[0]
            suggestions.append(
                _chip(
                    label=f"Missing: {first['label']}",
                    message=(
                        f"What proof is still missing for {repo} before scoped validation can move, "
                        f"especially {first['label']}?"
                    ),
                    source="review_run",
                    prompt_kind="proof",
                    missing_proof_ids=[first["id"]],
                    **base,
                )
            )
        suggestions.append(
            _chip(
                label="Can this move?",
                message=f"Can this agent access request move for {repo} under the current packet verdict `{ctx.verdict}`?",
                source="review_run",
                prompt_kind="movement",
                **base,
            )
        )
        suggestions.append(
            _chip(
                label=f"Portkey: {ctx.portkey_state}",
                message=(
                    f"What will Portkey do with packet {ctx.packet_id or 'for this review'} "
                    f"while proof is unresolved for {repo}?"
                ),
                source="review_run",
                prompt_kind="portkey",
                **base,
            )
        )
    elif ctx.stage == "proof_attached":
        suggestions.append(
            _chip(
                label="Rerun review",
                message=(
                    f"I attached proof for {repo}. What should change when I regenerate the packet "
                    f"from revision {ctx.revision_id or 'the current revision'}?"
                ),
                source="review_run",
                prompt_kind="rerun",
                **base,
            )
        )
        suggestions.append(
            _chip(
                label="Portkey after rerun",
                message=f"How should Portkey read this review after rerun for {repo}?",
                source="review_run",
                prompt_kind="portkey",
                **base,
            )
        )
    elif ctx.stage == "ready_to_export":
        suggestions.append(
            _chip(
                label="Export brief",
                message=f"What should I export from this ReviewRun for {repo} and who still must review?",
                source="review_run",
                prompt_kind="export",
                **base,
            )
        )
        if ctx.movement_blocked:
            blocked = ", ".join(ctx.movement_blocked[:2])
            suggestions.append(
                _chip(
                    label="Still blocked",
                    message=f"Which scopes remain blocked for {repo} after proof attach: {blocked}?",
                    source="review_run",
                    prompt_kind="movement",
                    **base,
                )
            )
        suggestions.append(
            _chip(
                label="Open ProofGraph",
                message=f"Show me the ProofGraph path for ReviewRun {ctx.run_id} on {repo}.",
                source="review_run",
                prompt_kind="proofgraph",
                chip_action="open_proofgraph",
                **base,
            )
        )

    return _dedupe_suggestions(suggestions)


def build_follow_up_suggestions(
    ctx: ReviewRunSuggestionContext,
    *,
    prompt_kind: str,
) -> list[dict[str, Any]]:
    repo = ctx.repo_full_name or "the selected repo"
    base = {
        "run_id": ctx.run_id,
        "repo_full_name": ctx.repo_full_name,
        "stage": ctx.stage,
        "packet_id": ctx.packet_id,
        "revision_id": ctx.revision_id,
    }
    unresolved = _unresolved_missing_proof(ctx.missing_proof, ctx.attached_proof_ids)
    follow_ups: list[dict[str, Any]] = []

    if prompt_kind == "movement" and unresolved:
        first = unresolved[0]
        follow_ups.append(
            _chip(
                label=f"Missing: {first['label']}",
                message=f"What proof is missing for {repo}, starting with {first['label']}?",
                source="review_run",
                prompt_kind="proof",
                missing_proof_ids=[first["id"]],
                **base,
            )
        )
    elif prompt_kind == "proof" and ctx.stage != "ready_to_export":
        follow_ups.append(
            _chip(
                label="Who reviews?",
                message=f"Who must review the missing proof for {repo} before movement?",
                source="review_run",
                prompt_kind="reviewers",
                **base,
            )
        )
    elif prompt_kind in {"portkey", "movement"} and ctx.stage == "proof_attached":
        follow_ups.append(
            _chip(
                label="Rerun review",
                message=f"Regenerate the IA Packet for {repo} using the proof I attached.",
                source="review_run",
                prompt_kind="rerun",
                **base,
            )
        )

    return _dedupe_suggestions(follow_ups)


def suggestions_for_run(
    run: ReviewRun,
    *,
    last_prompt_kind: str = "",
) -> list[dict[str, Any]]:
    ctx = review_run_context_from_run(run)
    if last_prompt_kind:
        ctx = ReviewRunSuggestionContext(
            run_id=ctx.run_id,
            stage=ctx.stage,
            repo_full_name=ctx.repo_full_name,
            verdict=ctx.verdict,
            packet_id=ctx.packet_id,
            revision_id=ctx.revision_id,
            missing_proof=ctx.missing_proof,
            attached_proof_ids=ctx.attached_proof_ids,
            portkey_state=ctx.portkey_state,
            movement_blocked=ctx.movement_blocked,
            last_prompt_kind=last_prompt_kind,
        )
    primary = build_review_run_suggestions(ctx)
    if last_prompt_kind:
        follow_ups = build_follow_up_suggestions(ctx, prompt_kind=last_prompt_kind)
        return _dedupe_suggestions(follow_ups + primary)
    return primary


def build_packet_advisor_suggestions_from_result(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixture = result.get("fixture") or {}
    fixture_id = str(fixture.get("fixture_id") or "")
    packet_ref = result.get("packet_reference") or {}
    packet_id = str(packet_ref.get("packet_id") or "")
    revision_id = str(packet_ref.get("revision_id") or "")
    missing_proof = list(result.get("missing_proof") or [])
    verdict_class = str((result.get("decision") or {}).get("verdict_class") or "")
    lane_id = str(fixture.get("lane_id") or "")
    base = {
        "fixture": fixture_id,
        "packet_id": packet_id,
        "revision_id": revision_id,
    }
    suggestions: list[dict[str, Any]] = []

    if missing_proof:
        first = missing_proof[0]
        if isinstance(first, Mapping):
            label = str(first.get("label") or first.get("id") or "proof")
            proof_id = str(first.get("id") or label)
        else:
            label = str(first).strip() or "proof"
            proof_id = label
        suggestions.append(
            _chip(
                label=f"Missing: {label}",
                message=(
                    f"What proof is missing on fixture {fixture_id} before this packet can move, "
                    f"especially {label}?"
                ),
                source="packet_advisor",
                prompt_kind="proof",
                missing_proof_ids=[proof_id],
                **base,
            )
        )

    suggestions.append(
        _chip(
            label="Can this move?",
            message=(
                f"Can fixture {fixture_id} move under verdict `{verdict_class or 'review_required'}` "
                f"for packet {packet_id or 'this packet'}?"
            ),
            source="packet_advisor",
            prompt_kind="movement",
            **base,
        )
    )

    if fixture_id in SPEND_FIXTURES or lane_id == "ai_spend":
        suggestions.append(
            _chip(
                label="Portkey spend",
                message=(
                    f"Can Portkey allow this spend for fixture {fixture_id} "
                    f"under subscriber portkey_model_spend_gate?"
                ),
                source="packet_advisor",
                prompt_kind="portkey",
                subscriber="portkey_model_spend_gate",
                **base,
            )
        )
    elif fixture_id in MCP_FIXTURES or lane_id == "mcp_tool_access":
        suggestions.append(
            _chip(
                label="Blast radius",
                message=(
                    f"Which MCP connector actions stay blocked on fixture {fixture_id} "
                    f"and who owns review?"
                ),
                source="packet_advisor",
                prompt_kind="blast_radius",
                **base,
            )
        )
    else:
        suggestions.append(
            _chip(
                label="Who reviews?",
                message=f"Who reviews fixture {fixture_id} and what is the next human action?",
                source="packet_advisor",
                prompt_kind="reviewers",
                **base,
            )
        )

    return _dedupe_suggestions(suggestions)


def build_packet_advisor_suggestions(answer: Mapping[str, Any]) -> list[dict[str, Any]]:
    return build_packet_advisor_suggestions_from_result(answer)


def build_packet_idle_suggestions(fixture_id: str) -> list[dict[str, Any]]:
    from .workbench import build_workbench_result

    result = build_workbench_result(fixture_id)
    return build_packet_advisor_suggestions_from_result(result)


def build_intake_suggestions(current_fixture: str = "") -> list[dict[str, Any]]:
    fixture = current_fixture or "mcp_tool_blast_radius"
    fixture_label = fixture.replace("_", " ")
    base = {"fixture": fixture}
    return _dedupe_suggestions(
        [
            _chip(
                label="Can this move?",
                message=f"Can fixture {fixture} move under the current IA Packet?",
                source="intake",
                prompt_kind="movement",
                **base,
            ),
            _chip(
                label="Missing proof",
                message=f"What proof is missing for fixture {fixture_label}?",
                source="intake",
                prompt_kind="proof",
                **base,
            ),
            _chip(
                label="Who reviews?",
                message=f"Who reviews fixture {fixture_label} and what is blocked?",
                source="intake",
                prompt_kind="reviewers",
                **base,
            ),
        ]
    )


def suggestions_as_quick_actions(suggestions: list[Mapping[str, Any]]) -> list[str]:
    return [str(item.get("message") or "").strip() for item in suggestions if str(item.get("message") or "").strip()]
