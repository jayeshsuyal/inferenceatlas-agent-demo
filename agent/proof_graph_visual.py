"""HTML visual surface for the public ProofGraph."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Any

from .proof_graph import DEFAULT_SCENARIO, build_proof_graph_for_scenario
from .scenarios import GENERATED_DIR, SCENARIOS


PROOF_GRAPH_VISUAL_FILE = "proofgraph.html"
PROOF_GRAPH_VISUAL_TITLE = "InferenceAtlas ProofGraph"
PROOF_GRAPH_VISUAL_SUBTITLE = (
    "The packet authority layer downstream systems trust before AI moves."
)
PROOF_GRAPH_SAFETY_BANNER = (
    "Sponsors contribute proof only - IA keeps the packet locked - "
    "no approval - no writes - no verdict mutation"
)


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _provider_count(graph: dict[str, Any], provider: str) -> int:
    return sum(1 for node in graph["proof_nodes"] if node["provider"] == provider)


def _provider_line(graph: dict[str, Any], provider: str) -> str:
    return f"{_provider_count(graph, provider)} proof nodes"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _stat(label: str, value: Any, *, ok: bool = False) -> str:
    cls = "stat ok" if ok else "stat"
    return f'<span class="{cls}"><strong>{_escape(value)}</strong><span>{_escape(label)}</span></span>'


def _metric(label: str, value: Any) -> str:
    return f"<p><span>{_escape(label)}</span><strong>{_escape(value)}</strong></p>"


def _sponsor_card(
    *,
    name: str,
    accent: str,
    count: str,
    primary: str,
    secondary: str,
) -> str:
    return f"""
          <article class="sponsor-card {accent}">
            <div class="sponsor-heading"><span></span><h3>{_escape(name)}</h3></div>
            <strong>{_escape(count)}</strong>
            <p>{_escape(primary)}</p>
            <small>{_escape(secondary)}</small>
          </article>"""


def _downstream_card(title: str, subtitle: str) -> str:
    return f"""
          <article class="downstream-card">
            <h3>{_escape(title)}</h3>
            <p>{_escape(subtitle)}</p>
          </article>"""


def _review_run_node_card(node: dict[str, Any]) -> str:
    return f"""
        <article class="review-node { _escape(node.get('node_type', 'node')) }">
          <span>{_escape(node.get('node_type', 'node'))}</span>
          <h2>{_escape(node.get('label', 'unknown'))}</h2>
          <p>{_escape(node.get('summary', ''))}</p>
          <strong>{_escape(node.get('status', 'unknown'))}</strong>
        </article>"""


def _review_run_edge_row(edge: dict[str, Any]) -> str:
    can_change = "yes" if edge.get("can_change_packet_verdict") else "no"
    return f"""
          <p>
            <span>{_escape(edge.get('from_node_id', 'source'))} -> {_escape(edge.get('to_node_id', 'target'))}</span>
            <strong>{_escape(edge.get('label', 'edge'))} / can change packet: {_escape(can_change)}</strong>
          </p>"""


def _review_run_fact(label: str, value: Any) -> str:
    return f"<p><span>{_escape(label)}</span><strong>{_escape(value)}</strong></p>"


def _svg_lines(value: Any, *, max_chars: int = 32, max_lines: int = 3) -> list[str]:
    words = str(value).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) == max_lines and words:
        joined = " ".join(lines)
        if len(joined) < len(str(value)) and not lines[-1].endswith("..."):
            lines[-1] = f"{lines[-1][: max(0, max_chars - 3)]}..."
    return lines


def _svg_text_block(
    text: Any,
    *,
    x: int,
    y: int,
    max_chars: int = 32,
    max_lines: int = 3,
    size: int = 16,
    fill: str = "#a7adb8",
    weight: int = 500,
    line_height: int = 21,
) -> str:
    lines = _svg_lines(text, max_chars=max_chars, max_lines=max_lines)
    tspans = "\n".join(
        f'<tspan x="{x}" dy="{0 if index == 0 else line_height}">{_escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}">{tspans}</text>'


def _svg_stat(label: str, value: Any, *, x: int, y: int, width: int = 160, ok: bool = False) -> str:
    stroke = "#4ade80" if ok else "#2b3442"
    fill = "#10261a" if ok else "#12161e"
    value_fill = "#bbf7d0" if ok else "#f4f5f7"
    return f"""
      <g>
        <rect x="{x}" y="{y}" width="{width}" height="58" rx="10" fill="{fill}" stroke="{stroke}" />
        <text x="{x + width / 2:.0f}" y="{y + 24}" text-anchor="middle" fill="{value_fill}" font-size="18" font-weight="760">{_escape(value)}</text>
        <text x="{x + width / 2:.0f}" y="{y + 43}" text-anchor="middle" fill="#a7adb8" font-size="11" font-weight="760">{_escape(label.upper())}</text>
      </g>"""


def _svg_node(
    *,
    title: Any,
    summary: Any,
    status: Any,
    x: int,
    y: int,
    width: int,
    accent: str,
    title_chars: int = 24,
) -> str:
    return f"""
      <g>
        <rect x="{x}" y="{y}" width="{width}" height="126" rx="12" fill="#12161e" stroke="#2b3442" />
        <rect x="{x}" y="{y}" width="5" height="126" rx="2" fill="{accent}" />
        {_svg_text_block(title, x=x + 18, y=y + 33, max_chars=title_chars, max_lines=2, size=20, fill="#f4f5f7", weight=760, line_height=23)}
        {_svg_text_block(summary, x=x + 18, y=y + 71, max_chars=28, max_lines=2, size=13, fill="#a7adb8", weight=500, line_height=17)}
        {_svg_text_block(status, x=x + 18, y=y + 109, max_chars=26, max_lines=1, size=13, fill=accent, weight=760, line_height=16)}
      </g>"""


def render_review_run_proof_graph_svg(graph: dict[str, Any]) -> str:
    """Render a deterministic, downloadable SVG for one ReviewRun ProofGraph."""
    run_id = graph.get("generated_from_run_id") or graph.get("generated_from", {}).get("run_id") or "unknown"
    selected_repo = graph.get("selected_repo") or graph.get("generated_from", {}).get("selected_repo") or "no repo selected"
    packet = graph.get("packet_reference") or {}
    movement = graph.get("movement_classes") or {}
    proof_counts = graph.get("proof_counts") or {}
    revision_id = packet.get("revision_id") or "not generated"
    portkey_state = graph.get("portkey_state") or "No packet"
    zero_writes = bool(graph.get("zero_writes"))
    content_hash = graph.get("content_hash") or "missing"
    nodes = graph.get("nodes", [])
    accents = {
        "repo": "#6aa6ff",
        "packet": "#f2b84b",
        "proof": "#24e0a4",
        "downstream": "#7cb7ff",
    }
    node_svg = []
    node_width = 214
    start_x = 70
    gap = 22
    for index, node in enumerate(nodes[:5]):
        node_svg.append(
            _svg_node(
                title=node.get("label", "unknown"),
                summary=node.get("summary", ""),
                status=node.get("status", "unknown"),
                x=start_x + index * (node_width + gap),
                y=286,
                width=node_width,
                accent=accents.get(node.get("node_type"), "#24e0a4"),
            )
        )
        if index < min(len(nodes[:5]), 5) - 1:
            arrow_x = start_x + index * (node_width + gap) + node_width + 6
            node_svg.append(
                f'<path d="M {arrow_x} 349 H {arrow_x + gap - 10}" stroke="#3b4657" stroke-width="2" marker-end="url(#arrow)" />'
            )
    allowed = ", ".join(movement.get("allowed") or []) or "none"
    review = ", ".join(movement.get("review_required") or []) or "none"
    blocked = ", ".join(movement.get("blocked") or []) or "none"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-label="InferenceAtlas ReviewRun ProofGraph export">
  <title>InferenceAtlas ReviewRun ProofGraph</title>
  <desc>run_id: {_escape(run_id)}; packet: {_escape(packet.get("packet_id") or "not generated")}; revision: {_escape(revision_id)}; content_hash: {_escape(content_hash)}; generated from current ReviewRun, not a screenshot.</desc>
  <metadata>{_escape(content_hash)}</metadata>
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#090b10" />
      <stop offset="1" stop-color="#05070b" />
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 H 0 V 40" fill="none" stroke="#111827" stroke-width="1" />
    </pattern>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#3b4657" />
    </marker>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)" />
  <rect x="36" y="36" width="1208" height="648" rx="18" fill="url(#grid)" stroke="#2b3442" />
  <text x="70" y="94" fill="#24e0a4" font-size="13" font-weight="780">REVIEWRUN PROOFGRAPH EXPORT</text>
  <text x="70" y="148" fill="#f4f5f7" font-size="48" font-weight="780">InferenceAtlas ReviewRun ProofGraph</text>
  {_svg_text_block(f"Generated from run_id {run_id}. Packet remains authority; sponsors contribute proof only.", x=70, y=184, max_chars=96, max_lines=2, size=18, fill="#a7adb8", line_height=24)}
  {_svg_stat("state", graph.get("status_label") or graph.get("graph_state") or "unknown", x=690, y=78, width=160)}
  {_svg_stat("revision", revision_id, x=866, y=78, width=178)}
  {_svg_stat("writes", "zero" if zero_writes else "unknown", x=1060, y=78, width=126, ok=zero_writes)}
  <rect x="70" y="224" width="1110" height="36" rx="8" fill="#10261a" stroke="#4ade80" />
  <text x="92" y="247" fill="#bbf7d0" font-size="16" font-weight="760">No approval / no writes / no mutation - zero writes</text>
  {''.join(node_svg)}
  <rect x="70" y="458" width="356" height="130" rx="12" fill="#12161e" stroke="#2b3442" />
  <text x="94" y="490" fill="#f4f5f7" font-size="18" font-weight="760">Current Read</text>
  {_svg_text_block(f"Selected repo: {selected_repo}", x=94, y=522, max_chars=42, max_lines=2, size=14, fill="#a7adb8", line_height=18)}
  {_svg_text_block(f"Packet: {packet.get('packet_id') or 'not generated'}", x=94, y=566, max_chars=42, max_lines=1, size=14, fill="#a7adb8", line_height=18)}
  <rect x="462" y="458" width="356" height="130" rx="12" fill="#12161e" stroke="#2b3442" />
  <text x="486" y="490" fill="#f4f5f7" font-size="18" font-weight="760">Movement Scope</text>
  {_svg_text_block(f"Allowed: {allowed}", x=486, y=522, max_chars=46, max_lines=1, size=14, fill="#71d58b", line_height=18)}
  {_svg_text_block(f"Review: {review}", x=486, y=546, max_chars=46, max_lines=1, size=14, fill="#f2b84b", line_height=18)}
  {_svg_text_block(f"Still blocked: {blocked}", x=486, y=570, max_chars=46, max_lines=1, size=14, fill="#ff786f", line_height=18)}
  <rect x="854" y="458" width="326" height="130" rx="12" fill="#12161e" stroke="#2b3442" />
  <text x="878" y="490" fill="#f4f5f7" font-size="18" font-weight="760">Proof And Portkey</text>
  {_svg_text_block(f"Proof: {proof_counts.get('attached', 0)} attached / {proof_counts.get('missing', 0)} missing", x=878, y=522, max_chars=38, max_lines=1, size=14, fill="#a7adb8", line_height=18)}
  {_svg_text_block(f"Portkey: {portkey_state}", x=878, y=546, max_chars=38, max_lines=1, size=14, fill="#7cb7ff", line_height=18)}
  {_svg_text_block(f"Hash: {content_hash}", x=878, y=570, max_chars=38, max_lines=1, size=14, fill="#a7adb8", line_height=18)}
  <text x="70" y="640" fill="#788191" font-size="13">The ProofGraph is generated from the current ReviewRun, not a screenshot. Export is read-only.</text>
</svg>"""


