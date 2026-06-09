"""Portkey BYO Guardrails webhook contract tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import HTTPException

from agent.portkey_guardrail import (
    PORTKEY_GUARDRAIL_SCHEMA_VERSION,
    build_portkey_guardrail_response,
    list_portkey_guardrail_events,
    validate_portkey_guardrail_token,
)
from web import app as web_app
from web.app import app, portkey_guardrail_events, portkey_guardrail_webhook


class _FakeRequest:
    def __init__(self, body: dict) -> None:
        self._body = body

    async def json(self) -> dict:
        return self._body


def _portkey_body(fixture: str, *, requested_mode: str = "model_request") -> dict:
    return {
        "eventType": "beforeRequestHook",
        "metadata": {
            "ia_fixture": fixture,
            "ia_requested_mode": requested_mode,
        },
        "request": {
            "model": "demo-model",
            "messages": [{"role": "user", "content": "demo"}],
        },
    }


def _post_guardrail(body: dict, *, token: str | None = None, authorization: str | None = None) -> dict:
    return asyncio.run(
        portkey_guardrail_webhook(
            request=_FakeRequest(body),
            authorization=authorization,
            x_ia_portkey_guardrail_token=token,
        )
    )


def _expect_http_error(
    body: dict,
    *,
    status_code: int,
    detail: str,
    token: str | None = None,
    authorization: str | None = None,
) -> None:
    try:
        _post_guardrail(body, token=token, authorization=authorization)
    except HTTPException as exc:
        assert exc.status_code == status_code
        assert exc.detail == detail
        return
    raise AssertionError(f"Expected HTTPException {status_code}:{detail}")


def test_portkey_guardrail_spend_packet_fails_closed() -> None:
    response = build_portkey_guardrail_response(
        _portkey_body("ai_spend_budget_overrun", requested_mode="model_request"),
        elapsed_ms=7,
        generated_at="2026-06-09T00:00:00Z",
    )

    assert response["verdict"] is False
    data = response["data"]
    assert data["schema_version"] == PORTKEY_GUARDRAIL_SCHEMA_VERSION
    assert data["delivery_mode"] == "live_guardrail_webhook"
    assert data["ia_packet_reference"]["packet_id"] == "ia-spend-review-ai_spend_budget_overrun-v0"
    assert data["verdict_class"] == "finance_procurement_review_required"
    assert data["reason"] == "requested_mode_not_packet_scoped"
    assert data["safety"]["portkey_policy_mutation_allowed"] is False
    assert data["safety"]["portkey_api_call_made"] is False
    assert data["safety"]["raw_agent_intent_trusted"] is False


def test_portkey_guardrail_allows_only_scoped_validation_mode() -> None:
    response = build_portkey_guardrail_response(
        _portkey_body("read_only_analytics_agent", requested_mode="read_only_validation"),
        elapsed_ms=3,
        generated_at="2026-06-09T00:00:00Z",
    )

    assert response["verdict"] is True
    data = response["data"]
    assert data["verdict_class"] == "read_only_validation"
    assert data["deny_reasons"] == []
    assert data["reason"] == "packet_allows_scoped_validation_only"
    assert data["safety"]["approves_access"] is False
    assert data["safety"]["executes_external_writes"] is False


def test_portkey_guardrail_unknown_or_missing_packet_fails_closed() -> None:
    missing_metadata = build_portkey_guardrail_response({}, generated_at="2026-06-09T00:00:00Z")
    unknown_fixture = build_portkey_guardrail_response(
        {
            "metadata": {
                "ia_fixture": "missing_fixture",
                "ia_requested_mode": "scoped_validation",
            }
        },
        generated_at="2026-06-09T00:00:00Z",
    )

    assert missing_metadata["verdict"] is False
    assert missing_metadata["data"]["deny_reasons"] == ["packet_metadata_missing"]
    assert unknown_fixture["verdict"] is False
    assert unknown_fixture["data"]["deny_reasons"] == ["packet_not_found"]


def test_portkey_guardrail_auth_accepts_header_or_bearer_token() -> None:
    validate_portkey_guardrail_token(provided_token="demo-token", expected_token="demo-token")
    validate_portkey_guardrail_token(provided_token="Bearer demo-token", expected_token="demo-token")


def test_portkey_guardrail_api_requires_configured_auth(monkeypatch) -> None:
    monkeypatch.delenv("PORTKEY_GUARDRAIL_TOKEN", raising=False)

    _expect_http_error(
        _portkey_body("ai_spend_budget_overrun"),
        status_code=503,
        detail="portkey_guardrail_token_not_configured",
    )


def test_portkey_guardrail_api_rejects_missing_or_wrong_auth(monkeypatch) -> None:
    monkeypatch.setenv("PORTKEY_GUARDRAIL_TOKEN", "demo-token")

    _expect_http_error(
        _portkey_body("ai_spend_budget_overrun"),
        status_code=401,
        detail="invalid_portkey_guardrail_token",
    )
    _expect_http_error(
        _portkey_body("ai_spend_budget_overrun"),
        status_code=401,
        detail="invalid_portkey_guardrail_token",
        token="wrong",
    )


def test_portkey_guardrail_api_records_read_only_event(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PORTKEY_GUARDRAIL_TOKEN", "demo-token")
    monkeypatch.setattr(web_app, "SPONSOR_PROOF_RUN_LEDGER_DIR", tmp_path)

    payload = _post_guardrail(
        _portkey_body("ai_spend_budget_overrun"),
        token="demo-token",
    )

    assert payload["verdict"] is False
    assert payload["data"]["guardrail_event"]["event_id"].startswith("portkey-guardrail-")
    assert payload["data"]["elapsed_ms"] < 150

    events = list_portkey_guardrail_events(ledger_dir=tmp_path)
    assert len(events) == 1
    assert events[0]["verdict"] is False
    assert events[0]["read_only"] is True
    assert events[0]["safety"]["portkey_policy_mutation_allowed"] is False
    assert events[0]["safety"]["portkey_api_call_made"] is False

    event_response = portkey_guardrail_events()
    assert event_response["read_only"] is True
    assert event_response["events"][0]["event_id"] == events[0]["event_id"]


def test_portkey_guardrail_route_is_post_only() -> None:
    route = next(route for route in app.routes if getattr(route, "path", "") == "/api/portkey/guardrail")
    assert route.methods == {"POST"}
