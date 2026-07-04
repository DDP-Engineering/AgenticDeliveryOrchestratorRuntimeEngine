<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Orchestrator (`ador/orchestrator.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/orchestrator.py` - file version 0.2.0.
> Design: Orchestrator_Design_And_Decisions.md sections 5a, 7a, 8, 9, 10.

## 1. Purpose

The thick-conductor engine: poll for ready tickets, isolate work, drive the
executor gate-by-gate with verification in between, park on clarification
questions and resume on human answers, enforce run budgets, and escalate
instead of thrashing. Deterministic Python only - every decision is an `if`
on exit codes, file presence, labels, and timestamps; all judgment lives in
the executor.

## 2. Responsibilities

- **Polling** (`run_loop` / `poll_once`, design 5a): interval + jitter,
  error backoff, quiet hours, single-instance lock, pause flag,
  `max_concurrent_runs`.
- **Selection** (design 5/5b): eligibility label -> control labels
  (hold/exclude always win) -> existing-run skip -> readiness filter
  (priority label + acceptance-criteria heuristic) -> priority order, lowest
  iid first.
- **Claim** (design 8a): ticket snapshot + content hash + RunState = the
  lock; deterministic run-id names every resource. The run branch is
  rendered from `[worktree] branch_template` ({slug}/{run_id}/{iid}) so repo
  push-rule conventions like a `feature/` prefix are config, and the stored
  `run.branch` stays authoritative for the run's lifetime.
- **The per-gate loop** (design 7a): mark status -> launch the executor for
  one gate -> inspect (questions / exit code) -> verify with the workflow
  CLI's `invariants` -> advance, retry with failure context, park, or
  escalate - bounded by run budgets.
- **Clarification** (design 9): the exact park order (questions comment
  FIRST, then status, rounds cap, parked_at, container stop) and the exact
  resume order (marker/system-aware answer detection or the answered-label
  override, container back, relaunch at the parked stage with the full
  thread; the executor re-decides and may re-park). A run parked during
  delivery resumes into the delivery sequence, never back into the gates;
  `_conduct` fails closed on any stage outside the gate list (live findings
  2026-07-04).
- **Parked lifecycle** (design 8b/9): container TTL reap (polls or seconds;
  never ends the run), one soft reminder, hard answer timeout that releases
  the ticket back to humans keeping state for audit.
- **Reconciliation** (design 8c, partial): deleted ticket -> orphan +
  teardown; closed ticket -> cancel. (hold/trigger-removed mid-run: later.)
- **Run budgets** (design 10): executor iterations, wall clock, files
  touched vs base ref. (Cost joins with the metrics phase.) Live-pilot
  refinements 2026-07-04: the files check is skipped while a target merge is
  in progress (staged upstream files are integration noise, not scope), and
  resume - like retry - restarts the active-work clock and iteration count
  (parked time is bounded by answer_timeout, not the work budget).
- **Ticket signaling** (design 5d): one status comment edited in place
  and/or lifecycle-label transitions, per `[state] channel`; signaling
  failures never break a run - local state is authoritative.
- **Operator commands** (design 8c): `cancel` (teardown, keep state) and
  `retry` (re-arm from the stored stage), used by the CLI.

- **Delivery** (design 11a, exact order): fetch + merge the target branch
  (conflicts -> executor resolves, budget-bounded), re-run `gates run`, the
  authoritative `delivery-preflight` (fix loops on both), push the run
  branch (the only remote-writing git call; the executor cannot push), open
  the DRAFT MR (reviewers assigned, "Related to #N", never a merge flag),
  post the kind=delivery comment, and retain the environment (container
  stopped, worktree kept) for review. An already-open MR for the branch is
  adopted, never duplicated.
- **Post-MR outcomes** (design 11b): each poll checks in-review runs by MR
  iid - merged -> `done` + full teardown (state kept for audit); closed
  without merge -> `failed` + teardown. Legacy `validated` runs from before
  phase 4 are delivered by reconciliation.
- **The revise cycle** (design 11b): the `agent-revise` label on the open MR
  is the trigger - a plain comment never auto-reacts. Exact order: rounds
  cap (`max_review_rounds` -> failed), clear the trigger label FIRST,
  restart the retained environment, launch the executor with the MR review
  thread, then re-run the delivery tail (merge, gates, preflight, push to
  the SAME branch - the MR updates in place and stays draft) and post the
  kind=delivery update comment. Revise questions park into the normal
  clarification flow. Trigger modes `comment-marker`/`auto` are treated as
  `label` until implemented.

Explicitly not owned: merging (structurally absent from the forge
interface) and metrics.

## 3. Implementation Overview

- `GATES = intake -> alignment -> requirement -> check -> implementation ->
  validation` - matching the workflow CLI's canonical STAGES (alignment is
  the pre-requirement intent check added by the Intent_Alignment_Stage_Plan;
  delivery is phase 4). Per-gate goals are fixed prompt blocks
  (`_GATE_GOALS`) plus the standing rules (worktree-only, never push/MR,
  questions-file convention, stop at gate end).