def render_proof_graph_svg(graph: dict[str, Any]) -> str:
    """Render a deterministic SVG for the public sponsor ProofGraph."""
    counts = graph.get("node_counts") or {}
    packet = graph.get("packet_reference") or {}
    safety = graph.get("safety_boundary") or {}
    invariants = graph.get("invariants") or {}
    zero_writes = (
        safety.get("executes_external_writes") is False
        and safety.get("mutates_production") is False
        and invariants.get("all_nodes_non_mutating") is True
    )
    sponsor_rows = [
        ("Tavily", _provider_line(graph, "tavily"), "proof contributor - cannot approve", "#60a5fa"),
        ("Composio", _provider_line(graph, "composio"), "dry-run blast radius - cannot execute", "#818cf8"),
        ("OpenClaw", _provider_line(graph, "openclaw"), "runtime trace - cannot approve", "#67e8f9"),
        ("Nebius", _provider_line(graph, "nebius"), "reviewer synthesis - cannot mutate", "#a78bfa"),
    ]
    sponsor_svg = []
    for index, (name, count, summary, color) in enumerate(sponsor_rows):
        y = 220 + index * 88
        sponsor_svg.append(
            f"""
            <g>
              <rect x="474" y="{y}" width="276" height="68" rx="12" fill="#12161e" stroke="{color}" />
              <circle cx="496" cy="{y + 23}" r="6" fill="{color}" />
              <text x="512" y="{y + 29}" fill="#f4f5f7" font-size="18" font-weight="760">{_escape(name)}</text>
              <text x="512" y="{y + 52}" fill="#a7adb8" font-size="13">{_escape(count)} - {_escape(summary)}</text>
              <path d="M 750 {y + 34} H 812" stroke="#f59e0b" stroke-width="2" />
            </g>"""
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-label="InferenceAtlas ProofGraph export">
  <title>InferenceAtlas ProofGraph</title>
  <desc>packet: {_escape(packet.get("packet_id", "unknown"))}; graph: {_escape(graph.get("graph_id", "unknown"))}; content_hash: {_escape(graph.get("content_hash", "missing"))}; generated ProofGraph export.</desc>
  <metadata>{_escape(graph.get("content_hash", "missing"))}</metadata>
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#07101f" />
      <stop offset="1" stop-color="#05070b" />
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 H 0 V 40" fill="none" stroke="#162033" stroke-width="1" />
    </pattern>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)" />
  <rect x="50" y="40" width="1180" height="628" rx="18" fill="url(#grid)" stroke="#334155" />
  <text x="88" y="106" fill="#f8fafc" font-size="58" font-weight="780">InferenceAtlas ProofGraph</text>
  <text x="90" y="142" fill="#a9b5c8" font-size="20">{PROOF_GRAPH_VISUAL_SUBTITLE}</text>
  {_svg_stat("proof nodes", counts.get("proof", 0), x=760, y=88, width=150)}
  {_svg_stat("edges", counts.get("edge", 0), x=930, y=88, width=130)}
  {_svg_stat("writes", "zero" if zero_writes else "unknown", x=1080, y=88, width=120, ok=zero_writes)}
  <rect x="114" y="310" width="220" height="134" rx="18" fill="#12161e" stroke="#334155" />
  <text x="164" y="364" fill="#f8fafc" font-size="26" font-weight="760">Agent Request</text>
  <text x="154" y="398" fill="#a9b5c8" font-size="16">raw intent is not trusted</text>
  <path d="M 334 377 H 420" stroke="#64748b" stroke-width="2" />
  <rect x="812" y="270" width="280" height="220" rx="20" fill="#fbbf24" stroke="#f59e0b" stroke-width="3" />
  <text x="850" y="342" fill="#43270b" font-size="38" font-weight="780">IA Packet</text>
  <text x="850" y="384" fill="#43270b" font-size="38" font-weight="780">Authority</text>
  <text x="852" y="424" fill="#713f12" font-size="17" font-weight="700">verdict - proof lock - routing</text>
  {''.join(sponsor_svg)}
  <rect x="110" y="560" width="1060" height="40" rx="10" fill="#10261a" stroke="#4ade80" />
  <text x="640" y="586" text-anchor="middle" fill="#dcfce7" font-size="18" font-weight="760">{PROOF_GRAPH_SAFETY_BANNER}</text>
  <text x="90" y="638" fill="#64748b" font-size="13">packet: {_escape(packet.get("packet_id", "unknown"))} - graph: {_escape(graph.get("graph_id", "unknown"))} - hash: {_escape(graph.get("content_hash", "missing"))}</text>
