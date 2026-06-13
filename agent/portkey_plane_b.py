"""Portkey Plane B — optional BYOK gateway shell (separate from Plane A governance)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Literal, Mapping

from .connector_oauth import disconnect, public_connection, save_user_api_key
from .connector_runtime import _raw_connection, _set_connection
from .portkey_setup import build_portkey_guardrail_setup, render_portkey_guardrail_setup_markdown

PORTKEY_PLANE_B_SCHEMA_VERSION = "portkey_plane_b.v1"
PORTKEY_CONNECTOR_ID = "portkey"
PORTKEY_GATEWAY_URL = os.getenv("PORTKEY_GATEWAY_URL", "https://api.portkey.ai/v1").rstrip("/")
PORTKEY_AUTH_DOC_URL = "https://portkey.ai/docs/api-reference/inference-api/authentication"
PORTKEY_JWT_DOC_URL = "https://portkey.ai/docs/product/enterprise-offering/org-management/jwt"
PORTKEY_APP_MODEL_CATALOG_URL = "https://app.portkey.ai/model-catalog"
PORTKEY_APP_API_KEYS_URL = "https://app.portkey.ai/api-keys"
PORTKEY_HTTP_USER_AGENT = os.getenv(
    "PORTKEY_HTTP_USER_AGENT",
    "InferenceAtlas/1.0 (+https://github.com/jayeshsuyal/inferenceatlas-agent-demo)",
)
DEFAULT_PROXY_MODEL = os.getenv("PORTKEY_PLANE_B_DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_VERIFY_MODEL = os.getenv("PORTKEY_PLANE_B_VERIFY_MODEL", DEFAULT_PROXY_MODEL)
DEFAULT_TEST_PROMPT = "Reply with exactly: connected"

ConnectionState = Literal["disconnected", "saved", "verified", "needs_provider", "verify_failed"]


def _plane_b_safety() -> dict[str, bool]:
    return {
        "governance_shell_unchanged": True,
        "plane_a_guardrail_non_mutating": True,
        "portkey_policy_mutation_allowed": False,
        "portkey_admin_api_called": False,
        "packet_mutation_allowed": False,
        "external_writes": False,
        "secrets_returned": False,
    }


def _wizard_steps() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "title": "Add an AI provider in Portkey (one-time)",
            "detail": "Connect OpenAI or another model. Note the slug (e.g. iaagent1) from API Setup.",
            "action_label": "Open Model Catalog",
            "action_url": PORTKEY_APP_MODEL_CATALOG_URL,
        },
        {
            "step": "2",
            "title": "Copy your Portkey API key",
            "detail": "Use the default workspace key — click Reveal, then copy.",
            "action_label": "Open API Keys",
            "action_url": PORTKEY_APP_API_KEYS_URL,
        },
        {
            "step": "3",
            "title": "Paste below — we save, auto-route, and test",
            "detail": "One click. Key stays in this browser session only.",
            "action_label": "",
            "action_url": "",
        },
    ]


def _is_cloudflare_access_denied(detail: str) -> bool:
    lowered = detail.lower()
    return (
        "error_1010" in lowered
        or "browser_signature_banned" in lowered
        or "cloudflare_error" in lowered
    )


def _next_action_for_verify_failure(verification: dict[str, Any]) -> dict[str, str]:
    code = verification.get("http_status")
    detail = str(verification.get("detail") or verification.get("message") or "").strip()
    lowered = detail.lower()

    if _is_cloudflare_access_denied(detail):
        return {
            "title": "Portkey gateway blocked this request",
            "detail": (
                "Cloudflare rejected the verify call from this server (not your API key). "
                "Update InferenceAtlas and retry — a User-Agent header is now sent on verify."
            ),
            "action_label": "Open API Keys",
            "action_url": PORTKEY_APP_API_KEYS_URL,
        }
    if code == 401 or "invalid api key" in lowered:
        return {
            "title": "Check your Portkey API key",
            "detail": detail or "Portkey rejected the API key. Reveal and copy the default workspace key.",
            "action_label": "Open API Keys",
            "action_url": PORTKEY_APP_API_KEYS_URL,
        }
    if code == 403:
        return {
            "title": "Check provider slug and model",
            "detail": detail
            or (
                "Use the provider slug from Portkey (e.g. iaagent1) and model name only "
                "(e.g. babbage-002), not the full @slug/model path in both fields."
            ),
            "action_label": "Open Model Catalog",
            "action_url": PORTKEY_APP_MODEL_CATALOG_URL,
        }
    return {
        "title": "Check your Portkey setup",
        "detail": detail or verification.get("message", "Verification failed."),
        "action_label": "Open API Keys",
        "action_url": PORTKEY_APP_API_KEYS_URL,
    }


def _connection_state(entry: dict[str, Any]) -> ConnectionState:
    if entry.get("status") != "connected" or not entry.get("api_key"):
        return "disconnected"
    if entry.get("verified") is True:
        return "verified"
    if not str(entry.get("provider_slug", "")).strip():
        return "needs_provider"
    if entry.get("last_verify_ok") is False:
        return "verify_failed"
    return "saved"


def _save_portkey_session(
    session_id: str,
    api_key: str,
    *,
    provider: str = "",
    model: str = "",
) -> dict[str, Any]:
    saved = save_user_api_key(session_id, PORTKEY_CONNECTOR_ID, api_key)
    if not saved.get("ok"):
        return saved
    slug, model_suffix = _normalize_provider_model(provider, model.strip() or DEFAULT_VERIFY_MODEL)
    patch: dict[str, Any] = {"provider_slug": slug, "model_suffix": model_suffix}
    if slug:
        patch["resolved_model"] = _resolve_portkey_model(model_suffix, slug)[0]
    _set_connection(session_id, PORTKEY_CONNECTOR_ID, patch)
    return saved


def connect_portkey(
    session_id: str,
    api_key: str,
    *,
    provider: str = "",
    model: str = "",
    run_test: bool = True,
) -> dict[str, Any]:
    """Save the user's Portkey key, optionally verify + run an automatic test."""
    key = api_key.strip()
    if len(key) < 8:
        return {"ok": False, "message": "Portkey API key too short."}

    slug, model_suffix = _normalize_provider_model(provider, model.strip() or DEFAULT_VERIFY_MODEL)
    saved = _save_portkey_session(session_id, key, provider=slug, model=model_suffix)
    if not saved.get("ok"):
        return saved

    if not slug:
        return {
            "ok": True,
            "connection_state": "needs_provider",
            "message": "API key saved. Enter your provider slug from Portkey (e.g. iaagent1).",
            "provider_slug": "",
            "model_suffix": model_suffix,
            "resolved_model": "",
            "safety_boundary": _plane_b_safety(),
        }

    verify = verify_portkey_api_key(key, model=model_suffix, provider=slug)
    resolved = verify.get("model") or _resolve_portkey_model(model_suffix, slug)[0]
    _set_connection(
        session_id,
        PORTKEY_CONNECTOR_ID,
        {
            "last_verify_ok": verify.get("ok"),
            "verified": bool(verify.get("ok")),
            "provider_slug": slug,
            "model_suffix": model_suffix,
            "resolved_model": resolved,
        },
    )

    if not verify.get("ok"):
        return {
            "ok": True,
            "connection_state": "verify_failed",
            "message": "API key saved, but Portkey is not routing yet.",
            "verification": verify,
            "next_action": _next_action_for_verify_failure(verify),
            "provider_slug": slug,
            "model_suffix": model_suffix,
            "resolved_model": resolved,
            "safety_boundary": _plane_b_safety(),
        }

    test_reply = None
    if run_test:
        test = proxy_portkey_chat(
            session_id,
            messages=[{"role": "user", "content": DEFAULT_TEST_PROMPT}],
            model=model_suffix,
            provider=slug,
        )
        if test.get("ok"):
            test_reply = test.get("reply")
        else:
            _set_connection(
                session_id,
                PORTKEY_CONNECTOR_ID,
                {"verified": False, "last_verify_ok": False},
            )
            return {
                "ok": True,
                "connection_state": "verify_failed",
                "message": "Key verified briefly, but the test message failed.",
                "verification": verify,
                "test": test,
                "next_action": _next_action_for_verify_failure(
                    {"http_status": test.get("http_status"), "detail": test.get("detail"), "message": test.get("message")}
                ),
                "provider_slug": slug,
                "resolved_model": verify.get("model", ""),
                "safety_boundary": _plane_b_safety(),
            }

    return {
        "ok": True,
        "connection_state": "verified",
        "message": "Connected and tested through your Portkey gateway.",
        "verification": verify,
        "test_reply": test_reply,
        "provider_slug": slug,
        "model_suffix": model_suffix,
        "resolved_model": verify.get("model", resolved),
        "safety_boundary": _plane_b_safety(),
    }


