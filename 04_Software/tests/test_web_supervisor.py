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
@file    test_web_supervisor.py
@brief   Independent local process supervision contracts.
@details Offline helpers and injected boundaries never run a forge or executor.
"""

# IMPORTS
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Event, Thread
import time
from types import SimpleNamespace

from adore.profiles import ProfileStore
from adore.state import RunState, StateError, StateStore
from adore.web import commands
from adore.web.ownership import OwnershipError, process_birth
from adore.web.processes import ProcessTree, assert_ancestry, stop_trees
from adore.web.store import WebStore
from adore.web.supervisor import ProjectWorker, Supervisor
import pytest

from tests.supervisor_helper import offline_engine


# LOCAL HELPERS
def eventually(predicate, *, timeout=12):
    """@brief Await only bounded local observations, surfacing process errors in assertions."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    assert predicate(), "bounded local observation did not arrive"


def project(profiles, name, limit=1):
    """@brief Prepare an isolated valid config and independent state/work paths."""
    root = profiles.home / (name + "-resources")
    root.mkdir(parents=True)
    (root / "clone").mkdir()
    profile = profiles.create(name, store_root=str(root / "state"))
    text = (Path(__file__).parents[1] / "config.example.toml").read_text(encoding="utf-8")
    text = text.replace('store_root = ".adore"', 'store_root = ' + json.dumps(profile.store_root))
    text = text.replace('repo_path = "../project"',
                        'repo_path = ' + json.dumps(str(root / "clone")))
    text = text.replace('root = "worktrees"', 'root = ' + json.dumps(str(root / "work")))
    text = text.replace('max_concurrent_runs = 1', f'max_concurrent_runs = {limit}')
    text = text.replace('publish_checkpoints = true', 'publish_checkpoints = false')
    text = text.replace('poll_interval_seconds = 60', 'poll_interval_seconds = 1')
    text = text.replace('poll_jitter_seconds = 5', 'poll_jitter_seconds = 0')
    profiles.config_path(name).write_text(text, encoding="utf-8")
    # Tests own admission; automatic external polling must remain stopped.
    StateStore(profile.store_root).pause()
    return profile


def reserve(profiles, name, iid):
    """@brief Exercise real atomic product admission without an external forge."""
    engine, forge, *_ = offline_engine(profiles, name)
    forge.ticket = replace(forge.ticket, iid=iid)
    return engine.poll_once(ticket_iid=iid, admit_only=True)


def run_factory(argv, environment):
    """@brief Replace only external collaborators, keeping actual dispatcher processes."""
    role = argv[argv.index("--role") + 1]
    assert role == "run", argv
    def value(flag):
        return argv[argv.index(flag) + 1]
    return ProcessTree([sys.executable, "-m", "tests.supervisor_helper",
                        value("--home"), value("--project-id"), value("--run-id"),
                        value("--revision")], environment)


def start_project(profiles, web, profile):
    """@brief Bind an independently schedulable project to the production dispatcher."""
    worker = ProjectWorker(profiles, web, profile.project_id, spawn=run_factory)
    worker.owner = web.register_worker("project", project_id=profile.project_id)
    return worker


# PUBLIC API
def test_worker_entry_uses_process_supervisor(tmp_path, monkeypatch):
    """@brief The installed entry launches the process owner rather than a serial loop."""
    seen = []
    monkeypatch.setitem(sys.modules, "adore.web.supervisor", SimpleNamespace(
        Supervisor=lambda profiles, web: SimpleNamespace(
            run_forever=lambda **kwargs: seen.append(profiles.home))))
    monkeypatch.setattr(commands.CommandWorker, "run_forever", lambda self: None)
    monkeypatch.setattr(sys, "argv", ["adore-web-worker", "--home", str(tmp_path)])
    assert commands.main() == 0
    assert seen == [tmp_path]


