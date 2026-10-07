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
@file    local_process.py
@brief   Native process scopes and fail-closed durable command ownership.
@details Windows Job Objects and delegated Linux cgroups are adapter details.
         Native APIs and subprocess creation are injectable for offline proof.
"""

from __future__ import annotations

# IMPORTS
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
from threading import RLock, Thread
import time
from uuid import uuid4

from adore.execution import ExecutionRecoveryError
from adore.preparation_runner import _drain
from adore.util import CommandResult, strict_json_loads

# CONSTANTS
_TOKEN = re.compile(r"[0-9a-f]{32}\Z")

# DATA MODELS / TYPEDEFINITIONS


class LocalExecutionError(ExecutionRecoveryError):
    """@brief Native execution/control evidence cannot safely authorize work."""


# LOCAL HELPERS


def atomic_record(path: Path, value: dict) -> None:
    """@brief Durably replace one parent-owned JSON control record.
    @param[in] path Authoritative record outside executor IO/worktree.
    @param[in] value Closed non-secret evidence.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_record(path: Path) -> dict:
    """@brief Read bounded strict native control JSON or fail closed.
    @param[in] path Parent-owned evidence path.
    @return Mapping with no ambiguous fields.
    @exception LocalExecutionError Missing/corrupt/link evidence.
    """
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            raise ValueError
        value = strict_json_loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (OSError, ValueError, TypeError) as exc:
        raise LocalExecutionError("native control evidence missing or corrupt") from exc


class WindowsJobs:
    """@brief Small Win32 Job/PID-birth API boundary; never issues a PID-only kill."""

    def __init__(self) -> None:
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "OpenJobObjectW": ([wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
                wintypes.BOOL,
            ),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "QueryInformationJobObject": (
                [
                    wintypes.HANDLE,
                    ctypes.c_int,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD),
                ],
                wintypes.BOOL,
            ),
            "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "GetProcessTimes": (
                [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4,
                wintypes.BOOL,
            ),
            "GetExitCodeProcess": (
                [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)],
                wintypes.BOOL,
            ),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = arguments, result
        self.handles: dict[str, int] = {}

    def create(self, name: str) -> None:
        """@brief Create a unique non-breakaway kill-on-close Job.
        @param[in] name Owned native Job name.
        """

        class Limits(ctypes.Structure):
            """@brief Native JOBOBJECT_BASIC_LIMIT_INFORMATION layout."""

            _fields_ = [
                ("process_time", ctypes.c_longlong),
                ("job_time", ctypes.c_longlong),
                ("flags", wintypes.DWORD),
                ("min_working", ctypes.c_size_t),
                ("max_working", ctypes.c_size_t),
                ("active", wintypes.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD),
            ]

        class Extended(ctypes.Structure):
            """@brief Native JOBOBJECT_EXTENDED_LIMIT_INFORMATION layout."""

            _fields_ = [
                ("basic", Limits),
                ("io", ctypes.c_ulonglong * 6),
                ("memory", ctypes.c_size_t * 4),
            ]

        ctypes.set_last_error(0)
        handle = self.api.CreateJobObjectW(None, name)
        if not handle:
            raise LocalExecutionError("cannot create native Job")
        if ctypes.get_last_error() == 183:
            self.api.CloseHandle(handle)
            raise LocalExecutionError("native Job identity already exists")
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, no breakaway.
        if not self.api.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            self.api.CloseHandle(handle)
            raise LocalExecutionError("cannot establish native Job ownership")
        self.handles[name] = handle

    def attach(self, name: str, pid: int) -> None:
        """@brief Assign the trusted waiting supervisor before release.
        @param[in] name Owned native Job name.
        @param[in] pid Native supervisor PID; birth is checked separately.
        """
        process = self.api.OpenProcess(0x0100 | 0x0001, False, pid)
        if not process:
            raise LocalExecutionError("cannot open owned supervisor")
        try:
            if not self.api.AssignProcessToJobObject(self.handles[name], process):
                raise LocalExecutionError("cannot assign owned supervisor to Job")
        finally:
            self.api.CloseHandle(process)

    def birth(self, pid: int) -> str | None:
        """@brief Query immutable native creation time, distinguishing absence/errors.
        @param[in] pid Native supervisor PID; birth is checked separately.
        @return Verified native operation result.
        """
        handle = self.api.OpenProcess(0x1000, False, pid)
        if not handle:
            if ctypes.get_last_error() in {87, 1168}:
                return None
            raise LocalExecutionError("native PID identity cannot be inspected")
        try:
            status = wintypes.DWORD()
            if not self.api.GetExitCodeProcess(handle, ctypes.byref(status)):
                raise LocalExecutionError("native PID liveness unavailable")
            if status.value != 259:  # STILL_ACTIVE
                return None
            stamps = [wintypes.FILETIME() for _ in range(4)]
            if not self.api.GetProcessTimes(handle, *(ctypes.byref(stamp) for stamp in stamps)):
                raise LocalExecutionError("native PID birth unavailable")
            return str((stamps[0].dwHighDateTime << 32) | stamps[0].dwLowDateTime)
        finally:
            self.api.CloseHandle(handle)

    def kill(self, name: str) -> None:
        """@brief Terminate only a verified random Job; absence is idempotent.
        @param[in] name Owned native Job name.
        """
        handle = self.handles.get(name) or self.api.OpenJobObjectW(0x0008, False, name)
        if not handle:
            if ctypes.get_last_error() == 2:
                return
            raise LocalExecutionError("native Job control unavailable")
        try:
            if not self.api.TerminateJobObject(handle, 124):
                raise LocalExecutionError("native Job termination failed")
        finally:
            if name not in self.handles:
                self.api.CloseHandle(handle)

    def remove(self, name: str) -> None:
        """@brief Confirm all owned descendants exited before releasing the Job.
        @param[in] name Owned native Job name.
        """
        handle = self.handles.get(name) or self.api.OpenJobObjectW(0x0004, False, name)
        if not handle:
            if ctypes.get_last_error() == 2:
                return
            raise LocalExecutionError("native Job drain unavailable")

        class Accounting(ctypes.Structure):
            """@brief JOBOBJECT_BASIC_ACCOUNTING_INFORMATION layout."""

            _fields_ = [
                ("times", ctypes.c_longlong * 4),
                ("faults", wintypes.DWORD),
                ("total", wintypes.DWORD),
                ("active", wintypes.DWORD),
                ("terminated", wintypes.DWORD),
            ]

        try:
            deadline = time.monotonic() + 5
            while True:
                info = Accounting()
                if not self.api.QueryInformationJobObject(
                    handle, 1, ctypes.byref(info), ctypes.sizeof(info), None
                ):
                    raise LocalExecutionError("native Job drain cannot be confirmed")
                if info.active == 0:
                    break
                if time.monotonic() >= deadline:
                    raise LocalExecutionError("native Job still contains owned processes")
                time.sleep(0.05)
        except LocalExecutionError:
            if name not in self.handles:
                self.api.CloseHandle(handle)
            raise
        if not self.api.CloseHandle(handle):
            raise LocalExecutionError("native Job handle release failed")
        self.handles.pop(name, None)


