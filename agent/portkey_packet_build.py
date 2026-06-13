"""Portkey Governance + Build — packet implementation plan and BYOK execution."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .connector_runtime import _raw_connection, _set_connection
from .portkey_guardrail import build_portkey_guardrail_response
from .portkey_plane_b import (
    PORTKEY_CONNECTOR_ID,
    PORTKEY_PLANE_B_SCHEMA_VERSION,
    _plane_b_safety,
    portkey_plane_b_status,
    proxy_portkey_chat,
)
from .review_run import (
    ReviewRun,
    build_review_run_portkey_guardrail_test,
    normalize_movement_classes,
    review_run_packet_projection,
)

PORTKEY_PACKET_BUILD_SCHEMA_VERSION = "portkey_packet_build.v1"


def _packet_metadata(run: ReviewRun) -> dict[str, str]:
    packet = run.packet or {}
    return {
        "ia_review_run_id": str(run.run_id),
        "ia_packet_id": str(packet.get("packet_id") or ""),
        "ia_revision_id": str(packet.get("revision_id") or ""),
        "ia_content_hash": str(packet.get("content_hash") or ""),
        "ia_requested_mode": "scoped_validation",
        "ia_source_of_truth": "ReviewRun",
        "ia_verdict": str(packet.get("verdict") or ""),
    }


def _build_graph_nodes(*, run: ReviewRun, session_verified: bool, implemented: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    packet = run.packet or {}
    movement = normalize_movement_classes(run.movement_classes)
    impl_steps = {step.get("id"): step for step in (implemented or {}).get("steps") or [] if isinstance(step, dict)}
    packet_ready = run.stage == "ready_to_export"

    def step_status(node_id: str, *, default: str = "pending") -> str:
        return str(impl_steps.get(node_id, {}).get("status") or default)

    return [
        {
            "id": "ia_packet",
            "label": "IA Packet authority",
            "detail": f"{packet.get('packet_id')} · {packet.get('revision_id')}",
            "kind": "source",
            "implementable": False,
            "status": "ready" if packet.get("packet_id") else "blocked",
            "portkey_surface": "ReviewRun packet projection",
        },
        {
            "id": "byok_gateway",
            "label": "BYOK inference gateway",
            "detail": "chat/completions + completions via your Portkey API key",
            "kind": "capability",
            "implementable": True,
            "status": "ready" if session_verified else "blocked",
            "portkey_surface": "POST /v1/chat/completions",
            "requires": ["ia_packet"],
        },
        {
            "id": "metadata_binding",
            "label": "Packet metadata on gateway calls",
            "detail": "ia_packet_id, ia_revision_id, ia_review_run_id on x-portkey-metadata",
            "kind": "implementable",
            "implementable": True,
            "status": step_status("metadata_binding", default="ready" if session_verified else "blocked"),
            "portkey_surface": "x-portkey-metadata header",
            "requires": ["ia_packet", "byok_gateway"],
        },
        {
            "id": "scoped_inference_probe",
            "label": "Scoped inference probe",
            "detail": f"Allowed: {', '.join(movement['allowed'][:3]) or 'none'}",
            "kind": "implementable",
            "implementable": True,
            "status": step_status("scoped_inference_probe"),
            "portkey_surface": "Plane B proxy with packet system prompt",
            "requires": ["metadata_binding"],
        },
        {
            "id": "local_packet_guardrail",
            "label": "Packet guardrail verdict (IA)",
            "detail": "IA returns allow/block from packet movement classes",
            "kind": "implementable",
            "implementable": True,
            "status": step_status("local_packet_guardrail", default="ready"),
            "portkey_surface": "POST /api/portkey/guardrail (BYO webhook target)",
            "requires": ["ia_packet"],
        },
        {
            "id": "guardrail_webhook_export",
            "label": "BYO Guardrail webhook config",
            "detail": "Dashboard paste — webhook URL + metadata JSON for this packet",
            "kind": "implementable",
            "implementable": True,
            "status": step_status("guardrail_webhook_export"),
            "portkey_surface": "Portkey dashboard BYO Guardrail",
            "requires": ["local_packet_guardrail"],
        },
        {
            "id": "dashboard_guardrail_attach",
            "label": "Attach guardrail in Portkey dashboard",
            "detail": "Operator pastes exported config; IA cannot call Admin API",
            "kind": "manual",
            "implementable": False,
            "status": step_status("dashboard_guardrail_attach", default="pending"),
            "portkey_surface": "Manual — app.portkey.ai guardrails",
            "requires": ["guardrail_webhook_export"],
        },
        {
            "id": "live_webhook_proof",
            "label": "Live webhook proof",
            "detail": "Portkey calls IA before model movement with packet metadata",
            "kind": "verify",
            "implementable": False,
            "status": "ready" if packet_ready else "pending",
            "portkey_surface": "ReviewRun Portkey live proof step",
            "requires": ["dashboard_guardrail_attach"],
        },
        {
            "id": "admin_policy_push",
            "label": "Admin API policy push",
            "detail": "Not available in BYOK demo — would mutate Portkey policy",
            "kind": "blocked",
            "implementable": False,
            "status": "blocked",
            "portkey_surface": "Portkey Admin API (disabled)",
            "requires": [],
        },
        {
            "id": "virtual_key_provision",
            "label": "Virtual key provisioning",
            "detail": "Not available in BYOK demo — requires Admin API",
            "kind": "blocked",
            "implementable": False,
            "status": "blocked",
            "portkey_surface": "Portkey Admin API (disabled)",
            "requires": [],
        },
    ]


def _build_graph_edges() -> list[dict[str, str]]:
    return [
        {"from": "ia_packet", "to": "byok_gateway"},
        {"from": "ia_packet", "to": "local_packet_guardrail"},
        {"from": "byok_gateway", "to": "metadata_binding"},
        {"from": "metadata_binding", "to": "scoped_inference_probe"},
        {"from": "local_packet_guardrail", "to": "guardrail_webhook_export"},
        {"from": "guardrail_webhook_export", "to": "dashboard_guardrail_attach"},
        {"from": "dashboard_guardrail_attach", "to": "live_webhook_proof"},
    ]


def build_portkey_packet_implementation_plan(
    run: ReviewRun,
    session_id: str,
    *,
    public_base_url: str,
) -> dict[str, Any]:
    """Graph of what Portkey can consume from this packet with the session BYOK key."""
    status = portkey_plane_b_status(session_id)
    conn = _raw_connection(session_id, PORTKEY_CONNECTOR_ID)
    implemented = (conn or {}).get("packet_implementation") or {}
    if str(implemented.get("run_id") or "") != run.run_id:
        implemented = {}
    nodes = _build_graph_nodes(run=run, session_verified=bool(status.get("verified")), implemented=implemented)
    implementable = [node for node in nodes if node.get("implementable")]
    return {
        "ok": True,
        "schema_version": PORTKEY_PACKET_BUILD_SCHEMA_VERSION,
        "read_only": True,
        "run_id": run.run_id,
        "packet_reference": {
            "packet_id": run.packet.get("packet_id"),
            "revision_id": run.packet.get("revision_id"),
            "content_hash": run.packet.get("content_hash"),
        },
        "portkey_session": {
            "connected": status.get("connected"),
            "verified": status.get("verified"),
            "resolved_model": status.get("resolved_model"),
            "provider_slug": status.get("provider_slug"),
        },
        "movement_classes": normalize_movement_classes(run.movement_classes),
        "graph": {
            "nodes": nodes,
            "edges": _build_graph_edges(),
        },
        "summary": {
            "implementable_via_byok": len(implementable),
            "manual_operator_steps": len([n for n in nodes if n.get("kind") == "manual"]),
            "blocked_admin_api": len([n for n in nodes if n.get("kind") == "blocked"]),
            "implemented": bool(implemented.get("completed")),
        },
        "public_base_url": public_base_url.rstrip("/"),
        "safety_boundary": _plane_b_safety(),
    }


def _guardrail_setup_for_run(run: ReviewRun, public_base_url: str) -> dict[str, Any]:
    metadata = _packet_metadata(run)
    base = public_base_url.rstrip("/")
    webhook_url = f"{base}/api/portkey/guardrail"
    return {
        "guardrail_type": "Bring Your Own Guardrail",
        "webhook_url": webhook_url,
        "headers_json": {
            "Authorization": "Bearer <PORTKEY_GUARDRAIL_TOKEN>",
            "Content-Type": "application/json",
        },
        "metadata_json": metadata,
        "timeout_ms": 3000,
        "expected_response_shape": {"verdict": "boolean", "data": "IA packet reference + deny reasons"},
    }


def _scoped_probe_messages(run: ReviewRun) -> list[dict[str, str]]:
    packet = run.packet or {}
    movement = normalize_movement_classes(run.movement_classes)
    projection = review_run_packet_projection(run)
    return [
        {
            "role": "system",
            "content": (
                f"You route under IA packet {packet.get('packet_id')} revision {packet.get('revision_id')}. "
                f"Allowed scope: {', '.join(movement['allowed']) or 'none'}. "
                f"Blocked scope: {', '.join(movement['blocked']) or 'none'}. "
                f"Verdict class: {packet.get('verdict')}. "
                "Do not approve blocked scope."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Confirm packet-gated routing for ReviewRun {run.run_id}. "
                f"Next human action: {projection['decision'].get('next_human_action', 'follow packet')} "
                "Reply with exactly: packet-routed"
            ),
        },
    ]


def implement_portkey_packet_build(
    run: ReviewRun,
    session_id: str,
    *,
    public_base_url: str,
) -> dict[str, Any]:
    """Execute all BYOK-implementable steps for this packet."""
    plan = build_portkey_packet_implementation_plan(run, session_id, public_base_url=public_base_url)
    if not plan["portkey_session"].get("verified"):
        return {
            "ok": False,
            "message": "Connect and verify Portkey on /portkey/signin first.",
            "needs_sign_in": True,
            "plan": plan,
        }
    if not run.packet.get("packet_id"):
        return {"ok": False, "message": "Generate an IA Packet before Governance + Build."}

    metadata = _packet_metadata(run)
    movement = normalize_movement_classes(run.movement_classes)
    steps: list[dict[str, Any]] = []

    _set_connection(
        session_id,
        PORTKEY_CONNECTOR_ID,
        {
            "packet_implementation": {
                "run_id": run.run_id,
                "packet_id": metadata["ia_packet_id"],
                "revision_id": metadata["ia_revision_id"],
                "started_at": metadata.get("ia_content_hash"),
            },
            "packet_metadata": metadata,
        },
    )
    steps.append(
        {
            "id": "metadata_binding",
            "status": "done",
            "detail": "Packet metadata bound to Portkey session.",
            "metadata": metadata,
        }
    )

    probe = proxy_portkey_chat(
        session_id,
        messages=_scoped_probe_messages(run),
        metadata=metadata,
    )
    steps.append(
        {
            "id": "scoped_inference_probe",
            "status": "done" if probe.get("ok") else "failed",
            "detail": probe.get("reply") or probe.get("message") or "Probe failed",
            "model": probe.get("model"),
            "usage": probe.get("usage"),
        }
    )

    guardrail_test = build_review_run_portkey_guardrail_test(run)
    webhook_body = {
        "eventType": "beforeRequestHook",
        "metadata": metadata,
        "request": {"metadata": metadata, "model": "packet-gated-model", "messages": []},
    }
    live_guardrail = build_portkey_guardrail_response(webhook_body, elapsed_ms=0)
    steps.append(
        {
            "id": "local_packet_guardrail",
            "status": "done",
            "detail": f"Verdict: {guardrail_test.get('verdict')}",
            "verdict": guardrail_test.get("verdict"),
            "portkey_state": guardrail_test.get("portkey_state"),
            "still_blocked_scope": guardrail_test.get("still_blocked_scope"),
        }
    )

    guardrail_export = _guardrail_setup_for_run(run, public_base_url)
    steps.append(
        {
            "id": "guardrail_webhook_export",
            "status": "done",
            "detail": "Webhook config generated for this packet revision.",
            "dashboard_config": guardrail_export,
        }
    )

    completed = probe.get("ok") is True
    implementation = {
        "schema_version": PORTKEY_PACKET_BUILD_SCHEMA_VERSION,
        "run_id": run.run_id,
        "packet_id": metadata["ia_packet_id"],
        "revision_id": metadata["ia_revision_id"],
        "completed": completed,
        "steps": steps,
        "movement_classes": movement,
        "guardrail_test": guardrail_test,
        "guardrail_live_simulation": live_guardrail,
        "guardrail_dashboard_config": guardrail_export,
        "inference_probe": probe,
    }
    _set_connection(
        session_id,
        PORTKEY_CONNECTOR_ID,
        {"packet_implementation": implementation},
    )

    updated_plan = build_portkey_packet_implementation_plan(run, session_id, public_base_url=public_base_url)
    return {
        "ok": completed,
        "message": (
            "Packet implemented via Portkey BYOK gateway. Paste guardrail config in Portkey dashboard for live webhook proof."
            if completed
            else "Packet binding succeeded but inference probe failed. Check provider/model on /portkey/signin."
        ),
        "implementation": implementation,
        "plan": updated_plan,
        "safety_boundary": _plane_b_safety(),
    }
