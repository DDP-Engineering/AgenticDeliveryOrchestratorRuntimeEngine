"""Public authentication and durable bootstrap contract tests."""

import shutil
import sqlite3

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.web.app import create_app
import adore.web.store as store_module
from adore.web.store import WebStore, WebStoreError
from fastapi.testclient import TestClient
import pytest

from tests.execution_records import execution_record

pytestmark = pytest.mark.real_password_hashing


def test_default_admin_is_hashed_and_preserved(tmp_path):
    """A fresh install permits login and a restart preserves changes."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    assert admin["role"] == "admin"
    with sqlite3.connect(path) as connection:
        raw = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert raw != "admin" and raw.startswith("$argon2id$")
    store.change_password(admin["id"], "admin", "replacement-long-password")
    assert WebStore(path).authenticate("admin", "replacement-long-password")
    assert WebStore(path).authenticate("admin", "admin") is None


def test_account_preferences_follow_the_user(tmp_path):
    """Locale/theme belong to accounts and persist when the store reopens."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    dev = store.create_user("dev", "longer-password", "developer")
    assert store.preferences(admin["id"]) == {
        "language": None, "theme": None, "ticket_body_mode": None}
    assert store.set_preferences(admin["id"], {"language": "ro"}) == {
        "language": "ro", "theme": None, "ticket_body_mode": None,
    }
    assert store.set_preferences(admin["id"], {"theme": "dark"}) == {
        "language": "ro", "theme": "dark", "ticket_body_mode": None,
    }
    assert WebStore(path).preferences(admin["id"]) == {
        "language": "ro", "theme": "dark", "ticket_body_mode": None}
    assert WebStore(path).preferences(dev["id"]) == {
        "language": None, "theme": None, "ticket_body_mode": None}
    assert WebStore(path).authenticate("admin", "admin")


def test_account_preferences_reject_corrupt_or_unsupported_values(tmp_path):
    """Invalid writes and corrupt persisted settings fail closed."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    with pytest.raises(WebStoreError):
        store.set_preferences(admin["id"], {"language": "es"})
    with pytest.raises(WebStoreError):
        store.set_preferences(admin["id"], {"theme": "neon"})
    store.set_preferences(admin["id"], {"language": "fr"})
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE user_preferences SET language='invalid'")
    with pytest.raises(WebStoreError, match="preferences"):
        store.preferences(admin["id"])


def test_ticket_body_mode_round_trip_and_partial_updates(tmp_path):
    """Ticket modes persist per account without overwriting other fields."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    dev = store.create_user("dev", "longer-password", "developer")
    assert store.preferences(admin["id"])["ticket_body_mode"] is None
    for mode in ("source", "rendered"):
        saved = store.set_preferences(admin["id"], {"ticket_body_mode": mode})
        assert saved["ticket_body_mode"] == mode
        store.set_preferences(admin["id"], {"language": "ro", "theme": "dark"})
        assert WebStore(path).preferences(admin["id"]) == {
            "language": "ro", "theme": "dark", "ticket_body_mode": mode,
        }
        assert WebStore(path).preferences(dev["id"])["ticket_body_mode"] is None


@pytest.mark.parametrize("mode", ["invalid", "", None, 1, True, [], {}])
def test_ticket_body_mode_store_rejects_invalid_update(tmp_path, mode):
    """Invalid direct writes preserve the last confirmed mode."""
    store = WebStore(tmp_path / "web.db")
    admin = store.authenticate("admin", "admin")
    before = store.set_preferences(admin["id"], {"ticket_body_mode": "source"})
    with pytest.raises(WebStoreError, match="invalid account preferences"):
        store.set_preferences(admin["id"], {"ticket_body_mode": mode})
    assert store.preferences(admin["id"]) == before