@pytest.mark.parametrize("limits", [(1, 1), (2, 1)])
def test_actual_project_and_pool_overlap(tmp_path, limits):
    """@brief Independent real conductors enter fake executors together; N+1 waits."""
    profiles = ProfileStore(tmp_path / "home")
    alpha, beta = project(profiles, "alpha", limits[0]), project(profiles, "beta", limits[1])
    web = WebStore(profiles.home / "web.db")
    workers = [start_project(profiles, web, alpha), start_project(profiles, web, beta)]
    picked = [(alpha, reserve(profiles, "alpha", 7)), (beta, reserve(profiles, "beta", 7))]
    if limits[0] == 2:
        picked.append((alpha, reserve(profiles, "alpha", 8)))
    assert reserve(profiles, "alpha", 9)["at_capacity"]
    markers = [profiles.home / "barriers" / (p.project_id + "-" + r["run_id"])
               for p, r in picked]
    try:
        for worker in workers:
            assert worker.tick()
        eventually(lambda: all(marker.exists() for marker in markers))
        evidence = [json.loads(marker.read_text()) for marker in markers]
        assert len({row["pid"] for row in evidence}) == len(markers)
        assert all(process_birth(row["pid"]) == row["birth"] for row in evidence)
        assert not any(marker.with_suffix(".ended").exists() for marker in markers)
        assert reserve(profiles, "alpha", 9)["at_capacity"]
        # A remains blocked while B completes its actual conductor workflow.
        markers[1].with_suffix(".release").touch()
        beta_child = workers[1].children["run:" + picked[1][1]["run_id"]]
        eventually(lambda: beta_child.poll() is not None)
        assert beta_child.poll() == 0, beta_child.tail()
        assert StateStore(beta.store_root).load(
            picked[1][1]["run_id"]).lifecycle == "awaiting-approval"
        assert not markers[0].with_suffix(".ended").exists()
        for marker in markers:
            marker.with_suffix(".release").touch()
        eventually(lambda: all(child.poll() is not None for worker in workers
                               for child in worker.children.values()))
        assert reserve(profiles, "alpha", 9)["picked"] == 9
        for worker in workers:
            assert all(child.poll() == 0 for child in worker.children.values()), [
                child.tail() for child in worker.children.values()]
    finally:
        for worker in workers:
            stop_trees(list(worker.children.values()))


def test_process_tree_reports_exit_and_contains_blocked_descendants(tmp_path):
    """@brief A bounded Stop kills a real grandchild, with actual exit codes preserved."""
    done = ProcessTree([sys.executable, "-c", "print('observed'); raise SystemExit(7)"],
                       dict(os.environ))
    try:
        eventually(lambda: done.poll() is not None)
        assert done.poll() == 7
        assert "observed" in done.tail()
    finally:
        stop_trees([done])
    marker = tmp_path / "grandchild.json"
    script = ("import subprocess,sys,time,json; from pathlib import Path; "
              "from adore.web.ownership import process_birth; "
              "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
              "Path(sys.argv[1]).write_text(json.dumps([p.pid,process_birth(p.pid)])); "
              "time.sleep(60)")
    child = ProcessTree([sys.executable, "-c", script, str(marker)], dict(os.environ))
    try:
        eventually(marker.exists)
        pid, birth = json.loads(marker.read_text())
        assert process_birth(pid) == birth
        started = time.monotonic()
        stop_trees([child], grace=0.1)
        assert time.monotonic() - started < 6
        eventually(lambda: process_birth(pid) != birth)
    finally:
        if not child.closed:
            stop_trees([child], grace=0)


@pytest.mark.parametrize("raw", ['[]', '{}', '[{"pid":true,"birth":"x"}]',
                                 '[{"pid":1,"birth":"reused"}]', '{bad'])
def test_unproven_ancestry_refuses_effects(monkeypatch, raw):
    """@brief Malformed, missing and reused process evidence cannot authorize writes."""
    monkeypatch.setenv("ADORE_WORKER_ANCESTRY", raw)
    with pytest.raises(OwnershipError):
        assert_ancestry()
    with pytest.raises(OwnershipError):
        ProcessTree([sys.executable, "-c", "raise AssertionError('launched')"], dict(os.environ))


def test_unknown_ancestor_probe_is_refused(monkeypatch):
    """@brief Unavailable process evidence is not interpreted as authorizing a child."""
    def unavailable(pid):
        raise OSError("inspection unavailable")
    monkeypatch.setattr("adore.web.processes.process_birth", unavailable)
    with pytest.raises(OwnershipError):
        assert_ancestry(json.dumps([{"pid":123, "birth":"known"}]))


