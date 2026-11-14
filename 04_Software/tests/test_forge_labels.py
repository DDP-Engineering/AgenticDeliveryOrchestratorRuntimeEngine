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
@file test_forge_labels.py
@brief Creating a project's missing ADORE labels in its forge.
@details ADORE reads the repository's labels once and creates only the missing
         ones named by the project's settings; existing labels are untouched.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path

from adore.config import default_config
from adore.forge.base import ForgeError
from adore.forge.gitea import GiteaForge
from adore.forge.github import GitHubForge
from adore.forge.gitlab import GitLabForge
from adore.forge_labels import ensure_labels, project_labels
from adore.profiles import ProfileStore
from adore.util import CommandResult
from adore.web.app import create_app
import pytest

from tests.configuration_client import TestClient
from tests.test_forge import FakeRunner


# LOCAL HELPERS
def _ok(stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(exit_code=0, stdout=stdout, stderr=stderr)


class LabelForge:
    """@brief A forge double holding repository labels."""

    def __init__(self, names: list[str], fail_create: str = "", fail_list: bool = False) -> None:
        self.names, self.fail_create, self.fail_list = list(names), fail_create, fail_list
        self.created: list[tuple[str, str, str]] = []

    def list_labels(self) -> list[str]:
        if self.fail_list:
            raise ForgeError("cannot list labels")
        return list(self.names)

    def create_label(self, name: str, color: str, description: str) -> None:
        if name == self.fail_create:
            raise ForgeError("403 Forbidden")
        self.created.append((name, color, description))
        self.names.append(name)


# TESTS
def test_project_labels_come_from_the_settings():
    """@brief Every label the settings name, once, each with a colour and description."""
    specs = project_labels(default_config())
    names = [spec.name for spec in specs]
    for name in (
        "agent-ready",
        "agent-working",
        "agent-clarify",
        "agent-answered",
        "agent-mr",
        "agent-failed",
        "agent-done",
        "agent-hold",
        "no-agent",
        "P1",
        "P2",
        "P3",
        "agent-approved",
        "agent-revise",
        "agent-quick",
    ):
        assert name in names, name
    assert len({name.casefold() for name in names}) == len(names)
    assert all(len(spec.color) == 6 and spec.description for spec in specs)


def test_only_missing_labels_are_created():
    """@brief Existing labels (any case) are kept; the rest are created."""
    specs = project_labels(default_config())
    forge = LabelForge(["Agent-Ready", "P1", "unrelated"])
    report = ensure_labels(forge, specs)
    assert set(report["existing"]) == {"agent-ready", "P1"}
    assert {name for name, _color, _desc in forge.created} == (
        {spec.name for spec in specs} - {"agent-ready", "P1"}
    )
    assert report["created"] == [name for name, _color, _desc in forge.created]
    assert report["failed"] == []
    # A second run creates nothing.
    again = ensure_labels(forge, specs)
    assert again["created"] == [] and len(again["existing"]) == len(specs)


def test_a_failed_create_is_reported_and_the_others_continue():
    """@brief One refused label does not stop the rest."""
    specs = project_labels(default_config())
    forge = LabelForge([], fail_create="agent-done")
    report = ensure_labels(forge, specs)
    assert report["failed"] == [{"name": "agent-done", "reason": "403 Forbidden"}]
    assert len(report["created"]) == len(specs) - 1


def test_a_failed_listing_creates_nothing():
    """@brief Without the existing labels nothing is created."""
    forge = LabelForge([], fail_list=True)
    with pytest.raises(ForgeError):
        ensure_labels(forge, project_labels(default_config()))
    assert forge.created == []


def test_github_lists_and_creates_through_the_api():
    """@brief Labels are read page by page and created with a colour without #."""
    runner = FakeRunner(_ok(json.dumps([{"name": "bug"}, {"name": "agent-ready"}])), _ok("{}"))
    forge = GitHubForge("owner/repo", runner=runner)
    assert forge.list_labels() == ["bug", "agent-ready"]
    forge.create_label("agent-done", "0E8A16", "Job finished")
    assert runner.calls[0] == ["gh", "api", "repos/owner/repo/labels?per_page=100&page=1"]
    assert runner.calls[1] == [
        "gh",
        "api",
        "--method",
        "POST",
        "repos/owner/repo/labels",
        "-f",
        "name=agent-done",
        "-f",
        "color=0E8A16",
        "-f",
        "description=Job finished",
    ]


def test_gitlab_lists_and_creates_through_the_api():
    """@brief GitLab takes the colour with #."""
    runner = FakeRunner(_ok(json.dumps([{"name": "P1"}])), _ok("{}"))
    forge = GitLabForge("group/project", runner=runner)
    assert forge.list_labels() == ["P1"]
    forge.create_label("P2", "FBCA04", "Medium priority")
    assert runner.calls[0] == ["glab", "api", "projects/group%2Fproject/labels?per_page=100&page=1"]
    assert runner.calls[1] == [
        "glab",
        "api",
        "--method",
        "POST",
        "projects/group%2Fproject/labels",
        "--raw-field",
        "name=P2",
        "--raw-field",
        "color=#FBCA04",
        "--raw-field",
        "description=Medium priority",
    ]


def test_gitea_lists_and_creates_through_the_api():
    """@brief Gitea goes through `tea api` with its HTTP status check."""
    runner = FakeRunner(
        _ok(json.dumps([{"name": "agent-hold"}]), "HTTP/1.1 200 OK\n"),
        _ok("{}", "HTTP/1.1 201 Created\n"),
    )
    forge = GiteaForge("owner/repo", runner=runner, login="ddp")
    assert forge.list_labels() == ["agent-hold"]
    forge.create_label("no-agent", "5319E7", "Never picked up")
    assert runner.calls[0][-1] == "repos/owner/repo/labels?limit=50&page=1"
    assert runner.calls[0][:5] == ["tea", "api", "-i", "--method", "GET"]
    create = runner.calls[1]
    assert create[:5] == ["tea", "api", "-i", "--method", "POST"]
    assert create[-1] == "repos/owner/repo/labels"
    assert create[create.index("name=no-agent") - 1 : create.index("name=no-agent") + 1] == [
        "--field",
        "name=no-agent",
    ]
    assert "color=#5319E7" in create


class GlabLabels:
    """@brief The web boundary: glab label listing and creation for the example project."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv, **_kwargs) -> CommandResult:
        argv = [str(part) for part in argv]
        self.calls.append(argv)
        if argv[:2] == ["glab", "api"] and "--method" not in argv:
            return CommandResult(
                argv=argv, exit_code=0, stdout=json.dumps([{"name": "agent-ready"}])
            )
        if argv[:2] == ["glab", "api"]:
            return CommandResult(argv=argv, exit_code=0, stdout="{}")
        return CommandResult(argv=argv, exit_code=0, stdout="")


def _profile(tmp_path: Path) -> ProfileStore:
    profiles = ProfileStore(tmp_path / "home")
    profiles.create("alpha", store_root=str(tmp_path / "state"))
    raw = (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(encoding="utf-8")
    raw = raw.replace('store_root = ".adore"', f'store_root = "{(tmp_path / "state").as_posix()}"')
    profiles.config_path("alpha").write_text(raw, encoding="utf-8")
    return profiles


def test_administrators_create_missing_labels_through_the_api(tmp_path):
    """@brief The endpoint reports created and existing labels and audits the action."""
    profiles = _profile(tmp_path)
    runner = GlabLabels()
    app = create_app(profiles.home, probe_runner=runner)
    app.state.web_store.create_user("dev", "longer-password", "developer")
    with TestClient(app) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/labels/ensure", headers={"X-CSRF-Token": csrf}
        )
        assert response.status_code == 200, response.text
        report = response.json()
        assert report["existing"] == ["agent-ready"]
        assert "agent-done" in report["created"] and report["failed"] == []
        actions = [row["action"] for row in app.state.web_store.recent_audit(10)]
        assert "labels-ensured" in actions
        client.delete("/api/v1/session")
        dev = client.post(
            "/api/v1/session", json={"username": "dev", "password": "longer-password"}
        ).json()["csrf"]
        assert client.post(
            "/api/v1/projects/alpha/labels/ensure", headers={"X-CSRF-Token": dev}
        ).status_code in (403, 404)


def test_a_failure_reason_keeps_the_forge_cause_not_the_command_line():
    """@brief The reason shows the forge's answer even when the argv is long."""
    from adore.forge_labels import failure_reason

    error = ForgeError(
        "gh command failed",
        [
            "gh",
            "api",
            "--method",
            "POST",
            "repos/acme-digital/delivery-orchestrator/labels",
            "-f",
            "name=x" * 20,
        ],
        "gh: Resource not accessible by integration (HTTP 403)",
    )
    reason = failure_reason(error)
    assert "HTTP 403" in reason and "argv" not in reason and len(reason) <= 200


class FailingListing(GlabLabels):
    """@brief A forge whose label listing fails."""

    def __call__(self, argv, **kwargs) -> CommandResult:
        argv = [str(part) for part in argv]
        if argv[:2] == ["glab", "api"] and "--method" not in argv:
            return CommandResult(argv=argv, exit_code=1, stderr="503 Service Unavailable")
        return super().__call__(argv, **kwargs)


def test_an_unreadable_label_list_is_a_typed_error(tmp_path):
    """@brief Nothing is created and the API answers 503 forge_read_failed."""
    profiles = _profile(tmp_path)
    runner = FailingListing()
    with TestClient(create_app(profiles.home, probe_runner=runner)) as client:
        csrf = client.post(
            "/api/v1/session", json={"username": "admin", "password": "admin"}
        ).json()["csrf"]
        response = client.post(
            "/api/v1/projects/alpha/labels/ensure", headers={"X-CSRF-Token": csrf}
        )
        assert response.status_code == 503, response.text
        assert response.json()["detail"]["code"] == "forge_read_failed"
    assert not any("--method" in call for call in runner.calls)


# END OF FILE