@pytest.mark.parametrize("mode", ["invalid", "", 1])
def test_ticket_body_mode_corrupt_read_and_partial_write_refused(tmp_path, mode):
    """Corrupt saved modes fail typed without partial-write repair."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    store.set_preferences(admin["id"], {"ticket_body_mode": "source", "theme": "dark"})
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE user_preferences SET ticket_body_mode=?", (mode,))
        before = connection.execute("SELECT * FROM user_preferences").fetchall()
    raw = path.read_bytes()
    with pytest.raises(WebStoreError, match="preferences"):
        store.preferences(admin["id"])
    assert path.read_bytes() == raw
    with pytest.raises(WebStoreError, match="preferences"):
        store.set_preferences(admin["id"], {"theme": "light"})
    with pytest.raises(WebStoreError, match="preferences"):
        store.set_preferences(admin["id"], {"ticket_body_mode": "rendered"})
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT * FROM user_preferences").fetchall() == before


@pytest.mark.parametrize("damage", ["old_version", "missing_column"])
def test_ticket_mode_schema_refusal_preserves_store(tmp_path, damage):
    """Old or incomplete stores are refused, never upgraded or recreated."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        if damage == "old_version":
            connection.execute("PRAGMA user_version=15")
        else:
            connection.execute("ALTER TABLE user_preferences DROP COLUMN ticket_body_mode")
    before = path.read_bytes()
    with pytest.raises(WebStoreError, match=(
            r"delete .*web\.db.*web\.db\.initialized" if damage == "old_version"
            else "missing account preferences")):
        WebStore(path)
    assert path.read_bytes() == before


def test_project_grant_follows_immutable_id_after_rename(tmp_path):
    """A renamed project retains grants; a recycled name cannot take them."""
    home = tmp_path / "home"
    profiles = ProfileStore(home)
    original = profiles.create("alpha")
    store = WebStore(home / "web.db")
    dev = store.create_user("dev", "longer-password", "developer")
    store.set_memberships(dev["id"], ["alpha"])
    profiles.rename("alpha", "renamed")
    profiles.create("alpha")
    assert profiles.load("renamed").project_id == original.project_id
    assert store.memberships(dev["id"]) == {"renamed"}
    with sqlite3.connect(home / "web.db") as connection:
        connection.execute("UPDATE memberships SET project_id='bad' WHERE user_id=?",
                           (dev["id"],))
    with pytest.raises(WebStoreError, match="membership identity"):
        store.memberships(dev["id"])


def test_schema_four_missing_membership_identity_fails_closed(tmp_path):
    """A claimed current schema cannot omit its project grant key."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE memberships DROP COLUMN profile_created_at")
    with pytest.raises(WebStoreError, match="membership identity"):
        WebStore(path)


def test_schema_twelve_missing_or_corrupt_policy_fails_startup(tmp_path):
    """Existing v12 identity data cannot silently reset audit limits."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE audit_policy")
    with pytest.raises(WebStoreError):
        WebStore(path)


def test_corrupt_existing_store_never_recreates_admin(tmp_path):
    """Existing corrupt identity data fails closed."""
    path = tmp_path / "web.db"
    path.write_bytes(b"not sqlite")
    with pytest.raises(WebStoreError):
        WebStore(path)
    assert path.read_bytes() == b"not sqlite"


def test_deleted_identity_store_never_recreates_default_admin(tmp_path):
    """A missing database after bootstrap requires explicit recovery."""
    path = tmp_path / "web.db"
    WebStore(path)
    path.unlink()
    with pytest.raises(WebStoreError, match="missing after initialization"):
        WebStore(path)


