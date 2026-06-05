"""Access-review questions must not hit Composio dry-run tool loop."""

from agent.chat_orchestrator import orchestrate_chat
from agent.workload_parse import is_access_review_question


def test_detects_support_triage_example():
    msg = (
        "Should our support triage agent get GitHub issues, Slack incident "
        "channels, and Jira ticket creation access?"
    )
    assert is_access_review_question(msg)


def test_orchestrate_injects_harness_without_skills():
    msg = (
        "Should our support triage agent get GitHub issues, Slack incident "
        "channels, and Jira ticket creation access?"
    )
    orch = orchestrate_chat(
        message=msg,
        skill_ids=[],
        skill_position="prepend",
        session_id="access-route-test",
        github_repos=[],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
    )
    assert orch.harness_injected
    assert orch.use_tools is False
    assert "HARNESS FACTS" in orch.llm_message
    assert "DecisionPacket" in orch.llm_message or "decision" in orch.llm_message.lower()
