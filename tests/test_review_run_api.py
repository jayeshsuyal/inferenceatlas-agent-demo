"""ReviewRun API contract tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from web.app import (
    ReviewRunCreateRequest,
    _review_runs,
    app,
    create_review_run_api,
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
