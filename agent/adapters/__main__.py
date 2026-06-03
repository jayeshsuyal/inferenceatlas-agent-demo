"""CLI for dry-run sponsor adapter contracts."""

from __future__ import annotations

import argparse
import json
import sys

from agent.adapters.core import ADAPTER_NAMES, build_adapter_result, build_all_adapter_results
from agent.scenarios import SCENARIOS


def _render_human(results: dict[str, dict]) -> str:
    lines = ["Sponsor adapter contracts:"]
    for provider, result in results.items():
        lines.append(
            "- {provider}: {status} | proof={proof_type} | would_execute={would_execute} | can_approve_access={can_approve}".format(
                provider=provider,
                status=result["status"],
                proof_type=result["proof_pack"]["proof_type"],
                would_execute=result["would_execute"],
                can_approve=result["can_approve_access"],
            )
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.adapters",
        description="Render dry-run sponsor adapter contracts.",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS),
        default="support_triage_agent",
        help="Registered scenario to build adapter contracts for.",
    )
    parser.add_argument(
        "--provider",
        choices=ADAPTER_NAMES,
        help="Render one provider. Defaults to all providers with --all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render all sponsor adapter contracts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable adapter results.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.all and not args.provider:
        parser.error("choose --all or --provider")

    if args.all:
        results = build_all_adapter_results(args.scenario)
    else:
        results = {args.provider: build_adapter_result(args.provider, args.scenario)}

    if args.json:
        print(json.dumps({"results": results}, indent=2, sort_keys=True))
    else:
        print(_render_human(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
