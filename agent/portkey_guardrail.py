"""Read-only Portkey BYO Guardrails webhook contract.

Portkey can call this surface before a model request moves. IA reads packet
metadata, returns a packet-backed verdict, and records a local proof event. It
does not call Portkey, mutate Portkey policy, or change the IA Packet.

Docs verified: 2026-06-09
- BYO Guardrails webhook verdict:
  https://portkey.ai/docs/product/guardrails/bring-your-own-guardrails
- Guardrails overview:
  https://portkey.ai/docs/product/guardrails
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .scenarios import ROOT_DIR
from .workbench import WORKBENCH_FIXTURES, build_workbench_result


PORTKEY_GUARDRAIL_SCHEMA_VERSION = "portkey_byo_guardrail.v0"
PORTKEY_GUARDRAIL_EVENT_SCHEMA_VERSION = "portkey_guardrail_event.v0"
PORTKEY_GUARDRAIL_AUTH_ENV = "PORTKEY_GUARDRAIL_TOKEN"
PORTKEY_GUARDRAIL_TOKEN_HEADER = "x-ia-portkey-guardrail-token"
PORTKEY_REHEARSAL_AUTH_ENV = "PORTKEY_REHEARSAL_TOKEN"
PORTKEY_REHEARSAL_MODE_HEADER = "x-ia-rehearsal-mode"
PORTKEY_GUARDRAIL_DOC_URL = "https://portkey.ai/docs/product/guardrails/bring-your-own-guardrails"
PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL = "https://portkey.ai/docs/product/guardrails"
PORTKEY_GUARDRAIL_DELIVERY_MODE = "live_guardrail_webhook"
PORTKEY_EVENT_KIND = "portkey_byo_guardrail"
PORTKEY_REHEARSAL_EVENT_KIND = "rehearsal_probe"
PORTKEY_LOCAL_TEST_EVENT_KIND = "review_run_guardrail_test"
SAFE_PORTKEY_REQUEST_MODES = {
    "dry_run",
    "dry-run",
    "scoped_validation",
    "validation",
    "read_only",
    "read-only",
    "read_only_validation",
}
ALLOWABLE_VERDICT_CLASSES = {"scoped_validation_only", "read_only_validation"}


class PortkeyGuardrailAuthError(ValueError):
    """Raised when the webhook is not authenticated."""


def bearer_or_token(value: str | None) -> str:
    """Normalize a raw token or Authorization: Bearer value."""
    if not value:
        return ""
    stripped = value.strip()
    if stripped.lower().startswith("bearer "):
        return stripped[7:].strip()
    return stripped


def validate_portkey_guardrail_token(
    *,
    provided_token: str | None,
    expected_token: str | None,
) -> None:
    """Validate the shared webhook token without exposing it in responses."""
    expected = (expected_token or "").strip()
    if not expected:
        raise PortkeyGuardrailAuthError("portkey_guardrail_token_not_configured")
    if not hmac.compare_digest(bearer_or_token(provided_token), expected):
        raise PortkeyGuardrailAuthError("invalid_portkey_guardrail_token")


def resolve_portkey_guardrail_event_kind(
    *,
    rehearsal_token: str | None,
    expected_rehearsal_token: str | None,
) -> str:
    """Classify a webhook event without weakening auth."""
    expected = (expected_rehearsal_token or "").strip()
    provided = rehearsal_token.strip() if isinstance(rehearsal_token, str) else ""
    if expected and hmac.compare_digest(provided, expected):
        return PORTKEY_REHEARSAL_EVENT_KIND
    return PORTKEY_EVENT_KIND


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def extract_portkey_metadata(body: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from the documented Portkey webhook body shape.

    The public demo expects packet metadata directly under `metadata`, while
    tolerating nested request/provider metadata fields when Portkey forwards
    them from a gateway request.
    """
    candidates = [
        body.get("metadata"),
        body.get("request", {}).get("metadata") if isinstance(body.get("request"), dict) else None,
        body.get("data", {}).get("metadata") if isinstance(body.get("data"), dict) else None,
        body.get("request", {}).get("json", {}).get("metadata")
        if isinstance(body.get("request"), dict) and isinstance(body.get("request", {}).get("json"), dict)
        else None,
    ]
    for candidate in candidates:
        metadata = _as_metadata(candidate)
        if metadata:
            return metadata
    return {}


def _fixture_for_packet_id(packet_id: str) -> str | None:
    for fixture in WORKBENCH_FIXTURES:
        try:
            result = build_workbench_result(fixture.fixture_id)
        except (KeyError, ValueError):
            continue
        if result["packet_reference"]["packet_id"] == packet_id:
            return fixture.fixture_id
    return None


