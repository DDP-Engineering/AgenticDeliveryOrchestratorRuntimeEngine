#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""
@file    test_web_tickets.py
@brief   Contract tests for browsing and stopping project tickets over the web API.
@details The forge CLI is faked through the injectable probe runner: listing,
         comments and stop are read or written only on explicit requests, and
         forge output is a trust boundary that fails closed with typed errors.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore, derive_run_id
from adore.util import CommandResult
from adore.web.app import create_app
from adore.web.store import WebStore
from fastapi.testclient import TestClient
import pytest

# CONSTANTS

REPO = "mygroup/myproject"

# HELPER FUNCTIONS


def _project(tmp_path: Path) -> ProfileStore:
    """
    @brief      Create an offline GitLab project with real config storage.
    @param[in]  tmp_path Test directory.
    @return     The profile store.
    """
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    raw = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text()
    raw = raw.replace('store_root = ".adore"', f'store_root = "{(tmp_path / "state").as_posix()}"')
    raw = raw.replace('repo = "group/subgroup/project"', f'repo = "{REPO}"')
    profiles.config_path("alpha").write_text(raw, encoding="utf-8")
    return profiles


def _issue(iid: int, *labels: str, title: str = "") -> dict[str, object]:
    """
    @brief      One glab issue record.
    @param[in]  iid Issue number.
    @param[in]  labels Issue labels.
    @param[in]  title Optional title.
    @return     The raw record.
    """
    return {
        "iid": iid,
        "title": title or f"Ticket {iid}",
        "description": f"Body {iid}",
        "labels": list(labels),
        "author": {"username": "dev"},
        "state": "opened",
        "web_url": f"https://gitlab.example/i/{iid}",
        "created_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-02T10:00:00Z",
    }


class Forge:
    """
    @brief   Fake glab boundary dispatching on the command vector.
    """

    def __init__(
        self, issues: list[dict[str, object]] | str, notes: object = None, fail: str = ""
    ) -> None:
        """
        @brief      Configure canned issue list, notes and an optional failing command.
        @param[in]  issues Issue records, or raw stdout text for corrupt output.
        @param[in]  notes Note records for the comments endpoint.
        @param[in]  fail Command word ("list", "view", "update", "notes") that fails.
        """
        self.issues, self.notes, self.fail = issues, notes or [], fail
        self.calls: list[list[str]] = []

    def __call__(self, argv, *, cwd=None, timeout=None, env=None) -> CommandResult:
        """
        @brief      Answer one glab call.
        @return     The canned CommandResult.
        """
        argv = [str(part) for part in argv]
        self.calls.append(argv)
        word = "notes" if argv[:2] == ["glab", "api"] else argv[2] if len(argv) > 2 else ""
        if word == self.fail:
            return CommandResult(argv=argv, exit_code=1, stdout="", stderr="forge unavailable")
        if word == "list":
            stdout = self.issues if isinstance(self.issues, str) else json.dumps(self.issues)
        elif word == "view":
            iid = int(argv[3])
            match = [item for item in self.issues if isinstance(item, dict) and item["iid"] == iid]
            if not match:
                return CommandResult(argv=argv, exit_code=1, stdout="", stderr="404 Not Found")
            stdout = json.dumps(match[0])
        elif word == "notes":
            stdout = self.notes if isinstance(self.notes, str) else json.dumps(self.notes)
        else:
            stdout = ""
        return CommandResult(argv=argv, exit_code=0, stdout=stdout, stderr="")


def _admin(client: TestClient) -> str:
    """
    @brief      Sign in as the bootstrap administrator.
    @return     The CSRF token.
    """
    return client.post("/api/v1/session", json={"username": "admin", "password": "admin"}).json()[
        "csrf"
    ]


def _developer(profiles: ProfileStore, client: TestClient, member: bool) -> str:
    """
    @brief      Create and sign in a developer, optionally assigned to alpha.
    @return     The CSRF token.
    """
    web = WebStore(profiles.home / "web.db")
    user = web.create_user("dev", "longer-password", "developer")
    if member:
        web.set_memberships(user["id"], ["alpha"])
    return client.post(
        "/api/v1/session", json={"username": "dev", "password": "longer-password"}
    ).json()["csrf"]