# PUBLIC API


def _windows_account_identity() -> tuple[str, str]:
    """@brief Read token account SID and qualified name, refusing username-only ownership."""
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise LocalExecutionError("native account token unavailable")
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise LocalExecutionError("native account token size invalid")
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise LocalExecutionError("native account SID unavailable")
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise LocalExecutionError("native account SID invalid")
        try:
            identity = text.value
            if not identity or not identity.startswith("S-"):
                raise LocalExecutionError("native account SID invalid")
        finally:
            kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))
        name = ctypes.create_unicode_buffer(256)
        size = wintypes.DWORD(256)
        if not ctypes.windll.secur32.GetUserNameExW(2, name, ctypes.byref(size)):
            raise LocalExecutionError("qualified native account unavailable")
        return name.value, identity
    finally:
        kernel.CloseHandle(token)


def native_context() -> dict[str, str]:
    """@brief Identify the actual machine/account, never environment USER spoofing.
    @return Native system/account/host fingerprint and effective home/PATH defaults.
    @exception LocalExecutionError Unsupported or unidentified host.
    """
    system = platform.system()
    try:
        if system == "Windows":
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
            ) as key:
                machine = winreg.QueryValueEx(key, "MachineGuid")[0]
            account, account_id = _windows_account_identity()
            home = str(Path.home())
        elif system == "Linux":
            import pwd

            user = pwd.getpwuid(os.geteuid())
            account, home = user.pw_name, user.pw_dir
            account_id = str(user.pw_uid)
            machine = Path("/etc/machine-id").read_text(encoding="ascii").strip()
        else:
            raise LocalExecutionError("local execution supports native Windows/Linux only")
        if not isinstance(machine, str) or not machine or not account:
            raise ValueError
        identity = hashlib.sha256(
            f"{system}\0{machine}\0{socket.gethostname()}\0{account_id}".encode()
        ).hexdigest()
        return {
            "system": system,
            "account": account,
            "host": identity,
            "machine": socket.gethostname(),
            "home": home,
            "path": os.environ.get("PATH", ""),
        }
    except (OSError, ValueError, KeyError) as exc:
        raise LocalExecutionError("native machine/account identity unavailable") from exc


