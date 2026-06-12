"""Deterministic Ask IA suggestion contract for ReviewRun surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from .review_run import ReviewRun


COACH_SUGGESTION_SCHEMA_VERSION = "coach_suggestion.v0"
MAX_COACH_SUGGESTIONS = 3
MAX_COACH_SUGGESTION_LABEL_LEN = 28


def normalize_suggestion_label(label: str) -> str:
    """Keep suggestion labels compact enough for sidecar chips."""
    cleaned = " ".join(str(label or "").split()).strip()
    if len(cleaned) <= MAX_COACH_SUGGESTION_LABEL_LEN:
        return cleaned
    return f"{cleaned[: MAX_COACH_SUGGESTION_LABEL_LEN - 3]}..."


def _repo_name(run: ReviewRun) -> str:
    repo = run.selected_repo or {}
    return str(repo.get("full_name") or repo.get("name") or "").strip()


def _packet_ref(run: ReviewRun) -> tuple[str, str]:
    packet = run.packet or {}
    return (
        str(packet.get("packet_id") or "").strip(),
        str(packet.get("revision_id") or "").strip(),
    )


def _missing_proof_ids(run: ReviewRun) -> list[str]:
    ids: list[str] = []
    for item in run.missing_proof or []:
        if not isinstance(item, Mapping):
            continue
        proof_id = str(item.get("id") or "").strip()
        if proof_id:
            ids.append(proof_id)
    return ids


def _base_entities(
    run: ReviewRun,
    *,
    prompt_kind: str,
    missing_proof_ids: list[str] | None = None,
    subscriber: str = "cto",
) -> dict[str, Any]:
    packet_id, revision_id = _packet_ref(run)
    entities: dict[str, Any] = {
        "source": "review_run",
        "prompt_kind": prompt_kind,
        "run_id": run.run_id,
        "stage": run.stage,
        "repo_full_name": _repo_name(run),
        "packet_id": packet_id,
        "revision_id": revision_id,
        "missing_proof_ids": missing_proof_ids or [],
        "subscriber": subscriber,
    }
    return {key: value for key, value in entities.items() if value not in ("", None)}


def _suggestion(
    run: ReviewRun,
    *,
    label: str,
    message: str,
    prompt_kind: str,
    missing_proof_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
        "label": normalize_suggestion_label(label),
        "message": " ".join(str(message or "").split()).strip(),
        "entities": _base_entities(run, prompt_kind=prompt_kind, missing_proof_ids=missing_proof_ids),
    }


def _dedupe_suggestions(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in suggestions:
        entities = item.get("entities") or {}
        key = f"{entities.get('prompt_kind')}:{item.get('message')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= MAX_COACH_SUGGESTIONS:
            break
    return out


def suggestions_for_review_run(run: ReviewRun) -> list[dict[str, Any]]:
    """Return safe, stage-specific suggestions for the current ReviewRun.

    Suggestions are contract data only. They do not approve, mutate, write,
    or dispatch. UI placement is intentionally left to a later PR.
    """
    repo = _repo_name(run) or "this repo"
    missing_ids = _missing_proof_ids(run)
    stage = run.stage
    packet_id, _revision_id = _packet_ref(run)

    if stage == "repo_not_connected":
        return _dedupe_suggestions(
            [
                _suggestion(
                    run,
                    label="Start with demo repo",
                    message="What should I do to start a ReviewRun with the demo repo?",
                    prompt_kind="next_action",
                ),
                _suggestion(
                    run,
                    label="What gets trusted?",
                    message="What will downstream systems trust before a packet exists?",
                    prompt_kind="current_read",
                ),
            ]
        )

    if stage in {"repo_selected", "request_entered"}:
        return _dedupe_suggestions(
            [
                _suggestion(
                    run,
                    label="Review access",
                    message=f"What will IA check before generating a packet for {repo}?",
                    prompt_kind="movement",
                ),
                _suggestion(
                    run,
                    label="What now?",
                    message="idk what to do next",
                    prompt_kind="next_action",
                ),
                _suggestion(
                    run,
                    label="Portkey later?",
                    message="What will Portkey be allowed to consume after the packet exists?",
                    prompt_kind="portkey",
                ),
            ]
        )

    if stage in {"packet_generated", "sponsor_proof_collected", "portkey_previewed"}:
        return _dedupe_suggestions(
            [
                _suggestion(
                    run,
                    label="What now?",
                    message="idk what to do next",
                    prompt_kind="next_action",
                    missing_proof_ids=missing_ids,
                ),
                _suggestion(
                    run,
                    label="Missing proof",
                    message=f"What proof is missing before {repo} can move from this packet?",
                    prompt_kind="proof",
                    missing_proof_ids=missing_ids,
                ),
                _suggestion(
                    run,
                    label="Portkey impact",
                    message=f"What will Portkey do with packet {packet_id or 'for this ReviewRun'}?",
                    prompt_kind="portkey",
                    missing_proof_ids=missing_ids,
                ),
            ]
        )

    if stage == "proof_attached":
        return _dedupe_suggestions(
            [
                _suggestion(
                    run,
                    label="Regenerate packet",
                    message="what next",
                    prompt_kind="next_action",
                    missing_proof_ids=missing_ids,
                ),
                _suggestion(
                    run,
                    label="Why unchanged?",
                    message="Why did attaching proof not approve access or change movement yet?",
                    prompt_kind="proof",
                    missing_proof_ids=missing_ids,
                ),
                _suggestion(
                    run,
                    label="Portkey still block?",
                    message="What does Portkey do before the packet is regenerated?",
                    prompt_kind="portkey",
                    missing_proof_ids=missing_ids,
                ),
            ]
        )

    if stage == "ready_to_export":
        proofgraph = _suggestion(
            run,
            label="Open ProofGraph",
            message=(
                f"Show me the ProofGraph path for ReviewRun {run.run_id} "
                f"on {repo}."
            ),
            prompt_kind="proofgraph",
        )
        proofgraph["entities"]["chip_action"] = "open_proofgraph"
        return _dedupe_suggestions(
            [
                _suggestion(
                    run,
                    label="Export brief",
                    message="idk what to do next",
                    prompt_kind="next_action",
                ),
                _suggestion(
                    run,
                    label="Still blocked?",
                    message="What remains blocked after the updated packet?",
                    prompt_kind="movement",
                ),
                _suggestion(
                    run,
                    label="Portkey impact",
                    message="What will Portkey do with the updated packet?",
                    prompt_kind="portkey",
                ),
                proofgraph,
            ]
        )

    return _dedupe_suggestions(
        [
            _suggestion(
                run,
                label="Current read",
                message="What can Ask IA answer from the current ReviewRun state?",
                prompt_kind="current_read",
            )
        ]
    )


SPEND_FIXTURES = frozenset({"ai_spend_budget_overrun"})
MCP_FIXTURES = frozenset({"mcp_tool_blast_radius"})


def review_run_context_from_run(run: ReviewRun) -> dict[str, Any]:
    """Compact ReviewRun context for follow-up chip generation."""
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
    repo = _repo_name(run)
    portkey_state = "Block"
    preview = run.portkey_preview or {}
    if isinstance(preview, Mapping):
        portkey_state = str(preview.get("guardrail_state") or preview.get("state") or "Block")
    return {
        "run_id": run.run_id,
        "stage": run.stage,
        "repo_full_name": repo,
        "verdict": str(packet.get("verdict") or "not_generated"),
        "packet_id": str(packet.get("packet_id") or ""),
        "revision_id": str(packet.get("revision_id") or ""),
        "missing_proof": tuple(missing),
        "attached_proof_ids": frozenset(attached),
        "portkey_state": portkey_state,
        "movement_blocked": blocked,
    }


def _unresolved_missing_proof(
    missing_proof: tuple[dict[str, str], ...],
    attached_proof_ids: frozenset[str],
) -> list[dict[str, str]]:
    unresolved: list[dict[str, str]] = []
    for item in missing_proof:
        proof_id = str(item.get("id") or "").strip()
        if proof_id and proof_id in attached_proof_ids:
            continue
        unresolved.append(item)
    return unresolved


def _follow_up_chip(
    ctx: Mapping[str, Any],
    *,
    label: str,
    message: str,
    prompt_kind: str,
    missing_proof_ids: list[str] | None = None,
    extra_entities: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entities = {
        "source": "review_run",
        "prompt_kind": prompt_kind,
        "run_id": ctx.get("run_id") or "",
        "stage": ctx.get("stage") or "",
        "repo_full_name": ctx.get("repo_full_name") or "",
        "packet_id": ctx.get("packet_id") or "",
        "revision_id": ctx.get("revision_id") or "",
        "missing_proof_ids": missing_proof_ids or [],
        "subscriber": "cto",
    }
    if extra_entities:
        entities.update({key: value for key, value in extra_entities.items() if value not in ("", None)})
    return {
        "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
        "label": normalize_suggestion_label(label),
        "message": " ".join(str(message or "").split()).strip(),
        "entities": {key: value for key, value in entities.items() if value not in ("", None)},
    }


def build_follow_up_suggestions(
    ctx: Mapping[str, Any],
    *,
    prompt_kind: str,
) -> list[dict[str, Any]]:
    """Return contextual follow-up chips after a coach answer."""
    repo = str(ctx.get("repo_full_name") or "the selected repo")
    missing_proof = tuple(dict(item) for item in ctx.get("missing_proof") or ())
    attached_proof_ids = frozenset(ctx.get("attached_proof_ids") or ())
    unresolved = _unresolved_missing_proof(missing_proof, attached_proof_ids)
    follow_ups: list[dict[str, Any]] = []

    if prompt_kind == "movement" and unresolved:
        first = unresolved[0]
        follow_ups.append(
            _follow_up_chip(
                ctx,
                label=f"Missing: {first['label']}",
                message=f"What proof is missing for {repo}, starting with {first['label']}?",
                prompt_kind="proof",
                missing_proof_ids=[first["id"]],
            )
        )
    elif prompt_kind == "proof" and ctx.get("stage") != "ready_to_export":
        follow_ups.append(
            _follow_up_chip(
                ctx,
                label="Who reviews?",
                message=f"Who must review the missing proof for {repo} before movement?",
                prompt_kind="reviewers",
            )
        )
    elif prompt_kind in {"portkey", "movement"} and ctx.get("stage") == "proof_attached":
        follow_ups.append(
            _follow_up_chip(
                ctx,
                label="Rerun review",
                message=f"Regenerate the IA Packet for {repo} using the proof I attached.",
                prompt_kind="next_action",
            )
        )
    elif prompt_kind == "proofgraph":
        follow_ups.append(
            _follow_up_chip(
                ctx,
                label="Open ProofGraph",
                message=f"Show me the ProofGraph path for ReviewRun {ctx.get('run_id')} on {repo}.",
                prompt_kind="proofgraph",
                extra_entities={"chip_action": "open_proofgraph"},
            )
        )

    return _dedupe_suggestions(follow_ups)


def coach_answer_suggestions(
    run: ReviewRun,
    *,
    prompt_kind: str = "",
    prompt_text: str = "",
) -> list[dict[str, Any]]:
    """Suggestions embedded in coach answers: follow-ups after prompts, idle chips otherwise."""
    if prompt_text and prompt_kind:
        ctx = review_run_context_from_run(run)
        follow_ups = build_follow_up_suggestions(ctx, prompt_kind=prompt_kind)
        if follow_ups:
            return follow_ups
    return suggestions_for_review_run(run)


def build_packet_advisor_suggestions_from_result(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixture = result.get("fixture") or {}
    fixture_id = str(fixture.get("fixture_id") or "")
    packet_ref = result.get("packet_reference") or {}
    packet_id = str(packet_ref.get("packet_id") or "")
    revision_id = str(packet_ref.get("revision_id") or "")
    missing_proof = list(result.get("missing_proof") or [])
    verdict_class = str((result.get("decision") or {}).get("verdict_class") or "")
    lane_id = str(fixture.get("lane_id") or "")

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
            {
                "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
                "label": normalize_suggestion_label(f"Missing: {label}"),
                "message": (
                    f"What proof is missing on fixture {fixture_id} before this packet can move, "
                    f"especially {label}?"
                ),
                "entities": {
                    "source": "packet_advisor",
                    "prompt_kind": "proof",
                    "fixture": fixture_id,
                    "packet_id": packet_id,
                    "revision_id": revision_id,
                    "missing_proof_ids": [proof_id],
                    "subscriber": "cto",
                },
            }
        )

    suggestions.append(
        {
            "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
            "label": normalize_suggestion_label("Can this move?"),
            "message": (
                f"Can fixture {fixture_id} move under verdict `{verdict_class or 'review_required'}` "
                f"for packet {packet_id or 'this packet'}?"
            ),
            "entities": {
                "source": "packet_advisor",
                "prompt_kind": "movement",
                "fixture": fixture_id,
                "packet_id": packet_id,
                "revision_id": revision_id,
                "subscriber": "cto",
            },
        }
    )

    if fixture_id in SPEND_FIXTURES or lane_id == "ai_spend":
        suggestions.append(
            {
                "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
                "label": normalize_suggestion_label("Portkey spend"),
                "message": (
                    f"Can Portkey allow this spend for fixture {fixture_id} "
                    f"under subscriber portkey_model_spend_gate?"
                ),
                "entities": {
                    "source": "packet_advisor",
                    "prompt_kind": "portkey",
                    "fixture": fixture_id,
                    "packet_id": packet_id,
                    "revision_id": revision_id,
                    "subscriber": "portkey_model_spend_gate",
                },
            }
        )
    elif fixture_id in MCP_FIXTURES or lane_id == "mcp_tool_access":
        suggestions.append(
            {
                "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
                "label": normalize_suggestion_label("Blast radius"),
                "message": (
                    f"Which MCP connector actions stay blocked on fixture {fixture_id} "
                    f"and who owns review?"
                ),
                "entities": {
                    "source": "packet_advisor",
                    "prompt_kind": "blast_radius",
                    "fixture": fixture_id,
                    "packet_id": packet_id,
                    "revision_id": revision_id,
                    "subscriber": "cto",
                },
            }
        )
    else:
        suggestions.append(
            {
                "schema_version": COACH_SUGGESTION_SCHEMA_VERSION,
                "label": normalize_suggestion_label("Who reviews?"),
                "message": f"Who reviews fixture {fixture_id} and what is the next human action?",
                "entities": {
                    "source": "packet_advisor",
                    "prompt_kind": "reviewers",
                    "fixture": fixture_id,
                    "packet_id": packet_id,
                    "revision_id": revision_id,
                    "subscriber": "cto",
                },
            }
        )

    return _dedupe_suggestions(suggestions)


def build_packet_idle_suggestions(fixture_id: str) -> list[dict[str, Any]]:
    from .workbench import build_workbench_result

    result = build_workbench_result(fixture_id)
    return build_packet_advisor_suggestions_from_result(result)