def test_stopped_service_home_copy_restores_identity_profile_and_run(tmp_path):
    """A quiescent manual backup preserves all default-home evidence."""
    original = tmp_path / "original"
    profiles = ProfileStore(original)
    profiles.create("alpha")
    state = StateStore(profiles.default_store_root("alpha"))
    state.save(RunState(run_id="run-1", ticket_iid=7, lifecycle="done",
        execution=execution_record()))
    web = WebStore(original / "web.db")
    admin = web.authenticate("admin", "admin")
    web.change_password(admin["id"], "admin", "replacement-long-password")
    web.add_price("alpha", "codex", "local-1", "2026-01-01", "2", "4", admin["id"])

    restored = tmp_path / "restored"
    shutil.copytree(original, restored)
    recovered = WebStore(restored / "web.db")
    assert recovered.authenticate("admin", "replacement-long-password")
    assert recovered.authenticate("admin", "admin") is None
    assert recovered.list_prices("alpha")[0]["input_usd_per_million"] == "2"
    assert ProfileStore(restored).load("alpha").name == "alpha"
    assert StateStore(ProfileStore(restored).default_store_root("alpha")).load(
        "run-1"
    ).lifecycle == "done"


def test_login_failure_window_is_bounded(tmp_path):
    """Repeated bad credentials lock out one identity and client."""
    store = WebStore(tmp_path / "web.db")
    for _ in range(5):
        assert store.allow_login("admin", "local")
        store.record_login("admin", "local", success=False)
    assert not store.allow_login("admin", "local")
    assert store.allow_login("admin", "another-client")


def test_sign_in_attempts_are_counted_before_the_password_check(tmp_path):
    """Five attempts are admitted per identity and client; success clears the count."""
    store = WebStore(tmp_path / "web.db")
    assert [store.reserve_login("admin", "local") for _ in range(6)] == [True] * 5 + [False]
    assert store.reserve_login("admin", "another-client")
    store.record_login("admin", "local", success=True)
    assert store.reserve_login("admin", "local")


def test_one_client_cannot_try_many_user_names(tmp_path):
    """A wider window counts one client across names; other clients are unaffected."""
    store = WebStore(tmp_path / "web.db")
    admitted = [store.reserve_login(f"guess-{index}", "local") for index in range(31)]
    assert admitted == [True] * 30 + [False]
    assert not store.reserve_login("admin", "local")
    assert store.reserve_login("admin", "another-client")


def test_successful_sign_ins_do_not_use_up_the_client_window(tmp_path):
    """Many people behind one address can sign in without locking each other out."""
    store = WebStore(tmp_path / "web.db")
    for index in range(40):
        assert store.reserve_login(f"user-{index}", "shared-address")
        store.record_login(f"user-{index}", "shared-address", success=True)


def test_sign_in_route_limits_wrong_passwords_and_recovers_after_success(tmp_path):
    """The sixth wrong password from one client is refused with 429."""
    with TestClient(create_app(tmp_path / "home")) as client:
        wrong = {"username": "admin", "password": "not-the-password"}
        assert [client.post("/api/v1/session", json=wrong).status_code
                for _ in range(6)] == [401] * 5 + [429]
        refused = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        assert refused.json()["detail"]["code"] == "login_rate_limited"
    with TestClient(create_app(tmp_path / "other")) as client:
        wrong = {"username": "admin", "password": "not-the-password"}
        assert client.post("/api/v1/session", json=wrong).status_code == 401
        assert client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).status_code == 200
        assert [client.post("/api/v1/session", json=wrong).status_code
                for _ in range(5)] == [401] * 5


def test_ended_login_failure_windows_and_expired_sessions_are_removed(tmp_path):
    """Guessed names and old sessions cannot grow the identity store without bound."""
    store = WebStore(tmp_path / "web.db")
    admin = store.authenticate("admin", "admin")
    expired, _ = store.create_session(admin["id"])
    for name in ("guess-one", "guess-two"):
        store.record_login(name, "local", success=False)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE login_failures SET window_started='2000-01-01T00:00:00+00:00'")
        connection.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00+00:00'")
    connection.close()

    store.record_login("guess-three", "local", success=False)
    current, _ = store.create_session(admin["id"])

    with sqlite3.connect(store.path) as connection:
        failures = connection.execute("SELECT COUNT(*) FROM login_failures").fetchone()[0]
        sessions = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    connection.close()
    assert (failures, sessions) == (1, 1)
    assert store.session_user(expired) is None
    assert store.session_user(current)["username"] == "admin"


