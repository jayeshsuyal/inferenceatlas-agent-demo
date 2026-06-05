"""Unified chat orchestration."""

from agent.chat_orchestrator import orchestrate_chat, _wants_tools
from agent.connector_runtime import save_session


def test_wants_tools_compare_providers():
    assert _wants_tools("Use compare_providers for llm workloads")


def test_orchestrate_merges_github_and_skills():
    sid = "orch-merge"
    save_session(
        sid,
        {
            "connections": {
                "github": {"status": "connected", "mode": "demo_session", "connector_id": "github"}
            },
            "github_attached": {
                "inferenceatlas/support-triage-trial": {
                    "digest": "# GitHub repository: inferenceatlas/support-triage-trial\n\n## README\nDemo readme\n",
                    "digest_chars": 80,
                }
            },
        },
    )
    orch = orchestrate_chat(
        message="What blocks production access?",
        skill_ids=["decision_packet_generation"],
        skill_position="prepend",
        session_id=sid,
        github_repos=["inferenceatlas/support-triage-trial"],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
    )
    assert orch.skills_used
    assert orch.github_used
    assert "HARNESS FACTS" in orch.llm_message
    assert "GITHUB REPO" in orch.llm_message
    assert len(orch.thinking_steps) >= 4
    assert any("compare_providers" not in s for s in orch.thinking_steps)


def test_orchestrate_cost_uses_v1_engine_not_tools():
    orch = orchestrate_chat(
        message="Use compare_providers for llm and recommend cheapest alternative at 500M tokens/month",
        skill_ids=[],
        skill_position="prepend",
        session_id="orch-cost",
        github_repos=["oasb16/design-delight"],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
    )
    assert orch.use_tools is False
    assert orch.engine_source in ("inferenceatlas-v1", "catalog_fallback")
    assert "INFERENCEATLAS ENGINE" in orch.llm_message
    assert any(
        "engine" in s.lower()
        or "catalog fallback" in s.lower()
        or "inferenceatlas-v1" in s.lower()
        or "plan_llm" in s.lower()
        for s in orch.thinking_steps
    )
