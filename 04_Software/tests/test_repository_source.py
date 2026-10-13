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
@file test_repository_source.py
@brief Enrollment from a repository URL: detection, preview without writes and clone at creation.
@details External commands go through a fake runner that records every call.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path

from adore.util import CommandResult
from adore.web.app import create_app
from adore.web.repository_source import (
    RepositorySourceError,
    default_branch,
    detect_kind,
    origin_matches,
    parse_repository_url,
    suggest_id,
    tea_login_hosts,
)
from fastapi.testclient import TestClient
import pytest

# CONSTANTS

URL = "ssh://git@192.168.1.15:2222/dpasare/Sample.Service.git"
TEA = json.dumps([{"Name": "dcp", "URL": "http://192.168.1.15:3000", "SSHHost": "192.168.1.15"}])


# HELPER FUNCTIONS


@pytest.fixture(autouse=True)
def offline_wizard(monkeypatch):
    """@brief Keep the wizard's own probes offline."""
    import adore.web.app as web_app
    from adore.wizard import run_wizard

    def wrapped(*args, **kwargs):
        return run_wizard(
            *args, **kwargs, runner=lambda argv, **options: CommandResult(argv=argv, exit_code=127)
        )

    monkeypatch.setattr(web_app, "run_wizard", wrapped)


class Forge:
    """@brief Fake git/tea boundary; `aegis` and `branch` shape what a clone contains."""

    def __init__(self, *, reachable: bool = True, aegis: bool = True, branch: bool = True):
        self.calls: list[list[str]] = []
        self.reachable, self.aegis, self.branch = reachable, aegis, branch

    def __call__(self, argv, **_options):
        argv = list(argv)
        self.calls.append(argv)
        if argv[:3] == ["tea", "logins", "list"]:
            return CommandResult(argv=argv, stdout=TEA)
        if argv[:2] == ["git", "ls-remote"]:
            if not self.reachable:
                return CommandResult(
                    argv=argv, exit_code=128, stderr="Permission denied (publickey)"
                )
            return CommandResult(
                argv=argv, stdout="ref: refs/heads/develop\tHEAD\n" + "a" * 40 + "\tHEAD\n"
            )
        if argv[:2] == ["git", "clone"]:
            dest = Path(argv[-1])
            (dest / ".git").mkdir(parents=True)
            (dest / ".git" / "config").write_text(
                f'[remote "origin"]\n\turl = {argv[-2]}\n', encoding="utf-8"
            )
            if self.aegis:
                (dest / ".agentic").mkdir()
                (dest / ".agentic" / "aegis.py").write_text("", encoding="utf-8")
                (dest / ".agentic" / "aegis.toml").write_text("", encoding="utf-8")
            return CommandResult(argv=argv)
        if argv[:2] == ["git", "-C"] and "rev-parse" in argv:
            return CommandResult(argv=argv, exit_code=0 if self.branch else 1)
        return CommandResult(argv=argv, exit_code=127)


def _login(client) -> dict:
    """@brief Sign in as the bootstrap administrator and return the CSRF header."""
    result = client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
    assert result.status_code == 200, result.text
    return {"X-CSRF-Token": result.json()["csrf"]}


def _setup(detected: dict, **changes) -> dict:
    """@brief Guided answers built from a detection result, as the wizard sends them."""
    return {
        "name": detected["name"],
        "display_name": detected["display_name"],
        "kind": detected["kind"],
        "repo": detected["repo"],
        "login": detected["login"],
        "repo_path": detected["repo_path"],
        "target_branch": detected["default_branch"],
        "clone_url": detected["url"],
        "reviewers": "reviewer",
        "auth_mode": "api-key",
        "image": "adore-test:latest",
        "model": "openai/gpt-5.5",
        **changes,
    }


# PUBLIC API / TESTS


