#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_web_transfer.py
@brief   Public portable enrollment source and atomic target contracts.
@details Offline strict file/copy, ownership, authorization and rollback proofs.
"""

# IMPORTS
from hashlib import sha256
import json
from pathlib import Path
import re

from adore.config import load_config
from adore.portable_settings import export_settings, parse_settings
from adore.state import RunState, StateStore
from adore.util import CommandResult
from adore.web.app import create_app
from adore.web.store import WebStoreError
from fastapi.testclient import TestClient
import pytest

from tests.test_web_enrollment import _body, _login, _no_probe, offline_wizard  # noqa: F401


# LOCAL HELPERS
def _source(client, app, tmp_path, method="file"):
    """@brief Enroll a source and select exact file or immutable project input."""
    headers = _login(client)
    source = client.post("/api/v1/projects", json=_body(tmp_path), headers=headers)
    assert source.status_code == 200, source.text
    path = app.state.profiles.config_path("alpha")
    document = path.read_text(encoding="utf-8")
    rules = {
        "polling": {
            "mode": "once",
            "poll_interval_seconds": 23,
            "poll_jitter_seconds": 7,
            "poll_backoff": False,
            "max_concurrent_runs": 3,
        },
        "readiness": {
            "require_acceptance_criteria": False,
            "require_priority_label": False,
        },
        "recovery": {
            "max_stage_failures": 5,
            "max_transient_retries": 6,
            "retry_backoff_seconds": [0, 7, 19],
        },
        "budgets": {
            "max_iterations": 9,
            "max_wall_clock_seconds": 900,
            "max_files_touched": 33,
            "max_cost_usd": 0.25,
            "per_gate_timeout_seconds": 80,
        },
    }
    for section, values in rules.items():
        document = re.sub(r"(?ms)^\[" + section + r"\]\s*\n.*?(?=^\[|\Z)", "", document)
        document += (
            "\n["
            + section
            + "]\n"
            + "\n".join(key + " = " + json.dumps(value) for key, value in values.items())
            + "\n"
        )
    path.write_text(document, encoding="utf-8")
    raw = path.read_bytes()
    source_input = (
        {"method": "file", "file_text": export_settings(raw).decode()}
        if method == "file"
        else {"method": "project", "source_id": source.json()["id"]}
    )
    review = client.post("/api/v1/projects/transfer-source", json=source_input, headers=headers)
    assert review.status_code == 200, review.text
    target = _body(
        tmp_path / "target",
        name="target",
        display_name="Target service",
        repo="owner/target",
        env_keys=["TARGET_API_KEY"],
    )
    body = {
        **source_input,
        "source_revision": review.json()["source_revision"],
        "target": target,
        "references_confirmed": True,
    }
    return headers, body, review.json(), raw


def _review(client, body, headers):
    """@brief Obtain a canonical target review and assert no publication."""
    response = client.post("/api/v1/projects/transfer-preview", json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["structural_valid"], response.text
    return {**body, "revision": response.json()["revision"]}, response.json()


# PUBLIC API / TESTS
@pytest.mark.parametrize("method", ["file", "project"])
def test_transfer_roundtrip_independent_stopped_and_replay(tmp_path, method):
    """@brief Both methods transfer only all rules into a fresh stopped profile."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, source, raw = _source(client, app, tmp_path, method)
        source_path = app.state.profiles.config_path("alpha")
        (source_path.parent / ".env").write_text("fixture-secret-file")
        (source_path.parent / "pending-config.json").write_text("fixture-pending-record")
        source_state = StateStore(load_config(source_path).state.store_root)
        source_state.save(RunState(run_id="source-history", ticket_iid=1, lifecycle="done"))
        dev = app.state.web_store.create_user("assigned", "test-password", "developer")
        app.state.web_store.set_membership(dev["id"], "alpha", True)
        before = {
            p.relative_to(source_path.parent): p.read_bytes()
            for p in source_path.parent.rglob("*")
            if p.is_file()
        }
        reviewed, preview = _review(client, body, headers)
        assert len(preview["mapping"]) == 15
        assert not app.state.profiles.exists("target")
        created = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert created.status_code == 200, created.text
        result = created.json()
        assert result["paused"] and result["pickup_state"] == "stopped"
        assert result["id"] != app.state.profiles.load("alpha").project_id
        target_path = app.state.profiles.config_path("target")
        config = load_config(target_path)
        assert parse_settings(export_settings(target_path.read_bytes())) == source["settings"]
        assert config.executor.env_keys == ["TARGET_API_KEY"]
        assert config.platform.repo == "owner/target"
        assert Path(config.state.store_root).is_relative_to(target_path.parent)
        assert Path(config.metrics.db_path).is_relative_to(Path(config.state.store_root))
        assert config.worktree.root != load_config(source_path).worktree.root
        assert config.state.store_root != load_config(source_path).state.store_root
        assert sha256(target_path.read_bytes()).hexdigest() == preview["config_revision"]
        assert list(StateStore(config.state.store_root).list_runs()) == []
        assert not (target_path.parent / "readiness.json").exists()
        assert not (target_path.parent / ".env").exists()
        assert not (target_path.parent / "pending-config.json").exists()
        assert app.state.web_store.memberships(1) == set()
        assert app.state.web_store.memberships(dev["id"]) == {"alpha"}
        assert before == {
            p.relative_to(source_path.parent): p.read_bytes()
            for p in source_path.parent.rglob("*")
            if p.is_file()
        }
        assert source_path.read_bytes() == raw
        target_bytes = target_path.read_bytes()
        replay = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert replay.status_code == 409
        assert target_path.read_bytes() == target_bytes