def _run(tmp_path: Path, iid: int, lifecycle: str) -> str:
    """
    @brief      Persist a run for one ticket.
    @return     The run id.
    """
    run_id = derive_run_id("gitlab", REPO, iid)
    StateStore(str(tmp_path / "state")).save(
        RunState(run_id=run_id, ticket_iid=iid, lifecycle=lifecycle)
    )
    return run_id


# PUBLIC API / TESTS - listing


def test_admin_lists_open_tickets_with_eligibility_and_job_state(tmp_path: Path) -> None:
    """
    @brief   Open tickets carry the shared eligibility reason and any existing job.
    """
    profiles = _project(tmp_path)
    run_id = _run(tmp_path, 14, "working")
    forge = Forge(
        [_issue(12, "agent-ready", "P2"), _issue(13, "P2"), _issue(14, "agent-working", "P2")]
    )
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        _admin(client)
        response = client.get("/api/v1/projects/alpha/tickets")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["truncated"] is False and body["ready_label"] == "agent-ready" and body["read_at"]
    rows = {row["iid"]: row for row in body["tickets"]}
    assert rows[12]["startable"] is True and rows[12]["reason"] is None and rows[12]["job"] is None
    assert rows[12]["description"] == "Body 12" and rows[12]["labels"] == ["agent-ready", "P2"]
    assert rows[13]["startable"] is False and rows[13]["reason"] == "missing_ready_label"
    assert rows[14]["job"] == {"run_id": run_id, "lifecycle": "working"}
    assert rows[14]["reason"] == "missing_ready_label"
    assert all("--label" not in call for call in forge.calls)


def test_listing_flags_truncation_beyond_500_tickets(tmp_path: Path) -> None:
    """
    @brief   More than 500 open tickets are cut at 500 and flagged.
    """
    profiles = _project(tmp_path)
    issues = [_issue(i) for i in range(1, 502)]

    def runner(argv, *, cwd=None, timeout=None, env=None):
        page = int(argv[argv.index("--page") + 1])
        return CommandResult(
            argv=list(argv), exit_code=0, stdout=json.dumps(issues[(page - 1) * 100 : page * 100])
        )

    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        _admin(client)
        body = client.get("/api/v1/projects/alpha/tickets").json()
    assert body["truncated"] is True and len(body["tickets"]) == 500


def test_assigned_developer_lists_and_unassigned_developer_cannot(tmp_path: Path) -> None:
    """
    @brief   Ticket reads follow project access.
    """
    profiles = _project(tmp_path)
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(12, "agent-ready", "P2")]))
    ) as client:
        _developer(profiles, client, member=True)
        assert client.get("/api/v1/projects/alpha/tickets").status_code == 200
    other = _project(tmp_path / "other")
    with TestClient(create_app(other.home, probe_runner=Forge([]))) as client:
        _developer(other, client, member=False)
        response = client.get("/api/v1/projects/alpha/tickets")
    assert response.status_code == 404 and response.json()["detail"]["code"] == "project_not_found"


@pytest.mark.parametrize(
    ("forge", "status", "code"),
    [
        (Forge([], fail="list"), 503, "forge_read_failed"),
        (Forge("not json"), 502, "forge_response_invalid"),
        (Forge([{"title": "no number"}]), 502, "forge_response_invalid"),
    ],
)
def test_listing_failures_return_typed_errors_and_no_partial_list(
    tmp_path: Path, forge: Forge, status: int, code: str
) -> None:
    """
    @brief   Failing or malformed forge output never yields a partial list.
    """
    profiles = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        _admin(client)
        response = client.get("/api/v1/projects/alpha/tickets")
    assert response.status_code == status and response.json()["detail"]["code"] == code
    assert "tickets" not in response.json()


# PUBLIC API / TESTS - comments


def test_comments_are_human_ordered_and_skip_system_notes(tmp_path: Path) -> None:
    """
    @brief   Comments keep forge order and omit system notes.
    """
    profiles = _project(tmp_path)
    notes = [
        {
            "id": 1,
            "body": "First",
            "author": {"username": "ana"},
            "created_at": "2026-10-01T10:00:00Z",
        },
        {
            "id": 2,
            "body": "added label",
            "author": {"username": "bot"},
            "created_at": "2026-10-01T11:00:00Z",
            "system": True,
        },
        {
            "id": 3,
            "body": "<script>x</script>",
            "author": {"username": "ion"},
            "created_at": "2026-10-01T12:00:00Z",
        },
    ]
    with TestClient(create_app(profiles.home, probe_runner=Forge([_issue(12)], notes))) as client:
        _admin(client)
        response = client.get("/api/v1/projects/alpha/tickets/12/comments")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "iid": 12,
        "comments": [
            {"author": "ana", "created_at": "2026-10-01T10:00:00Z", "body": "First"},
            {"author": "ion", "created_at": "2026-10-01T12:00:00Z", "body": "<script>x</script>"},
        ],
    }


