#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_web_paging.py
@brief Server-side paging contracts for audit history and job pages.
@details The browser requests one bounded page at a time; these tests prove the
         API slices, totals, bounds and role checks it relies on.
"""

# IMPORTS
from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from fastapi.testclient import TestClient


# LOCAL HELPERS
def _admin(client: TestClient) -> None:
    client.post("/api/v1/session", json={"username": "admin", "password": "admin"})


# TESTS
def test_audit_page_returns_newest_first_slice_with_total(tmp_path):
    """@brief A page request returns only that slice and the full count."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    for index in range(60):
        web.audit(None, f"event-{index:02d}")
    with TestClient(app) as client:
        _admin(client)
        page = client.get("/api/v1/audit-page?limit=25&offset=25")
        assert page.status_code == 200
        body = page.json()
        total = body["total"]
        assert total == 61  # 60 events plus the administrator login
        assert body["limit"] == 25 and body["offset"] == 25
        assert len(body["items"]) == 25
        newest = client.get("/api/v1/audit-page?limit=10").json()["items"]
        assert newest[0]["action"] == "login"
        # Newest first: the login is row 0, so offset 25 starts at event-35.
        assert [row["action"] for row in body["items"]][:2] == ["event-35", "event-34"]
        assert set(body["items"][0]) == {
            "id", "actor_id", "actor", "action", "project", "detail", "created_at",
            "schema", "project_id", "resource_type", "resource_id", "phase", "result",
            "operation_id", "base_revision", "candidate_revision", "before", "after",
            "correlation",
        }
        everything = client.get("/api/v1/audit-page?limit=all").json()
        assert everything["limit"] is None and len(everything["items"]) == total
        past_end = client.get("/api/v1/audit-page?limit=10&offset=500").json()
        assert past_end["items"] == [] and past_end["total"] == total


def test_audit_page_rejects_bad_bounds_and_non_administrators(tmp_path):
    """@brief Paging bounds and the administrator guard fail closed."""
    app = create_app(tmp_path / "home")
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        assert client.get("/api/v1/audit-page").json()["detail"]["code"] == (
            "authentication_required")
        _admin(client)
        for query in ("limit=0", "limit=101", "limit=abc", "limit=" + "9" * 50):
            response = client.get(f"/api/v1/audit-page?{query}")
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == "invalid_audit_limit"
        negative = client.get("/api/v1/audit-page?offset=-1")
        assert negative.status_code == 422
        assert negative.json()["detail"]["code"] == "invalid_request"
        client.post("/api/v1/session", json={"username": "dev", "password": "longer-password"})
        denied = client.get("/api/v1/audit-page")
        assert denied.status_code == 403 and denied.json()["detail"]["code"] == "admin_required"


def test_run_page_accepts_several_lifecycles(tmp_path):
    """@brief Overview review tables combine lifecycles in one bounded request."""
    profiles = ProfileStore(tmp_path / "home")
    profile = profiles.create("alpha", store_root=str(tmp_path / "state"))
    state = StateStore(profile.store_root)
    for run_id, lifecycle in (("a", "awaiting-approval"), ("b", "in-review"),
                              ("c", "failed"), ("d", "working")):
        state.save(RunState(run_id=run_id, ticket_iid=1, lifecycle=lifecycle))
    with TestClient(create_app(profiles.home)) as client:
        _admin(client)
        both = client.get("/api/v1/projects/alpha/runs-page?limit=all"
                          "&lifecycle=awaiting-approval&lifecycle=in-review").json()
        assert sorted(item["run_id"] for item in both["items"]) == ["a", "b"]
        assert both["total"] == 2
        single = client.get("/api/v1/projects/alpha/runs-page?lifecycle=failed").json()
        assert [item["run_id"] for item in single["items"]] == ["c"]
        assert client.get("/api/v1/projects/alpha/runs-page").json()["total"] == 4
        invalid = client.get("/api/v1/projects/alpha/runs-page?lifecycle=failed&lifecycle=bogus")
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "invalid_request"


# END OF FILE
