"""Google Drive OAuth token refresh."""

import time
from unittest.mock import patch

from agent.connector_oauth import (
    _google_token_expired,
    get_google_access_token,
    refresh_google_access_token,
)
from agent.connector_runtime import save_session


def _session_with_google(sid: str, **conn_extra) -> None:
    save_session(
        sid,
        {
            "connections": {
                "google_drive": {
                    "status": "connected",
                    "access_token": "old-access",
                    "refresh_token": "refresh-xyz",
                    "token_expires_at": time.time() - 10,
                    **conn_extra,
                }
            }
        },
    )


@patch("agent.connector_oauth.GOOGLE_CLIENT_SECRET", "secret")
@patch("agent.connector_oauth.GOOGLE_CLIENT_ID", "client-id")
@patch("agent.connector_oauth._http_form_post")
def test_refresh_google_access_token(mock_post):
    mock_post.return_value = {"access_token": "new-access", "expires_in": 3600}
    sid = "test-google-refresh"
    _session_with_google(sid)
    assert refresh_google_access_token(sid) is True
    assert get_google_access_token(sid) == "new-access"


def test_google_token_expired():
    assert _google_token_expired({"token_expires_at": time.time() - 1}) is True
    assert _google_token_expired({"token_expires_at": time.time() + 3600}) is False
    assert _google_token_expired({}) is False
