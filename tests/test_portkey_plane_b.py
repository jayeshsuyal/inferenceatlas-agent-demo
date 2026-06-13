"""Tests for Portkey Plane B — optional BYOK gateway shell."""

from __future__ import annotations

import io
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent.connector_runtime import load_session
from agent.portkey_plane_b import (
    build_plane_b_guardrail_setup,
    connect_portkey,
    disconnect_portkey,
    portkey_plane_b_status,
    proxy_portkey_chat,
    reconnect_portkey,
    verify_portkey_api_key,
)


class PortkeyPlaneBTests(unittest.TestCase):
    def test_status_includes_wizard_and_links(self) -> None:
        status = portkey_plane_b_status("plane-b-test-session-01")
        self.assertTrue(status["ok"])
        self.assertFalse(status["connected"])
        self.assertEqual(len(status["wizard"]), 3)
        self.assertIn("model_catalog", status["portkey_links"])
        self.assertTrue(status["safety_boundary"]["governance_shell_unchanged"])

    @patch("agent.portkey_plane_b.proxy_portkey_chat")
    @patch("agent.portkey_plane_b.verify_portkey_api_key", return_value={"ok": True, "model": "@openai-prod/gpt-4o-mini"})
    def test_connect_verifies_and_tests(self, _verify: object, proxy: object) -> None:
        proxy.return_value = {"ok": True, "reply": "connected"}
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                result = connect_portkey(
                    "plane-b-test-session-02",
                    "pk-test-key-12345678",
                    provider="openai-prod",
                )
        self.assertTrue(result["ok"])
        self.assertEqual(result["connection_state"], "verified")
        self.assertEqual(result["test_reply"], "connected")

    @patch("agent.portkey_plane_b.verify_portkey_api_key")
    def test_connect_keeps_key_when_verify_fails(self, verify: object) -> None:
        verify.return_value = {"ok": False, "http_status": 403, "detail": "forbidden", "model": "@x/y"}
        session_id = "plane-b-test-session-02b"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                result = connect_portkey(
                    session_id,
                    "pk-test-key-12345678",
                    provider="openai-prod",
                )
                data = load_session(session_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["connection_state"], "verify_failed")
        self.assertIn("portkey", data.get("connections", {}))
        self.assertIn("next_action", result)
        self.assertEqual(result["next_action"]["title"], "Check provider slug and model")

    def test_normalize_provider_model_from_route(self) -> None:
        from agent.portkey_plane_b import _normalize_provider_model, _resolve_portkey_model

        slug, model = _normalize_provider_model("openai-prod", "@iaagent1/babbage-002")
        self.assertEqual(slug, "openai-prod")
        self.assertEqual(model, "babbage-002")
        resolved, header = _resolve_portkey_model("@iaagent1/babbage-002", "")
        self.assertEqual(resolved, "@iaagent1/babbage-002")
        self.assertEqual(header, "iaagent1")

    @patch("agent.portkey_plane_b._portkey_request")
    def test_portkey_request_sends_user_agent(self, request: object) -> None:
        from agent.portkey_plane_b import PORTKEY_HTTP_USER_AGENT, _portkey_headers

        headers = _portkey_headers("pk-test-key", provider="iaagent1")
        self.assertEqual(headers["User-Agent"], PORTKEY_HTTP_USER_AGENT)
        self.assertEqual(headers["x-portkey-provider"], "iaagent1")

    def test_connect_without_provider_saves_key(self) -> None:
        session_id = "plane-b-test-session-02c"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                result = connect_portkey(session_id, "pk-test-key-12345678")
                data = load_session(session_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["connection_state"], "needs_provider")
        self.assertIn("portkey", data.get("connections", {}))

    def test_reconnect_uses_saved_key(self) -> None:
        session_id = "plane-b-test-session-02d"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                with patch(
                    "agent.portkey_plane_b.verify_portkey_api_key",
                    return_value={"ok": True, "model": "@iaagent1/babbage-002"},
                ):
                    connect_portkey(
                        session_id,
                        "pk-test-key-12345678",
                        provider="iaagent1",
                        model="babbage-002",
                        run_test=False,
                    )
                    with patch(
                        "agent.portkey_plane_b.proxy_portkey_chat",
                        return_value={"ok": True, "reply": "connected"},
                    ):
                        result = reconnect_portkey(session_id, provider="iaagent1", model="babbage-002")
        self.assertTrue(result["ok"])
        self.assertEqual(result["connection_state"], "verified")

    @patch("agent.portkey_plane_b._portkey_request")
    def test_verify_portkey_api_key_success(self, request: object) -> None:
        request.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "provider": "openai",
        }
        result = verify_portkey_api_key("pk-test-key-12345678", provider="openai-prod")
        self.assertTrue(result["ok"])
        self.assertEqual(result["model"], "@openai-prod/gpt-4o-mini")
        self.assertEqual(result["inference_surface"], "/chat/completions")

    @patch("agent.portkey_plane_b._portkey_request")
    def test_verify_falls_back_to_completions(self, request: object) -> None:
        def side_effect(method, path, **kwargs):
            if path == "/chat/completions":
                raise urllib.error.HTTPError(
                    url="x",
                    code=404,
                    msg="not chat",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"not a chat model","type":"invalid_request_error"}'
                    ),
                )
            return {"choices": [{"text": "connected"}], "provider": "openai"}

        request.side_effect = side_effect
        result = verify_portkey_api_key(
            "pk-test-key-12345678",
            provider="iaagent1",
            model="babbage-002",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["inference_surface"], "/completions")

    @patch("agent.portkey_plane_b._portkey_request")
    @patch("agent.portkey_plane_b.verify_portkey_api_key", return_value={"ok": True, "model": "@openai-prod/gpt-4o-mini"})
    def test_proxy_chat_uses_session_key(self, _verify: object, request: object) -> None:
        request.return_value = {
            "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 12},
        }
        session_id = "plane-b-test-session-03"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                connect = connect_portkey(
                    session_id,
                    "pk-test-key-12345678",
                    provider="openai-prod",
                    run_test=False,
                )
                self.assertTrue(connect["ok"])
                proxied = proxy_portkey_chat(
                    session_id,
                    messages=[{"role": "user", "content": "hi"}],
                )
        self.assertTrue(proxied["ok"])
        self.assertEqual(proxied["reply"], "hello")

    def test_proxy_requires_connection(self) -> None:
        result = proxy_portkey_chat(
            "plane-b-test-session-04",
            messages=[{"role": "user", "content": "hi"}],
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["needs_sign_in"])

    def test_guardrail_setup_merges_plane_b_status(self) -> None:
        setup = build_plane_b_guardrail_setup(
            "plane-b-test-session-05",
            public_base_url="https://ia.example.com",
        )
        self.assertIn("plane_b", setup)
        self.assertIn("wizard", setup)
        self.assertTrue(setup["safety"]["governance_shell_unchanged"])

    @patch("agent.portkey_plane_b.verify_portkey_api_key", return_value={"ok": True, "model": "@openai-prod/gpt-4o-mini"})
    def test_disconnect_clears_session(self, _verify: object) -> None:
        session_id = "plane-b-test-session-06"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                connect_portkey(session_id, "pk-test-key-12345678", provider="openai-prod", run_test=False)
                disconnect_portkey(session_id)
                data = load_session(session_id)
        self.assertNotIn("portkey", data.get("connections", {}))


class PortkeyPlaneBApiTests(unittest.TestCase):
    def test_plane_b_routes_registered(self) -> None:
        from web.app import app

        paths = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/portkey/signin", paths)
        self.assertIn("/api/portkey/plane-b/status", paths)
        self.assertIn("/api/portkey/plane-b/connect", paths)
        self.assertIn("/api/portkey/plane-b/chat", paths)
        self.assertIn("/api/portkey/plane-b/reconnect", paths)
