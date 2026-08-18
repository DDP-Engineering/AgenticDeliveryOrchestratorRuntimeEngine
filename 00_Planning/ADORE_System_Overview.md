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

ADORE is a companion to repository-installed AEGIS. It supports the AEGIS
Python companion CLI and JSON schema 1 only; any other contract is refused
rather than interpreted.

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
as the resume authority.

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
  -> governed revision loop when requested
  -> human review and merge
```

A full AEGIS task follows:

```text
frame -> specify -> design -> build -> validate -> deliver -> done
```

Eligible quick work omits `specify` and `design`. The ticket label is only a
hint; the governed framing decision must still justify the selected path.

ADORE conducts synchronously and serially. It may retain several durable runs
in waiting states, but a poll works on at most one active run at a time.

## Runtime States

| State | Meaning |
| --- | --- |
| `working` | A bounded engineering stage may run. |
| `parked-clarification` | The executor asked a question and the run awaits a human answer. |
| `awaiting-approval` | Validation passed and the exact candidate awaits fresh human approval. |
| `publishing` | Approved delivery bookkeeping, push, and draft creation are in progress. |
| `in-review` | A draft MR/PR awaits merge, close, or a bounded revision request. |
| `failed` | Work stopped loudly and retry evidence is preserved. |
| `done` | A human merged the draft. |
| `cancelled` | An operator or closed source ticket ended the run. |

Clarification, approval, and review waits do not silently consume active-work
time. The active clock is re-armed when clarification resumes, a revision
begins, approval drift forces re-conduction, or an operator explicitly retries.
Iteration, cost, and file limits remain cumulative.

## Safety and Recovery Model

ADORE is designed to fail closed at trust boundaries and fail loudly in
operation.

- Every stage has a bounded failure count; the default third failed attempt is
  terminal, with durable evidence and a visible problem comment.
- Executor launches, AEGIS calls, active wall-clock time, reported cost, and
  files touched are bounded.
- Transient forge, Git, and container retries are separate from engineering
  stage failures.
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

## Main Components

| Component | Responsibility |
| --- | --- |
| CLI and profiles | Configuration, project selection, operator commands, and multi-project operation |
| Orchestrator | Polling, state transitions, recovery, budgets, approval, and publication |
| Forge adapters | Normalized GitHub, GitLab, and Gitea ticket/MR operations |
| AEGIS client | Version/schema checks and validated access to the AEGIS companion CLI |
| Worktree manager | Run branches, isolated worktrees, checkpoints, integration, fingerprints, and push |
| Container manager | Docker/Podman lifecycle, mounts, tools, credentials boundary, and egress policy |
| Executor launcher | Fresh stage sessions for supported coding executors and bounded result capture |
| State store | Schema-4 run records, ticket snapshots, locks, JSONL journals, and notification outbox |
| Metrics | Best-effort SQLite, JSONL, CSV, and static HTML operational summaries |

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
adore --profile <profile> status
adore --profile <profile> runs
adore --profile <profile> logs <run-id>
adore --profile <profile> retry <run-id>
adore --profile <profile> cleanup
```

Forge credentials stay with the authenticated host CLI (`gh`, `glab`, or
`tea`) and are not passed to executor containers. Only explicitly allowlisted
model-provider environment keys may enter the executor environment.

## Supported Environment

ADORE supports:

- GitHub, GitLab, and Gitea through forge adapters;
- Docker, rootless Podman, and WSL-wrapped container commands;
- open, disabled, or allowlist-proxy container egress;
- configurable executor launchers, including opencode, pi.dev, and Codex;
- Windows and Linux-oriented deployment scripts;
- offline unit and contract testing through injectable command runners.

Each real project still requires operator-authorized acceptance checks for its
forge authentication, container runtime, executor credentials, repository
rules, and installed AEGIS payload.

## What ADORE Is Not

ADORE is not:

- a replacement for AEGIS governance;
- a general-purpose CI/CD server;
- an automatic merge bot;
- a multi-worker parallel scheduler;
- a system that grants an executor forge credentials;
- a compatibility layer for former ADORE or AEGIS contracts;
- a guarantee that arbitrary code is safe merely because it runs in a
  container.

Its isolation controls reduce risk, while repository policy, scoped
credentials, human approval, branch protection, and review remain essential.

## Current Product Position

ADORE 0.6.0 is a working, offline-tested companion runtime for AEGIS. It
provides the complete path from opt-in ticket selection through isolated
execution, durable recovery, strict validation, fresh approval, and draft
publication. The design intentionally favors a simple single-conductor model,
explicit limits, typed failure, preserved evidence, and human-controlled merge
over speculative concurrency or hidden automation.