- Every collaborator is injected (`forge`, `store`, `worktrees`,
  `containers`, `executor`, `sleep`, `log`); `from_config` wires production
  implementations and pulls the executor secret subset
  (`[executor] env_keys`) from the environment / `.env`.
- `[executor] stage_host_auth` (pilot-only): at provision, the host's
  opencode `auth.json` is copied into the container through the io mount and
  scrubbed from io immediately - the OAuth bridge from
  Setup_And_Credentials.md 3.1.
- **Executor sessions live inside the container**: provision reports
  created/started/running, and a "created" container resets the stored
  session id (journal: `session-reset`) - a fresh container can never be
  asked to continue a dead session (live finding 2026-07-04).
- Gate failures and invariant failures relaunch the same gate with the
  failure tail as added prompt context; the iterations budget ends the loop.
- The status comment is posted once (id in state.json) and edited in place
  afterwards; comment identity is marker-based throughout.
- `poll_once(dry_run=True)` selects and reports without any side effect.

## 4. Dependencies

- Internal: config, identity, state store, forge adapters, isolation,
  executor launcher, gates wrappers, util (durations, timestamps, quiet
  hours, dotenv).
- External: only what the collaborators need (git, container runtime,
  glab/gh, the executor image).

## 5. Inputs And Outputs

- Inputs: `config.toml`, ready tickets and comments from the platform,
  executor GateRuns, `.env` secrets.
- Outputs: per-run state + journal under `<store>/runs/<run-id>/`, worktrees
  and containers, ticket comments/labels, log lines; a validated branch
  awaiting phase-4 delivery.

## 6. Data Contracts

- Poll summary mapping: `resumed` / `reaped` / `timed_out` counters,
  `picked` iid or None, `paused` / `at_capacity` flags (CLI prints it as
  JSON).
- Lifecycles: `working`, `parked`, `validated`, `failed`, plus terminal
  outcomes (`cancelled`, `ticket-closed`, `orphaned`, `answer-timeout`,
  `deleted`).
- Label transitions per state are a fixed table (`_apply_lifecycle_labels`).
- Resume threshold: comments with id greater than the recorded question
  comment id, non-system, without the agent marker.

## 7. Workflow Integration

`ador run --loop` (service) or `--once` (cron/Task Scheduler) enters here.
Phase 4 plugs the delivery sequence (design 11a) where
`_complete_validation` currently stops, and the review loop (11b) on top of
the same state machine.

## 8. Usage

```bash
ador run --dry-run   # what would be picked, no side effects
ador run --once      # one poll pass (cron / Task Scheduler)
ador run --loop      # the long-running poller
ador cancel <run-id> && ador retry <run-id>
ador logs <run-id>
```

## 9. Validation And Tests

- `tests/test_orchestrator.py` (all collaborators faked, real store/config):
  full happy path to `validated` (session continuity, journal, single edited
  status comment), selection ordering + control labels + readiness
  negatives, idempotent re-poll skip, park order (question before status),
  resume filtering (system/marker ignored, human resumes with thread),
  answered-label override, round-cap escalation, gate retry with context +
  iterations budget, invariants-failure relaunch, TTL reap vs run survival,
  answer timeout release, pause/capacity, deleted/closed reconciliation,
  cancel/retry round trip, labels-channel transitions.
- Minimum validation after a change: `uv run --group dev pytest tests/test_orchestrator.py`.
- Live pilot pending: first supervised run against a real `agent-ready`
  ticket (crawl phase) - will also confirm the `.agentic` CLI verbs used by
  the gates wrappers.

## 10. Limitations And Future Work

- Delivery, review loop, and metrics are phase 4; a validated run waits.
- Readiness checks `known_component` / `max_scope_hint` are config intent,
  not yet enforced.
- Reconciliation of hold/trigger-removed mid-run and content-hash drift
  reactions (design 8a/8c) are not yet wired.
- Crashed `working` runs are skipped on restart (design 8) and need a manual
  `ador retry`; automatic crash-resume is a later refinement.
- The executor cost budget needs token accounting (metrics phase).
