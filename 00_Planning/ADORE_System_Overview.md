<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE System Overview

## Executive Summary

ADORE - the Agentic Delivery Orchestrator & Runtime Engine - is a local,
operator-controlled system that turns eligible forge tickets into governed,
isolated software-delivery runs.

It connects four areas that are normally handled manually:

1. a GitHub, GitLab, or Gitea ticket and its human discussion;
2. an isolated Git worktree and Docker/Podman executor container;
3. the repository-installed AEGIS engineering workflow;
4. human approval, draft MR/PR publication, review, and merge.

ADORE automates the repeatable coordination around engineering work. It does
not replace engineering governance and it does not make the final merge
decision. AEGIS defines and records the governed task workflow; the executor
performs the engineering work; ADORE supervises the run and independently
checks whether it is safe to proceed.

## What Problem It Solves

An autonomous coding executor can edit files, but a dependable delivery system
also needs to select the right work, preserve state across interruptions,
contain execution, enforce limits, request clarification, validate results,
obtain fresh approval, publish safely, and report failures visibly.

ADORE supplies that surrounding runtime. Its main goal is not maximum
autonomy. Its goal is bounded, recoverable autonomy with truthful state and
clear human control points.

## Relationship Between ADORE and AEGIS

ADORE is a companion to repository-installed AEGIS. It conducts the AEGIS
Python companion CLI on the major-0 line from 0.5.0 upward over JSON schema 1,
a range declared once in `04_Software/adore/aegis.py`. A different major, a
payload below the floor, or any other contract is refused at probe rather than
interpreted, so a new AEGIS minor needs no ADORE code change. Each AEGIS
release is still re-verified surface by surface, and the ADORE release number
names the AEGIS release the contract was last re-proven on; that is why 0.13.0
followed 0.9.0 directly.

The ownership boundary is deliberate:

| AEGIS and the executor own | ADORE owns |
| --- | --- |
| The durable task journal and engineering-stage content | Ticket selection and run identity |
| Framing, specification, design, implementation, validation, and delivery work | Branch, worktree, container, and executor lifecycle |
| The evidence created while performing the task | Independent contract, transition, Git, and publication checks |
| Progress through the governed task stages | Budgets, retries, recovery, comments, labels, and local run state |
| Engineering decisions recorded in repository artifacts | Candidate-bound approval, push, and draft MR/PR creation |

ADORE does not edit AEGIS journals as an alternative machine API. It invokes
the AEGIS CLI, validates the returned contract, and treats the durable journal
as the resume authority. Every stage prompt declares the task
autopilot-to-deliver by explicit conductor instruction, the per-task override
AEGIS defines for its checkpoint default, so an executor never stops at a
stage boundary that ADORE is waiting to observe. The pre-publication approval
is ADORE's own and happens on the forge.

## End-to-End Workflow

```text
eligible ticket
  -> ADORE schema-1 run state
  -> isolated branch + worktree + container
  -> AEGIS task journal
  -> one fresh executor session per stage
  -> local checkpoint after each successful transition
  -> target integration + strict independent verification
  -> candidate fingerprint + fresh human approval
  -> push + draft MR/PR
  -> governed revision loop on request or a failed pipeline
  -> human review and merge
```

A full AEGIS task follows:

```text
frame -> specify -> design -> build -> validate -> deliver -> done
```

Eligible quick work omits `specify` and `design`. The ticket label is only a
hint; the governed framing decision must still justify the selected path.

ADORE conducts one ticket per poll pass, synchronously, and picks a new ticket
only while fewer than `[polling] max_concurrent_runs` runs are `working`; the
default is one. Runs in waiting states persist between passes and are
reconciled before any pickup.

## Runtime States

| State | Meaning |
| --- | --- |
| `working` | A bounded engineering stage may run. |
| `parked-clarification` | The executor asked a question and the run awaits a human answer. |
| `awaiting-approval` | Validation passed and the exact candidate awaits fresh human approval. |
| `publishing` | Approved delivery bookkeeping, push, and draft creation are in progress. |
| `in-review` | A draft MR/PR awaits merge, close, or a bounded revision, requested by a human or started by a failed pipeline. |
| `failed` | Work stopped loudly and retry evidence is preserved. |
| `done` | A human merged the draft. |
| `cancelled` | An operator or closed source ticket ended the run. |

Clarification, approval, and review waits do not silently consume active-work
time. The active clock is re-armed when clarification resumes, a revision
begins, approval drift forces re-conduction, or an operator explicitly retries.
Iteration, cost, and file limits remain cumulative. `awaiting-approval` and
`in-review` have no timers by design; they are human-paced.

