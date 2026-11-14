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
@file       status.py
@brief      Read-only project capacity and component worker projections.
@details    Heartbeats describe observations, never ownership recovery or free slots.
"""

# IMPORTS
from adore.capacity import initial_start_slots


# PUBLIC API
def worker_status(rows: list[dict], role: str, project_id: str = "", run_id: str = "") -> dict:
    """@brief Summarize one explicit component without exposing owner capabilities.
    @param[in] rows Validated WebStore heartbeat observations.
    @param[in] role Component role.
    @param[in] project_id Immutable project identity, empty for server components.
    @param[in] run_id Exact run for a run component.
    @return Heartbeat freshness, observed activity and timestamp, independently.
    """
    selected = [
        row
        for row in rows
        if (row["role"], row["project_id"], row["run_id"]) == (role, project_id, run_id)
    ]
    recent = [row for row in selected if row["ready"]]
    return {
        "role": role,
        "project_id": project_id,
        "run_id": run_id,
        "heartbeat": "recent" if recent else "stale" if selected else "missing",
        "activity": (
            "busy"
            if any(row["activity"] == "busy" for row in recent)
            else "idle"
            if recent
            else "unknown"
        ),
        "updated_at": max((row["updated_at"] for row in selected), default=None),
    }


def occupied_slots(state, runs: list) -> set[str]:
    """@brief Mirror admission's working/reserved slots, including owned execution locks.
    @param[in] state Current project StateStore.
    @param[in] runs Validated current runs.
    @return Distinct occupied run identities; parked idle waits do not reserve slots.
    """
    return state.execution_slots() | {
        run.run_id
        for run in runs
        if run.lifecycle in ("working", "handoff-pending")
        or run.lifecycle == "parked-clarification"
        and run.parked_polls == 0
    }


def capacity_status(
    project_id: str,
    limit: int,
    state,
    runs: list,
    workers: list[dict],
    operations: list[dict],
    *,
    archived: bool = False,
    active_limit: int | None = None,
) -> dict:
    """@brief Project immutable-identity capacity and evidenced queued command causes.
    @param[in] project_id Authorized immutable project identity.
    @param[in] limit Canonical polling.max_concurrent_runs.
    @param[in] state Current project state store.
    @param[in] runs Validated runs.
    @param[in] workers Validated relevant component observations.
    @param[in] operations Validated unfinished project requests.
    @param[in] archived Whether dispatch is disabled by project archival.
    @param[in] active_limit Saved limit before any staged reduction.
    @return Slots and queue facts, without simulating admission or probing a process.
    """
    occupied = len(occupied_slots(state, runs))
    free = max(0, limit - occupied)
    worker = worker_status(workers, "project", project_id)
    running = {
        row["run_id"] for row in workers if row["role"] == "run" and row["project_id"] == project_id
    }
    ready = (
        worker["heartbeat"] == "recent"
        and worker_status(workers, "supervisor")["heartbeat"] == "recent"
    )
    queue, jobs = [], set()
    for op in operations:
        if op["domain"] != "execution" or op["status"] != "pending":
            continue
        key = op["resource_key"]
        same_job = key.startswith("job:") and key[4:] in running
        if same_job:
            reason = "same_job"
        elif not ready:
            reason = "worker_unavailable"
        elif not free and op["action"] != "cancel":
            reason = (
                "staged_change"
                if active_limit is not None and occupied < active_limit
                else "project_limit"
            )
        else:
            reason = "dispatching"
        queue.append({"id": op["id"], "action": op["action"], "reason": reason})
        if op["action"] in ("start", "retry", "restart"):
            jobs.add(key)
    waiting_runs = []
    started = len(initial_start_slots(state, runs))
    for run in runs:
        if run.execution_pending and run.run_id not in running:
            jobs.add("job:" + run.run_id)
            reason = "dispatching"
            if not ready:
                reason = "worker_unavailable"
            elif started >= limit:
                reason = (
                    "staged_change"
                    if active_limit is not None and started < active_limit
                    else "project_limit"
                )
            waiting_runs.append(
                {
                    "ticket_iid": run.ticket_iid,
                    "reason": reason,
                }
            )
    return {
        "project_id": project_id,
        "limit": limit,
        "occupied": occupied,
        "free": free,
        "waiting_jobs": len(jobs),
        "queue": queue,
        "waiting_runs": waiting_runs,
        "worker": worker,
        "available": ready and free > 0 and not archived,
    }


# END OF FILE
