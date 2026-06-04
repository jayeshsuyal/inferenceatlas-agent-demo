"""InferenceAtlas-v1 HTTP client."""

from agent.v1_client import normalize_plans


def test_normalize_plans_list():
    assert len(normalize_plans([{"rank": 1, "monthly_cost_usd": 10}])) == 1


def test_normalize_plans_wrapped():
    payload = {"plans": [{"rank": 2, "provider_id": "x"}]}
    assert normalize_plans(payload)[0]["provider_id"] == "x"


def test_normalize_plans_single_dict():
    assert normalize_plans({"rank": 1, "monthly_cost_usd": 5})[0]["rank"] == 1
