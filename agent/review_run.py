"""ReviewRun contract and durable local store.

A ReviewRun is the single local product spine for one agent-access review. It
can hold repo selection, indexed context, the access request, packet revisions,
proof attachment state, Portkey preview state, ProofGraph references, and Ask IA
coach state without approving access or mutating downstream systems.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .scenarios import ROOT_DIR


REVIEW_RUN_SCHEMA_VERSION = "review_run.v0"
REVIEW_RUN_RECORD_SCHEMA_VERSION = "review_run_record.v0"
DEFAULT_REVIEW_RUN_STORE_DIR = ROOT_DIR / "state" / "review_runs"

REVIEW_RUN_STAGES = (
    "repo_not_connected",
    "repo_selected",
    "request_entered",
    "packet_generated",
    "sponsor_proof_collected",
    "portkey_previewed",
    "proof_attached",
    "ready_to_export",
)

ALLOWED_STAGE_TRANSITIONS = {
    "repo_not_connected": {"repo_selected"},
    "repo_selected": {"request_entered"},
    "request_entered": {"packet_generated"},
    "packet_generated": {"sponsor_proof_collected", "portkey_previewed", "proof_attached"},
    "sponsor_proof_collected": {"portkey_previewed", "proof_attached"},
    "portkey_previewed": {"proof_attached", "ready_to_export"},
    "proof_attached": {"ready_to_export"},
    "ready_to_export": set(),
}

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|bearer|oauth|password|private[_-]?key|secret|token)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{8,}|"
    r"sk-ant-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{12,}|"
    r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})"
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _public_dict(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_public_dict(item) for item in value]
    if isinstance(value, list):
        return [_public_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _public_dict(item) for key, item in value.items()}
    return value


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _safe_run_id(run_id: str) -> str:
    if not run_id or not _RUN_ID_RE.match(run_id):
        raise ValueError("invalid review run_id")
    return run_id


def _record_path(run_id: str, store_dir: Path) -> Path:
    return store_dir / f"{_safe_run_id(run_id)}.json"


def _sanitize_public_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_sanitize_public_value(item) for item in value]
    if isinstance(value, list):
        return [_sanitize_public_value(item) for item in value]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for raw_key, raw_item in value.items():
            key = str(raw_key)
            cleaned[key] = "[redacted]" if _SECRET_KEY_RE.search(key) else _sanitize_public_value(raw_item)
        return cleaned
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub("[redacted]", value)
    return value


def _default_repo_index_summary() -> dict[str, Any]:
    return {
        "status": "not_indexed",
        "selected_repo_only": True,
        "indexed_repo_count": 0,
        "secret_redaction_applied": True,
    }


def _default_packet() -> dict[str, Any]:
    return {
        "packet_id": None,
        "revision_id": None,
        "revision_number": 0,
        "previous_revision_id": None,
        "verdict": "not_generated",
        "ready_for_rerun": False,
        "raw_agent_request_hash": None,
    }


def _default_movement_classes() -> dict[str, list[str]]:
    return {"allowed": [], "review_required": [], "blocked": []}


def _default_safety_invariants() -> dict[str, bool]:
    return {
        "read_only": True,
        "approval_granted": False,
        "spend_approved": False,
        "permissions_granted": False,
        "external_writes_enabled": False,
        "packet_mutated_without_rerun": False,
        "portkey_api_call_made": False,
        "portkey_policy_mutation_allowed": False,
        "ask_ia_can_approve": False,
        "proof_attachment_changes_verdict": False,
        "rerun_required_for_verdict_change": True,
        "human_action_required": True,
    }


def _ask_ia_state(stage: str, *, run_id: str, selected_repo: Optional[dict[str, Any]]) -> dict[str, Any]:
    repo_name = (selected_repo or {}).get("full_name") or (selected_repo or {}).get("name") or None
    next_actions = {
        "repo_not_connected": "Connect GitHub or use the demo repo.",
        "repo_selected": "Describe what the agent wants to do in this repo.",
        "request_entered": "Generate the IA Packet.",
        "packet_generated": "Collect sponsor proof.",
        "sponsor_proof_collected": "Preview the Portkey gate.",
        "portkey_previewed": "Attach missing proof or export the review brief.",
        "proof_attached": "Regenerate the packet.",
        "ready_to_export": "Export review brief and route human owners.",
    }
    return {
        "run_id": run_id,
        "stage": stage,
        "selected_repo": repo_name,
        "answer_shape": [
            "Current read",
            "What blocks movement",
            "Next human action",
            "Downstream impact",
            "Safety",
        ],
        "next_human_action": next_actions[stage],
        "safety_anchor": "IA did not approve, dispatch, grant access, or mutate downstream policy.",
    }


def _audit_event(event_type: str, *, stage: str, details: Optional[Mapping[str, Any]] = None, now: Optional[str] = None) -> dict[str, Any]:
    payload = _sanitize_public_value(dict(details or {}))
    return {
        "event_id": f"review-run-event-{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "stage": stage,
        "created_at": now or _utcnow(),
        "human_triggered": True,
        "approves_access": False,
        "grants_permissions": False,
        "mutates_downstream_policy": False,
        "details": payload,
    }


def normalize_movement_classes(value: Optional[Mapping[str, Any]] = None) -> dict[str, list[str]]:
    raw = dict(value or {})
    normalized: dict[str, list[str]] = {}
    for key in ("allowed", "review_required", "blocked"):
        items = raw.get(key, [])
        if isinstance(items, str):
            items = [items]
        normalized[key] = [str(item).strip() for item in list(items or []) if str(item).strip()]
    return _sanitize_public_value(normalized)


def _safe_portkey_preview(value: Mapping[str, Any]) -> dict[str, Any]:
    preview = _sanitize_public_value(dict(value))
    preview["api_call_made"] = False
    preview["portkey_api_call_made"] = False
    preview["policy_mutation_allowed"] = False
    preview["portkey_policy_mutation_allowed"] = False
    preview["dry_run"] = True
    return preview


@dataclass(frozen=True)
class ReviewRun:
    schema_version: str
    run_id: str
    stage: str
    created_at: str
    updated_at: str
    session_id: Optional[str] = None
    selected_repo: Optional[dict[str, Any]] = None
    repo_index_summary: dict[str, Any] = field(default_factory=_default_repo_index_summary)
    access_request: dict[str, Any] = field(default_factory=dict)
    packet: dict[str, Any] = field(default_factory=_default_packet)
    movement_classes: dict[str, list[str]] = field(default_factory=_default_movement_classes)
    missing_proof: list[dict[str, Any]] = field(default_factory=list)
    attached_proof: list[dict[str, Any]] = field(default_factory=list)
    sponsor_proof_trace: Optional[dict[str, Any]] = None
    portkey_preview: Optional[dict[str, Any]] = None
    proofgraph_ref: Optional[dict[str, Any]] = None
    ask_ia_state: dict[str, Any] = field(default_factory=dict)
    safety_invariants: dict[str, bool] = field(default_factory=_default_safety_invariants)
    audit_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _public_dict(asdict(self))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewRun":
        data = dict(value)
        stage = str(data.get("stage") or "repo_not_connected")
        if stage not in REVIEW_RUN_STAGES:
            raise ValueError("invalid review run stage")
        return cls(
            schema_version=str(data.get("schema_version") or REVIEW_RUN_SCHEMA_VERSION),
            run_id=_safe_run_id(str(data["run_id"])),
            stage=stage,
            created_at=str(data.get("created_at") or _utcnow()),
            updated_at=str(data.get("updated_at") or _utcnow()),
            session_id=data.get("session_id"),
            selected_repo=copy.deepcopy(data.get("selected_repo")),
            repo_index_summary=copy.deepcopy(data.get("repo_index_summary") or _default_repo_index_summary()),
            access_request=copy.deepcopy(data.get("access_request") or {}),
            packet=copy.deepcopy(data.get("packet") or _default_packet()),
            movement_classes=normalize_movement_classes(data.get("movement_classes")),
            missing_proof=copy.deepcopy(data.get("missing_proof") or []),
            attached_proof=copy.deepcopy(data.get("attached_proof") or []),
            sponsor_proof_trace=copy.deepcopy(data.get("sponsor_proof_trace")),
            portkey_preview=copy.deepcopy(data.get("portkey_preview")),
            proofgraph_ref=copy.deepcopy(data.get("proofgraph_ref")),
            ask_ia_state=copy.deepcopy(data.get("ask_ia_state") or {}),
            safety_invariants=copy.deepcopy(data.get("safety_invariants") or _default_safety_invariants()),
            audit_events=copy.deepcopy(data.get("audit_events") or []),
        )


def assert_stage_transition(current_stage: str, next_stage: str) -> None:
    if current_stage == next_stage:
        return
    if current_stage not in ALLOWED_STAGE_TRANSITIONS or next_stage not in ALLOWED_STAGE_TRANSITIONS[current_stage]:
        raise ValueError(f"invalid ReviewRun stage transition: {current_stage} -> {next_stage}")


def _replace_run(
    run: ReviewRun,
    *,
    stage: Optional[str] = None,
    event_type: str,
    details: Optional[Mapping[str, Any]] = None,
    now: Optional[str] = None,
    **updates: Any,
) -> ReviewRun:
    data = run.to_dict()
    next_stage = stage or run.stage
    assert_stage_transition(run.stage, next_stage)
    data.update(_sanitize_public_value(updates))
    data["stage"] = next_stage
    data["updated_at"] = now or _utcnow()
    data["ask_ia_state"] = _ask_ia_state(
        next_stage,
        run_id=run.run_id,
        selected_repo=data.get("selected_repo"),
    )
    events = list(data.get("audit_events") or [])
    events.append(_audit_event(event_type, stage=next_stage, details=details, now=now))
    data["audit_events"] = events
    return ReviewRun.from_dict(data)


def create_review_run(
    *,
    session_id: Optional[str] = None,
    selected_repo: Optional[Mapping[str, Any]] = None,
    repo_index_summary: Optional[Mapping[str, Any]] = None,
    access_request: str = "",
    now: Optional[str] = None,
) -> ReviewRun:
    """Create a ReviewRun with safe defaults and optional initial repo/request."""
    timestamp = now or _utcnow()
    run_id = f"ia-review-run-{uuid.uuid4().hex[:16]}"
    run = ReviewRun(
        schema_version=REVIEW_RUN_SCHEMA_VERSION,
        run_id=run_id,
        stage="repo_not_connected",
        created_at=timestamp,
        updated_at=timestamp,
        session_id=str(session_id)[:160] if session_id else None,
        ask_ia_state=_ask_ia_state("repo_not_connected", run_id=run_id, selected_repo=None),
        audit_events=[_audit_event("run_created", stage="repo_not_connected", now=timestamp)],
    )
    if selected_repo:
        run = select_review_run_repo(run, selected_repo, repo_index_summary=repo_index_summary, now=timestamp)
    if access_request.strip():
        if not run.selected_repo:
            raise ValueError("selected_repo is required before access_request")
        run = record_review_run_access_request(run, access_request, now=timestamp)
    return run


def select_review_run_repo(
    run: ReviewRun,
    selected_repo: Mapping[str, Any],
    *,
    repo_index_summary: Optional[Mapping[str, Any]] = None,
    now: Optional[str] = None,
) -> ReviewRun:
    """Attach exactly one selected repo and its local index summary."""
    repo = _sanitize_public_value(dict(selected_repo))
    if not (repo.get("full_name") or repo.get("name")):
        raise ValueError("selected_repo requires full_name or name")
    summary = _default_repo_index_summary()
    summary.update(_sanitize_public_value(dict(repo_index_summary or {})))
    summary["selected_repo_only"] = True
    summary["indexed_repo_count"] = 1 if summary.get("status") in {"indexed", "ready"} else int(summary.get("indexed_repo_count") or 0)
    return _replace_run(
        run,
        stage="repo_selected",
        event_type="repo_selected",
        details={"selected_repo": repo.get("full_name") or repo.get("name")},
        selected_repo=repo,
        repo_index_summary=summary,
        now=now,
    )


def record_review_run_access_request(run: ReviewRun, raw_text: str, *, now: Optional[str] = None) -> ReviewRun:
    """Record the raw agent-access request without classifying it as approval."""
    text = str(raw_text).strip()
    if not text:
        raise ValueError("access_request cannot be empty")
    if len(text) > 10000:
        raise ValueError("access_request is too large")
    payload = {
        "raw_text": _sanitize_public_value(text),
        "raw_request_hash": _digest(text),
        "classification_status": "pending_packet_generation",
    }
    return _replace_run(
        run,
        stage="request_entered",
        event_type="access_request_entered",
        details={"raw_request_hash": payload["raw_request_hash"]},
        access_request=payload,
        now=now,
    )


def record_review_run_packet(
    run: ReviewRun,
    *,
    packet_id: str,
    revision_id: str,
    verdict: str,
    movement_classes: Mapping[str, Any],
    missing_proof: Optional[list[Mapping[str, Any]]] = None,
    sponsor_proof_trace: Optional[Mapping[str, Any]] = None,
    proofgraph_ref: Optional[Mapping[str, Any]] = None,
    now: Optional[str] = None,
) -> ReviewRun:
    """Attach the first generated packet revision to a request-entered run."""
    if run.stage != "request_entered":
        raise ValueError("packet generation requires request_entered stage")
    normalized = normalize_movement_classes(movement_classes)
    packet = {
        "packet_id": str(packet_id),
        "revision_id": str(revision_id),
        "revision_number": 1,
        "previous_revision_id": None,
        "verdict": str(verdict),
        "ready_for_rerun": False,
        "raw_agent_request_hash": run.access_request.get("raw_request_hash"),
    }
    return _replace_run(
        run,
        stage="packet_generated",
        event_type="packet_generated",
        details={"packet_id": packet["packet_id"], "revision_id": packet["revision_id"]},
        packet=packet,
        movement_classes=normalized,
        missing_proof=_sanitize_public_value(list(missing_proof or [])),
        sponsor_proof_trace=_sanitize_public_value(dict(sponsor_proof_trace or {})) if sponsor_proof_trace else None,
        proofgraph_ref=_sanitize_public_value(dict(proofgraph_ref or {})) if proofgraph_ref else None,
        now=now,
    )


def record_review_run_portkey_preview(
    run: ReviewRun,
    portkey_preview: Mapping[str, Any],
    *,
    now: Optional[str] = None,
) -> ReviewRun:
    """Attach a dry-run Portkey preview without mutating downstream policy."""
    preview = _safe_portkey_preview(portkey_preview)
    invariants = copy.deepcopy(run.safety_invariants)
    invariants["portkey_api_call_made"] = False
    invariants["portkey_policy_mutation_allowed"] = False
    return _replace_run(
        run,
        stage="portkey_previewed",
        event_type="portkey_previewed",
        details={"packet_revision": run.packet.get("revision_id")},
        portkey_preview=preview,
        safety_invariants=invariants,
        now=now,
    )


def attach_review_run_proof(
    run: ReviewRun,
    proof_items: list[Mapping[str, Any]],
    *,
    now: Optional[str] = None,
) -> ReviewRun:
    """Attach human-provided proof and require rerun before verdict changes."""
    if run.stage not in {"packet_generated", "sponsor_proof_collected", "portkey_previewed"}:
        raise ValueError("proof attachment requires generated packet state")
    clean_items = _sanitize_public_value(list(proof_items))
    packet = copy.deepcopy(run.packet)
    previous_verdict = packet.get("verdict")
    previous_portkey = copy.deepcopy(run.portkey_preview)
    packet["ready_for_rerun"] = True
    next_run = _replace_run(
        run,
        stage="proof_attached",
        event_type="proof_attached",
        details={"proof_count": len(clean_items), "packet_revision": packet.get("revision_id")},
        attached_proof=clean_items,
        packet=packet,
        now=now,
    )
    if next_run.packet.get("verdict") != previous_verdict or next_run.portkey_preview != previous_portkey:
        raise ValueError("proof attachment cannot change verdict or Portkey preview")
    return next_run


def rerun_review_run_packet(
    run: ReviewRun,
    *,
    revision_id: str,
    verdict: str,
    movement_classes: Mapping[str, Any],
    portkey_preview: Optional[Mapping[str, Any]] = None,
    still_blocked: Optional[list[str]] = None,
    now: Optional[str] = None,
) -> ReviewRun:
    """Record a human-triggered rerun after proof attachment."""
    if run.stage != "proof_attached":
        raise ValueError("rerun requires proof_attached stage")
    if not run.attached_proof:
        raise ValueError("rerun requires attached proof")
    previous_revision = run.packet.get("revision_id")
    if str(revision_id) == previous_revision:
        raise ValueError("rerun must create a new packet revision")
    packet = copy.deepcopy(run.packet)
    packet.update(
        {
            "revision_id": str(revision_id),
            "revision_number": int(packet.get("revision_number") or 1) + 1,
            "previous_revision_id": previous_revision,
            "verdict": str(verdict),
            "ready_for_rerun": False,
            "raw_agent_request_hash": run.access_request.get("raw_request_hash"),
        }
    )
    delta = {
        "same_request": True,
        "raw_request_hash": run.access_request.get("raw_request_hash"),
        "previous_revision_id": previous_revision,
        "new_revision_id": str(revision_id),
        "new_proof_count": len(run.attached_proof),
        "portkey_state": None,
        "still_blocked": list(still_blocked or normalize_movement_classes(movement_classes)["blocked"]),
    }
    preview = _sanitize_public_value(dict(portkey_preview or {})) if portkey_preview else run.portkey_preview
    if preview:
        preview = _safe_portkey_preview(preview)
    if preview:
        delta["portkey_state"] = preview.get("state") or preview.get("verdict") or preview.get("status")
    return _replace_run(
        run,
        stage="ready_to_export",
        event_type="review_rerun",
        details=delta,
        packet=packet,
        movement_classes=normalize_movement_classes(movement_classes),
        portkey_preview=preview,
        now=now,
    )


def build_review_run_record(
    run: ReviewRun,
    *,
    store_dir: Path = DEFAULT_REVIEW_RUN_STORE_DIR,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    run_id = _safe_run_id(run.run_id)
    record_path = _record_path(run_id, store_dir)
    return {
        "schema_version": REVIEW_RUN_RECORD_SCHEMA_VERSION,
        "run_id": run_id,
        "record_path": _relative(record_path),
        "generated_at": run.updated_at,
        "mode": "local_durable_read_model",
        "read_only": True,
        "run": run.to_dict(),
        "safety_invariants": run.safety_invariants,
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def review_run_record_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    run = dict(record["run"])
    return {
        "schema_version": record["schema_version"],
        "run_id": record["run_id"],
        "record_path": record["record_path"],
        "generated_at": record["generated_at"],
        "mode": record["mode"],
        "read_only": record["read_only"],
        "stage": run["stage"],
        "selected_repo": run.get("selected_repo"),
        "packet": run.get("packet"),
        "movement_classes": run.get("movement_classes"),
        "safety_invariants": record["safety_invariants"],
        "private_boundary": record["private_boundary"],
    }


def write_review_run_record(
    run: ReviewRun,
    *,
    store_dir: Path = DEFAULT_REVIEW_RUN_STORE_DIR,
) -> dict[str, Any]:
    record = build_review_run_record(run, store_dir=store_dir)
    path = _record_path(record["run_id"], store_dir.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_public_dict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def load_review_run_record(
    run_id: str,
    *,
    store_dir: Path = DEFAULT_REVIEW_RUN_STORE_DIR,
) -> Optional[dict[str, Any]]:
    path = _record_path(run_id, store_dir.resolve())
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema_version") != REVIEW_RUN_RECORD_SCHEMA_VERSION:
        return None
    return record