def reconnect_portkey(
    session_id: str,
    *,
    provider: str = "",
    model: str = "",
    run_test: bool = True,
) -> dict[str, Any]:
    """Re-test using the session-saved Portkey key (no re-paste required)."""
    conn = _raw_connection(session_id, PORTKEY_CONNECTOR_ID)
    key = str(conn.get("api_key", "")).strip()
    if conn.get("status") != "connected" or not key:
        return {
            "ok": False,
            "message": "No saved key. Paste your Portkey API key first.",
            "needs_sign_in": True,
        }
    slug, model_suffix = _normalize_provider_model(
        provider.strip() or str(conn.get("provider_slug", "")).strip(),
        model.strip() or str(conn.get("model_suffix", "")).strip() or DEFAULT_VERIFY_MODEL,
    )
    return connect_portkey(
        session_id,
        key,
        provider=slug,
        model=model_suffix,
        run_test=run_test,
    )


def disconnect_portkey(session_id: str) -> dict[str, Any]:
    result = disconnect(session_id, PORTKEY_CONNECTOR_ID)
    result["safety_boundary"] = _plane_b_safety()
    return result


def portkey_plane_b_status(session_id: str) -> dict[str, Any]:
    entry = _raw_connection(session_id, PORTKEY_CONNECTOR_ID)
    connected = entry.get("status") == "connected" and bool(entry.get("api_key"))
    state = _connection_state(entry)
    slug = str(entry.get("provider_slug", "")).strip()
    model_suffix = str(entry.get("model_suffix", "")).strip() or DEFAULT_VERIFY_MODEL
    public = public_connection(entry) if entry else {"status": "disconnected"}
    if slug and public:
        public = {
            **public,
            "provider_slug": slug,
            "model_suffix": model_suffix,
            "resolved_model": entry.get("resolved_model", ""),
        }
    return {
        "ok": True,
        "schema_version": PORTKEY_PLANE_B_SCHEMA_VERSION,
        "connected": connected,
        "connection_state": state,
        "verified": state == "verified",
        "connector_id": PORTKEY_CONNECTOR_ID,
        "session_connection": public,
        "provider_slug": slug,
        "model_suffix": model_suffix,
        "resolved_model": entry.get("resolved_model") or (_resolve_portkey_model(model_suffix, slug)[0] if slug else ""),
        "default_model_suffix": DEFAULT_VERIFY_MODEL,
        "has_saved_key": connected,
        "wizard": _wizard_steps(),
        "portkey_links": {
            "model_catalog": PORTKEY_APP_MODEL_CATALOG_URL,
            "api_keys": PORTKEY_APP_API_KEYS_URL,
        },
        "safety_boundary": _plane_b_safety(),
    }


