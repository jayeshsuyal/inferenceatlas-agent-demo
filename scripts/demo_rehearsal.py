#!/usr/bin/env python3
"""Run the no-key rehearsal gate for the 90-second public demo."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = os.environ.get("PYTHON", sys.executable)
BASE_URL = "http://127.0.0.1:8080"
COLD_START_URL = f"{BASE_URL}/packet?fixture=mcp_tool_blast_radius&autorun=1"
SPONSOR_ORDER = ("tavily", "composio", "openclaw", "nebius")
PACKET_COACH_PROMPTS: tuple[dict[str, str | None], ...] = (
    {
        "fixture": "mcp_tool_blast_radius",
        "subscriber": None,
        "question": "Can this move?",
    },
    {
        "fixture": "mcp_tool_blast_radius",
        "subscriber": None,
        "question": "What proof is missing?",
    },
    {
        "fixture": "mcp_tool_blast_radius",
        "subscriber": None,
        "question": "Who reviews this?",
    },
    {
        "fixture": "ai_spend_budget_overrun",
        "subscriber": "portkey_model_spend_gate",
        "question": "Can Portkey allow this spend?",
    },
)
SAFETY_FALSE_KEYS = (
    "approves_access",
    "approves_spend",
    "executes_external_writes",
    "grants_permissions",
    "guarantees_savings",
    "mutates_production",
    "selects_provider",
)


class RehearsalFailure(RuntimeError):
    pass


def _demo_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "NEBIUS_API_KEY",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
        "COMPOSIO_API_KEY",
        "GITHUB_OAUTH_CLIENT_SECRET",
        "GOOGLE_OAUTH_CLIENT_SECRET",
    ):
        env[key] = ""
    env["COMPOSIO_DRY_RUN"] = "1"
    env["IA_DISABLE_DOTENV"] = "1"
    env["IA_LIVE_MODE"] = ""
    return env


def _run(args: list[str], *, parse_json: bool = False) -> Any:
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=_demo_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        command = " ".join(args)
        raise RehearsalFailure(
            f"{command} failed with exit code {result.returncode}\n"
            f"stdout:\n{result.stdout[-2000:]}\n"
            f"stderr:\n{result.stderr[-2000:]}"
        )
    if parse_json:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RehearsalFailure(f"{' '.join(args)} did not return valid JSON: {exc}") from exc
    return result.stdout


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalFailure(message)


def _assert_safety_boundary(safety: dict[str, Any], *, label: str) -> None:
    for key in SAFETY_FALSE_KEYS:
        _expect(safety.get(key) is False, f"{label} safety drifted: {key} must be false")
    _expect(safety.get("requires_human_review") is True, f"{label} must require human review")


def _run_packet_coach_checks() -> list[dict[str, Any]]:
    answers: list[dict[str, Any]] = []
    for prompt in PACKET_COACH_PROMPTS:
        args = [
            PYTHON_BIN,
            "-m",
            "agent.packet_advisor",
            "--fixture",
            str(prompt["fixture"]),
            "--question",
            str(prompt["question"]),
            "--json",
        ]
        if prompt["subscriber"]:
            args.extend(["--subscriber", str(prompt["subscriber"])])

        answer = _run(args, parse_json=True)
        label = f"Ask IA prompt {prompt['question']!r}"
        _expect(answer.get("schema_version") == "packet_advisor_answer.v0", f"{label} schema drifted")
        _expect(answer.get("supported") is True, f"{label} must stay supported")
        _expect(answer.get("packet_reference", {}).get("packet_id"), f"{label} missing packet id")
        _assert_safety_boundary(answer.get("safety", {}), label=label)

        tone = answer.get("tone_invariants", {})
        _expect(tone.get("contains_does_not_approve") is True, f"{label} lost no-approval anchor")
        _expect(tone.get("contains_human_review") is True, f"{label} lost human-review anchor")
        _expect(tone.get("contains_stays_blocked") is True, f"{label} lost blocked-state anchor")
        _expect(tone.get("forbidden_hedges") == [], f"{label} contains hedge phrases")
        rendered = answer.get("rendered_text", "")
        _expect("Safety anchor" in rendered, f"{label} missing rendered safety anchor")

        answers.append(
            {
                "question": prompt["question"],
                "fixture": prompt["fixture"],
                "subscriber": prompt["subscriber"],
                "answer_kind": answer.get("answer_kind"),
                "packet_id": answer.get("packet_reference", {}).get("packet_id"),
                "verdict_class": answer.get("verdict_class"),
                "next_human_action": answer.get("next_human_action"),
            }
        )
    return answers


def _run_portkey_check() -> dict[str, Any]:
    portkey = _run(
        [
            PYTHON_BIN,
            "-m",
            "agent.portkey_adapter",
            "--fixture",
            "ai_spend_budget_overrun",
            "--mode",
            "dry-run",
            "--json",
        ],
        parse_json=True,
    )
    _expect(portkey.get("schema_version") == "portkey_gate_v0", "Portkey schema drifted")
    _expect(portkey.get("mode") == "dry-run", "Portkey mode must stay dry-run")
    _expect(portkey.get("dry_run") is True, "Portkey dry-run flag must be true")
    _expect(portkey.get("api_call_made") is False, "Portkey API call must not be made")
    _expect(
        portkey.get("portkey_guardrail_response", {}).get("verdict") is False,
        "Portkey guardrail verdict must stay false",
    )
    _expect(
        portkey.get("usage_policy_plan", {}).get("request_body", {}).get("credit_limit") == 0,
        "Portkey credit limit must stay zero in the public dry-run",
    )
    invariants = portkey.get("invariants", {})
    _expect(invariants.get("live_mutation_enabled") is False, "Portkey live mutation must stay disabled")
    _expect(invariants.get("portkey_api_call_made") is False, "Portkey invariant must show no API call")
    _expect(invariants.get("raw_agent_intent_trusted") is False, "Portkey must not trust raw agent intent")
    return {
        "mode": portkey.get("mode"),
        "api_call_made": portkey.get("api_call_made"),
        "guardrail_verdict": portkey.get("portkey_guardrail_response", {}).get("verdict"),
        "credit_limit": portkey.get("usage_policy_plan", {}).get("request_body", {}).get("credit_limit"),
        "packet_id": portkey.get("ia_packet_reference", {}).get("packet_id"),
    }


def _run_sponsor_check() -> dict[str, Any]:
    sponsor = _run(
        [
            PYTHON_BIN,
            "-m",
            "agent.sponsor_proof_collector",
            "examples/requests/support_triage_trial.yml",
            "--no-write",
            "--json",
        ],
        parse_json=True,
    )
    _expect(
        sponsor.get("schema_version") == "sponsor_proof_collector_run.v0",
        "Sponsor Proof Run schema drifted",
    )
    _expect(sponsor.get("mode") == "offline_dry_run", "Sponsor Proof Run must stay offline dry-run")
    _expect(sponsor.get("status") == "completed", "Sponsor Proof Run must complete")
    _expect(sponsor.get("run_id"), "Sponsor Proof Run missing run_id")
    _expect(sponsor.get("packet_reference", {}).get("packet_id"), "Sponsor Proof Run missing packet reference")
    _assert_safety_boundary(sponsor.get("safety_boundary", {}), label="Sponsor Proof Run")
    _expect(
        sponsor.get("safety_boundary", {}).get("read_only") is True,
        "Sponsor Proof Run must stay read-only",
    )
    _expect(
        sponsor.get("safety_boundary", {}).get("live_calls_made") is False,
        "Sponsor Proof Run must not make live calls in rehearsal",
    )

    steps = sponsor.get("collector_steps", [])
    _expect([step.get("sponsor") for step in steps] == list(SPONSOR_ORDER), "Sponsor order drifted")
    for step in steps:
        sponsor_name = step.get("sponsor")
        _expect(step.get("fallback_used") is True, f"{sponsor_name} fallback must be used")
        _expect(step.get("used_live_key") is False, f"{sponsor_name} must not use a live key")
        _expect(step.get("would_execute") is False, f"{sponsor_name} must not execute")
        _expect(step.get("can_approve_access") is False, f"{sponsor_name} must not approve access")
        _expect(step.get("can_grant_permissions") is False, f"{sponsor_name} must not grant permissions")
        _expect(
            step.get("can_mutate_external_state") is False,
            f"{sponsor_name} must not mutate external state",
        )

    return {
        "run_id": sponsor.get("run_id"),
        "mode": sponsor.get("mode"),
        "packet_id": sponsor.get("packet_reference", {}).get("packet_id"),
        "steps": [step.get("sponsor") for step in steps],
        "fallback_used": {step.get("sponsor"): step.get("fallback_used") for step in steps},
        "live_calls_made": sponsor.get("safety_boundary", {}).get("live_calls_made"),
    }


def build_rehearsal_report() -> dict[str, Any]:
    _run(["bash", "scripts/review_60.sh", "--dry-run"])
    packet_coach = _run_packet_coach_checks()
    portkey = _run_portkey_check()
    sponsor = _run_sponsor_check()
    _run([PYTHON_BIN, "-m", "agent.verify_artifacts", "--json"], parse_json=True)
    return {
        "schema_version": "demo_rehearsal_gate.v0",
        "status": "passed",
        "cold_start_url": COLD_START_URL,
        "no_live_keys_required": True,
        "external_writes_enabled": False,
        "approval_granted": False,
        "checks": {
            "review_path_preflight": "passed",
            "packet_coach_prompts": packet_coach,
            "portkey_dry_run": portkey,
            "sponsor_proof_run": sponsor,
            "artifact_integrity": "passed",
        },
        "recording_ready_when_rehearsed_twice": True,
    }


def render_markdown(report: dict[str, Any]) -> str:
    ask_lines = "\n".join(
        f"- {item['question']} -> {item['answer_kind']} from `{item['packet_id']}`"
        for item in report["checks"]["packet_coach_prompts"]
    )
    sponsor = report["checks"]["sponsor_proof_run"]
    portkey = report["checks"]["portkey_dry_run"]
    return f"""# Demo Rehearsal Gate

Private engine, public proof.

- status: `{report["status"]}`
- cold-start URL: `{report["cold_start_url"]}`
- no live keys required: `{report["no_live_keys_required"]}`
- external writes enabled: `{report["external_writes_enabled"]}`
- approval granted: `{report["approval_granted"]}`

## Ask IA Prompts

{ask_lines}

## Portkey Dry-Run

- mode: `{portkey["mode"]}`
- API call made: `{portkey["api_call_made"]}`
- guardrail verdict: `{portkey["guardrail_verdict"]}`
- usage credit limit: `{portkey["credit_limit"]}`

## Sponsor Proof Run

- run id: `{sponsor["run_id"]}`
- packet id: `{sponsor["packet_id"]}`
- mode: `{sponsor["mode"]}`
- sponsor order: `{ " -> ".join(sponsor["steps"]) }`
- live calls made: `{sponsor["live_calls_made"]}`

Record only after this gate passes twice and the browser path is clean.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the no-key demo rehearsal gate.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable rehearsal report.")
    args = parser.parse_args()

    try:
        report = build_rehearsal_report()
    except RehearsalFailure as exc:
        print(f"Demo rehearsal gate failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
