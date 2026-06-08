"""Sponsor live-readiness surface for the public agent-access harness."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .adapters import build_adapter_result
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS
from .sponsor_proof_trace import SPONSOR_ORDER


SPONSOR_READINESS_SCHEMA_VERSION = "sponsor_live_readiness.v0"
SPONSOR_READINESS_ID = "ia-sponsor-live-readiness-public-v0"
DEFAULT_SCENARIO = "support_triage_agent"
DEFAULT_PUBLIC_DEMO_MODE = {
    "nebius": "fallback_narration",
    "tavily": "fallback_evidence_candidates",
    "composio": "dry_run_permission_diff",
    "openclaw": "fallback_runtime_trace",
}


PROVIDER_READINESS = {
    "nebius": {
        "env_vars": ["NEBIUS_API_KEY", "NEBIUS_BASE_URL", "NEBIUS_MODEL"],
        "dry_run_surface": "locked-field narration preview",
        "fallback_surface": "deterministic reviewer narration",
        "live_capability": "LLM narration over locked packet fields",
        "live_value": "Reviewer-ready narration over locked packet fields.",
        "visible_outputs": [
            "reviewer summary projection",
            "demo transcript narration note",
            "trace step for model narration",
        ],
        "next_cto_step": "Connect Nebius only as a narration layer; keep verdict, blocked claims, and safety state locked.",
    },
    "tavily": {
        "env_vars": ["TAVILY_API_KEY"],
        "dry_run_surface": "evidence candidate slots",
        "fallback_surface": "deterministic missing-proof search plan",
        "live_capability": "source-backed evidence candidate retrieval",
        "live_value": "Source-backed evidence notes with URL and freshness fields.",
        "visible_outputs": [
            "evidence notes",
            "source URL slots",
            "freshness status",
        ],
        "next_cto_step": "Fetch evidence candidates for missing proof; require human review before proof debt changes.",
    },
    "composio": {
        "env_vars": ["COMPOSIO_API_KEY", "COMPOSIO_DRY_RUN"],
        "dry_run_surface": "permission diff plan",
        "fallback_surface": "deterministic permission diff plan",
        "live_capability": "scoped connector planning with dry-run enforcement",
        "live_value": "Dry-run permission diff for GitHub, Slack, and Jira actions.",
        "visible_outputs": [
            "tool-by-tool permission diff",
            "blocked action list",
            "required proof per action",
        ],
        "next_cto_step": "Keep Composio dry-run by default; emit action plans without granting permissions or writing.",
    },
    "openclaw": {
        "env_vars": ["IA_LIVE_MODE", "AGENT_MAX_STEPS"],
        "dry_run_surface": "runtime trace plan",
        "fallback_surface": "deterministic runtime trace plan",
        "live_capability": "runtime trace capture for attempted agent steps",
        "live_value": "Runtime trace plan for attempted steps, policy decisions, and blocked outcomes.",
        "visible_outputs": [
            "runtime trace steps",
            "policy decisions",
            "blocked outcome records",
        ],
        "next_cto_step": "Record the live agent loop as trace evidence; do not let runtime checks replace pre-permission review.",
    },
}

READINESS_MATRIX_COLUMNS = [
    "fallback_available",
    "dry_run_available",
    "live_capable",
    "env_ready_for_live",
    "live_enabled",
    "disabled_reason",
    "default_demo_mode",
]


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _env_status(env_vars: list[str], *, inspect_env: bool) -> dict[str, Any]:
    if not inspect_env:
        return {
            "inspected": False,
            "configured": False,
            "configured_vars": [],
            "missing_vars": [],
            "note": "Environment variables are not inspected in the default public path.",
        }

    configured = [name for name in env_vars if bool(os.environ.get(name))]
    missing = [name for name in env_vars if name not in configured]
    return {
        "inspected": True,
        "configured": bool(configured),
        "configured_vars": configured,
        "missing_vars": missing,
        "note": "Only variable names are reported; secret values are never printed.",
    }


def _env_ready_for_live(env_status: dict[str, Any], *, inspect_env: bool) -> bool:
    return bool(inspect_env and env_status["configured"] and not env_status["missing_vars"])


def _disabled_reason(provider: str, env_status: dict[str, Any], *, inspect_env: bool) -> str:
    if not inspect_env:
        return "env_not_inspected_public_default"
    if provider == "composio" and "COMPOSIO_DRY_RUN" in env_status["missing_vars"]:
        return "dry_run_flag_missing"
    if env_status["missing_vars"]:
        return "missing_env_vars"
    return "disabled_by_public_demo_policy"


def _readiness_matrix_row(provider: str, adapter: dict[str, Any], env_status: dict[str, Any], *, inspect_env: bool) -> dict[str, Any]:
    readiness = PROVIDER_READINESS[provider]
    env_ready = _env_ready_for_live(env_status, inspect_env=inspect_env)
    return {
        "provider": provider,
        "fallback_available": True,
        "fallback_surface": readiness["fallback_surface"],
        "dry_run_available": True,
        "dry_run_surface": readiness["dry_run_surface"],
        "live_capable": True,
        "live_capability": readiness["live_capability"],
        "env_ready_for_live": env_ready,
        "live_enabled": False,
        "disabled_reason": _disabled_reason(provider, env_status, inspect_env=inspect_env),
        "default_demo_mode": DEFAULT_PUBLIC_DEMO_MODE[provider],
        "api_key_required_for_default_path": adapter["requires_api_key"],
        "would_execute": adapter["would_execute"],
        "can_approve_access": adapter["can_approve_access"],
        "can_grant_permissions": adapter["can_grant_permissions"],
        "can_mutate_external_state": adapter["can_mutate_external_state"],
        "human_review_required": adapter["human_review_required"],
    }


def build_sponsor_live_readiness(
    scenario_name: str = DEFAULT_SCENARIO,
    *,
    inspect_env: bool = False,
) -> dict[str, Any]:
    """Build a no-key readiness report for sponsor integrations."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")

    providers = []
    readiness_matrix = []
    for provider in SPONSOR_ORDER:
        adapter = build_adapter_result(provider, scenario_name)
        readiness = PROVIDER_READINESS[provider]
        env_status = _env_status(readiness["env_vars"], inspect_env=inspect_env)
        providers.append(
            {
                "provider": provider,
                "scenario": scenario_name,
                "adapter_status": adapter["status"],
                "proof_pack_type": adapter["proof_pack"]["proof_type"],
                "readiness": "contract_ready",
                "live_value": readiness["live_value"],
                "visible_outputs": readiness["visible_outputs"],
                "next_cto_step": readiness["next_cto_step"],
                "env": env_status,
                "safety_boundary": {
                    "requires_api_key_in_default_path": adapter["requires_api_key"],
                    "would_execute": adapter["would_execute"],
                    "can_approve_access": adapter["can_approve_access"],
                    "can_grant_permissions": adapter["can_grant_permissions"],
                    "can_mutate_external_state": adapter["can_mutate_external_state"],
                    "blocked_from_approving_access": adapter["blocked_from_approving_access"],
                    "human_review_required": adapter["human_review_required"],
                },
                "cannot_do": adapter["proof_pack"]["cannot_do"],
            }
        )
        readiness_matrix.append(
            _readiness_matrix_row(provider, adapter, env_status, inspect_env=inspect_env)
        )

    return {
        "schema_version": SPONSOR_READINESS_SCHEMA_VERSION,
        "readiness_id": SPONSOR_READINESS_ID,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_readiness_contract",
        "scenario": scenario_name,
        "environment_inspected": inspect_env,
        "headline": "Sponsor tools enrich proof; they do not approve access.",
        "summary": {
            "provider_count": len(providers),
            "matrix_columns": READINESS_MATRIX_COLUMNS,
            "all_contracts_ready": all(provider["readiness"] == "contract_ready" for provider in providers),
            "default_path_requires_keys": False,
            "all_non_executing": all(not provider["safety_boundary"]["would_execute"] for provider in providers),
            "all_non_approving": all(not provider["safety_boundary"]["can_approve_access"] for provider in providers),
            "all_non_granting": all(not provider["safety_boundary"]["can_grant_permissions"] for provider in providers),
            "all_non_mutating": all(not provider["safety_boundary"]["can_mutate_external_state"] for provider in providers),
            "human_review_required": all(provider["safety_boundary"]["human_review_required"] for provider in providers),
            "all_fallback_available": all(row["fallback_available"] for row in readiness_matrix),
            "all_dry_run_available": all(row["dry_run_available"] for row in readiness_matrix),
            "all_live_capable": all(row["live_capable"] for row in readiness_matrix),
            "any_env_ready_for_live": any(row["env_ready_for_live"] for row in readiness_matrix),
            "any_live_enabled": any(row["live_enabled"] for row in readiness_matrix),
        },
        "providers": providers,
        "readiness_matrix": readiness_matrix,
        "default_public_boundary": {
            "works_without_keys": True,
            "live_calls_made": False,
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_production": False,
            "requires_human_review": True,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def render_sponsor_live_readiness_markdown(report: dict[str, Any]) -> str:
    """Render sponsor live readiness as compact Markdown."""
    lines = [
        "# Sponsor Live Readiness",
        "",
        "Private engine, public proof.",
        "",
        report["headline"],
        "",
        "## Summary",
        "",
        f"- scenario: `{report['scenario']}`",
        f"- provider count: {report['summary']['provider_count']}",
        f"- all contracts ready: {report['summary']['all_contracts_ready']}",
        f"- default path requires keys: {report['summary']['default_path_requires_keys']}",
        f"- all non-executing: {report['summary']['all_non_executing']}",
        f"- all non-approving: {report['summary']['all_non_approving']}",
        f"- all non-granting: {report['summary']['all_non_granting']}",
        f"- all non-mutating: {report['summary']['all_non_mutating']}",
        f"- human review required: {report['summary']['human_review_required']}",
        f"- all fallback available: {report['summary']['all_fallback_available']}",
        f"- all dry-run available: {report['summary']['all_dry_run_available']}",
        f"- all live-capable: {report['summary']['all_live_capable']}",
        f"- any live enabled: {report['summary']['any_live_enabled']}",
        "",
        "## Provider Readiness",
        "",
        "| Provider | Live Value | Proof Pack | Default Safety |",
        "| --- | --- | --- | --- |",
    ]
    for provider in report["providers"]:
        safety = provider["safety_boundary"]
        lines.append(
            "| {provider} | {live_value} | {proof_pack} | execute={execute}; approve={approve}; grant={grant}; mutate={mutate} |".format(
                provider=provider["provider"],
                live_value=provider["live_value"],
                proof_pack=provider["proof_pack_type"],
                execute=safety["would_execute"],
                approve=safety["can_approve_access"],
                grant=safety["can_grant_permissions"],
                mutate=safety["can_mutate_external_state"],
            )
        )

    lines.extend(
        [
            "",
            "## Readiness Matrix",
            "",
            "| Provider | Fallback | Dry Run | Live Capable | Live Enabled | Disabled Reason | Demo Mode |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["readiness_matrix"]:
        lines.append(
            "| {provider} | {fallback} | {dry_run} | {live_capable} | {live_enabled} | {disabled_reason} | {demo_mode} |".format(
                provider=row["provider"],
                fallback=row["fallback_available"],
                dry_run=row["dry_run_available"],
                live_capable=row["live_capable"],
                live_enabled=row["live_enabled"],
                disabled_reason=row["disabled_reason"],
                demo_mode=row["default_demo_mode"],
            )
        )

    lines.extend(["", "## CTO Next Steps", ""])
    for provider in report["providers"]:
        lines.append(f"- {provider['provider']}: {provider['next_cto_step']}")

    lines.extend(
        [
            "",
            "## Default Public Boundary",
            "",
            f"- works without keys: {report['default_public_boundary']['works_without_keys']}",
            f"- live calls made: {report['default_public_boundary']['live_calls_made']}",
            f"- approves access: {report['default_public_boundary']['approves_access']}",
            f"- grants permissions: {report['default_public_boundary']['grants_permissions']}",
            f"- executes external writes: {report['default_public_boundary']['executes_external_writes']}",
            f"- mutates production: {report['default_public_boundary']['mutates_production']}",
            f"- requires human review: {report['default_public_boundary']['requires_human_review']}",
            "",
            "Sponsor tools are proof contributors, not approval authorities.",
            "",
        ]
    )
    return "\n".join(lines)


def write_sponsor_live_readiness_artifacts(
    scenario_name: str = DEFAULT_SCENARIO,
    output_dir: Path = GENERATED_DIR,
    *,
    inspect_env: bool = False,
) -> list[Path]:
    """Write sponsor live readiness Markdown and JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_sponsor_live_readiness(scenario_name, inspect_env=inspect_env)
    readiness_json = output_dir / "sponsor_live_readiness.json"
    readiness_md = output_dir / "sponsor_live_readiness.md"

    readiness_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readiness_md.write_text(render_sponsor_live_readiness_markdown(report), encoding="utf-8")
    return [readiness_json, readiness_md]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.sponsor_readiness",
        description="Generate the public sponsor live-readiness surface.",
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default=DEFAULT_SCENARIO,
        help="Scenario to use for sponsor readiness contracts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory where readiness artifacts should be written.",
    )
    parser.add_argument(
        "--inspect-env",
        action="store_true",
        help="Report whether sponsor environment variable names are configured without printing values.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the readiness report as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing artifacts and print only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_sponsor_live_readiness(args.scenario, inspect_env=args.inspect_env)

    if not args.no_write:
        written = write_sponsor_live_readiness_artifacts(
            args.scenario,
            args.output_dir,
            inspect_env=args.inspect_env,
        )
        for path in written:
            print(_relative(path))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.no_write:
        print(render_sponsor_live_readiness_markdown(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