@pytest.mark.parametrize("path", ["/api/v1/session", "/api/v1/me/password"])
def test_account_routes_refuse_an_oversized_body_before_reading_it(tmp_path, path):
    """A sign-in or password request above its small bound gets 413, signed in or not."""
    with TestClient(create_app(tmp_path / "home")) as client:
        refused = client.post(path, content=b"x" * (64 * 1024 + 1),
                              headers={"content-type": "application/json"})
        assert refused.status_code == 413
        assert refused.json() == {"detail": {"code": "request_too_large"}}
        assert client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).status_code == 200


def test_a_body_without_a_declared_length_is_bounded_while_it_arrives(tmp_path):
    """Chunked uploads are counted, so omitting Content-Length is no way around the bound."""
    def chunks():
        for _ in range(9):
            yield b"x" * 8192

    with TestClient(create_app(tmp_path / "home")) as client:
        refused = client.post("/api/v1/session", content=chunks(),
                              headers={"content-type": "application/json"})
        assert refused.status_code == 413
        assert refused.json() == {"detail": {"code": "request_too_large"}}


def test_every_response_carries_browser_protections(tmp_path):
    """Pages, API answers, errors and refusals all tell the browser how to treat them."""
    with TestClient(create_app(tmp_path / "home")) as client:
        responses = [
            client.get("/"),
            client.get("/api/v1/health"),
            client.get("/api/v1/projects"),
            client.post("/api/v1/session", json={"username": "admin", "password": "admin"}),
            client.post("/api/v1/session", content=b"x" * (64 * 1024 + 1),
                        headers={"content-type": "application/json"}),
        ]
        assert [response.status_code for response in responses] == [200, 200, 401, 200, 413]
        for response in responses:
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["referrer-policy"] == "same-origin"
        assert all(response.headers["cache-control"] == "no-store" for response in responses[1:])
        # Static pages keep their own caching; only API answers are never stored.
        assert responses[0].headers.get("cache-control") != "no-store"


def test_own_password_change_bounds_both_passwords(tmp_path):
    """A password above the accepted length is refused before it is hashed."""
    with TestClient(create_app(tmp_path / "home")) as client:
        csrf = client.post("/api/v1/session", json={
            "username": "admin", "password": "admin"}).json()["csrf"]
        refused = client.post("/api/v1/me/password", headers={"X-CSRF-Token": csrf},
                              json={"current": "admin", "replacement": "p" * 1025})
        assert refused.status_code == 422
        assert refused.json()["detail"]["code"] == "invalid_request"


def test_sessions_and_disabled_accounts(tmp_path):
    """Sessions can be revoked and disabled users cannot sign in."""
    store = WebStore(tmp_path / "web.db")
    admin = store.authenticate("admin", "admin")
    token, csrf = store.create_session(admin["id"])
    assert csrf and store.session_user(token)["username"] == "admin"
    store.revoke_session(token)
    assert store.session_user(token) is None
    user = store.create_user("dev", "longer-password", "developer")
    assert store.authenticate("dev", "longer-password")
    store.disable_user(user["id"])
    assert store.authenticate("dev", "longer-password") is None
    store.enable_user(user["id"])
    assert store.authenticate("dev", "longer-password") is not None
    with pytest.raises(WebStoreError, match="last administrator"):
        store.disable_user(admin["id"])


def test_admin_password_reset_revokes_sessions(tmp_path):
    """Recovery sets a fresh hash and invalidates old sessions."""
    store = WebStore(tmp_path / "web.db")
    user = store.create_user("dev", "longer-password", "developer")
    token, _csrf = store.create_session(user["id"])
    store.reset_password(user["id"], "new-long-password")
    assert store.session_user(token) is None
    assert store.authenticate("dev", "longer-password") is None
    assert store.authenticate("dev", "new-long-password")
    with pytest.raises(WebStoreError, match="8 characters"):
        store.reset_password(user["id"], "short")
    with pytest.raises(WebStoreError, match="user not found"):
        store.reset_password(999, "new-long-password")