@pytest.mark.parametrize("mutation", ["comment", "missing", "identity", "file", "target"])
def test_transfer_exact_source_and_target_binding(tmp_path, mutation):
    """@brief Source bytes/identity and target edits invalidate confirmed review."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _source_review, raw = _source(
            client, app, tmp_path, "file" if mutation == "file" else "project"
        )
        reviewed, _ = _review(client, body, headers)
        path = app.state.profiles.config_path("alpha")
        if mutation == "comment":
            path.write_bytes(raw + b"\n# effective portable rules unchanged\n")
        elif mutation == "missing":
            (path.parent / "profile.json").unlink()
        elif mutation == "identity":
            metadata = json.loads((path.parent / "profile.json").read_text())
            metadata["project_id"] = "a" * 32
            (path.parent / "profile.json").write_text(json.dumps(metadata))
        elif mutation == "file":
            reviewed["file_text"] += " "
        else:
            reviewed["target"]["display_name"] = "Changed target"
        result = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert result.status_code in (404, 409), result.text
        assert result.json()["detail"]["code"] in ("portable_settings_changed", "project_not_found")
        assert not app.state.profiles.profile_dir("target").exists()


@pytest.mark.parametrize("bad", ["unknown", "version", "duplicate", "secret", "broken", "large"])
def test_transfer_invalid_package_no_partial(tmp_path, bad):
    """@brief Untrusted JSON uses unchanged strict parser with safe typed errors."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path)
        raw = body["file_text"]
        value = json.loads(raw)
        if bad == "unknown":
            value["settings"]["polling"]["extra"] = 1
        elif bad == "version":
            value["source"]["version"] = "999.0.0"
        elif bad == "secret":
            value["settings"]["executor"] = {"api_key": "fixture-sensitive-value"}
        body["file_text"] = (
            raw.replace('"kind":', '"kind":"duplicate","kind":')
            if bad == "duplicate"
            else "broken"
            if bad == "broken"
            else "x" * 65537
            if bad == "large"
            else json.dumps(value)
        )
        result = client.post(
            "/api/v1/projects/transfer-source",
            json={"method": "file", "file_text": body["file_text"]},
            headers=headers,
        )
        assert result.status_code in (400, 422), result.text
        assert "fixture-sensitive-value" not in result.text
        assert not app.state.profiles.profile_dir("target").exists()