class NativeScopes:
    """@brief Injectable native scope API and PID-birth authority."""

    def __init__(
        self,
        system: str,
        cgroup_root: str = "",
        *,
        windows=None,
        linux_base: Path = Path("/sys/fs/cgroup"),
        birth_reader=None,
    ) -> None:
        self.system, self.root = system, Path(cgroup_root) if cgroup_root else None
        self.windows = windows
        self.linux_base, self.birth_reader = linux_base, birth_reader
        if system == "Windows":
            self.windows = windows or WindowsJobs()
        elif system == "Linux":
            if (
                self.root is None
                or not self.root.is_absolute()
                or self.root.is_symlink()
                or not self.root.resolve().is_relative_to(linux_base.resolve())
                or not (self.root / "cgroup.controllers").is_file()
            ):
                raise LocalExecutionError("local Linux needs a delegated cgroup-v2 root")
        else:
            raise LocalExecutionError("unsupported local process platform")

    def create(self, token: str) -> dict:
        """@brief Create a uniquely owned Job or delegated cgroup leaf.
        @param[in] token Random scope UUID.
        @return Verified native operation result.
        """
        if not _TOKEN.fullmatch(token):
            raise LocalExecutionError("invalid native scope token")
        if self.system == "Windows":
            name = "Local\\ADORE-" + token
            self.windows.create(name)
            return {"kind": "windows-job", "name": name}
        directory = self.root / ("adore-" + token)
        try:
            directory.mkdir()
            if not (directory / "cgroup.kill").is_file():
                directory.rmdir()
                raise LocalExecutionError("local Linux scope lacks cgroup.kill")
            details = directory.stat()
            return {
                "kind": "linux-cgroup",
                "path": str(directory),
                "device": details.st_dev,
                "inode": details.st_ino,
            }
        except OSError as exc:
            raise LocalExecutionError("cannot provision delegated native scope") from exc

    def validate(self, scope: object) -> None:
        """@brief Validate closed scope identity before any external control.
        @param[in] scope Closed owned Job/cgroup identity.
        """
        if not isinstance(scope, dict):
            raise LocalExecutionError("invalid native scope")
        if self.system == "Windows":
            if (
                set(scope) != {"kind", "name"}
                or scope["kind"] != "windows-job"
                or not isinstance(scope["name"], str)
                or not re.fullmatch(r"Local\\ADORE-[0-9a-f]{32}", scope["name"])
            ):
                raise LocalExecutionError("invalid native Job identity")
            return
        if (
            set(scope) != {"kind", "path", "device", "inode"}
            or scope["kind"] != "linux-cgroup"
            or not isinstance(scope["path"], str)
            or type(scope["device"]) is not int
            or type(scope["inode"]) is not int
        ):
            raise LocalExecutionError("invalid native cgroup identity")
        directory = Path(scope["path"])
        if (
            directory.parent != self.root
            or not re.fullmatch(r"adore-[0-9a-f]{32}", directory.name)
            or directory.is_symlink()
        ):
            raise LocalExecutionError("native cgroup ownership differs")
        if directory.exists():
            details = directory.stat()
            if details.st_dev != scope["device"] or details.st_ino != scope["inode"]:
                raise LocalExecutionError("native cgroup was replaced")

    def attach(self, scope: dict, pid: int) -> None:
        """@brief Attach trusted Windows supervisor; Linux child joins before exec.
        @param[in] scope Closed owned Job/cgroup identity.
        @param[in] pid Native supervisor PID; birth is checked separately.
        """
        self.validate(scope)
        if self.system == "Windows":
            self.windows.attach(scope["name"], pid)

    def birth(self, pid: int) -> str | None:
        """@brief Read native creation identity rather than trusting a persisted PID.
        @param[in] pid Native supervisor PID; birth is checked separately.
        @return Verified native operation result.
        """
        if self.birth_reader is not None:
            return self.birth_reader(pid)
        if self.system == "Windows":
            return self.windows.birth(pid)
        try:
            text = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
            ticks = text[text.rindex(")") + 2 :].split()[19]
            boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
            if not ticks.isdigit():
                raise ValueError
            return boot + ":" + ticks
        except FileNotFoundError:
            return None
        except (OSError, ValueError, IndexError) as exc:
            raise LocalExecutionError("native PID birth cannot be inspected") from exc

    def kill(self, scope: dict) -> None:
        """@brief Kill the complete verified scope, including detached descendants.
        @param[in] scope Closed owned Job/cgroup identity.
        """
        self.validate(scope)
        try:
            if self.system == "Windows":
                self.windows.kill(scope["name"])
            elif Path(scope["path"]).exists():
                (Path(scope["path"]) / "cgroup.kill").write_text("1", encoding="ascii")
        except OSError as exc:
            raise LocalExecutionError("native scope termination failed") from exc

    def remove(self, scope: dict) -> None:
        """@brief Release only an empty owned native scope; no recursive deletion.
        @param[in] scope Closed owned Job/cgroup identity.
        """
        self.validate(scope)
        try:
            if self.system == "Windows":
                self.windows.remove(scope["name"])
            elif Path(scope["path"]).exists():
                deadline = time.monotonic() + 5
                while True:
                    lines = (Path(scope["path"]) / "cgroup.events").read_text().splitlines()
                    populated = [line.split() for line in lines if line.startswith("populated")]
                    if (
                        len(populated) != 1
                        or len(populated[0]) != 2
                        or populated[0][1] not in {"0", "1"}
                    ):
                        raise LocalExecutionError("native cgroup liveness evidence corrupt")
                    if populated[0][1] == "0":
                        break
                    if time.monotonic() >= deadline:
                        raise LocalExecutionError("native cgroup still contains owned processes")
                    time.sleep(0.05)
                Path(scope["path"]).rmdir()
        except OSError as exc:
            raise LocalExecutionError("native scope cleanup not confirmed") from exc


