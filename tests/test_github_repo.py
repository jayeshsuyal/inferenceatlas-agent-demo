"""GitHub repo list/attach/chat context (session-scoped)."""

from agent.connector_runtime import save_session
from agent.github_repo import (
    attach_repository,
    build_github_chat_context,
    list_repositories,
)


def _demo_github_session(session_id: str) -> None:
    save_session(
        session_id,
        {
            "connections": {
                "github": {
                    "status": "connected",
                    "mode": "demo_session",
                    "connector_id": "github",
                }
            }
        },
    )


def test_list_repositories_demo():
    sid = "test-github-list"
    _demo_github_session(sid)
    out = list_repositories(sid, query="triage")
    assert out["ok"]
    assert out["demo"]
    assert any("triage" in r["full_name"] for r in out["repos"])


def test_attach_and_chat_context():
    sid = "test-github-attach"
    _demo_github_session(sid)
    full_name = "inferenceatlas/support-triage-trial"
    result = attach_repository(sid, full_name)
    assert result["ok"]
    assert result["digest_chars"] > 100

    ctx, used = build_github_chat_context(sid, [full_name])
    assert full_name in used
    assert "GITHUB REPO" in ctx
    assert "support_triage" in ctx.lower() or "Repository context" in ctx
