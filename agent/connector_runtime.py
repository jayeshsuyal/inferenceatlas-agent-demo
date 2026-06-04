"""Connector sign-in, import, and export for the InferenceAtlas web UI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    COMPOSIO_API_KEY,
    COMPOSIO_DRY_RUN,
    LLM_API_KEY,
    LLM_PROVIDER,
    NEBIUS_API_KEY,
    OPENAI_API_KEY,
    TAVILY_API_KEY,
)
from .scenarios import ROOT_DIR

COMPOSIO_API_BASE = os.getenv("COMPOSIO_API_BASE", "https://backend.composio.dev/api/v3")
COMPOSIO_LINK_BASE = os.getenv("COMPOSIO_LINK_BASE", "https://backend.composio.dev/api/v3.1")
WEB_PUBLIC_URL = os.getenv("WEB_PUBLIC_URL", "http://127.0.0.1:8080").rstrip("/")

SESSIONS_DIR = ROOT_DIR / "state" / "web_io" / "connector_sessions"

# Optional: set in .env after creating auth configs at https://platform.composio.dev
AUTH_CONFIG_ENV = {
    "github": "COMPOSIO_AUTH_CONFIG_GITHUB",
    "google_drive": "COMPOSIO_AUTH_CONFIG_GOOGLEDRIVE",
}

TOOLKIT_SLUG = {
    "github": "github",
    "google_drive": "googledrive",
}

READ_ACTIONS = {
    "github": "GITHUB_LIST_REPOSITORIES_FOR_AUTHENTICATED_USER",
    "google_drive": "GOOGLEDRIVE_LIST_FILES",
}


@dataclass(frozen=True)
class ConnectorMeta:
    id: str
    auth_type: str  # oauth | api_key_server | runtime
    composio_toolkit: Optional[str] = None


CONNECTOR_META: Dict[str, ConnectorMeta] = {
    "github": ConnectorMeta("github", "oauth_popup", "github"),
    "google_drive": ConnectorMeta("google_drive", "oauth_popup", "googledrive"),
    "nebius": ConnectorMeta("nebius", "oauth_popup"),
    "tavily": ConnectorMeta("tavily", "oauth_popup"),
    "composio": ConnectorMeta("composio", "oauth_popup"),
    "openclaw": ConnectorMeta("openclaw", "oauth_popup"),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:80]
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR / f"{safe}.json"


def load_session(session_id: str) -> Dict[str, Any]:
    path = _session_path(session_id)
    if not path.is_file():
        return {"session_id": session_id, "connections": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"session_id": session_id, "connections": {}}


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    data["session_id"] = session_id
    data["updated_at"] = _now_iso()
    _session_path(session_id).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _set_connection(session_id: str, connector_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    data = load_session(session_id)
    conns = data.setdefault("connections", {})
    entry = {**conns.get(connector_id, {}), **patch, "connector_id": connector_id}
    conns[connector_id] = entry
    save_session(session_id, data)
    return entry


def _composio_request(
    method: str,
    url: str,
    body: Optional[dict] = None,
    *,
    timeout: int = 30,
) -> dict[str, Any]:
    if not COMPOSIO_API_KEY:
        raise RuntimeError("COMPOSIO_API_KEY is not set in .env")
    headers = {"x-api-key": COMPOSIO_API_KEY, "Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Composio HTTP {exc.code}: {detail[:500]}") from exc


def _discover_auth_config_id(toolkit_slug: str) -> Optional[str]:
    slug = toolkit_slug.replace("-", "").lower()
    if slug in ("github",):
        env_key = AUTH_CONFIG_ENV["github"]
    elif slug in ("googledrive", "google_drive", "google drive"):
        env_key = AUTH_CONFIG_ENV["google_drive"]
    else:
        env_key = None
    if env_key:
        explicit = os.getenv(env_key, "").strip()
        if explicit:
            return explicit
    q = urllib.parse.urlencode({"toolkit_slug": toolkit_slug, "limit": 5})
    try:
        payload = _composio_request("GET", f"{COMPOSIO_API_BASE}/auth_configs?{q}")
    except Exception:
        return None
    items = payload.get("items") or payload.get("data") or []
    if isinstance(items, list) and items:
        first = items[0]
        return first.get("id") or first.get("nanoid")
    return None


def start_oauth_connect(session_id: str, connector_id: str) -> dict[str, Any]:
    meta = CONNECTOR_META.get(connector_id)
    if not meta or meta.auth_type != "oauth":
        raise ValueError(f"connector {connector_id} does not use OAuth")
    toolkit = meta.composio_toolkit or connector_id
    slug = TOOLKIT_SLUG.get(connector_id, toolkit)
    auth_config_id = _discover_auth_config_id(slug)
    if not auth_config_id:
        env_hint = AUTH_CONFIG_ENV.get(connector_id, "COMPOSIO_AUTH_CONFIG_*")
        return {
            "ok": False,
            "mode": "setup_required",
            "message": (
                f"Create a Composio auth config for toolkit '{slug}' at https://platform.composio.dev, "
                f"then set {env_hint} in .env and restart the server."
            ),
        }
    callback = f"{WEB_PUBLIC_URL}/api/connectors/oauth/callback?session_id={urllib.parse.quote(session_id)}&connector_id={connector_id}"
    body = {
        "auth_config_id": auth_config_id,
        "user_id": session_id,
        "callback_url": callback,
    }
    try:
        link = _composio_request("POST", f"{COMPOSIO_LINK_BASE}/connected_accounts/link", body)
    except Exception as exc:
        return {"ok": False, "mode": "error", "message": str(exc)}
    redirect = link.get("redirect_url") or link.get("redirectUrl")
    if not redirect:
        return {"ok": False, "mode": "error", "message": "Composio did not return a redirect URL"}
    _set_connection(
        session_id,
        connector_id,
        {
            "status": "pending",
            "auth_config_id": auth_config_id,
            "started_at": _now_iso(),
        },
    )
    return {
        "ok": True,
        "mode": "oauth_redirect",
        "redirect_url": redirect,
        "message": f"Complete sign-in for {connector_id} in the popup window.",
    }


def complete_oauth_callback(session_id: str, connector_id: str, **query: str) -> dict[str, Any]:
    """Mark OAuth complete after Composio redirects back (or poll finds account)."""
    connected = _poll_composio_connected(session_id, connector_id)
    if connected:
        _set_connection(session_id, connector_id, connected)
        return {"ok": True, "status": "connected", "connector_id": connector_id}
    status = query.get("status") or query.get("connection_status")
    if status in ("success", "active", "connected"):
        _set_connection(
            session_id,
            connector_id,
            {"status": "connected", "connected_at": _now_iso(), "via": "callback"},
        )
        return {"ok": True, "status": "connected"}
    _set_connection(session_id, connector_id, {"status": "connected", "connected_at": _now_iso()})
    return {"ok": True, "status": "connected", "note": "Marked connected; verify import works."}


def _poll_composio_connected(session_id: str, connector_id: str) -> Optional[dict[str, Any]]:
    meta = CONNECTOR_META.get(connector_id)
    if not meta or not meta.composio_toolkit:
        return None
    slug = TOOLKIT_SLUG.get(connector_id, meta.composio_toolkit)
    q = urllib.parse.urlencode({"user_ids": session_id, "toolkit_slugs": slug, "limit": 10})
    try:
        payload = _composio_request("GET", f"{COMPOSIO_API_BASE}/connected_accounts?{q}")
    except Exception:
        return None
    items = payload.get("items") or payload.get("data") or []
    if not isinstance(items, list):
        return None
    for item in items:
        st = (item.get("status") or "").lower()
        if st in ("active", "connected", "success"):
            return {
                "status": "connected",
                "connected_account_id": item.get("id"),
                "connected_at": _now_iso(),
                "toolkit": slug,
            }
    return None


def connect_api_key_server(session_id: str, connector_id: str) -> dict[str, Any]:
    checks = {
        "nebius": bool(NEBIUS_API_KEY and LLM_API_KEY),
        "tavily": bool(TAVILY_API_KEY),
        "composio": bool(COMPOSIO_API_KEY),
    }
    if connector_id == "nebius" and OPENAI_API_KEY and LLM_API_KEY and not NEBIUS_API_KEY:
        _set_connection(
            session_id,
            connector_id,
            {"status": "connected", "mode": "server_key", "provider": LLM_PROVIDER},
        )
        return {
            "ok": True,
            "mode": "server_key",
            "message": f"Using server LLM ({LLM_PROVIDER}). Nebius key optional.",
        }
    if not checks.get(connector_id):
        hints = {
            "nebius": "Add NEBIUS_API_KEY (or OPENAI_API_KEY) to .env and restart python3 -m web",
            "tavily": "Add TAVILY_API_KEY to .env and restart",
            "composio": "Add COMPOSIO_API_KEY to .env and restart",
        }
        return {"ok": False, "mode": "needs_key", "message": hints.get(connector_id, "Missing API key")}
    _set_connection(session_id, connector_id, {"status": "connected", "mode": "server_key"})
    return {"ok": True, "mode": "server_key", "message": f"{connector_id} is ready on the server."}


def connect_openclaw(session_id: str) -> dict[str, Any]:
    try:
        import importlib

        importlib.import_module("openclaw")
        _set_connection(session_id, "openclaw", {"status": "connected", "mode": "runtime"})
        return {"ok": True, "mode": "runtime", "message": "OpenClaw runtime is installed."}
    except Exception:
        _set_connection(session_id, "openclaw", {"status": "connected", "mode": "builtin"})
        return {
            "ok": True,
            "mode": "builtin",
            "message": "Using built-in agent loop (pip install openclaw for OpenClaw).",
        }


def start_connect(session_id: str, connector_id: str) -> dict[str, Any]:
    from .connector_oauth import begin_sign_in

    if connector_id not in CONNECTOR_META:
        raise ValueError(f"unknown connector: {connector_id}")
    return begin_sign_in(session_id, connector_id)


def get_connection_status(session_id: str, connector_id: str) -> dict[str, Any]:
    from .connector_oauth import public_connection

    data = load_session(session_id)
    entry = data.get("connections", {}).get(connector_id, {})
    return public_connection(entry) if entry else {"status": "disconnected", "connector_id": connector_id}


def session_statuses(session_id: str) -> Dict[str, dict[str, Any]]:
    out: Dict[str, dict[str, Any]] = {}
    for cid in CONNECTOR_META:
        out[cid] = get_connection_status(session_id, cid)
    return out


def _demo_import_payload(connector_id: str, action: str) -> List[dict[str, Any]]:
    if connector_id == "github":
        path = ROOT_DIR / "examples" / "requests" / "support_triage_trial.yml"
        text = path.read_text(encoding="utf-8") if path.is_file() else "# demo repo file"
        return [{"name": "support_triage_trial.yml", "content": text, "mime": "text/yaml"}]
    if connector_id == "google_drive":
        brief = ROOT_DIR / "examples" / "generated" / "support_triage_agent.decision_brief.md"
        text = brief.read_text(encoding="utf-8") if brief.is_file() else "# demo drive doc"
        label = {"files": "decision_brief.md", "photos": "architecture.png.txt", "videos": "walkthrough.txt"}
        return [{"name": label.get(action, "evidence.md"), "content": text, "mime": "text/markdown"}]
    return [{"name": "connector_sample.txt", "content": "Demo connector import.", "mime": "text/plain"}]


def _composio_execute(action: str, params: dict) -> Any:
    if not COMPOSIO_API_KEY:
        raise RuntimeError("COMPOSIO_API_KEY not set")
    if COMPOSIO_DRY_RUN:
        return {"dry_run": True, "action": action, "params": params}
    body = {"action": action, "params": params, "entity_id": params.pop("entity_id", None)}
    # Try tool execute endpoint (v3)
    try:
        return _composio_request("POST", f"{COMPOSIO_API_BASE}/tools/execute", body)
    except Exception:
        pass
    try:
        from composio_openai import ComposioToolSet

        toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)
        return toolset.execute_action(action=action, params=params)
    except Exception as exc:
        raise RuntimeError(f"Composio execute failed: {exc}") from exc


def _raw_connection(session_id: str, connector_id: str) -> dict[str, Any]:
    data = load_session(session_id)
    return data.get("connections", {}).get(connector_id, {})


def import_connector_content(
    session_id: str,
    connector_id: str,
    action: str,
    *,
    query: str = "",
) -> dict[str, Any]:
    """Pull text content using the user's session-scoped sign-in only."""
    from .connector_oauth import github_fetch_repos, google_drive_list_files

    conn = _raw_connection(session_id, connector_id)
    if conn.get("status") != "connected":
        connect_hint = start_connect(session_id, connector_id)
        if connect_hint.get("mode") == "oauth_redirect":
            return {
                "ok": False,
                "needs_sign_in": True,
                "redirect_url": connect_hint.get("redirect_url"),
                "message": "Sign in via popup before import.",
            }
        return {"ok": False, "message": connect_hint.get("message", "Sign in first.")}

    files: List[dict[str, Any]] = []
    demo_mode = conn.get("mode") in ("demo_session", "demo_oauth")

    if connector_id == "github":
        if conn.get("access_token") and not demo_mode:
            text = github_fetch_repos(session_id)[:12000]
            files = [{"name": "github_repos.json", "content": text, "mime": "application/json"}]
        else:
            files = _demo_import_payload(connector_id, action)
            demo_mode = True
    elif connector_id == "google_drive":
        if conn.get("access_token") and not demo_mode:
            text = google_drive_list_files(session_id)[:12000]
            name = {"files": "drive_files.json", "photos": "drive_images.json", "videos": "drive_videos.json"}
            files = [{"name": name.get(action, "drive_listing.json"), "content": text, "mime": "application/json"}]
        else:
            files = _demo_import_payload(connector_id, action)
            demo_mode = True
    elif connector_id in ("nebius", "tavily", "composio"):
        key = conn.get("api_key", "")
        files = [
            {
                "name": f"{connector_id}_connected.txt",
                "content": f"{connector_id} signed in for this session (key length {len(key)}).\n",
                "mime": "text/plain",
            }
        ]
    else:
        return {"ok": False, "message": f"Import not implemented for {connector_id}/{action}"}

    return {
        "ok": True,
        "files": files,
        "demo": demo_mode,
        "message": "Imported using your session sign-in."
        if not demo_mode
        else "Imported demo content (complete OAuth or paste API key for live data).",
    }


def export_to_connector(
    session_id: str,
    connector_id: str,
    content: str,
    destination: str = "file",
) -> dict[str, Any]:
    conn = get_connection_status(session_id, connector_id)
    if conn.get("status") != "connected":
        return {"ok": False, "message": "Connect this service before exporting."}
    if COMPOSIO_DRY_RUN:
        return {
            "ok": True,
            "dry_run": True,
            "message": "Export plan recorded (COMPOSIO_DRY_RUN=1). Set COMPOSIO_DRY_RUN=0 for live writes.",
            "planned": {"connector": connector_id, "destination": destination, "bytes": len(content)},
        }
    if connector_id == "google_drive":
        action = "GOOGLEDRIVE_CREATE_FILE"
    elif connector_id == "github":
        action = "GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS"
    else:
        return {"ok": False, "message": f"Export not supported for {connector_id}"}
    try:
        result = _composio_execute(action, {"entity_id": session_id, "content": content[:8000]})
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