@pytest.mark.parametrize(
    ("forge", "status", "code"),
    [
        (Forge([]), 404, "ticket_not_found"),
        (Forge([_issue(12)], fail="notes"), 503, "forge_read_failed"),
        (Forge([_issue(12)], notes=[{"body": "no id"}]), 502, "forge_response_invalid"),
        (Forge([_issue(12)], notes=[{"id": 1, "body": {"x": 1}}]), 502, "forge_response_invalid"),
    ],
)
def test_comment_failures_are_typed(tmp_path: Path, forge: Forge, status: int, code: str) -> None:
    """
    @brief   Missing tickets and bad forge output return typed errors.
    """
    profiles = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        _admin(client)
        response = client.get("/api/v1/projects/alpha/tickets/12/comments")
    assert response.status_code == status and response.json()["detail"]["code"] == code


# PUBLIC API / TESTS - stop


def _audit(profiles: ProfileStore) -> list[dict[str, object]]:
    """
    @brief      Read the structured evidence of ticket stop audit rows.
    @return     Evidence payloads in insertion order.
    """
    with sqlite3.connect(profiles.home / "web.db") as connection:
        rows = connection.execute(
            "SELECT evidence FROM audit WHERE action='ticket-stopped' ORDER BY id"
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def test_stop_queues_cancel_removes_ready_label_and_audits(tmp_path: Path) -> None:
    """
    @brief   Stop cancels the unfinished job and removes the ready label.
    """
    profiles = _project(tmp_path)
    run_id = _run(tmp_path, 12, "working")
    forge = Forge([_issue(12, "agent-ready", "agent-working")])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        csrf = _admin(client)
        response = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
    operation = WebStore(profiles.home / "web.db").operation(body["cancel_operation_id"])
    assert body["ready_label"] == "removed" and body["ready_label_error"] is None
    assert operation["action"] == "cancel" and operation["run_id"] == run_id
    assert [
        "glab",
        "issue",
        "update",
        "12",
        "--repo",
        REPO,
        "--unlabel",
        "agent-ready",
    ] in forge.calls
    evidence = _audit(profiles)
    assert len(evidence) == 1 and evidence[0]["resource_id"] == "12"
    assert evidence[0]["operation_id"] == body["cancel_operation_id"]
    assert evidence[0]["result"] == "applied"


def test_stop_without_job_or_ready_label_changes_nothing_extra(tmp_path: Path) -> None:
    """
    @brief   No job means no cancel; no ready label means no forge write.
    """
    profiles = _project(tmp_path)
    _run(tmp_path, 13, "done")
    forge = Forge([_issue(12, "agent-ready"), _issue(13, "P2")])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        csrf = _admin(client)
        first = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        ).json()
        second = client.post(
            "/api/v1/projects/alpha/tickets/13/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-13"},
        ).json()
    assert first == {
        "cancel_operation_id": None,
        "ready_label": "removed",
        "ready_label_error": None,
    }
    assert second == {
        "cancel_operation_id": None,
        "ready_label": "absent",
        "ready_label_error": None,
    }
    assert not any(call[2:4] == ["update", "13"] for call in forge.calls)


def test_stop_reports_label_failure_but_keeps_queued_cancel(tmp_path: Path) -> None:
    """
    @brief   A forge write failure after queueing is reported, not rolled back.
    """
    profiles = _project(tmp_path)
    _run(tmp_path, 12, "working")
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(12, "agent-ready")], fail="update"))
    ) as client:
        csrf = _admin(client)
        body = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        ).json()
    assert body["cancel_operation_id"] is not None
    assert body["ready_label"] == "failed" and body["ready_label_error"] == "forge_write_failed"
    assert [row["result"] for row in _audit(profiles)] == ["uncertain"]


