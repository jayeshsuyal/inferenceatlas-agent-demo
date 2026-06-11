"""Portkey BYO Guardrail setup artifact tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agent.portkey_setup import (
    PORTKEY_GUARDRAIL_SETUP_SCHEMA_VERSION,
    build_portkey_guardrail_setup,
    render_portkey_guardrail_setup_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


def _expect_value_error(message: str, **kwargs) -> None:
    try:
        build_portkey_guardrail_setup(public_base_url="https://ia-demo.example.com", **kwargs)
    except ValueError as exc:
        assert message in str(exc)
        return
    raise AssertionError(f"Expected ValueError containing {message!r}")


def test_portkey_setup_builds_dashboard_config_without_printing_token(monkeypatch) -> None:
    monkeypatch.setenv("PORTKEY_GUARDRAIL_TOKEN", "real-demo-secret")

    payload = build_portkey_guardrail_setup(
        public_base_url="https://ia-demo.example.com/",
        fixture="ai_spend_budget_overrun",
        requested_mode="model_request",
    )

    assert payload["schema_version"] == PORTKEY_GUARDRAIL_SETUP_SCHEMA_VERSION
    assert payload["read_only"] is True
    assert payload["webhook"]["url"] == "https://ia-demo.example.com/api/portkey/guardrail"
    assert payload["webhook"]["token_configured"] is True

    config = payload["portkey_dashboard_config"]
    assert config["webhook_url"] == "https://ia-demo.example.com/api/portkey/guardrail"
    assert config["headers_json"] == {
        "Authorization": "Bearer <PORTKEY_GUARDRAIL_TOKEN>",
        "Content-Type": "application/json",
    }
    assert config["metadata_json"]["ia_fixture"] == "ai_spend_budget_overrun"
    assert config["metadata_json"]["ia_packet_id"] == "ia-spend-review-ai_spend_budget_overrun-v0"
    assert config["metadata_json"]["ia_revision_id"] == "rev_47f8ff3775dec3c5"
    assert config["metadata_json"]["ia_requested_mode"] == "model_request"
    assert config["expected_response_shape"]["verdict"] == "boolean"

    serialized = json.dumps(payload, sort_keys=True)
    assert "real-demo-secret" not in serialized
    assert payload["safety"]["portkey_api_call_made"] is False
    assert payload["safety"]["portkey_policy_mutation_allowed"] is False
    assert payload["timeout_boundary"]["portkey_timeout_default_verdict"] is True
    assert "not an IA approval" in payload["timeout_boundary"]["claim_boundary"]


def test_portkey_setup_markdown_is_operator_ready_and_secret_safe(monkeypatch) -> None:
    monkeypatch.setenv("PORTKEY_GUARDRAIL_TOKEN", "real-demo-secret")
    payload = build_portkey_guardrail_setup(public_base_url="https://ia-demo.example.com")

    rendered = render_portkey_guardrail_setup_markdown(payload)

    assert "Portkey BYO Guardrail Setup" in rendered
    assert "https://ia-demo.example.com/api/portkey/guardrail" in rendered
    assert "Authorization" in rendered
    assert "Bearer <PORTKEY_GUARDRAIL_TOKEN>" in rendered
    assert "ia_packet_id" in rendered
    assert "Portkey timeout default verdict: `true`" in rendered
    assert "No Admin API mutation" in rendered
    assert "real-demo-secret" not in rendered


def test_portkey_setup_cli_emits_json_and_rejects_bad_base_url(monkeypatch) -> None:
    monkeypatch.setenv("PORTKEY_GUARDRAIL_TOKEN", "real-demo-secret")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.portkey_setup",
            "--public-base-url",
            "https://ia-demo.example.com",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == PORTKEY_GUARDRAIL_SETUP_SCHEMA_VERSION
    assert payload["portkey_dashboard_config"]["headers_json"]["Authorization"] == (
        "Bearer <PORTKEY_GUARDRAIL_TOKEN>"
    )
    assert "real-demo-secret" not in proc.stdout

    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.portkey_setup",
            "--public-base-url",
            "not-a-url",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert bad.returncode == 2
    assert "public_base_url" in bad.stderr


def test_portkey_setup_is_documented() -> None:
    command_reference = (ROOT / "docs" / "COMMAND_REFERENCE.md").read_text(encoding="utf-8")
    assert "Portkey BYO Guardrail Setup" in command_reference
    assert "python3 -m agent.portkey_setup" in command_reference
    assert "Authorization: Bearer <PORTKEY_GUARDRAIL_TOKEN>" in command_reference
    assert "does not call Portkey APIs" in command_reference


def test_portkey_setup_rejects_non_positive_timeouts() -> None:
    _expect_value_error("timeout_ms", timeout_ms=0)
    _expect_value_error("ia_latency_budget_ms", ia_latency_budget_ms=0)