def _consumer_path_steps() -> list[dict[str, str]]:
    return _wizard_steps()


def _multi_tenant_note() -> dict[str, str]:
    return {
        "status": "architecture_required",
        "summary": "Multi-tenant hosting needs per-customer isolation — not in this demo.",
    }


def _portkey_headers(api_key: str, *, provider: str = "", metadata: Mapping[str, Any] | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": PORTKEY_HTTP_USER_AGENT,
        "x-portkey-api-key": api_key,
    }
    if provider.strip():
        headers["x-portkey-provider"] = provider.strip()
    if metadata:
        headers["x-portkey-metadata"] = json.dumps(_sanitize_metadata(metadata))
    return headers


def _sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in metadata.items() if value is not None and str(value).strip()}


def _normalize_provider_model(provider: str, model: str) -> tuple[str, str]:
    """Accept slug + model, or a pasted Portkey route like @iaagent1/babbage-002."""
    provider = provider.strip().lstrip("@")
    model = model.strip()
    if model.startswith("@"):
        route = model.lstrip("@")
        if "/" in route:
            route_slug, route_model = route.split("/", 1)
            if not provider:
                provider = route_slug.strip()
            model = route_model.lstrip("/")
        else:
            model = route
    return provider, model


def _resolve_portkey_model(model: str, provider: str) -> tuple[str, str]:
    provider, model = _normalize_provider_model(provider, model)
    if provider:
        return f"@{provider}/{model.lstrip('/')}", provider
    return model, ""