def test_reset_password_requires_own_change_until_it_succeeds(tmp_path):
    """An administrator reset marks the account until its own change."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    user = store.create_user("dev", "longer-password", "developer")
    assert store.authenticate("dev", "longer-password")["password_change_required"] is False
    store.reset_password(user["id"], "recovery-password")
    marked = WebStore(path).authenticate("dev", "recovery-password")
    assert marked["password_change_required"] is True
    token, _csrf = store.create_session(user["id"])
    assert store.session_user(token)["password_change_required"] is True
    with pytest.raises(WebStoreError, match="incorrect"):
        store.change_password(user["id"], "wrong-password", "chosen-password")
    with pytest.raises(WebStoreError, match="8 characters"):
        store.change_password(user["id"], "recovery-password", "short")
    assert store.authenticate("dev", "recovery-password")["password_change_required"] is True
    store.change_password(user["id"], "recovery-password", "chosen-password")
    assert WebStore(path).authenticate("dev", "chosen-password")[
        "password_change_required"] is False


def test_bootstrap_admin_starts_unmarked(tmp_path):
    """The fresh administrator keeps its bootstrap password without a forced change."""
    store = WebStore(tmp_path / "web.db")
    assert store.authenticate("admin", "admin")["password_change_required"] is False


def test_schema_thirteen_missing_password_policy_fails_closed(tmp_path):
    """A current store without the reset marker cannot start."""
    path = tmp_path / "web.db"
    WebStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE users DROP COLUMN password_change_required")
    with pytest.raises(WebStoreError, match="password policy"):
        WebStore(path)


def test_password_change_required_limits_api_to_account_routes(tmp_path):
    """A reset account reaches only its own account routes until it changes."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.reset_password(dev["id"], "recovery-password")
    with TestClient(app) as client:
        assert client.get("/api/v1/projects").json()["detail"]["code"] == (
            "authentication_required")
        login = client.post("/api/v1/session", json={
            "username": "dev", "password": "recovery-password"})
        assert login.status_code == 200
        assert login.json()["user"]["password_change_required"] is True
        csrf = login.json()["csrf"]
        headers = {"X-CSRF-Token": csrf}
        for blocked in (client.get("/api/v1/projects"),
                        client.get("/api/v1/metrics"),
                        client.post("/api/v1/projects/alpha/operations/pause",
                                    headers=headers, json={"idempotency_key": "k1"})):
            assert blocked.status_code == 403
            assert blocked.json()["detail"]["code"] == "password_change_required"
        assert client.get("/api/v1/me").json()["user"]["password_change_required"] is True
        assert client.get("/api/v1/me/preferences").status_code == 200
        assert client.patch("/api/v1/me/preferences", json={
            "theme": "dark"}).json()["detail"]["code"] == "csrf_required"
        assert client.patch("/api/v1/me/preferences", headers=headers,
                            json={"theme": "dark"}).status_code == 200
        assert client.post("/api/v1/me/password", headers=headers, json={
            "current": "wrong-password", "replacement": "chosen-password"}).status_code == 400
        assert client.get("/api/v1/projects").status_code == 403
        assert client.post("/api/v1/me/password", headers=headers, json={
            "current": "recovery-password", "replacement": "chosen-password"}).status_code == 200
        assert client.get("/api/v1/me").status_code == 401
        relogin = client.post("/api/v1/session", json={
            "username": "dev", "password": "chosen-password"})
        assert relogin.json()["user"]["password_change_required"] is False
        assert client.get("/api/v1/projects").status_code == 200
        assert client.delete("/api/v1/session", headers={
            "X-CSRF-Token": relogin.json()["csrf"]}).status_code == 200


