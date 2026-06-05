"""Workload parsing for cost questions."""

from agent.workload_parse import is_cost_question, parse_workload_specs


def test_parse_500m_tokens_per_month():
    specs = parse_workload_specs(
        "We run 500M tokens/month on GPT-4o — compare providers and cheapest option"
    )
    assert specs.tokens_per_month == 500_000_000
    assert specs.tokens_per_day == 500_000_000 / 30.0
    assert specs.model_bucket == "4o"
    assert specs.baseline_model == "gpt-4o"


def test_is_cost_question_keywords():
    assert is_cost_question("Use compare_providers for llm workloads")
    assert is_cost_question("500 million tokens per month gpt-4o pricing")
    assert not is_cost_question("What blocks production access?")
