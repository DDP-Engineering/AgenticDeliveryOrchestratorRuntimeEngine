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
@file       test_azure_cli.py
@brief      Deterministic Azure SDK locations and shell-free Windows launch contracts.
@details    The JSON fixture is a resource-location subset of Microsoft's public
            azure-devops-cli-extension recording:
            azext_devops/tests/latest/integrationtests/recordings/test_invoke_command_basic.yaml.
            It retains competing same-name locations, not handpicked unique names.
            SDK bootstrap/transport and process creation are faked; no credentials,
            installed Azure tooling or network are used.
"""
# IMPORTS
import json
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from urllib.parse import quote

from adore import azure_cli
from adore.doctor import detect_platform_cli
from adore.forge.azure_devops import AzureDevOpsForge
from adore.util import CommandResult, run_command
import pytest

from tests.test_azure_devops import SCOPE, pull, work_item

# CONSTANTS
METADATA = json.loads(
    (Path(__file__).parent / "fixtures/azure_resource_locations.json").read_text())

# LOCAL HELPERS
@pytest.fixture
def sdk(monkeypatch, tmp_path):
    """@brief Bootstrap a fake installed extension, with real server route metadata."""
    sent, replies = [], []
    credentials = object()

    class Client:
        """@brief Resolve the exact SDK location ID against competing official routes."""
        def __init__(self, url, creds):
            assert url == "https://dev.azure.com/contoso"
            assert creds is credentials

        def _send(self, **request):
            location, = [v for v in METADATA if v["id"] == request["location_id"]]
            values = {"area": location["area"], "resource": location["resourceName"],
                      **request["route_values"]}

            def substitute(match):
                """@brief Model optional and catch-all SDK route substitution."""
                key = match[1].lstrip("*")
                return quote(str(values.get(key, "")), safe="/" if match[1][0] == "*" else "")

            wire_path = re.sub(r"\{([^}]+)\}", substitute, location["routeTemplate"])
            wire_path = re.sub("/+", "/", wire_path).rstrip("/")
            sent.append((request, wire_path))
            reply = replies.pop(0) if replies else {"value": []}
            if isinstance(reply, Exception):
                raise reply
            token = "next" if location["resourceName"] == "comments" else None
            return SimpleNamespace(json=lambda: reply, headers={"X-MS-ContinuationToken": token})

    connection = SimpleNamespace(_creds=credentials, _get_resource_areas=lambda **_: [
        SimpleNamespace(name=area, location_url="https://dev.azure.com/contoso")
        for area in ("git", "wit")])

    def get_connection(organization):
        assert organization == "https://dev.azure.com/contoso"
        return connection

    for name, members in {
        "azure": {}, "azure.cli": {},
        "azure.cli.core": {"get_default_cli": lambda: None},
        "azure.cli.core.extension": {"get_extension": lambda name: SimpleNamespace(
            path=str(tmp_path / name))},
        "azext_devops": {}, "azext_devops.dev": {}, "azext_devops.dev.common": {},
        "azext_devops.dev.common.services": {"get_connection": get_connection},
        "azext_devops.devops_sdk": {}, "azext_devops.devops_sdk.client": {"Client": Client},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(members)
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    return sent, replies


def spec(area, resource, **route):
    """@brief Build a scoped request at the public CLI bridge boundary."""
    return {"organization": SCOPE["organization"], "area": area, "resource": resource,
            "method": "GET", "route": {"project": "Payments", **route}, "query": {},
            "body": None, "version": "7.1", "media_type": "application/json"}


# PUBLIC API / TESTS
@pytest.mark.parametrize("area,resource,route,path", [
    ("wit", "workItems", {"id": 25}, "wit/workItems/25"),
    ("wit", "wiql", {}, "wit/wiql"),
    ("wit", "comments", {"workItemId": 25}, "wit/workItems/25/comments"),
    ("wit", "comments", {"workItemId": 25, "commentId": 3}, "wit/workItems/25/comments/3"),
    ("wit", "classificationNodes", {"structureGroup": "Areas", "path": "Backend/Child"},
     "wit/classificationNodes/Areas/Backend/Child"),
    ("git", "repositories", {}, "git/repositories/backend"),
    ("git", "pullRequests", {}, "git/repositories/backend/pullRequests"),
    ("git", "pullRequests", {"pullRequestId": 7}, "git/repositories/backend/pullRequests/7"),
    ("git", "pullRequestLabels", {"pullRequestId": 7},
     "git/repositories/backend/pullRequests/7/labels"),
    ("git", "pullRequestWorkItems", {"pullRequestId": 7},
     "git/repositories/backend/pullRequests/7/workitems"),
    ("git", "pullRequestThreads", {"pullRequestId": 7},
     "git/repositories/backend/pullRequests/7/threads"),
    ("git", "pullRequestThreadComments", {"pullRequestId": 7, "threadId": 9, "commentId": 2},
     "git/repositories/backend/pullRequests/7/threads/9/comments/2"),
    ("git", "pullRequestIterations", {"pullRequestId": 7},
     "git/repositories/backend/pullRequests/7/iterations"),
    ("git", "pullRequestIterationStatuses", {"pullRequestId": 7, "iterationId": 2},
     "git/repositories/backend/pullRequests/7/iterations/2/statuses"),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_locations_ignore_metadata_order_and_same_name_competitors(sdk, monkeypatch,
                                                                  area, resource, route, path,
                                                                  reverse):
    """@brief All resource families use exact official routes, even with duplicate names."""
    monkeypatch.setattr(sys.modules[__name__], "METADATA", METADATA[::-1] if reverse else METADATA)
    if area == "git":
        route = {"repositoryId": "backend", **route}
    request = spec(area, resource, **route)
    expected_token = "next" if resource == "comments" else None
    assert azure_cli.sdk_request(request)["continuation_token"] == expected_token
    sent, _ = sdk
    assert sent[-1][1] == "Payments/_apis/" + path


def test_public_adapter_work_item_patch_and_pr_publication_reach_exact_endpoints(sdk):
    """@brief Exercise adapter serialization through SDK dispatch, not just mocked JSON."""
    sent, replies = sdk
    replies.extend([work_item(), work_item(**{"System.Tags": "human-owned; agent-ready; P2; new"}),
                    pull(), {"value": []}])

    def runner(argv, **kwargs):
        assert kwargs["timeout"] == 60
        path = Path(argv[-1])
        assert path.stat().st_mode & 0o077 == 0
        request = json.loads(path.read_text(encoding="utf-8"))
        return CommandResult(stdout=json.dumps(azure_cli.sdk_request(request)))

    adapter = AzureDevOpsForge("backend", runner, **SCOPE)
    adapter.add_labels(25, ["new"])
    adapter.open_merge_request("adore/25", "main", "t", "body")
    assert [(r["http_method"], path) for r, path in sent[:3]] == [
        ("GET", "Payments/_apis/wit/workItems/25"),
        ("PATCH", "Payments/_apis/wit/workItems/25"),
        ("POST", "Payments/_apis/git/repositories/backend/pullRequests")]
    assert sent[1][0]["media_type"] == "application/json-patch+json"
    assert sent[1][0]["content"][0] == {"op": "test", "path": "/rev", "value": 3}
    assert "completionOptions" not in sent[2][0]["content"]


@pytest.mark.parametrize("change", [{"resource": "unknown"}, {"method": "DELETE"},
    {"route": {}}, {"organization": "https://server/tfs"}])
def test_sdk_boundary_rejects_unknown_locations_and_unscoped_requests(sdk, change):
    """@brief Invalid requests never reach a transport or rely on CLI defaults."""
    with pytest.raises((KeyError, ValueError)):
        azure_cli.sdk_request({**spec("wit", "workItems", id=25), **change})
    assert not sdk[0]


def test_sdk_errors_and_unexpected_json_are_value_free(sdk, tmp_path, capsys):
    """@brief Child errors cannot echo credentials, payloads or SDK streams."""
    path = tmp_path / "request.json"
    path.write_text(json.dumps(spec("wit", "workItems", id=25)), encoding="utf-8")
    for value in (RuntimeError("PAT-DO-NOT-LOG"), ["PAT-DO-NOT-LOG"]):
        sdk[1].append(value)
        assert azure_cli.main(["sdk", str(path)]) == 1
        captured = capsys.readouterr()
        assert not captured.out and "PAT-DO-NOT-LOG" not in captured.err


def test_windows_cli_probe_and_arguments_bypass_cmd_safely(monkeypatch, tmp_path):
    """@brief The standard MSI launcher works without cmd expansion or shell quoting."""
    root = tmp_path / "Program Files" / "Azure CLI2"
    (root / "wbin").mkdir(parents=True)
    launcher = root / "wbin" / "az.CMD"
    launcher.touch()
    python = root / "python.exe"
    python.touch()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(azure_cli.shutil, "which", lambda *_, **__: str(launcher))
    calls = []

    def execute(argv, **kwargs):
        calls.append(argv)
        assert argv[:3] == [str(python), "-IBm", "azure.cli"]
        assert not kwargs.get("shell") and kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["creationflags"] == 0x08000000
        output = b'{"name":"azure-devops"}' if "extension" in argv else b'azure-cli 2.80.0'
        return SimpleNamespace(returncode=0, stdout=output, stderr=b"")

    monkeypatch.setattr("adore.util.subprocess.run", execute)
    assert detect_platform_cli("azure_devops").present
    human = 'space & whoami | < > ^ ! %PATH% "quoted"\nGrüße'
    original = ["az", "repos", "pr", "label", "remove", "--name", human]
    result = run_command(original, timeout=8, env={"PATH": str(root / "wbin")})
    assert result.ok and result.argv == original
    assert calls[-1][3:] == original[1:]
    python.unlink()
    calls.clear()
    assert run_command(["az", "--version"]).exit_code == 127
    assert not calls


def test_cli_runtime_resolution_supports_zip_and_posix_but_refuses_shell_wrappers(
        monkeypatch, tmp_path):
    """@brief Only known Python layouts are used; arbitrary shell text is not executed."""
    monkeypatch.setattr(sys, "platform", "win32")
    (tmp_path / "bin").mkdir()
    launcher = tmp_path / "bin" / "az.cmd"
    launcher.touch()
    python = tmp_path / "python.exe"
    python.touch()
    monkeypatch.setattr(azure_cli.shutil, "which", lambda *_, **__: str(launcher))
    assert azure_cli.azure_python() == str(python)
    monkeypatch.setattr(sys, "platform", "linux")
    python = tmp_path / "bin" / "python3"
    python.touch()
    launcher.write_text(f"#!{python}\n", encoding="utf-8")
    assert azure_cli.azure_python() == str(python)
    launcher.write_text("#!/bin/sh\nexec arbitrary shell text\n", encoding="utf-8")
    with pytest.raises(OSError):
        azure_cli.azure_python()


def test_bridge_request_and_sdk_entry_points_return_only_json(monkeypatch, sdk, tmp_path, capsys):
    """@brief Both process entry modes preserve successful JSON without forwarding stderr."""
    path = tmp_path / "request.json"
    path.write_text(json.dumps(spec("wit", "workItems", id=25)), encoding="utf-8")
    sdk[1].append({"id": 25})
    assert azure_cli.main(["sdk", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"id": 25, "continuation_token": None}
    monkeypatch.setattr(azure_cli, "azure_python", lambda: "/azure/python")
    monkeypatch.setattr(azure_cli.subprocess, "run", lambda *_, **__: SimpleNamespace(
        returncode=0, stdout=b'{"id":25}', stderr=b"PAT-DO-NOT-LOG"))
    assert azure_cli.main(["request", str(path)]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"id": 25} and not captured.err


def test_bridge_bounds_child_and_sanitizes_launch_failure(monkeypatch, tmp_path, capsys):
    """@brief Missing tooling and hung SDK children cannot escape the parent CLI contract."""
    monkeypatch.setattr(azure_cli, "azure_python", lambda: "/azure/python")

    def execute(argv, **kwargs):
        assert argv[:3] == ["/azure/python", "-I", "-B"]
        assert argv[-2:] == ["sdk", str(tmp_path / "request.json")]
        assert kwargs["timeout"] == 55 and not kwargs.get("shell")
        raise subprocess.TimeoutExpired(argv, 55, stderr=b"PAT-DO-NOT-LOG")

    monkeypatch.setattr(azure_cli.subprocess, "run", execute)
    assert azure_cli.main(["request", str(tmp_path / "request.json")]) == 1
    assert "PAT-DO-NOT-LOG" not in capsys.readouterr().err

def test_official_sdk_dispatch_when_optional_host_libraries_are_available(monkeypatch):
    """@brief Run Microsoft's real resolver/URL/version code with HTTP and auth disabled.
    @note Optional host-tool libraries are not application/test dependencies. This
          test skips offline when they are absent; it never installs anything.
    """
    core = pytest.importorskip("azure.cli.core")
    extension = pytest.importorskip("azure.cli.core.extension")
    client_module = pytest.importorskip("azext_devops.devops_sdk.client")
    client = client_module.Client
    locations = [SimpleNamespace(
        id=row["id"], area=row["area"], resource_name=row["resourceName"],
        route_template=row["routeTemplate"], min_version=float(row["minVersion"]),
        max_version=float(row["maxVersion"]), released_version=row["releasedVersion"],
        resource_version=4) for row in METADATA]
    connection = SimpleNamespace(_creds=None, _get_resource_areas=lambda **_: [
        SimpleNamespace(name=area, location_url=SCOPE["organization"]) for area in ("git", "wit")])
    services = ModuleType("azext_devops.dev.common.services")
    services.get_connection = lambda organization: connection
    monkeypatch.setitem(sys.modules, services.__name__, services)
    monkeypatch.setattr(core, "get_default_cli", lambda: None)
    monkeypatch.setattr(extension, "get_extension", lambda name: SimpleNamespace(path="/unused"))
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setattr(client, "_get_resource_locations", lambda self, **_: locations)
    monkeypatch.setattr(client, "_locations_cache", {})
    sent = []

    def transport(self, request, headers=None, **kwargs):
        """@brief Stop before HTTP/auth while retaining the actual SDK-built URL."""
        sent.append((request.method, request.url, headers))
        return SimpleNamespace(json=lambda: {"value": []}, headers={})

    monkeypatch.setattr(client, "_send_request", transport)
    for reverse in (False, True):
        if reverse:
            locations.reverse()
        client._locations_cache.clear()
        for area, resource in azure_cli.LOCATIONS:
            route = {"repositoryId": "backend", "id": 25, "workItemId": 25,
                     "pullRequestId": 7, "threadId": 9, "commentId": 2, "iterationId": 3,
                     "structureGroup": "Areas", "path": "Backend/Child"}
            for method in ("GET", "POST", "PATCH"):
                request = {**spec(area, resource, **route), "method": method}
                if resource == "comments":
                    request["version"] = "7.1-preview.4"
                azure_cli.sdk_request(request)
            url = sent[-1][1]
            if resource == "workItems":
                assert url.endswith("/wit/workItems/25")
            if resource == "pullRequests":
                assert url.endswith("/git/repositories/backend/pullRequests/7")
            if resource == "comments":
                assert url.endswith("/wit/workItems/25/comments/2")
                assert sent[-1][2]["Accept"].endswith("api-version=7.1-preview.4")
            if resource == "wiql":
                assert url.endswith("/wit/wiql")
    assert len(sent) == 72

# END OF FILE
