<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-7d73a3eb — Direct candidate completion

Status: active. This specifies the completion state machine, not implementation
structure or a configurable verification facility.

## Authority and boundary

- STATED (ticket #62 Decisions, Done and Failures; direct-workflow plan sections
  4.1–4.3): direct work starts at `build`, uses fresh bounded Pi attempts and
  hands a completed candidate to the existing approval mechanism.
- STATED (ticket #62 scope): no verification command or additional setting in
  this change; every direct candidate is explicitly unverified.
- OBSERVED (`04_Software/adore/orchestrator.py::_present_for_approval`,
  `_approval_ready`, `_publish_impl`): publication already consumes candidate
  fingerprints, target identity and validation evidence separately from an AEGIS
  command. The existing human gate remains authoritative.

## Completion state machine

| State / trigger | Observable outcome |
|---|---|
| `build`, authorization within current limits | One fresh direct implementation session |
| Blocking questions remain | Existing clarification parking; no completed candidate |
| Executor error or typed timeout | Existing bounded failure accounting; no completed candidate |
| Successful settled session, no questions, unchanged non-exchange fingerprint | Terminal `NO_CHANGES`, carrying available summary |
| Successful settled session, no questions, changed non-exchange fingerprint | Conductor-owned `validate` completion, checkpoint and candidate presentation |
| Candidate successfully recorded and presented | `stage = done`, `lifecycle = awaiting-approval` |

The failure and parking rows delimit this completion requirement; their
independently verifiable responses have separate requirement records in the task
coverage table. This spec introduces no new failure code beyond the ticket's
`NO_CHANGES`, and does not redefine shared error or question precedence.

Successful settlement means the existing executor success/settlement contract,
not merely a process exit code or a line in the agent's summary. A summary-only
edit never satisfies product progress. The progress comparison excludes root
`ADORE_SUMMARY.md` and the configured questions file. A questions file's presence
prevents completion, including an empty file.

## Successful completion ordering

1. Observe settled success, absence of the questions file and changed product
   progress relative to the attempt's starting fingerprint.
2. Retain available summary text as conductor-owned durable evidence using
   existing state/evidence storage; remove `ADORE_SUMMARY.md` from the worktree.
3. Make the host-owned checkpoint with neither exchange artifact included.
4. Record `validation_evidence` identifying verification as **not configured**,
   and the clean `candidate_fingerprint` and target identity used by existing
   approval freshness checks.
5. Present at `done` / `awaiting-approval` through the existing human gate.

A failed checkpoint or failed candidate observation is not a completed
candidate. Shared typed failure handling retains the actual stage/cause.
Existing cancellation, handoff and required-notification boundaries remain in
force; this sequence does not grant a bypass around them.

No second Pi session performs verification in this ticket. `validate` is a
conductor-owned phase and does not invoke AEGIS or fabricate passing commands.
Pi's summary of its own checks is reported as such, never as independent strict
verification. The exact approval and MR/PR notice is:

```text
Verification: not configured. This candidate is unverified.
```

## Persisted and presentation contract

- The only new top-level run-state field is `workflow`, the string `direct` or
  `aegis`, selected at claim and retained thereafter.
- A direct run has `active_task_id = null` and `task_ids = []`.
- Direct workflow stages are `build`, `validate`, `done`. The existing shared
  `publishing` reset pointer is control state, not an extra executor stage.
- Summary survives removal of its exchange file and reload before approval or
  MR/PR body construction. Existing evidence sanitization applies before forge
  presentation. No top-level summary field or stored-format migration is added.
- Approval and MR/PR bodies carry summary, changed-file count and the unverified
  notice; neither has an AEGIS task line. A fresh approval still binds the exact
  candidate and target. ADORE never merges.

## Examples and acceptance

- A fake executor edits `src/feature.py` and writes a short summary, returns
  settled success and leaves no questions: one session produces a checkpoint,
  durable summary and not-configured evidence, then awaiting approval. After
  state reload and fresh human approval, the published body retains that
  summary and notice; the exchange files were never in any checkpoint.
- A fake executor writes only `ADORE_SUMMARY.md`: `NO_CHANGES` retains its text,
  no approval is posted and no extra remediation attempt is authorized by this
  completion rule.
- Product edits plus questions park instead of completing. An answer label
  resumes a new session with the thread and the same workflow/budget history.
- A nonzero result, settle error, timeout, unreadable/unsafe present summary or
  failed checkpoint cannot produce awaiting approval.
- An AEGIS repository still uses its pinned task and existing strict gate; an
  unsupported present payload is not a direct candidate.

Offline fake forge/executor/Git acceptance tests are linked in the requirement;
actual build commands and exit results are recorded in TASK-652f9133's Log.

## Assumptions and design resolution

- INFERRED (ticket's explicit done conditions): the summary is requested output,
  not an additional mandatory success condition; an absent summary alone is not
  grounds for inventing `SUMMARY_MISSING` or rejecting genuine product progress.
  No fabricated agent summary is acceptable. Safe handling of present corrupt
  summary input follows the repository's fail-closed boundary rule.
- OBSERVED (`RunState.validation_evidence` is an object and `outcome` is text):
  existing fields can carry summary/evidence. The task Design D5 chooses bounded
  sanitized `summary`, a conductor-owned `implementation = completed` marker,
  `verification = not configured` and observed `changed_files` within that object.
  Summary-only or failed-session evidence never authorizes approval. The marker
  and entry into validate are persisted in the same state write. A restart after
  that write lets checkpoint recovery finish validate without repeating successful
  work, including when the successful attempt consumed the final permitted launch.
- INFERRED (task Design D1/D4/D6/D7, based on inspected source): shared plan/worktree
  allocation before the first claim save, direct-only exchange exclusions and
  workflow dispatch in shared continuation helpers preserve the AEGIS stage loop.
  The conductor saves safely read summary text before isolation removes its file.
  Direct drift retains completed implementation evidence but invalidates the
  candidate binding and requires integration plus fresh presentation. Build's
  linked offline tests prove these seams; the ticket's stop-and-ask conditions
  remain the boundary for any expansion beyond those helpers or the one-field scope.