def test_stop_rejects_missing_ticket_archived_project_csrf_and_foreign_developer(
    tmp_path: Path,
) -> None:
    """
    @brief   Stop follows the mutation, archive and access boundaries.
    """
    profiles = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=Forge([]))) as client:
        csrf = _admin(client)
        missing = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        )
        no_csrf = client.post(
            "/api/v1/projects/alpha/tickets/12/stop", json={"idempotency_key": "stop-ticket-12"}
        )
        assert (
            client.post(
                "/api/v1/projects/alpha/archive", headers={"X-CSRF-Token": csrf}
            ).status_code
            == 200
        )
        archived = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12b"},
        )
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "ticket_not_found"
    assert no_csrf.status_code == 403 and no_csrf.json()["detail"]["code"] == "csrf_required"
    assert archived.status_code == 409 and archived.json()["detail"]["code"] == "project_archived"
    other = _project(tmp_path / "other")
    with TestClient(
        create_app(other.home, probe_runner=Forge([_issue(12, "agent-ready")]))
    ) as client:
        csrf = _developer(other, client, member=False)
        foreign = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        )
    assert foreign.status_code == 404 and foreign.json()["detail"]["code"] == "project_not_found"


def test_corrupt_run_state_is_reported_as_local_state_not_forge(tmp_path: Path) -> None:
    """
    @brief   An unreadable run for a listed ticket returns run_state_corrupt.
    """
    profiles = _project(tmp_path)
    run_id = derive_run_id("gitlab", REPO, 12)
    store = StateStore(str(tmp_path / "state"))
    store.save(RunState(run_id=run_id, ticket_iid=12, lifecycle="working"))
    for path in (tmp_path / "state").rglob("*.json"):
        if run_id in str(path):
            path.write_text("{not json", encoding="utf-8")
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(12, "agent-ready")]))
    ) as client:
        _admin(client)
        response = client.get("/api/v1/projects/alpha/tickets")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "run_state_corrupt"


def test_stop_reports_malformed_ticket_after_queueing_cancel(tmp_path: Path) -> None:
    """
    @brief   A malformed ticket record is a typed label failure, not a server error.
    """
    profiles = _project(tmp_path)
    _run(tmp_path, 12, "working")
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([{"iid": 12, "author": "not-a-mapping"}]))
    ) as client:
        csrf = _admin(client)
        response = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cancel_operation_id"] is not None and body["ready_label"] == "failed"
    assert body["ready_label_error"] == "forge_response_invalid"
    assert [row["result"] for row in _audit(profiles)] == ["uncertain"]


def test_stop_cancels_even_when_repository_credentials_are_corrupt(tmp_path: Path) -> None:
    """
    @brief   Unusable credentials fail only the label step, never the local cancel.
    """
    profiles = _project(tmp_path)
    _run(tmp_path, 12, "working")
    (profiles.profile_dir("alpha") / "repository-auth.json").write_text(
        "{corrupt", encoding="utf-8"
    )
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(12, "agent-ready")]))
    ) as client:
        csrf = _admin(client)
        body = client.post(
            "/api/v1/projects/alpha/tickets/12/stop",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "stop-ticket-12"},
        ).json()
    assert body["cancel_operation_id"] is not None and body["ready_label"] == "failed"
    assert body["ready_label_error"] == "repository_credentials_corrupt"


def test_unassigned_developer_cannot_read_comments(tmp_path: Path) -> None:
    """
    @brief   Comment reads follow project access like the ticket list.
    """
    profiles = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=Forge([_issue(12)]))) as client:
        _developer(profiles, client, member=False)
        response = client.get("/api/v1/projects/alpha/tickets/12/comments")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "project_not_found"


# PUBLIC API / TESTS - start preparation


def _start(
    client: TestClient, csrf: str, iid: int, priority: str = "", key: str = "start-ticket-1"
):
    """
    @brief      Post a ticket start request.
    @return     The response.
    """
    body: dict[str, object] = {"idempotency_key": key}
    if priority:
        body["priority"] = priority
    return client.post(
        f"/api/v1/projects/alpha/tickets/{iid}/start", headers={"X-CSRF-Token": csrf}, json=body
    )


def _starts(profiles: ProfileStore) -> list[dict[str, object]]:
    """
    @brief      Read queued start operations.
    @return     Operation rows.
    """
    with sqlite3.connect(profiles.home / "web.db") as connection:
        connection.row_factory = sqlite3.Row
        return [
            dict(row)
            for row in connection.execute(
                "SELECT action, run_id FROM operations WHERE action='start' ORDER BY id"
            )
        ]