def test_password_change_required_session_can_sign_out(tmp_path):
    """Signing out remains available while a new password is required."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    dev = web.create_user("dev", "longer-password", "developer")
    web.reset_password(dev["id"], "recovery-password")
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={
            "username": "dev", "password": "recovery-password"})
        assert client.delete("/api/v1/session", headers={
            "X-CSRF-Token": login.json()["csrf"]}).status_code == 200
        assert client.get("/api/v1/me").status_code == 401


def test_factory_admin_status_and_first_boot_notice(tmp_path, capsys):
    """First boot and own session expose only the current factory state."""
    app = create_app(tmp_path / "home")
    assert "admin/admin" in capsys.readouterr().out
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        assert login.json()["user"]["factory_password"] is True
        assert client.get("/api/v1/me").json()["user"]["factory_password"] is True
        response = client.post(
            "/api/v1/me/password", headers={"X-CSRF-Token": login.json()["csrf"]},
            json={"current": "admin", "replacement": "new-long-password"})
        assert response.status_code == 200
        login = client.post("/api/v1/session", json={
            "username": "admin", "password": "new-long-password"})
        assert login.json()["user"]["factory_password"] is False
    create_app(tmp_path / "home")
    assert "admin/admin" not in capsys.readouterr().out


def test_factory_password_status_is_private_and_corruption_fails_closed(tmp_path):
    """Other accounts and reset credentials do not inherit the reminder."""
    app = create_app(tmp_path / "home")
    web = app.state.web_store
    other = web.create_user("otheradmin", "long-password", "admin")
    with TestClient(app) as client:
        login = client.post("/api/v1/session", json={
            "username": "otheradmin", "password": "long-password"})
        assert login.json()["user"]["factory_password"] is False
        assert "password_hash" not in login.text
        client.delete("/api/v1/session", headers={"X-CSRF-Token": login.json()["csrf"]})
        login = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        admin_id = login.json()["user"]["id"]
        web.reset_password(admin_id, "recovery-long-password", actor_id=other["id"])
        assert client.get("/api/v1/me").status_code == 401
        login = client.post("/api/v1/session", json={
            "username": "admin", "password": "recovery-long-password"})
        assert login.json()["user"]["factory_password"] is False
        assert login.json()["user"]["password_change_required"] is True
        with sqlite3.connect(web.path) as connection:
            connection.execute("UPDATE users SET password_hash='broken' WHERE id=?", (admin_id,))
        assert client.get("/api/v1/me").status_code == 503


def test_factory_notice_requires_actual_creation(tmp_path, capsys, monkeypatch):
    """A stale pre-open existence observation cannot announce an existing account."""
    path = tmp_path / "web.db"
    store = WebStore(path)
    admin = store.authenticate("admin", "admin")
    store.change_password(admin["id"], "admin", "new-long-password")
    capsys.readouterr()
    real_exists = type(path).exists
    marker = path.with_name(path.name + ".initialized")
    monkeypatch.setattr(type(path), "exists", lambda self: False if self in (path, marker)
                        else real_exists(self))
    reopened = WebStore(path)
    assert "admin/admin" not in capsys.readouterr().out
    assert reopened.authenticate("admin", "new-long-password") is not None


def test_unknown_and_disabled_names_spend_one_password_check(tmp_path, monkeypatch):
    """A refusal costs one hash check whether or not the user name exists."""
    store = WebStore(tmp_path / "web.db")
    checks: list[str] = []
    real = store_module._HASHER

    class Counting:
        def hash(self, password):
            return real.hash(password)

        def verify(self, stored, password):
            checks.append(stored)
            return real.verify(stored, password)

    monkeypatch.setattr(store_module, "_HASHER", Counting())
    assert store.authenticate("nobody", "admin") is None
    assert store.authenticate("admin", "wrong") is None
    assert len(checks) == 2 and checks[0] != checks[1]
