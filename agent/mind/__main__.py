"""CLI: python -m agent.mind [step|run|e2e|project|init]"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

from agent.scenarios import SCENARIOS

from .model import Mind
from .project import project_mind
from .store import load_mind, save_mind, state_dir
from .transition import init_mind, step


def _cmd_init(args: argparse.Namespace) -> int:
    for scenario in _scenarios(args):
        mind = init_mind(scenario)
        path = save_mind(mind)
        print(f"initialized {scenario} -> {path}")
    return 0


def _cmd_step(args: argparse.Namespace) -> int:
    for scenario in _scenarios(args):
        mind = load_mind(scenario) or init_mind(scenario)
        mind = step(mind, allow_cortex=not args.no_cortex)
        save_mind(mind)
        top = mind.top_tensions(1)
        t = top[0] if top else None
        print(
            f"{scenario} tick={mind.tick} "
            f"tensions={len(mind.internal.get('tensions', []))} "
            f"top={t.type}:{t.strength:.2f}" if t else f"{scenario} tick={mind.tick} tensions=0"
        )
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    print(f"Mind loop running (interval={args.interval}s). Ctrl-C to stop.")
    print(f"State dir: {state_dir()}")
    try:
        while True:
            for scenario in SCENARIOS:
                mind = load_mind(scenario) or init_mind(scenario)
                mind = step(mind, allow_cortex=not args.no_cortex)
                save_mind(mind)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


def _cmd_project(args: argparse.Namespace) -> int:
    out = Path(args.output)
    errors_total = []
    for scenario in _scenarios(args):
        mind = load_mind(scenario)
        if mind is None:
            print(f"skip {scenario}: no mind state (run init first)")
            continue
        paths, errors = project_mind(mind, out)
        for path in paths:
            print(path)
        if errors:
            errors_total.extend(errors)
            print(f"contract errors for {scenario}: {len(errors)}", file=sys.stderr)
    return 1 if errors_total else 0


def _cmd_e2e(args: argparse.Namespace) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ia_mind_e2e_"))
    try:
        ok = True
        for scenario in SCENARIOS:
            mind = init_mind(scenario)
            mind = step(mind, allow_cortex=False)
            mind = step(mind, allow_cortex=False)
            tensions = mind.internal.get("tensions", [])
            if not tensions and len(mind.packet.get("missing_proof", [])) > 0:
                print(f"FAIL {scenario}: expected tensions when proof debt exists", file=sys.stderr)
                ok = False
            if args.with_cortex:
                mind = step(mind, allow_cortex=True)
            paths, errors = project_mind(mind, tmp)
            if errors:
                print(f"FAIL {scenario}: contract validation", file=sys.stderr)
                for err in errors[:5]:
                    print(f"  {err}", file=sys.stderr)
                ok = False
            else:
                top = mind.top_tensions(1)
                t = top[0] if top else None
                posture = mind.packet.get("approval_posture", {})
                print(
                    f"OK {scenario} tick={mind.tick} "
                    f"tensions={len(tensions)} "
                    f"top={t.type if t else 'none'} "
                    f"production_access={posture.get('production_access')}"
                )
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _scenarios(args: argparse.Namespace) -> list:
    if args.scenario:
        if args.scenario not in SCENARIOS:
            raise SystemExit(f"unknown scenario: {args.scenario}")
        return [args.scenario]
    return list(SCENARIOS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.mind",
        description="Mind state-transition runtime (Mind(t+1) = F(Mind(t))).",
    )
    parser.add_argument("--scenario", choices=list(SCENARIOS), help="Limit to one scenario")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize mind state for scenario(s)")

    p_step = sub.add_parser("step", help="Run one transition tick")
    p_step.add_argument("--no-cortex", action="store_true", help="Skip LLM cortex")

    p_run = sub.add_parser("run", help="Continuous transition loop")
    p_run.add_argument("--interval", type=float, default=1.0, help="Seconds between ticks")
    p_run.add_argument("--no-cortex", action="store_true", help="Skip LLM cortex")

    p_project = sub.add_parser("project", help="Write packet/brief projections")
    p_project.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[2] / "examples" / "mind_runtime"),
        help="Output directory",
    )

    p_e2e = sub.add_parser("e2e", help="Offline end-to-end validation for all scenarios")
    p_e2e.add_argument(
        "--with-cortex",
        action="store_true",
        help="Run an extra tick with cortex if LLM_API_KEY is set",
    )

    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(args)
    if args.command == "step":
        return _cmd_step(args)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "project":
        return _cmd_project(args)
    if args.command == "e2e":
        return _cmd_e2e(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