def resolve_portkey_fixture(metadata: dict[str, Any]) -> tuple[str | None, str]:
    """Resolve the IA fixture from Portkey metadata."""
    fixture = metadata.get("ia_fixture") or metadata.get("fixture") or metadata.get("scenario")
    if isinstance(fixture, str) and fixture.strip():
        return fixture.strip(), "ia_fixture"

    packet_id = metadata.get("ia_packet_id")
    if isinstance(packet_id, str) and packet_id.strip():
        matched = _fixture_for_packet_id(packet_id.strip())
        return matched, "ia_packet_id"

    return None, "metadata_missing"


def _requested_mode(metadata: dict[str, Any]) -> str:
    value = (
        metadata.get("ia_requested_mode")
        or metadata.get("ia_movement")
        or metadata.get("allowed_mode")
        or metadata.get("mode")
        or ""
    )
    return str(value).strip().lower().replace(" ", "_")


def extract_portkey_requested_mode(metadata: dict[str, Any]) -> str:
    """Return the normalized Portkey movement mode metadata."""
    return _requested_mode(metadata)


def _deny_reasons(result: dict[str, Any], reason: str) -> list[str]:
    reasons = list(result.get("blocked_claims", []))[:6]
    if reason and reason not in reasons:
        reasons.insert(0, reason)
    return reasons[:8]


def _packet_allows_portkey_movement(
    result: dict[str, Any],
    *,
    requested_mode: str,
) -> tuple[bool, str]:
    decision = result["decision"]
    verdict_class = decision["verdict_class"]
    if requested_mode not in SAFE_PORTKEY_REQUEST_MODES:
        return False, "requested_mode_not_packet_scoped"
    if verdict_class not in ALLOWABLE_VERDICT_CLASSES:
        return False, "packet_verdict_does_not_allow_movement"
    if decision["production_access"] or decision["permission_grants"] or decision["external_writes"]:
        return False, "packet_blocks_live_or_write_scope"
    if decision["approves_spend"] or decision["selects_provider"] or decision["guarantees_savings"]:
        return False, "packet_blocks_spend_or_provider_movement"
    return True, "packet_allows_scoped_validation_only"


