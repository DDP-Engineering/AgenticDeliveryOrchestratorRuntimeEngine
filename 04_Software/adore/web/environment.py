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
@file    environment.py
@brief   Prepare ADORE-owned shared images inside durable configuration tasks.
@details Only bundled recipes enter temporary build contexts. Short reservations
         coordinate image work; config/kernel locks never span probes or builds.
"""

from __future__ import annotations

# IMPORTS
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
import json
import os
from pathlib import Path
import shlex
from tempfile import TemporaryDirectory
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4

from adore.branding import EGRESS_PROXY_IMAGE, EXECUTOR_BASE_IMAGE
from adore.config import Config, egress_policy
from adore.config_edit import ConfigEditLockedError, config_edit_lock
from adore.doctor import inventory_runtime_argv
from adore.isolation import wsl_mount_path
from adore.util import CommandResult, CommandRunner, strict_json_loads
from adore.web.executor_settings import read_private_record, write_private_record
from adore.web.ownership import process_birth

# CONSTANTS
_ASSETS = (
    "Dockerfile.executor-base",
    "Dockerfile.egress-proxy",
    "pi/adore-guard.ts",
    "pi/adore-chatgpt.mjs",
)
_BUILD_SECONDS = 1800
_ERRORS = frozenset(
    {
        "container_runtime_unavailable",
        "executor_image_unavailable",
        "environment_identity_unavailable",
        "environment_busy",
        "environment_preparation_failed",
        "environment_build_failed",
        "environment_executor_invalid",
    }
)


class EnvironmentError(RuntimeError):
    """A value-free, localized preparation failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# HELPER FUNCTIONS
def _ok(result: CommandResult) -> bool:
    return (
        isinstance(result, CommandResult)
        and type(result.exit_code) is int
        and result.exit_code == 0
        and type(result.timed_out) is bool
        and not result.timed_out
    )


def _identity(prefix: list[str], runner: CommandRunner) -> tuple[int, int]:
    """Match the Linux runtime user for bind-mounted files, including WSL."""
    if prefix[0] == "wsl":
        values = []
        for flag in ("-u", "-g"):
            result = runner([*prefix[:-1], "id", flag], timeout=8)
            value = result.stdout.strip()
            if not _ok(result) or not value.isascii() or not value.isdigit():
                raise EnvironmentError("environment_identity_unavailable")
            values.append(int(value))
        uid, gid = values
    else:
        uid, gid = (os.getuid(), os.getgid()) if hasattr(os, "getuid") else (1000, 1000)
    if not (0 < uid < 2**31 and 0 < gid < 2**31):
        raise EnvironmentError("environment_identity_unavailable")
    return uid, gid


def _copy_assets(destination: Path) -> None:
    """Use the source checkout or the exact same recipes bundled in the wheel."""
    source = Path(__file__).resolve().parents[2] / "docker"
    packaged = files("adore").joinpath("container_assets")
    for name in _ASSETS:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            data = (source / name).read_bytes()
        elif name == "Dockerfile.egress-proxy":
            data = packaged.joinpath(name).read_bytes()
        else:
            recipe_name = "Dockerfile" if name == "Dockerfile.executor-base" else name
            data = files("adore").joinpath("_executor_recipe", recipe_name).read_bytes()
        target.write_bytes(data)


# DATA MODELS / TYPEDEFINITIONS
@dataclass
class _Job:
    id: str
    key: tuple[str, str, str]
    status: str = "running"
    stage: str = "waiting"
    error: str | None = None

    def view(self) -> dict:
        return {"id": self.id, "status": self.status, "stage": self.stage, "error": self.error}