class LocalProcessController:
    """@brief Bounded native process launch and durable run-owned control boundary."""

    def __init__(self, scopes: NativeScopes, *, spawn=subprocess.Popen) -> None:
        self.scopes, self.spawn = scopes, spawn
        self.lock = RLock()

    def interrupt(self, control: Path, run_id: str, host: str) -> None:
        """@brief Control verified persisted ownership; reused PID never authorizes kill.
        @param[in] control Parent-owned authoritative control directory.
        @param[in] run_id Pinned local run UUID.
        @param[in] host Pinned machine/account fingerprint.
        @exception LocalExecutionError Corrupt identity or failed process control.
        """
        with self.lock:
            path = control / "active-process.json"
            if not path.exists():
                return
            lease = read_record(path)
            if (
                set(lease) != {"schema", "run_id", "host", "pid", "birth", "scope"}
                or type(lease["schema"]) is not int
                or lease["schema"] != 1
                or lease["run_id"] != run_id
                or lease["host"] != host
                or type(lease["pid"]) is not int
                or lease["pid"] <= 0
                or not isinstance(lease["birth"], str)
                or not lease["birth"]
            ):
                raise LocalExecutionError("native process lease identity is corrupt")
            self.scopes.validate(lease["scope"])
            scope = lease["scope"]
            token = (
                scope["name"].rsplit("-", 1)[1]
                if self.scopes.system == "Windows"
                else Path(scope["path"]).name.removeprefix("adore-")
            )
            if read_record(control / "launches" / token / "ownership.json") != lease:
                raise LocalExecutionError("native scope differs from immutable launch ownership")
            observed = self.scopes.birth(lease["pid"])
            if observed is not None and observed != lease["birth"]:
                raise LocalExecutionError("native PID was reused; process control refused")
            self.scopes.kill(lease["scope"])

    def recover(self, control: Path, run_id: str, host: str) -> None:
        """@brief Reconcile a verified stopped lease before retry/cleanup.
        @param[in] control Authoritative control directory.
        @param[in] run_id Pinned local run UUID.
        @param[in] host Pinned native account/machine.
        @exception LocalExecutionError Ownership/control/drain is unconfirmed.
        """
        with self.lock:
            path = control / "active-process.json"
            if not path.exists():
                return
            self.interrupt(control, run_id, host)
            lease = read_record(path)
            deadline = time.monotonic() + 5
            while self.scopes.birth(lease["pid"]) is not None:
                if time.monotonic() >= deadline:
                    raise LocalExecutionError("native process recovery drain not confirmed")
                time.sleep(0.05)
            self.scopes.remove(lease["scope"])
            path.unlink()

    def run_files(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout: float,
        stdout: Path,
        stderr: Path,
        control: Path,
        run_id: str,
        host: str,
        secrets: list[str],
        stdout_limit: int = 65536,
    ) -> CommandResult:
        """@brief Persist scope/PID ownership before releasing one bounded native command.
        @param[in] argv Resolved native argv; no shell interpretation.
        @param[in] cwd Dedicated native worktree or explicit probe directory.
        @param[in] env Controlled service-account environment.
        @param[in] timeout Positive wall-clock bound.
        @param[in] stdout Bounded redacted output file.
        @param[in] stderr Bounded redacted error file.
        @param[in] control Authoritative parent-owned control directory.
        @param[in] run_id Pinned local run UUID.
        @param[in] host Pinned machine/account identity.
        @param[in] secrets Approved known values for redaction, never written to controls.
        @param[in] stdout_limit Native stdout bound; AEGIS JSON uses its existing limit.
        @return Actual command exit and authoritative timeout outcome.
        @exception LocalExecutionError Ownership, launch or cleanup cannot be confirmed.
        """
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
            raise LocalExecutionError("native command requires a positive timeout")
        if type(stdout_limit) is not int or not 1 <= stdout_limit <= 4 * 1024 * 1024:
            raise LocalExecutionError("native stdout limit is invalid")
        token = uuid4().hex
        with self.lock:
            if (control / "active-process.json").exists():
                raise LocalExecutionError("native command lease needs explicit recovery")
            scope = self.scopes.create(token)
            launch = control / "launches" / token
            envelope = launch / "command.json"
            release = launch / "release"
            process = None
            try:
                launch.mkdir(parents=True, exist_ok=False)
                atomic_record(
                    envelope,
                    {"argv": argv, "cwd": str(cwd), "scope": scope, "release": str(release)},
                )
                process = self.spawn(
                    [
                        sys.executable,
                        "-I",
                        str(Path(__file__).with_name("local_child.py")),
                        str(envelope),
                    ],
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                )
                self.scopes.attach(scope, process.pid)
                birth = self.scopes.birth(process.pid)
                if birth is None:
                    raise LocalExecutionError("owned native supervisor exited before release")
                lease = {
                    "schema": 1,
                    "run_id": run_id,
                    "host": host,
                    "pid": process.pid,
                    "birth": birth,
                    "scope": scope,
                }
                atomic_record(launch / "ownership.json", lease)
                atomic_record(control / "active-process.json", lease)
                release.write_text("released", encoding="ascii")
            except (OSError, ValueError, LocalExecutionError) as exc:
                if launch.is_dir():
                    (launch / "cancel").write_text("cancelled", encoding="ascii")
                self.scopes.kill(scope)
                if process is not None:
                    # Only the handle just returned by spawn; no recovered PID control.
                    if self.scopes.system == "Windows":
                        process.kill()  # Fresh native HANDLE, never recovered PID.
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired as drain_error:
                        raise LocalExecutionError(
                            "native launch drain unconfirmed"
                        ) from drain_error
                self.scopes.remove(scope)
                raise LocalExecutionError("native launch ownership failed") from exc
        errors = []

        def drain(stream, path):
            """@brief Capture stream failure instead of accepting a dead drain thread.
            @param[in] stream Child byte output stream.
            @param[in] path Owned bounded output file.
            """
            try:
                _drain(
                    stream,
                    path,
                    secrets,
                    max_bytes=stdout_limit if path == stdout else 65536,
                    strict_utf8=True,
                )
            except (OSError, ValueError) as exc:
                errors.append(exc)

        threads = [
            Thread(target=drain, args=(stream, path), daemon=True)
            for stream, path in ((process.stdout, stdout), (process.stderr, stderr))
        ]
        for thread in threads:
            thread.start()
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self.interrupt(control, run_id, host)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise LocalExecutionError("native timeout drain unconfirmed") from exc
            code = 124
        finally:
            self.interrupt(control, run_id, host)  # Drain descendants after normal exit too.
            for thread in threads:
                thread.join(timeout=5)
            if any(thread.is_alive() for thread in threads):
                raise LocalExecutionError("native output drain did not finish")
            if errors:
                raise LocalExecutionError("native output capture failed") from errors[0]
            self.scopes.remove(scope)
            with self.lock:
                (control / "active-process.json").unlink(missing_ok=True)
        return CommandResult(
            argv=[argv[0], "[native-file-launch]"], exit_code=code, timed_out=timed_out
        )


# END OF FILE
