"""Static HTML Review Room renderer."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Any

from .scenarios import GENERATED_DIR, ROOT_DIR
from .trust import build_review_room


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _pill(label: str, value: Any, *, tone: str = "neutral") -> str:
    return f'<span class="pill {tone}"><span>{_e(label)}</span><strong>{_e(value)}</strong></span>'


def _command_block(commands: list[str]) -> str:
    lines = "\n".join(_e(command) for command in commands)
    return f"<pre><code>{lines}</code></pre>"


def _scenario_rows(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        risk_tone = {
            "low": "ok",
            "medium": "warn",
            "high": "warn",
            "critical": "danger",
        }[item["highest_risk"]]
        validation_tone = "ok" if item["scoped_validation_review"] else "danger"
        rows.append(
            "<tr>"
            f"<td data-label=\"Scenario\"><strong>{_e(item['scenario'])}</strong><span>{_e(item['agent_name'])}</span></td>"
            f"<td data-label=\"Risk\">{_pill('risk', item['highest_risk'], tone=risk_tone)}</td>"
            f"<td data-label=\"Validation\">{_pill('validation', item['scoped_validation_review'], tone=validation_tone)}</td>"
            f"<td data-label=\"Production\">{_pill('production', item['production_access'], tone='danger' if item['production_access'] else 'ok')}</td>"
            f"<td data-label=\"Systems\">{_e(', '.join(item['requested_systems']))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _policy_gate_cards(results: dict[str, dict[str, Any]]) -> str:
    cards = []
    for scenario, result in results.items():
        tone = "danger" if result["decision"] == "BLOCKED" else "ok"
        rules = ", ".join(result["triggered_rule_ids"])
        cards.append(
            '<article class="panel compact">'
            f"<h3>{_e(scenario)}</h3>"
            f"{_pill('decision', result['decision'], tone=tone)}"
            f"<p>{_e(result['reason'])}</p>"
            f"<small>Rules: {_e(rules)}</small>"
            "</article>"
        )
    return "\n".join(cards)


def _adapter_cards(providers: dict[str, dict[str, Any]]) -> str:
    cards = []
    for provider, summary in providers.items():
        cards.append(
            '<article class="panel compact">'
            f"<h3>{_e(provider)}</h3>"
            f"{_pill('status', ', '.join(summary['statuses']), tone='ok')}"
            f"{_pill('would execute', summary['would_execute'], tone='danger' if summary['would_execute'] else 'ok')}"
            f"{_pill('can approve', summary['can_approve_access'], tone='danger' if summary['can_approve_access'] else 'ok')}"
            "</article>"
        )
    return "\n".join(cards)


def _list_items(items: list[str], *, limit: int | None = None) -> str:
    visible = items if limit is None else items[:limit]
    rendered = "".join(f"<li>{_e(item)}</li>" for item in visible)
    if limit is not None and len(items) > limit:
        rendered += f"<li>{len(items) - limit} more in JSON</li>"
    return rendered


def _safety_grid(items: dict[str, Any]) -> str:
    cells = []
    for key, value in items.items():
        bad_true = key in {"approval_granted", "production_access_granted", "external_writes_enabled", "packet_state_mutation"}
        tone = "danger" if bool(value) and bad_true else "ok"
        cells.append(
            '<div class="metric">'
            f"<span>{_e(key.replace('_', ' '))}</span>"
            f"<strong>{_e(value)}</strong>"
            f'<i class="{tone}"></i>'
            "</div>"
        )
    return "\n".join(cells)


def _count_label(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def render_review_room_html(review_room: dict[str, Any]) -> str:
    """Render the static Review Room HTML artifact."""
    gate_results = review_room["policy_gate_status"]["results"]
    adapter_status = review_room["sponsor_adapter_status"]["providers"]
    envelope = review_room["permission_envelope"]
    proof = review_room["proof_debt_summary"]
    artifact_links = "".join(f"<li><code>{_e(item)}</code></li>" for item in review_room["first_artifacts_to_inspect"])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(review_room["title"])}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8f5;
      --surface: #ffffff;
      --ink: #17211d;
      --muted: #5f6e67;
      --line: #d9ded8;
      --teal: #08766f;
      --green: #20724f;
      --amber: #a66412;
      --red: #b63535;
      --blue: #315e9f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 44px; }}
    header {{
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 8px;
      padding: 24px;
      display: grid;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 48px); line-height: 1.05; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }}
    p {{ margin: 0; color: var(--muted); max-width: 76ch; }}
    code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    pre {{ margin: 0; white-space: pre-wrap; border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: #101a17; color: #e9f2ed; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ font-size: 12px; color: var(--muted); text-transform: uppercase; }}
    td span {{ display: block; color: var(--muted); }}
    ul {{ margin: 0; padding-left: 18px; }}
    li, code {{ overflow-wrap: anywhere; }}
    small {{ display: block; color: var(--muted); margin-top: 10px; }}
    .hash {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .grid {{ display: grid; gap: 16px; }}
    .two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .four {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .section {{ margin-top: 18px; }}
    .panel {{
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 8px;
      padding: 18px;
      min-width: 0;
    }}
    .compact {{ display: grid; gap: 10px; align-content: start; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      max-width: 100%;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 10px;
      background: #f9fbf7;
      color: var(--muted);
      font-size: 12px;
    }}
    .pill strong {{ color: var(--ink); overflow-wrap: anywhere; }}
    .pill span {{ display: inline; color: inherit; }}
    .pill.ok {{ border-color: #b7d7c2; background: #edf7ef; }}
    .pill.warn {{ border-color: #e1c28e; background: #fff7e7; }}
    .pill.danger {{ border-color: #e6b0aa; background: #fff0ee; }}
    .metric {{ position: relative; border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--surface); min-height: 86px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; margin-bottom: 8px; }}
    .metric strong {{ font-size: 18px; overflow-wrap: anywhere; }}
    .metric i {{ position: absolute; right: 12px; top: 12px; width: 10px; height: 10px; border-radius: 50%; background: var(--green); }}
    .metric i.danger {{ background: var(--red); }}
    .callout {{ border-left: 4px solid var(--teal); background: #eff8f4; }}
    .dangerText {{ color: var(--red); font-weight: 700; }}
    .ownerLine {{ display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding: 10px 0; }}
    .ownerLine:last-child {{ border-bottom: 0; }}
    @media (max-width: 840px) {{
      main {{ width: min(100vw - 20px, 1180px); padding-top: 10px; }}
      header {{ padding: 18px; }}
      .two, .three, .four {{ grid-template-columns: 1fr; }}
      table, thead, tbody, tr, th, td {{ display: block; width: 100%; }}
      thead {{ display: none; }}
      tr {{ border-bottom: 1px solid var(--line); padding: 10px 0; }}
      tr:last-child {{ border-bottom: 0; }}
      td {{
        border-bottom: 0;
        padding: 8px 0;
        display: flex;
        justify-content: space-between;
        gap: 12px;
      }}
      td::before {{
        content: attr(data-label);
        flex: 0 0 88px;
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
      }}
      td:first-child {{ display: block; }}
      td:first-child::before {{ display: block; margin-bottom: 4px; }}
      th:nth-child(5), td:nth-child(5) {{ display: none; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>{_e(review_room["title"])}</h1>
      <p>{_e(review_room["headline"])}</p>
    </div>
    <div class="hash">
      {_pill("Trust Receipt", review_room["derived_from_trust_receipt_id"], tone="neutral")}
      {_pill("Hash", review_room["trust_receipt_hash"], tone="ok")}
      {_pill("Mode", "offline deterministic", tone="neutral")}
      {_pill("External writes", review_room["safety_state"]["external_writes_enabled"], tone="ok")}
    </div>
  </header>

  <section class="section panel">
    <h2>Scenario Matrix</h2>
    <table>
      <thead><tr><th>Scenario</th><th>Risk</th><th>Validation</th><th>Production</th><th>Systems</th></tr></thead>
      <tbody>{_scenario_rows(review_room["scenario_matrix"])}</tbody>
    </table>
  </section>

  <section class="section">
    <h2>Policy Gate Status</h2>
    <div class="grid three">
      {_policy_gate_cards(gate_results)}
    </div>
  </section>

  <section class="section">
    <h2>Sponsor Adapter Status</h2>
    <div class="grid four">
      {_adapter_cards(adapter_status)}
    </div>
  </section>

  <section class="section grid two">
    <article class="panel">
      <h2>Permission Envelope</h2>
      <h3>Allowed For Validation</h3>
      <ul>{_list_items(envelope["allowed_for_validation"], limit=5)}</ul>
      <h3>Dry-Run Only</h3>
      <ul>{_list_items(envelope["dry_run_only"], limit=5)}</ul>
    </article>
    <article class="panel">
      <h2>Blocked Surface</h2>
      <h3>Blocked In Validation</h3>
      <ul>{_list_items(envelope["blocked_in_validation"], limit=8)}</ul>
      <h3>Never Allowed In Public Demo</h3>
      <ul>{_list_items(envelope["never_allowed_in_public_demo"])}</ul>
    </article>
  </section>

  <section class="section grid two">
    <article class="panel">
      <h2>Proof Debt</h2>
      <p>Open proof items: <strong>{_e(proof["open_items"])}</strong></p>
      <ul>{_list_items(proof["owners"])}</ul>
    </article>
    <article class="panel">
      <h2>Reviewer Routing</h2>
      {''.join(f'<div class="ownerLine"><strong>{_e(item["owner"])}</strong><span>{_e(_count_label(item["gate_count"], "gate", "gates"))} across {_e(_count_label(item["scenario_count"], "scenario", "scenarios"))}</span></div>' for item in review_room["reviewer_routing_summary"])}
    </article>
  </section>

  <section class="section grid four">
    {_safety_grid(review_room["safety_state"])}
  </section>

  <section class="section grid two">
    <article class="panel callout">
      <h2>Private Boundary</h2>
      <p>{_e(review_room["private_boundary"]["principle"])}</p>
      <p>Private source exposed: <strong>{_e(review_room["private_boundary"]["private_source_exposed"])}</strong></p>
    </article>
    <article class="panel">
      <h2>Review Commands</h2>
      {_command_block(review_room["copy_paste_commands"])}
    </article>
  </section>

  <section class="section panel">
    <h2>First Artifacts To Inspect</h2>
    <ul>{artifact_links}</ul>
  </section>
</main>
</body>
</html>
"""


def write_review_room_html(output_dir: Path = GENERATED_DIR) -> Path:
    """Write the static Review Room HTML artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "review_room.html"
    path.write_text(render_review_room_html(build_review_room()), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.review_room",
        description="Generate the static InferenceAtlas Review Room HTML artifact.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory where review_room.html should be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = write_review_room_html(args.output_dir)
    print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
