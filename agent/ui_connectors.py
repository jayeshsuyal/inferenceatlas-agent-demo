"""UI connector registry for the InferenceAtlas web + menu."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, List, Literal, Optional

from .config import (
    COMPOSIO_API_KEY,
    COMPOSIO_DRY_RUN,
    LLM_API_KEY,
    LLM_PROVIDER,
    NEBIUS_API_KEY,
    OPENAI_API_KEY,
    TAVILY_API_KEY,
)
from .connector_runtime import CONNECTOR_META, session_statuses

ConnectorStatus = Literal[
    "connected",
    "dry_run",
    "needs_key",
    "optional",
    "connect_via_composio",
]


@dataclass(frozen=True)
class ConnectorAction:
    id: str
    label: str
    layman: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label, "layman": self.layman}


@dataclass(frozen=True)
class UIConnector:
    id: str
    name: str
    icon: str
    layman_summary: str
    helps_with: str
    how_to_connect: str
    env_vars: tuple[str, ...]
    actions: tuple[ConnectorAction, ...] = ()

    auth_type: str = "api_key_server"

    def to_dict(
        self,
        *,
        status: ConnectorStatus,
        status_label: str,
        session_connection: Optional[dict] = None,
    ) -> dict[str, Any]:
        meta = CONNECTOR_META.get(self.id)
        sc = session_connection or {}
        signed_in = sc.get("status") == "connected"
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "layman_summary": self.layman_summary,
            "helps_with": self.helps_with,
            "how_to_connect": self.how_to_connect,
            "env_vars": list(self.env_vars),
            "auth_type": meta.auth_type if meta else self.auth_type,
            "status": status,
            "status_label": status_label,
            "signed_in": signed_in,
            "session_status": sc.get("status", "disconnected"),
            "actions": [a.to_dict() for a in self.actions],
        }


CONNECTORS: tuple[UIConnector, ...] = (
    UIConnector(
        id="github",
        name="GitHub",
        icon="github",
        layman_summary="Pull repos, issues, and YAML access requests from your GitHub account.",
        helps_with="Import real repo context and trial request files for access-review evidence.",
        how_to_connect="Click Sign in — GitHub OAuth popup (your account, cached for this chat session only).",
        env_vars=(),
        auth_type="oauth_popup",
        actions=(
            ConnectorAction(
                id="repos",
                label="Repositories",
                layman="Search and attach a repo — the chat reads README, tree, and key files.",
            ),
            ConnectorAction(
                id="issues",
                label="Issues & PRs",
                layman="Pull recent issues/PR metadata as evidence for triage bots.",
            ),
        ),
    ),
    UIConnector(
        id="google_drive",
        name="Google Drive",
        icon="gdrive",
        layman_summary="Pull spreadsheets, docs, and images from Drive as review evidence.",
        helps_with="Attach policy PDFs, architecture diagrams, or trial notes without emailing files.",
        how_to_connect="Click Sign in — Google OAuth popup for Drive (session-only; not stored in .env).",
        env_vars=(),
        auth_type="oauth_popup",
        actions=(
            ConnectorAction(
                id="files",
                label="Files & spreadsheets",
                layman="Search Drive and attach docs, sheets, or PDFs — indexed for chat like GitHub repos.",
            ),
            ConnectorAction(
                id="photos",
                label="Photos & images",
                layman="Pick images from Drive — metadata and preview indexed for review evidence.",
            ),
            ConnectorAction(
                id="videos",
                label="Videos",
                layman="Pick videos from Drive — title, link, and metadata indexed for triage proof.",
            ),
        ),
    ),
    UIConnector(
        id="nebius",
        name="Nebius",
        icon="nebius",
        layman_summary="Powers the chat LLM (cost Q&A and access-review narration).",
        helps_with="Runs Llama and other models on Nebius Studio for this demo agent.",
        how_to_connect="Click Sign in — paste your Nebius API key in the popup (this session only).",
        env_vars=(),
        auth_type="oauth_popup",
    ),
    UIConnector(
        id="tavily",
        name="Tavily",
        icon="tavily",
        layman_summary="Live web search for AI provider pricing, benchmarks, and news.",
        helps_with="Grounds cost comparisons in current public pricing instead of stale guesses.",
        how_to_connect="Click Sign in — paste your Tavily API key in the popup (this session only).",
        env_vars=(),
        auth_type="oauth_popup",
    ),
    UIConnector(
        id="composio",
        name="Composio",
        icon="composio",
        layman_summary="Your Composio project for integrations (GitHub, Slack, Jira, Sheets).",
        helps_with="Uses your Composio key in-session to plan tool actions.",
        how_to_connect="Click Sign in — paste your Composio API key in the popup (session only).",
        env_vars=(),
        auth_type="oauth_popup",
    ),
    UIConnector(
        id="openclaw",
        name="OpenClaw",
        icon="openclaw",
        layman_summary="Optional agent runtime for multi-step tool loops (advanced).",
        helps_with="When installed, runs the same tool-calling loop as the built-in agent runtime.",
        how_to_connect="Click Sign in — confirm OpenClaw for this session in the popup.",
        env_vars=(),
        auth_type="oauth_popup",
    ),
)


def _openclaw_available() -> bool:
    try:
        importlib.import_module("openclaw")
        return True
    except Exception:
        return False


def _status_for(connector: UIConnector, session_connection: Optional[dict] = None) -> tuple[ConnectorStatus, str]:
    sc = session_connection or {}
    if sc.get("status") == "connected":
        account = sc.get("account")
        if account:
            return "connected", f"Signed in as {account}"
        return "connected", "Signed in"
    if sc.get("status") == "pending":
        return "connect_via_composio", "Finish sign-in in popup"
    return "connect_via_composio", "Sign in"


def build_connectors_payload(session_id: Optional[str] = None) -> dict[str, Any]:
    live = session_statuses(session_id) if session_id else {}
    items: List[dict[str, Any]] = []
    for connector in CONNECTORS:
        sc = live.get(connector.id, {})
        status, label = _status_for(connector, sc)
        items.append(
            connector.to_dict(status=status, status_label=label, session_connection=sc)
        )
    return {
        "schema_version": "inferenceatlas_ui_connectors.v0",
        "count": len(items),
        "connectors": items,
        "intro": {
            "skills_title": "Skills",
            "skills_blurb": (
                "Skills are pre-built **access-review proof packs**. Attach one or more, "
                "ask a plain-English question, then Send — the AI answers from real "
                "DecisionPacket data (who is blocked, what proof is missing). "
                "They do not grant production access."
            ),
            "connectors_title": "Connectors",
            "connectors_blurb": (
                "Each connector opens a sign-in popup (GitHub/Google OAuth or paste your API key). "
                "Credentials are cached per chat session — not in the host .env."
            ),
        },
    }