def test_listing_reports_what_start_would_add(tmp_path: Path) -> None:
    """
    @brief   Each ticket says whether Start can fix it with labels and which ones.
    """
    profiles = _project(tmp_path)
    issues = [
        _issue(12, "agent-ready", "P2"),
        _issue(13, "P2"),
        _issue(14),
        _issue(15, "agent-hold"),
    ]
    with TestClient(create_app(profiles.home, probe_runner=Forge(issues))) as client:
        _admin(client)
        body = client.get("/api/v1/projects/alpha/tickets").json()
    rows = {row["iid"]: row for row in body["tickets"]}
    assert body["priority_labels"] == ["P1", "P2", "P3"]
    assert (rows[12]["can_start"], rows[12]["adds_ready_label"], rows[12]["needs_priority"]) == (
        True,
        False,
        False,
    )
    assert (rows[13]["can_start"], rows[13]["adds_ready_label"], rows[13]["needs_priority"]) == (
        True,
        True,
        False,
    )
    assert (rows[14]["can_start"], rows[14]["adds_ready_label"], rows[14]["needs_priority"]) == (
        True,
        True,
        True,
    )
    assert (rows[15]["can_start"], rows[15]["adds_ready_label"], rows[15]["needs_priority"]) == (
        False,
        False,
        False,
    )
    assert rows[15]["blocked_by"] == "held" and rows[13]["blocked_by"] is None


def test_start_eligible_ticket_queues_without_forge_write(tmp_path: Path) -> None:
    """
    @brief   An already eligible ticket is only queued.
    """
    profiles = _project(tmp_path)
    forge = Forge([_issue(12, "agent-ready", "P2")])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        response = _start(client, _admin(client), 12)
    assert response.status_code == 200, response.text
    assert response.json()["labels_added"] == [] and response.json()["operation_id"] >= 1
    assert not any(call[2:3] == ["update"] for call in forge.calls)
    assert _starts(profiles) == [{"action": "start", "run_id": "12"}]


def test_start_adds_missing_labels_then_queues_and_audits(tmp_path: Path) -> None:
    """
    @brief   Missing ready and priority labels are added before the start is queued.
    """
    profiles = _project(tmp_path)
    forge = Forge([_issue(13, "P2"), _issue(14)])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        csrf = _admin(client)
        ready_only = _start(client, csrf, 13, key="start-ticket-13")
        both = _start(client, csrf, 14, priority="P3", key="start-ticket-14")
    assert ready_only.json()["labels_added"] == ["agent-ready"]
    assert both.json()["labels_added"] == ["agent-ready", "P3"]
    assert [
        "glab",
        "issue",
        "update",
        "13",
        "--repo",
        REPO,
        "--label",
        "agent-ready",
    ] in forge.calls
    assert [
        "glab",
        "issue",
        "update",
        "14",
        "--repo",
        REPO,
        "--label",
        "agent-ready",
        "--label",
        "P3",
    ] in forge.calls
    assert [row["run_id"] for row in _starts(profiles)] == ["13", "14"]
    with sqlite3.connect(profiles.home / "web.db") as connection:
        actions = [
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit WHERE action='ticket-start-prepared'"
            )
        ]
    assert actions == ["ticket-start-prepared", "ticket-start-prepared"]


@pytest.mark.parametrize("priority", ["", "P9"])
def test_start_without_valid_priority_choice_changes_nothing(tmp_path: Path, priority: str) -> None:
    """
    @brief   A ticket needing a priority requires a configured priority label.
    """
    profiles = _project(tmp_path)
    forge = Forge([_issue(14)])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        response = _start(client, _admin(client), 14, priority=priority)
    assert response.status_code == 400 and response.json()["detail"]["code"] == "priority_required"
    assert not any(call[2:3] == ["update"] for call in forge.calls) and _starts(profiles) == []