@pytest.mark.parametrize(
    "boundary", ["unconfirmed", "reference", "clone", "repository", "worktrees", "alias", "corrupt"]
)
def test_transfer_target_boundaries(tmp_path, boundary):
    """@brief Unresolved references or ambiguous/colliding ownership block creation."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path, "project")
        if boundary == "unconfirmed":
            body["references_confirmed"] = False
        elif boundary == "reference":
            # Empty credential names are valid (no forwarded variables); a malformed one is not.
            body["target"]["env_keys"] = ["not-an-env-name"]
        elif boundary == "clone":
            body["target"]["repo_path"] = _body(tmp_path)["repo_path"]
        elif boundary == "repository":
            body["target"]["repo"] = "owner/alpha"
        elif boundary == "worktrees":
            path = app.state.profiles.home / "worktrees" / "target"
            path.mkdir(parents=True)
            (path / "unowned").write_text("preserve")
        elif boundary == "alias":
            path = app.state.profiles.config_path("alpha")
            path.write_bytes(
                path.read_bytes()
                + b'\n[metrics]\ndb_path = "'
                + str(app.state.profiles.default_store_root("target") / "metrics.db")
                .replace("\\", "/")
                .encode()
                + b'"\n'
            )
            source = client.post(
                "/api/v1/projects/transfer-source",
                json={"method": "project", "source_id": body["source_id"]},
                headers=headers,
            )
            body["source_revision"] = source.json()["source_revision"]
        else:
            (app.state.profiles.profile_dir("alpha") / "profile.json").write_text("broken")
        result = client.post("/api/v1/projects/transfer-preview", json=body, headers=headers)
        assert result.status_code in (200, 409, 503), result.text
        if result.status_code == 200:
            assert not result.json()["structural_valid"]
        assert not app.state.profiles.profile_dir("target").exists()


def test_transfer_rollback_and_late_source_change(tmp_path, monkeypatch):
    """@brief Publication faults and mid-publication source edits leave no target."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, raw = _source(client, app, tmp_path, "project")
        reviewed, _ = _review(client, body, headers)
        audit = app.state.web_store.audit

        def broken(*args, **kwargs):
            raise WebStoreError("fixture-sensitive-value")

        monkeypatch.setattr(app.state.web_store, "audit", broken)
        failed = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert failed.status_code == 503, failed.text
        assert "fixture-sensitive-value" not in failed.text
        assert not app.state.profiles.profile_dir("target").exists()
        monkeypatch.setattr(app.state.web_store, "audit", audit)
        create = app.state.profiles.create

        def changed(*args, **kwargs):
            result = create(*args, **kwargs)
            app.state.profiles.config_path("alpha").write_bytes(raw + b"\n# change\n")
            return result

        monkeypatch.setattr(app.state.profiles, "create", changed)
        conflict = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert conflict.status_code == 409, conflict.text
        assert not app.state.profiles.profile_dir("target").exists()


@pytest.mark.parametrize(
    "route", ["transfer-source", "transfer-preview", "transfer-check", "transfer-create"]
)
def test_transfer_admin_csrf_and_session_denial(tmp_path, route):
    """@brief Both source and target methods deny Dev/CSRF/session before source IO."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path, "project")
        reviewed, _ = _review(client, body, headers)
        assert client.post("/api/v1/projects/" + route, json=reviewed).status_code == 403
        app.state.web_store.create_user("dev", "test-password", "developer")
        dev = _login(client, "dev", "test-password")
        assert (
            client.post("/api/v1/projects/" + route, json=reviewed, headers=dev).status_code == 403
        )
        client.cookies.clear()
        assert (
            client.post("/api/v1/projects/" + route, json=reviewed, headers=headers).status_code
            == 401
        )


def test_transfer_rechecks_role_inside_confirmation(tmp_path, monkeypatch):
    """@brief An Admin revoked during preparation cannot publish a copied source."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path, "project")
        reviewed, _ = _review(client, body, headers)
        app.state.web_store.create_user("backup", "test-password", "admin")
        import adore.web.app as web_app

        original = web_app._prepare_project

        def revoke(*args, **kwargs):
            result = original(*args, **kwargs)
            app.state.web_store.disable_user(1)
            return result

        monkeypatch.setattr(web_app, "_prepare_project", revoke)
        response = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert response.status_code == 401, response.text
        assert not app.state.profiles.profile_dir("target").exists()


