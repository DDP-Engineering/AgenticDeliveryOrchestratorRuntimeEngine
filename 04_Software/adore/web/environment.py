#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
"""Prepare shared, ADORE-owned container images for reviewed web imports.

Only bundled recipes enter the build context. No repository, credential folder,
project recipe, host shell or caller-supplied build argument is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
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
from adore.util import CommandResult, CommandRunner

_ASSETS = ("Dockerfile.executor-base", "Dockerfile.egress-proxy",
           "pi/adore-guard.ts", "pi/adore-chatgpt.mjs")
_BUILD_SECONDS = 1800


class EnvironmentError(RuntimeError):
    """A value-free, localized preparation failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _ok(result: CommandResult) -> bool:
    return (isinstance(result, CommandResult) and type(result.exit_code) is int
            and result.exit_code == 0 and type(result.timed_out) is bool
            and not result.timed_out)


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


@dataclass
class _Job:
    id: str
    key: tuple[str, str, str]
    status: str = "running"
    stage: str = "waiting"
    error: str | None = None

    def view(self) -> dict:
        return {"id": self.id, "status": self.status, "stage": self.stage, "error": self.error}


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
        proxy = (egress_policy(config).proxy_image if config.execution.backend == "container"
                 and egress_policy(config).mode == "allowlist-proxy" else "")
        runtime = config.container.runtime.strip()
        prefix = inventory_runtime_argv(runtime)
        runtime = shlex.join(prefix) if prefix else runtime
        key = ((runtime, config.container.image, proxy)
               if config.execution.backend == "container" else ("local", "", ""))
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
            Thread(target=self._run, args=(job,), daemon=True,
                   name="adore-environment-prepare").start()
            return job.view()

    def read(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.view() if job else None

    def _update(self, job: _Job, stage: str, *, error: str | None = None) -> None:
        with self._lock:
            job.stage = stage
            job.error = error
            job.status = "failed" if error else "ready" if stage == "ready" else "running"

    def _run(self, job: _Job) -> None:
        try:
            runtime, image, proxy = job.key
            prefix = inventory_runtime_argv(runtime)
            if prefix is None:
                raise EnvironmentError("container_runtime_unavailable")
            # Serialize builds across web processes as well as simultaneous requests.
            lock_path = self.home / "environment" / sha256(runtime.encode()).hexdigest() / "images"
            deadline = monotonic() + _BUILD_SECONDS
            while True:
                try:
                    with config_edit_lock(lock_path):
                        self._prepare(job, prefix, image, proxy)
                    break
                except ConfigEditLockedError:
                    if monotonic() >= deadline:
                        raise EnvironmentError("environment_busy") from None
                    Event().wait(0.5)
            self._update(job, "ready")
        except EnvironmentError as exc:
            self._update(job, "failed", error=exc.code)
        except Exception:
            # An unexpected worker failure must also terminate polling. Never expose
            # subprocess output or configuration through its exception message.
            self._update(job, "failed", error="environment_preparation_failed")

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
                args = [*prefix, "build", "--quiet", "--file", f"{path}/{recipe}",
                        "--tag", managed]
                if selected == EXECUTOR_BASE_IMAGE:
                    uid, gid = _identity(prefix, self.runner)
                    args += ["--build-arg", f"USER_UID={uid}", "--build-arg", f"USER_GID={gid}"]
                result = self.runner([*args, path], timeout=_BUILD_SECONDS)
                if not _ok(result):
                    raise EnvironmentError("environment_build_failed")
            if not _ok(self.runner([*prefix, "image", "inspect", selected], timeout=15)):
                raise EnvironmentError("environment_build_failed")
        self._update(job, "verifying")
        result = self.runner([
            *prefix, "run", "--rm", "--pull=never", "--network", "none",
            "--entrypoint", "python", image, "-c",
            "import pathlib,shutil; assert shutil.which('pi')" + (
                "; assert pathlib.Path('/opt/adore/pi/adore-chatgpt.mjs').is_file()"
                if image == EXECUTOR_BASE_IMAGE else ""),
        ], timeout=30)
        if not _ok(result):
            raise EnvironmentError("environment_executor_invalid")