def _wants_completions_endpoint(detail: str) -> bool:
    lowered = detail.lower()
    return "not a chat model" in lowered or "v1/completions" in lowered


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for msg in messages:
        content = str(msg.get("content", "")).strip()
        if content:
            parts.append(content)
    return "\n".join(parts)


def _extract_inference_reply(payload: dict[str, Any], *, surface: str) -> str:
    choice = (payload.get("choices") or [{}])[0]
    if surface == "/completions":
        return str(choice.get("text", ""))
    message = choice.get("message") or {}
    return str(message.get("content", ""))


def _portkey_infer(
    api_key: str,
    *,
    resolved_model: str,
    provider_header: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 8,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """Try chat/completions first; fall back to /completions for legacy models."""
    chat_body = {
        "model": resolved_model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    try:
        payload = _portkey_request(
            "POST",
            "/chat/completions",
            api_key=api_key,
            body=chat_body,
            provider=provider_header,
            metadata=metadata,
        )
        return payload, "/chat/completions"
    except urllib.error.HTTPError as exc:
        detail = _read_http_error(exc)
        if not _wants_completions_endpoint(detail):
            raise
        completion_body = {
            "model": resolved_model,
            "prompt": _messages_to_prompt(messages),
            "max_tokens": max_tokens,
        }
        payload = _portkey_request(
            "POST",
            "/completions",
            api_key=api_key,
            body=completion_body,
            provider=provider_header,
            metadata=metadata,
        )
        return payload, "/completions"


def verify_portkey_api_key(
    api_key: str,
    *,
    model: str = DEFAULT_VERIFY_MODEL,
    provider: str = "",
) -> dict[str, Any]:
    resolved_model, provider_header = _resolve_portkey_model(model, provider)
    messages = [{"role": "user", "content": DEFAULT_TEST_PROMPT}]
    try:
        payload, surface = _portkey_infer(
            api_key,
            resolved_model=resolved_model,
            provider_header=provider_header,
            messages=messages,
        )
    except urllib.error.HTTPError as exc:
        detail = _read_http_error(exc)
        return {
            "ok": False,
            "message": f"Portkey returned {exc.code}.",
            "http_status": exc.code,
            "detail": detail,
            "model": resolved_model,
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc), "model": resolved_model}
    return {
        "ok": True,
        "message": "Portkey gateway responded.",
        "model": resolved_model,
        "sample_reply": _extract_inference_reply(payload, surface=surface)[:120],
        "provider_trace": payload.get("provider", ""),
        "inference_surface": surface,
    }


def proxy_portkey_chat(
    session_id: str,
    *,
    messages: list[dict[str, Any]],
    model: str = DEFAULT_PROXY_MODEL,
    provider: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    conn = _raw_connection(session_id, PORTKEY_CONNECTOR_ID)
    api_key = str(conn.get("api_key", "")).strip()
    if conn.get("status") != "connected" or not api_key:
        return {
            "ok": False,
            "message": "Save your Portkey API key on this page first.",
            "needs_sign_in": True,
        }
    if not messages:
        return {"ok": False, "message": "messages are required."}

    provider = provider.strip() or str(conn.get("provider_slug", "")).strip()
    if not model or model == DEFAULT_PROXY_MODEL:
        stored_model = str(conn.get("model_suffix", "")).strip()
        if stored_model:
            model = stored_model
    resolved_model, provider_header = _resolve_portkey_model(model, provider)
    bound_metadata = dict(metadata or {})
    conn_meta = conn.get("packet_metadata") if isinstance(conn.get("packet_metadata"), dict) else {}
    if conn_meta:
        bound_metadata = {**conn_meta, **bound_metadata}
    try:
        payload, surface = _portkey_infer(
            api_key,
            resolved_model=resolved_model,
            provider_header=provider_header,
            messages=messages,
            max_tokens=64,
            metadata=bound_metadata or None,
        )
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "message": f"Portkey gateway error ({exc.code}).",
            "http_status": exc.code,
            "detail": _read_http_error(exc),
            "model": resolved_model,
            "safety_boundary": _plane_b_safety(),
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc), "safety_boundary": _plane_b_safety()}

    usage = payload.get("usage") or {}
    return {
        "ok": True,
        "schema_version": PORTKEY_PLANE_B_SCHEMA_VERSION,
        "model": resolved_model,
        "provider": provider or None,
        "reply": _extract_inference_reply(payload, surface=surface),
        "finish_reason": (payload.get("choices") or [{}])[0].get("finish_reason"),
        "usage": usage,
        "gateway": {
            "surface": "inference_api",
            "url": f"{PORTKEY_GATEWAY_URL}{surface}",
            "auth": "user_api_key_byok",
        },
        "safety_boundary": _plane_b_safety(),
    }


