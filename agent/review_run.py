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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .scenarios import ROOT_DIR


REVIEW_RUN_SCHEMA_VERSION = "review_run.v0"
REVIEW_RUN_RECORD_SCHEMA_VERSION = "review_run_record.v0"
REVIEW_RUN_PACKET_SCHEMA_VERSION = "review_run_packet.v0"
REVIEW_RUN_COACH_SCHEMA_VERSION = "review_run_coach_answer.v0"
REVIEW_RUN_PROOFGRAPH_SCHEMA_VERSION = "review_run_proofgraph.v0"
REVIEW_RUN_PORTKEY_GUARDRAIL_SCHEMA_VERSION = "review_run_portkey_guardrail_test.v0"
REVIEW_RUN_PROOF_LENSES_SCHEMA_VERSION = "review_run_proof_lenses.v0"
REVIEW_RUN_APPROVAL_RECEIPT_SCHEMA_VERSION = "review_run_approval_receipt.v0"
DEFAULT_REVIEW_RUN_STORE_DIR = ROOT_DIR / "state" / "review_runs"
DEFAULT_REVIEW_RUN_ACCESS_REQUEST = "support-triage-bot needs to read issues, comment, and create labels."

REVIEW_RUN_COACH_ANSWER_SHAPE = (
    "Current read",
    "What blocks movement",
    "Next human action",
    "Downstream impact",
    "Safety",
)

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


