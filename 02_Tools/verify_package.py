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
@file       verify_package.py
@brief      Test an actual extracted portable distribution on its native host.
@details    Uses isolated user data and an empty PATH, no forge/container/model
            calls, a fake browser, and bounded startup/shutdown. Temporary files
            are removed on exit; results go to the console only.
"""

from __future__ import annotations

# IMPORTS
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shlex
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from internal.check_release_consistency import check_package

# CONSTANTS
REPO = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform == "win32"


# PUBLIC API
def test_archive(argv: list[str] | None, resources: ExitStack) -> int:
    """@brief Verify a complete archive using its actual public entrypoints."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, nargs="?",
                        help="Archive to verify; defaults to this host's current release")
    args = parser.parse_args(argv)
    with (REPO / "04_Software/pyproject.toml").open("rb") as metadata:
        version = tomllib.load(metadata)["project"]["version"]
    system = platform.system().lower()
    suffix = ".zip" if WINDOWS else ".tar.gz"
    archive = (args.archive or REPO / "07_Delivery" / f"adore-{version}-{system}-x64{suffix}").resolve()
    if not archive.is_relative_to((REPO / "07_Delivery").resolve()):
        parser.error("test media must be under 07_Delivery")
    issues = check_package(archive)
    if issues:
        raise RuntimeError("; ".join(issues))
    work = Path(resources.enter_context(
        tempfile.TemporaryDirectory(prefix="adore-portable-check-")))
    extraction = work / "extracted"
    extraction.mkdir()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    checks = []

    def check(condition: bool, message: str) -> None:
        """@brief Report each proven contract to the console and stop on failure."""
        if not condition:
            raise RuntimeError(message)
        checks.append(message)
        print("PASS " + message, flush=True)

    def safe_name(name: str) -> None:
        """@brief Reject archive paths escaping the owned extraction directory."""
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise RuntimeError("unsafe archive member: " + name)

    if WINDOWS:
        with zipfile.ZipFile(archive) as handle:
            for entry in handle.infolist():
                safe_name(entry.filename)
            handle.extractall(extraction)
    else:
        with tarfile.open(archive) as handle:
            for entry in handle.getmembers():
                safe_name(entry.name)
                if not entry.isfile() and not entry.isdir():
                    raise RuntimeError("non-regular archive entry")
            handle.extractall(extraction, filter="data")
    bundle, = extraction.iterdir()
    relocated = extraction / "relocated application with spaces"
    if not bundle.resolve().is_relative_to(extraction.resolve()):
        raise RuntimeError("unexpected extraction root")
    bundle.rename(relocated)
    bundle = relocated
    home = extraction / "isolated user data"
    empty_bin = extraction / "empty-bin"
    empty_bin.mkdir()
    browser_result = extraction / "browser.json"
    browser_probe = extraction / "browser_probe.py"
    browser_probe.write_text(
        "import json, os, pathlib, sys, urllib.request\n"
        "opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))\n"
        "with opener.open(sys.argv[1]+'api/v1/ready', timeout=2) as response:\n"
        "    ready=json.load(response)\n"
        "pathlib.Path(os.environ['ADORE_TEST_BROWSER']).write_text(json.dumps(ready))\n",
        encoding="utf-8")
    python = bundle / ("python/python.exe" if WINDOWS else "python/bin/python3.12")
    env = dict(os.environ, PATH=str(empty_bin), PYTHONPATH="invalid-system-path",
               PYTHONHOME="invalid-system-home", ADORE_TEST_BROWSER=str(browser_result),
               BROWSER=shlex.join([python.as_posix(), "-I", "-B",
                                   browser_probe.as_posix()]) + " %s")
    for name in ("ADORE_HOME", "VIRTUAL_ENV"):
        env.pop(name, None)

    def command(script: str, arguments: list[str]) -> list[str] | str:
        """@brief Use only the OS shell and included Python; no host PATH tools."""
        if WINDOWS:
            shell = os.environ.get("COMSPEC")
            if not shell or not Path(shell).is_file():
                raise RuntimeError("Windows COMSPEC does not identify the native command shell")
            invocation = subprocess.list2cmdline([str(bundle / script), *arguments])
            return f'"{shell}" /d /s /c "{invocation}"'
        return [str(bundle / script), *arguments]

    def run(script: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        """@brief Run one public wrapper with a finite timeout and captured output."""
        return subprocess.run(command(script, arguments), cwd=work, env=env,
                              capture_output=True, text=True, timeout=180, check=False)

    start = "Start-ADORE.cmd" if WINDOWS else "start-adore.sh"
    stop = "Stop-ADORE.cmd" if WINDOWS else "stop-adore.sh"
    cli = "ADORE.cmd" if WINDOWS else "adore.sh"
    result = run(start, ["--verify"])
    if result.returncode != 0:
        raise RuntimeError("Package verification failed: " + result.stdout + result.stderr)
    check(result.returncode == 0, "relocated package verifies with no host tools on PATH")
    documentation = bundle / "Documentation"
    expected_guides = {"README.md", "Administrator_Guide.md", "Troubleshooting.md"}
    guide_files = {path.relative_to(documentation).as_posix()
                   for path in documentation.rglob("*") if path.is_file()}
    links_ok = True
    for guide in expected_guides:
        path = documentation / guide
        if not path.is_file():
            links_ok = False
            continue
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            candidate = (path.parent / target.split("#", 1)[0]).resolve()
            if not candidate.is_relative_to(bundle.resolve()) or not candidate.is_file():
                links_ok = False
    check(guide_files == expected_guides and links_ok,
          "user documentation contains only three practical guides with valid packaged links")
    result = run(cli, ["--help"])
    check(result.returncode == 0, "included CLI runs with no installed Python")
    result = subprocess.run([str(python), "-I", "-c",
                             "import adore.web.commands, sys; print(sys.dont_write_bytecode)"],
                            cwd=work, env=env, capture_output=True, text=True,
                            check=False, timeout=60)
    check(result.returncode == 0 and result.stdout.strip() == "True",
          "child engine imports preserve immutable media even without the -B flag")
    original = (bundle / "README.md").read_bytes()
    (bundle / "README.md").write_bytes(original + b"corrupt")
    result = run(start, ["--verify"])
    check(result.returncode != 0 and "changed" in result.stderr,
          "corrupt media fails closed before application startup")
    (bundle / "README.md").write_bytes(original)
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        result = run(start, ["--home", str(home), "--port", str(port), "--no-browser"])
        check(result.returncode != 0 and "in use" in result.stderr,
              "an unrelated occupied port is refused")
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    # An inert native fixture verifies host discovery without using a real agent.
    tools_directory = Path(resources.enter_context(
        tempfile.TemporaryDirectory(prefix="adore-installed-executor-check-")))
    executor_fixture = tools_directory / ("opencode.exe" if WINDOWS else "opencode")
    executor_fixture.write_text(
        "# Copyright (c) 2026 DDP Engineering\n"
        "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "# Commercial use requires a separate commercial license.\n"
        "# See the LICENSE.txt file for full license details. "
        "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
        "This inert discovery fixture must never execute.\n", encoding="utf-8")
    executor_fixture.chmod(0o755)
    node_fixture = tools_directory / ("node.exe" if WINDOWS else "node")
    node_fixture.write_bytes(executor_fixture.read_bytes())
    node_fixture.chmod(0o755)
    pi_fixture = tools_directory / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    pi_fixture.parent.mkdir(parents=True)
    pi_fixture.write_text(executor_fixture.read_text().replace("# ", "// "), encoding="utf-8")
    env.update(PATH=str(tools_directory), HOME=str(home), USERPROFILE=str(home),
               APPDATA=str(home / "roaming"))
    arguments = ["--home", str(home), "--port", str(port),
                 "--restart-limit", "0", "--startup-timeout", "45"]
    output = extraction / "console.log"
    with output.open("w", encoding="utf-8") as stream:
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if WINDOWS else {}
        process = subprocess.Popen(command(start, arguments), cwd=work, env=env,
                                   stdout=stream, stderr=subprocess.STDOUT, **options)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("launcher exited: " + output.read_text(encoding="utf-8"))
                if browser_result.exists():
                    break
                time.sleep(0.2)
            check(browser_result.exists(),
                  "automatic browser opens after real API/worker readiness")
            check(json.loads(browser_result.read_text()) == {"status": "ready", "worker": "ready"},
                  "browser sees a ready worker, not merely an HTTP listener")
            with opener.open(url, timeout=3) as response:
                check(response.status == 200 and b"<html" in response.read().lower(),
                      "compiled web interface is served from the included application")
            try:
                opener.open(url + "api/v1/local-executors", timeout=3)
                raise RuntimeError("anonymous executor discovery was accepted")
            except urllib.error.HTTPError as error:
                check(error.code == 401, "installed executor paths require authentication")
            try:
                opener.open(url + "api/v1/host-folders", timeout=3)
                raise RuntimeError("anonymous host folder listing was accepted")
            except urllib.error.HTTPError as error:
                check(error.code == 401, "host folder navigation requires authentication")
            cookies = urllib.request.HTTPCookieProcessor()
            authenticated = urllib.request.build_opener(urllib.request.ProxyHandler({}), cookies)
            login_request = urllib.request.Request(url + "api/v1/session",
                data=json.dumps({"username": "admin", "password": "admin"}).encode(),
                headers={"Content-Type": "application/json"})
            with authenticated.open(login_request, timeout=3) as response:
                check(response.status == 200, "isolated administrator can sign in")
            with authenticated.open(url + "api/v1/local-executors", timeout=10) as response:
                listing = json.load(response)
            installed = next(item["installations"] for item in listing["executors"]
                             if item["agent"] == "opencode")
            check(any(Path(item["executable"]) == executor_fixture.resolve()
                      and "{prompt}" in item["command"] for item in installed),
                  "packaged API detects native executor and supplies its command")
            pi_installed = next(item["installations"] for item in listing["executors"]
                                if item["agent"] == "pi")
            check(any(item["entrypoint"] and Path(item["entrypoint"]) == pi_fixture.resolve()
                      and Path(item["executable"]) == node_fixture.resolve()
                      for item in pi_installed),
                  "packaged API detects installed npm agent with native Node entrypoint")
            folder_query = urllib.parse.urlencode({"path": str(tools_directory)})
            with authenticated.open(url + "api/v1/host-folders?" + folder_query,
                                    timeout=10) as response:
                folders = json.load(response)
                check(response.headers.get("Cache-Control") == "no-store"
                      and folders["system"] == platform.system()
                      and Path(folders["path"]) == tools_directory.resolve()
                      and all(row["name"] != executor_fixture.name for row in folders["folders"]),
                      "packaged clone picker lists native host directories without file contents")
            check(not (tools_directory / "new-clone").exists(),
                  "host folder navigation does not create the proposed clone destination")
            try:
                authenticated.open(url + "api/v1/host-folders?path=relative", timeout=3)
                raise RuntimeError("relative host directory was accepted")
            except urllib.error.HTTPError as error:
                check(error.code == 400, "malformed host directory selection fails closed")
            owner = (home / ".launcher.json").read_bytes()
            result = run(start, ["--home", str(home), "--no-browser"])
            check(result.returncode == 0 and "already running" in result.stdout,
                  "second launch reuses the running instance and recorded custom port")
            check((home / ".launcher.json").read_bytes() == owner,
                  "second launch preserves the original service ownership")
            try:
                (home / ".launcher.json").write_bytes(b"{truncated")
                result = run(start, ["--home", str(home), "--no-browser",
                                     "--startup-timeout", "1"])
                check(result.returncode != 0 and "valid ownership record" in result.stderr,
                      "corrupt live-instance metadata fails closed")
            finally:
                (home / ".launcher.json").write_bytes(owner)
            marker = home / "persistent-user-data.txt"
            marker.write_text("retain across updates", encoding="utf-8")
            result = run(stop, ["--home", str(home)])
            check(result.returncode == 0, "public stop wrapper accepts the owner's stop request")
            code = process.wait(timeout=30)
            check(code == 0 and not (home / ".launcher.json").exists(),
                  "API and worker stop cleanly and release launcher ownership")
            check(marker.read_text(encoding="utf-8") == "retain across updates"
                  and (home / "web.db").is_file(),
                  "shutdown preserves user data outside the bundle")
            with socket.socket() as probe:
                check(probe.connect_ex(("127.0.0.1", port)) != 0,
                      "HTTP listener is closed after shutdown")
            result = run(start, ["--verify"])
            check(result.returncode == 0, "running the application leaves delivery media unchanged")
        finally:
            if process.poll() is None:
                run(stop, ["--home", str(home)])
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    print(f"All {len(checks)} checks passed; temporary files are removed on exit.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """@brief Own and clean temporary native runtime storage without delivery files.
    @param[in] argv Optional command arguments.
    @return Zero after all archive acceptance checks pass.
    """
    with ExitStack() as resources:
        return test_archive(argv, resources)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Package verification failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

# END OF FILE
