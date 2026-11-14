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
@file test_run_concurrency.py
@brief Offline project admission and owned-run concurrency contracts.
@details Uses only injected offline fakes; no forge, git, container or model is
         contacted. The tests focus on observable contracts and fail-closed
         trust boundaries rather than private implementation structure.
"""

from __future__ import annotations

# IMPORTS
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import multiprocessing
from threading import Event, Thread

from adore.orchestrator import LockHeldError
from adore.state import StateError, StateStore
import pytest

from tests.test_orchestrator import direct_edit, direct_engine, make_engine, make_run


@pytest.fixture(autouse=True)
def offline_probe(monkeypatch):
    """@brief Concurrency proof never invokes target repository or host commands."""
    from adore.orchestrator import Orchestrator
    monkeypatch.setattr(Orchestrator, '_probe_repository_payload', lambda self: None)


# PUBLIC API
def test_admission_releases_project_lock_before_conduction(tmp_path, monkeypatch):
    """@brief A second admission proceeds while another run executes."""
    first, forge, *_ = make_engine(tmp_path)
    first.config.polling.max_concurrent_runs = 2
    forge.ticket.labels = ['P1', 'agent-ready']
    second, other, *_ = make_engine(tmp_path)
    second.config.polling.max_concurrent_runs = 2
    other.ticket = replace(forge.ticket, iid=8, labels=['P1', 'agent-ready'])
    entered, release = Event(), Event()
    errors = []
    def conduct(run_id, **kwargs):
        entered.set()
        assert release.wait(10)
        return True
    monkeypatch.setattr(first, 'conduct_run', conduct)
    def poll():
        try:
            first.poll_once(ticket_iid=7)
        except BaseException as exc:
            errors.append(exc)
    worker = Thread(target=poll)
    worker.start()
    try:
        assert entered.wait(5)
        result = second.poll_once(ticket_iid=8, admit_only=True)
        assert result['picked'] == 8
        assert len(second.store.list_runs()) == 2
    finally:
        release.set()
        worker.join(10)
    assert not errors


def test_admission_only_is_atomic_and_pause_preserving(tmp_path):
    """@brief Explicit admission preserves pause and enforces capacity and uniqueness."""
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    engine.store.pause()
    assert engine.poll_once(admit_only=True)['paused']
    result = engine.poll_once(ticket_iid=7, admit_only=True)
    assert result['picked'] == 7
    assert engine.store.is_paused()
    forge.ticket = replace(forge.ticket, iid=8, labels=['P1', 'agent-ready'])
    assert engine.poll_once(ticket_iid=8, admit_only=True)['at_capacity']
    assert len(engine.store.list_runs()) == 1


def test_foreign_run_lock_protects_reconciliation_and_cancel(tmp_path):
    """@brief A live conductor cannot be cancelled or diagnosed stale by a peer."""
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    peer, *_ = make_engine(tmp_path)
    with engine.store.run_lock(run.run_id):
        assert peer.poll_once()['picked'] is None
        assert peer.store.load(run.run_id).lifecycle == 'working'
        assert peer.cancel(run.run_id)
        assert peer.store.cancel_requested(run.run_id)
        assert peer.store.load(run.run_id).lifecycle == 'working'
    assert peer.cancel(run.run_id)
    assert peer.store.load(run.run_id).lifecycle == 'cancelled'


def test_durable_foreign_owner_skips_all_reconciliation(tmp_path):
    """@brief Unknown/live durable ownership prevents effects even without a local lock."""
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    run.updated_at = '2020-01-01T00:00:00+00:00'
    engine.store.save(run)
    engine.run_available = lambda run_id: False
    engine.poll_once()
    assert engine.store.load(run.run_id).lifecycle == 'working'


def test_retry_at_capacity_preserves_failed_state(tmp_path):
    """@brief Retry cannot bypass another execution reservation."""
    engine, forge, *_ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = 'failed'
    engine.store.save(run)
    other = replace(run, run_id=run.run_id + '-other', ticket_iid=8, lifecycle='working')
    engine.store.save(other)
    assert not engine.retry(run.run_id)
    assert engine.store.load(run.run_id).lifecycle == 'failed'


def test_owned_run_refuses_foreign_target_and_changed_config(tmp_path):
    """@brief Single-run execution checks target and exact configuration before effects."""
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    engine.owned_run_id = run.run_id + '-other'
    with pytest.raises(LockHeldError):
        engine.conduct_run(run.run_id)
    engine.owned_run_id = run.run_id
    with pytest.raises(ValueError, match='revision'):
        engine.conduct_run(run.run_id, config_revision='0' * 64)


def test_run_locks_are_exclusive_reentrant_and_crash_released(tmp_path):
    """@brief Independent stores cannot mutate the same run at once."""
    first, second = StateStore(tmp_path), StateStore(tmp_path)
    with (first.run_lock('run-7'), first.run_lock('run-7'),
          pytest.raises(LockHeldError), second.run_lock('run-7')):
        pytest.fail('foreign lock admitted')
    with second.run_lock('run-7'):
        pass
    with pytest.raises(StateError), first.run_lock('../escape'):
        pytest.fail('invalid run admitted')


def test_two_direct_executions_advance_without_cross_run_mutation(tmp_path, monkeypatch):
    """@brief Independent conductors finish real fake-agent runs while a peer is blocked."""
    import adore.orchestrator as module
    one, two = tmp_path / 'one', tmp_path / 'two'
    one.mkdir()
    two.mkdir()
    entered, release = Event(), Event()
    first, forge, worktrees, _, executor, _ = direct_engine(one, monkeypatch)
    second, other, other_worktrees, _, other_executor, _ = direct_engine(two, monkeypatch)
    first.config.polling.max_concurrent_runs = second.config.polling.max_concurrent_runs = 2
    second.store = StateStore(first.store.root)
    second.config.state.store_root = str(first.store.root)
    other.ticket = replace(other.ticket, iid=8)
    edit = direct_edit(worktrees)
    def blocked(root):
        entered.set()
        assert release.wait(10)
        return edit(root)
    executor.attempts.append(blocked)
    other_executor.attempts.append(direct_edit(other_worktrees))
    monkeypatch.setattr(module, '_STALE_WORKING_GRACE_SECONDS', 0)
    errors = []
    def run():
        try:
            first.poll_once(ticket_iid=7)
        except BaseException as exc:
            errors.append(exc)
    worker = Thread(target=run)
    worker.start()
    try:
        assert entered.wait(5)
        before = (first.store.run_dir(first._run_id(7)) / 'state.json').read_bytes()
        assert second.poll_once(ticket_iid=8)['picked'] == 8
        assert second.store.load(second._run_id(8)).lifecycle == 'awaiting-approval'
        assert (first.store.run_dir(first._run_id(7)) / 'state.json').read_bytes() == before
    finally:
        release.set()
        worker.join(10)
    assert not errors and not worker.is_alive()
    assert first.store.load(first._run_id(7)).lifecycle == 'awaiting-approval'
    assert not any('STALE' in run.outcome for run in first.store.list_runs())
    assert len(executor.prompts) == len(other_executor.prompts) == 1


@pytest.mark.parametrize('trigger', ['clarification', 'review', 'approval', 'restart'])
def test_all_resume_boundaries_keep_capacity(tmp_path, trigger):
    """@brief Waiting jobs and destructive restart do not bypass a busy project."""
    engine, forge, worktrees, containers, executor = make_engine(tmp_path)
    run = make_run(engine)
    other = replace(run, run_id=run.run_id + '-other', ticket_iid=8)
    engine.store.save(other)
    if trigger == 'clarification':
        run.lifecycle = 'parked-clarification'
        run.parked_at = run.updated_at
        run.parked_polls = 1
        forge.ticket.labels = [engine.config.labels.lifecycle.clarify,
                               engine.config.labels.lifecycle.answered]
        forge.ticket_comments[1000] = 'Use the reviewed implementation.'
    elif trigger == 'review':
        run.lifecycle = 'in-review'
        run.stage = 'done'
        run.mr_iid = forge.mr.iid
        forge.mr.labels = [engine.config.review.revise_label]
    elif trigger == 'approval':
        run.lifecycle = 'awaiting-approval'
        run.stage = 'done'
        run.candidate_fingerprint = 'd' * 64
        run.candidate_base_ref = 'a' * 40
        run.approval_presented_at = run.updated_at
        run.approval_label_removed = True
        forge.ticket.labels = [engine.config.delivery.approval_label]
    else:
        run.lifecycle = 'failed'
    engine.store.save(run)
    before = (engine.store.run_dir(run.run_id) / 'state.json').read_bytes()
    if trigger == 'restart':
        result = engine.restart(run.run_id, sha256(before).hexdigest())
        assert result['at_capacity'] and not worktrees.removed
        assert (engine.store.run_dir(run.run_id) / 'state.json').read_bytes() == before
    else:
        engine.poll_once()
        assert engine.store.load(run.run_id).lifecycle == run.lifecycle
    assert not executor.prompts


def test_queued_time_does_not_consume_active_budget(tmp_path, monkeypatch):
    """@brief First conduction starts its active clock after the admission wait."""
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    result = engine.poll_once(ticket_iid=7, admit_only=True)
    run_id = result['run_id']
    path = engine.store.run_dir(run_id) / 'state.json'
    value = json.loads(path.read_text())
    old = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    value.update(created_at=old, updated_at=old, active_started_at=old)
    path.write_text(json.dumps(value))
    observed = []
    def finish(run, ticket):
        observed.append(run.active_work_seconds(datetime.now(UTC).isoformat()))
        run.lifecycle = 'awaiting-approval'
        engine.store.save(run)
    monkeypatch.setattr(engine, '_conduct', finish)
    assert engine.conduct_run(run_id, config_revision=engine.configuration_revision())
    assert observed[0] < 5
    assert engine.store.load(run_id).active_work_seconds(datetime.now(UTC).isoformat()) < 5


def _hold_run_lock(root, entered):
    """@brief Child process holds only an isolated test-store lifecycle lock."""
    with StateStore(root).run_lock('run-7'):
        entered.set()
        Event().wait(30)


def test_process_death_releases_kernel_run_lock(tmp_path):
    """@brief Kernel ownership survives stale metadata and ends with the actual process."""
    context = multiprocessing.get_context('spawn')
    entered = context.Event()
    process = context.Process(target=_hold_run_lock, args=(str(tmp_path), entered))
    process.start()
    try:
        assert entered.wait(10)
        assert StateStore(tmp_path).run_locked('run-7')
    finally:
        process.terminate()
        process.join(10)
    assert not process.is_alive()
    with StateStore(tmp_path).run_lock('run-7'):
        pass


def test_cli_conduct_targets_one_run_and_refuses_changed_revision(tmp_path, monkeypatch):
    """@brief CLI dispatch builds one engine and never polls or claims a different ticket."""
    from adore import cli
    engine, forge, *_ = make_engine(tmp_path)
    engine.config.polling.max_concurrent_runs = 2
    forge.ticket.labels = ['P1', 'agent-ready']
    run_id = engine.poll_once(ticket_iid=7, admit_only=True)['run_id']
    run = engine.store.load(run_id)
    other = replace(run, run_id=run.run_id + '-other', ticket_iid=8,
                    execution_pending=False)
    engine.store.save(other)
    before = (engine.store.run_dir(other.run_id) / 'state.json').read_bytes()
    monkeypatch.setattr(cli, '_engine', lambda args: (engine.config, engine))
    conducted = []
    monkeypatch.setattr(engine, '_conduct', lambda run, ticket: conducted.append(run.run_id))
    revision = engine.configuration_revision()
    assert cli.main(['conduct', run.run_id, '--config-revision', revision]) == 0
    assert conducted == [run.run_id]
    assert (engine.store.run_dir(other.run_id) / 'state.json').read_bytes() == before
    assert cli.main(['conduct', run.run_id, '--config-revision', '0' * 64]) == 1
    assert cli.main(['conduct', 'missing', '--config-revision', revision]) == 1
    assert conducted == [run.run_id]


def test_corrupt_state_blocks_atomic_admission(tmp_path):
    """@brief Corrupt persisted capacity evidence cannot be treated as a free slot."""
    engine, forge, *_ = make_engine(tmp_path)
    run = make_run(engine)
    (engine.store.run_dir(run.run_id) / 'state.json').write_text('{}')
    forge.ticket = replace(forge.ticket, iid=8, labels=['P1', 'agent-ready'])
    with pytest.raises(StateError, match='capacity'):
        engine.poll_once(ticket_iid=8, admit_only=True)
    assert not engine.store.exists(engine._run_id(8))


def test_cleanup_keeps_execution_slot_until_backend_stop_finishes(tmp_path, monkeypatch):
    """@brief Waiting approval frees executor capacity only after its cleanup boundary."""
    one, two = tmp_path / 'one', tmp_path / 'two'
    one.mkdir()
    two.mkdir()
    first, forge, worktrees, _, executor, _ = direct_engine(one, monkeypatch)
    second, other, *_ = make_engine(two)
    second.store = StateStore(first.store.root)
    second.config.state.store_root = str(first.store.root)
    other.ticket = replace(other.ticket, iid=8, labels=['P1', 'agent-ready'])
    executor.attempts.append(direct_edit(worktrees))
    entered, release = Event(), Event()
    errors = []
    def stop(*args, **kwargs):
        entered.set()
        assert release.wait(10)
    monkeypatch.setattr(first.backend, 'stop', stop)
    def run():
        try:
            first.poll_once(ticket_iid=7)
        except BaseException as exc:
            errors.append(exc)
    worker = Thread(target=run)
    worker.start()
    try:
        assert entered.wait(5)
        assert first.store.load(first._run_id(7)).lifecycle == 'awaiting-approval'
        assert second.poll_once(ticket_iid=8, admit_only=True)['at_capacity']
    finally:
        release.set()
        worker.join(10)
    assert not errors
    second.forge.get_ticket = lambda iid: forge.ticket if iid == 7 else other.ticket
    assert second.poll_once(ticket_iid=8, admit_only=True)['picked'] == 8


def test_reduced_limit_preserves_admitted_jobs_and_blocks_new_work(tmp_path, monkeypatch):
    """@brief A lower limit prevents only later execution reservations."""
    engine, forge, *_ = make_engine(tmp_path)
    engine.config.polling.max_concurrent_runs = 2
    forge.ticket.labels = ['P1', 'agent-ready']
    result = engine.poll_once(ticket_iid=7, admit_only=True)
    called = []
    def conduct(run, ticket):
        engine.config.polling.max_concurrent_runs = 1
        called.append(run.run_id)
    monkeypatch.setattr(engine, '_conduct', conduct)
    assert engine.conduct_run(result['run_id'])
    forge.ticket = replace(forge.ticket, iid=8, labels=['P1', 'agent-ready'])
    assert engine.poll_once(ticket_iid=8, admit_only=True)['at_capacity']
    assert called == [result['run_id']]
    assert engine.store.load(result['run_id']).lifecycle == 'working'


def test_dispatch_evidence_refuses_corrupt_input_and_uncertain_replay(tmp_path, monkeypatch):
    """@brief Durable started evidence prevents replay even if the audit journal was torn."""
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    result = engine.poll_once(ticket_iid=7, admit_only=True)
    run_id = result['run_id']
    path = engine.store.run_dir(run_id) / 'dispatch.json'
    original = path.read_bytes()
    path.write_text('{}')
    with pytest.raises(StateError, match='dispatch'):
        engine.conduct_run(run_id)
    path.write_bytes(original)
    calls = []
    monkeypatch.setattr(engine, '_conduct', lambda run, ticket: calls.append(run.run_id))
    assert engine.conduct_run(run_id)
    (engine.store.run_dir(run_id) / 'journal.jsonl').write_text('{torn')
    assert not engine.conduct_run(run_id)
    assert calls == [run_id]
    assert engine.store.load(run_id).outcome.startswith('STALE_WORKING:')


def test_initial_allocation_reserves_capacity_without_holding_admission(tmp_path, monkeypatch):
    """@brief An uninitialized reservation is visible while Git allocation blocks."""
    engine, forge, trees, *_ = make_engine(tmp_path)
    peer, other, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    other.ticket = replace(forge.ticket, iid=8)
    entered, release = Event(), Event()
    create = trees.create
    results, errors = [], []
    def allocate(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return create(*args, **kwargs)
    monkeypatch.setattr(trees, 'create', allocate)
    def start():
        try:
            results.append(engine.poll_once(ticket_iid=7, admit_only=True))
        except BaseException as exc:
            errors.append(exc)
    worker = Thread(target=start)
    worker.start()
    try:
        assert entered.wait(5)
        assert not engine.store.list_runs()
        assert peer.poll_once(ticket_iid=8, admit_only=True)['at_capacity']
        assert not peer.store.lock_path.exists()
    finally:
        release.set()
        worker.join(10)
    assert not errors and results[0]['picked'] == 7


def test_retry_cli_reports_capacity_without_mutating_failed_job(tmp_path, monkeypatch, capsys):
    """@brief The closed CLI result explains the actual reservation refusal."""
    from adore import cli
    from adore.start_result import read_retry_result
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = 'failed'
    engine.store.save(run)
    engine.store.save(replace(run, run_id=run.run_id + '-other', lifecycle='working'))
    monkeypatch.setattr(cli, '_engine', lambda args: (engine.config, engine))
    monkeypatch.setattr(cli, '_store', lambda config: engine.store)
    assert cli.main(['retry', run.run_id]) == 1
    reason = read_retry_result(capsys.readouterr().out, run_id=run.run_id, exit_code=1)
    assert reason == 'at_capacity'
    assert engine.store.load(run.run_id).lifecycle == 'failed'


def _conduct_in_process(root, iid, entered, release, results):
    """@brief Run the ordinary conductor in a fresh offline process with owned fakes."""
    from pathlib import Path

    import adore.orchestrator as module

    from tests.test_orchestrator import direct_edit, direct_engine
    root = Path(root)
    with pytest.MonkeyPatch.context() as patch:
        engine, forge, trees, _, executor, _ = direct_engine(root / str(iid), patch)
        engine.store = StateStore(root / 'state')
        engine.config.state.store_root = str(engine.store.root)
        engine.config.polling.max_concurrent_runs = 2
        forge.ticket = replace(forge.ticket, iid=iid)
        patch.setattr(module, '_STALE_WORKING_GRACE_SECONDS', 0)
        edit = direct_edit(trees)
        def attempt(work):
            if iid == 7:
                entered.set()
                assert release.wait(15)
            return edit(work)
        executor.attempts.append(attempt)
        try:
            result = engine.poll_once(ticket_iid=iid)
            run = engine.store.load(result['run_id'])
            results.put((iid, run.lifecycle, run.outcome))
        except BaseException as exc:
            results.put((iid, 'error', type(exc).__name__ + ': ' + str(exc)))


def test_two_processes_conduct_one_project_without_stale_diagnosis(tmp_path):
    """@brief Real process isolation keeps two bounded fake-agent executions independent."""
    context = multiprocessing.get_context('spawn')
    entered, release, results = context.Event(), context.Event(), context.Queue()
    for iid in (7, 8):
        (tmp_path / str(iid)).mkdir()
    first = context.Process(target=_conduct_in_process,
                            args=(str(tmp_path), 7, entered, release, results))
    second = context.Process(target=_conduct_in_process,
                             args=(str(tmp_path), 8, entered, release, results))
    first.start()
    try:
        assert entered.wait(10)
        second.start()
        observed = results.get(timeout=10)
        assert observed[:2] == (8, 'awaiting-approval'), observed
        assert StateStore(tmp_path / 'state').load('github-owner-repo-7').lifecycle == 'working'
        release.set()
        observed = results.get(timeout=10)
        assert observed[:2] == (7, 'awaiting-approval'), observed
        first.join(10)
        second.join(10)
        assert first.exitcode == second.exitcode == 0
    finally:
        release.set()
        for process in (first, second):
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(10)
        results.close()


def test_cleanup_skips_foreign_run_and_retains_ownership_through_effects(tmp_path, monkeypatch):
    """@brief Ordinary cleanup cannot remove a busy run or race a fresh reset."""
    engine, _, _, containers, _ = make_engine(tmp_path)
    peer, *_ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle = 'done'
    engine.store.save(run)
    with peer.store.run_lock(run.run_id):
        engine.cleanup()
    assert not containers.removed
    observed = []
    def remove(name, *args, **kwargs):
        assert name == run.container
        with pytest.raises(LockHeldError):
            peer.reset(run.run_id, 'build')
        observed.append('exclusive cleanup')
        return {}
    monkeypatch.setattr(containers, 'release_owned', remove)
    engine.cleanup()
    assert observed == ['exclusive cleanup']
    assert peer.reset(run.run_id, 'build')


def test_uncertain_publication_is_not_replayed_by_later_polls(tmp_path, monkeypatch):
    """@brief An orphaned publisher remains failed until explicit operator recovery."""
    engine, _, _, _, executor = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle, run.stage = 'publishing', 'done'
    engine.store.save(run)
    engine.config.delivery.publish_checkpoints = True
    def refuse(*args, **kwargs):
        pytest.fail('uncertain publication must not repeat remote checkpoint effects')
    monkeypatch.setattr(engine, '_push_checkpoint', refuse)
    engine.poll_once()
    assert engine.store.load(run.run_id).outcome.startswith('STALE_PUBLISHING:')
    engine.poll_once()
    assert not executor.prompts


def test_manual_and_automatic_admission_keep_ticket_unique_during_initialization(
    tmp_path, monkeypatch,
):
    """@brief Automatic pickup cannot duplicate an explicit Start before state is saved."""
    engine, forge, trees, *_ = make_engine(tmp_path)
    peer, other, *_ = make_engine(tmp_path)
    engine.config.polling.max_concurrent_runs = peer.config.polling.max_concurrent_runs = 2
    forge.ticket.labels = other.ticket.labels = ['P1', 'agent-ready']
    entered, release = Event(), Event()
    create, errors = trees.create, []
    def allocate(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return create(*args, **kwargs)
    monkeypatch.setattr(trees, 'create', allocate)
    def start():
        try:
            engine.poll_once(ticket_iid=7, admit_only=True)
        except BaseException as exc:
            errors.append(exc)
    worker = Thread(target=start)
    worker.start()
    try:
        assert entered.wait(5)
        with pytest.raises(LockHeldError):
            peer.poll_once(admit_only=True)
    finally:
        release.set()
        worker.join(10)
    assert not errors and len(engine.store.list_runs()) == 1


@pytest.mark.parametrize('content', [
    '[polling]\nmax_concurrent_runs = true\n',
    '[polling]\nmax_concurrent_runs = 0\n',
    '[polling\nbroken',
])
def test_invalid_current_capacity_refuses_admission(tmp_path, content):
    """@brief Human configuration corruption cannot authorize an executor reservation."""
    engine, forge, _, _, executor = make_engine(tmp_path)
    path = tmp_path / 'config.toml'
    path.write_text(content)
    engine.config.source_path = path
    forge.ticket.labels = ['P1', 'agent-ready']
    with pytest.raises(StateError, match='capacity'):
        engine.poll_once(ticket_iid=7, admit_only=True)
    assert not engine.store.list_runs() and not executor.prompts


@pytest.mark.parametrize('raw', [
    None, '{}', '{broken',
    '{"schema": true, "config_revision": "' + 'a' * 64 + '", "status": "queued"}',
    '{"schema": 2, "config_revision": "' + 'a' * 64 + '", "status": "queued"}',
    '{"schema": 1, "config_revision": 42, "status": "queued"}',
    '{"schema": 1, "config_revision": "bad", "status": "queued"}',
    '{"schema": 1, "config_revision": "' + 'a' * 64 + '", "status": "unknown"}',
    '{"schema": 1, "config_revision": "' + 'a' * 64 + '", "status": []}',
    '{"schema": 1, "schema": 1, "config_revision": "' + 'a' * 64 + '", "status": "queued"}',
    '[' * 1100 + ']' * 1100,
    'x' * 4097,
])
def test_corrupt_dispatch_never_grants_initial_execution(tmp_path, monkeypatch, raw):
    """@brief Current persisted dispatch evidence fails closed at every parsing boundary."""
    engine, _, _, _, executor = make_engine(tmp_path)
    run = make_run(engine)
    engine.store.save_dispatch(run.run_id, engine.configuration_revision())
    path = engine.store.run_dir(run.run_id) / 'dispatch.json'
    if raw is None:
        path.unlink()
    else:
        path.write_text(raw)
    before = (engine.store.run_dir(run.run_id) / 'state.json').read_bytes()
    with pytest.raises(StateError, match='dispatch'):
        engine.conduct_run(run.run_id)
    assert (engine.store.run_dir(run.run_id) / 'state.json').read_bytes() == before
    assert not executor.prompts


def test_unavailable_lifecycle_lock_storage_is_a_typed_refusal(tmp_path):
    """@brief An unusable configured state location cannot bypass lifecycle exclusion."""
    store = StateStore(tmp_path)
    store.locks_root.parent.mkdir(parents=True, exist_ok=True)
    store.locks_root.write_text('not a lock directory')
    with pytest.raises(StateError), store.run_lock('run-7'):
        pytest.fail('unavailable lifecycle lock was bypassed')


def test_admit_only_does_not_reconcile_an_existing_resumable_job(tmp_path, monkeypatch):
    """@brief Admission-only never observes or resumes another job's answer/revision."""
    engine, forge, *_ = make_engine(tmp_path)
    run = make_run(engine)
    run.lifecycle, run.parked_polls, run.parked_at = 'parked-clarification', 1, run.updated_at
    engine.store.save(run)
    before = (engine.store.run_dir(run.run_id) / 'state.json').read_bytes()
    ticket = replace(forge.ticket, iid=8, labels=['P1', 'agent-ready'])
    def get(iid):
        assert iid == 8, 'admission-only must not reconcile another job'
        return ticket
    monkeypatch.setattr(forge, 'get_ticket', get)
    result = engine.poll_once(ticket_iid=8, admit_only=True)
    assert result['picked'] == 8
    assert (engine.store.run_dir(run.run_id) / 'state.json').read_bytes() == before