@pytest.mark.parametrize(
    ("url", "host", "repo", "name"),
    [
        ("https://github.com/Owner/Repo.git", "github.com", "Owner/Repo", "Repo"),
        ("git@github.com:owner/repo.git", "github.com", "owner/repo", "repo"),
        (URL, "192.168.1.15", "dpasare/Sample.Service", "Sample.Service"),
        ("https://gitlab.com/group/sub/project/", "gitlab.com", "group/sub/project", "project"),
        ("http://192.168.1.15:3000/owner/app", "192.168.1.15", "owner/app", "app"),
    ],
)
def test_repository_urls_are_parsed(url, host, repo, name) -> None:
    """@brief Supported https, http, ssh and scp-like forms yield host, repository and name."""
    parsed = parse_repository_url(url)
    assert (parsed.host, parsed.repo, parsed.name) == (host, repo, name)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repo",
        "/srv/repo",
        "https://user:secret@github.com/o/r",
        "https://github.com/onlyone",
        "ftp://host/o/r",
        "https://github.com/o/r?token=x",
        "--upload-pack=touch",
        "https://github.com/o/r x",
        "https://github.com/o/r#main",
        "ssh://git:pw@host/o/r",
        "ssh://-oProxyCommand=x@host/o/r",
        "git@-host:o/r",
        "-oX@host:o/r",
        "git\x07@host:o/r",
        "ssh://git@host:22/o/r\x00",
        "",
    ],
)
def test_unsupported_or_unsafe_urls_are_rejected(url) -> None:
    """@brief Local paths, other schemes, credentials, queries and option-like values fail."""
    with pytest.raises(RepositorySourceError):
        parse_repository_url(url)


def test_kind_login_branch_id_and_origin_helpers() -> None:
    """@brief Detection helpers cover public hosts, tea logins and naming."""
    hosts = tea_login_hosts(TEA)
    assert hosts == {"192.168.1.15": "dcp"}
    assert tea_login_hosts('[{"name": "x", "url": "https://git.example.invalid"}]') == {
        "git.example.invalid": "x"
    }
    assert tea_login_hosts("not json") == {}
    assert detect_kind("github.com", hosts) == ("github", "")
    assert detect_kind("gitlab.com", hosts) == ("gitlab", "")
    assert detect_kind("192.168.1.15", hosts) == ("gitea", "dcp")
    assert detect_kind("git.unknown.invalid", hosts) == (None, "")
    assert default_branch("ref: refs/heads/release/2.0\tHEAD\nabc\tHEAD\n") == "release/2.0"
    assert default_branch("abc\tHEAD\n") is None
    assert (
        suggest_id("AgenticDeliveryOrchestratorRuntimeEngine", lambda _name: True)
        == "agenticdeliveryorchestratorruntimeengine"
    )
    assert suggest_id("My Repo!", lambda _name: True) == "my-repo"
    assert suggest_id("x" * 80, lambda _name: True) == "x" * 60
    assert suggest_id("app", lambda name: name == "app-3") == "app-3"
    assert origin_matches("git@github.com:Owner/Repo.git", "https://github.com/owner/repo")
    assert not origin_matches("git@github.com:owner/other.git", "https://github.com/owner/repo")


def test_detection_endpoint_reads_the_repository_without_writing(tmp_path) -> None:
    """@brief Read repository returns detected values and leaves the server untouched."""
    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        )
        assert detected.status_code == 200, detected.text
        value = detected.json()
        assert value == {
            "url": URL,
            "kind": "gitea",
            "login": "dcp",
            "repo": "dpasare/Sample.Service",
            "default_branch": "develop",
            "name": "sample.service",
            "display_name": "Sample.Service",
            "repo_path": str((tmp_path / "home" / "repos" / "sample.service").resolve()),
            "clone": "new",
        }
        assert not (tmp_path / "home" / "repos").exists()
        assert not any(call[:2] == ["git", "clone"] for call in forge.calls)
        assert (
            client.post(
                "/api/v1/projects/repository-source", json={"url": "file:///x"}, headers=headers
            ).json()["detail"]["code"]
            == "repository_url_invalid"
        )
        assert client.post("/api/v1/projects/repository-source", json={"url": URL}).status_code in {
            401,
            403,
        }
    unreachable = create_app(tmp_path / "other", probe_runner=Forge(reachable=False))
    with TestClient(unreachable) as client:
        response = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=_login(client)
        )
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "repository_unreachable"


