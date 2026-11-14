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
@file       launch.py
@brief      Run an extracted ADORE distribution without host Python or setup.
@details    Verifies delivery media, owns one API/worker pair per user home,
            opens a ready UI, and supports bounded, graceful shutdown.
"""

from __future__ import annotations

# IMPORTS
import argparse
import errno
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import socket
import subprocess
import sys
from threading import Event, Thread
import time
import urllib.error
import urllib.request
from uuid import uuid4
import webbrowser

# CONSTANTS
BUNDLE = Path(__file__).resolve().parent
LOG = logging.getLogger("adore.launcher")


# DATA MODELS / TYPEDEFINITIONS
class DeliveryError(RuntimeError):
    """@brief Report corrupt media or unavailable ownership without guessing."""


# PUBLIC API
def verify(bundle: Path = BUNDLE) -> dict:
    """@brief Verify exact host compatibility and every packaged file's digest.
    @param[in] bundle Extracted delivery directory.
    @return Validated manifest.
    @exception DeliveryError A file, manifest or host fails the delivery contract.
    """
    try:
        manifest_path = bundle / "manifest.json"
        if manifest_path.stat().st_size > 4 * 1024 * 1024:
            raise DeliveryError("package manifest is too large")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (not isinstance(manifest, dict) or type(manifest.get("schema")) is not int
                or manifest["schema"] != 1
                or manifest.get("system") != platform.system().lower()
                or manifest.get("architecture") != "x64"
                or platform.machine().lower() not in {"amd64", "x86_64"}
                or manifest.get("python_version") != platform.python_version()
                or not isinstance(manifest.get("version"), str)):
            raise DeliveryError("package manifest does not match this OS, architecture or Python")
        files = manifest.get("files")
        if not isinstance(files, dict) or not 1 <= len(files) <= 30000:
            raise DeliveryError("invalid package file inventory")
        actual, pending, total = {}, [bundle], 0
        # DirEntry caches Windows reparse/type metadata from directory listing.
        # Avoid reopening every parent/file merely to test its type.
        while pending:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    if entry.is_symlink() or (hasattr(entry, "is_junction")
                                              and entry.is_junction()):
                        raise DeliveryError("package contains a link: " + entry.path)
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(path)
                    elif entry.is_file(follow_symlinks=False) and path != manifest_path:
                        total += entry.stat(follow_symlinks=False).st_size
                        if total > 1024 * 1024 * 1024 or len(actual) >= 30000:
                            raise DeliveryError("package exceeds its file/size limit")
                        actual[path.relative_to(bundle).as_posix()] = path
                    elif path != manifest_path:
                        raise DeliveryError("package contains a non-regular file")
        for relative, digest in files.items():
            if (not isinstance(relative, str) or not relative or "\\" in relative
                    or ":" in relative or PurePosixPath(relative).is_absolute()
                    or any(part in {"", ".", ".."} for part in relative.split("/"))
                    or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
                raise DeliveryError("invalid package file path or checksum")
            if relative not in actual:
                raise DeliveryError("package file is missing: " + relative)
            checksum = hashlib.sha256()
            with actual[relative].open("rb") as payload:
                for chunk in iter(lambda: payload.read(1024 * 1024), b""):
                    checksum.update(chunk)
            if checksum.hexdigest() != digest:
                raise DeliveryError(f"package file changed: {relative}")
        if set(actual) != set(files):
            raise DeliveryError("package contains missing or unlisted files")
        return manifest
    except (OSError, ValueError, TypeError) as error:
        raise DeliveryError(f"cannot verify package: {error}") from error


# LOCAL HELPERS
def _atomic_json(path: Path, data: dict) -> None:
    """@brief Replace one complete owner/stop record on the same filesystem."""
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _record(path: Path, home: Path) -> dict:
    """@brief Validate a live owner's record before opening or stopping it."""
    try:
        if path.stat().st_size > 8192:
            raise DeliveryError("launcher record is too large")
        item = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(item, dict) or set(item) != {"schema", "home", "port", "token"}
                or item["schema"] != 1 or item["home"] != str(home)
                or type(item["port"]) is not int or not 1 <= item["port"] <= 65535
                or not isinstance(item["token"], str)
                or not re.fullmatch(r"[a-f0-9]{32}", item["token"])):
            raise DeliveryError("invalid live launcher record")
        return item
    except (OSError, ValueError) as error:
        raise DeliveryError(f"cannot read live launcher record: {error}") from error


def _lock(handle) -> bool:
    """@brief Acquire a nonblocking process-lifetime lock on both hosts."""
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as error:
        if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
            raise DeliveryError(f"cannot acquire launcher ownership: {error}") from error
        return False