def test_initial_queue_clock_is_zero_before_dispatch_and_after_cancel(tmp_path):
    """@brief Cancellation of an undispatched admission never freezes queue time as work."""
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    run_id = engine.poll_once(ticket_iid=7, admit_only=True)['run_id']
    path = engine.store.run_dir(run_id) / 'state.json'
    raw = json.loads(path.read_text())
    old = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    raw.update(created_at=old, updated_at=old, active_started_at=old)
    path.write_text(json.dumps(raw))
    assert engine.store.load(run_id).active_work_seconds(datetime.now(UTC).isoformat()) == 0
    assert engine.cancel(run_id)
    assert engine.store.load(run_id).active_work_seconds(datetime.now(UTC).isoformat()) == 0


def test_start_crash_cannot_restore_queued_time_to_retry_budget(tmp_path, monkeypatch):
    """@brief Clock activation is durable before the first claim effect may crash."""
    class SimulatedCrash(BaseException):
        pass
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    run_id = engine.poll_once(ticket_iid=7, admit_only=True)['run_id']
    path = engine.store.run_dir(run_id) / 'state.json'
    raw = json.loads(path.read_text())
    old = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    raw.update(created_at=old, updated_at=old, active_started_at=old)
    path.write_text(json.dumps(raw))
    def crash(*args):
        raise SimulatedCrash()
    monkeypatch.setattr(forge, 'remove_labels', crash)
    with pytest.raises(SimulatedCrash):
        engine.conduct_run(run_id)
    run = engine.store.load(run_id)
    assert run.active_work_seconds(datetime.now(UTC).isoformat()) < 5
    run.lifecycle = 'failed'
    engine.store.save(run)
    observed = []
    monkeypatch.setattr(engine, '_conduct', lambda run, ticket:
                        observed.append(run.active_work_seconds(datetime.now(UTC).isoformat())))
    assert engine.retry(run_id)
    assert observed[0] < 5


