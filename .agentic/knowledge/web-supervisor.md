<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local web supervisor and process trees

## Routing

Use for independent project/run pools, home ownership, gated child process trees,
parent loss and portable application Stop. Start at `web/supervisor.py` and
`web/processes.py`; focused proof is `tests/test_web_supervisor.py`. Operation
schema/authorization routes to web-interface.md and state locks to state-store.md.

## Purpose and boundaries

One supervisor owns each home. Project workers dispatch admission, scoped commands
and N run children independently. Configuration tasks and immediate controls run in a separate bounded consumer; see configuration-worker.md.
The conductor remains responsible for lifecycle transitions, budgets and publication.

## Public interface

`adore-web-worker --home`, `Supervisor.run_forever/tick`,
`ProjectWorker.run_forever/tick`, `ProcessTree` and `stop_trees`.
`assert_ancestry` validates bounded internal PID/birth transport before effects.

## Invariants

No project lock spans a job. Canonical polling.max_concurrent_runs governs each
project; no global one-job ceiling exists. Linux cleans crashed wrapper groups before reaping their reserved leader PID.
A failed scope cleanup quarantines only its project. Unknown birth evidence refuses effects
and never permits owner recovery. Queued initial dispatch is distinct from
consumed execution/publication. Restart does not replay uncertain operations.

## Change map

| Change | Start | Proof |
|---|---|---|
| discovery/restart/identity | Supervisor.tick | test_web_supervisor.py |
| admission/pool/cadence | ProjectWorker.tick | test_web_supervisor.py, test_run_concurrency.py |
| containment/parent death | ProcessTree, assert_ancestry | test_web_supervisor.py |
| command trust/results | CommandWorker.run_pending | test_web_commands.py, test_web_ownership.py |

## Key behaviors

- REQ-FUNC-43e2f999: independent project/run processes and canonical pool.
- REQ-REL-c240007b: duplicate-home refusal and ancestry fencing.
- REQ-REL-af360022: bounded tree stop with retained uncertain evidence.
- REQ-FUNC-e93e4944: stable project discovery/rename/archive/delete and paused Start.

## Files

- `04_Software/adore/web/supervisor.py`: event loops and fixed-role children.
- `04_Software/adore/web/processes.py`: gate, bounded capture, containment and ancestry.
- `04_Software/adore/web/commands.py`: scoped command consumer and installed entry.
- `04_Software/adore/web/worker_context.py`: effect ancestry fence.
- `04_Software/tests/test_web_supervisor.py`, `tests/supervisor_helper.py`: offline real processes.
- `05_SoftwareDocu/Component_Web_Worker.md`, `Component_Worker_Processes.md`: process contracts.

ProjectWorker uses shared admission_limit to respect current staged lower N before dispatching new commands/polls. Existing children continue with unchanged active config bytes; corrupt staged evidence refuses dispatch. Read-only role/capacity diagnostics route to project-capacity.md. Focused proof includes test_web_project_status.py.

After a lower N, already-started executors continue, while queued initial reservations wait for actual start capacity. Pending reservations retain their dispatch evidence; they do not block each other indefinitely. Initial activation rechecks current N atomically in the conductor as well as limiting supervisor dispatch.

Integrated acceptance reuses those contracts in tests/test_worker_acceptance.py:
real controlled Direct/AEGIS A execution overlaps B, B/global configuration
finishes while A remains blocked, active A retains unsafe staging, and full-pool
Cancel preserves its live peer and deduplicates requests. No target repository
checks run. Exact command/oracle/platform evidence is recorded in
01_Documentation/Worker_Acceptance.md.