def _ready(port: int) -> bool:
    """@brief Require bounded, non-proxied local worker-readiness JSON."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        """@brief Keep readiness probes strictly on the requested loopback URL."""

        def redirect_request(self, *_args, **_kwargs):
            return None

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(f"http://127.0.0.1:{port}/api/v1/ready", timeout=1) as response:
            readiness = json.loads(response.read(8192))
            return (response.status == 200 and isinstance(readiness, dict)
                    and readiness.get("status") == "ready" and readiness.get("worker") == "ready")
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _open_ui(port: int, disabled: bool) -> None:
    """@brief Always display the URL; open a browser only on a desktop."""
    url = f"http://127.0.0.1:{port}/"
    print(f"ADORE is ready: {url}", flush=True)
    desktop = os.name == "nt" or any(os.environ.get(key)
                                    for key in ("DISPLAY", "WAYLAND_DISPLAY", "BROWSER"))
    if not disabled and desktop:
        try:
            webbrowser.open(url, new=2)
        except (OSError, webbrowser.Error):
            LOG.warning("Could not open the browser; use %s", url)


def _child_logs(process, role: str) -> None:
    """@brief Drain service output into bounded rotating launcher logs."""
    try:
        for line in iter(lambda: process.stdout.readline(65536), ""):
            LOG.info("%s: %s", role, line.rstrip())
    finally:
        process.stdout.close()


def _stop(children: list, service_stop: Path) -> None:
    """@brief Signal both owned service groups, then apply a finite kill timeout."""
    deadline = time.monotonic() + 15
    service_stop.touch()
    grace = time.monotonic() + 3
    while any(process.poll() is None for process in children) and time.monotonic() < grace:
        time.sleep(0.1)
    for process in children:
        if process.poll() is None:
            try:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
            except (OSError, ValueError):
                process.terminate()
    for process in children:
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=5)


def _service(role: str, home: Path, port: int, service_stop: Path) -> int:
    """@brief Adapt native stop signals to existing API/worker shutdown hooks."""
    from adore.web.processes import assert_ancestry

    stop, done = Event(), Event()

    def watch_stop() -> None:
        """@brief Deliver the owner's stop request even without a Windows console."""
        while not done.wait(0.1):
            try:
                assert_ancestry()
                parent_lost = False
            except RuntimeError:
                parent_lost = True
            if parent_lost or service_stop.exists():
                stop.set()
                return

    watcher = Thread(target=watch_stop, daemon=True)
    watcher.start()
    if role == "worker":
        from adore.profiles import ProfileStore
        from adore.web.supervisor import Supervisor
        from adore.web.store import WebStore
        for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), lambda *_: stop.set())
        profiles = ProfileStore(home)
        try:
            Supervisor(profiles, WebStore(home / "web.db")).run_forever(stop=stop)
        finally:
            done.set()
    else:
        from adore.web.app import create_app
        import uvicorn
        server = uvicorn.Server(uvicorn.Config(create_app(home), host="127.0.0.1", port=port,
                                               proxy_headers=False))

        def request_exit() -> None:
            """@brief Translate the portable stop event into Uvicorn's exit hook."""
            while not done.wait(0.1):
                if stop.is_set():
                    server.should_exit = True
                    return

        Thread(target=request_exit, daemon=True).start()
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, lambda *_: setattr(server, "should_exit", True))
        try:
            server.run()
        finally:
            done.set()
    return 0


