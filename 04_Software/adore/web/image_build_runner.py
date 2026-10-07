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
@file    image_build_runner.py
@brief   Owned native runtime-client process control for project image builds.
@details Reuses Windows Jobs/Linux delegated cgroups, bounded redacted drains
         and identity-checked recovery. Daemon cleanup remains a separate claim.
"""

from __future__ import annotations

# IMPORTS
import os
from pathlib import Path
import platform
import shutil
from threading import Event, Thread

from adore.local_process import LocalProcessController, NativeScopes, native_context
from adore.web.image_build import ImageBuildError


# PUBLIC API
class ImageBuildRunner:
    """@brief Adapt the existing owned native controller to runtime argv calls."""

    def __init__(self, store, operation, *, controller=None, watch_cancel=True) -> None:
        """@brief Select only operation-owned control and output paths.
        @param[in] store Project image artifact store.
        @param[in] operation Closed immutable build record.
        @param[in] controller Optional injected native process controller.
        """
        self.store, self.operation = store, operation
        self.watch_cancel = watch_cancel
        self.control = store.owned_path(operation["id"] + "/control")
        self.control.mkdir(parents=True, exist_ok=True)
        self.controller = controller or LocalProcessController(
            NativeScopes(
                platform.system(), cgroup_root=os.environ.get("ADORE_BUILD_CGROUP_ROOT", "")
            )
        )
        self.host = native_context()["host"]

    def __call__(self, argv, *, cwd=None, timeout=None, env=None):
        """@brief Run bounded argv while a durable cancel stops its owned scope.
        @return Native command result; retained files are bounded and redacted.
        @exception ImageBuildError Failed scope control is an uncertain outcome.
        """
        launches = self.store.owned_path(self.operation["id"] + "/control/launches")
        if launches.exists() and len(list(launches.iterdir())) >= 160:
            raise ImageBuildError("image_control_retention_full")
        executable = shutil.which(argv[0], path=env.get("PATH", ""))
        if executable is None:
            raise ImageBuildError("image_runtime_unavailable")
        try:
            actual = [str(Path(executable).resolve(strict=True)), *argv[1:]]
        except OSError as exc:
            raise ImageBuildError("image_runtime_unavailable") from exc
        done = Event()
        failures = []

        def watch():
            """@brief Stop only the operation's verified process scope."""
            while not done.wait(0.1):
                try:
                    if self.watch_cancel and self.store.cancelled(self.operation["id"]):
                        self.controller.interrupt(self.control, self.operation["id"], self.host)
                except Exception:  # noqa: BLE001 - unsafe control must become uncertain
                    failures.append(True)
                    return

        watcher = Thread(target=watch, daemon=True)
        watcher.start()
        try:
            result = self.controller.run_files(
                actual,
                cwd=Path(cwd),
                env=env,
                timeout=timeout,
                stdout=self.store.owned_path(self.operation["id"] + "/stdout.txt"),
                stderr=self.store.owned_path(self.operation["id"] + "/stderr.txt"),
                control=self.control,
                run_id=self.operation["id"],
                host=self.host,
                secrets=self.store.secrets,
                stdout_limit=65536,
            )
            if failures:
                raise ImageBuildError("image_cancel_unconfirmed")
            # run_files owns redacted stream files; its result carries status only.
            # Recheck ownership and bounds after the process/drains have finished.
            streams = []
            for stream in ("stdout", "stderr"):
                path = self.store.owned_path(self.operation["id"] + "/" + stream + ".txt")
                if not path.is_file() or path.stat().st_size > 65536:
                    raise ImageBuildError("image_runtime_output_invalid")
                with path.open("rb") as captured:
                    data = captured.read(65537)
                if len(data) > 65536:
                    raise ImageBuildError("image_runtime_output_invalid")
                try:
                    streams.append(self.store.redact(data.decode("utf-8")))
                except UnicodeError as exc:
                    raise ImageBuildError("image_runtime_output_invalid") from exc
            result.stdout, result.stderr = streams
            return result
        except ImageBuildError:
            raise
        except Exception as exc:  # noqa: BLE001 - never guess an uncontrolled outcome
            raise ImageBuildError("image_process_control_unconfirmed") from exc
        finally:
            done.set()
            watcher.join(timeout=2)

    def recover(self) -> None:
        """@brief Recover verified ownership on the original machine/account only.
        @exception ImageBuildError Changed host or unconfirmed owned process drain.
        """
        if self.operation["host"] != native_context():
            raise ImageBuildError("image_host_changed")
        try:
            self.controller.recover(self.control, self.operation["id"], self.host)
        except Exception as exc:  # noqa: BLE001 - native controller closes all ownership failures
            raise ImageBuildError("image_process_control_unconfirmed") from exc


# END OF FILE
