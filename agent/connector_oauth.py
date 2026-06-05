"""Per-user connector sign-in: OAuth popups + session-scoped token cache (no host user secrets)."""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from .connector_runtime import (
    CONNECTOR_META,
    WEB_PUBLIC_URL,
    _now_iso,
    _raw_connection,
    _set_connection,
    get_connection_status,
    load_session,
)
from .scenarios import ROOT_DIR

# Host-only OAuth *app* registration (not end-user tokens). Users sign in via popup.
GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID", os.getenv("GITHUB_CLIENT_ID", "")).strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", os.getenv("GITHUB_CLIENT_SECRET", "")).strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID", "")).strip()
GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_OAUTH_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET", "")
).strip()

SECRET_KEYS = frozenset(
    {"access_token", "refresh_token", "api_key", "token", "oauth_state", "code_verifier"}
)

POPUP_CONNECTORS = frozenset({"nebius", "tavily", "composio", "openclaw"})


def public_connection(entry: dict[str, Any]) -> dict[str, Any]:
    """Strip secrets before sending connection state to the browser."""
    return {k: v for k, v in entry.items() if k not in SECRET_KEYS}


def _encode_state(session_id: str, connector_id: str, nonce: str) -> str:
    raw = json.dumps({"s": session_id, "c": connector_id, "n": nonce})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_state(state: str) -> Optional[Tuple[str, str, str]]:
    try:
        pad = "=" * (-len(state) % 4)
        raw = base64.urlsafe_b64decode(state + pad).decode()
        data = json.loads(raw)
        return data["s"], data["c"], data["n"]
    except Exception:
        return None


def _http_form_post(url: str, data: dict) -> Any:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _http_json(
    method: str,
    url: str,
    data: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> Any:
    hdrs = {"Accept": "application/json", "Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    body = None
    if data is not None:
        if hdrs.get("Content-Type") == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
            hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:600]}") from exc


def popup_sign_in_url(session_id: str, connector_id: str) -> str:
    return (
        f"{WEB_PUBLIC_URL}/api/connectors/oauth/popup/{connector_id}"
        f"?session_id={urllib.parse.quote(session_id)}"
    )


def begin_sign_in(session_id: str, connector_id: str) -> dict[str, Any]:
    """Start user sign-in; always returns a popup URL (OAuth provider or hosted form)."""
    if connector_id not in CONNECTOR_META:
        raise ValueError(f"unknown connector: {connector_id}")

    if connector_id in POPUP_CONNECTORS:
        _set_connection(session_id, connector_id, {"status": "pending", "started_at": _now_iso()})
        return {
            "ok": True,
            "mode": "oauth_redirect",
            "redirect_url": popup_sign_in_url(session_id, connector_id),
            "message": f"Sign in to {connector_id} in the popup window.",
        }

    if connector_id == "github":
        return _begin_github_oauth(session_id)
    if connector_id == "google_drive":
        return _begin_google_oauth(session_id)

    raise ValueError(f"unsupported connector: {connector_id}")


def _begin_github_oauth(session_id: str) -> dict[str, Any]:
    if not GITHUB_CLIENT_ID:
        _set_connection(session_id, "github", {"status": "pending"})
        return {
            "ok": True,
            "mode": "oauth_redirect",
            "redirect_url": popup_sign_in_url(session_id, "github"),
            "message": "GitHub OAuth app not configured on host — use demo sign-in or set GITHUB_OAUTH_CLIENT_ID.",
        }
    nonce = secrets.token_urlsafe(16)
    state = _encode_state(session_id, "github", nonce)
    _set_connection(
        session_id,
        "github",
        {"status": "pending", "oauth_state": nonce, "started_at": _now_iso()},
    )
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": f"{WEB_PUBLIC_URL}/api/connectors/oauth/callback/github",
        "scope": "read:user repo",
        "state": state,
        "allow_signup": "true",
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return {
        "ok": True,
        "mode": "oauth_redirect",
        "redirect_url": url,
        "message": "Sign in with GitHub in the popup (like installing a GitHub App).",
    }


def _begin_google_oauth(session_id: str) -> dict[str, Any]:
    if not GOOGLE_CLIENT_ID:
        _set_connection(session_id, "google_drive", {"status": "pending"})
        return {
            "ok": True,
            "mode": "oauth_redirect",
            "redirect_url": popup_sign_in_url(session_id, "google_drive"),
            "message": "Google OAuth not configured on host — use demo sign-in or set GOOGLE_OAUTH_CLIENT_ID.",
        }
    nonce = secrets.token_urlsafe(16)
    state = _encode_state(session_id, "google_drive", nonce)
    _set_connection(
        session_id,
        "google_drive",
        {"status": "pending", "oauth_state": nonce, "started_at": _now_iso()},
    )
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{WEB_PUBLIC_URL}/api/connectors/oauth/callback/google_drive",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {
        "ok": True,
        "mode": "oauth_redirect",
        "redirect_url": url,
        "message": "Sign in with Google in the popup to access Drive.",
    }


