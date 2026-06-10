"""ReviewRun API contract tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from agent.connector_oauth import demo_sign_in

from web.app import (
    GithubAttachRequest,
    ReviewRunCreateRequest,
    ReviewRunPacketRequest,
    _review_runs,
    app,
    create_review_run_api,
    generate_review_run_packet_api,
    github_attach_repo,
    github_list_repos,
    get_review_run,
)


class ReviewRunApiTests(TestCase):
    def test_review_run_api_creates_and_reads_durable_run(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                            "oauth_token": "ghp_1234567890abcdefSECRET",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 4},
                    )
                )

                self.assertIs(created["ok"], True)
                self.assertIs(created["read_only"], True)
                run = created["run"]
                self.assertEqual(run["stage"], "repo_selected")
                self.assertEqual(run["selected_repo"]["full_name"], "acme/demo-support-incidents")
                self.assertEqual(run["selected_repo"]["oauth_token"], "[redacted]")
                self.assertIs(run["repo_index_summary"]["selected_repo_only"], True)
                self.assertEqual(run["repo_index_summary"]["indexed_repo_count"], 1)
                self.assertIs(run["safety_invariants"]["approval_granted"], False)
                self.assertIs(run["safety_invariants"]["external_writes_enabled"], False)
                self.assertEqual(created["record"]["run_id"], run["run_id"])
                self.assertIs(created["record"]["read_only"], True)

                _review_runs.clear()
                fetched = get_review_run(run["run_id"])
                self.assertIs(fetched["ok"], True)
                self.assertIs(fetched["read_only"], True)
                self.assertEqual(fetched["run"], run)
                self.assertEqual(fetched["record"]["stage"], "repo_selected")
                self.assertTrue(list(store_dir.glob("*.json")))

    def test_review_run_api_generates_compact_packet_from_selected_repo(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                created = create_review_run_api(
                    ReviewRunCreateRequest(
                        selected_repo={
                            "provider": "github",
                            "full_name": "acme/demo-support-incidents",
                        },
                        repo_index_summary={"status": "indexed", "indexed_repo_count": 1},
                    )
                )
                generated = generate_review_run_packet_api(
                    created["run"]["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )

                self.assertIs(generated["ok"], True)
                self.assertIs(generated["read_only"], True)
                run = generated["run"]
                packet = generated["packet"]
                self.assertEqual(run["stage"], "packet_generated")
                self.assertEqual(run["packet"]["source_run_id"], run["run_id"])
                self.assertEqual(run["packet"]["revision_number"], 1)
                self.assertEqual(packet["schema_version"], "review_run_packet.v0")
                self.assertEqual(packet["packet_reference"]["run_id"], run["run_id"])
                self.assertEqual(packet["packet_reference"]["source_of_truth"], "ReviewRun")
                self.assertEqual(packet["compact_output"]["allowed"], ["read issues"])
                self.assertEqual(packet["compact_output"]["review_required"], ["comment"])
                self.assertEqual(
                    packet["compact_output"]["blocked"],
                    ["create labels", "repo admin", "org-wide write", "secrets"],
                )
                self.assertEqual(packet["source_inputs"]["selected_repo"], "acme/demo-support-incidents")
                self.assertFalse(packet["safety_boundary"]["approval_granted"])
                self.assertFalse(packet["safety_boundary"]["external_writes"])
                self.assertFalse(packet["safety_boundary"]["portkey_api_call_made"])

                fetched = get_review_run(run["run_id"])
                self.assertEqual(fetched["run"]["stage"], "packet_generated")
                self.assertEqual(fetched["run"]["packet"], run["packet"])

                second = generate_review_run_packet_api(
                    run["run_id"],
                    ReviewRunPacketRequest(
                        access_request="support-triage-bot needs to read issues, comment, and create labels."
                    ),
                )
                self.assertEqual(second["run"]["packet"]["revision_id"], run["packet"]["revision_id"])

                with self.assertRaises(HTTPException) as changed:
                    generate_review_run_packet_api(
                        run["run_id"],
                        ReviewRunPacketRequest(access_request="support-triage-bot now needs repo admin"),
                    )
                self.assertEqual(changed.exception.status_code, 400)
                self.assertIn("raw agent request cannot change", changed.exception.detail)

    def test_review_run_api_rejects_request_without_repo(self) -> None:
        with self.assertRaises(HTTPException) as exc:
            create_review_run_api(ReviewRunCreateRequest(access_request="read issues"))

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("selected_repo is required", exc.exception.detail)

    def test_review_run_api_bad_or_unknown_run_ids_fail_closed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store_dir = Path(temp_dir)
            with patch("web.app.REVIEW_RUN_STORE_DIR", store_dir):
                with self.assertRaises(HTTPException) as bad:
                    get_review_run("../escape")
                self.assertEqual(bad.exception.status_code, 400)

                with self.assertRaises(HTTPException) as missing:
                    get_review_run("ia-review-run-missing")
                self.assertEqual(missing.exception.status_code, 404)

    def test_review_run_api_routes_are_create_and_read_only(self) -> None:
        post_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs")
        get_route = next(route for route in app.routes if getattr(route, "path", "") == "/api/review-runs/{run_id}")

        self.assertEqual(post_route.methods, {"POST"})
        self.assertEqual(get_route.methods, {"GET"})

    def test_demo_github_repo_select_creates_safe_review_run(self) -> None:
        session_id = "review-run-root-demo-flow"
        demo_sign_in(session_id, "github")

        repos = github_list_repos(session_id=session_id, q="triage")
        self.assertTrue(repos["ok"])
        self.assertTrue(repos["demo"])
        selected = repos["repos"][0]

        attached = github_attach_repo(
            GithubAttachRequest(session_id=session_id, full_name=selected["full_name"])
        )
        self.assertTrue(attached["ok"])
        self.assertGreater(attached["digest_chars"], 100)

        created = create_review_run_api(
            ReviewRunCreateRequest(
                session_id=session_id,
                selected_repo={
                    "provider": "github",
                    "full_name": selected["full_name"],
                    "source": "demo_repo",
                },
                repo_index_summary={
                    "status": "indexed",
                    "indexed_repo_count": 1,
                    "digest_chars": attached["digest_chars"],
                    "readme_found": attached["readme_found"],
                    "files_included": attached["files_included"],
                    "paths_in_tree": attached["paths_in_tree"],
                    "sample_paths": attached["sample_paths"],
                },
            )
        )

        run = created["run"]
        self.assertTrue(created["read_only"])
        self.assertEqual(run["stage"], "repo_selected")
        self.assertEqual(run["selected_repo"]["full_name"], selected["full_name"])
        self.assertEqual(run["repo_index_summary"]["status"], "indexed")
        self.assertEqual(run["repo_index_summary"]["indexed_repo_count"], 1)
        self.assertFalse(run["access_request"])
        self.assertFalse(run["safety_invariants"]["approval_granted"])
        self.assertFalse(run["safety_invariants"]["external_writes_enabled"])
