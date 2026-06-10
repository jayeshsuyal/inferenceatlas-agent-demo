"""ProofGraph HTML visual contract tests."""

from __future__ import annotations

from fastapi import HTTPException

from agent.proof_graph import build_proof_graph_for_scenario
from agent.proof_graph_visual import (
    PROOF_GRAPH_SAFETY_BANNER,
    PROOF_GRAPH_VISUAL_FILE,
    PROOF_GRAPH_VISUAL_SUBTITLE,
    PROOF_GRAPH_VISUAL_TITLE,
    render_proof_graph_html,
    write_proof_graph_visual_artifact,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


def _all_sponsor_graph() -> dict:
    return build_proof_graph_for_scenario(
        "support_triage_agent",
        include_all_sponsor_proof=True,
    )


def test_proof_graph_visual_is_data_backed_and_not_stale() -> None:
    graph = _all_sponsor_graph()
    html = render_proof_graph_html(graph)

    assert PROOF_GRAPH_VISUAL_TITLE in html
    assert PROOF_GRAPH_VISUAL_SUBTITLE in html
    assert f"<strong>{graph['node_counts']['proof']}</strong><span>proof nodes</span>" in html
    assert f"<strong>{graph['node_counts']['edge']}</strong><span>edges</span>" in html
    assert "<strong>zero</strong><span>writes</span>" in html
    assert "77 proof nodes" not in html
    assert "136 edges" not in html
    assert graph["graph_id"] in html
    assert graph["content_hash"] in html


def test_proof_graph_visual_names_sponsor_roles_and_packet_authority() -> None:
    html = render_proof_graph_html(_all_sponsor_graph())

    for label in [
        "Sponsor Proof Collector",
        "Tavily",
        "Composio",
        "OpenClaw",
        "Nebius",
        "IA Packet Authority",
        "Portkey Gate",
        "CI / Deploy",
        "Finance",
        "Security / Legal",
    ]:
        assert label in html
    assert PROOF_GRAPH_SAFETY_BANNER in html
    assert "Sponsors contribute proof only" in html
    assert "raw intent is not trusted directly" in html


def test_proof_graph_visual_preserves_public_boundary_language() -> None:
    html = render_proof_graph_html(_all_sponsor_graph())

    assert "Approve access</span><strong>no</strong>" in html
    assert "Grant permissions</span><strong>no</strong>" in html
    assert "Mutate production</span><strong>no</strong>" in html
    assert "Verdict changes" in html
    assert "Graph creator</span><strong>InferenceAtlas</strong>" in html
    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden.lower() not in html.lower()


def test_proof_graph_visual_artifact_writer_uses_canonical_name(tmp_path) -> None:
    output_path = write_proof_graph_visual_artifact(output_dir=tmp_path)
    html = output_path.read_text(encoding="utf-8")

    assert output_path.name == PROOF_GRAPH_VISUAL_FILE
    assert PROOF_GRAPH_VISUAL_TITLE in html
    assert "ia-proof-graph-support_triage_agent-" in html


def test_proof_graph_route_serves_visual_html_and_rejects_unknown_fixture() -> None:
    from web.app import app, proofgraph_index

    assert any(getattr(route, "path", "") == "/proofgraph" for route in app.routes)
    response = proofgraph_index("support_triage_agent")
    body = response.body.decode("utf-8")

    assert response.status_code == 200
    assert PROOF_GRAPH_VISUAL_TITLE in body
    assert "IA Packet Authority" in body

    try:
        proofgraph_index("unknown_fixture")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("unknown ProofGraph fixture should 404")
