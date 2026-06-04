"""Cost plan engine block (v1 gateway + catalog fallback)."""

from unittest.mock import patch

from agent.cost_plan import AttachmentRoles, build_cost_plan, format_engine_block
from agent.workload_parse import parse_workload_specs


def test_catalog_fallback_produces_engine_block():
    roles = AttachmentRoles(skills=[], github=[], drive=[], uploads=[])
    msg = "500M tokens/month on GPT-4o — use compare_providers"
    result = build_cost_plan(msg, roles)
    assert result.engine_block
    assert "INFERENCEATLAS ENGINE" in result.engine_block
    assert result.source in ("catalog_fallback", "inferenceatlas-v1")
    assert result.plans


def test_format_engine_block_includes_roles():
    specs = parse_workload_specs("500M tokens/month gpt-4o")
    payload = {
        "source": "catalog_fallback",
        "plans": [
            {
                "rank": 1,
                "provider_id": "openai",
                "billing_mode": "per_token",
                "monthly_cost_usd": 100.0,
                "cost_per_million_tokens": 0.5,
                "why": "test",
            }
        ],
    }
    roles = AttachmentRoles(skills=["/normalize"], github=["org/repo"], drive=[], uploads=["data.csv"])
    block = format_engine_block(payload, specs, roles)
    assert "/normalize" in block
    assert "org/repo" in block
    assert "data.csv" in block


@patch("agent.cost_plan.plan_llm")
def test_v1_plan_when_configured(mock_plan):
    mock_plan.return_value = {
        "ok": True,
        "source": "inferenceatlas-v1",
        "plans": [
            {
                "rank": 1,
                "provider_id": "nebius",
                "monthly_cost_usd": 42.0,
                "why": "rank_configs",
            }
        ],
    }
    with patch("agent.cost_plan.is_v1_configured", return_value=True):
        result = build_cost_plan(
            "500M tokens/month gpt-4o compare_providers",
            AttachmentRoles(skills=[], github=[], drive=[], uploads=[]),
        )
    assert result.source == "inferenceatlas-v1"
    assert "nebius" in result.engine_block