def build_portkey_guardrail_response(
    body: dict[str, Any],
    *,
    elapsed_ms: int = 0,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the Portkey BYO Guardrails response from public IA packet truth."""
    if not isinstance(body, dict):
        body = {}

    metadata = extract_portkey_metadata(body)
    fixture_id, resolved_by = resolve_portkey_fixture(metadata)
    requested_mode = _requested_mode(metadata)

    if fixture_id is None:
        return {
            "verdict": False,
            "data": {
                "schema_version": PORTKEY_GUARDRAIL_SCHEMA_VERSION,
                "delivery_mode": PORTKEY_GUARDRAIL_DELIVERY_MODE,
                "portkey_surface": "BYO Guardrails webhook",
                "docs_reference": {
                    "guardrail_webhook": PORTKEY_GUARDRAIL_DOC_URL,
                    "guardrails_overview": PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
                    "last_verified": "2026-06-09",
                },
                "generated_at": generated_at or _utc_now(),
                "elapsed_ms": elapsed_ms,
                "metadata_resolved_by": resolved_by,
                "requested_mode": requested_mode or None,
                "deny_reasons": ["packet_metadata_missing"],
                "next_human_action": "Attach IA packet metadata before Portkey allows movement.",
                "safety": _safety_payload(),
            },
        }

    try:
        result = build_workbench_result(fixture_id)
    except (KeyError, ValueError):
        return {
            "verdict": False,
            "data": {
                "schema_version": PORTKEY_GUARDRAIL_SCHEMA_VERSION,
                "delivery_mode": PORTKEY_GUARDRAIL_DELIVERY_MODE,
                "portkey_surface": "BYO Guardrails webhook",
                "docs_reference": {
                    "guardrail_webhook": PORTKEY_GUARDRAIL_DOC_URL,
                    "guardrails_overview": PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
                    "last_verified": "2026-06-09",
                },
                "generated_at": generated_at or _utc_now(),
                "elapsed_ms": elapsed_ms,
                "metadata_resolved_by": resolved_by,
                "fixture": fixture_id,
                "requested_mode": requested_mode or None,
                "deny_reasons": ["packet_not_found"],
                "next_human_action": "Use a registered IA fixture or packet_id before Portkey allows movement.",
                "safety": _safety_payload(),
            },
        }

    allowed, reason = _packet_allows_portkey_movement(result, requested_mode=requested_mode)
    packet = result["packet_reference"]
    decision = result["decision"]

    return {
        "verdict": allowed,
        "data": {
            "schema_version": PORTKEY_GUARDRAIL_SCHEMA_VERSION,
            "delivery_mode": PORTKEY_GUARDRAIL_DELIVERY_MODE,
            "portkey_surface": "BYO Guardrails webhook",
            "docs_reference": {
                "guardrail_webhook": PORTKEY_GUARDRAIL_DOC_URL,
                "guardrails_overview": PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
                "last_verified": "2026-06-09",
            },
            "generated_at": generated_at or _utc_now(),
            "elapsed_ms": elapsed_ms,
            "metadata_resolved_by": resolved_by,
            "fixture": result["fixture"]["fixture_id"],
            "requested_mode": requested_mode or None,
            "ia_packet_reference": {
                "packet_id": packet["packet_id"],
                "revision_id": packet["revision_id"],
                "content_hash": packet["content_hash"],
            },
            "verdict_class": decision["verdict_class"],
            "reason": reason,
            "deny_reasons": [] if allowed else _deny_reasons(result, reason),
            "missing_proof": list(result.get("missing_proof", []))[:8],
            "reviewer_routing": list(result.get("reviewer_routing", []))[:8],
            "next_human_action": decision["next_human_action"],
            "safety": _safety_payload(),
        },
    }


def _safety_payload() -> dict[str, bool]:
    return {
        "read_only": True,
        "packet_mutation_allowed": False,
        "portkey_policy_mutation_allowed": False,
        "portkey_api_call_made": False,
        "approves_access": False,
        "approves_spend": False,
        "executes_external_writes": False,
        "mutates_production": False,
        "raw_agent_intent_trusted": False,
    }


def build_portkey_guardrail_event(
    *,
    body: dict[str, Any],
    response: dict[str, Any],
    elapsed_ms: int,
    kind: str = PORTKEY_EVENT_KIND,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a local proof event for the webhook call."""
    timestamp = generated_at or _utc_now()
    data = response.get("data", {})
    metadata = extract_portkey_metadata(body if isinstance(body, dict) else {})
    packet_ref = data.get("ia_packet_reference")
    packet_ref = packet_ref if isinstance(packet_ref, dict) else {}
    digest_payload = {
        "packet_reference": packet_ref,
        "verdict": response.get("verdict"),
        "reason": data.get("reason"),
        "requested_mode": data.get("requested_mode"),
        "generated_at": timestamp,
    }
    event_id = f"portkey-guardrail-{_stable_digest(digest_payload)[:12]}-{uuid.uuid4().hex[:8]}"
    return {
        "schema_version": PORTKEY_GUARDRAIL_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "kind": kind,
        "generated_at": timestamp,
        "delivery_mode": data.get("delivery_mode") or PORTKEY_GUARDRAIL_DELIVERY_MODE,
        "read_only": True,
        "event_type": str(body.get("eventType") or body.get("event_type") or "unknown"),
        "verdict": bool(response.get("verdict")),
        "elapsed_ms": elapsed_ms,
        "packet_reference": packet_ref,
        "review_run_id": metadata.get("ia_review_run_id") or packet_ref.get("run_id"),
        "packet_id": metadata.get("ia_packet_id") or packet_ref.get("packet_id"),
        "revision_id": metadata.get("ia_revision_id") or packet_ref.get("revision_id"),
        "reason": data.get("reason"),
        "requested_mode": data.get("requested_mode"),
        "api_mutation": False,
        "policy_mutation": False,
        "external_writes": False,
        "safety": data.get("safety", _safety_payload()),
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def write_portkey_guardrail_event(
    event: dict[str, Any],
    *,
    ledger_dir: Path,
) -> Path:
    """Persist a local Portkey webhook proof event under ignored state."""
    ledger_dir = ledger_dir.resolve()
    events_dir = ledger_dir / "portkey_guardrail_events"
    events_dir.mkdir(parents=True, exist_ok=True)
    path = events_dir / f"{event['event_id']}.json"
    path.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def list_portkey_guardrail_events(*, ledger_dir: Path) -> list[dict[str, Any]]:
    """Load local Portkey webhook proof events newest-first."""
    events_dir = ledger_dir.resolve() / "portkey_guardrail_events"
    if not events_dir.is_dir():
        return []
    events: list[dict[str, Any]] = []
    for path in sorted(events_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if event.get("schema_version") == PORTKEY_GUARDRAIL_EVENT_SCHEMA_VERSION:
            events.append(event)
    return events


def relative_event_path(path: Path) -> str:
    """Return a repo-relative path where possible for API display."""
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
