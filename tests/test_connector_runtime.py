"""Connector runtime — session and demo import."""

import unittest
from unittest.mock import patch

from agent.connector_oauth import begin_sign_in, demo_sign_in, save_user_api_key
from agent.connector_runtime import import_connector_content, load_session, save_session


class ConnectorRuntimeTests(unittest.TestCase):
    def test_session_roundtrip(self) -> None:
        sid = "test-session-connector-1"
        save_session(sid, {"connections": {"tavily": {"status": "connected"}}})
        data = load_session(sid)
        self.assertEqual(data["connections"]["tavily"]["status"], "connected")

    def test_begin_sign_in_popup(self) -> None:
        out = begin_sign_in("sess-popup", "tavily")
        self.assertTrue(out.get("ok"))
        self.assertIn("oauth_redirect", out.get("mode", ""))
        self.assertIn("/api/connectors/oauth/popup/tavily", out.get("redirect_url", ""))

    def test_user_api_key_session(self) -> None:
        sid = "sess-key-1"
        r = save_user_api_key(sid, "tavily", "tvly-test-key-12345678")
        self.assertTrue(r.get("ok"))
        data = load_session(sid)
        self.assertEqual(data["connections"]["tavily"]["status"], "connected")

    def test_github_callback_uses_raw_oauth_state(self) -> None:
        from agent.connector_oauth import finish_github_callback
        from agent.connector_runtime import _set_connection

        sid = "sess-gh-cb"
        nonce = "test-nonce-abc"
        _set_connection(sid, "github", {"status": "pending", "oauth_state": nonce})
        from agent.connector_oauth import _encode_state

        state = _encode_state(sid, "github", nonce)
        # Without fix, public_connection strips oauth_state → mismatch
        with patch("agent.connector_oauth.GITHUB_CLIENT_SECRET", ""):
            result = finish_github_callback("fake-code", state)
        self.assertIn("ok", result)

    def test_github_live_oauth_overwrites_stale_demo_mode(self) -> None:
        from agent.connector_oauth import _encode_state, finish_github_callback
        from agent.connector_runtime import _set_connection

        sid = "sess-gh-live-over-demo"
        nonce = "test-nonce-live"
        _set_connection(
            sid,
            "github",
            {
                "status": "pending",
                "mode": "demo_session",
                "oauth_state": nonce,
            },
        )

        with patch("agent.connector_oauth.GITHUB_CLIENT_SECRET", "secret"), patch(
            "agent.connector_oauth._http_form_post",
            return_value={"access_token": "gho_live", "scope": "read:user,repo"},
        ), patch("agent.connector_oauth._github_user_login", return_value="octo"):
            result = finish_github_callback("live-code", _encode_state(sid, "github", nonce))

        self.assertTrue(result["ok"])
        github = load_session(sid)["connections"]["github"]
        self.assertEqual(github["status"], "connected")
        self.assertEqual(github["mode"], "live_oauth")
        self.assertEqual(github["account"], "octo")
        self.assertTrue(github["access_token"])

    def test_demo_import_github(self) -> None:
        demo_sign_in("test-session-import-1", "github")
        sid = "test-session-import-1"
        save_session(sid, {"connections": {"github": {"status": "connected"}}})
        result = import_connector_content(sid, "github", "repos")
        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("files"))


if __name__ == "__main__":
    unittest.main()
