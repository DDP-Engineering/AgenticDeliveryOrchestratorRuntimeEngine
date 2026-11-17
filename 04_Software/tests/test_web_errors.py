"""Web API error-body contract tests."""

import re

from adore.profiles import ProfileStore
from adore.web.app import create_app
from adore.web.store import WebStoreError

from tests.configuration_client import TestClient

_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _admin(client: TestClient) -> dict:
    login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    return {"X-CSRF-Token": login.json()["csrf"]}


def _code(response, status: int, code: str) -> dict:
    """Assert one error response and return its detail object."""
    assert response.status_code == status, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, dict) and _CODE.fullmatch(detail["code"])
    assert detail["code"] == code
    assert set(detail) <= ({"code", "message", "issues"}
                           if code == "project_setup_invalid" else {"code", "message"})
    if "issues" in detail:
        assert detail["issues"]
        assert all(set(issue) == {"code", "field", "remediation"}
                   and all(isinstance(value, str) and value for value in issue.values())
                   for issue in detail["issues"])
    return detail


# TESTS
def test_account_failures_return_stable_codes(tmp_path):
    """Account-store sentences become identifiers with unchanged statuses."""
    app = create_app(tmp_path / "home")
    with TestClient(app) as client:
        headers = _admin(client)
        _code(client.post("/api/v1/users", headers=headers, json={
            "username": "bob", "password": "short"}), 400, "password_too_short")
        _code(client.post("/api/v1/users", headers=headers, json={
            "username": "bad name!", "password": "longer-password"}), 400, "invalid_username")
        _code(client.post("/api/v1/users", headers=headers, json={
            "username": "bob", "password": "longer-password", "role": "owner"}),
            400, "invalid_role")
        assert client.post("/api/v1/users", headers=headers, json={
            "username": "bob", "password": "longer-password"}).status_code == 200
        _code(client.post("/api/v1/users", headers=headers, json={
            "username": "bob", "password": "longer-password"}), 400, "username_exists")
        _code(client.post("/api/v1/users/1/disable", headers=headers),
              409, "last_administrator")
        _code(client.post("/api/v1/users/999/enable", headers=headers), 404, "user_not_found")
        _code(client.post("/api/v1/users/999/reset-password", headers=headers, json={
            "replacement": "longer-password"}), 404, "user_not_found")
        _code(client.put("/api/v1/users/999/projects", headers=headers, json={
            "projects": []}), 404, "user_not_found")
        _code(client.post("/api/v1/me/password", headers=headers, json={
            "current": "wrong-password", "replacement": "longer-password"}),
            400, "current_password_incorrect")
        _code(client.post("/api/v1/me/password", headers=headers, json={
            "current": "admin", "replacement": "short"}), 400, "password_too_short")


def test_request_validation_returns_invalid_request_with_field_reasons(tmp_path):
    """Body validation failures name fields without echoing input values."""
    app = create_app(tmp_path / "home")
    with TestClient(app) as client:
        headers = _admin(client)
        detail = _code(client.post("/api/v1/users/1/reset-password", headers=headers, json={
            "replacement": "secret7"}), 422, "invalid_request")
        assert "replacement" in detail["message"] and "secret7" not in detail["message"]
        _code(client.get("/api/v1/audit?limit=0"), 422, "invalid_audit_limit")


def test_unknown_api_routes_return_coded_errors(tmp_path):
    """API paths never fall through to the browser application shell."""
    app = create_app(tmp_path / "home")
    with TestClient(app) as client:
        _admin(client)
        detail = _code(client.get("/api/v1/no-such-route"), 404, "not_found")
        assert detail["message"]
        _code(client.post("/api/v1/no-such-route"), 405, "method_not_allowed")


def test_price_and_operation_conflicts_return_stable_codes(tmp_path):
    """Price and queue store conflicts keep 409 with identifiers."""
    home = tmp_path / "home"
    ProfileStore(home).create("alpha")
    app = create_app(home)
    price = {"executor": "codex", "model": "local-1", "effective_from": "2026-01-01",
             "input_usd_per_million": "2", "output_usd_per_million": "4"}
    with TestClient(app) as client:
        headers = _admin(client)
        assert client.post("/api/v1/projects/alpha/prices", headers=headers,
                           json=price).status_code == 201
        _code(client.post("/api/v1/projects/alpha/prices", headers=headers, json=price),
              409, "price_exists")
        key = {"idempotency_key": "operation-key-1"}
        assert client.post("/api/v1/projects/alpha/operations/pause", headers=headers,
                           json=key).status_code == 200
        _code(client.post("/api/v1/projects/alpha/operations/resume", headers=headers,
                          json=key), 409, "idempotency_conflict")


def test_full_job_queue_refuses_new_work_but_never_a_cancel(tmp_path, monkeypatch):
    """One project's queued starts are bounded; a repeated request and a cancel still pass."""
    home = tmp_path / "home"
    ProfileStore(home).create("alpha")
    ProfileStore(home).create("beta")
    app = create_app(home)
    monkeypatch.setattr("adore.web.store._QUEUED_WORK_LIMIT", 2)
    with TestClient(app) as client:
        headers = _admin(client)

        def start(project: str, ticket: int, key: str):
            return client.post(f"/api/v1/projects/{project}/operations/start", headers=headers,
                               json={"idempotency_key": key, "ticket_iid": ticket})

        first = start("alpha", 1, "start-key-1")
        assert first.status_code == 200 and start("alpha", 2, "start-key-2").status_code == 200
        _code(start("alpha", 3, "start-key-3"), 409, "operation_queue_full")
        # The same request again is answered with its operation, not counted anew.
        assert start("alpha", 1, "start-key-1").json()["id"] == first.json()["id"]
        # Each project has a queue of its own.
        assert start("beta", 1, "start-key-4").status_code == 200
        # Stopping a job is never refused by the limit.
        cancel = app.state.web_store.enqueue(1, "alpha", "cancel", "run-1", "cancel-key-1")
        assert cancel["status"] == "pending"


def test_project_setup_failure_keeps_diagnostic_in_message(tmp_path):
    """Wizard explanations survive beside a stable creation code."""
    app = create_app(tmp_path / "home")
    with TestClient(app) as client:
        headers = _admin(client)
        detail = _code(client.post("/api/v1/projects", headers=headers, json={
            "name": "alpha", "kind": "bogus-forge", "repo": "acme/alpha",
            "repo_path": str(tmp_path), "reviewers": "alice"}), 400, "project_setup_invalid")
        assert detail["message"]


def test_unmapped_store_failure_returns_request_rejected(tmp_path, monkeypatch):
    """An unexpected store sentence is never used as a code."""
    app = create_app(tmp_path / "home")

    def odd_failure(_user_id: int, *, actor_id: int | None = None) -> None:
        raise WebStoreError("odd store failure")

    monkeypatch.setattr(app.state.web_store, "enable_user", odd_failure)
    with TestClient(app) as client:
        headers = _admin(client)
        detail = _code(client.post("/api/v1/users/1/enable", headers=headers),
                       404, "request_rejected")
        assert detail["message"] == "odd store failure"