@pytest.mark.parametrize(
    ("issue", "has_run", "reason"),
    [
        (_issue(12, "agent-ready", "P2", "agent-hold"), False, "held"),
        (_issue(12, "agent-ready", "P2", "no-agent"), False, "excluded"),
        ({**_issue(12, "agent-ready", "P2"), "state": "closed"}, False, "not_open"),
        (_issue(12, "agent-ready", "P2"), True, "has_job"),
    ],
)
def test_start_refuses_rules_labels_cannot_fix(
    tmp_path: Path, issue: dict[str, object], has_run: bool, reason: str
) -> None:
    """
    @brief   Hold, exclude, closed state and existing runs block Start without side effects.
    """
    profiles = _project(tmp_path)
    if has_run:
        _run(tmp_path, 12, "failed")
    forge = Forge([issue])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        response = _start(client, _admin(client), 12, priority="P2")
    detail = response.json()["detail"]
    assert response.status_code == 409 and detail["code"] == "ticket_not_startable"
    assert detail["message"] == reason
    assert not any(call[2:3] == ["update"] for call in forge.calls) and _starts(profiles) == []


def test_start_label_write_failure_queues_nothing(tmp_path: Path) -> None:
    """
    @brief   A failed forge write leaves no queued start.
    """
    profiles = _project(tmp_path)
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(13, "P2")], fail="update"))
    ) as client:
        response = _start(client, _admin(client), 13)
    assert response.status_code == 503 and response.json()["detail"]["code"] == "forge_write_failed"
    assert _starts(profiles) == []


def test_start_follows_archive_csrf_access_and_missing_ticket_boundaries(tmp_path: Path) -> None:
    """
    @brief   Start uses the mutation, archive and access boundaries.
    """
    profiles = _project(tmp_path)
    with TestClient(create_app(profiles.home, probe_runner=Forge([]))) as client:
        csrf = _admin(client)
        missing = _start(client, csrf, 12)
        no_csrf = client.post(
            "/api/v1/projects/alpha/tickets/12/start", json={"idempotency_key": "start-ticket-x"}
        )
        client.post("/api/v1/projects/alpha/archive", headers={"X-CSRF-Token": csrf})
        archived = _start(client, csrf, 12, key="start-ticket-2")
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "ticket_not_found"
    assert no_csrf.status_code == 403
    assert archived.status_code == 409 and archived.json()["detail"]["code"] == "project_archived"
    other = _project(tmp_path / "other")
    with TestClient(
        create_app(other.home, probe_runner=Forge([_issue(12, "agent-ready", "P2")]))
    ) as client:
        foreign = _start(client, _developer(other, client, member=False), 12)
    assert foreign.status_code == 404 and foreign.json()["detail"]["code"] == "project_not_found"


def _pickup(tmp_path: Path, stopped: bool) -> None:
    """
    @brief      Stop or start the project's pickup the way `adore pause/resume` do.
    @param[in]  tmp_path Test directory holding the project's state root.
    @param[in]  stopped True to stop pickup, False to start it.
    """
    state = StateStore(tmp_path / "state")
    if stopped:
        state.pause()
    else:
        state.resume()


def _prepared(profiles: ProfileStore) -> int:
    """
    @brief      Count recorded prepared starts.
    @return     Number of ticket-start-prepared audit rows.
    """
    with sqlite3.connect(profiles.home / "web.db") as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM audit WHERE action='ticket-start-prepared'"
        ).fetchone()[0]


def test_start_with_pickup_stopped_is_refused_before_any_label(tmp_path: Path) -> None:
    """
    @brief   Stopped pickup refuses Start with no label, queue or prepared start.
    """
    profiles = _project(tmp_path)
    forge = Forge([_issue(13, "P2")])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        csrf = _admin(client)
        _pickup(tmp_path, stopped=True)
        refused = _start(client, csrf, 13, key="start-while-stopped")
        writes_while_stopped = [call for call in forge.calls if call[2:3] == ["update"]]
        starts_while_stopped, prepared_while_stopped = _starts(profiles), _prepared(profiles)
        _pickup(tmp_path, stopped=False)
        resumed = _start(client, csrf, 13, key="start-after-resume")
    assert refused.status_code == 409
    assert refused.json()["detail"] == {"code": "ticket_not_startable", "message": "pickup_paused"}
    assert writes_while_stopped == [] and starts_while_stopped == [] and prepared_while_stopped == 0
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["labels_added"] == ["agent-ready"]
    assert _starts(profiles) == [{"action": "start", "run_id": "13"}]


