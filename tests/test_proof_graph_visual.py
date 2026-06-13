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
    render_proof_graph_svg,
    render_review_run_proof_graph_html,
    render_review_run_proof_graph_svg,
    write_proof_graph_visual_artifact,
)
from agent.review_run import (
    DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
    attach_review_run_proof,
    build_review_run_proofgraph,
    create_review_run,
    generate_proof_resolved_review_run_packet,
    generate_initial_review_run_packet,
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


def test_proof_graph_svg_export_is_data_backed() -> None:
    graph = _all_sponsor_graph()
    svg = render_proof_graph_svg(graph)

    assert svg.startswith("<svg")
    assert "InferenceAtlas ProofGraph" in svg
    assert str(graph["node_counts"]["proof"]) in svg
    assert graph["packet_reference"]["packet_id"] in svg
    assert graph["content_hash"] in svg
    assert "zero" in svg


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


def test_review_run_proof_graph_visual_is_dynamic_and_packet_backed() -> None:
    run = create_review_run(
        selected_repo={"provider": "github", "full_name": "acme/demo-support-incidents"},
        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
    )
    packet_run = generate_initial_review_run_packet(run, DEFAULT_REVIEW_RUN_ACCESS_REQUEST)
    proofed = attach_review_run_proof(
        packet_run,
        [
            {"id": "repo_owner_approval"},
            {"id": "rollback_offswitch"},
            {"id": "environment_boundary"},
        ],
    )
    rerun = generate_proof_resolved_review_run_packet(proofed, DEFAULT_REVIEW_RUN_ACCESS_REQUEST)
    graph = build_review_run_proofgraph(rerun)
    html = render_review_run_proof_graph_html(graph)

    assert "InferenceAtlas ReviewRun ProofGraph" in html
    assert f"Generated from run_id <span class=\"run-id\">{rerun.run_id}</span>" in html
    assert "Packet remains authority" in html
    assert "Sponsors contribute proof only" in html
    assert "No approval / no writes / no mutation - zero writes" in html
    assert "Allow with policy" in html
    assert rerun.packet["revision_id"] in html
    assert graph["content_hash"] in html
    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden.lower() not in html.lower()


def test_review_run_proof_graph_svg_export_is_dynamic_and_packet_backed() -> None:
    run = create_review_run(
        selected_repo={"provider": "github", "full_name": "acme/demo-support-incidents"},
        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
    )
    packet_run = generate_initial_review_run_packet(run, DEFAULT_REVIEW_RUN_ACCESS_REQUEST)
    proofed = attach_review_run_proof(
        packet_run,
        [
            {"id": "repo_owner_approval"},
            {"id": "rollback_offswitch"},
            {"id": "environment_boundary"},
        ],
    )
    rerun = generate_proof_resolved_review_run_packet(proofed, DEFAULT_REVIEW_RUN_ACCESS_REQUEST)
    graph = build_review_run_proofgraph(rerun)
    svg = render_review_run_proof_graph_svg(graph)

    assert svg.startswith("<svg")
    assert "InferenceAtlas ReviewRun ProofGraph" in svg
    assert rerun.run_id in svg
    assert rerun.packet["revision_id"] in svg
    assert graph["content_hash"] in svg
    assert "Allow with policy" in svg
    assert "Still blocked" in svg
    assert "not a screenshot" in svg
    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden.lower() not in svg.lower()


def test_proof_graph_visual_artifact_writer_uses_canonical_name(tmp_path) -> None:
    output_path = write_proof_graph_visual_artifact(output_dir=tmp_path)
    html = output_path.read_text(encoding="utf-8")

    assert output_path.name == PROOF_GRAPH_VISUAL_FILE
    assert PROOF_GRAPH_VISUAL_TITLE in html
    assert "ia-proof-graph-support_triage_agent-" in html


def test_proof_graph_route_serves_visual_html_and_rejects_unknown_fixture() -> None:
    from web.app import app, proofgraph_index, proofgraph_svg_index

    assert any(getattr(route, "path", "") == "/proofgraph" for route in app.routes)
    assert any(getattr(route, "path", "") == "/proofgraph.svg" for route in app.routes)
    response = proofgraph_index("support_triage_agent")
    body = response.body.decode("utf-8")

    assert response.status_code == 200
    assert PROOF_GRAPH_VISUAL_TITLE in body
    assert "IA Packet Authority" in body
    assert "Export SVG" in body
    assert "/proofgraph.svg?fixture=support_triage_agent" in body

    svg_response = proofgraph_svg_index("support_triage_agent")
    svg_body = svg_response.body.decode("utf-8")
    assert svg_response.status_code == 200
    assert svg_response.media_type == "image/svg+xml"
    assert "attachment;" in svg_response.headers["content-disposition"]
    assert PROOF_GRAPH_VISUAL_TITLE in svg_body

    try:
        proofgraph_index("unknown_fixture")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("unknown ProofGraph fixture should 404")