def test_bound_run_cancel_refuses_a_foreign_target_before_marker_fallback(tmp_path):
    """@brief A single-run conductor cannot request mutation of another run."""
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    other = replace(run, run_id=run.run_id + '-other', ticket_iid=8)
    engine.store.save(other)
    engine.owned_run_id = run.run_id
    with pytest.raises(LockHeldError):
        engine.cancel(other.run_id)
    assert not engine.store.cancel_requested(other.run_id)


def test_cli_cancel_reports_request_until_saved_stop(tmp_path, monkeypatch, capsys):
    """@brief Standalone CLI does not confirm a cancellation marker as an actual stop."""
    from adore import cli
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    monkeypatch.setattr(cli, '_engine', lambda args: (engine.config, engine))
    monkeypatch.setattr(cli, '_store', lambda config: engine.store)
    with StateStore(engine.store.root).run_lock(run.run_id):
        assert cli.main(['cancel', run.run_id]) == 0
    assert 'cancellation requested' in capsys.readouterr().out
    assert engine.store.load(run.run_id).lifecycle == 'working'
    assert cli.main(['cancel', run.run_id]) == 0
    assert capsys.readouterr().out.strip() == 'cancelled'


@pytest.mark.parametrize('change', [
    {'execution_pending': 1}, {'execution_pending': None},
    {'execution_pending': 'true'}, {'execution_pending': True, 'iterations': 1},
])
def test_pending_execution_clock_flag_refuses_corrupt_state(tmp_path, change):
    """@brief Corrupt pending authority cannot hide executor consumption."""
    engine, forge, *_ = make_engine(tmp_path)
    forge.ticket.labels = ['P1', 'agent-ready']
    run_id = engine.poll_once(ticket_iid=7, admit_only=True)['run_id']
    path = engine.store.run_dir(run_id) / 'state.json'
    raw = json.loads(path.read_text())
    raw.update(change)
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    with pytest.raises(StateError, match='pending'):
        engine.store.load(run_id)
    assert path.read_bytes() == before