def main(argv: list[str] | None = None) -> int:
    """@brief Verify, start, reopen or stop one portable ADORE installation.
    @param[in] argv Optional command arguments.
    @return Zero after verification, reopening, stop request or graceful shutdown.
    @exception DeliveryError Media, ownership or bounded service startup fails.
    """
    parser = argparse.ArgumentParser(description="ADORE — start the web interface and worker")
    parser.add_argument("--home", type=Path, help="override the normal user data directory")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--verify", action="store_true", help="verify the package without starting")
    parser.add_argument("--stop", action="store_true", help="stop this user's running ADORE pair")
    parser.add_argument("--startup-timeout", type=float, default=45)
    parser.add_argument("--restart-limit", type=int, default=3)
    parser.add_argument("--service", choices=("api", "worker"), help=argparse.SUPPRESS)
    parser.add_argument("--service-stop", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or not 1 <= args.startup_timeout <= 120:
        parser.error("port must be 1..65535 and startup timeout 1..120 seconds")
    if not 0 <= args.restart_limit <= 10:
        parser.error("restart limit must be 0..10")
    if args.service:
        if (args.home is None or args.service_stop is None
                or args.service_stop.resolve().parent != args.home.resolve()
                or not re.fullmatch(r"\.launcher-services-[a-f0-9]{32}\.stop",
                                    args.service_stop.name)):
            parser.error("internal service requires an explicit home and owned stop path")
        return _service(args.service, args.home.resolve(), args.port, args.service_stop)
    manifest = verify()
    if args.verify:
        import ssl  # noqa: F401

        from adore import __version__
        import argon2  # noqa: F401 - native dependency smoke
        import fastapi  # noqa: F401
        import tzdata  # noqa: F401
        import uvicorn  # noqa: F401
        if __version__ != manifest["version"]:
            raise DeliveryError("installed application version differs from the manifest")
        print(f"ADORE {__version__}: package, Python and web dependencies verified", flush=True)
        return 0
    from adore.profiles import adore_home
    home = (args.home or adore_home()).resolve()
    if home.is_relative_to(BUNDLE):
        raise DeliveryError("user data must be outside the extracted application directory")
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    record_path, stop_path = home / ".launcher.json", home / ".launcher-stop.json"
    with (home / ".launcher.lock").open("a+b") as ownership:
        if ownership.tell() == 0:
            ownership.write(b"\0")
            ownership.flush()
        if not _lock(ownership):
            deadline = time.monotonic() + args.startup_timeout
            while time.monotonic() < deadline:
                try:
                    record = _record(record_path, home)
                    break
                except DeliveryError:
                    time.sleep(0.1)
            else:
                raise DeliveryError("running launcher has no valid ownership record")
            if args.stop:
                _atomic_json(stop_path, {"token": record["token"]})
                print("Stop requested for the running ADORE instance", flush=True)
                return 0
            while time.monotonic() < deadline:
                if _ready(record["port"]):
                    print("ADORE is already running; reusing the existing instance", flush=True)
                    _open_ui(record["port"], args.no_browser)
                    return 0
                time.sleep(0.2)
            raise DeliveryError("existing ADORE instance is not ready; inspect its launcher log")
        if args.stop:
            print("ADORE is not running", flush=True)
            return 0
        log_dir = home / "logs"
        log_dir.mkdir(exist_ok=True)
        LOG.setLevel(logging.INFO)
        handler = RotatingFileHandler(log_dir / "launcher.log", maxBytes=2 * 1024 * 1024,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOG.addHandler(handler)
        print(f"ADORE data: {home}\nLogs: {log_dir / 'launcher.log'}", flush=True)
        with socket.socket() as probe:
            if os.name == "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(("127.0.0.1", args.port))
            except OSError as error:
                raise DeliveryError(
                    f"port {args.port} is in use; choose --port or stop its owner"
                ) from error
        token = uuid4().hex
        _atomic_json(record_path, {"schema": 1, "home": str(home),
                                   "port": args.port, "token": token})
        service_stop = home / f".launcher-services-{token}.stop"
        stop = Event()
        for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), lambda *_: stop.set())
        env = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
            env.pop(key, None)
        env.update(ADORE_HOME=str(home), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
        try:
            for attempt in range(args.restart_limit + 1):
                service_stop.unlink(missing_ok=True)
                children, readers = [], []
                try:
                    from adore.web.processes import child_environment

                    for role in ("api", "worker"):
                        command = [sys.executable, "-I", "-B", str(BUNDLE / "launch.py"),
                                   "--service", role, "--home", str(home), "--port", str(args.port),
                                   "--service-stop", str(service_stop)]
                        options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                                   if os.name == "nt" else {"start_new_session": True})
                        child = subprocess.Popen(command, cwd=home, env=child_environment(env),
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.STDOUT, text=True,
                                                 encoding="utf-8", errors="replace", **options)
                        children.append(child)
                        reader = Thread(target=_child_logs, args=(child, role), daemon=True)
                        reader.start()
                        readers.append(reader)
                    deadline = time.monotonic() + args.startup_timeout
                    ready = False
                    while not stop.wait(0.2):
                        if stop_path.exists():
                            if stop_path.stat().st_size > 8192:
                                raise DeliveryError("launcher stop record is too large")
                            request = json.loads(stop_path.read_text(encoding="utf-8"))
                            if (not isinstance(request, dict) or set(request) != {"token"}
                                    or not isinstance(request["token"], str)
                                    or not re.fullmatch(r"[a-f0-9]{32}", request["token"])):
                                raise DeliveryError("invalid launcher stop record")
                            if request == {"token": token}:
                                stop.set()
                                break
                        if any(child.poll() is not None for child in children):
                            break
                        if not ready and _ready(args.port):
                            ready = True
                            _open_ui(args.port, args.no_browser)
                        if not ready and time.monotonic() >= deadline:
                            LOG.error("API/worker startup timed out")
                            break
                finally:
                    _stop(children, service_stop)
                    for reader in readers:
                        reader.join(timeout=2)
                if stop.is_set():
                    print("ADORE stopped", flush=True)
                    return 0
                if attempt < args.restart_limit:
                    LOG.warning("Service pair failed; bounded restart %s", attempt + 1)
                    if stop.wait(min(2 ** attempt, 8)):
                        return 0
            raise DeliveryError("ADORE could not stay running; see "
                                + str(log_dir / "launcher.log"))
        finally:
            record_path.unlink(missing_ok=True)
            stop_path.unlink(missing_ok=True)
            service_stop.unlink(missing_ok=True)
            LOG.removeHandler(handler)
            handler.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DeliveryError, OSError, ValueError) as error:
        print(f"ADORE startup failed: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error

# END OF FILE
