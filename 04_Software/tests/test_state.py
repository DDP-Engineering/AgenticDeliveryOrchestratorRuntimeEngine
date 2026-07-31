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
@file test_state.py
@brief Tests for the local authoritative run-state store.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.1.1
"""

from __future__ import annotations

# IMPORTS
import json
import os
from pathlib import Path
import socket

from adore.state import RunState, StateError, StateStore, content_hash, derive_run_id
import pytest

# HELPER FUNCTIONS


def _store(tmp_path: Path) -> StateStore:
    """
    @brief      A store rooted in the test tmp dir.
    @param[in]  tmp_path pytest tmp dir.
    @return     The StateStore.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.1
    """
    return StateStore(tmp_path / ".adore", slug="adore")


# PUBLIC API / TESTS


def test_derive_run_id_is_stable_and_safe() -> None:
    """
    @brief   Run-id is deterministic and filesystem-safe (design doc 8a).
    @version 0.1.0
    """
    a = derive_run_id("gitlab", "group/sub/runtime-project", 14)
    b = derive_run_id("gitlab", "group/sub/runtime-project", 14)
    assert a == b == "gitlab-group-sub-runtime-project-14"
    assert "/" not in a


def test_content_hash_detects_drift() -> None:
    """
    @brief   Same content hashes equal; changed content hashes differ.
    @version 0.1.0
    """
    assert content_hash("Title", "Body") == content_hash("Title", "Body")
    assert content_hash("Title", "Body") != content_hash("Title", "Body changed")
    assert content_hash("  Title  ", "Body\n") == content_hash("Title", "Body")


def test_save_load_round_trip(tmp_path: Path) -> None:
    """
    @brief   RunState persists and reloads with timestamps stamped.
    @version 0.1.0
    """
    store = _store(tmp_path)
    state = RunState(run_id="gitlab-g-p-14", ticket_iid=14, stage="check", lifecycle="working")
    store.save(state)
    assert state.created_at and state.updated_at
    loaded = store.load("gitlab-g-p-14")
    assert loaded.run_id == "gitlab-g-p-14"
    assert loaded.ticket_iid == 14
    assert loaded.stage == "check"
    assert loaded.created_at == state.created_at


def test_from_dict_ignores_unknown_keys() -> None:
    """
    @brief   Newer state files with extra keys still load (forward compat).
    @version 0.1.0
    """
    state = RunState.from_dict({"run_id": "r", "ticket_iid": 1, "future_field": True})
    assert state.run_id == "r"


def test_aegis_run_id_round_trips(tmp_path: Path) -> None:
    """
    @brief   The AEGIS run id survives save/load, so a restart resumes the
             same governed run instead of starting a second one.
    @version 0.1.0
    """
    store = _store(tmp_path)
    aegis_run = "fix-2026-08-01T101112Z-0a1b2c3d"
    state = RunState(run_id="gitlab-g-p-14", ticket_iid=14, aegis_run_id=aegis_run)
    store.save(state)
    assert store.load("gitlab-g-p-14").aegis_run_id == aegis_run
    payload = json.loads(
        (store.run_dir("gitlab-g-p-14") / "state.json").read_text(encoding="utf-8")
    )
    assert payload["aegis_run_id"] == aegis_run


def test_state_without_the_aegis_run_id_field_loads_as_not_started(
    tmp_path: Path,
) -> None:
    """
    @brief   A state file written before the field existed yields None - the
             conductor's "no AEGIS run started yet" signal. The dataclass
             default is the whole mechanism; no migration code exists.
    @version 0.1.0
    """
    store = _store(tmp_path)
    run_dir = store.run_dir("gitlab-g-p-15")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "gitlab-g-p-15", "ticket_iid": 15, "stage": "intake"}),
        encoding="utf-8",
    )
    assert store.load("gitlab-g-p-15").aegis_run_id is None


def test_ticket_snapshot_and_journal(tmp_path: Path) -> None:
    """
    @brief   Ticket snapshot round-trips; journal appends in order.
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.save_ticket("r-1", {"iid": 14, "title": "T", "labels": ["agent-ready"]})
    assert store.load_ticket("r-1")["title"] == "T"
    store.journal("r-1", "picked", ticket=14)
    store.journal("r-1", "gate-advanced", stage="requirement")
    events = store.read_journal("r-1")
    assert [event["event"] for event in events] == ["picked", "gate-advanced"]
    assert all("ts" in event for event in events)


def test_list_runs_and_delete(tmp_path: Path) -> None:
    """
    @brief   Runs list sorted; delete_run removes the whole state dir.
    @version 0.1.0
    """
    store = _store(tmp_path)
    assert store.list_runs() == []
    store.save(RunState(run_id="b-run", ticket_iid=2))
    store.save(RunState(run_id="a-run", ticket_iid=1))
    assert [run.run_id for run in store.list_runs()] == ["a-run", "b-run"]
    store.delete_run("a-run")
    assert [run.run_id for run in store.list_runs()] == ["b-run"]
    assert not store.exists("a-run")


def test_load_missing_run_raises(tmp_path: Path) -> None:
    """
    @brief   Loading an unknown run raises FileNotFoundError.
    @version 0.1.0
    """
    with pytest.raises(FileNotFoundError):
        _store(tmp_path).load("nope")


def test_single_instance_lock(tmp_path: Path) -> None:
    """
    @brief   The lock is exclusive, reports its holder, and releases cleanly.
    @version 0.1.0
    """
    store = _store(tmp_path)
    assert store.lock_info() is None
    assert store.acquire_lock() is True
    assert store.acquire_lock() is False
    info = store.lock_info()
    assert info is not None and "pid" in info
    store.release_lock()
    assert store.lock_info() is None
    assert store.acquire_lock() is True
    store.release_lock()


