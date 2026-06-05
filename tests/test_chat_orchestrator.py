"""Unified chat orchestration."""

import agent.chat_orchestrator as chat_orchestrator
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
    assert orch.engine_source in (
        "inferenceatlas-v1-copilot",
        "inferenceatlas-v1",
        "catalog_fallback",
    )
    if orch.direct_reply:
        assert "Recommendation" in orch.direct_reply or "Engine summary" in orch.direct_reply
    else:
        assert "INFERENCEATLAS ENGINE" in orch.llm_message
    assert any(
        "copilot" in s.lower()
        or "engine" in s.lower()
        or "catalog fallback" in s.lower()
        or "inferenceatlas-v1" in s.lower()
        or "plan_llm" in s.lower()
        for s in orch.thinking_steps
    )


def test_known_catalog_example_is_direct_and_not_llm_mush():
    orch = orchestrate_chat(
        message="Use get_catalog_summary: what does InferenceAtlas track?",
        skill_ids=[],
        skill_position="prepend",
        session_id="orch-catalog-example",
        github_repos=[],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
    )

    assert orch.direct_reply
    assert orch.direct_reply_source == "catalog_example"
    assert orch.use_tools is False
    assert "InferenceAtlas Catalog" in orch.direct_reply
    assert "Catalog fallback engine" not in orch.context_manifest
    assert "Deterministic catalog example" in orch.context_manifest


def test_mistral_demo_search_is_summarized_not_raw_scrape_dump(monkeypatch):
    monkeypatch.setattr(
        chat_orchestrator,
        "tavily_search",
        lambda *_args, **_kwargs: (
            "**Pricing - Mistral** — https://mistral.ai/pricing\n"
            "$0 0 1 2 3 noisy scraped pricing content"
        ),
    )

    orch = orchestrate_chat(
        message=(
            "Use tavily_search for Mistral Large pricing, then compare_providers "
            "for llm workloads in the catalog."
        ),
        skill_ids=[],
        skill_position="prepend",
        session_id="orch-mistral-example",
        github_repos=[],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
    )

    assert orch.direct_reply
    assert orch.direct_reply_source == "pricing_example"
    assert orch.use_tools is False
    assert "Live search evidence from Tavily" in orch.direct_reply
    assert "Catalog comparison" in orch.direct_reply
    assert "not a savings guarantee" in orch.direct_reply
    assert "$0 0 1 2 3" not in orch.direct_reply


def test_product_positioning_questions_are_direct_control_layer_answers():
    for message in ("what else can u do??", "how are u better than claude and chatgpt/"):
        orch = orchestrate_chat(
            message=message,
            skill_ids=[],
            skill_position="prepend",
            session_id="orch-positioning",
            github_repos=[],
            drive_file_ids=[],
            file_blocks=[],
            attach_warnings=[],
        )

        assert orch.direct_reply
        assert orch.direct_reply_source == "product_positioning"
        assert orch.use_tools is False
        assert "proof packet" in orch.direct_reply
        assert "DecisionPacket" in orch.direct_reply
        assert "another general chatbot" in orch.direct_reply
        assert "export_report" not in orch.direct_reply
        assert "InferenceAtlas product positioning" in orch.context_manifest
