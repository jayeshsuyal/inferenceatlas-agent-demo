"""Policy gate for deterministic agent-access review artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .scenarios import ROOT_DIR, SCENARIOS, build_scenario_brief, build_scenario_packet


POLICY_PATH = ROOT_DIR / "policy" / "agent_access.yml"
GATE_SCHEMA_VERSION = "agent_access_policy_gate.v0"


def _load_policy(policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    """Load the public policy file.

    The checked-in file uses YAML-compatible JSON so the no-key CI path can
    parse it with Python's standard library.
    """
    return json.loads(policy_path.read_text(encoding="utf-8"))


def _path_values(item: Any, path: str) -> list[Any]:
    values = [item]
    for part in path.split("."):
        next_values = []
        if part.endswith("[*]"):
            key = part[:-3]
            for value in values:
                if isinstance(value, dict) and isinstance(value.get(key), list):
                    next_values.extend(value[key])
        else:
            for value in values:
                if isinstance(value, dict) and part in value:
                    next_values.append(value[part])
        values = next_values
    return values


def _condition_matches(context: dict[str, Any], condition: dict[str, Any]) -> bool:
    values = _path_values(context, condition["path"])
    if "equals" in condition:
        return any(value == condition["equals"] for value in values)
    if "contains" in condition:
        expected = condition["contains"]
        for value in values:
            if isinstance(value, list) and expected in value:
                return True
            if value == expected:
                return True
        return False
    if condition.get("non_empty") is True:
        return any(bool(value) for value in values)
    raise ValueError(f"unsupported policy condition: {condition}")


def _rule_matches(context: dict[str, Any], rule: dict[str, Any]) -> bool:
    if "when_all" in rule:
        return all(_condition_matches(context, condition) for condition in rule["when_all"])
    return _condition_matches(context, rule["when"])


def _decision_from_rules(triggered_rules: list[dict[str, Any]]) -> tuple[str, str]:
    blocked = [rule for rule in triggered_rules if rule["effect"] == "blocked"]
    if blocked:
        return "BLOCKED", blocked[0]["message"]

    allowed = [rule for rule in triggered_rules if rule["effect"] == "allow_validation"]
    proof = [rule for rule in triggered_rules if rule["effect"] == "requires_proof"]
    if allowed and proof:
        return "VALIDATION_ALLOWED_WITH_GATES", "Scoped validation may proceed, but open proof debt remains owner-routed."
    if allowed:
        return "VALIDATION_ALLOWED", allowed[0]["message"]
    return "BLOCKED", "No policy rule allowed this request to move."


def evaluate_gate(scenario_name: str, *, policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    """Evaluate one scenario against the public agent-access policy gate."""
    policy = _load_policy(policy_path)
    packet = build_scenario_packet(scenario_name)
    brief = build_scenario_brief(scenario_name)
    context = {"packet": packet, "brief": brief}
    triggered_rules = [
        {
            "rule_id": rule["id"],
            "effect": rule["effect"],
            "message": rule["message"],
        }
        for rule in policy["rules"]
        if _rule_matches(context, rule)
    ]
    decision, reason = _decision_from_rules(triggered_rules)
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "policy_version": policy["policy_version"],
        "policy_path": str(policy_path.relative_to(ROOT_DIR) if policy_path.is_relative_to(ROOT_DIR) else policy_path),
        "scenario": scenario_name,
        "packet_id": packet["packet_id"],
        "brief_id": brief["brief_id"],
        "decision": decision,
        "reason": reason,
        "triggered_rules": triggered_rules,
        "safety_state": {
            "production_access": brief["go_no_go"]["production_access"],
            "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
            "external_writes": brief["go_no_go"]["external_writes"],
            "composio_dry_run": brief["go_no_go"]["composio_dry_run"],
            "approval_granted": packet["safety_state"]["approval_granted"],
        },
        "required_actions": [
            {
                "owner": item["owner"],
                "action": item["action"],
                "blocks": item["blocks"],
            }
            for item in packet["reviewer_action_items"]
        ],
    }


def evaluate_all(*, policy_path: Path = POLICY_PATH) -> dict[str, dict[str, Any]]:
    """Evaluate every registered scenario against the policy gate."""
    return {scenario_name: evaluate_gate(scenario_name, policy_path=policy_path) for scenario_name in SCENARIOS}


def render_gate_markdown(result: dict[str, Any]) -> str:
    """Render a gate decision for humans."""
    lines = [
        f"# Policy Gate: {result['scenario']}",
        "",
        f"- policy: {result['policy_version']}",
        f"- decision: {result['decision']}",
        f"- reason: {result['reason']}",
        f"- packet: {result['packet_id']}",
        f"- brief: {result['brief_id']}",
        "",
        "## Triggered Rules",
        "",
    ]
    for rule in result["triggered_rules"]:
        lines.append(f"- {rule['rule_id']} ({rule['effect']}): {rule['message']}")
    lines.extend(["", "## Safety State", ""])
    for key, value in result["safety_state"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Required Actions", ""])
    for item in result["required_actions"]:
        lines.append(f"- {item['owner']}: {item['action']} | blocks: {item['blocks']}")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.gate",
        description="Evaluate deterministic agent-access scenarios against the public policy gate.",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS),
        default="support_triage_agent",
        help="Registered scenario to evaluate.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all registered scenarios.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=POLICY_PATH,
        help="Policy file to evaluate.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable gate results.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.all:
        results = evaluate_all(policy_path=args.policy)
        if args.json:
            print(json.dumps({"results": results}, indent=2, sort_keys=True))
        else:
            for result in results.values():
                print(render_gate_markdown(result))
        return 0

    result = evaluate_gate(args.scenario, policy_path=args.policy)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_gate_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
