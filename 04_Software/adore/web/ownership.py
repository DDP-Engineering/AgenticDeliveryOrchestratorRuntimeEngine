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
@file    ownership.py
@brief   Explicit local worker identities and conservative process evidence.
@details Heartbeats report availability; only demonstrated process death permits
         recovery. PID birth prevents reuse from granting an old owner authority.
"""

from __future__ import annotations

# IMPORTS
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import re


# DATA MODELS / TYPEDEFINITIONS
class WebStoreError(RuntimeError):
    """@brief Invalid or corrupt web storage and account actions."""


class OwnershipError(WebStoreError):
    """@brief The caller no longer holds the required durable ownership."""

    def __init__(self, message: str, *, reason: str = "ownership_lost") -> None:
        """@brief Preserve a closed refusal code separately from diagnostic text."""
        self.reason = reason
        super().__init__(message)


@dataclass(frozen=True)
class WorkerOwner:
    """@brief Immutable server-issued handle for one scoped owner incarnation."""

    id: str
    generation: int
    role: str
    project_id: str = ""
    run_id: str = ""


# PUBLIC API
def process_birth(pid: int) -> str | None:
    """@brief Read process creation identity; None proves absence, errors do not.
    @param[in] pid Positive local PID.
    @return Immutable creation evidence, or None for a missing process.
    @exception WebStoreError Creation identity cannot be established.
    """
    if type(pid) is not int or pid < 1:
        raise WebStoreError("worker process identity is corrupt")
    if os.name == "nt":
        from adore.local_process import LocalExecutionError, WindowsJobs

        try:
            return WindowsJobs().birth(pid)
        except (LocalExecutionError, OSError) as exc:
            raise WebStoreError("worker process identity unavailable") from exc
    if platform.system() != "Linux":
        raise WebStoreError("worker process identity unavailable on this platform")
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", boot):
            raise ValueError("invalid boot identity")
    except (OSError, ValueError) as exc:
        raise WebStoreError("worker boot identity unavailable") from exc
    try:
        text = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields = text[text.rindex(")") + 2:].split()
        ticks = fields[19]
        if not ticks.isdigit() or not boot:
            raise ValueError("invalid process birth")
        # An unreaped zombie cannot perform another effect.
        return None if fields[0] == "Z" else boot + ":" + ticks
    except FileNotFoundError:
        from adore.util import process_alive

        if process_alive(pid):
            raise WebStoreError("live worker process identity unavailable") from None
        return None
    except (OSError, ValueError, IndexError) as exc:
        raise WebStoreError("worker process identity unavailable") from exc


# END OF FILE