def finish_github_callback(code: str, state: str) -> dict[str, Any]:
    decoded = _decode_state(state)
    if not decoded:
        return {"ok": False, "message": "Invalid OAuth state — try Sign in again."}
    session_id, connector_id, nonce = decoded
    conn = _raw_connection(session_id, connector_id)
    stored_nonce = conn.get("oauth_state")
    if stored_nonce and stored_nonce != nonce:
        return {"ok": False, "message": "OAuth state mismatch — try Sign in again."}

    if not GITHUB_CLIENT_SECRET:
        _set_connection(
            session_id,
            "github",
            {"status": "connected", "mode": "demo_oauth", "connected_at": _now_iso()},
        )
        return {"ok": True, "session_id": session_id, "connector_id": connector_id}

    redirect_uri = f"{WEB_PUBLIC_URL}/api/connectors/oauth/callback/github"
    try:
        token_payload = _http_form_post(
            "https://github.com/login/oauth/access_token",
            {
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
    except RuntimeError as exc:
        return {"ok": False, "message": str(exc)}
    access = token_payload.get("access_token")
    if not access:
        err = token_payload.get("error_description") or token_payload.get("error", "No access token")
        return {
            "ok": False,
            "message": f"{err}. Check GitHub OAuth app callback URL is {redirect_uri}",
        }
    _set_connection(
        session_id,
        "github",
        {
            "status": "connected",
            "access_token": access,
            "scope": token_payload.get("scope", ""),
            "connected_at": _now_iso(),
            "account": _github_user_login(access),
        },
    )
    return {"ok": True, "session_id": session_id, "connector_id": connector_id}


def finish_google_callback(code: str, state: str) -> dict[str, Any]:
    decoded = _decode_state(state)
    if not decoded:
        return {"ok": False, "message": "Invalid OAuth state — try Sign in again."}
    session_id, connector_id, nonce = decoded
    conn = _raw_connection(session_id, connector_id)
    stored_nonce = conn.get("oauth_state")
    if stored_nonce and stored_nonce != nonce:
        return {"ok": False, "message": "OAuth state mismatch — try Sign in again."}

    if not GOOGLE_CLIENT_SECRET:
        _set_connection(
            session_id,
            "google_drive",
            {"status": "connected", "mode": "demo_oauth", "connected_at": _now_iso()},
        )
        return {"ok": True, "session_id": session_id, "connector_id": connector_id}

    token_payload = _http_form_post(
        "https://oauth2.googleapis.com/token",
        {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{WEB_PUBLIC_URL}/api/connectors/oauth/callback/google_drive",
            "grant_type": "authorization_code",
        },
    )
    access = token_payload.get("access_token")
    if not access:
        return {"ok": False, "message": token_payload.get("error", "No access token")}
    expires_in = int(token_payload.get("expires_in", 3600))
    _set_connection(
        session_id,
        "google_drive",
        {
            "status": "connected",
            "access_token": access,
            "refresh_token": token_payload.get("refresh_token", ""),
            "token_expires_at": time.time() + max(expires_in - 60, 300),
            "connected_at": _now_iso(),
        },
    )
    return {"ok": True, "session_id": session_id, "connector_id": connector_id}


def _google_token_expired(conn: dict[str, Any]) -> bool:
    exp = conn.get("token_expires_at")
    if exp is None:
        return False
    try:
        return time.time() >= float(exp)
    except (TypeError, ValueError):
        return False


def refresh_google_access_token(session_id: str) -> bool:
    """Exchange refresh_token for a new access_token; updates session file."""
    conn = _raw_connection(session_id, "google_drive")
    refresh = (conn.get("refresh_token") or "").strip()
    if not refresh or not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return False
    try:
        token_payload = _http_form_post(
            "https://oauth2.googleapis.com/token",
            {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
    except Exception:
        return False
    access = token_payload.get("access_token")
    if not access:
        return False
    expires_in = int(token_payload.get("expires_in", 3600))
    patch: dict[str, Any] = {
        "access_token": access,
        "token_expires_at": time.time() + max(expires_in - 60, 300),
    }
    if token_payload.get("refresh_token"):
        patch["refresh_token"] = token_payload["refresh_token"]
    _set_connection(session_id, "google_drive", patch)
    return True


def get_google_access_token(session_id: str, *, force_refresh: bool = False) -> str:
    """Return a valid Drive access token, refreshing when expired."""
    conn = _raw_connection(session_id, "google_drive")
    token = (conn.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Sign in to Google Drive first.")
    if force_refresh or _google_token_expired(conn):
        if refresh_google_access_token(session_id):
            return (_raw_connection(session_id, "google_drive").get("access_token") or "").strip()
        if force_refresh or _google_token_expired(conn):
            raise RuntimeError(
                "Google Drive session expired. In Connectors: Disconnect Google Drive, "
                "then Sign in again (use the Google account that is a Test user on your OAuth app)."
            )
    return token


def save_user_api_key(session_id: str, connector_id: str, api_key: str) -> dict[str, Any]:
    key = api_key.strip()
    if len(key) < 8:
        return {"ok": False, "message": "API key too short"}
    _set_connection(
        session_id,
        connector_id,
        {
            "status": "connected",
            "api_key": key,
            "mode": "user_key",
            "connected_at": _now_iso(),
        },
    )
    return {"ok": True, "message": f"{connector_id} connected for this browser session only."}


def demo_sign_in(session_id: str, connector_id: str) -> dict[str, Any]:
    """Demo OAuth when host has not registered an OAuth app — still session-scoped."""
    _set_connection(
        session_id,
        connector_id,
        {"status": "connected", "mode": "demo_session", "connected_at": _now_iso()},
    )
    return {"ok": True, "message": "Demo sign-in (session only). Configure OAuth app on host for live APIs."}


def disconnect(session_id: str, connector_id: str) -> dict[str, Any]:
    from .connector_runtime import load_session, save_session

    data = load_session(session_id)
    conns = data.get("connections", {})
    if connector_id in conns:
        del conns[connector_id]
        save_session(session_id, data)
    return {"ok": True, "connector_id": connector_id, "status": "disconnected"}


def _github_user_login(token: str) -> str:
    try:
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "InferenceAtlas-Agent-Demo",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("login", "github-user")
    except Exception:
        return "github-user"


def github_fetch_repos(session_id: str, *, per_page: int = 10) -> str:
    conn = _raw_connection(session_id, "github")
    token = conn.get("access_token")
    if not token:
        return ""
    url = f"https://api.github.com/user/repos?per_page={per_page}&sort=updated"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "InferenceAtlas-Agent-Demo",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def google_drive_list_files(session_id: str, *, page_size: int = 10) -> str:
    try:
        token = get_google_access_token(session_id)
    except RuntimeError:
        return ""
    q = urllib.parse.urlencode(
        {
            "pageSize": page_size,
            "fields": "files(id,name,mimeType,modifiedTime,size)",
            "orderBy": "modifiedTime desc",
        }
    )
    url = f"https://www.googleapis.com/drive/v3/files?{q}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def render_popup_html(connector_id: str, session_id: str, *, error: str = "") -> str:
    titles = {
        "github": "Sign in with GitHub",
        "google_drive": "Sign in with Google Drive",
        "nebius": "Connect your Nebius API key",
        "tavily": "Connect your Tavily API key",
        "composio": "Connect your Composio API key",
        "openclaw": "Enable OpenClaw runtime",
    }
    title = titles.get(connector_id, f"Connect {connector_id}")
    err = f'<p style="color:#f87171">{error}</p>' if error else ""

    if connector_id in ("nebius", "tavily", "composio"):
        hint = {
            "nebius": "Paste your Nebius Studio API key. Stored only in this chat session on this server.",
            "tavily": "Paste your Tavily API key from tavily.com. Session-only — never written to .env.",
            "composio": "Paste your Composio project API key. Session-only.",
        }[connector_id]
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title></head>
        <body style="font-family:system-ui;background:#0b0e14;color:#e2e8f0;padding:1.5rem;max-width:420px">
        <h2 style="margin:0 0 0.5rem;font-size:1.1rem">{title}</h2>
        <p style="font-size:0.85rem;color:#94a3b8">{hint}</p>{err}
        <form method="post" action="/api/connectors/oauth/popup/{connector_id}?session_id={urllib.parse.quote(session_id)}">
        <input type="password" name="api_key" required placeholder="API key" style="width:100%;padding:0.5rem;margin:0.5rem 0;border-radius:6px;border:1px solid #334155;background:#1e293b;color:#fff"/>
        <button type="submit" style="width:100%;padding:0.55rem;background:#3d9cf5;color:#fff;border:none;border-radius:6px;font-weight:600;cursor:pointer">Connect</button>
        </form></body></html>"""

    if connector_id == "openclaw":
        return f"""<!DOCTYPE html><html><body style="font-family:system-ui;background:#0b0e14;color:#e2e8f0;padding:1.5rem">
        <h2>{title}</h2><p>Confirm use of OpenClaw runtime for this session (or built-in fallback).</p>
        <form method="post" action="/api/connectors/oauth/popup/openclaw?session_id={urllib.parse.quote(session_id)}">
        <button type="submit" name="confirm" value="1" style="padding:0.55rem 1rem;background:#3d9cf5;color:#fff;border:none;border-radius:6px">Enable for this session</button>
        </form></body></html>"""

    # github / google_drive without host OAuth app
    setup = ""
    if connector_id == "github" and not GITHUB_CLIENT_ID:
        setup = "<p>Host: set <code>GITHUB_OAUTH_CLIENT_ID</code> for real GitHub OAuth.</p>"
    if connector_id == "google_drive" and GOOGLE_CLIENT_ID:
        setup = """<p style="font-size:0.8rem;color:#94a3b8">Google app in <strong>Testing</strong>?
        Add your Gmail under OAuth consent → <strong>Test users</strong> in
        <a href="https://console.cloud.google.com/apis/credentials/consent" style="color:#3d9cf5">Cloud Console</a>.</p>"""
    if connector_id == "google_drive" and not GOOGLE_CLIENT_ID:
        setup = "<p>Host: set <code>GOOGLE_OAUTH_CLIENT_ID</code> for real Google OAuth.</p>"
    return f"""<!DOCTYPE html><html><body style="font-family:system-ui;background:#0b0e14;color:#e2e8f0;padding:1.5rem">
    <h2>{title}</h2>{setup}{err}
    <p>Use demo sign-in to try import with fixture files (session cached).</p>
    <form method="post" action="/api/connectors/oauth/popup/{connector_id}?session_id={urllib.parse.quote(session_id)}">
    <button type="submit" name="demo" value="1" style="padding:0.55rem 1rem;background:#3d9cf5;color:#fff;border:none;border-radius:6px">Demo sign-in (this session)</button>
    </form></body></html>"""


def google_access_denied_html() -> str:
    return """<!DOCTYPE html><html><body style="font-family:system-ui;background:#0b0e14;color:#e2e8f0;padding:1.5rem;max-width:480px">
    <h2 style="margin:0 0 0.75rem">Google Drive — access blocked</h2>
    <p style="font-size:0.9rem;line-height:1.45;color:#94a3b8">
      Your Google Cloud OAuth app is in <strong>Testing</strong> mode. Only emails listed as
      <strong>Test users</strong> can sign in (Error 403: access_denied).
    </p>
    <ol style="font-size:0.85rem;line-height:1.5;color:#cbd5e1">
      <li>Open <a href="https://console.cloud.google.com/apis/credentials/consent" style="color:#3d9cf5">Google Cloud → OAuth consent screen</a></li>
      <li>Under <strong>Test users</strong>, click <strong>Add users</strong></li>
      <li>Add your Gmail (e.g. the account you just used)</li>
      <li>Retry Sign in on Google Drive in InferenceAtlas</li>
    </ol>
    <p style="font-size:0.8rem;color:#64748b">Or use <strong>Demo sign-in</strong> from the popup for fixture files without Google.</p>
    <script>
      if (window.opener) {
        window.opener.postMessage({type:"connector-oauth",connector_id:"google_drive",ok:false,
          message:"Add your Gmail as a Test user in Google Cloud Console"}, "*");
      }
      setTimeout(() => window.close(), 12000);
    </script></body></html>"""


def oauth_close_html(connector_id: str, ok: bool, message: str = "") -> str:
    cid = connector_id.replace("'", "")
    msg = (message or ("Connected!" if ok else "Sign-in failed.")).replace("<", "").replace(">", "")
    return f"""<!DOCTYPE html><html><body style="font-family:system-ui;background:#0b0e14;color:#e2e8f0;padding:2rem;max-width:420px">
    <p style="font-weight:600">{"Connected" if ok else "Sign-in failed"} — {cid}</p>
    <p style="font-size:0.85rem;color:#94a3b8">{msg}</p>
    <script>
      if (window.opener) {{
        window.opener.postMessage({{type:"connector-oauth",connector_id:"{cid}",ok:{str(ok).lower()},
          message:{json.dumps(msg)}}}, "*");
      }}
      setTimeout(() => window.close(), {8000 if not ok else 600});
    </script></body></html>"""
