<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Orchestrator Component

## 1. Purpose

`adore/orchestrator.py` is the deterministic ADORE 0.5 conductor around the
agent-driven AEGIS 0.5 workflow. It prevents silent stalls and keeps remote
publication human-approved and draft-only.

## 2. Responsibilities

- select/claim forge tickets and provision worktree/container isolation;
- create and bind active/historical AEGIS tasks;
- launch a fresh executor session for each stage attempt;
- validate full/quick progression and documented validation rollback;
- create an unpushed local checkpoint commit after every successful stage;
- distinguish clarification, stage failures, transient infrastructure failures
  and immediate integrity/policy/budget failures;
- persist and deliver mandatory incident/terminal/approval notifications;
- integrate the target, run independent strict verification and fingerprint the
  candidate/target/commit series;
- require a fresh approval-label transition after presentation;
- push and open/update a draft MR/PR, then require journal close-out at done;
- create a new AEGIS task for each bounded review round;
- reconcile parked, approval, review, stale-working and outbox states.

The component never edits AEGIS journals, gives forge credentials to an
executor, or merges.

## 3. State Machine

Lifecycle states are `working`, `parked-clarification`, `awaiting-approval`,
`publishing`, `in-review`, `failed`, and `done`. AEGIS stage is tracked
separately.

Every nonterminal state has a poll action or timeout. A stale `working` state
with no live conductor becomes a loud failure rather than occupying capacity.

## 4. Recovery Contract

`max_stage_failures` counts attempts for the current stage. The default third
failure posts a terminal comment, stops the container and preserves the
worktree. Multiple AEGIS findings in one invocation count once. A successful
stage transition resets the counter. Questions do not consume it.

`max_transient_retries` covers container/fetch/forge transport independently.
Required comments are outboxed before transport. A write failure stops code
work and polling replays it without consuming an execution slot.

## 5. Validation and Approval

The conductor integrates `origin/<target>`, runs the validation executor, then
calls `check --task <id> --strict --run --json`. It requires at least one
executed successful verification command and a task at deliver. Approval is
bound to the candidate fingerprint and target commit. Any drift or product
mutation invalidates approval.

## 6. Dependencies

Internal dependencies: config, state, AEGIS client, executor launcher,
isolation, forge adapters, identity, metrics and utilities. All decision
collaborators are injectable for offline tests.

## 7. Validation and Tests

`tests/test_orchestrator.py` covers full/quick paths, fresh sessions,
checkpointing, two failures then success, exact third-attempt abort,
finding-count semantics, questions, incident editing, outbox outage/replay,
MR fallback, approval freshness/drift, prompt restrictions and the absence of
a merge capability.
