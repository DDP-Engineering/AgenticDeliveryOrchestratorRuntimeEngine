<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Deliver queued instructions through acknowledged Pi commands

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-DATA-1d84dc79](../requirements/data/REQ-DATA-1d84dc79.toml) — Refuse invalid instruction requests

If instruction text is empty, longer than 4000 characters, contains NUL or is not text, or mode is not now or after, ADORE shall refuse the request without writing an instruction.

Verification scope: POST each invalid boundary including non-string text and assert 422 and no queued instruction.

### [REQ-DATA-2777f139](../requirements/data/REQ-DATA-2777f139.toml) — Retain bounded atomic instruction records

ADORE shall retain each current-schema instruction in a bounded atomic per-run inbox across process restart.

Verification scope: Reopen inbox and verify exact records; exercise capacity, linked files, oversize and invalid schema without rewriting input.

### [REQ-DATA-2df9e8ef](../requirements/data/REQ-DATA-2df9e8ef.toml) — Journal acknowledged instruction delivery once

When instruction delivery is acknowledged, ADORE shall record one instruction-delivered journal event with instruction id, user, mode and delivery method.

Verification scope: Reconcile after simulated persistence interruption/restart and assert exactly one event for a delivered id.

### [REQ-FUNC-5942c3b1](../requirements/functional/REQ-FUNC-5942c3b1.toml) — Carry pending instructions into the next session prompt

When queued instructions remain at an implementation launch boundary, ADORE shall include their literal wrappers after the current human thread in that job conversation and record delivery only after Pi acknowledges the prompt.

Verification scope: AEGIS and direct fake launch prompts follow human discussion; rejected or unacknowledged prompt leaves queue, accepted prompt delivers exactly the captured snapshot.

### [REQ-FUNC-6bfce004](../requirements/functional/REQ-FUNC-6bfce004.toml) — Queue working job instructions

When an authenticated user allowed to stop a working job submits text of 1 to 4000 characters without NUL and mode now or after, ADORE shall atomically enqueue an instruction identifying that user and time.

Verification scope: Authorized admin and assigned developer POSTs retain exact Unicode/whitespace text and identity; GET returns queued state.

### [REQ-FUNC-84b2d01e](../requirements/functional/REQ-FUNC-84b2d01e.toml) — Deliver queued instructions through acknowledged Pi commands

While a Pi session is running, its existing RPC stdin owner shall send wrapped pending now instructions with steer and after instructions with follow_up.

Verification scope: Fake Pi records both command types, literal loader-wrapped text, same single process and unchanged cancellation.

### [REQ-FUNC-d25eb15e](../requirements/functional/REQ-FUNC-d25eb15e.toml) — Refuse instructions outside working jobs

If a job is not working, the instructions POST shall return HTTP 409 job_not_working without enqueuing text.

Verification scope: POST to finished, parked and handoff jobs and inspect conflict code and unchanged inbox.

### [REQ-REL-6dd5a689](../requirements/reliability/REQ-REL-6dd5a689.toml) — Skip corrupt queued instruction files

If an inbox instruction is malformed or unsafe to read, ADORE shall leave it unsent and expose value-free refusal evidence.

Verification scope: Inject malformed JSON, identity mismatch, schema mismatch and linked files; valid neighbors still deliver while notices identify refusal.

### [REQ-REL-73d642d7](../requirements/reliability/REQ-REL-73d642d7.toml) — Replay instruction ticket comments independently

For each delivered instruction, ADORE shall copy its text once to the source ticket using stable durable notification replay independently of Pi delivery success.

Verification scope: Fake forge outage and posted-then-error response preserve delivered state and replay one marker-bound ticket comment without failing the working run.

### [REQ-REL-c6354595](../requirements/reliability/REQ-REL-c6354595.toml) — Keep unacknowledged instructions queued

Unless Pi positively acknowledges the matching instruction command, ADORE shall retain that instruction as queued for a subsequent session.

Verification scope: Fake Pi success false, missing/wrong acknowledgement, exit and restart leave queued files; matching success marks delivered.

### [REQ-SEC-a076c292](../requirements/security/REQ-SEC-a076c292.toml) — Refuse unauthorized job instructions

If a caller is unauthenticated or lacks the job project grant, the instruction API shall refuse access through the existing authentication and hidden-project responses.

Verification scope: Exercise missing session, CSRF and unauthorized project requests with no inbox creation.

### [REQ-UX-bf7c7916](../requirements/ux/REQ-UX-bf7c7916.toml) — Compose instructions below the agent session

While viewing Agent sessions, authorized operators shall see a composer below the session including empty working sessions, queued and Pi-acknowledged delivered instructions, and the current-tool waiting note with fenced job-bound updates.

Verification scope: Offline browser sends both modes, checks literal text and status meaning, empty session access, disabled finished composer, and delayed job-switch responses without resetting scope/list/header.

## Implementation

- `04_Software/adore/executor/base.py`
- `04_Software/adore/executor/launcher.py`
- `04_Software/adore/executor/pi_rpc.py`
- `04_Software/adore/instructions.py`
- `04_Software/adore/orchestrator.py`
- `04_Software/adore/prompts.py`
- `04_Software/adore/prompts/live/instruction.md`
- `04_Software/adore/release_notes.toml`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/static/`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/src/InstructionComposer.tsx`
- `04_Software/web/src/JobWorkspace.tsx`
- `04_Software/web/src/help/content/de/jobs.md`
- `04_Software/web/src/help/content/en/jobs.md`
- `04_Software/web/src/help/content/fr/jobs.md`
- `04_Software/web/src/help/content/ro/jobs.md`
- `04_Software/web/src/instructionCopy.ts`
- `04_Software/web/src/instructionModel.ts`
- `04_Software/web/src/styles.css`
- `04_Software/web/tests/instructions.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_instructions.py`
- `04_Software/tests/test_orchestrator.py`
- `04_Software/tests/test_pi_rpc.py`
- `04_Software/tests/test_prompts.py`
- `04_Software/tests/test_web_jobs.py`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/tests/instructions.test.mjs`