@pytest.mark.parametrize(
    "name", ["transfer-source", "transfer-preview", "transfer-check", "transfer-create"]
)
def test_transfer_route_ids_reserved(tmp_path, name):
    """@brief New route names cannot alias a profile directory identity."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        result = client.post(
            "/api/v1/projects/id-availability", json={"name": name}, headers=_login(client)
        )
        assert result.status_code == 400


def test_transfer_probe_and_late_target_occupancy(tmp_path):
    """@brief Explicit check is ephemeral; ownership created after review blocks publication."""
    app = create_app(
        tmp_path / "home",
        probe_runner=lambda argv, **kwargs: CommandResult(argv=argv, exit_code=127),
    )
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path, "project")
        reviewed, preview = _review(client, body, headers)
        checked = client.post("/api/v1/projects/transfer-check", json=reviewed, headers=headers)
        assert checked.status_code == 200, checked.text
        assert checked.json()["status"] == "failed"
        assert checked.json()["draft_revision"] == preview["revision"]
        assert not app.state.profiles.profile_dir("target").exists()
        trees = app.state.profiles.home / "worktrees" / "target"
        trees.mkdir(parents=True)
        (trees / "evidence").write_text("preserve")
        response = client.post("/api/v1/projects/transfer-create", json=reviewed, headers=headers)
        assert response.status_code == 409, response.text
        assert (trees / "evidence").read_text() == "preserve"
        assert not app.state.profiles.profile_dir("target").exists()


def test_transfer_creation_keeps_server_check(tmp_path):
    """@brief Copy setup carries only the check issued for its reviewed target."""
    app = create_app(
        tmp_path / "home",
        probe_runner=lambda argv, **kwargs: CommandResult(argv=argv, exit_code=127),
    )
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path, "project")
        reviewed, _preview = _review(client, body, headers)
        checked = client.post(
            "/api/v1/projects/transfer-check", json=reviewed, headers=headers
        ).json()
        bad = client.post(
            "/api/v1/projects/transfer-create",
            json={**reviewed, "evidence_token": "0" * 64},
            headers=headers,
        )
        assert bad.status_code == 409
        created = client.post(
            "/api/v1/projects/transfer-create",
            json={**reviewed, "evidence_token": checked["evidence_token"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert created.json()["verification"]["status"] == checked["status"]
        assert created.json()["verification"]["checks"] == checked["checks"]
        assert created.json()["verification"]["workflow"] == checked["workflow"] == "direct"
        assert "aegis_files" not in checked["checks"]


@pytest.mark.parametrize("bad", ["unknown", "duplicate", "missing", "both", "none"])
def test_transfer_source_selection_and_active_corruption(tmp_path, bad):
    """@brief Source choice and corrupt active TOML are strict public boundaries."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, raw = _source(client, app, tmp_path, "project")
        selection = {"method": "project", "source_id": body["source_id"]}
        if bad == "unknown":
            app.state.profiles.config_path("alpha").write_bytes(
                raw + b"\n[unexpected]\nsecret = 'fixture-sensitive-value'\n"
            )
        elif bad == "duplicate":
            app.state.profiles.config_path("alpha").write_bytes(
                raw + b"\n[polling]\nmode = 'loop'\n"
            )
        elif bad == "missing":
            app.state.profiles.config_path("alpha").unlink()
        elif bad == "both":
            selection["file_text"] = "fixture-sensitive-value"
        else:
            selection.pop("source_id")
        response = client.post("/api/v1/projects/transfer-source", json=selection, headers=headers)
        assert response.status_code in (400, 503), response.text
        assert response.json()["detail"]["code"] == "portable_settings_invalid"
        assert "fixture-sensitive-value" not in response.text
        assert not app.state.profiles.profile_dir("target").exists()


def test_clone_preview_defaults_reflect_the_copied_rules(tmp_path):
    """@brief Settings copied from the source are not listed as defaults."""
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _source_item, _raw = _source(client, app, tmp_path, "file")
        _reviewed, preview = _review(client, body, headers)
    defaults = {item["key"]: item["value"] for item in preview["defaults"]}
    copied = {row["key"]: row["source_value"] for row in preview["mapping"]}
    for key, value in copied.items():
        if value != next(row["server_value"] for row in preview["mapping"] if row["key"] == key):
            assert key not in defaults, key


@pytest.mark.parametrize("bad", ["missing", "unknown", None, True, 1, [], {}])
def test_transfer_probe_rejects_invalid_workflow(tmp_path, monkeypatch, bad):
    """@brief Portable enrollment never issues a token from malformed workflow evidence."""
    import adore.web.app as web_app

    evidence = {"checks": dict.fromkeys(["git", "forge_cli", "forge_auth", "container_runtime",
                                         "executor_cli", "egress_proxy"], True)}
    if bad != "missing":
        evidence["workflow"] = bad
    monkeypatch.setattr(web_app, "_probe_setup", lambda *a, **kw: evidence)
    app = create_app(tmp_path / "home", probe_runner=_no_probe)
    with TestClient(app) as client:
        headers, body, _, _ = _source(client, app, tmp_path, "project")
        reviewed, _preview = _review(client, body, headers)
        result = client.post("/api/v1/projects/transfer-check", json=reviewed, headers=headers)
        assert result.status_code == 503, result.text
        assert result.json()["detail"]["code"] == "readiness_probe_failed"
        assert "evidence_token" not in result.json()
        assert not app.state.profiles.profile_dir("target").exists()


# END OF FILE