def test_duplicate_supervisor_refused_without_disturbing_owner(tmp_path):
    """@brief A home lock admits exactly one supervisor and Stop releases readiness."""
    profiles = ProfileStore(tmp_path)
    web = WebStore(tmp_path / "web.db")
    stop = Event()
    entered = Event()
    supervisor = Supervisor(profiles, web)
    supervisor.tick = entered.set
    errors = []
    def run():
        try:
            supervisor.run_forever(stop=stop, interval=0.02)
        except BaseException as exc:
            errors.append(exc)
    thread = Thread(target=run)
    thread.start()
    try:
        assert entered.wait(5)
        with pytest.raises(OwnershipError, match="another web supervisor"):
            Supervisor(profiles, web).run_forever(stop=Event())
        assert web.worker_ready()
    finally:
        stop.set()
        thread.join(5)
    assert not errors and not thread.is_alive()
    assert not web.worker_ready()


def test_supervisor_starts_distinct_project_and_configuration_processes(tmp_path):
    """@brief Production discovery owns separate real workers, including paused projects."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha")
    beta = profiles.create("beta")
    web = WebStore(profiles.home / "web.db")
    supervisor = Supervisor(profiles, web)
    try:
        supervisor.tick()
        eventually(lambda: len(web.worker_heartbeats(role="project")) == 2)
        eventually(lambda: len(web.worker_heartbeats(role="configuration")) == 1)
        with sqlite3.connect(web.path) as connection:
            pids = [row[0] for row in connection.execute(
                "SELECT p.pid FROM worker_processes p JOIN worker_owners w ON w.id=p.owner_id "
                "WHERE w.status='active'")]
        assert len(pids) == len(set(pids)) == 3
        assert os.getpid() not in pids
        alpha_child = supervisor.children[alpha.project_id]
        beta_child = supervisor.children[beta.project_id]
        configuration_child = supervisor.children["configuration"]
        # Killing A restarts only A; B and configuration keep their exact process.
        alpha_child.kill()
        eventually(lambda: alpha_child.poll() is not None)
        supervisor.tick()
        assert supervisor.children[beta.project_id] is beta_child
        assert supervisor.children["configuration"] is configuration_child
        assert beta_child.poll() is configuration_child.poll() is None
        assert alpha.project_id not in supervisor.children
        supervisor.retry_at[alpha.project_id] = 0
        supervisor.tick()
        assert supervisor.children[alpha.project_id] is not alpha_child
    finally:
        stop_trees([*supervisor.children.values(),
                    *(child for child, _ in supervisor.retiring.values())])


def test_corrupt_dispatch_or_state_blocks_process_launch(tmp_path):
    """@brief Persisted corruption never becomes implicit restart authority."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    admitted = reserve(profiles, "alpha", 7)
    web = WebStore(profiles.home / "web.db")
    calls = []
    worker = ProjectWorker(profiles, web, alpha.project_id,
                           spawn=lambda *args: calls.append(args))
    worker.owner = web.register_worker("project", project_id=alpha.project_id)
    state = StateStore(alpha.store_root)
    dispatch = state.run_dir(admitted["run_id"]) / "dispatch.json"
    original = dispatch.read_bytes()
    dispatch.write_text('{"schema":1,"status":"started"}', encoding="utf-8")
    with pytest.raises(StateError):
        worker.tick()
    assert not calls
    dispatch.write_bytes(original)
    (state.run_dir(admitted["run_id"]) / "state.json").write_text("{}", encoding="utf-8")
    with pytest.raises(StateError, match="corrupt"):
        worker.tick()
    assert not calls