</svg>"""


def render_proof_graph_html(graph: dict[str, Any]) -> str:
    """Render a data-backed, no-JS ProofGraph page."""
    counts = graph["node_counts"]
    packet = graph["packet_reference"]
    packet_node = graph["packet_node"]
    safety = graph["safety_boundary"]
    invariants = graph["invariants"]
    tavily = graph.get("tavily_evidence", {})
    composio = graph.get("composio_blast_radius", {})
    openclaw = graph.get("openclaw_runtime_trace", {})
    nebius = graph.get("nebius_reviewer_synthesis", {})
    portkey = graph.get("portkey_guardrail", {})
    zero_writes = (
        safety["executes_external_writes"] is False
        and safety["mutates_production"] is False
        and invariants["all_nodes_non_mutating"] is True
    )
    source_mode = "offline deterministic"
    if any(node["api_call_made"] for node in graph["proof_nodes"]):
        source_mode = "mixed live proof"

    sponsor_cards = "\n".join(
        [
            _sponsor_card(
                name="Tavily",
                accent="tavily",
                count=_provider_line(graph, "tavily"),
                primary=(
                    f"{tavily.get('query_count', 0)} evidence questions, "
                    f"{tavily.get('total_planned_searches', 0)} planned searches"
                ),
                secondary="proof contributor - cannot approve",
            ),
            _sponsor_card(
                name="Composio",
                accent="composio",
                count=_provider_line(graph, "composio"),
                primary=(
                    f"{composio.get('blocked_action_count', 0)} blocked actions, "
                    f"max {composio.get('max_risk_level', 'unknown')}"
                ),
                secondary="dry-run blast radius - cannot execute",
            ),
            _sponsor_card(
                name="OpenClaw",
                accent="openclaw",
                count=_provider_line(graph, "openclaw"),
                primary=(
                    f"{openclaw.get('checkpoint_count', 0)} checkpoints, "
                    f"{openclaw.get('blocked_event_count', 0)} blocked events"
                ),
                secondary="runtime trace - cannot approve",
            ),
            _sponsor_card(
                name="Nebius",
                accent="nebius",
                count=_provider_line(graph, "nebius"),
                primary=(
                    f"{nebius.get('locked_field_count', 0)} locked fields, "
                    f"{nebius.get('required_anchor_count', 0)} anchors kept"
                ),
                secondary="reviewer synthesis - cannot mutate",
            ),
        ]
    )
    downstream_cards = "\n".join(
        [
            _downstream_card("Portkey Gate", f"{portkey.get('webhook_path', '/api/portkey/guardrail')}"),
            _downstream_card("CI / Deploy", "release check"),
            _downstream_card("Verification", "packet id - hash - verdict - revision"),
            _downstream_card("Finance", "spend review"),
            _downstream_card("Security / Legal", "human owners"),
        ]
    )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{PROOF_GRAPH_VISUAL_TITLE}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07101f;
      --panel: #0c1628;
      --panel-strong: #101b31;
      --line: #334155;
      --line-soft: rgba(148, 163, 184, 0.2);
      --text: #f8fafc;
      --muted: #a9b5c8;
      --blue: #60a5fa;
      --cyan: #67e8f9;
      --violet: #a78bfa;
      --amber: #f59e0b;
      --amber-light: #fde68a;
      --green: #4ade80;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    main {{
      width: min(1480px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 40px 0;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 24px;
      align-items: end;
      margin-bottom: 28px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2.2rem, 5vw, 4.4rem);
      line-height: 1;
      font-weight: 740;
    }}
    .lede {{
      margin: 0;
      color: var(--muted);
      font-size: clamp(1rem, 2vw, 1.35rem);
      max-width: 850px;
    }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 12px;
    }}
    .actions {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 12px;
    }}
    .actions a {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      border: 1px solid rgba(148, 163, 184, 0.3);
      border-radius: 999px;
      padding: 0 14px;
      color: var(--text);
      background: rgba(15, 23, 42, 0.72);
      text-decoration: none;
      font-size: 0.82rem;
      font-weight: 760;
    }}
    .actions a.primary {{
      border-color: rgba(74, 222, 128, 0.56);
      color: #bbf7d0;
      background: rgba(20, 83, 45, 0.35);
    }}
    .stat {{
      min-width: 150px;
      border: 1px solid rgba(148, 163, 184, 0.28);
      background: rgba(15, 23, 42, 0.72);
      border-radius: 999px;
      padding: 10px 18px;
      text-align: center;
      color: var(--muted);
    }}
    .stat strong {{
      display: block;
      color: var(--text);
      font-size: 1rem;
    }}
    .stat span {{
      display: block;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .stat.ok {{
      border-color: rgba(74, 222, 128, 0.52);
      background: rgba(20, 83, 45, 0.35);
    }}
    .stat.ok strong {{ color: #bbf7d0; }}
    .stage {{
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 28px;
      background:
        linear-gradient(var(--line-soft) 1px, transparent 1px),
        linear-gradient(90deg, var(--line-soft) 1px, transparent 1px),
        rgba(15, 23, 42, 0.58);
      background-size: 32px 32px;
      padding: 52px 44px 34px;
      box-shadow: 0 24px 90px rgba(0, 0, 0, 0.35);
    }}
    .flow {{
      display: grid;
      grid-template-columns: 1.1fr 1.25fr 1.45fr 1.5fr 1.18fr;
      gap: 28px;
      align-items: center;
      min-height: 610px;
    }}
    .node, .collector, .packet, .sponsor-card, .downstream-card {{
      border: 1px solid rgba(148, 163, 184, 0.35);
      background: rgba(15, 23, 42, 0.88);
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.24);
    }}
    .node, .collector {{
      border-radius: 22px;
      padding: 28px;
      text-align: center;
    }}
    .node h2, .collector h2, .packet h2, .downstream-card h3, .sponsor-card h3 {{
      margin: 0;
      line-height: 1.05;
    }}
    .node p, .collector p, .packet p, .downstream-card p, .sponsor-card p {{
      margin: 12px 0 0;
      color: var(--muted);
      line-height: 1.5;
    }}
    .collector {{
      border-radius: 26px;
      padding: 44px 26px;
    }}
    .collector h2 {{
      font-size: clamp(1.7rem, 3vw, 2.45rem);
    }}
    .connector-line {{
      width: 100%;
      height: 2px;
      background: linear-gradient(90deg, transparent, #64748b, transparent);
      margin: 20px 0;
    }}
    .sponsors {{
      display: grid;
      gap: 20px;
    }}
    .sponsor-card {{
      position: relative;
      border-radius: 18px;
      padding: 20px 22px;
    }}
    .sponsor-card::before {{
      content: "";
      position: absolute;
      left: -34px;
      top: 50%;
      width: 34px;
      border-top: 2px dashed rgba(96, 165, 250, 0.75);
    }}
    .sponsor-card::after {{
      content: "";
      position: absolute;
      right: -38px;
      top: 50%;
      width: 38px;
      border-top: 3px solid rgba(245, 158, 11, 0.88);
    }}
    .sponsor-heading {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .sponsor-heading span {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--blue);
      box-shadow: 0 0 0 5px rgba(96, 165, 250, 0.12);
    }}
    .sponsor-card strong {{
      display: block;
      margin-top: 12px;
      font-size: 1.12rem;
      color: #dbeafe;
    }}
    .sponsor-card small {{
      display: block;
      margin-top: 8px;
      color: #93c5fd;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .sponsor-card.tavily {{ border-color: rgba(96, 165, 250, 0.82); }}
    .sponsor-card.composio {{ border-color: rgba(129, 140, 248, 0.78); }}
    .sponsor-card.openclaw {{ border-color: rgba(103, 232, 249, 0.78); }}
    .sponsor-card.nebius {{ border-color: rgba(167, 139, 250, 0.78); }}
    .packet {{
      position: relative;
      border: 3px solid rgba(245, 158, 11, 0.96);
      border-radius: 26px;
      padding: 42px 34px;
      min-height: 260px;
      display: grid;
      align-content: center;
      background: linear-gradient(135deg, var(--amber-light), #fb923c);
      color: #43270b;
      box-shadow: 0 0 0 8px rgba(245, 158, 11, 0.12), 0 24px 86px rgba(245, 158, 11, 0.28);
    }}
    .packet h2 {{
      font-size: clamp(2rem, 4vw, 3.3rem);
      font-weight: 760;
    }}
    .packet p {{
      color: #713f12;
      font-weight: 650;
    }}
    .packet .mini {{
      margin-top: 18px;
      display: grid;
      gap: 8px;
    }}
    .packet .mini p {{
      margin: 0;
      display: flex;
      justify-content: space-between;
      gap: 14px;
      color: #78350f;
      font-size: 0.94rem;
    }}
    .downstream {{
      display: grid;
      gap: 24px;
    }}
    .downstream-card {{
      border-radius: 18px;
      padding: 20px 24px;
      min-height: 88px;
    }}
    .downstream-card h3 {{ font-size: 1.25rem; }}
    .downstream-card p {{
      margin-top: 8px;
      font-size: 0.94rem;
    }}
    .safety-banner {{
      width: min(1120px, 100%);
      margin: 36px auto 0;
      border: 1px solid rgba(74, 222, 128, 0.76);
      border-radius: 18px;
      padding: 17px 22px;
      color: #dcfce7;
      background: rgba(20, 83, 45, 0.35);
      text-align: center;
      font-size: clamp(1rem, 2vw, 1.25rem);
      font-weight: 720;
    }}
    .details {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-top: 22px;
    }}
    .detail-card {{
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 18px;
      background: rgba(15, 23, 42, 0.62);
      padding: 20px;
    }}
    .detail-card h2 {{
      margin: 0 0 12px;
      font-size: 1rem;
      text-transform: uppercase;
      letter-spacing: 0.09em;
      color: #cbd5e1;
    }}
    .detail-card p {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      margin: 10px 0;
      color: var(--muted);
      line-height: 1.35;
    }}
    .detail-card strong {{ color: var(--text); text-align: right; }}
    footer {{
      margin-top: 18px;
      color: #64748b;
      font-size: 0.82rem;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 1100px) {{
      header {{ grid-template-columns: 1fr; }}
      .stats {{ justify-content: flex-start; }}
      .flow {{ grid-template-columns: 1fr; min-height: auto; }}
      .sponsor-card::before, .sponsor-card::after {{ display: none; }}
      .details {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      main {{ width: min(100vw - 20px, 1480px); padding: 20px 0; }}
      .stage {{ padding: 24px 16px; border-radius: 20px; }}
      .stat {{ min-width: 132px; }}
      .node, .collector, .packet, .sponsor-card, .downstream-card {{ padding: 20px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{PROOF_GRAPH_VISUAL_TITLE}</h1>
        <p class="lede">{PROOF_GRAPH_VISUAL_SUBTITLE}</p>
      </div>
      <div class="stats" aria-label="ProofGraph counts">
        {_stat("proof nodes", counts["proof"])}
        {_stat("edges", counts["edge"])}
        {_stat("writes", "zero", ok=zero_writes)}
      </div>
      <div class="actions" aria-label="ProofGraph export actions">
        <a class="primary" href="/proofgraph.svg?fixture={_escape(graph.get("scenario_name") or DEFAULT_SCENARIO)}" download>Export SVG</a>
      </div>
    </header>

    <section class="stage" aria-label="InferenceAtlas ProofGraph flow">
      <div class="flow">
        <article class="node">
          <h2>Agent Request</h2>
          <p>tools - data - spend - production movement</p>
          <div class="connector-line"></div>
          <p>raw intent is not trusted directly</p>
        </article>

        <article class="collector">
          <h2>Sponsor Proof Collector</h2>
          <p>locked order - proof only</p>
          <p>{_escape(source_mode)}</p>
        </article>

        <section class="sponsors" aria-label="Sponsor proof contributors">
{sponsor_cards}
        </section>

        <article class="packet">
          <h2>IA Packet Authority</h2>
          <p>verdict - proof lock - reviewer routing</p>
          <div class="mini">
            {_metric("packet nodes", counts["packet"])}
            {_metric("native proof nodes", _provider_count(graph, "ia_packet"))}
            {_metric("decision lock", packet_node["decision_lock"])}
            {_metric("Verdict changes", _yes_no(invariants["graph_can_change_verdict"]))}
          </div>
        </article>

        <section class="downstream" aria-label="Downstream consumers">
{downstream_cards}
        </section>
      </div>
      <div class="safety-banner">{PROOF_GRAPH_SAFETY_BANNER}</div>
    </section>

    <section class="details" aria-label="ProofGraph proof summary">
      <article class="detail-card">
        <h2>Why It Matters</h2>
        <p><span>Graph creator</span><strong>InferenceAtlas</strong></p>
        <p><span>Trust source</span><strong>IA Packet</strong></p>
        <p><span>Human review</span><strong>{_yes_no(safety["requires_human_review"])}</strong></p>
      </article>
      <article class="detail-card">
        <h2>Sponsor Boundary</h2>
        <p><span>Approve access</span><strong>{_yes_no(safety["approves_access"])}</strong></p>
        <p><span>Grant permissions</span><strong>{_yes_no(safety["grants_permissions"])}</strong></p>
        <p><span>Mutate production</span><strong>{_yes_no(safety["mutates_production"])}</strong></p>
      </article>
      <article class="detail-card">
        <h2>Packet Reference</h2>
        <p><span>Packet</span><strong>{_escape(packet["packet_id"])}</strong></p>
        <p><span>Revision</span><strong>{_escape(packet["revision_id"])}</strong></p>
        <p><span>Portkey proof nodes</span><strong>{_provider_count(graph, "portkey")}</strong></p>
      </article>
    </section>

    <footer>
      packet: {_escape(packet["packet_id"])} - graph: {_escape(graph["graph_id"])} - hash: {_escape(graph["content_hash"])}
    </footer>
  </main>
</body>
</html>
"""
    return html_doc