def test_start_replay_from_before_pickup_stopped_returns_original_operation(
    tmp_path: Path,
) -> None:
    """
    @brief   A start queued before pickup stopped replays its operation, not a refusal.
    """
    profiles = _project(tmp_path)
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(12, "agent-ready", "P2")]))
    ) as client:
        csrf = _admin(client)
        first = _start(client, csrf, 12, key="start-before-stop")
        _pickup(tmp_path, stopped=True)
        replay = _start(client, csrf, 12, key="start-before-stop")
    assert replay.status_code == 200, replay.text
    assert replay.json()["operation_id"] == first.json()["operation_id"]


def test_listing_with_pickup_stopped_blocks_start_by_pickup_paused(tmp_path: Path) -> None:
    """
    @brief   Stopped pickup makes Start unavailable without changing pickup eligibility.
    """
    profiles = _project(tmp_path)
    issues = [_issue(12, "agent-ready", "P2"), _issue(13, "P2"), _issue(15, "agent-hold")]
    with TestClient(create_app(profiles.home, probe_runner=Forge(issues))) as client:
        _admin(client)
        active = {row["iid"]: row for row in client.get("/api/v1/projects/alpha/tickets").json()[
            "tickets"]}
        _pickup(tmp_path, stopped=True)
        stopped = {row["iid"]: row for row in client.get("/api/v1/projects/alpha/tickets").json()[
            "tickets"]}
    for iid in (12, 13):
        row = stopped[iid]
        assert (row["can_start"], row["blocked_by"], row["adds_ready_label"],
                row["needs_priority"]) == (False, "pickup_paused", False, False)
    assert active[12]["can_start"] and active[13]["adds_ready_label"]
    assert stopped[15]["blocked_by"] == "held" and stopped[15] == active[15]
    for iid in (12, 13, 15):
        assert (stopped[iid]["startable"], stopped[iid]["reason"]) == (
            active[iid]["startable"], active[iid]["reason"])


def test_start_replay_with_same_key_returns_original_operation(tmp_path: Path) -> None:
    """
    @brief   Replaying a start key returns the queued operation even after a run exists.
    """
    profiles = _project(tmp_path)
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(12, "agent-ready", "P2")]))
    ) as client:
        csrf = _admin(client)
        first = _start(client, csrf, 12, key="start-ticket-replay")
        _run(tmp_path, 12, "working")
        replay = _start(client, csrf, 12, key="start-ticket-replay")
    assert replay.status_code == 200, replay.text
    assert replay.json()["operation_id"] == first.json()["operation_id"]
    assert len(_starts(profiles)) == 1


def test_start_label_write_failure_is_audited_as_uncertain(tmp_path: Path) -> None:
    """
    @brief   A forge write failure leaves an uncertain audit row and nothing queued.
    """
    profiles = _project(tmp_path)
    with TestClient(
        create_app(profiles.home, probe_runner=Forge([_issue(13, "P2")], fail="update"))
    ) as client:
        _start(client, _admin(client), 13)
    with sqlite3.connect(profiles.home / "web.db") as connection:
        rows = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT evidence FROM audit WHERE action='ticket-start-prepared'"
            )
        ]
    assert [row["result"] for row in rows] == ["uncertain"] and rows[0]["operation_id"] is None


def test_start_refuses_ticket_without_required_acceptance_criteria(tmp_path: Path) -> None:
    """
    @brief   Labels cannot replace required acceptance criteria.
    """
    profiles = _project(tmp_path)
    path = profiles.config_path("alpha")
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("require_acceptance_criteria = false", "require_acceptance_criteria = true"),
        encoding="utf-8",
    )
    forge = Forge([_issue(13, "P2")])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        response = _start(client, _admin(client), 13)
    detail = response.json()["detail"]
    assert response.status_code == 409 and detail["code"] == "ticket_not_startable"
    assert detail["message"] == "missing_acceptance_criteria"
    assert not any(call[2:3] == ["update"] for call in forge.calls) and _starts(profiles) == []


def test_start_with_malformed_ticket_record_is_a_bad_gateway(tmp_path: Path) -> None:
    """
    @brief   A malformed ticket record during Start is reported as invalid forge data.
    """
    profiles = _project(tmp_path)
    forge = Forge([{"iid": 12, "author": "not-a-mapping"}])
    with TestClient(create_app(profiles.home, probe_runner=forge)) as client:
        response = _start(client, _admin(client), 12)
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "forge_response_invalid"


# END OF FILE