def test_create_clones_after_review_and_checks_do_not(tmp_path) -> None:
    """@brief Preview and checks leave the clone pending; creation clones and publishes."""
    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        body = _setup(detected)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        assert preview["structural_valid"], preview
        assert preview["review"]["clone_url"] == URL and preview["review"]["clone"] == "new"
        check = client.post(
            "/api/v1/projects/setup-check",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert check.status_code == 200, check.text
        assert check.json()["checks"]["aegis_files"] == "not-checked"
        assert not Path(detected["repo_path"]).exists()
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert (Path(detected["repo_path"]) / ".agentic" / "aegis.py").is_file()
        clone = [call for call in forge.calls if call[:2] == ["git", "clone"]]
        assert clone == [["git", "clone", "--origin", "origin", "--", URL, detected["repo_path"]]]
        assert app.state.profiles.load("sample.service")


def test_matching_existing_clone_is_reused_and_occupied_folder_refused(tmp_path) -> None:
    """@brief A clone of the same remote is reused; another folder there is never overwritten."""
    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        target = Path(detected["repo_path"])
        (target / ".git").mkdir(parents=True)
        (target / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = https://elsewhere.invalid/o/r\n', encoding="utf-8"
        )
        occupied = client.post(
            "/api/v1/projects/setup-preview", json=_setup(detected), headers=headers
        ).json()
        assert not occupied["structural_valid"]
        assert {issue["code"] for issue in occupied["issues"]} == {"clone_path_occupied"}
        (target / ".git" / "config").write_text(
            f'[remote "origin"]\n\turl = {URL}\n', encoding="utf-8"
        )
        (target / ".agentic").mkdir()
        for name in ("aegis.py", "aegis.toml"):
            (target / ".agentic" / name).write_text("", encoding="utf-8")
        again = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        assert again["clone"] == "existing"
        preview = client.post(
            "/api/v1/projects/setup-preview", json=_setup(again), headers=headers
        ).json()
        assert preview["structural_valid"] and preview["review"]["clone"] == "existing"
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**_setup(again), "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert not any(call[:2] == ["git", "clone"] for call in forge.calls)


@pytest.mark.parametrize(
    ("forge", "code"),
    [
        (Forge(aegis=False), "repository_aegis_missing"),
        (Forge(branch=False), "repository_branch_missing"),
    ],
)
def test_failed_clone_verification_removes_the_fresh_clone(tmp_path, forge, code) -> None:
    """@brief A clone without AEGIS or the target branch is removed and nothing is published."""
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        body = _setup(detected)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 409, created.text
        assert created.json()["detail"]["code"] == code
        assert not Path(detected["repo_path"]).exists()
        assert app.state.profiles.id_availability("sample.service")


def test_folder_appearing_after_review_is_refused_and_kept(tmp_path) -> None:
    """@brief A clone location taken between review and creation is never cloned into or removed."""
    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        body = _setup(detected)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        target = Path(detected["repo_path"])
        target.mkdir(parents=True)
        (target / "keep.txt").write_text("someone else", encoding="utf-8")
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 400, created.text
        assert {issue["code"] for issue in created.json()["detail"]["issues"]} == {
            "clone_path_occupied"
        }
        assert (target / "keep.txt").read_text(encoding="utf-8") == "someone else"
        assert not any(call[:2] == ["git", "clone"] for call in forge.calls)


def test_clone_answers_must_match_the_url_and_allowed_location(tmp_path) -> None:
    """@brief The repository must match the URL; the clone may move, but not into ADORE folders."""
    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()

        def issues(**changes) -> set[str]:
            preview = client.post(
                "/api/v1/projects/setup-preview", json=_setup(detected, **changes), headers=headers
            ).json()
            return {issue["field"] for issue in preview["issues"]}

        assert issues(repo="someone/else") == {"repo"}
        assert "clone_url" in issues(clone_url="file:///srv/x")
        assert issues(repo_path="relative/clone") == {"repo_path"}
        assert issues(repo_path=str(tmp_path / "home" / "worktrees" / "x")) == {"repo_path"}
        assert issues(repo_path=str(tmp_path / "home" / "repos")) == {"repo_path"}
        moved = tmp_path / "elsewhere" / "service"
        moved.parent.mkdir()  # Outside ADORE home the parent must already exist.
        body = _setup(detected, repo_path=str(moved))
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        assert preview["structural_valid"], preview
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert (moved / ".agentic" / "aegis.py").is_file()
        assert not Path(detected["repo_path"]).exists()


def test_failed_clone_and_reserved_names(tmp_path) -> None:
    """@brief A failing clone leaves nothing behind; reserved repository names get a suffix."""

    class Failing(Forge):
        def __call__(self, argv, **options):
            if list(argv[:2]) == ["git", "clone"]:
                Path(argv[-1], "partial").write_text("x", encoding="utf-8")
                return CommandResult(argv=list(argv), exit_code=128, stderr="denied")
            return super().__call__(argv, **options)

    app = create_app(tmp_path / "home", probe_runner=Failing())
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        body = _setup(detected)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 502
        assert created.json()["detail"]["code"] == "repository_clone_failed"
        assert not Path(detected["repo_path"]).exists()
        for name, expected in (("import", "import-2"), ("clone", "clone-2")):
            value = client.post(
                "/api/v1/projects/repository-source",
                json={"url": f"https://github.com/owner/{name}.git"},
                headers=headers,
            ).json()
            assert value["name"] == expected, value


def test_tilde_marker_parent_and_publication_failure(tmp_path, monkeypatch) -> None:
    """@brief Paths are used as typed; clones in progress, missing parents, failed publication."""
    import adore.web.app as web_app

    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()

        def fields(**changes) -> dict[str, set[str]]:
            preview = client.post(
                "/api/v1/projects/setup-preview", json=_setup(detected, **changes), headers=headers
            ).json()
            return {issue["field"]: issue["code"] for issue in preview["issues"]}

        assert fields(repo_path="~/repos/service") == {"repo_path": "setup_field_invalid"}
        assert fields(repo_path=str(tmp_path / "missing" / "parent" / "service")) == {
            "repo_path": "setup_field_invalid"
        }
        target = Path(detected["repo_path"])
        target.parent.mkdir(parents=True)
        marker = target.parent / f".{target.name}.adore-cloning"
        marker.write_text("", encoding="utf-8")
        assert fields() == {"repo_path": "clone_path_occupied"}
        marker.unlink()

        def refuse(*_args, **_kwargs):
            raise web_app._error(409, "project_exists")

        body = _setup(detected)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        monkeypatch.setattr(web_app, "_publish_paused", refuse)
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 409, created.text
        assert any(call[:2] == ["git", "clone"] for call in forge.calls)
        assert not target.exists() and not marker.exists()


def test_stale_cloning_marker_is_ignored_and_replaced(tmp_path) -> None:
    """@brief A marker left by an interrupted request does not block the location forever."""
    import os
    import time

    forge = Forge()
    app = create_app(tmp_path / "home", probe_runner=forge)
    with TestClient(app) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        target = Path(detected["repo_path"])
        target.parent.mkdir(parents=True)
        marker = target.parent / f".{target.name}.adore-cloning"
        marker.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(marker, (old, old))
        body = _setup(detected)
        preview = client.post("/api/v1/projects/setup-preview", json=body, headers=headers).json()
        assert preview["structural_valid"], preview
        created = client.post(
            "/api/v1/projects/setup-create",
            json={**body, "revision": preview["revision"]},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        assert (target / ".agentic" / "aegis.py").is_file() and not marker.exists()
    # An interrupted clone left both its marker and a partial folder: refused, never reused.
    other = create_app(tmp_path / "other", probe_runner=Forge())
    with TestClient(other) as client:
        headers = _login(client)
        detected = client.post(
            "/api/v1/projects/repository-source", json={"url": URL}, headers=headers
        ).json()
        target = Path(detected["repo_path"])
        (target / ".git").mkdir(parents=True)
        (target / ".git" / "config").write_text(
            f'[remote "origin"]{chr(10)}{chr(9)}url = {URL}{chr(10)}', encoding="utf-8"
        )
        marker = target.parent / f".{target.name}.adore-cloning"
        marker.write_text("", encoding="utf-8")
        os.utime(marker, (old, old))
        preview = client.post(
            "/api/v1/projects/setup-preview", json=_setup(detected), headers=headers
        ).json()
        assert {issue["code"] for issue in preview["issues"]} == {"clone_path_occupied"}
