"""Session metrics counters."""

import uuid

from agent.session_metrics import (
    get_session_metrics,
    record_demo_llm_usage,
    record_v1_http,
    set_metrics_session,
)


def test_session_metrics_accumulate():
    sid = f"metrics-test-{uuid.uuid4().hex[:8]}"
    set_metrics_session(sid)
    record_demo_llm_usage(prompt_tokens=100, completion_tokens=50, label="test")
    record_v1_http("copilot")
    data = get_session_metrics(sid)
    assert data["billable"]["demo_llm"]["calls"] == 1
    assert data["billable"]["demo_llm"]["total_tokens"] == 150
    assert data["billable"]["v1_http"]["copilot_calls"] == 1
