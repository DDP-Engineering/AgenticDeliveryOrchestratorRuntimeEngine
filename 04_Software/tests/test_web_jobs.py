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
@file    test_web_jobs.py
@brief   Authorized global persisted job read contracts.
@details Offline HTTP tests cover complete pages, composite identities, real
         evidence, source revisions and fail-closed external data boundaries.
"""

# IMPORTS
import json
from pathlib import Path
import subprocess
import time

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
from adore.web.jobs import redact_text
from fastapi.testclient import TestClient
import pytest


# LOCAL HELPERS
def _fixture(tmp_path):
    """@brief Create two profiles with colliding run IDs and equal UTC times."""
    profiles = ProfileStore(tmp_path / "home")
    items = [profiles.create(name, store_root=str(tmp_path / name),
                             display_name=f"Project {name}", platform="gitea")
             for name in ("alpha", "beta")]
    stores = [StateStore(item.store_root) for item in items]
    example = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text()
    for item in items:
        profiles.config_path(item.name).write_text(example.replace(
            'store_root = ".adore"', f'store_root = "{Path(item.store_root).as_posix()}"'))
    for index, store in enumerate(stores):
        for run_id, lifecycle in (("same", "working"), ("old", "done")):
            store.save(RunState(run_id=run_id, ticket_iid=1, lifecycle=lifecycle,
                                stage="build", outcome="" if run_id == "same" else "merged"))
            _state(store, run_id, updated_at="2026-10-05T10:00:00+00:00" if index == 0
                   else "2026-10-05T13:00:00+03:00", created_at="2026-10-05T09:00:00+00:00")
        store.save_ticket("same", {"iid": 1, "title": f"Actual {items[index].name}",
                                   "web_url": "https://forge.example/org/repo/issues/1",
                                   "description": "SECRET_DESCRIPTION"})
    def forbidden(*args, **kwargs):
        """@brief Any attempted external read operation fails the test."""
        pytest.fail("read endpoint called command runner")
    app = create_app(profiles.home, probe_runner=forbidden)
    return profiles, items, stores, app


def _state(store, run_id, **updates):
    path = store.run_dir(run_id) / "state.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value.update(updates)
    path.write_text(json.dumps(value), encoding="utf-8")


def _login(client, username="admin", credential=None):
    client.post("/api/v1/session", json={"username": username,
                                         "password": credential or username})


def _get(client, query=""):
    response = client.get("/api/v1/jobs-page" + query)
    assert response.status_code == 200, response.text
    return response.json()


# PUBLIC CONTRACT TESTS
def test_job_list_has_no_advanced_filters_and_detail_keeps_safe_timeline(tmp_path):
    """@brief Removed advanced filter parameters are ignored; detail keeps safe event evidence."""
    _, items, stores, app = _fixture(tmp_path)
    stores[1].journal("same", "gate-started", stage="build", executor="pi",
                           model="SECRET_MODEL", password="SECRET_PASSWORD")
    stores[1].journal("same", "gate-passed", stage="validate")
    with TestClient(app) as client:
        _login(client)
        everything = _get(client)
        for query in ("?executor=pi&stage=build&updated_from=2026-10-05&updated_to=2026-10-05",
                      "?executor=%20", "?outcome=MERGED", "?lifecycle=working",
                      "?updated_from=wrong", "?updated_from=2026-10-06&updated_to=2026-10-05"):
            page = _get(client, query)
            assert page["total"] == everything["total"], query
        assert "timeline" not in everything["items"][0]
        assert "observed_executors" not in everything["items"][0]
        assert _get(client, "?attention=true")["total"] == 0
        detail = client.get(f"/api/v1/jobs/{items[1].project_id}/same").json()["job"]
        assert [row["stage"] for row in detail["timeline"]] == ["build", "validate"]
        assert all(set(row) == {"ts", "event", "stage"} for row in detail["timeline"])
        assert "SECRET_" not in str(detail)
        assert "observed_executors" not in detail


@pytest.mark.parametrize("field,value", [("executor", 12), ("executor", ""),
                                         ("stage", "unknown-stage")])
def test_global_projected_timeline_corruption_fails_closed(tmp_path, field, value):
    """@brief Invalid observed filter/timeline evidence never yields partial totals."""
    _, _, stores, app = _fixture(tmp_path)
    stores[0].journal("same", "gate-started", **{field: value})
    with TestClient(app) as client:
        _login(client)
        response = client.get("/api/v1/jobs-page")
        assert response.status_code == 503
        assert response.json() == {"detail": {"code": "run_journal_corrupt"}}


@pytest.mark.parametrize("stamp", ["", "malformed", "2026-10-05T10:00:00"])
def test_project_summary_refuses_a_run_without_an_aware_activity_time(tmp_path, stamp):
    """@brief Every save stamps updated_at in UTC; anything else is corrupt run state."""
    _, _, stores, app = _fixture(tmp_path)
    _state(stores[0], "same", updated_at=stamp)
    with TestClient(app) as client:
        _login(client)
        response = client.get("/api/v1/projects")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "run_state_corrupt"


def test_global_pages_search_groups_and_collision_identity(tmp_path):
    """@brief Full global ordering precedes slicing and retains colliding IDs."""
    _, items, _, app = _fixture(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/v1/jobs-page").status_code == 401
        _login(client)
        first = _get(client, "?limit=1")
        assert first["total"] == 4 and first["complete"] is True
        assert first["counts"] == {"working": 2, "done": 2}
        assert first["groups"] == {"active": 2, "waiting": 0, "review": 0, "terminal": 2}
        assert first["snapshot_semantics"] == "optimistic-source-revision"
        rows = []
        for offset in range(4):
            page = _get(client, f"?limit=1&offset={offset}&snapshot={first['snapshot']}")
            rows.extend(page["items"])
        expected = sorted((item.project_id, run_id) for item in items for run_id in ("old", "same"))
        assert [(row["project_id"], row["run_id"]) for row in rows] == expected
        assert len(set((row["project_id"], row["run_id"]) for row in rows)) == 4
        search = _get(client, "?q=ACTUAL%20BETA&limit=all")
        assert search["total"] == 1 and search["items"][0]["ticket_title"] == "Actual beta"
        assert _get(client, "?q=missing")["total"] == 0
        assert _get(client, "?q=merged&status_group=terminal")["total"] == 2
        assert _get(client, "?status_group=waiting")["total"] == 0
        assert _get(client, "?offset=50")["items"] == []
        assert _get(client, f"?project_id={items[0].project_id}")["total"] == 2
        assert "SECRET_DESCRIPTION" not in str(rows)
        # Existing response fields and project clients keep their contracts.
        assert client.get("/api/v1/projects/alpha/runs-page").json()["total"] == 2


def test_developer_scope_precedes_reads_counts_search_and_details(tmp_path):
    """@brief Unauthorized corrupt sources and matches never affect Dev reads."""
    _, items, stores, app = _fixture(tmp_path)
    dev = app.state.web_store.create_user("dev", "longer-password", "developer")
    app.state.web_store.set_memberships(dev["id"], ["alpha"])
    (stores[1].run_dir("same") / "state.json").write_text("SECRET_CORRUPT", encoding="utf-8")
    with TestClient(app) as client:
        _login(client, "dev", "longer-password")
        page = _get(client)
        assert page["total"] == 2 and page["counts"] == {"working": 1, "done": 1}
        assert _get(client, "?q=beta")["total"] == 0
        assert client.get(f"/api/v1/jobs-page?project_id={items[1].project_id}").status_code == 404
        assert client.get(f"/api/v1/jobs/{items[1].project_id}/same").status_code == 404
        assert client.get(f"/api/v1/jobs/{items[0].project_id}/same").status_code == 200
        assert client.get("/api/v1/projects/beta/runs/same").status_code == 404
        assert "cost_usd" not in str(page)
        before = page["snapshot"]
        app.state.web_store.set_memberships(dev["id"], [])
        changed = client.get(f"/api/v1/jobs-page?snapshot={before}")
        assert changed.status_code == 409
        assert _get(client)["total"] == 0
        assert client.get(f"/api/v1/jobs/{items[0].project_id}/same").status_code == 404


def test_persisted_wait_evidence_unknowns_archive_and_last_activity(tmp_path):
    """@brief Actual questions and approval references drive actionable evidence."""
    profiles, items, stores, app = _fixture(tmp_path)
    items[1].archived = True
    profiles.save(items[1])
    _state(stores[0], "same", lifecycle="parked-clarification", question_comment_id=7,
           parked_at="2026-10-05T11:59:00Z")
    stores[0].journal("same", "parked", questions="Which target? token=secret123",
                      ts="2026-10-05T12:00:00Z", private={"token": "HIDDEN"})
    _state(stores[1], "same", lifecycle="awaiting-approval", approval_comment_id=9,
           candidate_fingerprint="a" * 40, candidate_base_ref="b" * 40,
           approval_presented_at="2026-10-05T11:00:00Z")
    _state(stores[0], "old", outcome="", stage="done")
    with TestClient(app) as client:
        _login(client)
        page = _get(client)
        assert page["items"][0]["last_activity_at"] == "2026-10-05T12:00:00+00:00"
        detail = client.get(f"/api/v1/jobs/{items[0].project_id}/same").json()
        row = detail["job"]
        assert row["stage"] == "build" and row["outcome"] == ""
        assert row["waiting"]["reason"].startswith("Which target?")
        assert "secret123" not in str(detail) and "HIDDEN" not in str(detail)
        assert row["waiting"]["next_action"] == "answer_question_on_ticket"
        assert row["waiting"]["responsible_role"] == "human_responder"
        assert row["waiting"]["responsible_person"] is None
        assert row["waiting"]["evidence_url"].endswith("#issuecomment-7")
        assert row["consumption"] == {"availability": "unknown"}
        approval = client.get(f"/api/v1/jobs/{items[1].project_id}/same").json()["job"]
        assert approval["project_archived"] is True
        assert approval["waiting"]["next_action"] == "review_candidate_on_ticket"
        assert approval["waiting"]["evidence_url"].endswith("#issuecomment-9")
        bare = client.get(f"/api/v1/jobs/{items[0].project_id}/old").json()["job"]
        assert bare["ticket_title"] is None and bare["ticket_url"] is None
        assert bare["outcome"] == ""
        assert bare["coverage"]["ticket"] == "missing"
        assert bare["coverage"]["journal"] == "missing"
        assert bare["waiting"]["availability"] == "unknown"
        # A stage alone must never create an action.
        _state(stores[0], "old", lifecycle="awaiting-approval", stage="done")
        assert client.get(f"/api/v1/jobs/{items[0].project_id}/old").json()["job"][
            "waiting"]["next_action"] is None


@pytest.mark.parametrize("change", ["state", "add", "delete", "ticket", "journal", "archive"])
def test_page_revision_rejects_source_changes(tmp_path, change):
    """@brief Continuations detect changing records and profile history metadata."""
    profiles, items, stores, app = _fixture(tmp_path)
    with TestClient(app) as client:
        _login(client)
        first = _get(client, "?limit=1")
        store = stores[0]
        if change == "state":
            _state(store, "same", outcome="changed")
        elif change == "add":
            store.save(RunState("new", 2))
        elif change == "delete":
            (store.run_dir("same") / "ticket.json").unlink()
        elif change == "ticket":
            store.save_ticket("same", {"title": "Changed title"})
        elif change == "journal":
            store.journal("same", "observed")
        else:
            items[0].archived = True
            profiles.save(items[0])
        response = client.get(f"/api/v1/jobs-page?offset=1&snapshot={first['snapshot']}")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "job_snapshot_changed"
        assert _get(client)["snapshot"] != first["snapshot"]


def test_job_list_sorts_by_requested_column_before_paging(tmp_path):
    """@brief The server orders every matched job by the chosen column, then pages."""
    _, _, stores, app = _fixture(tmp_path)
    _state(stores[1], "old", updated_at="2026-10-06T09:00:00+00:00")
    with TestClient(app) as client:
        _login(client)
        first = _get(client)["items"][0]
        assert (first["project_name"], first["run_id"]) == ("beta", "old")
        ascending = _get(client, "?sort=project&order=asc&limit=2")
        assert [row["project_name"] for row in ascending["items"]] == ["alpha", "alpha"]
        assert ascending["total"] == 4
        second = _get(client, "?sort=project&order=asc&limit=2&offset=2"
                      f"&snapshot={ascending['snapshot']}")
        assert [row["project_name"] for row in second["items"]] == ["beta", "beta"]
        descending = _get(client, "?sort=project&order=desc")["items"]
        assert [row["project_name"] for row in descending[:2]] == ["beta", "beta"]
        groups = [row["status_group"] for row in _get(client, "?sort=status")["items"]]
        assert groups == sorted(groups, key=["active", "waiting", "review", "terminal"].index)
        reverse = _get(client, "?sort=status&order=desc")["items"]
        assert [row["status_group"] for row in reverse] == groups[::-1]
        tickets = _get(client, "?sort=ticket")["items"]
        assert [(row["project_name"], row["run_id"]) for row in tickets[:2]] == [
            ("alpha", "same"), ("beta", "same")]
        assert _get(client, "?sort=activity&order=asc")["items"][-1]["run_id"] == "old"


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=abc", "offset=-1",
                                    "q=%20", "q=" + "x" * 81,
                                    "status_group=bogus", "snapshot=no", "sort=bogus", "order=up"])
def test_invalid_job_queries_fail_closed(tmp_path, query):
    """@brief Query trust boundaries reject ambiguous or invalid selection."""
    _, _, _, app = _fixture(tmp_path)
    with TestClient(app) as client:
        _login(client)
        assert client.get(f"/api/v1/jobs-page?{query}").status_code == 422
        assert client.get("/api/v1/jobs/not-an-id/same").status_code == 404


@pytest.mark.parametrize("file,content,code", [
    ("state.json", "SECRET_CORRUPT", "run_state_corrupt"),
    ("ticket.json", "{SECRET_CORRUPT", "job_evidence_corrupt"),
    ("ticket.json", '{"iid":2}', "job_evidence_corrupt"),
    ("ticket.json", '{"title":[]}', "job_evidence_corrupt"),
    ("ticket.json", '{"title":"a","title":"b"}', "job_evidence_corrupt"),
    ("ticket.json", '{"title":NaN}', "job_evidence_corrupt"),
    ("ticket.json", '{"title":"\\ud800"}', "job_evidence_corrupt"),
    pytest.param("ticket.json", '{"description":' + '[' * 20000 + '0' + ']' * 20000 + '}',
                 "job_evidence_corrupt", id="deep-json"),
    ("journal.jsonl", '{"event":"ok"}\nSECRET_CORRUPT', "run_journal_corrupt"),
    ("journal.jsonl", '[]\n', "run_journal_corrupt"),
    ("journal.jsonl", '{"event":"ok","ts":"invalid"}\n', "run_journal_corrupt"),
])
def test_corrupt_authorized_evidence_has_no_partial_totals_or_secrets(
        tmp_path, file, content, code):
    """@brief Bad persisted sources reject page and detail without changing bytes."""
    _, items, stores, app = _fixture(tmp_path)
    path = stores[0].run_dir("same") / file
    path.write_text(content, encoding="utf-8")
    before = path.read_bytes()
    with TestClient(app, raise_server_exceptions=False) as client:
        _login(client)
        for endpoint in ("/api/v1/jobs-page", f"/api/v1/jobs/{items[0].project_id}/same"):
            response = client.get(endpoint)
            assert response.status_code == 503
            assert response.json() == {"detail": {"code": code}}
            assert "SECRET_CORRUPT" not in response.text and "total" not in response.text
    assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [("updated_at", "naive"), ("updated_at", 42),
                                        ("outcome", {}), ("mr_url", []),
                                        ("stage", []), ("question_comment_id", -1),
                                        ("schema_version", True), ("foreign_key", 1)])
def test_bad_state_metadata_is_typed(tmp_path, field, value):
    """@brief Additional projected state fields have explicit validated types."""
    _, _, stores, app = _fixture(tmp_path)
    _state(stores[0], "same", **{field: value})
    with TestClient(app) as client:
        _login(client)
        assert client.get("/api/v1/jobs-page").status_code == 503


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:secret@forge/a",
                                 "https://forge:invalid/a", "https://forge/a?token=SECRET",
                                 "https://forge/a#SECRET", "https://forge/a\nSECRET",
                                 "https://forge\\evil/a", "http:///missing", "https://[bad/a"])
@pytest.mark.parametrize("source", ["ticket", "mr"])
def test_unsafe_urls_fail_closed_without_exposure(tmp_path, url, source):
    """@brief Malformed and credential-bearing links never reach the browser."""
    _, _, stores, app = _fixture(tmp_path)
    if source == "ticket":
        stores[0].save_ticket("same", {"web_url": url})
    else:
        _state(stores[0], "same", mr_url=url)
    with TestClient(app) as client:
        _login(client)
        response = client.get("/api/v1/jobs-page")
        assert response.status_code == 503 and "SECRET" not in response.text


def test_source_mutation_during_read_is_rejected(tmp_path, monkeypatch):
    """@brief Reinspection detects a change during the projection scan."""
    _, _, stores, app = _fixture(tmp_path)
    original = Path.read_bytes
    changed = False
    path = stores[0].run_dir("same") / "state.json"
    def mutate(self):
        nonlocal changed
        value = original(self)
        if self == path and not changed:
            changed = True
            data = json.loads(value)
            data["outcome"] = "new evidence"
            self.write_text(json.dumps(data), encoding="utf-8")
        return value
    monkeypatch.setattr(Path, "read_bytes", mutate)
    with TestClient(app) as client:
        _login(client)
        response = client.get("/api/v1/jobs-page")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "job_snapshot_changed"


@pytest.mark.parametrize("platform,anchor", [("gitlab", "#note_7"),
                                            ("github", "#issuecomment-7"),
                                            ("gitea", "#issuecomment-7"), ("", "issues/1")])
def test_wait_locations_respect_forge_and_reads_launch_no_commands(
        tmp_path, monkeypatch, platform, anchor):
    """@brief Comment locations use forge evidence and all reads avoid subprocesses."""
    profiles, items, stores, app = _fixture(tmp_path)
    items[0].platform = platform
    profiles.save(items[0])
    _state(stores[0], "same", lifecycle="parked-clarification", question_comment_id=7,
           parked_at="2026-10-05T11:59:00Z")
    stores[0].journal("same", "parked", questions="Real persisted question")
    def prohibited(*args, **kwargs):
        pytest.fail("job read attempted an external command")
    monkeypatch.setattr(subprocess, "run", prohibited)
    monkeypatch.setattr(subprocess, "Popen", prohibited)
    with TestClient(app) as client:
        _login(client)
        assert _get(client)["total"] == 4
        row = client.get(f"/api/v1/jobs/{items[0].project_id}/same").json()["job"]
        assert row["waiting"]["evidence_url"].endswith(anchor)
        assert row["waiting"]["source"] == "journal:parked"


def test_all_lifecycle_groups_exact_stage_review_and_redaction(tmp_path):
    """@brief Grouping is lifecycle-based and retains exact state/evidence semantics."""
    _, items, stores, app = _fixture(tmp_path)
    lifecycles = {"working": "active", "publishing": "active", "handoff-pending": "waiting",
                  "parked-clarification": "waiting", "awaiting-approval": "waiting",
                  "in-review": "review", "done": "terminal", "failed": "terminal",
                  "cancelled": "terminal", "stale": "terminal", "handed-off": "terminal"}
    for lifecycle in lifecycles:
        stores[0].save(RunState(lifecycle, 3, lifecycle=lifecycle, stage="publishing",
                                outcome="Authorization: opaque ACCESS_TOKEN=hide Bearer hidden"))
    _state(stores[0], "in-review", mr_url="https://forge.example/org/repo/pulls/3")
    with TestClient(app) as client:
        _login(client)
        rows = {row["run_id"]: row for row in _get(client, "?limit=all")["items"]}
        for lifecycle, group in lifecycles.items():
            row = rows[lifecycle]
            assert row["lifecycle"] == lifecycle and row["status_group"] == group
            assert row["stage"] == "publishing"
            assert all(secret not in row["outcome"] for secret in ("opaque", "hide", "hidden"))
        assert rows["in-review"]["waiting"]["next_action"] == "review_draft_on_forge"
        assert rows["failed"]["waiting"]["next_action"] is None
        assert client.get(f"/api/v1/jobs/{items[0].project_id}/not-present").status_code == 404


def test_unreadable_source_and_orphan_run_are_not_empty_success(tmp_path, monkeypatch):
    """@brief IO failures and directories without state cannot disappear from totals."""
    _, _, stores, app = _fixture(tmp_path)
    original = Path.read_bytes
    path = stores[0].run_dir("same") / "state.json"
    def denied(self):
        if self == path:
            raise PermissionError("SECRET_HOST_PATH")
        return original(self)
    with TestClient(app) as client:
        _login(client)
        with monkeypatch.context() as patch:
            patch.setattr(Path, "read_bytes", denied)
            response = client.get("/api/v1/jobs-page")
            assert response.status_code == 503 and "SECRET_HOST_PATH" not in response.text
        stores[0].run_dir("orphan").mkdir()
        assert client.get("/api/v1/jobs-page").json() == {
            "detail": {"code": "run_state_corrupt"}}


def test_empty_legacy_project_and_absent_default_state_root(tmp_path):
    """@brief No persisted runs is a complete empty collection, including archived history."""
    profiles = ProfileStore(tmp_path / "home")
    item = profiles.create("empty")
    item.archived = True
    profiles.save(item)
    with TestClient(create_app(profiles.home)) as client:
        _login(client)
        page = _get(client)
        assert page["items"] == [] and page["total"] == 0 and page["complete"] is True
        assert page["counts"] == {}
        assert not profiles.default_store_root("empty").exists()


def test_free_text_masks_entire_quoted_and_authorization_credentials(tmp_path):
    """@brief Redaction consumes full credential values before exposing title or outcome."""
    _, items, stores, app = _fixture(tmp_path)
    stores[0].save_ticket("same", {"title": 'Actual title password="two word secret"'})
    _state(stores[0], "same", outcome="Authorization: Bearer opaquevalue; API_KEY='secret phrase'")
    with TestClient(app) as client:
        _login(client)
        response = client.get(f"/api/v1/jobs/{items[0].project_id}/same")
        assert response.status_code == 200
        assert all(secret not in response.text for secret in
                   ("two word secret", "word secret", "opaquevalue", "secret phrase", "phrase"))
        assert response.json()["job"]["ticket_title"].startswith("Actual title")


def test_stale_parked_questions_are_unknown_for_new_wait(tmp_path):
    """@brief A historical question cannot become an action for a newer parked round."""
    _, items, stores, app = _fixture(tmp_path)
    _state(stores[0], "same", lifecycle="parked-clarification", question_comment_id=7,
           parked_at="2026-10-05T12:00:00Z")
    stores[0].journal("same", "parked", ts="2026-10-05T11:00:00Z", questions="Old question")
    with TestClient(app) as client:
        _login(client)
        row = client.get(f"/api/v1/jobs/{items[0].project_id}/same").json()["job"]
        assert row["waiting"]["availability"] == "unknown"
        assert row["waiting"]["reason"] is None and row["waiting"]["next_action"] is None


def test_broken_runs_root_symlink_fails_closed(tmp_path, monkeypatch):
    """@brief A missing symlink target is corrupt evidence, not an empty legacy root."""
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("empty")
    root = profiles.default_store_root("empty") / "runs"
    original = Path.is_symlink
    def linked(self):
        return self == root or original(self)
    monkeypatch.setattr(Path, "is_symlink", linked)
    with TestClient(create_app(profiles.home)) as client:
        _login(client)
        response = client.get("/api/v1/jobs-page")
        assert response.status_code == 503


@pytest.mark.parametrize("payload", [b"\xff", pytest.param(
    b'{"name":"alpha","description":' + b'[' * 20000 + b'0' + b']' * 20000 + b'}',
    id="deep-profile")])
@pytest.mark.parametrize("role", ["admin", "developer"])
def test_corrupt_profile_decoding_is_typed_on_global_project_and_direct_reads(
        tmp_path, payload, role):
    """@brief Every job scope converts malformed profile decoding to a safe typed error."""
    profiles, items, _, app = _fixture(tmp_path)
    if role == "developer":
        dev = app.state.web_store.create_user("dev", "longer-password", "developer")
        app.state.web_store.set_memberships(dev["id"], ["alpha"])
    with TestClient(app, raise_server_exceptions=False) as client:
        _login(client) if role == "admin" else _login(client, "dev", "longer-password")
        path = profiles.profile_dir("alpha") / "profile.json"
        path.write_bytes(payload)
        for endpoint in ("/api/v1/jobs-page",
                         f"/api/v1/jobs-page?project_id={items[0].project_id}",
                         f"/api/v1/jobs/{items[0].project_id}/same"):
            response = client.get(endpoint)
            assert response.status_code == 503
            assert response.json() == {"detail": {"code": "project_corrupt"}}
        assert path.read_bytes() == payload


# END OF FILE


def test_job_preparation_projection_is_closed_and_rejects_false_success(tmp_path):
    """@brief Jobs expose authoritative outcomes without source/policy or false success."""
    from adore.preparation import resolve_plan

    from tests.test_preparation import SourceRunner, recipe_config

    _, items, stores, app = _fixture(tmp_path)
    plan = resolve_plan(recipe_config(), runner=SourceRunner())
    execution = {"plan": plan, "resource": {"container_id": "c" * 64,
        "image_id": "sha256:" + "d" * 64}, "status": "running", "attempts": 1,
        "steps": [{"index": 0, "name": plan["steps"][0]["name"],
            "started_at": "2026-10-07T10:00:00Z", "finished_at": "2026-10-07T10:00:01Z",
            "exit_code": 0, "timed_out": False, "cancelled": False}],
        "history": [], "reprepare": False}
    _state(stores[0], "same", execution=execution)
    url = f"/api/v1/jobs/{items[0].project_id}/same"
    with TestClient(app) as client:
        _login(client)
        response = client.get(url)
        assert response.status_code == 200, response.text
        projected = response.json()["job"]["preparation"]
        assert projected["image"] == "project:1" and projected["status"] == "running"
        assert set(projected) == {"status", "attempts", "image", "fingerprint", "steps"}
        assert "uv sync" not in response.text and '"policy"' not in response.text
        execution["status"] = "success"  # Missing the second step cannot claim success.
        _state(stores[0], "same", execution=execution)
        assert client.get(url).status_code == 503


@pytest.mark.parametrize("unit", ["x", "a.", "a-", "a+"])
def test_redact_text_stays_linear_on_long_word_runs(unit):
    """@brief Long identifier or dotted runs are redacted without a quadratic scan."""
    text = unit * (40_000 // len(unit)) + " token=abc123"
    started = time.monotonic()
    redacted = redact_text(text)
    assert time.monotonic() - started < 1.0
    assert redacted.endswith(" token=[REDACTED]")


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        ("clone https://oauth2:glpat-abcdefghij1234567890@gitlab.example/x.git",
         "glpat-abcdefghij1234567890"),
        ("remote https://user:hunter2@host/repo", "hunter2"),
        ("using ghp_abcdefghijklmnopqrstuvwxyz0123456789 now",
         "ghp_abcdefghijklmnopqrstuvwxyz0123456789"),
        ("found glpat-AbCdEfGhIjKlMnOpQrSt in a log", "glpat-AbCdEfGhIjKlMnOpQrSt"),
        ("github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz", "11ABCDEFG0123456789"),
    ],
)
def test_redact_text_masks_url_credentials_and_forge_tokens(raw, secret):
    """@brief Credentials in remote URLs and well-known forge tokens never reach the page."""
    redacted = redact_text(raw)
    assert secret not in redacted and "[REDACTED]" in redacted


def test_job_detail_shows_saved_launches_and_frozen_active_time(tmp_path):
    """@brief Counters and current limits remain available independently of statistics."""
    _, items, stores, app = _fixture(tmp_path)
    _state(stores[0], "same", lifecycle="parked-clarification", iterations=9,
           active_started_at="2026-10-05T09:58:30+00:00", updated_at="2026-10-05T10:00:00+00:00")
    with TestClient(app) as client:
        _login(client)
        response = client.get(f"/api/v1/jobs/{items[0].project_id}/same")
        assert response.status_code == 200, response.text
        budget = response.json()["job"]["budget"]
        assert budget["launches"] == 9 and budget["max_launches"] == 20
        assert budget["active_seconds"] == 90 and budget["max_active_seconds"] == 3600
        assert budget["availability"] == "observed" and budget["reason"] is None
        assert set(budget) == {"launches", "max_launches", "active_seconds",
                               "max_active_seconds", "config_revision", "availability", "reason"}


@pytest.mark.parametrize("corruption", ["counter", "clock"])
def test_job_budget_detail_refuses_corrupt_evidence(tmp_path, corruption):
    """@brief Corrupt saved work never becomes guessed zero consumption."""
    _, items, stores, app = _fixture(tmp_path)
    _state(stores[0], "same", **({"iterations": True} if corruption == "counter"
                                else {"active_started_at": "bad"}))
    with TestClient(app) as client:
        _login(client)
        response = client.get(f"/api/v1/jobs/{items[0].project_id}/same")
        assert response.status_code == 503, response.text


@pytest.mark.parametrize("config_state", [
    "missing", "syntax", "derived-type", "budget-value", "bytes",
])
def test_job_details_preserve_recovery_and_consumption_without_current_limits(
    tmp_path, config_state,
):
    """@brief Unavailable limits never erase valid saved evidence or recovery revision."""
    from hashlib import sha256

    profiles, items, stores, app = _fixture(tmp_path)
    _state(stores[0], "same", lifecycle="failed", iterations=9,
           outcome="BUDGET_EXHAUSTED: iteration budget reached (9/9)",
           active_started_at="2026-10-05T09:58:30+00:00", updated_at="2026-10-05T10:00:00+00:00")
    path = profiles.config_path("alpha")
    if config_state == "missing":
        path.unlink()
    elif config_state == "bytes":
        path.write_bytes(b"\xff\xfe")
    else:
        text = {"syntax": "[broken", "derived-type": "[agent]\nname = 1\n",
                "budget-value": "[budgets]\nmax_iterations = -1\n"}[config_state]
        path.write_text(text, encoding="utf-8")
    state_path = stores[0].run_dir("same") / "state.json"
    original = state_path.read_bytes()
    with TestClient(app, raise_server_exceptions=False) as client:
        _login(client)
        response = client.get(f"/api/v1/jobs/{items[0].project_id}/same")
        assert response.status_code == 200, response.text
        job = response.json()["job"]
        assert job["lifecycle"] == "failed"
        assert job["state_revision"] == sha256(original).hexdigest()
        budget = job["budget"]
        assert budget["launches"] == 9 and budget["active_seconds"] == 90
        assert budget["availability"] == "unavailable"
        expected_reason = "config_missing" if config_state == "missing" else "config_corrupt"
        assert budget["reason"] == expected_reason
        assert budget["max_launches"] is None and budget["max_active_seconds"] is None
        assert budget["config_revision"] is None
    assert state_path.read_bytes() == original


def test_job_budget_configuration_race_refuses_an_unbound_observation(tmp_path, monkeypatch):
    """@brief Config replacement during a detail read remains a 409, not unknown limits."""
    profiles, items, _, app = _fixture(tmp_path)
    selected = profiles.config_path("alpha")
    original = Path.read_bytes
    calls = 0

    def changing(path):
        """@brief Replace only the second selected-config byte read in this isolated fixture."""
        nonlocal calls
        if path == selected:
            calls += 1
            if calls == 2:
                path.write_bytes(original(path) + b"\n# concurrent configuration write\n")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", changing)
    with TestClient(app) as client:
        _login(client)
        result = client.get(f"/api/v1/jobs/{items[0].project_id}/same")
        assert result.status_code == 409, result.text
        assert result.json()["detail"]["code"] == "job_snapshot_changed"
