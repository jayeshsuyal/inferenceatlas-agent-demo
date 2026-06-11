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