## Safety and Recovery Model

ADORE is designed to fail closed at trust boundaries and fail loudly in
operation.

- Every stage has a bounded failure count; the default third failed attempt is
  terminal, with durable evidence and a visible problem comment.
- Executor launches, AEGIS calls, active wall-clock time, reported cost, and
  files touched are bounded.
- Transient forge, Git, and container retries are separate from engineering
  stage failures. The push is retried on the same bounded schedule: it is the
  least reversible moment in a run, and a credential refresh must not discard a
  validated candidate and the approval bound to it.
- Work a failed publication attempt leaves behind is committed before the next
  attempt, so a precondition meant to protect the candidate cannot consume the
  retry budget instead. The mutation guard still compares against the state the
  human approved, not against what the failed attempt left.
- A single-conductor lock prevents the poller and operator mutations from
  changing the same run concurrently.
- Required notifications use a durable outbox. If a problem cannot be reported,
  code work stops until the notification can be replayed.
- Corrupt external or persisted input raises typed errors; ADORE does not guess,
  silently reinitialize, or continue from partial data.
- Failed-run worktrees, containers, and evidence are retained for explicit
  recovery. Routine cleanup protects them.
- Cleanup removes only deterministically identified orphan ADORE resources and
  never steals a live or unknown lock.

## Approval and Delivery Boundary

ADORE never merges.

After strict validation, ADORE records the candidate fingerprint and target
commit, removes any stale approval label, presents the evidence, and waits. A
human must review the presentation and freshly add the configured approval
label. Before pushing, ADORE fetches the target and verifies the same candidate
again.

Target drift, product mutation, approval staleness, or a revision request
invalidates the earlier approval and requires integration, validation, and a
new approval. Publication creates or adopts a draft MR/PR only. Forge branch
rules and human permissions remain the final delivery boundary.

## Pipeline Observation and Repair

While a run waits in `in-review`, each poll reads the forge pipeline verdict for
the draft and normalizes it across platforms to `success`, `failed`, `running`,
`none`, or `unknown`. Only a change in that verdict is a signal, so a run that
waits for days is neither nagged nor repaired twice for one failure, and an
unreadable verdict is silent.

`[review] on_pipeline_failure` decides what a newly failed verdict does.
`revise`, the default, starts a governed repair round; `notify` posts one
comment and waits for a human; `ignore` skips the read for a repository with no
CI.

A repair is the same bounded path a human request uses: a new task on the same
branch, earlier journals preserved, and the executor told that a green pipeline
is part of this round's acceptance criteria. It therefore ends where every round
ends, at strict validation and a fresh human approval before anything is pushed.
`max_review_rounds` bounds repairs and requested revisions together, so a
permanently red pipeline cannot loop; when the budget is spent the run keeps
waiting with a comment saying so rather than failing.

ADORE reads the verdict only. It does not fetch job logs, so a repair executor
reproduces the failure from the repository's own CI definition inside its
container.

## Main Components

| Component | Responsibility |
| --- | --- |
| CLI and profiles | The `adore` command, configuration selection, operator commands, and per-project profile homes |
| Setup | Guided `adore init` with host and target-payload readiness probes and validated configuration |
| Orchestrator | Polling, state transitions, recovery, budgets, approval, and publication |
| Forge adapters | Normalized GitHub (`gh`), GitLab (`glab`), and Gitea (`tea`) ticket, comment, label, draft MR/PR, and pipeline-verdict operations |
| AEGIS client | Version-range and schema checks, validated task and check documents, and the evolution and report calls |
| Worktree manager | Run branches, isolated worktrees, checkpoints, integration, fingerprints, and push |
| Container manager | Docker/Podman lifecycle, WSL-wrapped runtimes, mounts and their SELinux labeling, tool checks, the credential boundary, and egress policy |
| Executor launcher | Fresh stage sessions for OpenCode, Pi, Codex, and Qwen Code through a file-based gate protocol |
| State store | Schema-1 run records, ticket snapshots, the single-conductor lock, JSONL journals, and the notification outbox |
| Metrics | SQLite run summaries with a JSONL mirror, CSV export, and a static HTML dashboard |
| Process log | Rotating `adore.log` mirror of `run` output under the state root |

The runnable Python implementation and offline tests are under `04_Software/`.
Component-level contracts are documented under `05_SoftwareDocu/`.

## Operating Model