def test_pause_flag(tmp_path: Path) -> None:
    """
    @brief   pause/resume toggles the global pickup flag.
    @version 0.1.0
    """
    store = _store(tmp_path)
    assert not store.is_paused()
    store.pause()
    assert store.is_paused()
    store.resume()
    assert not store.is_paused()
    store.resume()  # idempotent


def test_corrupt_state_json_fails_closed(tmp_path: Path) -> None:
    """
    @brief   Unparseable, wrong-shape, or key-incomplete state.json raises
             StateError (never silently reinitialized).
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.save(RunState(run_id="r-1", ticket_iid=1))
    state_file = store.run_dir("r-1") / "state.json"
    for corrupt in ("{not json", '["not", "an", "object"]', '{"stage": "intake"}'):
        state_file.write_text(corrupt, encoding="utf-8")
        with pytest.raises(StateError):
            store.load("r-1")


def test_corrupt_ticket_json_fails_closed(tmp_path: Path) -> None:
    """
    @brief   A corrupt ticket snapshot raises StateError.
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.save_ticket("r-1", {"iid": 14, "title": "T"})
    ticket_file = store.run_dir("r-1") / "ticket.json"
    for corrupt in ("###", "[1, 2]"):
        ticket_file.write_text(corrupt, encoding="utf-8")
        with pytest.raises(StateError):
            store.load_ticket("r-1")


def test_list_runs_skips_corrupt_and_invalid_runs_reports_them(tmp_path: Path) -> None:
    """
    @brief   One corrupt run never breaks listing; it stays visible through
             invalid_runs() instead of disappearing.
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.save(RunState(run_id="good-run", ticket_iid=1))
    store.save(RunState(run_id="bad-run", ticket_iid=2))
    (store.run_dir("bad-run") / "state.json").write_text("garbage", encoding="utf-8")
    assert [run.run_id for run in store.list_runs()] == ["good-run"]
    assert store.invalid_runs() == ["bad-run"]
    assert store.exists("bad-run")  # never silently deleted


def test_journal_tolerates_torn_tail(tmp_path: Path) -> None:
    """
    @brief   A torn trailing journal line (crash mid-append) is skipped; the
             intact records still load.
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.journal("r-1", "picked")
    store.journal("r-1", "gate-advanced")
    with (store.run_dir("r-1") / "journal.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"ts": "2026-07-02T1')  # power loss mid-write
    events = store.read_journal("r-1")
    assert [event["event"] for event in events] == ["picked", "gate-advanced"]


def test_corrupt_lock_file_still_counts_as_held(tmp_path: Path) -> None:
    """
    @brief   A damaged lock file blocks a second poller instead of being
             treated as free.
    @version 0.1.0
    """
    store = _store(tmp_path)
    store.root.mkdir(parents=True, exist_ok=True)
    store.lock_path.write_text("###", encoding="utf-8")
    assert store.lock_info() == {}
    assert store.acquire_lock() is False


def _write_lock(root: Path, *, pid: int, host: str) -> None:
    """
    @brief      Plant a lock file with a chosen pid + host (crash simulation).
    @param[in]  root Store root.
    @param[in]  pid Recorded owner pid.
    @param[in]  host Recorded owner host.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-24
    @version    0.1.0
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "adore.lock").write_text(
        json.dumps({"pid": pid, "acquired_at": "t", "host": host}),
        encoding="utf-8",
    )


def test_stale_lock_from_this_host_is_reclaimed(tmp_path: Path) -> None:
    """
    @brief   A lock whose owner is provably gone on THIS host is reclaimed, so a
             crashed poller does not wedge every future start (systemd restart /
             Task Scheduler) until a manual `adore cleanup`.
    @version 0.1.0
    """
    root = tmp_path / ".adore"
    _write_lock(root, pid=424242, host=socket.gethostname())
    store = StateStore(root, slug="adore", process_alive=lambda _pid: False)
    assert store.acquire_lock() is True
    info = store.lock_info()
    assert info is not None and info["pid"] == os.getpid()
    store.release_lock()


def test_live_lock_is_never_reclaimed(tmp_path: Path) -> None:
    """
    @brief   A lock whose owner is still alive is never stolen (no double poller).
    @version 0.1.0
    """
    root = tmp_path / ".adore"
    _write_lock(root, pid=4242, host=socket.gethostname())
    store = StateStore(root, slug="adore", process_alive=lambda _pid: True)
    assert store.acquire_lock() is False


def test_lock_from_another_host_is_not_reclaimed(tmp_path: Path) -> None:
    """
    @brief   A lock written on a different host is never reclaimed, even if its
             pid looks dead here - a pid is meaningless across hosts.
    @version 0.1.0
    """
    root = tmp_path / ".adore"
    _write_lock(root, pid=1, host="some-other-host")
    store = StateStore(root, slug="adore", process_alive=lambda _pid: False)
    assert store.acquire_lock() is False


def test_unreadable_lock_is_not_reclaimed(tmp_path: Path) -> None:
    """
    @brief   An unreadable lock record fails closed - never reclaimed on a guess,
             even with a dead-owner probe.
    @version 0.1.0
    """
    root = tmp_path / ".adore"
    root.mkdir(parents=True, exist_ok=True)
    (root / "adore.lock").write_text("###", encoding="utf-8")
    store = StateStore(root, slug="adore", process_alive=lambda _pid: False)
    assert store.acquire_lock() is False


# END OF FILE