# PUBLIC API
class EnvironmentPreparation:
    """Bounded background work shared by simultaneous imports on one server.

    Completed jobs are re-probed on the next import, so removed images are not
    mistaken for cached success. Failed builds can reuse the engine's layer cache.
    """

    def __init__(self, home: Path, runner: CommandRunner):
        self.home = home
        self.runner = runner
        self._lock = Lock()
        self._jobs: dict[str, _Job] = {}

    def start(self, config: Config) -> dict:
        proxy = (
            egress_policy(config).proxy_image
            if config.execution.backend == "container"
            and egress_policy(config).mode == "allowlist-proxy"
            else ""
        )
        runtime = config.container.runtime.strip()
        prefix = inventory_runtime_argv(runtime)
        runtime = shlex.join(prefix) if prefix else runtime
        key = (
            (runtime, config.container.image, proxy)
            if config.execution.backend == "container"
            else ("local", "", "")
        )
        with self._lock:
            for job in self._jobs.values():
                if job.key == key and job.status == "running":
                    return job.view()
            if sum(job.status == "running" for job in self._jobs.values()) >= 8:
                raise EnvironmentError("environment_busy")
            while len(self._jobs) >= 64:
                completed = next(key for key, job in self._jobs.items() if job.status != "running")
                del self._jobs[completed]
            job = _Job(uuid4().hex, key)
            self._jobs[job.id] = job
            if config.execution.backend == "local":
                job.status = job.stage = "ready"
                return job.view()
            Thread(
                target=self._run, args=(job,), daemon=True, name="adore-environment-prepare"
            ).start()
            return job.view()

    def prepare(self, config: Config) -> dict:
        """@brief Prepare a reviewed environment synchronously inside a durable control task.
        @param[in] config Exact reviewed prospective project configuration.
        @return Confirmed, value-free environment outcome; no API thread is launched.
        """
        proxy = (
            egress_policy(config).proxy_image
            if config.execution.backend == "container"
            and egress_policy(config).mode == "allowlist-proxy"
            else ""
        )
        runtime = config.container.runtime.strip()
        prefix = inventory_runtime_argv(runtime)
        runtime = shlex.join(prefix) if prefix else runtime
        job = _Job(uuid4().hex, (runtime, config.container.image, proxy))
        with self._lock:
            for old in list(self._jobs):
                if len(self._jobs) < 64:
                    break
                if self._jobs[old].status != "running":
                    del self._jobs[old]
            self._jobs[job.id] = job
        if config.execution.backend == "local":
            self._update(job, "ready")
        else:
            self._run(job)
        return job.view()

    def read(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return job.view()
        if (
            not isinstance(job_id, str)
            or len(job_id) != 32
            or any(char not in "0123456789abcdef" for char in job_id)
        ):
            return None
        try:
            raw = read_private_record(self.home / "environment" / "jobs" / (job_id + ".json"), 4096)
            if raw is None:
                return None
            value = strict_json_loads(raw.decode("utf-8"))
            if (
                not isinstance(value, dict)
                or set(value) != {"schema", "id", "status", "stage", "error"}
                or type(value["schema"]) is not int
                or value["schema"] != 1
                or value["id"] != job_id
                or value["status"] not in ("running", "ready", "failed")
                or value["stage"]
                not in (
                    "waiting",
                    "checking_runtime",
                    "checking_images",
                    "building_executor",
                    "building_proxy",
                    "verifying",
                    "ready",
                    "failed",
                )
                or value["status"] == "ready"
                and (value["stage"] != "ready" or value["error"] is not None)
                or value["status"] == "failed"
                and (value["stage"] != "failed" or value["error"] not in _ERRORS)
            ):
                raise ValueError("invalid environment evidence")
            if value["status"] == "running" and (
                value["stage"] in ("ready", "failed") or value["error"] is not None
            ):
                raise ValueError("inconsistent environment progress")
            return {key: value[key] for key in ("id", "status", "stage", "error")}
        except (OSError, ValueError, TypeError) as exc:
            raise EnvironmentError("environment_preparation_failed") from exc

    def _update(self, job: _Job, stage: str, *, error: str | None = None) -> None:
        with self._lock:
            job.stage = stage
            job.error = (
                error if error is None or error in _ERRORS else "environment_preparation_failed"
            )
            job.status = (
                "failed" if job.error is not None else "ready" if stage == "ready" else "running")
            directory = self.home / "environment" / "jobs"
            directory.mkdir(parents=True, exist_ok=True)
            write_private_record(
                directory / (job.id + ".json"), json.dumps({"schema": 1, **job.view()}).encode()
            )

    def _run(self, job: _Job) -> None:
        try:
            runtime, image, proxy = job.key
            prefix = inventory_runtime_argv(runtime)
            if prefix is None:
                raise EnvironmentError("container_runtime_unavailable")
            # A short locked reservation serializes this shared runtime's image effects.
            # The reservation is durable ownership; no kernel/config lock spans a probe/build.
            with self._reservation(runtime):
                self._prepare(job, prefix, image, proxy)
            self._update(job, "ready")
        except EnvironmentError as exc:
            self._update(job, "failed", error=exc.code)
        except Exception:
            # An unexpected worker failure must also terminate polling. Never expose
            # subprocess output or configuration through its exception message.
            self._update(job, "failed", error="environment_preparation_failed")

    @contextmanager
    def _reservation(self, runtime: str):
        """@brief Reserve shared image work with short transactions and proven process birth."""
        lock_path = self.home / "environment" / sha256(runtime.encode()).hexdigest() / "images"
        record = lock_path.parent / "reservation.json"
        token = uuid4().hex
        identity = {
            "schema": 1,
            "pid": os.getpid(),
            "birth": process_birth(os.getpid()),
            "token": token,
        }
        deadline = monotonic() + _BUILD_SECONDS
        claimed = False
        while not claimed:
            try:
                with config_edit_lock(lock_path):
                    raw = read_private_record(record, 4096)
                    previous = None if raw is None else strict_json_loads(raw.decode("utf-8"))
                    if previous is not None:
                        if (
                            not isinstance(previous, dict)
                            or set(previous) != set(identity)
                            or type(previous["schema"]) is not int
                            or previous["schema"] != 1
                            or type(previous["pid"]) is not int
                            or not isinstance(previous["birth"], str)
                            or not isinstance(previous["token"], str)
                        ):
                            raise EnvironmentError("environment_preparation_failed")
                        observed = process_birth(previous["pid"])
                        if observed is None or observed != previous["birth"]:
                            previous = None
                    if previous is None:
                        write_private_record(record, json.dumps(identity).encode())
                        claimed = True
            except ConfigEditLockedError:
                pass
            if not claimed:
                if monotonic() >= deadline:
                    raise EnvironmentError("environment_busy")
                Event().wait(0.05)
        try:
            yield
        finally:
            # Only this exact birth/token relinquishes the reservation.
            for _ in range(40):
                try:
                    with config_edit_lock(lock_path):
                        raw = read_private_record(record, 4096)
                        if raw is not None and strict_json_loads(raw.decode("utf-8")) == identity:
                            record.unlink()
                    break
                except ConfigEditLockedError:
                    Event().wait(0.025)
            else:
                raise EnvironmentError("environment_busy")

    def _prepare(self, job: _Job, prefix: list[str], image: str, proxy: str) -> None:
        self._update(job, "checking_runtime")
        if not _ok(self.runner([*prefix, "info"], timeout=15)):
            raise EnvironmentError("container_runtime_unavailable")
        for selected, managed, recipe, stage in (
            (image, EXECUTOR_BASE_IMAGE, "Dockerfile.executor-base", "building_executor"),
            (proxy, EGRESS_PROXY_IMAGE, "Dockerfile.egress-proxy", "building_proxy"),
        ):
            if not selected:
                continue
            self._update(job, "checking_images")
            if _ok(self.runner([*prefix, "image", "inspect", selected], timeout=15)):
                continue
            if selected != managed:
                raise EnvironmentError("executor_image_unavailable")
            self._update(job, stage)
            with TemporaryDirectory(prefix="adore-environment-") as directory:
                context = Path(directory).resolve()
                _copy_assets(context)
                path = wsl_mount_path(context) if prefix[0] == "wsl" else context.as_posix()
                args = [*prefix, "build", "--quiet", "--file", f"{path}/{recipe}", "--tag", managed]
                if selected == EXECUTOR_BASE_IMAGE:
                    uid, gid = _identity(prefix, self.runner)
                    args += ["--build-arg", f"USER_UID={uid}", "--build-arg", f"USER_GID={gid}"]
                result = self.runner([*args, path], timeout=_BUILD_SECONDS)
                if not _ok(result):
                    raise EnvironmentError("environment_build_failed")
            if not _ok(self.runner([*prefix, "image", "inspect", selected], timeout=15)):
                raise EnvironmentError("environment_build_failed")
        self._update(job, "verifying")
        result = self.runner(
            [
                *prefix,
                "run",
                "--rm",
                "--pull=never",
                "--network",
                "none",
                "--entrypoint",
                "python",
                image,
                "-c",
                "import pathlib,shutil; assert shutil.which('pi')"
                + (
                    "; assert pathlib.Path('/opt/adore/pi/adore-chatgpt.mjs').is_file()"
                    if image == EXECUTOR_BASE_IMAGE
                    else ""
                ),
            ],
            timeout=30,
        )
        if not _ok(result):
            raise EnvironmentError("environment_executor_invalid")


# END OF FILE