One ADORE installation can manage multiple project profiles. A profile binds a
forge repository, local clone, container image/runtime, labels, budgets,
executor command, delivery target, and local state root.

Typical operator commands are:

```text
adore init <profile>
adore --profile <profile> config validate
adore --profile <profile> run --dry-run
adore --profile <profile> run --once
adore --profile <profile> run --loop
adore --profile <profile> status
adore --profile <profile> runs
adore --profile <profile> logs <run-id>
adore --profile <profile> retry <run-id>
adore --profile <profile> cancel <run-id>
adore --profile <profile> cleanup
adore --profile <profile> stats --html
```

Forge credentials stay with the authenticated host CLI (`gh`, `glab`, or
`tea`) and are not passed to executor containers. Only explicitly allowlisted
model-provider environment keys may enter the executor environment.

## Supported Environment

ADORE supports:

- GitHub, GitLab, and Gitea through forge adapters;
- Docker, rootless Podman, and WSL-wrapped container commands;
- open, disabled, or allowlist-proxy container egress;
- OpenCode, Pi, Codex, and Qwen Code executor launchers;
- Windows 11 Task Scheduler and Ubuntu 22+ systemd deployment scripts, and a
  trimmed runtime bundle built by the `02_Tools/` packagers;
- offline unit and contract testing through injectable command runners.

Each real project still requires operator-authorized acceptance checks for its
forge authentication, container runtime, executor credentials, repository
rules, and installed AEGIS payload.

## What ADORE Is Not

ADORE is not:

- a replacement for AEGIS governance;
- a general-purpose CI/CD server: it reads a pipeline verdict to decide whether
  to open a repair round, and never runs, hosts, or reports pipelines itself;
- an automatic merge bot;
- a multi-worker parallel scheduler;
- a system that grants an executor forge credentials;
- a compatibility layer for former ADORE or AEGIS contracts;
- a guarantee that arbitrary code is safe merely because it runs in a
  container.

Its isolation controls reduce risk, while repository policy, scoped
credentials, human approval, branch protection, and review remain essential.

## Known Limits and Open Work

The configuration accepts and validates these keys, and the runtime does not
consult them yet; `config.example.toml` marks each one:

- `[readiness] require_known_component` and `max_scope_hint`: pickup filters
  only on acceptance criteria and the priority label;
- `[executor] mode`: the conductor is always thick and launches one stage per
  session. An executor that instead runs several stages in one session is
  accepted when the durable journal carries an entry for every stage it
  crossed, and refused otherwise, but the run then loses the per-stage
  checkpoints, error budget, and failure-context handback that the session
  boundary provides;
- `[review] review_reminder_after`: no MR/PR reminder is posted;
- `[reconcile] on_ticket_deleted` and `on_ticket_closed` values: reconciliation
  applies one built-in behavior regardless of the value, and
  `on_trigger_removed` has no effect at all, so an active run is stopped with
  `adore cancel`;
- `[state] channel`: the ticket always receives one status comment and the
  lifecycle labels;
- `[clarification] reminder_after` and `timeout_state`: no reminder is
  posted and a timeout always fails the run; the `stale` lifecycle value is
  accepted by the state schema but never produced;
- `[container] keep_parked` and the `parked_ttl_*` keys: a parked container
  is always stopped and retained until resume or explicit cleanup;
- `[metrics] capture_resource`: no container or disk resource probing.

Stage summaries and review verdicts that the executor records in the AEGIS
journal are not surfaced at the approval gate; recorded deviations are, as a
count and in full.

Pipeline job logs are not fetched, so a repair round reproduces the failure
locally rather than reading what the forge already recorded. On GitHub and Gitea
the review thread covers conversation comments, submitted review bodies, and
inline diff comments; GitLab's notes endpoint already carries all three. The
GitLab adapter is the one forge not yet exercised against a live instance: its
branch-lookup, pagination, and pipeline behavior are derived from the published
CLI and API contracts rather than observed. Native Windows single-file
executables and Ubuntu `.deb` packages are not implemented; delivery is a
Python package directory plus an executor container image.

## Current Product Position

ADORE 0.13.0 is a working, offline-tested companion runtime for AEGIS,
re-verified against AEGIS 0.13.0. It provides the complete path from opt-in
ticket selection through isolated execution, durable recovery, strict
validation, fresh approval, and draft publication. The design intentionally
favors a simple single-conductor model, explicit limits, typed failure,
preserved evidence, and human-controlled merge over speculative concurrency or
hidden automation.