def build_plane_b_guardrail_setup(
    session_id: str,
    *,
    public_base_url: str,
    fixture: str = "ai_spend_budget_overrun",
    requested_mode: str = "model_request",
) -> dict[str, Any]:
    status = portkey_plane_b_status(session_id)
    setup = build_portkey_guardrail_setup(public_base_url=public_base_url, fixture=fixture, requested_mode=requested_mode)
    setup["plane_b"] = {
        "schema_version": PORTKEY_PLANE_B_SCHEMA_VERSION,
        "portkey_inference_connected": status["connected"],
        "portkey_inference_verified": status.get("verified"),
        "inference_auth": "user_api_key_byok",
        "proxy_surface": f"{PORTKEY_GATEWAY_URL}/chat/completions",
    }
    setup["wizard"] = _wizard_steps()
    setup["safety"] = {**setup.get("safety", {}), **_plane_b_safety()}
    return setup


def render_plane_b_guardrail_setup_markdown(payload: dict[str, Any]) -> str:
    base = render_portkey_guardrail_setup_markdown(payload)
    plane_b = payload.get("plane_b", {})
    extra = [
        "",
        "## Plane B",
        "",
        f"- Inference connected: `{plane_b.get('portkey_inference_connected')}`",
        f"- Inference verified: `{plane_b.get('portkey_inference_verified')}`",
        "",
    ]
    return base + "\n".join(extra)


def _portkey_request(
    method: str,
    path: str,
    *,
    api_key: str,
    body: dict[str, Any] | None = None,
    provider: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{PORTKEY_GATEWAY_URL}{path}"
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers=_portkey_headers(api_key, provider=provider, metadata=metadata),
        method=method,
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _read_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict):
            return str(parsed.get("error", parsed.get("message", raw)))[:500]
        return raw[:500]
    except Exception:
        return str(exc)
