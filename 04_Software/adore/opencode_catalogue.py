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
@file opencode_catalogue.py
@brief Refresh OpenCode's model catalogue in a container and reuse it for jobs.
@details A fresh container only has the catalogue built into its OpenCode
         release, which lags behind new models: a request for a newer model
         then fails ("Unexpected server error") until `opencode models
         --refresh` has run. ADORE refreshes the catalogue when the AI
         connection is tested, keeps it in the project's state folder, and
         copies it into each job container; a job refreshes by itself only when
         the saved catalogue does not know the project's model. Every step is
         best effort: without network the built-in catalogue is used.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
import json
from pathlib import Path
import shutil

from adore.branding import CONTAINER_HOME
from adore.util import CommandResult

# CONSTANTS
CATALOGUE_NAME = "opencode-models.json"
CONTAINER_OPENCODE_CACHE_DIR = f"{CONTAINER_HOME}/.cache/opencode"
REFRESH_TIMEOUT = 30
MAX_CATALOGUE_BYTES = 32 * 1024 * 1024

Execute = Callable[..., CommandResult]


def catalogue_path(store_root: str | Path) -> Path:
    """@brief Where a project keeps its last good OpenCode catalogue."""
    return Path(store_root) / CATALOGUE_NAME


def _read(path: Path) -> dict | None:
    """@brief A bounded catalogue object, or None when absent or unreadable."""
    try:
        if not 0 < path.stat().st_size <= MAX_CATALOGUE_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def knows_model(path: Path, model: str) -> bool:
    """@brief True when the saved catalogue lists `provider/model`."""
    provider, _, name = model.partition("/")
    entry = (_read(path) or {}).get(provider)
    models = entry.get("models") if isinstance(entry, dict) else None
    return bool(name) and isinstance(models, dict) and name in models


def stage(execute: Execute, saved: Path, io_host: Path, io_container: str) -> bool:
    """
    @brief      Copy the saved catalogue into the container's OpenCode cache.
    @param[in]  execute Runs one command in the container (argv, timeout=None).
    @param[in]  saved The project's saved catalogue.
    @param[in]  io_host Host side of the container's exchange folder.
    @param[in]  io_container The same folder inside the container.
    @return     True when the catalogue is in place.
    """
    if _read(saved) is None:
        return False
    staged = io_host / CATALOGUE_NAME
    try:
        shutil.copyfile(saved, staged)
        staged.chmod(0o644)  # the container user reads it; the exchange folder is private
        return (
            execute(["mkdir", "-p", CONTAINER_OPENCODE_CACHE_DIR]).ok
            and execute(
                [
                    "cp",
                    f"{io_container}/{CATALOGUE_NAME}",
                    f"{CONTAINER_OPENCODE_CACHE_DIR}/models.json",
                ]
            ).ok
        )
    except OSError:
        return False
    finally:
        staged.unlink(missing_ok=True)


def refresh(execute: Execute, saved: Path, io_host: Path, io_container: str) -> bool:
    """
    @brief      Refresh the catalogue in the container and save it for later jobs.
    @return     True when a valid fresh catalogue replaced the saved one.
    """
    fetched = io_host / CATALOGUE_NAME
    try:
        if not execute(["opencode", "models", "--refresh"], timeout=REFRESH_TIMEOUT).ok:
            return False
        if not execute(
            [
                "cp",
                f"{CONTAINER_OPENCODE_CACHE_DIR}/models.json",
                f"{io_container}/{CATALOGUE_NAME}",
            ]
        ).ok:
            return False
        if _read(fetched) is None:
            return False
        saved.parent.mkdir(parents=True, exist_ok=True)
        partial = saved.with_name(saved.name + ".partial")
        shutil.copyfile(fetched, partial)
        partial.replace(saved)
        return True
    except OSError:
        return False
    finally:
        fetched.unlink(missing_ok=True)


def stage_or_refresh(
    execute: Execute, saved: Path, io_host: Path, io_container: str, model: str
) -> str:
    """
    @brief      Give a job container a catalogue that knows its model.
    @return     "staged" (saved catalogue reused), "refreshed" (fresh one saved),
                "saved" (refresh failed, older saved catalogue in place) or
                "built-in" (OpenCode's own catalogue only).
    """
    if knows_model(saved, model) and stage(execute, saved, io_host, io_container):
        return "staged"
    had_saved = stage(execute, saved, io_host, io_container)
    if refresh(execute, saved, io_host, io_container):
        return "refreshed"
    return "saved" if had_saved else "built-in"


# END OF FILE
