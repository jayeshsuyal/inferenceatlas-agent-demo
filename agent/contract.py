"""CLI for validating public conformance artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .public_contract import PUBLIC_CONTRACT_VERSION, validate_public_review_artifacts
from .scenarios import SCENARIOS, build_scenario_brief, build_scenario_packet


def _artifact_paths(scenario_name: str, generated_dir: Path) -> tuple[Path, Path]:
    return (
        generated_dir / f"{scenario_name}.packet.json",
        generated_dir / f"{scenario_name}.decision_brief.json",
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_scenario(scenario_name: str, *, generated_dir: Path | None = None) -> list[str]:
    """Validate one scenario from generated artifacts or from the in-memory engine."""
    if generated_dir is None:
        packet = build_scenario_packet(scenario_name)
        brief = build_scenario_brief(scenario_name)
    else:
        packet_path, brief_path = _artifact_paths(scenario_name, generated_dir)
        packet = _load_json(packet_path)
        brief = _load_json(brief_path)
    return validate_public_review_artifacts(packet, brief)


def validate_all(*, generated_dir: Path | None = None) -> dict[str, list[str]]:
    """Validate every registered scenario."""
    return {scenario_name: validate_scenario(scenario_name, generated_dir=generated_dir) for scenario_name in SCENARIOS}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.contract",
        description="Validate public InferenceAtlas conformance artifacts.",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS),
        help="Validate one scenario. Defaults to all scenarios with --all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all registered scenarios.",
    )
    parser.add_argument(
        "--generated-dir",
        type=Path,
        help="Validate checked-in generated JSON artifacts from this directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable validation results.",
    )
    return parser


def _print_human(results: dict[str, list[str]]) -> None:
    print(f"Public contract: {PUBLIC_CONTRACT_VERSION}")
    for scenario_name, errors in results.items():
        if errors:
            print(f"- {scenario_name}: FAIL")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"- {scenario_name}: OK")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.all and not args.scenario:
        parser.error("choose --all or --scenario")

    if args.all:
        results = validate_all(generated_dir=args.generated_dir)
    else:
        results = {args.scenario: validate_scenario(args.scenario, generated_dir=args.generated_dir)}

    if args.json:
        print(json.dumps({"contract_version": PUBLIC_CONTRACT_VERSION, "results": results}, indent=2, sort_keys=True))
    else:
        _print_human(results)

    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
