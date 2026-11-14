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
@file test_web_configuration_worker.py
@brief Durable independent configuration worker contracts.
@details Offline HTTP and deterministic worker barriers prove project/control boundaries.
"""

from adore.web.app import create_app

# IMPORTS
from fastapi.testclient import TestClient

from tests.test_web_pending_config import _headers, _project


# PUBLIC API / TESTS
def test_existing_save_route_returns_durable_acceptance_before_effect(tmp_path):
    """@brief An existing settings route accepts work without publishing early."""
    profiles, path, _ = _project(tmp_path)
    original = path.read_bytes()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        response = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "12", "revision": revision},
        )
        assert response.status_code == 202, response.text
        operation = response.json()
        assert operation["status"] == "pending"
        assert operation["domain"] == "configuration_project"
        assert operation["project_id"] == profiles.load("alpha").project_id
        assert path.read_bytes() == original
        assert (
            client.get("/api/v1/operations/" + str(operation["id"])).json()["status"] == "pending"
        )


def _settle(worker, operation, *, seconds=8):
    """@brief Bound offline worker progress and return its durable operation."""
    import time

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        worker.tick()
        record = worker.web.operation(operation["id"])
        if record["status"] not in ("pending", "running"):
            return record
        time.sleep(0.005)
    raise AssertionError("configuration worker did not finish within test budget")


def test_worker_confirms_existing_save_and_stale_second_save(tmp_path):
    """@brief Concurrent reviewed saves serialize and the stale revision fails closed."""
    from adore.config import load_config
    from adore.web.configuration import ConfigurationWorker

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        first = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "12", "revision": revision},
        ).json()
        second = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "13", "revision": revision},
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            assert _settle(worker, first)["status"] == "succeeded"
            assert _settle(worker, second)["status"] == "failed"
            result = client.get("/api/v1/operations/" + str(second["id"])).json()
            assert result["outcome"]["status_code"] == 409
            assert result["outcome"]["body"]["detail"]["code"] == "stale_config_revision"
            assert load_config(path).budgets.max_iterations == 12
            confirmed = client.get("/api/v1/operations/" + str(first["id"])).json()
            assert confirmed["outcome"]["body"]["revision"] != revision
        finally:
            worker.close()


def _beta(profiles, path, tmp_path):
    """@brief Add a second independent project with a distinct managed state root."""
    root = tmp_path / "beta-state"
    profiles.create("beta", store_root=str(root))
    beta = profiles.config_path("beta")
    from adore.config import load_config

    original_root = load_config(path).state.store_root
    beta.write_bytes(
        path.read_bytes().replace(
            str(original_root).replace("\\", "/").encode(), root.as_posix().encode()
        )
    )
    return beta


def test_blocked_probe_preserves_fast_project_global_and_admission_control(tmp_path, monkeypatch):
    """@brief Full long lane A cannot block B, global audit or scoped Pause/Resume."""
    import importlib
    from threading import Event

    from adore.config import load_config
    from adore.config_edit import config_edit_lock
    from adore.state import StateStore
    from adore.web.configuration import ConfigurationWorker

    module = importlib.import_module("adore.web.app")
    profiles, path, state = _project(tmp_path)
    beta = _beta(profiles, path, tmp_path)
    original_a = path.read_bytes()
    entered, release = Event(), Event()

    def probe(config, *_args, **_kwargs):
        """@brief Hold the external boundary while proving publication locks are free."""
        with config_edit_lock(path):
            assert state.acquire_lock()
            state.release_lock()
        entered.set()
        assert release.wait(10)
        return {"ready": True, "reason": "ready", "executor": "pi", "model": config.executor.model}

    monkeypatch.setattr(module, "probe_model_connection", probe)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        long = client.post("/api/v1/projects/alpha/model-connection-test", headers=headers).json()
        worker = ConfigurationWorker(app.state.configuration_tasks, long_slots=1, fast_slots=1)
        try:
            worker.tick()
            assert entered.wait(5)
            revision = client.get("/api/v1/projects/beta/config").json()["revision"]
            saved = client.put(
                "/api/v1/projects/beta/config",
                headers=headers,
                json={"key": "budgets.max_iterations", "value": "17", "revision": revision},
            ).json()
            global_operation = client.delete("/api/v1/chatgpt-sign-in", headers=headers).json()
            assert global_operation["domain"] == "configuration_global"
            policy = client.put(
                "/api/v1/audit-policy",
                headers=headers,
                json={"retention_days": 30, "max_bytes": None},
            )
            assert policy.status_code == 200
            assert _settle(worker, saved)["status"] == "succeeded"
            assert _settle(worker, global_operation)["status"] == "succeeded"
            assert load_config(beta).budgets.max_iterations == 17
            assert path.read_bytes() == original_a
            assert not state.is_paused()
            for action in ("pause", "resume"):
                control = client.post(
                    "/api/v1/projects/beta/operations/" + action,
                    headers=headers,
                    json={"idempotency_key": action + "-test-key"},
                ).json()
                assert _settle(worker, control)["status"] == "succeeded"
                assert StateStore(tmp_path / "beta-state").is_paused() == (action == "pause")
                assert not state.is_paused()
            assert worker.web.operation(long["id"])["status"] == "running"
        finally:
            release.set()
            _settle(worker, long)
            worker.close()


def test_unsafe_apply_retains_project_candidate_and_other_project_bytes(tmp_path):
    """@brief Active A gets an explicit conflict and retains the reviewed container edit."""
    from adore.state import RunState
    from adore.web.configuration import ConfigurationWorker

    profiles, path, state = _project(tmp_path)
    beta = _beta(profiles, path, tmp_path)
    originals = path.read_bytes(), beta.read_bytes()
    state.save(RunState(run_id="active-a", ticket_iid=1, lifecycle="working"))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        staged = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": "container.image", "value": "changed:1", "revision": revision},
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            assert _settle(worker, staged)["status"] == "succeeded"
            pending = worker.tasks.outcome(worker.web.operation(staged["id"]))["body"]
            apply = client.post(
                "/api/v1/projects/alpha/config/apply",
                headers=headers,
                json={
                    "base_revision": revision,
                    "candidate_revision": pending["candidate_revision"],
                },
            ).json()
            result = _settle(worker, apply)
            assert result["status"] == "failed" and result["reason"] == "project_has_active_work"
            assert worker.tasks.outcome(result)["status_code"] == 409
            assert (path.parent / "pending_config.json").is_file()
            assert (path.read_bytes(), beta.read_bytes()) == originals
        finally:
            worker.close()


def test_queued_actor_revocation_fails_without_credential_disclosure(tmp_path):
    """@brief Queued secrets stay protected and revoked actors cannot publish them."""
    from adore.web.configuration import ConfigurationWorker

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    web = app.state.web_store
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        secret = "sentinel-private-provider-token"
        accepted = client.put(
            "/api/v1/projects/alpha/executor-credentials",
            headers=headers,
            json={"variable": "OPENAI_API_KEY", "token": secret, "revision": revision},
        )
        assert accepted.status_code == 202
        operation = accepted.json()
        record = web.operation(operation["id"])
        assert secret not in str(record)
        with web._connect() as connection:
            assert secret not in str(
                [tuple(row) for row in connection.execute("SELECT * FROM audit")]
            )
        protected = app.state.configuration_tasks.directory / (record["run_id"] + ".request.json")
        assert secret in protected.read_text()
        other = web.create_user("other_admin", "longer-password", "admin")
        web.disable_user(record["actor_id"], actor_id=other["id"])
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            denied = _settle(worker, operation)
            assert denied["status"] == "failed" and denied["reason"] == "permission_revoked"
            assert not (path.parent / ".env").exists()
            assert not protected.exists()
        finally:
            worker.close()


def test_corrupt_protected_request_is_a_closed_terminal_failure(tmp_path):
    """@brief Edited persisted task data cannot retarget a queued settings write."""
    import json

    from adore.web.configuration import ConfigurationWorker

    profiles, path, _ = _project(tmp_path)
    original = path.read_bytes()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        operation = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "12", "revision": revision},
        ).json()
        record = app.state.web_store.operation(operation["id"])
        target = app.state.configuration_tasks.directory / (record["run_id"] + ".request.json")
        envelope = json.loads(target.read_text())
        envelope["arguments"]["body"]["value"] = "999"
        target.write_text(json.dumps(envelope))
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            result = _settle(worker, operation)
            assert (
                result["status"] == "failed" and result["reason"] == "configuration_request_corrupt"
            )
            assert path.read_bytes() == original
        finally:
            worker.close()


def test_missing_project_scope_is_refused_before_queueing(tmp_path):
    """@brief A project handler cannot use active-profile fallback when scope is absent."""
    from fastapi import HTTPException
    import pytest

    profiles, _path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    tasks = app.state.configuration_tasks
    admin = app.state.web_store.user_by_id(1)

    @tasks.route()
    def missing_scope(user):
        return {}

    with pytest.raises(HTTPException) as error:
        missing_scope(user=admin)
    assert error.value.status_code == 422
    assert not tasks.web.pending_configuration()


def test_actual_configuration_process_confirms_save_without_http_execution(tmp_path):
    """@brief The installed fixed-role configuration process consumes the durable HTTP queue."""
    import sys
    import time

    from adore.config import load_config
    from adore.web.processes import ProcessTree, stop_trees
    from adore.web.supervisor import _environment

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        accepted = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "21", "revision": revision},
        ).json()
        child = ProcessTree(
            [
                sys.executable,
                "-m",
                "adore.web.supervisor",
                "--role",
                "configuration",
                "--home",
                str(profiles.home),
            ],
            _environment(profiles),
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                operation = app.state.web_store.operation(accepted["id"])
                if operation["status"] not in ("pending", "running"):
                    break
                assert child.poll() is None, child.tail()
                time.sleep(0.02)
            assert operation["status"] == "succeeded", (operation, child.tail())
            result = client.get("/api/v1/operations/" + str(accepted["id"])).json()
            assert result["outcome"]["status_code"] == 200
            assert load_config(path).budgets.max_iterations == 21
        finally:
            stop_trees([child])


def test_authority_revoked_during_model_probe_prevents_evidence_publication(tmp_path, monkeypatch):
    """@brief Claim-time authorization cannot authorize later publication after revocation."""
    import importlib
    from threading import Event

    from adore.web.configuration import ConfigurationWorker

    module = importlib.import_module("adore.web.app")
    profiles, path, _ = _project(tmp_path)
    entered, release = Event(), Event()

    def probe(config, *_args, **_kwargs):
        entered.set()
        assert release.wait(10)
        return {"ready": True, "reason": "ready", "executor": "pi", "model": config.executor.model}

    monkeypatch.setattr(module, "probe_model_connection", probe)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        accepted = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers=headers
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            worker.tick()
            assert entered.wait(5)
            other = worker.web.create_user("another_admin", "longer-password", "admin")
            worker.web.disable_user(1, actor_id=other["id"])
            release.set()
            refused = _settle(worker, accepted)
            assert refused["status"] == "failed" and refused["reason"] == "permission_revoked"
            assert not (path.parent / "model-connection.json").exists()
        finally:
            release.set()
            worker.close()


def test_scope_resolver_refuses_hex_name_id_ambiguity(tmp_path):
    """@brief A valid hexadecimal profile name cannot redirect edits to another profile ID."""
    profiles, path, _ = _project(tmp_path)
    identity = profiles.load("alpha").project_id
    profiles.create(identity, store_root=str(tmp_path / "other-state"))
    profiles.config_path(identity).write_bytes(path.read_bytes())
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        response = client.put(
            "/api/v1/projects/" + identity + "/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "13", "revision": "0" * 64},
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "project_identity_ambiguous"
        assert not app.state.web_store.pending_configuration()


def test_revocation_immediately_before_settings_publication_keeps_active_bytes(
    tmp_path, monkeypatch
):
    """@brief Revocation after edit-lock entry and validation still refuses the actual write."""
    from adore.web.configuration import ConfigurationWorker

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    web = app.state.web_store
    other = web.create_user("last_admin", "longer-password", "admin")
    original_begin = web.begin_change
    original = path.read_bytes()

    def revoke(*args, **kwargs):
        result = original_begin(*args, **kwargs)
        web.disable_user(1, actor_id=other["id"])
        return result

    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        accepted = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "18", "revision": revision},
        ).json()
        monkeypatch.setattr(web, "begin_change", revoke)
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            refused = _settle(worker, accepted)
            assert refused["status"] == "failed" and refused["reason"] == "permission_revoked"
            assert path.read_bytes() == original
        finally:
            worker.close()


def test_confirmation_failure_after_settings_effect_is_uncertain(tmp_path, monkeypatch):
    """@brief A post-write audit failure cannot be presented as a rejected request."""
    from adore.config import load_config
    from adore.web.configuration import ConfigurationWorker
    from adore.web.store import WebStoreError

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)

    def broken_confirmation(*args, **kwargs):
        raise WebStoreError("private storage details must not escape")

    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        accepted = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "19", "revision": revision},
        ).json()
        monkeypatch.setattr(app.state.web_store, "confirm_change", broken_confirmation)
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            result = _settle(worker, accepted)
            assert result["status"] == "uncertain"
            assert result["reason"] == "configuration_confirmation_failed"
            assert load_config(path).budgets.max_iterations == 19
            public = client.get("/api/v1/operations/" + str(accepted["id"])).json()
            assert public["outcome"] is None and "private storage" not in str(public)
        finally:
            worker.close()


def test_corrupt_or_contradictory_private_results_return_typed_service_error(tmp_path):
    """@brief Stored outcomes reject nonregular records and false success."""
    import json

    from adore.web.configuration import ConfigurationWorker

    profiles, _path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        revision = client.get("/api/v1/projects/alpha/config").json()["revision"]
        accepted = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "19", "revision": revision},
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            operation = _settle(worker, accepted)
            target = worker.tasks.directory / (operation["run_id"] + ".result.json")
            valid = json.loads(target.read_text())
            for invalid in (
                {**valid, "status_code": 409},
                {**valid, "schema": True},
                {**valid, "operation_id": accepted["id"] + 1},
            ):
                target.write_text(json.dumps(invalid))
                response = client.get("/api/v1/operations/" + str(accepted["id"]))
                assert (
                    response.status_code == 503
                    and response.json()["detail"]["code"] == "web_store_corrupt"
                )
            target.unlink()
            target.mkdir()
            assert client.get("/api/v1/operations/" + str(accepted["id"])).status_code == 503
        finally:
            worker.close()


def test_slow_native_settings_plan_uses_long_lane_and_releases_edit_lock(tmp_path, monkeypatch):
    """@brief Long stage preparation cannot consume the reserved fast settings capacity."""
    import importlib
    from threading import Event

    from adore.config_edit import config_edit_lock
    from adore.web.configuration import ConfigurationWorker

    module = importlib.import_module("adore.web.app")
    profiles, path, _ = _project(tmp_path)
    beta = _beta(profiles, path, tmp_path)
    import re

    native = path.read_text().replace('backend = "container"', 'backend = "local"')
    native = re.sub(
        r"required_tool_checks = \[.*?\]", "required_tool_checks = []", native, flags=re.S
    )
    path.write_text(native)
    entered, release = Event(), Event()

    def plan(config, **kwargs):
        with config_edit_lock(path):
            pass
        entered.set()
        assert release.wait(10)
        return {"backend": "local"}

    monkeypatch.setattr(module, "preview_plan", plan)
    # Existing plan contracts cover the format; this seam controls only its wait.
    monkeypatch.setattr(
        module,
        "_public_pending_config",
        lambda value, **kwargs: {key: val for key, val in value.items() if key != "candidate_text"},
    )
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        from hashlib import sha256

        stage = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={
                "key": "budgets.max_iterations",
                "value": "14",
                "revision": sha256(path.read_bytes()).hexdigest(),
            },
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks, long_slots=1, fast_slots=1)
        try:
            worker.tick()
            assert entered.wait(5)
            beta_revision = sha256(beta.read_bytes()).hexdigest()
            saved = client.put(
                "/api/v1/projects/beta/config",
                headers=headers,
                json={"key": "budgets.max_iterations", "value": "15", "revision": beta_revision},
            ).json()
            assert _settle(worker, saved)["status"] == "succeeded"
            assert worker.web.operation(stage["id"])["status"] == "running"
        finally:
            release.set()
            _settle(worker, stage)
            worker.close()


def test_managed_image_build_is_durable_lock_free_and_independent(tmp_path, monkeypatch):
    """@brief Actual onboarding preparation holds no edit lock and preserves B/global progress."""
    from hashlib import sha256
    import importlib

    from adore.branding import EXECUTOR_BASE_IMAGE
    from adore.config_edit import config_edit_lock
    from adore.util import CommandResult
    from adore.web.configuration import ConfigurationWorker
    from adore.wizard import run_wizard

    from tests.test_web_enrollment import _body
    from tests.test_web_environment import Engine

    module = importlib.import_module("adore.web.app")
    profiles, path, _ = _project(tmp_path)
    beta = _beta(profiles, path, tmp_path)
    engine = Engine()
    engine.release.clear()
    monkeypatch.setattr("adore.web.environment.os.getuid", lambda: 1001, raising=False)
    monkeypatch.setattr("adore.web.environment.os.getgid", lambda: 1002, raising=False)
    monkeypatch.setattr(
        module,
        "run_wizard",
        lambda *args, **kwargs: run_wizard(
            *args, **kwargs, runner=lambda *a, **k: CommandResult(exit_code=127)
        ),
    )

    def runner(argv, **kwargs):
        if "build" in argv:
            key = profiles.home / "environment" / sha256(b"docker").hexdigest() / "images"
            with config_edit_lock(key):
                pass
        return engine(argv, **kwargs)

    app = create_app(profiles.home, environment_runner=runner)
    with TestClient(app) as client:
        headers = _headers(client)
        body = _body(tmp_path, name="new_project", image=EXECUTOR_BASE_IMAGE)
        preview_task = client.post(
            "/api/v1/projects/setup-preview", headers=headers, json=body
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks, long_slots=1, fast_slots=1)
        operation = None
        try:
            reviewed = worker.tasks.outcome(_settle(worker, preview_task))["body"]
            operation = client.post(
                "/api/v1/projects/setup-environment",
                headers=headers,
                json={**body, "revision": reviewed["revision"]},
            ).json()
            assert not engine.calls  # HTTP acceptance performed no environment work.
            worker.tick()
            assert engine.building.wait(5)
            save = client.put(
                "/api/v1/projects/beta/config",
                headers=headers,
                json={
                    "key": "budgets.max_iterations",
                    "value": "22",
                    "revision": sha256(beta.read_bytes()).hexdigest(),
                },
            ).json()
            global_task = client.delete("/api/v1/chatgpt-sign-in", headers=headers).json()
            assert _settle(worker, save)["status"] == "succeeded"
            assert _settle(worker, global_task)["status"] == "succeeded"
            assert worker.web.operation(operation["id"])["status"] == "running"
        finally:
            engine.release.set()
            if operation:
                result = _settle(worker, operation)
                assert result["status"] == "succeeded"
                assert worker.tasks.outcome(result)["body"]["status"] == "ready"
            worker.close()


def test_exact_claim_preserves_global_lane_when_earlier_long_request_cannot_start(
    tmp_path, monkeypatch
):
    """@brief An earlier saturated global long request cannot steal a reserved auth slot."""
    import importlib
    import json
    from threading import Event

    from adore.web.configuration import ConfigurationWorker

    profiles, _path, _ = _project(tmp_path)
    entered, release = Event(), Event()
    module = importlib.import_module("adore.web.app")

    def probe(config, *args, **kwargs):
        entered.set()
        assert release.wait(10)
        return {"ready": True, "reason": "ready", "executor": "pi", "model": config.executor.model}

    monkeypatch.setattr(module, "probe_model_connection", probe)
    app = create_app(profiles.home)

    @app.state.configuration_tasks.route(scope="global", lane="long", resource="earlier-long")
    def earlier_long(user):
        return {"finished": True}

    with TestClient(app) as client:
        headers = _headers(client)
        blocked = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers=headers
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks, long_slots=1)
        try:
            worker.tick()
            assert entered.wait(5)
            earlier = json.loads(earlier_long(user=worker.web.user_by_id(1)).body)
            later = client.delete("/api/v1/chatgpt-sign-in", headers=headers).json()
            assert _settle(worker, later)["status"] == "succeeded"
            assert worker.web.operation(earlier["id"])["status"] == "pending"
        finally:
            release.set()
            _settle(worker, blocked)
            _settle(worker, earlier)
            worker.close()


def test_malformed_execution_section_is_a_typed_submission_refusal(tmp_path):
    """@brief Valid TOML with a corrupt section type never raises an HTTP handler exception."""
    from hashlib import sha256
    import re

    profiles, path, _ = _project(tmp_path)
    raw = re.sub(r"(?ms)^\[execution\]\n.*?(?=^\[container\])", "", path.read_text())
    path.write_text('execution = "local"\n' + raw)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        response = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={
                "key": "budgets.max_iterations",
                "value": "12",
                "revision": sha256(path.read_bytes()).hexdigest(),
            },
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "config_corrupt"
        assert not app.state.web_store.pending_configuration()


def test_post_effect_deadline_crossing_is_uncertain(tmp_path):
    """@brief A completed effect cannot become rejected merely by crossing its task deadline."""
    import json

    from adore.web.configuration import ConfigurationWorker

    profiles, _path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    clock = [100.0]
    marker = tmp_path / "effect.json"

    @app.state.configuration_tasks.route(scope="global", lane="global")
    def crosses_deadline(user):
        marker.write_text('{"saved":true}')
        clock[0] += 3601
        return {"saved": True}

    accepted = json.loads(crosses_deadline(user=app.state.web_store.user_by_id(1)).body)
    worker = ConfigurationWorker(app.state.configuration_tasks, clock=lambda: clock[0])
    try:
        result = _settle(worker, accepted)
        assert result["status"] == "uncertain"
        assert result["reason"] == "configuration_confirmation_failed"
        assert marker.is_file() and worker.tasks.outcome(result) is None
    finally:
        worker.close()


def test_settings_read_uses_only_current_cached_plan_without_probing(tmp_path, monkeypatch):
    """@brief Read-side settings never launch a host/Git plan probe; corrupt caches fail closed."""
    from hashlib import sha256
    import importlib
    import json

    from adore.config import load_config
    from adore.preparation import preview_plan

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    profile = profiles.load("alpha")
    revision = sha256(path.read_bytes()).hexdigest()
    plan = preview_plan(
        load_config(path), runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("probe"))
    )
    app.state.configuration_tasks.save_execution_plan(profile, revision, plan)
    module = importlib.import_module("adore.web.app")
    monkeypatch.setattr(
        module, "preview_plan", lambda *a, **k: (_ for _ in ()).throw(AssertionError("HTTP probe"))
    )
    with TestClient(app) as client:
        _headers(client)
        assert client.get("/api/v1/projects/alpha/config").json()["execution_plan"] is not None
        path.write_text(path.read_text() + "\n# new revision\n")
        assert client.get("/api/v1/projects/alpha/config").json()["execution_plan"] is None
        cached = path.parent / "execution-plan.json"
        value = json.loads(cached.read_text())
        value["schema"] = 99
        cached.write_text(json.dumps(value))
        response = client.get("/api/v1/projects/alpha/config")
        assert response.status_code == 503
        assert "execution-plan.json" in response.json()["detail"]["message"]
        from fastapi import HTTPException
        import pytest

        with pytest.raises(HTTPException):
            app.state.configuration_tasks.save_execution_plan(
                profile, sha256(path.read_bytes()).hexdigest(), plan
            )
        assert json.loads(cached.read_text())["schema"] == 99


def test_revoked_model_actor_still_cleans_its_owned_disposable_probe(tmp_path, monkeypatch):
    """@brief Revocation refuses evidence while retaining exact worker-owned model cleanup."""
    import importlib

    from adore.web.configuration import ConfigurationWorker
    from adore.web.model_connection import probe_model_connection

    from tests.test_model_connection import SECRET, Runtime

    profiles, path, _ = _project(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (path.parent / ".env").write_text("OPENAI_API_KEY=" + SECRET + "\n")
    runtime = Runtime(tmp_path, "run_connection_test_endpoint")
    module = importlib.import_module("adore.web.app")
    app = create_app(profiles.home, probe_runner=runtime.runner)
    web = app.state.web_store
    other = web.create_user("cleanup_admin", "longer-password", "admin")

    def popen(*args, **kwargs):
        web.disable_user(1, actor_id=other["id"])
        return runtime.popen(*args, **kwargs)

    monkeypatch.setattr(
        module,
        "probe_model_connection",
        lambda config, runner, env_file, **kwargs: probe_model_connection(
            config, runner, env_file, popen=popen, **kwargs
        ),
    )
    with TestClient(app) as client:
        headers = _headers(client)
        accepted = client.post(
            "/api/v1/projects/alpha/model-connection-test", headers=headers
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            result = _settle(worker, accepted)
            assert result["status"] == "failed" and result["reason"] == "permission_revoked"
            assert any("run" in argv for argv, _ in runtime.calls)
            assert any("rm" in argv for argv, _ in runtime.calls)
            assert not (path.parent / "model-connection.json").exists()
        finally:
            worker.close()


def test_project_and_global_configuration_history_is_redacted_and_strict(tmp_path):
    """@brief Project/global configuration history is redacted and refuses corrupt references."""
    from hashlib import sha256

    from adore.web.configuration import ConfigurationWorker

    profiles, path, _ = _project(tmp_path)
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        project = client.put(
            "/api/v1/projects/alpha/config",
            headers=headers,
            json={
                "key": "budgets.max_iterations",
                "value": "23",
                "revision": sha256(path.read_bytes()).hexdigest(),
            },
        ).json()
        global_task = client.delete("/api/v1/chatgpt-sign-in", headers=headers).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            assert _settle(worker, project)["status"] == "succeeded"
            assert _settle(worker, global_task)["status"] == "succeeded"
            history = client.get("/api/v1/audit-page?limit=all")
            assert history.status_code == 200, history.text
            assert "request.json" not in history.text and "credential_revision" not in history.text
            with worker.web._connect() as connection:
                connection.execute(
                    "UPDATE operations SET run_id='bad-reference' WHERE id=?", (global_task["id"],)
                )
            assert client.get("/api/v1/audit-page?limit=all").status_code == 503
        finally:
            worker.close()


def test_fast_admission_control_refuses_corrupt_persisted_state_root(tmp_path):
    """@brief Invalid metadata refuses control without a partial or global write."""
    import json

    from adore.web.configuration import ConfigurationWorker

    profiles, path, state = _project(tmp_path)
    _beta(profiles, path, tmp_path)
    metadata = path.parent / "profile.json"
    value = json.loads(metadata.read_text())
    value["store_root"] = 123
    metadata.write_text(json.dumps(value))
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        accepted = client.post(
            "/api/v1/projects/alpha/operations/pause",
            headers=headers,
            json={"idempotency_key": "corrupt-state-root"},
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            result = _settle(worker, accepted)
            assert result["status"] == "failed" and result["reason"] == "control_refused"
            assert not state.is_paused()
            from adore.state import StateStore

            assert not StateStore(tmp_path / "beta-state").is_paused()
        finally:
            worker.close()


def test_native_apply_refuses_foreign_plan_cache_before_config_publication(tmp_path, monkeypatch):
    """@brief Refuse a corrupt plan cache before changing active settings."""
    from hashlib import sha256
    import re

    from adore.web.configuration import ConfigurationWorker

    from tests.test_local_execution import local_fixture

    local_fixture(tmp_path, monkeypatch)
    profiles, path, state = _project(tmp_path)
    text = path.read_text().replace('backend = "container"', 'backend = "local"')
    text = re.sub(r"required_tool_checks = \[.*?\]", "required_tool_checks = []", text, flags=re.S)
    path.write_text(text)
    state.pause()
    original = path.read_bytes()
    revision = sha256(original).hexdigest()
    app = create_app(profiles.home)
    with TestClient(app) as client:
        headers = _headers(client)
        stage = client.post(
            "/api/v1/projects/alpha/config/pending",
            headers=headers,
            json={"key": "budgets.max_iterations", "value": "25", "revision": revision},
        ).json()
        worker = ConfigurationWorker(app.state.configuration_tasks)
        try:
            staged = _settle(worker, stage)
            assert staged["status"] == "succeeded", worker.tasks.outcome(staged)
            candidate = worker.tasks.outcome(staged)["body"]["candidate_revision"]
            cached = path.parent / "execution-plan.json"
            cached.write_text('{"schema":99}')
            apply = client.post(
                "/api/v1/projects/alpha/config/apply",
                headers=headers,
                json={"base_revision": revision, "candidate_revision": candidate},
            ).json()
            refused = _settle(worker, apply)
            assert refused["status"] == "failed"
            assert worker.tasks.outcome(refused)["status_code"] == 503
            assert path.read_bytes() == original
            assert (path.parent / "pending_config.json").exists()
            assert cached.read_text() == '{"schema":99}'
            # Explicit deletion permits a fresh cache and the same reviewed apply.
            cached.unlink()
            retry = client.post(
                "/api/v1/projects/alpha/config/apply",
                headers=headers,
                json={"base_revision": revision, "candidate_revision": candidate},
            ).json()
            confirmed = _settle(worker, retry)
            assert confirmed["status"] == "succeeded", worker.tasks.outcome(confirmed)
            assert path.read_bytes() != original
            assert not (path.parent / "pending_config.json").exists()
            assert client.get("/api/v1/projects/alpha/config").json()["execution_plan"] is not None
        finally:
            worker.close()
