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
@file test_opencode_catalogue.py
@brief The OpenCode model catalogue refreshed in a container and reused by jobs.
@details OpenCode's built-in catalogue lags behind new models, so a request for
         a newer model fails until `opencode models --refresh` has run. ADORE
         refreshes it when the AI connection is tested, keeps it in the
         project's state folder, and copies it into each job container.
"""

from __future__ import annotations

# IMPORTS
import json
from pathlib import Path

from adore.opencode_catalogue import (
    CATALOGUE_NAME,
    CONTAINER_OPENCODE_CACHE_DIR,
    knows_model,
    refresh,
    stage,
    stage_or_refresh,
)
from adore.util import CommandResult

# CONSTANTS
CATALOGUE = {"openai": {"id": "openai", "models": {"gpt-6.1-sol": {}, "gpt-5.5": {}}}}


# LOCAL HELPERS
class Container:
    """@brief A container double: records commands and plays the cache and io copies."""

    def __init__(self, io_host: Path, refresh_ok: bool = True, fetched: str | None = None) -> None:
        self.io_host, self.refresh_ok = io_host, refresh_ok
        self.fetched = json.dumps(CATALOGUE) if fetched is None else fetched
        self.calls: list[tuple[list[str], float | None]] = []
        self.staged: str | None = None

    def __call__(self, argv, timeout=None) -> CommandResult:
        argv = list(argv)
        self.calls.append((argv, timeout))
        if argv[:3] == ["opencode", "models", "--refresh"]:
            return CommandResult(argv, 0 if self.refresh_ok else 1)
        if argv[0] == "cp" and argv[1].startswith(CONTAINER_OPENCODE_CACHE_DIR):
            (self.io_host / CATALOGUE_NAME).write_text(self.fetched, encoding="utf-8")
        elif argv[0] == "cp":
            self.staged = (self.io_host / CATALOGUE_NAME).read_text(encoding="utf-8")
        return CommandResult(argv)


def _io(tmp_path: Path) -> Path:
    path = tmp_path / "io"
    path.mkdir()
    return path


# TESTS
def test_knows_model_reads_provider_and_model(tmp_path):
    """@brief A saved catalogue knows `provider/model` IDs; anything unreadable knows none."""
    saved = tmp_path / CATALOGUE_NAME
    assert not knows_model(saved, "openai/gpt-6.1-sol")
    saved.write_text(json.dumps(CATALOGUE), encoding="utf-8")
    assert knows_model(saved, "openai/gpt-6.1-sol")
    assert not knows_model(saved, "openai/gpt-7")
    assert not knows_model(saved, "anthropic/claude")
    saved.write_text("{not json", encoding="utf-8")
    assert not knows_model(saved, "openai/gpt-6.1-sol")


def test_stage_copies_the_saved_catalogue_into_the_container(tmp_path):
    """@brief The saved catalogue lands in OpenCode's cache; the exchange copy is removed."""
    io_host = _io(tmp_path)
    saved = tmp_path / CATALOGUE_NAME
    saved.write_text(json.dumps(CATALOGUE), encoding="utf-8")
    container = Container(io_host)
    assert stage(container, saved, io_host, "/adore/io")
    assert ["mkdir", "-p", CONTAINER_OPENCODE_CACHE_DIR] in [argv for argv, _ in container.calls]
    assert ["cp", "/adore/io/" + CATALOGUE_NAME, CONTAINER_OPENCODE_CACHE_DIR + "/models.json"] in [
        argv for argv, _ in container.calls
    ]
    assert json.loads(container.staged or "{}") == CATALOGUE
    assert not (io_host / CATALOGUE_NAME).exists()
    assert not stage(container, tmp_path / "missing.json", io_host, "/adore/io")


def test_refresh_saves_a_fresh_catalogue(tmp_path):
    """@brief A successful refresh replaces the saved catalogue."""
    io_host = _io(tmp_path)
    saved = tmp_path / "state" / CATALOGUE_NAME
    container = Container(io_host)
    assert refresh(container, saved, io_host, "/adore/io")
    assert json.loads(saved.read_text(encoding="utf-8")) == CATALOGUE
    assert any(
        argv[:3] == ["opencode", "models", "--refresh"] and timeout and timeout >= 20
        for argv, timeout in container.calls
    )
    assert not (io_host / CATALOGUE_NAME).exists()


def test_a_failed_or_bad_refresh_keeps_the_saved_catalogue(tmp_path):
    """@brief No network or a malformed download never replaces the last good catalogue."""
    io_host = _io(tmp_path)
    saved = tmp_path / CATALOGUE_NAME
    saved.write_text('{"openai": {"models": {"gpt-5.5": {}}}}', encoding="utf-8")
    before = saved.read_bytes()
    assert not refresh(Container(io_host, refresh_ok=False), saved, io_host, "/adore/io")
    assert not refresh(Container(io_host, fetched="[1, 2]"), saved, io_host, "/adore/io")
    assert not refresh(Container(io_host, fetched="{broken"), saved, io_host, "/adore/io")
    assert saved.read_bytes() == before
    assert not (io_host / CATALOGUE_NAME).exists()


def test_jobs_reuse_a_catalogue_that_knows_the_model(tmp_path):
    """@brief A known model costs no refresh; an unknown one refreshes once and saves."""
    io_host = _io(tmp_path)
    saved = tmp_path / CATALOGUE_NAME
    saved.write_text(json.dumps(CATALOGUE), encoding="utf-8")
    known = Container(io_host)
    assert stage_or_refresh(known, saved, io_host, "/adore/io", "openai/gpt-6.1-sol") == "staged"
    assert not any(argv[:2] == ["opencode", "models"] for argv, _ in known.calls)
    saved.write_text('{"openai": {"models": {"gpt-5.5": {}}}}', encoding="utf-8")
    unknown = Container(io_host)
    assert (
        stage_or_refresh(unknown, saved, io_host, "/adore/io", "openai/gpt-6.1-sol") == "refreshed"
    )
    assert knows_model(saved, "openai/gpt-6.1-sol")
    offline = Container(io_host, refresh_ok=False)
    saved.unlink()
    assert (
        stage_or_refresh(offline, saved, io_host, "/adore/io", "openai/gpt-6.1-sol") == "built-in"
    )


# END OF FILE