def render_review_run_proof_graph_html(graph: dict[str, Any]) -> str:
    """Render the dynamic ReviewRun-backed ProofGraph page."""
    run_id = graph.get("generated_from_run_id") or graph.get("generated_from", {}).get("run_id") or "unknown"
    selected_repo = graph.get("selected_repo") or graph.get("generated_from", {}).get("selected_repo") or "no repo selected"
    packet = graph.get("packet_reference") or {}
    packet_id = packet.get("packet_id") or "not generated"
    revision_id = packet.get("revision_id") or "not generated"
    revision_number = packet.get("revision_number") or 0
    previous_revision = packet.get("previous_revision_id") or "none"
    proof_counts = graph.get("proof_counts") or {}
    node_counts = graph.get("node_counts") or {}
    movement = graph.get("movement_classes") or {}
    safety = graph.get("safety_boundary") or {}
    summary = graph.get("summary") or {}
    zero_writes = bool(graph.get("zero_writes"))
    status_label = graph.get("status_label") or graph.get("graph_state") or "unknown"
    portkey_state = graph.get("portkey_state") or "No packet"

    nodes = "\n".join(_review_run_node_card(node) for node in graph.get("nodes", []))
    edges = "\n".join(_review_run_edge_row(edge) for edge in graph.get("edges", []))
    movement_rows = "\n".join(
        _review_run_fact(label, ", ".join(movement.get(key) or []) or "none")
        for label, key in (
            ("Allowed", "allowed"),
            ("Review required", "review_required"),
            ("Blocked", "blocked"),
        )
    )
    safety_rows = "\n".join(
        _review_run_fact(label, _yes_no(bool(safety.get(key))))
        for label, key in (
            ("Approves access", "approves_access"),
            ("Grants permissions", "permissions_granted"),
            ("External writes", "external_writes"),
            ("Portkey API call", "portkey_api_call_made"),
            ("Raw intent trusted", "raw_agent_intent_trusted"),
        )
    )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>InferenceAtlas ReviewRun ProofGraph</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #090b10;
      --panel: #12161e;
      --panel-soft: #171c24;
      --line: #2b3442;
      --text: #f4f5f7;
      --muted: #a7adb8;
      --blue: #6aa6ff;
      --green: #71d58b;
      --amber: #f2b84b;
      --red: #ff786f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    main {{
      width: min(1220px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 34px 0 42px;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 5vw, 4.1rem);
      line-height: 1;
      font-weight: 760;
    }}
    .lede {{
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.5;
    }}
    .run-id {{
      color: var(--green);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      overflow-wrap: anywhere;
    }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
    }}
    .actions {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 12px;
    }}
    .actions a {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0 14px;
      color: var(--text);
      background: var(--panel);
      text-decoration: none;
      font-size: 0.82rem;
      font-weight: 760;
    }}
    .actions a.primary {{
      border-color: rgba(113, 213, 139, 0.72);
      color: #c9f8d5;
      background: rgba(25, 92, 48, 0.32);
    }}
    .stat {{
      min-width: 138px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 10px 12px;
      text-align: center;
      color: var(--muted);
    }}
    .stat strong {{
      display: block;
      color: var(--text);
      font-size: 1rem;
      overflow-wrap: anywhere;
    }}
    .stat span {{
      display: block;
      margin-top: 3px;
      font-size: 0.72rem;
      font-weight: 760;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .stat.ok {{
      border-color: rgba(113, 213, 139, 0.72);
      background: rgba(25, 92, 48, 0.32);
    }}
    .boundary {{
      display: inline-flex;
      margin-top: 12px;
      border: 1px solid rgba(113, 213, 139, 0.62);
      border-radius: 8px;
      padding: 8px 10px;
      color: #c9f8d5;
      background: rgba(25, 92, 48, 0.24);
      font-weight: 780;
    }}
    .graph-shell {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      padding: 18px;
    }}
    .rail {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      align-items: stretch;
      margin-bottom: 18px;
    }}
    .review-node {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      padding: 14px;
    }}
    .review-node span {{
      display: block;
      color: var(--muted);
      font-size: 0.68rem;
      font-weight: 780;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .review-node h2 {{
      margin: 8px 0;
      color: var(--text);
      font-size: 1rem;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .review-node p {{
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.45;
    }}
    .review-node strong {{
      color: var(--green);
      overflow-wrap: anywhere;
    }}
    .review-node.packet {{
      border-color: rgba(242, 184, 75, 0.78);
    }}
    .review-node.downstream {{
      border-color: rgba(106, 166, 255, 0.7);
    }}
    .facts {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .fact-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      padding: 15px;
    }}
    .fact-card h2 {{
      margin: 0 0 10px;
      font-size: 0.9rem;
      color: var(--text);
    }}
    .fact-card p {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin: 8px 0;
      color: var(--muted);
      line-height: 1.35;
    }}
    .fact-card strong {{
      color: var(--text);
      text-align: right;
      overflow-wrap: anywhere;
    }}
    .edge-list p {{
      display: block;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 8px;
    }}
    footer {{
      margin-top: 16px;
      color: #788191;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.78rem;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 980px) {{
      header {{ grid-template-columns: 1fr; }}
      .stats {{ justify-content: flex-start; }}
      .rail, .facts {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 620px) {{
      main {{ width: min(100vw - 20px, 1220px); padding: 20px 0 28px; }}
      .graph-shell {{ padding: 12px; }}
      .fact-card p {{ display: block; }}
      .fact-card strong {{ display: block; margin-top: 3px; text-align: left; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>InferenceAtlas ReviewRun ProofGraph</h1>
        <p class="lede">Generated from run_id <span class="run-id">{_escape(run_id)}</span>. Same request, current packet revision, proof state, and downstream Portkey read are rendered from the live ReviewRun.</p>
        <span class="boundary">No approval / no writes / no mutation - zero writes</span>
      </div>
      <div class="stats" aria-label="ReviewRun ProofGraph status">
        {_stat("state", status_label)}
        {_stat("packet revision", revision_id)}
        {_stat("writes", "zero" if zero_writes else "unknown", ok=zero_writes)}
      </div>
      <div class="actions" aria-label="ReviewRun ProofGraph export actions">
        <a class="primary" href="/proofgraph.svg?review_run_id={_escape(run_id)}" download>Export SVG</a>
      </div>
    </header>

    <section class="graph-shell" aria-label="Dynamic ReviewRun ProofGraph">
      <div class="rail">
{nodes}
      </div>
      <div class="facts">
        <article class="fact-card">
          <h2>Current Read</h2>
          {_review_run_fact("Selected repo", selected_repo)}
          {_review_run_fact("Packet", packet_id)}
          {_review_run_fact("Revision", f"{revision_id} (rev {revision_number})")}
          {_review_run_fact("Previous revision", previous_revision)}
          {_review_run_fact("Portkey state", portkey_state)}
        </article>
        <article class="fact-card">
          <h2>Proof State</h2>
          {_review_run_fact("Sponsor proof count", proof_counts.get("sponsor_steps", 0))}
          {_review_run_fact("Attached proof", proof_counts.get("attached", 0))}
          {_review_run_fact("Missing proof", proof_counts.get("missing", 0))}
          {_review_run_fact("Graph nodes", node_counts.get("proof", 0))}
          {_review_run_fact("Revision changed", _yes_no(bool(graph.get("revision_changed"))))}
        </article>
        <article class="fact-card">
          <h2>Packet Authority</h2>
          {_review_run_fact("Authority", summary.get("authority", "Packet remains authority. Sponsors contribute proof only."))}
          {_review_run_fact("Next human action", graph.get("next_human_action", "human review required"))}
          {_review_run_fact("Safety", "Packet remains authority")}
          {_review_run_fact("Sponsor role", "Sponsors contribute proof only")}
          {_review_run_fact("Writes", "zero writes")}
        </article>
        <article class="fact-card">
          <h2>Movement</h2>
          {movement_rows}
        </article>
        <article class="fact-card">
          <h2>Edges</h2>
          <div class="edge-list">
{edges}
          </div>
        </article>
        <article class="fact-card">
          <h2>Safety Boundary</h2>
          {safety_rows}
        </article>
      </div>
    </section>

    <footer>
      ReviewRun ProofGraph: {_escape(graph.get("graph_id", "unknown"))} - hash: {_escape(graph.get("content_hash", "missing"))}
    </footer>
  </main>
</body>
</html>
"""
    return html_doc


def build_proof_graph_visual(
    scenario_name: str = DEFAULT_SCENARIO,
) -> str:
    graph = build_proof_graph_for_scenario(
        scenario_name,
        include_all_sponsor_proof=True,
    )
    return render_proof_graph_html(graph)


def write_proof_graph_visual_artifact(
    output_dir: Path = GENERATED_DIR,
    *,
    scenario_name: str = DEFAULT_SCENARIO,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / PROOF_GRAPH_VISUAL_FILE
    output_path.write_text(build_proof_graph_visual(scenario_name), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.proof_graph_visual",
        description="Render the public ProofGraph HTML visual.",
    )
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO, choices=sorted(SCENARIOS))
    parser.add_argument(
        "--write",
        action="store_true",
        help=f"Write examples/generated/{PROOF_GRAPH_VISUAL_FILE} instead of printing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write:
        output_path = write_proof_graph_visual_artifact(scenario_name=args.scenario)
        print(output_path)
    else:
        print(build_proof_graph_visual(args.scenario))
    return 0


if __name__ == "__main__":
    sys.exit(main())
