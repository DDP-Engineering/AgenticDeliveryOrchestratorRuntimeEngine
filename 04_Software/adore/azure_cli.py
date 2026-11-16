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
@file       azure_cli.py
@brief      Shell-free Azure CLI launch and deterministic extension SDK requests.
@details    Runs with the host Azure CLI's Python, not a new application dependency.
            Authentication remains owned by the official azure-devops extension.
            This file is also a standalone child entry point; import only stdlib.
"""
from __future__ import annotations

# IMPORTS
import json
import ntpath
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

# CONSTANTS
# Microsoft v7.1 SDK location IDs. Resource names alone are NOT unique.
# Sources: microsoft/azure-devops-python-api, v7_1/{git,work_item_tracking} clients.
LOCATIONS = {
    ("wit", "workItems"): "72c7ddf8-2cdc-4f60-90cd-ab71c14a399b",
    ("wit", "wiql"): "1a9c53f7-f243-4447-b110-35ef023636e4",
    ("wit", "comments"): "608aac0a-32e1-4493-a863-b9cf4566d257",
    ("wit", "classificationNodes"): "5a172953-1b41-49d3-840a-33f79c3ce89f",
    ("git", "repositories"): "225f7195-f9c7-4d14-ab28-a83f7ff77e1f",
    ("git", "pullRequests"): "9946fd70-0d40-406e-b686-b4744cbbcc37",
    ("git", "pullRequestWorkItems"): "0a637fcc-5370-4ce8-b0e8-98091f5f9482",
    ("git", "pullRequestLabels"): "f22387e3-984e-4c52-9c6d-fbb8f14c812d",
    ("git", "pullRequestThreads"): "ab6e2e5d-a0b7-4153-b64a-a4efe0d49449",
    ("git", "pullRequestThreadComments"): "965a3ec7-5ed8-455a-bdcb-835a5ea7fe7b",
    ("git", "pullRequestIterations"): "d43911ee-6958-46b0-a42b-8445b8a0d004",
    ("git", "pullRequestIterationStatuses"): "75cf11c5-979f-4038-a76e-058a06adf2bf",
}

# PUBLIC API

def azure_python(env: dict[str, str] | None = None, command: str = "az") -> str:
    """@brief Locate the installed Azure CLI interpreter without executing a shell.
    @param[in] env Effective child environment, including its account's PATH.
    @param[in] command Azure launcher name/path to resolve.
    @return Absolute Python executable in the selected Azure installation.
    @exception OSError Missing CLI, unsupported launcher or missing interpreter.
    @note Supports Windows MSI/ZIP/pip layouts and POSIX Python entry scripts.
    """
    source = os.environ if env is None else env
    found = shutil.which(command, path=source.get("PATH", os.defpath))
    if not found:
        raise FileNotFoundError("Azure CLI is not installed on the host PATH")
    launcher = Path(found).absolute()
    if sys.platform == "win32":
        # MSI: CLI2/wbin/az.cmd; ZIP: root/bin/az.cmd; pip: Scripts/az.bat.
        if launcher.suffix.lower() not in {".cmd", ".bat"}:
            raise OSError("Unsupported Azure CLI launcher; install the official CLI")
        candidates = [launcher.parent.parent / "python.exe", launcher.parent / "python.exe"]
    else:
        launcher = launcher.resolve()
        with launcher.open(encoding="utf-8") as stream:
            header = stream.readline(4096).strip()
        if not header.startswith("#!"):
            raise OSError("Azure CLI must expose a Python entry script")
        parts = shlex.split(header[2:])
        if len(parts) == 2 and parts[0] == "/usr/bin/env":
            resolved = shutil.which(parts[1], path=source.get("PATH", os.defpath))
            parts = [resolved] if resolved else []
        if (len(parts) != 1 or not Path(parts[0]).is_absolute()
                or not re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", Path(parts[0]).name)):
            raise OSError("Unsupported Azure CLI Python entry script")
        candidates = [Path(parts[0])]
    for candidate in candidates:
        if candidate.is_file():
            # Do not resolve Python symlinks: doing so loses a pip/venv installation.
            return str(candidate)
    raise FileNotFoundError("Azure CLI Python is missing; repair the host CLI installation")


def windows_azure_argv(argv: list[str], env: dict[str, str]) -> list[str]:
    """@brief Bypass az.cmd with its bundled Python; never parse human args as cmd text.
    @param[in] argv Original shell-free command arguments.
    @param[in] env Effective child environment used to resolve the Azure installation.
    @return Original argv, or an equivalent direct Azure Python invocation.
    @exception OSError Azure installation cannot be resolved safely.
    """
    if (sys.platform == "win32" and argv
            and ntpath.basename(argv[0]).lower() in {"az", "az.cmd", "az.bat"}):
        return [azure_python(env, argv[0]), "-IBm", "azure.cli", *argv[1:]]
    return argv


def sdk_request(spec: dict) -> dict:
    """@brief Send one request by immutable location ID through the official extension.
    @param[in] spec Private request from AzureDevOpsForge, including exact scope.
    @return JSON object with the response-header continuation token preserved.
    @exception Exception SDK, installation, authentication or response failure.
    @note Called only inside the Azure CLI runtime; imports never install extensions.
    """
    location = LOCATIONS[(spec["area"], spec["resource"])]
    if (not re.fullmatch(r"https://dev\.azure\.com/[A-Za-z0-9][A-Za-z0-9-]{0,49}",
                         spec["organization"])
            or spec["method"] not in {"GET", "POST", "PATCH"}
            or not spec["route"].get("project")
            or spec["area"] == "git" and not spec["route"].get("repositoryId")):
        raise ValueError("Invalid Azure request scope")
    from azure.cli.core import get_default_cli
    from azure.cli.core.extension import get_extension

    get_default_cli()  # Initialize the same host account/configuration context as az.
    extension = get_extension("azure-devops")
    sys.path.insert(0, extension.path)
    from azext_devops.dev.common.services import get_connection
    from azext_devops.devops_sdk.client import Client

    connection = get_connection(spec["organization"])
    areas = connection._get_resource_areas(force=True)
    urls = {area.location_url for area in areas if area.name.lower() == spec["area"]}
    if len(urls) != 1:
        raise ValueError("Azure service area is unavailable or ambiguous")
    client = Client(urls.pop(), connection._creds)
    response = client._send(
        http_method=spec["method"], location_id=location, version=spec["version"],
        route_values=spec["route"], query_parameters=spec["query"], content=spec["body"],
        media_type=spec["media_type"], accept_media_type="application/json")
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Azure response is not an object")
    data["continuation_token"] = response.headers.get("X-MS-ContinuationToken")
    return data


def main(argv: list[str] | None = None) -> int:
    """@brief Execute a private request with a 55-second inner child bound.
    @param[in] argv Internal mode and request-file path, never shell command text.
    @return Zero on success, one on value-free failure.
    @note The parent CommandRunner owns the outer 60-second bound.
    """
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2 or args[0] not in {"request", "sdk"}:
            raise ValueError("Invalid Azure bridge invocation")
        if args[0] == "request":
            result = subprocess.run(
                [azure_python(), "-I", "-B", str(Path(__file__).absolute()), "sdk", args[1]],
                capture_output=True, stdin=subprocess.DEVNULL, timeout=55, check=False,
                **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
            if result.returncode:
                raise RuntimeError("Azure request failed")
            sys.stdout.buffer.write(result.stdout)
        else:
            path = Path(args[1])
            if path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("Azure request exceeds limit")
            spec = json.loads(path.read_text(encoding="utf-8"))
            print(json.dumps(sdk_request(spec)))
        return 0
    except Exception:
        # Never copy SDK exceptions, human content, tokens or child streams to logs.
        print("Azure request failed; check host CLI/extension, sign-in and resource access",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