def test_project_paused_start_admits_only_and_full_pool_defers_queue(tmp_path):
    """@brief Start remains explicit in pause; N+1 stays pending until space exists."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    operation = web.enqueue(admin["id"], "alpha", "start", "7", "manual-one")
    owner = web.register_worker("project", project_id=alpha.project_id)

    def admission(argv, environment):
        assert argv[-1] == "--admit-only"
        from adore.web.worker_context import WorkerContext
        value = json.loads(environment["ADORE_WORKER_CONTEXT"])
        context = WorkerContext(web, owner, value["operation_id"], value["generation"])
        engine, *_ = offline_engine(profiles, "alpha")
        context.bind_engine(engine)
        try:
            result = engine.poll_once(ticket_iid=7, admit_only=True)
            assert result["picked"] == 7
        finally:
            context.close()
        return 0

    commands.CommandWorker(profiles, web, runner=admission, project_id=alpha.project_id,
        domains=("execution",), execution_owner=owner, admit_only=True).run_pending()
    assert web.operation(operation["id"])["status"] == "succeeded"
    state = StateStore(alpha.store_root)
    assert state.is_paused()
    queued = web.enqueue(admin["id"], "alpha", "start", "8", "manual-two")
    calls = []
    worker = ProjectWorker(profiles, web, alpha.project_id,
                           spawn=lambda argv, env: calls.append(argv))
    worker.owner = owner
    worker.tick()
    assert len(calls) == 1 and calls[0][calls[0].index("--role") + 1] == "run"
    assert web.operation(queued["id"])["status"] == "pending"


def test_parent_crash_quiesces_tree_and_preserves_uncertain_claim(tmp_path):
    """@brief Crashing an actual owner cannot leave a conductor able to resume effects."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    operation = web.enqueue(admin["id"], "alpha", "start", "7", "before-crash")
    marker = tmp_path / "owned-processes.json"
    child_script = (
        "import json,os,subprocess,sys,time; from pathlib import Path; "
        "from adore.web.store import WebStore; "
        "from adore.web.ownership import process_birth; "
        "w=WebStore(Path(sys.argv[1])/'web.db'); "
        "o=w.register_worker('project',project_id=sys.argv[2]); "
        "w.claim_next(o,domain='execution'); "
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
        "Path(sys.argv[3]).write_text(json.dumps([[os.getpid(),process_birth(os.getpid())],"
        "[p.pid,process_birth(p.pid)]])); time.sleep(60)"
    )
    parent_script = (
        "import os,sys,time; from adore.web.processes import ProcessTree; "
        "p=ProcessTree([sys.executable,'-c',sys.argv[1],*sys.argv[2:]],dict(os.environ)); "
        "time.sleep(60)"
    )
    parent = subprocess.Popen([sys.executable, "-c", parent_script, child_script,
                               str(profiles.home), alpha.project_id, str(marker)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        eventually(marker.exists)
        identities = json.loads(marker.read_text())
        assert web.operation(operation["id"])["status"] == "running"
        parent.kill()
        parent.wait(timeout=5)
        eventually(lambda: all(process_birth(pid) != birth for pid, birth in identities))
        assert web.recover_interrupted(project_id=alpha.project_id) == 1
        observed = web.operation(operation["id"])
        assert observed["status"] == "uncertain" and observed["reason"] == "owner_dead"
        assert web.pending_domains(actions=("start",)) == []
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=5)


def test_discovery_restore_rename_archive_delete_preserves_project_identity(tmp_path):
    """@brief Name recycling cannot transfer a worker or its immutable queued request."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = profiles.create("alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    request = web.enqueue(admin["id"], "alpha", "start", "7", "renamed-request")

    class Child:
        """@brief Nonblocking process-boundary fake for identity discovery events."""
        def __init__(self):
            self.code = None
            self.stopped = False
        def poll(self):
            return self.code
        def request_stop(self):
            self.stopped = True
        def kill(self):
            self.code = 124
        def close(self):
            pass

    clock = [0.0]
    supervisor = Supervisor(profiles, web, spawn=lambda *args: Child(), clock=lambda: clock[0])
    supervisor.tick()
    first = supervisor.children[alpha.project_id]
    configuration = supervisor.children["configuration"]
    profiles.rename("alpha", "renamed")
    replacement = profiles.create("alpha")
    supervisor.tick()
    assert first.stopped and alpha.project_id in supervisor.retiring
    assert replacement.project_id in supervisor.children
    assert web.operation(request["id"])["project"] == "renamed"
    assert web.operation(request["id"])["project_id"] == alpha.project_id
    clock[0] = 3
    supervisor.tick()
    assert supervisor.children[alpha.project_id] is not first
    restored = profiles.load("renamed")
    restored.archived = True
    profiles.save(restored)
    supervisor.tick()
    clock[0] = 6
    supervisor.tick()
    assert alpha.project_id not in supervisor.children
    restored.archived = False
    profiles.save(restored)
    supervisor.tick()
    assert alpha.project_id in supervisor.children
    profiles.delete("renamed")
    supervisor.tick()
    clock[0] = 9
    supervisor.tick()
    assert alpha.project_id not in supervisor.children
    assert supervisor.children["configuration"] is configuration
    assert supervisor.children[replacement.project_id].poll() is None


def test_project_cadence_backoff_and_quiet_hours_keep_explicit_commands(tmp_path, monkeypatch):
    """@brief The independent scheduler backs off after completion and keeps quiet Start."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    state = StateStore(alpha.store_root)
    state.resume()
    web = WebStore(profiles.home / "web.db")
    clock, quiet = [0.0], [False]
    polls = []

    class Child:
        """@brief A bounded, controllable external poll completion."""
        code = None
        def poll(self):
            return self.code
        def kill(self):
            pass
        def close(self):
            pass

    def spawn(argv, environment):
        role = argv[argv.index("--role") + 1]
        if role == "poll":
            polls.append(clock[0])
        return Child()

    monkeypatch.setattr("adore.web.supervisor.in_quiet_hours", lambda _: quiet[0])
    worker = ProjectWorker(profiles, web, alpha.project_id, spawn=spawn, clock=lambda: clock[0])
    worker.owner = web.register_worker("project", project_id=alpha.project_id)
    worker.tick()
    worker.children["poll"].code = 1
    clock[0] = 1
    worker.tick()
    assert worker.next_poll == 3 and polls == [0]
    quiet[0] = True
    clock[0] = 3
    admin = web.authenticate("admin", "admin")
    web.enqueue(admin["id"], "alpha", "start", "7", "quiet-start")
    worker.tick()
    assert "command" in worker.children and "poll" not in worker.children
    assert worker.next_poll == 5
    quiet[0] = False
    clock[0] = 5
    worker.tick()
    assert polls == [0, 5]
    before = dict(worker.children)
    profiles.config_path("alpha").write_text("[polling", encoding="utf-8")
    with pytest.raises(ValueError):
        worker.tick()
    assert worker.children == before


def test_linux_session_gate_and_owned_group_kill(monkeypatch):
    """@brief The Linux adapter releases argv only after creating a private session."""
    import io

    import adore.web.processes as module

    calls = []

    class Pipe(io.BytesIO):
        """@brief Retain the launch gate observation after handle cleanup."""
        def close(self):
            pass

    process = SimpleNamespace(pid=12345, stdin=Pipe(), stdout=io.BytesIO(b"7\n"),
        stderr=io.BufferedReader(io.BytesIO(b"")), returncode=None,
        poll=lambda: 7, wait=lambda **kwargs: 7)

    def spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        assert process.stdin.getvalue() == b""
        return process

    # Isolate the OS adapter instead of mutating global os.name on Windows.
    adapter = SimpleNamespace(**{key: getattr(os, key) for key in dir(os)})
    adapter.name = "posix"
    adapter.killpg = lambda pid, sig: calls.append((pid, sig))
    adapter.P_PID, adapter.WEXITED, adapter.WNOHANG, adapter.WNOWAIT = 1, 2, 4, 8
    adapter.waitid = lambda *args: SimpleNamespace(si_pid=12345)
    monkeypatch.setattr(module, "os", adapter)
    monkeypatch.setattr(module, "signal", SimpleNamespace(SIGKILL=9))
    birth_probe = module.process_birth
    monkeypatch.setattr(module, "process_birth", lambda pid:
                        "owned-birth" if pid == 12345 else birth_probe(pid))
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    child = ProcessTree(["python3", "-m", "adore"], dict(os.environ))
    try:
        assert calls[0][1]["start_new_session"] is True
        assert process.stdin.getvalue() == b"G"
        eventually(lambda: child.poll() is not None)
        assert child.poll() == 7
        child.kill()
        assert calls[-1][0] == 12345
        process.returncode = 7
        count = len(calls)
        child.kill()
        assert len(calls) == count, "a reaped/recycled PGID must never be signalled"
    finally:
        child.close()


def test_lost_ancestor_fences_conductor_state_write(tmp_path, monkeypatch):
    """@brief Parent loss cannot resume a bound engine write after a blocked executor."""
    from adore.web.worker_context import WorkerContext

    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    web = WebStore(profiles.home / "web.db")
    owner = web.register_worker("project", project_id=alpha.project_id)
    engine, *_ = offline_engine(profiles, "alpha")
    WorkerContext(web, owner, 0, 0).bind_engine(engine)
    monkeypatch.setenv("ADORE_WORKER_ANCESTRY", '[{"pid":1,"birth":"previous-incarnation"}]')
    with pytest.raises(OwnershipError, match="ancestor"):
        engine.store.save(RunState("fenced", 7))
    assert not engine.store.exists("fenced")


def test_process_capture_is_bounded_under_large_output():
    """@brief Long-lived worker output cannot grow memory/disk without bound."""
    child = ProcessTree([sys.executable, "-c", "print('x'*3000000)"], dict(os.environ))
    try:
        eventually(lambda: child.poll() is not None)
        assert child.poll() == 0
        assert len(child.tail(3000000).encode()) <= 65536
        with pytest.raises(ValueError):
            child.tail(-1)
    finally:
        stop_trees([child])


def test_configuration_worker_reports_busy_during_command(tmp_path, monkeypatch):
    """@brief Supervisor aggregation can distinguish blocked configuration from idle."""
    import adore.web.supervisor as module

    profiles = ProfileStore(tmp_path / "home")
    project(profiles, "alpha")
    web = WebStore(profiles.home / "web.db")
    admin = web.authenticate("admin", "admin")
    web.enqueue(admin["id"], "alpha", "pause", "", "pause-once")
    entered, release, stop = Event(), Event(), Event()
    errors = []

    def runner(argv, environment):
        entered.set()
        assert release.wait(5)
        return 0

    def factory(profiles, web, **kwargs):
        return commands.CommandWorker(profiles, web, runner=runner, **kwargs)

    monkeypatch.setattr(module, "CommandWorker", factory)
    def run():
        try:
            module.configuration_loop(profiles, web, stop)
        except BaseException as exc:
            errors.append(exc)
    thread = Thread(target=run)
    thread.start()
    try:
        assert entered.wait(5)
        assert any(row["activity"] == "busy" for row in web.worker_heartbeats(
            role="configuration"))
    finally:
        stop.set()
        release.set()
        thread.join(5)
    assert not errors and not thread.is_alive()


@pytest.mark.parametrize("crash", [False, True])
def test_transient_command_drains_cancel_or_recovers_after_death(tmp_path, crash):
    """@brief A live scheduler cannot retain a dead command's Retry/Cancel claims."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    state = StateStore(alpha.store_root)
    state.save(RunState("job-42", 42, lifecycle="failed", outcome="test failure"))
    web = WebStore(profiles.home / "web.db")
    project_owner = web.register_worker("project", project_id=alpha.project_id)
    admin = web.authenticate("admin", "admin")
    retry = web.enqueue(admin["id"], "alpha", "retry", "job-42", "retry-once")
    release, entered = tmp_path / "release", tmp_path / "entered"
    child = ProcessTree([sys.executable, "-m", "tests.supervisor_helper", "command",
                         str(profiles.home), alpha.project_id, str(release), str(entered)],
                        dict(os.environ))
    try:
        eventually(entered.exists)
        cancel = web.enqueue(admin["id"], "alpha", "cancel", "job-42", "cancel-once")
        eventually(lambda: web.operation(cancel["id"])["status"] == "running")
        eventually(lambda: state.cancel_requested("job-42"))
        if crash:
            child.kill()
        else:
            release.touch()
        eventually(lambda: child.poll() is not None)
        web.assert_worker(project_owner)
        if crash:
            assert web.recover_interrupted(project_id=alpha.project_id, role="command") == 2
            assert web.operation(retry["id"])["status"] == "uncertain"
            assert web.operation(cancel["id"])["status"] == "uncertain"
        else:
            assert child.poll() == 0, child.tail()
            assert web.operation(cancel["id"])["status"] == "succeeded"
            assert web.operation(retry["id"])["status"] == "failed"
            assert not web.worker_heartbeats(role="command", project_id=alpha.project_id)
    finally:
        stop_trees([child])


def test_command_ownership_cannot_poll_or_consume_configuration(tmp_path):
    """@brief A transient execution command is not a project/configuration scheduler."""
    profiles = ProfileStore(tmp_path / "home")
    alpha = project(profiles, "alpha")
    web = WebStore(profiles.home / "web.db")
    owner = web.register_worker("command", project_id=alpha.project_id)
    with pytest.raises(OwnershipError):
        web.authorize_worker(owner)
    with pytest.raises(OwnershipError):
        web.claim_next(owner, domain="configuration_project")


def test_wrapper_root_crash_does_not_leave_live_descendants(tmp_path):
    """@brief Root-only death drains the original scope before Linux reaps its leader."""
    marker = tmp_path / "descendants.json"
    script = (
        "import json,os,sys,subprocess,time; from pathlib import Path; "
        "from adore.web.ownership import process_birth; "
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
        "Path(sys.argv[1]).write_text(json.dumps([[os.getpid(),process_birth(os.getpid())],"
        "[p.pid,process_birth(p.pid)]]));time.sleep(60)"
    )
    child = ProcessTree([sys.executable, "-c", script, str(marker)], dict(os.environ))
    try:
        eventually(marker.exists)
        identities = json.loads(marker.read_text())
        # Kill only the wrapper, bypassing both its finally and ProcessTree.kill.
        child.process.kill()
        eventually(lambda: child.poll() is not None)
        child.kill()
        eventually(lambda: all(process_birth(pid) != birth for pid, birth in identities))
    finally:
        stop_trees([child])


def test_shutdown_attempts_every_scope_despite_control_failure():
    """@brief One unconfirmed kill/drain retains evidence without skipping other trees."""
    calls = []

    class Child:
        """@brief Fail one scope at each boundary and observe all subsequent attempts."""
        def __init__(self, name, fail=False):
            self.name, self.fail = name, fail
            self.process = SimpleNamespace(wait=self.wait)
        def action(self, name):
            calls.append((self.name, name))
            if self.fail:
                raise OSError("unconfirmed scope")
        def request_stop(self):
            self.action("stop")
        def kill(self):
            self.action("kill")
        def wait(self, **kwargs):
            self.action("wait")
        def close(self):
            self.action("close")

    with pytest.raises(OwnershipError, match="shutdown could not be confirmed"):
        stop_trees([Child("A", fail=True), Child("B")], grace=0)
    assert calls == [(name, phase) for phase in ("stop", "kill", "wait", "close")
                     for name in ("A", "B")]


def test_failed_project_scope_cleanup_preserves_other_worker_processes(tmp_path):
    """@brief A cleanup refusal quarantines A instead of restarting B/configuration."""
    profiles = ProfileStore(tmp_path / "home")
    alpha, beta = profiles.create("alpha"), profiles.create("beta")
    web = WebStore(profiles.home / "web.db")

    class Child:
        """@brief Scope-control failure fake with independently visible process identity."""
        code = None
        def poll(self):
            return self.code
        def kill(self):
            raise OSError("scope unavailable")
        def close(self):
            raise AssertionError("kill was not confirmed")

    supervisor = Supervisor(profiles, web, spawn=lambda *args: Child())
    supervisor.tick()
    before = dict(supervisor.children)
    supervisor.children[alpha.project_id].code = 1
    supervisor.tick()
    assert alpha.project_id in supervisor.retiring
    assert supervisor.children[beta.project_id] is before[beta.project_id]
    assert supervisor.children["configuration"] is before["configuration"]


# END OF FILE