def test_current_state_requires_pending_clock_field_without_repair(tmp_path):
    """@brief Earlier stored shapes are refused with the exact run directory to delete."""
    engine, *_ = make_engine(tmp_path)
    run = make_run(engine)
    path = engine.store.run_dir(run.run_id) / 'state.json'
    raw = json.loads(path.read_text())
    del raw['execution_pending']
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    with pytest.raises(StateError, match='execution_pending') as refused:
        engine.store.load(run.run_id)
    assert 'delete ' + str(path.parent) in str(refused.value)
    assert path.read_bytes() == before


def test_jobs_projection_freezes_pending_execution_budget(tmp_path):
    """@brief Jobs reads the pending clock from current state without dispatch/file inference."""
    from adore.web.jobs import read_job_budget, read_jobs

    from tests.test_web_jobs import _fixture, _state
    profiles, items, stores, _ = _fixture(tmp_path)
    _state(stores[0], 'same', execution_pending=True,
           active_started_at='2026-10-05T09:00:00+00:00')
    rows, _ = read_jobs(profiles, [items[0]])
    row = next(row for row in rows if row['run_id'] == 'same')
    budget = read_job_budget(profiles, items[0], 'same', row['state_revision'])
    assert budget['active_seconds'] == 0


@pytest.mark.parametrize('unrecorded_control', [False, True])
def test_cancel_native_admission_before_provision_requires_proven_absence(
    tmp_path, monkeypatch, unrecorded_control,
):
    """@brief A queued native job owns no process yet; unrecorded control still blocks cleanup."""
    from adore.isolation import IsolationError
    from adore.local_execution import LocalBackend

    from tests.test_local_execution import local_fixture
    config, context, _, controller, work = local_fixture(tmp_path, monkeypatch)
    engine, forge, trees, _, executor = make_engine(tmp_path)
    config.state.store_root = str(engine.store.root)
    config.delivery.publish_checkpoints = False
    engine.config = config
    engine.backend = LocalBackend(config, context=context, controller=controller)
    trees.repo_path = work
    trees.path_for = lambda run_id: work
    trees.create = lambda *args, **kwargs: work
    forge.ticket.labels = ['P1', config.labels.lifecycle.ready]
    run_id = engine.poll_once(ticket_iid=7, admit_only=True)['run_id']
    run = engine.store.load(run_id)
    assert run.execution['resource'] == {} and run.execution_pending
    if unrecorded_control:
        (engine.store.run_dir(run_id) / 'local-control').mkdir()
        with pytest.raises(IsolationError, match='unrecorded'):
            engine.cancel(run_id)
        assert engine.store.load(run_id).lifecycle == 'working'
        assert not trees.removed
    else:
        assert engine.cancel(run_id)
        assert engine.store.load(run_id).lifecycle == 'cancelled'
        assert trees.removed == [run_id]
    assert not executor.prompts and not controller.controlled