def _add_utc_days(timestamp: str, days: int) -> str:
    value = str(timestamp or "").strip()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (parsed.astimezone(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _content_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(_public_dict(value), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def _default_missing_proof() -> list[dict[str, str]]:
    return [
        {"id": "repo_owner_approval", "label": "Repo owner approval"},
        {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
        {"id": "environment_boundary", "label": "Environment boundary"},
    ]


REVIEW_RUN_PROOF_LENS_DEFINITIONS = (
    {
        "lens_id": "support_ops",
        "label": "Support Ops",
        "owner_group": "Support Ops",
        "applies_to": "agent_access_review",
        "proof_item_ids": ("repo_owner_approval",),
        "review_focus": "Repo/workflow owner approval",
        "unblocks_scope": ("comment/create labels in selected repo",),
        "prepared_evidence_note": "Support Ops confirmed repo-owner approval for selected repo only.",
        "next_human_action": "Attach repo-owner approval from the workflow owner.",
    },
    {
        "lens_id": "engineering",
        "label": "Engineering",
        "owner_group": "Engineering",
        "applies_to": "agent_access_review",
        "proof_item_ids": ("rollback_offswitch",),
        "review_focus": "Rollback/off-switch proof",
        "unblocks_scope": ("comment/create labels in selected repo",),
        "prepared_evidence_note": "Engineering provided rollback/off-switch proof for support-triage-bot.",
        "next_human_action": "Attach rollback/off-switch proof before rerun.",
    },
    {
        "lens_id": "security",
        "label": "Security",
        "owner_group": "Security",
        "applies_to": "agent_access_review",
        "proof_item_ids": ("environment_boundary",),
        "review_focus": "Secrets/org-wide boundary",
        "unblocks_scope": ("selected-repo scoped movement only",),
        "prepared_evidence_note": "Security confirmed selected-repo boundary; secrets and org-wide access remain blocked.",
        "next_human_action": "Attach environment-boundary proof; secrets and org-wide access stay blocked.",
    },
    {
        "lens_id": "finance_procurement",
        "label": "Finance / Procurement",
        "owner_group": "Finance / Procurement",
        "applies_to": "spend_review",
        "proof_item_ids": (),
        "review_focus": "Budget owner and vendor-spend evidence",
        "unblocks_scope": (),
        "prepared_evidence_note": "",
        "next_human_action": "Not required for this repo-access lane.",
    },
    {
        "lens_id": "legal",
        "label": "Legal",
        "owner_group": "Legal",
        "applies_to": "data_class_review",
        "proof_item_ids": (),
        "review_focus": "Data-class and retention evidence",
        "unblocks_scope": (),
        "prepared_evidence_note": "",
        "next_human_action": "Not required for this repo-access lane.",
    },
)


def _proof_lookup(run: "ReviewRun") -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in run.missing_proof or _default_missing_proof():
        if not isinstance(item, Mapping):
            continue
        proof_id = str(item.get("id") or "").strip()
        if proof_id:
            lookup[proof_id] = {"id": proof_id, "label": str(item.get("label") or proof_id).strip()}
    return lookup


def _attached_proof_ids(run: "ReviewRun") -> set[str]:
    proof_ids: set[str] = set()
    for item in run.attached_proof:
        if not isinstance(item, Mapping):
            continue
        proof_id = str(item.get("id") or "").strip()
        if proof_id:
            proof_ids.add(proof_id)
    return proof_ids


def build_review_run_proof_lenses(run: "ReviewRun", packet_reference: Mapping[str, Any]) -> dict[str, Any]:
    """Project missing proof into human owner lenses without approving access."""
    proof_lookup = _proof_lookup(run)
    attached_ids = _attached_proof_ids(run)
    movement = normalize_movement_classes(run.movement_classes)
    lenses: list[dict[str, Any]] = []
    active_lane = "agent_access_review"
    for definition in REVIEW_RUN_PROOF_LENS_DEFINITIONS:
        proof_item_ids = tuple(definition["proof_item_ids"])
        applies_to = str(definition["applies_to"])
        active = applies_to == active_lane and bool(proof_item_ids)
        missing_items = [
            proof_lookup[proof_id]
            for proof_id in proof_item_ids
            if proof_id in proof_lookup and proof_id not in attached_ids
        ]
        attached_items = [
            proof_lookup.get(proof_id, {"id": proof_id, "label": proof_id})
            for proof_id in proof_item_ids
            if proof_id in attached_ids
        ]
        prepared_items = [
            {
                "id": proof_id,
                "label": proof_lookup.get(proof_id, {"label": proof_id})["label"],
                "evidence_note": definition["prepared_evidence_note"],
                "approves_access": False,
                "grants_permissions": False,
                "mutates_downstream_policy": False,
            }
            for proof_id in proof_item_ids
            if proof_id in proof_lookup
        ]
        lenses.append(
            {
                "lens_id": definition["lens_id"],
                "label": definition["label"],
                "owner_group": definition["owner_group"],
                "active": active,
                "applies_to": applies_to,
                "review_focus": definition["review_focus"],
                "proof_item_ids": list(proof_item_ids),
                "missing_proof": missing_items,
                "attached_proof": attached_items,
                "blocked_claims": movement["blocked"] if active else [],
                "unblocks_scope": list(definition["unblocks_scope"]),
                "prepared_proof_items": prepared_items,
                "next_human_action": definition["next_human_action"],
                "safety_note": "This lens names human proof only. It does not approve, grant, write, mutate, or dispatch.",
            }
        )
    return _sanitize_public_value(
        {
            "schema_version": REVIEW_RUN_PROOF_LENSES_SCHEMA_VERSION,
            "run_id": run.run_id,
            "stage": run.stage,
            "active_lane": active_lane,
            "selected_repo": (run.selected_repo or {}).get("full_name") or (run.selected_repo or {}).get("name"),
            "packet_reference": dict(packet_reference),
            "lenses": lenses,
            "guardrails": {
                "read_only": True,
                "does_not_approve": True,
                "proof_attachment_changes_verdict": False,
                "rerun_required_for_verdict_change": True,
                "portkey_policy_mutation_allowed": False,
                "external_writes": False,
            },
        }
    )


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
        "repo_selected": "Click Review access to generate the packet for this selected repo.",
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
        "answer_shape": list(REVIEW_RUN_COACH_ANSWER_SHAPE),
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


def normalize_review_run_proof_items(run: "ReviewRun", proof_items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalize human-attached proof without allowing approval-like shortcuts."""
    if not proof_items:
        raise ValueError("proof_items cannot be empty")

    allowed = _proof_lookup(run)
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    blocked_phrases = (
        "approve all",
        "approve blocked",
        "force approve",
        "override packet",
        "bypass review",
        "grant access",
        "grant permissions",
    )
    for item in proof_items:
        if not isinstance(item, Mapping):
            raise ValueError("proof item requires object")
        payload = _sanitize_public_value(dict(item or {}))
        proof_id = str(payload.get("id") or "").strip()
        if not proof_id:
            raise ValueError("proof item requires id")
        if proof_id in seen:
            raise ValueError("duplicate proof item")
        if allowed and proof_id not in allowed:
            raise ValueError(f"unknown proof item: {proof_id}")
        label = str(payload.get("label") or allowed.get(proof_id, {}).get("label") or proof_id).strip()
        evidence_note = str(payload.get("evidence_note") or "").strip()
        phrase_target = f"{proof_id} {label} {evidence_note}".lower()
        if any(phrase in phrase_target for phrase in blocked_phrases):
            raise ValueError("proof item cannot approve or override blocked claims")
        seen.add(proof_id)
        normalized.append(
            {
                "id": proof_id,
                "label": label,
                "evidence_note": evidence_note or "Human marked this proof item as attached.",
                "human_attached": True,
                "approves_access": False,
                "grants_permissions": False,
                "mutates_downstream_policy": False,
            }
        )
    return normalized


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def classify_review_run_access_request(raw_text: str) -> dict[str, list[str]]:
    """Classify a repo access request without treating any action as approved."""
    text = " ".join(str(raw_text or "").lower().split())
    movement = _default_movement_classes()

    if "read" in text and ("issue" in text or "issues" in text):
        _append_once(movement["allowed"], "read issues")
    if "comment" in text or "reply" in text:
        _append_once(movement["review_required"], "comment")
    if "label" in text:
        _append_once(movement["blocked"], "create labels")

    if "admin" in text:
        _append_once(movement["blocked"], "repo admin")
    if "org-wide" in text or "org wide" in text or "organization" in text:
        _append_once(movement["blocked"], "org-wide write")
    if "secret" in text or "credential" in text:
        _append_once(movement["blocked"], "secrets")
    if "approve everything" in text or "bypass" in text or "ignore ia" in text or "override" in text:
        _append_once(movement["blocked"], "approval override request")

    for hard_block in ("repo admin", "org-wide write", "secrets"):
        _append_once(movement["blocked"], hard_block)

    return normalize_movement_classes(movement)


def _missing_proof_labels(items: list[Any]) -> list[str]:
    labels: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            label = item.get("label") or item.get("id") or item
        else:
            label = item
        text = str(label).strip()
        if text:
            labels.append(text)
    return labels


def _review_run_packet_id(run: ReviewRun) -> str:
    repo_name = (run.selected_repo or {}).get("full_name") or (run.selected_repo or {}).get("name") or "repo"
    return f"ia-review-run-packet-{_digest(f'{run.run_id}:{repo_name}')}-v0"


def _review_run_revision_id(run: ReviewRun, revision_number: int = 1) -> str:
    raw_hash = run.access_request.get("raw_request_hash") or "no-request"
    repo_name = (run.selected_repo or {}).get("full_name") or (run.selected_repo or {}).get("name") or "repo"
    return f"rev_{_digest(f'{run.run_id}:{repo_name}:{raw_hash}:{revision_number}')}"


def _packet_hash_payload(
    *,
    run: ReviewRun,
    packet_id: str,
    revision_id: str,
    verdict: str,
    movement_classes: Mapping[str, Any],
    missing_proof: list[Any],
) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "selected_repo": (run.selected_repo or {}).get("full_name") or (run.selected_repo or {}).get("name"),
        "raw_request_hash": run.access_request.get("raw_request_hash"),
        "packet_id": packet_id,
        "revision_id": revision_id,
        "verdict": verdict,
        "movement_classes": normalize_movement_classes(movement_classes),
        "missing_proof": _missing_proof_labels(missing_proof),
    }


def _safe_portkey_preview(value: Mapping[str, Any]) -> dict[str, Any]:
    preview = _sanitize_public_value(dict(value))
    preview["api_call_made"] = False
    preview["portkey_api_call_made"] = False
    preview["policy_mutation_allowed"] = False
    preview["portkey_policy_mutation_allowed"] = False
    preview["dry_run"] = True
    return preview


def _portkey_state(value: Optional[Mapping[str, Any]], *, default: str = "Block") -> str:
    if not value:
        return default
    for key in ("state", "verdict", "status"):
        candidate = value.get(key)
        if candidate:
            return str(candidate)
    guardrail = value.get("portkey_guardrail_response")
    if isinstance(guardrail, Mapping):
        verdict = guardrail.get("verdict")
        if verdict is True:
            return "Allow with policy"
        if verdict is False:
            return "Block"
    return default


def _review_run_allow_portkey_preview(run: "ReviewRun") -> dict[str, Any]:
    packet = run.packet or {}
    return _safe_portkey_preview(
        {
            "state": "Allow with policy",
            "mode": "dry-run",
            "packet_id": packet.get("packet_id"),
            "revision_id": _review_run_revision_id(run, int(packet.get("revision_number") or 1) + 1),
            "portkey_guardrail_response": {
                "verdict": True,
                "reason": "Attached human proof allows scoped movement under policy for the selected repo only.",
            },
            "usage_policy_plan": {
                "request_body": {
                    "policy_name": "reviewrun-scoped-repo-access",
                    "credit_limit": 0,
                    "scope": "selected_repo_only",
                    "allowed_with_policy": ["read issues", "comment", "create labels in selected repo"],
                    "still_blocked": ["repo admin", "org-wide write", "secrets"],
                }
            },
        }
    )


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
    clean_missing_proof = _sanitize_public_value(list(missing_proof or []))
    packet = {
        "packet_id": str(packet_id),
        "revision_id": str(revision_id),
        "revision_number": 1,
        "previous_revision_id": None,
        "verdict": str(verdict),
        "ready_for_rerun": False,
        "raw_agent_request_hash": run.access_request.get("raw_request_hash"),
        "source_run_id": run.run_id,
    }
    packet["content_hash"] = _content_hash(
        _packet_hash_payload(
            run=run,
            packet_id=packet["packet_id"],
            revision_id=packet["revision_id"],
            verdict=packet["verdict"],
            movement_classes=normalized,
            missing_proof=clean_missing_proof,
        )
    )
    return _replace_run(
        run,
        stage="packet_generated",
        event_type="packet_generated",
        details={"packet_id": packet["packet_id"], "revision_id": packet["revision_id"]},
        packet=packet,
        movement_classes=normalized,
        missing_proof=clean_missing_proof,
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
    clean_items = normalize_review_run_proof_items(run, proof_items)
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
    required_proof_ids = set(_proof_lookup(run))
    attached_proof_ids = _attached_proof_ids(run)
    missing_required_proof = sorted(required_proof_ids - attached_proof_ids)
    if missing_required_proof:
        raise ValueError("rerun requires all missing proof")
    previous_revision = run.packet.get("revision_id")
    previous_verdict = run.packet.get("verdict")
    previous_portkey_state = _portkey_state(run.portkey_preview)
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
            "source_run_id": run.run_id,
        }
    )
    packet["content_hash"] = _content_hash(
        _packet_hash_payload(
            run=run,
            packet_id=str(packet.get("packet_id") or _review_run_packet_id(run)),
            revision_id=str(revision_id),
            verdict=str(verdict),
            movement_classes=movement_classes,
            missing_proof=run.missing_proof,
        )
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
    new_portkey_state = _portkey_state(preview, default=previous_portkey_state)
    if preview:
        delta["portkey_state"] = new_portkey_state
    delta.update(
        {
            "packet_changed": True,
            "previous_verdict": previous_verdict,
            "new_verdict": str(verdict),
            "previous_portkey_state": previous_portkey_state,
            "new_portkey_state": new_portkey_state,
            "portkey_changed": previous_portkey_state != new_portkey_state,
            "verdict_changed": previous_verdict != str(verdict),
            "attached_proof_ids": sorted(attached_proof_ids),
        }
    )
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


def generate_proof_resolved_review_run_packet(
    run: ReviewRun,
    raw_access_request: Optional[str] = None,
    *,
    now: Optional[str] = None,
) -> ReviewRun:
    """Generate the second packet revision after all human proof is attached."""
    request_text = str(raw_access_request or "").strip()
    if request_text and _digest(request_text) != run.access_request.get("raw_request_hash"):
        raise ValueError("raw agent request cannot change before rerun")
    next_revision_number = int(run.packet.get("revision_number") or 1) + 1
    movement_classes = {
        "allowed": ["read issues", "comment", "create labels in selected repo"],
        "review_required": [],
        "blocked": ["repo admin", "org-wide write", "secrets"],
    }
    return rerun_review_run_packet(
        run,
        revision_id=_review_run_revision_id(run, next_revision_number),
        verdict="ready_with_gates",
        movement_classes=movement_classes,
        portkey_preview=_review_run_allow_portkey_preview(run),
        still_blocked=movement_classes["blocked"],
        now=now,
    )


def generate_initial_review_run_packet(
    run: ReviewRun,
    raw_access_request: str = DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
    *,
    sponsor_proof_trace: Optional[Mapping[str, Any]] = None,
    now: Optional[str] = None,
) -> ReviewRun:
    """Generate the first compact IA Packet from selected repo + index + request."""
    request_text = str(raw_access_request or "").strip()
    if not request_text:
        raise ValueError("access_request cannot be empty")
    request_hash = _digest(request_text)

    if run.stage == "repo_selected":
        run = record_review_run_access_request(run, request_text, now=now)
    elif run.stage == "request_entered":
        if run.access_request.get("raw_request_hash") != request_hash:
            raise ValueError("access_request cannot change before packet generation")
    elif run.stage == "packet_generated":
        if run.access_request.get("raw_request_hash") != request_hash:
            raise ValueError("raw agent request cannot change after packet generation")
        return run
    else:
        raise ValueError("packet generation requires repo_selected or request_entered stage")

    movement_classes = classify_review_run_access_request(request_text)
    missing_proof = _default_missing_proof()
    return record_review_run_packet(
        run,
        packet_id=_review_run_packet_id(run),
        revision_id=_review_run_revision_id(run, 1),
        verdict="scoped_validation_only",
        movement_classes=movement_classes,
        missing_proof=missing_proof,
        sponsor_proof_trace=sponsor_proof_trace,
        proofgraph_ref={
            "source": "review_run",
            "run_id": run.run_id,
            "status": "ready_for_dynamic_graph",
        },
        now=now,
    )


def _latest_review_rerun_delta(run: ReviewRun) -> dict[str, Any]:
    for event in reversed(run.audit_events or []):
        if event.get("event_type") == "review_rerun":
            return _sanitize_public_value(dict(event.get("details") or {}))
    return {}


def review_run_packet_projection(run: ReviewRun) -> dict[str, Any]:
    """Return the compact packet shape the root cockpit consumes."""
    if run.stage not in {"packet_generated", "sponsor_proof_collected", "portkey_previewed", "proof_attached", "ready_to_export"}:
        raise ValueError("review run has no generated packet")

    repo = run.selected_repo or {}
    repo_name = repo.get("full_name") or repo.get("name") or "selected repo"
    movement = normalize_movement_classes(run.movement_classes)
    missing_labels = _missing_proof_labels(run.missing_proof)
    packet = run.packet
    ready_for_rerun = bool(packet.get("ready_for_rerun"))
    ready_to_export = run.stage == "ready_to_export"
    verdict_class = packet.get("verdict") or "scoped_validation_only"
    review_delta = _latest_review_rerun_delta(run)
    packet_reference = {
        "packet_id": packet.get("packet_id"),
        "revision_id": packet.get("revision_id"),
        "revision_number": packet.get("revision_number"),
        "previous_revision_id": packet.get("previous_revision_id"),
        "content_hash": packet.get("content_hash"),
        "run_id": run.run_id,
        "source_of_truth": "ReviewRun",
    }
    proof_lenses = build_review_run_proof_lenses(run, packet_reference)
    next_action = (
        "Export the updated packet brief and route the scoped allow-with-policy review."
        if ready_to_export
        else "Proof attached. Regenerate the packet before any verdict or Portkey state can change."
        if ready_for_rerun
        else (
            "Attach Support Ops repo-owner approval, Engineering rollback/off-switch proof, "
            "and Security environment-boundary proof, then rerun review."
        )
    )
    brief_lines = [
        f"ReviewRun `{run.run_id}` generated packet `{packet.get('packet_id')}` for `{repo_name}`.",
        f"Verdict class: `{verdict_class}`.",
        f"Allowed: {', '.join(movement['allowed']) or 'none'}.",
        f"Review required: {', '.join(movement['review_required']) or 'none'}.",
        f"Blocked: {', '.join(movement['blocked']) or 'none'}.",
        f"Missing proof: {', '.join(missing_labels) or 'none'}.",
        "IA did not approve, grant, write, mutate, or dispatch. Raw agent intent is not trusted; proof changes packet state.",
    ]
    return {
        "schema_version": REVIEW_RUN_PACKET_SCHEMA_VERSION,
        "ok": True,
        "read_only": True,
        "product_object": "IA Packet",
        "title": f"IA Packet: {repo_name}",
        "definition": "Compact packet generated from the current ReviewRun.",
        "review_run": {
            "run_id": run.run_id,
            "stage": run.stage,
            "selected_repo": repo,
            "repo_index_summary": run.repo_index_summary,
            "access_request": run.access_request,
            "packet": run.packet,
            "missing_proof": run.missing_proof,
            "attached_proof": run.attached_proof,
            "portkey_preview": run.portkey_preview,
        },
        "packet_reference": packet_reference,
        "source_inputs": {
            "selected_repo": repo_name,
            "repo_index_summary": run.repo_index_summary,
            "raw_request_hash": run.access_request.get("raw_request_hash"),
        },
        "decision": {
            "verdict_class": verdict_class,
            "requires_human_review": not ready_to_export,
            "production_access": False,
            "permission_grants": False,
            "external_writes": False,
            "approval_granted": False,
            "next_human_action": next_action,
        },
        "movement_classes": movement,
        "allowed": movement["allowed"],
        "review_required": movement["review_required"],
        "blocked": movement["blocked"],
        "missing_proof": missing_labels,
        "blocked_claims": [
            "Production tool access is not approved.",
            "Repo label creation is blocked until repo-owner approval, rollback proof, and environment boundary exist.",
            "Repo admin, org-wide writes, and secrets remain blocked.",
        ],
        "compact_output": {
            "verdict": packet.get("verdict") or "scoped_validation_only",
            "allowed": movement["allowed"],
            "review_required": movement["review_required"],
            "blocked": movement["blocked"],
            "missing_proof": missing_labels,
            "next_human_action": next_action,
            "ready_for_rerun": ready_for_rerun,
        },
        "proof_resolution": {
            "missing_proof": run.missing_proof,
            "attached_proof": run.attached_proof,
            "attached_proof_count": len(run.attached_proof),
            "ready_for_rerun": ready_for_rerun,
            "verdict_changed": bool(review_delta.get("verdict_changed")),
            "portkey_changed": bool(review_delta.get("portkey_changed")),
            "next_human_action": next_action,
            "owner_lenses": proof_lenses,
        },
        "proof_lenses": proof_lenses,
        "review_delta": {
            "schema_version": "review_run_delta.v0",
            "same_request": bool(review_delta.get("same_request")),
            "raw_request_hash": run.access_request.get("raw_request_hash"),
            "new_proof": run.attached_proof,
            "packet_revision_before": review_delta.get("previous_revision_id") or packet.get("previous_revision_id"),
            "packet_revision_after": packet.get("revision_id"),
            "packet_changed": bool(review_delta.get("packet_changed")),
            "verdict_before": review_delta.get("previous_verdict"),
            "verdict_after": verdict_class,
            "portkey_before": review_delta.get("previous_portkey_state"),
            "portkey_after": review_delta.get("new_portkey_state") or _portkey_state(run.portkey_preview, default="Block"),
            "portkey_changed": bool(review_delta.get("portkey_changed")),
            "still_blocked": review_delta.get("still_blocked") or movement["blocked"],
        },
        "portkey_preview": run.portkey_preview,
        "safety_boundary": {
            "approval_granted": False,
            "production_access": False,
            "permission_grants": False,
            "external_writes": False,
            "packet_mutated_without_rerun": False,
            "proof_attachment_changes_verdict": False,
            "portkey_api_call_made": False,
            "portkey_policy_mutation_allowed": False,
            "raw_agent_intent_trusted": False,
            "source_of_truth": "ReviewRun",
        },
        "safety_anchor": "Raw agent intent is not trusted. Proof changes packet state. Downstream systems consume the packet.",
        "copy_review_brief": "\n".join(brief_lines),
        "export_label": "Copy ReviewRun packet brief",
    }


def build_review_run_portkey_guardrail_test(
    run: ReviewRun,
    *,
    elapsed_ms: int = 0,
    generated_at: Optional[str] = None,
) -> dict[str, Any]:
    """Build a read-only Portkey guardrail test from the current ReviewRun packet."""
    packet_projection = review_run_packet_projection(run)
    packet = run.packet or {}
    packet_id = packet.get("packet_id")
    revision_id = packet.get("revision_id")
    if not packet_id or not revision_id:
        raise ValueError("Portkey guardrail test requires a generated packet")

    timestamp = generated_at or _utcnow()
    movement = normalize_movement_classes(run.movement_classes)
    missing_labels = _missing_proof_labels(run.missing_proof)
    requested_mode = "scoped_validation"
    packet_ready = run.stage == "ready_to_export" and packet.get("verdict") == "ready_with_gates"
    preview_verdict = (run.portkey_preview or {}).get("portkey_guardrail_response", {}).get("verdict")
    allowed = bool(packet_ready and preview_verdict is True)
    reason = (
        "packet_allows_scoped_review_with_policy"
        if allowed
        else "packet_not_ready_for_portkey_movement"
    )
    deny_reasons = (
        []
        if allowed
        else [
            reason,
            *[f"missing_proof:{label}" for label in missing_labels[:4]],
            *[f"blocked_scope:{scope}" for scope in movement["blocked"][:4]],
        ]
    )
    packet_reference = {
        "packet_id": str(packet_id),
        "revision_id": str(revision_id),
        "revision_number": int(packet.get("revision_number") or 0),
        "content_hash": packet.get("content_hash"),
        "run_id": run.run_id,
        "source_of_truth": "ReviewRun",
    }
    safety = {
        "read_only": True,
        "approves_access": False,
        "approves_spend": False,
        "executes_external_writes": False,
        "mutates_production": False,
        "raw_agent_intent_trusted": False,
        "packet_mutation_allowed": False,
        "portkey_api_call_made": False,
        "portkey_policy_mutation_allowed": False,
    }
    response = {
        "verdict": allowed,
        "data": {
            "schema_version": "portkey_byo_guardrail.v0",
            "delivery_mode": "review_run_guardrail_test",
            "portkey_surface": "BYO Guardrails webhook",
            "generated_at": timestamp,
            "elapsed_ms": elapsed_ms,
            "requested_mode": requested_mode,
            "ia_packet_reference": packet_reference,
            "verdict_class": packet.get("verdict"),
            "reason": reason,
            "deny_reasons": deny_reasons,
            "allowed_scope": list(movement["allowed"]),
            "review_required_scope": list(movement["review_required"]),
            "still_blocked_scope": list(movement["blocked"]),
            "next_human_action": packet_projection["decision"]["next_human_action"],
            "safety": safety,
        },
    }
    request_body = {
        "eventType": "beforeRequestHook",
        "metadata": {
            "ia_review_run_id": run.run_id,
            "ia_packet_id": packet_reference["packet_id"],
            "ia_revision_id": packet_reference["revision_id"],
            "ia_content_hash": packet_reference["content_hash"],
            "ia_requested_mode": requested_mode,
            "ia_source_of_truth": "ReviewRun",
        },
        "request": {
            "metadata": {
                "ia_review_run_id": run.run_id,
                "ia_packet_id": packet_reference["packet_id"],
                "ia_revision_id": packet_reference["revision_id"],
            },
            "model": "packet-gated-model",
            "messages": [
                {
                    "role": "user",
                    "content": "Portkey asks IA whether this packet-backed movement can proceed.",
                }
            ],
        },
    }

    return _sanitize_public_value(
        {
            "schema_version": REVIEW_RUN_PORTKEY_GUARDRAIL_SCHEMA_VERSION,
            "run_id": run.run_id,
            "stage": run.stage,
            "read_only": True,
            "dry_run": True,
            "mode": "review_run_guardrail_test",
            "api_call_made": False,
            "policy_mutation_allowed": False,
            "generated_at": timestamp,
            "elapsed_ms": elapsed_ms,
            "portkey_state": "Allow with policy" if allowed else "Block",
            "verdict": allowed,
            "reason": reason,
            "packet_reference": packet_reference,
            "allowed_scope": list(movement["allowed"]),
            "review_required_scope": list(movement["review_required"]),
            "still_blocked_scope": list(movement["blocked"]),
            "deny_reasons": deny_reasons,
            "next_human_action": packet_projection["decision"]["next_human_action"],
            "portkey_request": request_body,
            "portkey_guardrail_response": response,
            "invariants": {
                "read_only": True,
                "raw_agent_intent_trusted": False,
                "packet_remains_authority": True,
                "packet_mutation_allowed": False,
                "portkey_api_call_made": False,
                "portkey_policy_mutation_allowed": False,
                "approval_granted": False,
                "external_writes": False,
            },
            "safety_anchor": "Portkey receives a packet-backed verdict. IA does not approve, write, or mutate Portkey.",
        }
    )


def build_review_run_approval_receipt(
    run: ReviewRun,
    *,
    generated_at: Optional[str] = None,
    valid_for_days: int = 30,
) -> dict[str, Any]:
    """Build a portable approval receipt from ReviewRun state without approving anything itself."""
    if valid_for_days <= 0:
        raise ValueError("valid_for_days must be positive")

    packet = run.packet or {}
    packet_id = str(packet.get("packet_id") or "").strip()
    revision_id = str(packet.get("revision_id") or "").strip()
    content_hash = str(packet.get("content_hash") or "").strip()
    if not packet_id or not revision_id or not content_hash:
        raise ValueError("approval receipt requires a generated packet")

    movement = normalize_movement_classes(run.movement_classes)
    attached_ids = _attached_proof_ids(run)
    required_approvers = (
        {
            "role_id": "manager",
            "label": "Manager / workflow owner",
            "proof_item_id": "repo_owner_approval",
            "scope": "business need and selected-repo ownership",
            "required": True,
        },
        {
            "role_id": "engineering",
            "label": "Engineering",
            "proof_item_id": "rollback_offswitch",
            "scope": "rollback/off-switch boundary",
            "required": True,
        },
        {
            "role_id": "security",
            "label": "Security",
            "proof_item_id": "environment_boundary",
            "scope": "selected-repo boundary; secrets and org-wide access stay blocked",
            "required": True,
        },
        {
            "role_id": "procurement",
            "label": "Procurement",
            "proof_item_id": None,
            "scope": "spend/vendor review",
            "required": False,
            "not_required_reason": "repo-access lane has no spend or vendor movement",
        },
    )
    ready_to_circulate = run.stage == "ready_to_export" and packet.get("verdict") == "ready_with_gates"
    approvals: list[dict[str, Any]] = []
    for approver in required_approvers:
        proof_item_id = approver.get("proof_item_id")
        required = bool(approver["required"])
        if not required:
            state = "not_required"
        elif proof_item_id in attached_ids and ready_to_circulate:
            state = "approved_for_scoped_validation"
        elif proof_item_id in attached_ids:
            state = "recorded_pending_packet_rerun"
        else:
            state = "missing"
        approvals.append(
            {
                "role_id": approver["role_id"],
                "label": approver["label"],
                "required": required,
                "approval_state": state,
                "proof_item_id": proof_item_id,
                "scope": approver["scope"],
                "not_required_reason": approver.get("not_required_reason"),
                "approves_outside_scope": False,
            }
        )

    required = [item for item in approvals if item["required"]]
    recorded = [
        item
        for item in required
        if item["approval_state"] in {"approved_for_scoped_validation", "recorded_pending_packet_rerun"}
    ]
    missing = [item for item in required if item["approval_state"] == "missing"]
    if ready_to_circulate:
        receipt_status = "ready_to_circulate"
        human_approval_state = "recorded_for_scoped_validation"
    elif not missing and recorded:
        receipt_status = "pending_packet_rerun"
        human_approval_state = "proof_recorded_rerun_required"
    else:
        receipt_status = "pending_human_approval"
        human_approval_state = "missing_required_approval"

    issued_at = generated_at or run.updated_at or _utcnow()
    expires_at = _add_utc_days(issued_at, valid_for_days)
    receipt_id = f"rcpt_{_digest(f'{packet_id}:{revision_id}:{content_hash}')[:10]}"
    receipt = {
        "schema_version": REVIEW_RUN_APPROVAL_RECEIPT_SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "receipt_type": "portable_approval_receipt_for_ai_movement",
        "product_object": "Portable approval receipt",
        "status": receipt_status,
        "can_circulate": ready_to_circulate,
        "read_only": True,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "valid_for_days": valid_for_days,
        "verification_path": f"/api/review-runs/{run.run_id}/approval-receipt",
        "packet_reference": {
            "packet_id": packet_id,
            "revision_id": revision_id,
            "revision_number": int(packet.get("revision_number") or 0),
            "previous_revision_id": packet.get("previous_revision_id"),
            "content_hash": content_hash,
            "run_id": run.run_id,
            "source_of_truth": "ReviewRun",
        },
        "movement": {
            "verdict": packet.get("verdict"),
            "allowed_scope": list(movement["allowed"]),
            "review_required_scope": list(movement["review_required"]),
            "still_blocked_scope": list(movement["blocked"]),
            "movement_class": "scoped_validation" if ready_to_circulate else "blocked_until_receipt_ready",
        },
        "approval_summary": {
            "human_approval_state": human_approval_state,
            "required_count": len(required),
            "recorded_count": len(recorded),
            "missing_count": len(missing),
            "required_roles": [item["role_id"] for item in required],
            "missing_roles": [item["role_id"] for item in missing],
            "not_required_roles": [item["role_id"] for item in approvals if not item["required"]],
        },
        "approvals": approvals,
        "proof_receipts": list(run.attached_proof or []),
        "portkey": {
            "state": _portkey_state(run.portkey_preview, default="Block"),
            "event_id": None,
            "api_call_made": False,
            "policy_mutation_allowed": False,
            "consumes_packet_revision": revision_id,
        },
        "revocation": {
            "supersedes_revision_id": packet.get("previous_revision_id"),
            "reverify_on_new_packet_revision": True,
            "reverify_before_production_access": True,
            "receipt_expiration_invalidates_movement": True,
        },
        "delegation": {
            "manager": "Business/workflow ownership review is carried by the receipt once recorded.",
            "security": "Security boundary review is carried by the receipt; secrets and org-wide access stay blocked.",
            "procurement": "Procurement is not required for this repo-access lane; spend lanes must require it.",
        },
        "safety_boundary": {
            "ia_approved": False,
            "ia_grants_permissions": False,
            "ia_executes_external_writes": False,
            "ia_mutates_portkey_policy": False,
            "receipt_expands_scope": False,
            "raw_agent_intent_trusted": False,
            "humans_approved_scope": ready_to_circulate,
            "downstream_must_enforce_scope": True,
        },
        "safety_anchor": (
            "Humans approve scoped movement. IA records and packages the receipt. "
            "Downstream systems verify the receipt; IA does not approve, write, grant, or mutate policy."
        ),
    }
    receipt["receipt_hash"] = _content_hash(receipt)
    return _sanitize_public_value(receipt)


def _review_run_repo_name(run: ReviewRun) -> str:
    repo = run.selected_repo or {}
    return str(repo.get("full_name") or repo.get("name") or "no repo selected")


def _review_run_verdict_label(verdict: Any) -> str:
    value = str(verdict or "not_generated")
    labels = {
        "not_generated": "not generated",
        "scoped_validation_only": "Scoped validation only",
        "ready_with_gates": "Ready with gates",
    }
    return labels.get(value, value.replace("_", " "))


def _review_run_coach_prompt_kind(prompt: str) -> str:
    text = " ".join(str(prompt or "").lower().split())
    if not text or text in {"hi", "hey", "hello", "yo"}:
        return "greeting"
    if any(
        phrase in text
        for phrase in (
            "approve blocked",
            "approve all",
            "force approve",
            "override",
            "bypass",
            "grant access",
            "grant permissions",
        )
    ):
        return "approval_override"
    if any(
        phrase in text
        for phrase in (
            "idk",
            "i don't know",
            "what do i do",
            "what next",
            "next step",
            "what should i do",
        )
    ):
        return "next_action"
    if "portkey" in text or "downstream" in text or "spend" in text or "policy" in text:
        return "portkey"
    if "proof" in text or "missing" in text or "block" in text:
        return "proof"
    if "move" in text or "allow" in text or "can this" in text:
        return "movement"
    if any(phrase in text for phrase in ("weather", "joke", "recipe", "poem", "song", "movie")):
        return "unrelated"
    return "current_read"


def _review_run_coach_next_action(run: ReviewRun) -> str:
    if run.stage == "repo_not_connected":
        return "Connect GitHub or use the demo repo."
    if run.stage == "repo_selected":
        return "Click Review access to generate the packet for this selected repo."
    if run.stage == "request_entered":
        return "Generate the IA Packet."
    if run.stage in {"packet_generated", "sponsor_proof_collected", "portkey_previewed"}:
        return (
            "Attach Support Ops repo-owner approval, Engineering rollback/off-switch proof, "
            "and Security environment-boundary proof, then rerun review."
        )
    if run.stage == "proof_attached":
        return "Regenerate the packet from the same request and attached proof."
    if run.stage == "ready_to_export":
        return "Export the updated packet brief and route the scoped allow-with-policy review."
    state = run.ask_ia_state or _ask_ia_state(run.stage, run_id=run.run_id, selected_repo=run.selected_repo)
    return str(state.get("next_human_action") or "Review the current packet state before movement.")


def _review_run_coach_current_read(run: ReviewRun) -> str:
    repo_name = _review_run_repo_name(run)
    packet = run.packet or {}
    revision = packet.get("revision_id") or "not generated"
    verdict = _review_run_verdict_label(packet.get("verdict"))
    if run.stage == "repo_not_connected":
        return "No GitHub repo is selected yet; Ask IA is waiting for one ReviewRun."
    if run.stage == "repo_selected":
        return f"`{repo_name}` is selected and indexed. No packet exists yet."
    if run.stage == "request_entered":
        return f"`{repo_name}` has an access request recorded. Generate the IA Packet next."
    if run.stage == "proof_attached":
        return f"`{repo_name}` has proof attached to packet revision `{revision}`, but the verdict is still `{verdict}` until rerun."
    if run.stage == "ready_to_export":
        return f"`{repo_name}` has updated packet revision `{revision}` with verdict `{verdict}`."
    return f"`{repo_name}` has packet revision `{revision}` with verdict `{verdict}`."


def _review_run_coach_blockers(run: ReviewRun) -> str:
    movement = normalize_movement_classes(run.movement_classes)
    missing_labels = _missing_proof_labels(run.missing_proof)
    still_blocked = movement["blocked"]
    owner_summary = (
        "Owners: Support Ops brings repo-owner approval; Engineering brings rollback/off-switch proof; "
        "Security brings the secrets/org-wide boundary."
    )
    if run.stage in {"repo_not_connected", "repo_selected", "request_entered"}:
        return "Movement cannot be evaluated until IA generates a packet for the selected repo."
    if run.stage == "proof_attached":
        return (
            "Proof is attached, but movement is still blocked until a human reruns review and creates a new packet revision. "
            f"{owner_summary}"
        )
    if run.stage == "ready_to_export":
        return f"No proof debt blocks scoped movement. Still blocked: {', '.join(still_blocked) or 'none'}."
    return (
        f"Missing proof: {', '.join(missing_labels) or 'none'}. "
        f"Blocked claims: {', '.join(still_blocked) or 'none'}. {owner_summary}"
    )


def _review_run_coach_downstream_impact(run: ReviewRun) -> str:
    movement = normalize_movement_classes(run.movement_classes)
    portkey_state = _portkey_state(run.portkey_preview, default="Block")
    if run.stage == "ready_to_export":
        return (
            f"Portkey dry-run reads the updated packet as `{portkey_state}` for selected-repo scope only. "
            f"Still blocked downstream: {', '.join(movement['blocked']) or 'none'}."
        )
    if run.stage == "proof_attached":
        return "Portkey remains effectively `Block` until the rerun produces a new packet revision from the attached proof."
    if run.stage in {"repo_not_connected", "repo_selected", "request_entered"}:
        return "Downstream systems have no packet to consume yet, so no movement should be allowed."
    return "Portkey should treat this as `Block` while proof is missing; downstream systems consume the packet, not raw agent intent."


def build_review_run_coach_answer(
    run: ReviewRun,
    prompt: str = "",
    chip_entities: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build a compact, deterministic Ask IA answer from ReviewRun state only."""
    from .coach_suggestions import coach_answer_suggestions

    prompt_text = str(prompt or "").strip()
    pinned_kind = ""
    if isinstance(chip_entities, Mapping):
        pinned_kind = str(chip_entities.get("prompt_kind") or "").strip()
    prompt_kind = pinned_kind or _review_run_coach_prompt_kind(prompt_text)
    movement = normalize_movement_classes(run.movement_classes)
    packet = run.packet or {}
    repo_name = _review_run_repo_name(run)
    current_read = _review_run_coach_current_read(run)
    blockers = _review_run_coach_blockers(run)
    next_action = _review_run_coach_next_action(run)
    downstream = _review_run_coach_downstream_impact(run)
    safety = (
        "Raw agent intent is not trusted. Proof changes packet state. "
        "Downstream systems consume the packet. IA did not approve, grant, "
        "write, mutate, dispatch, or call Portkey."
    )

    if prompt_kind == "approval_override":
        blockers = (
            "Cannot approve or override blocked claims. Resolve missing proof, "
            "attach it to the ReviewRun, and rerun review so a new packet can change state."
        )
        next_action = (
            "Attach human-provided proof, then regenerate the packet; "
            "do not approve blocked claims directly."
        )
    elif prompt_kind == "unrelated":
        current_read = f"I am routing that back to the current review: {current_read}"
    elif prompt_kind == "portkey":
        next_action = (
            next_action
            if run.stage != "packet_generated"
            else "Attach missing proof before expecting Portkey to move from Block."
        )
    elif prompt_kind == "proof" and run.stage == "ready_to_export":
        blockers = "Required proof is attached and the packet was regenerated. Only hard-blocked scopes remain blocked."

    sections = {
        "current_read": current_read,
        "what_blocks_movement": blockers,
        "next_human_action": next_action,
        "downstream_impact": downstream,
        "safety": safety,
    }
    reply_lines = []
    for label, key in (
        ("Current read", "current_read"),
        ("What blocks movement", "what_blocks_movement"),
        ("Next human action", "next_human_action"),
        ("Downstream impact", "downstream_impact"),
        ("Safety", "safety"),
    ):
        reply_lines.append(f"## {label}\n{sections[key]}")

    suggestions = coach_answer_suggestions(
        run,
        prompt_kind=prompt_kind if prompt_text else "",
        prompt_text=prompt_text,
    )

    return _sanitize_public_value(
        {
            "schema_version": REVIEW_RUN_COACH_SCHEMA_VERSION,
            "run_id": run.run_id,
            "stage": run.stage,
            "prompt_kind": prompt_kind,
            "prompt_routed_to_review": prompt_kind == "unrelated",
            "selected_repo": repo_name,
            "verdict": packet.get("verdict") or "not_generated",
            "packet_revision": packet.get("revision_id"),
            "packet_revision_number": packet.get("revision_number") or 0,
            "portkey_state": _portkey_state(run.portkey_preview, default="Block"),
            "answer_shape": list(REVIEW_RUN_COACH_ANSWER_SHAPE),
            "sections": sections,
            "suggestions": suggestions,
            "movement_classes": {
                "allowed": movement["allowed"],
                "review_required": movement["review_required"],
                "blocked": movement["blocked"],
            },
            "quick_actions": [
                "Can this move?",
                "What proof is missing?",
                "What will Portkey do?",
            ],
            "safety_boundary": {
                "read_only": True,
                "approval_granted": False,
                "approves_access": False,
                "spend_approved": False,
                "permissions_granted": False,
                "external_writes": False,
                "packet_mutated_without_rerun": False,
                "raw_packet_dumped": False,
                "raw_agent_intent_trusted": False,
                "portkey_api_call_made": False,
                "portkey_policy_mutation_allowed": False,
                "human_action_required": True,
            },
            "raw_packet_dumped": False,
            "approves_access": False,
            "read_only": True,
            "coach_provider": "review_run_state_coach",
            "reply": "\n\n".join(reply_lines),
        }
    )


def build_review_run_proofgraph(
    run: ReviewRun,
    *,
    sponsor_trace: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build the dynamic ProofGraph read model for one ReviewRun."""
    repo = run.selected_repo or {}
    repo_name = str(repo.get("full_name") or repo.get("name") or "no repo selected")
    packet = run.packet or {}
    packet_id = packet.get("packet_id")
    revision_id = packet.get("revision_id")
    revision_number = int(packet.get("revision_number") or 0)
    previous_revision_id = packet.get("previous_revision_id")
    movement = normalize_movement_classes(run.movement_classes)
    attached_proof = list(run.attached_proof or [])
    missing_proof = list(run.missing_proof or [])
    attached_proof_ids = {
        str(item.get("id") or "").strip()
        for item in attached_proof
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    }
    unresolved_missing_proof = [
        item
        for item in missing_proof
        if not isinstance(item, Mapping) or str(item.get("id") or "").strip() not in attached_proof_ids
    ]
    unresolved_missing_count = len(unresolved_missing_proof)
    trace = _sanitize_public_value(dict(sponsor_trace or run.sponsor_proof_trace or {}))
    sponsor_steps = trace.get("steps")
    if isinstance(sponsor_steps, list):
        sponsor_step_count = len(sponsor_steps)
    else:
        sponsor_step_count = int(trace.get("step_count") or 0)
    if sponsor_step_count == 0 and run.stage in {"packet_generated", "proof_attached", "ready_to_export"}:
        sponsor_step_count = 0

    if run.stage in {"repo_not_connected", "repo_selected", "request_entered"}:
        graph_state = "waiting_for_packet"
        status_label = "Waiting for packet"
        next_human_action = _review_run_coach_next_action(run)
    elif run.stage == "proof_attached":
        graph_state = "proof_attached_rerun_required"
        status_label = "Proof attached - rerun required"
        next_human_action = "Regenerate the packet from the same request and attached proof."
    elif run.stage == "ready_to_export":
        graph_state = "updated_packet_ready"
        status_label = "Updated packet ready"
        next_human_action = "Export review brief and route the scoped allow-with-policy review."
    else:
        graph_state = "packet_generated"
        status_label = "Packet generated"
        next_human_action = (
            "Attach Support Ops repo-owner approval, Engineering rollback/off-switch proof, "
            "and Security environment-boundary proof, then rerun review."
        )

    portkey_state = _portkey_state(run.portkey_preview, default="Block" if packet_id else "No packet")
    proof_counts = {
        "missing": unresolved_missing_count,
        "attached": len(attached_proof),
        "sponsor_steps": sponsor_step_count,
        "total": unresolved_missing_count + len(attached_proof) + sponsor_step_count,
    }
    node_counts = {
        "repo": 1 if run.selected_repo else 0,
        "packet": 1 if packet_id else 0,
        "proof": proof_counts["total"],
        "downstream": 1,
        "edge": 4 if packet_id else 1,
    }
    packet_label = revision_id or "not_generated"
    graph_id = f"reviewrun-proofgraph-{_digest(f'{run.run_id}:{run.stage}:{packet_label}:{portkey_state}')}"
    generated_from = {
        "source_of_truth": "ReviewRun",
        "run_id": run.run_id,
        "stage": run.stage,
        "selected_repo": repo_name,
        "repo_index_status": run.repo_index_summary.get("status") or "not_indexed",
        "raw_request_hash": run.access_request.get("raw_request_hash"),
    }
    packet_reference = {
        "packet_id": packet_id,
        "revision_id": revision_id,
        "revision_number": revision_number,
        "previous_revision_id": previous_revision_id,
        "verdict": packet.get("verdict") or "not_generated",
        "ready_for_rerun": bool(packet.get("ready_for_rerun")),
        "content_hash": packet.get("content_hash"),
    }
    nodes = [
        {
            "node_id": "repo:selected",
            "node_type": "repo",
            "label": repo_name,
            "summary": "Selected GitHub repo for this ReviewRun.",
            "status": run.repo_index_summary.get("status") or "not_indexed",
        },
        {
            "node_id": "packet:authority",
            "node_type": "packet",
            "label": packet_label,
            "summary": "IA Packet remains the authority; raw agent intent is not trusted.",
            "status": packet.get("verdict") or "not_generated",
        },
        {
            "node_id": "proof:sponsor",
            "node_type": "proof",
            "label": f"{sponsor_step_count} sponsor proof steps",
            "summary": "Sponsors contribute proof only and cannot approve access.",
            "status": "proof_only",
        },
        {
            "node_id": "proof:human",
            "node_type": "proof",
            "label": f"{len(attached_proof)} attached / {unresolved_missing_count} missing",
            "summary": "Human proof can change packet state only after rerun.",
            "status": "ready_for_rerun" if packet.get("ready_for_rerun") else "packet_locked",
        },
        {
            "node_id": "downstream:portkey",
            "node_type": "downstream",
            "label": portkey_state,
            "summary": "Portkey consumes the packet revision; IA does not mutate Portkey policy.",
            "status": "dry_run",
        },
    ]
    edges = [
        {
            "edge_id": "repo-to-packet",
            "from_node_id": "repo:selected",
            "to_node_id": "packet:authority",
            "label": "repo context",
            "can_change_packet_verdict": False,
        },
        {
            "edge_id": "sponsor-to-packet",
            "from_node_id": "proof:sponsor",
            "to_node_id": "packet:authority",
            "label": "proof only",
            "can_change_packet_verdict": False,
        },
        {
            "edge_id": "human-proof-to-packet",
            "from_node_id": "proof:human",
            "to_node_id": "packet:authority",
            "label": "requires rerun",
            "can_change_packet_verdict": run.stage == "ready_to_export",
        },
        {
            "edge_id": "packet-to-portkey",
            "from_node_id": "packet:authority",
            "to_node_id": "downstream:portkey",
            "label": "downstream consumes packet",
            "can_change_packet_verdict": False,
        },
    ]
    proofgraph = {
        "schema_version": REVIEW_RUN_PROOFGRAPH_SCHEMA_VERSION,
        "graph_id": graph_id,
        "generated_from_run_id": run.run_id,
        "generated_from": generated_from,
        "graph_state": graph_state,
        "status_label": status_label,
        "selected_repo": repo_name,
        "packet_reference": packet_reference,
        "proof_counts": proof_counts,
        "node_counts": node_counts,
        "nodes": nodes,
        "edges": edges if packet_id else edges[:1],
        "movement_classes": movement,
        "portkey_state": portkey_state,
        "zero_writes": True,
        "next_human_action": next_human_action,
        "revision_changed": bool(previous_revision_id and revision_id != previous_revision_id),
        "summary": {
            "generated_from_run_id": f"Generated from run_id {run.run_id}",
            "selected_repo": repo_name,
            "packet_revision": revision_id or "not generated",
            "sponsor_proof_count": sponsor_step_count,
            "attached_proof_count": len(attached_proof),
            "portkey_state": portkey_state,
            "zero_writes": "zero writes",
            "authority": "Packet remains authority. Sponsors contribute proof only.",
        },
        "safety_boundary": {
            "read_only": True,
            "approval_granted": False,
            "approves_access": False,
            "permissions_granted": False,
            "external_writes": False,
            "mutates_production": False,
            "packet_mutated_without_rerun": False,
            "portkey_api_call_made": False,
            "portkey_policy_mutation_allowed": False,
            "raw_agent_intent_trusted": False,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }
    proofgraph["content_hash"] = _content_hash(proofgraph)
    return _sanitize_public_value(proofgraph)


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
