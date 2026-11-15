<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# One Pi conversation per job

Status: implemented on `master`; verification and local commit are tracked in TASK-1d2c5b87.
Requested: 2026-11-15. Implementation uses the installed AEGIS workflow.

## Decision and scope

STATED: Keep one implementation conversation throughout a job. Independent
reviewers apply when the repository's AEGIS review setting enables them.
Keep the change simple: no new convergence controller, repeated-cause classifier,
review scheduler, planning service or operator setting.

One conversation does not require one uninterrupted operating-system process.
Keep the existing bounded RPC execution and ADORE stage boundaries; resume the
same exact, job-owned Pi session when starting the next process. This preserves
stage checkpoints, cancellation, time limits and fresh per-attempt credentials.

Use Pi 1.5.2's session persistence and built-in compaction. Do not implement
another conversation store, transcript format or compaction algorithm.

## Evidence behind the change

OBSERVED during the read-only DCP investigation:

| Job | Active work | Pi launches | Recorded behavior |
|---|---|---|---|
| #25 | 4h 47m | 16 | 13 Build launches; 12 partial continuations; no Validate |
| #77 | 13h 43m | 42 | 14 Validate launches; 11 Validate-to-Build returns |

Both jobs are cancelled. Their journals and Git checkpoints remain evidence;
this implementation does not restart, modify or import their conversations.
The old #77 recordings were truncated, so its complete Pi dialogue is unavailable.

OBSERVED in current source:

- `04_Software/adore/executor/launcher.py`: RPC launches use `--no-session`.
- `04_Software/adore/orchestrator.py`: each stage/continuation launches another
  executor process and renders a fresh-session prompt.
- `04_Software/adore/prompts/stage/`: instructions require a session to end at
  a stage boundary; continuation includes recent journal evidence.
- `04_Software/adore/local_execution.py`: native Pi settings use a temporary
  agent directory. Conversation persistence must survive that directory's cleanup.
- `04_Software/adore/executor/pi_rpc.py`: turn usage is cross-checked against
  session statistics. Resumed statistics can contain earlier attempts.

INFERRED: Keeping conversation context can reduce repeated orientation and
replanning. It does not guarantee a completion time or eliminate real defects,
test failures, large ticket scope or independent review corrections.

Pi references pinned to the installed version:
[sessions](https://github.com/earendil-works/pi/blob/v1.5.2/packages/coding-agent/docs/sessions.md),
[RPC](https://github.com/earendil-works/pi/blob/v1.5.2/packages/coding-agent/docs/rpc.md).

## Implementation sequence

1. **Bind a conversation to the existing job.** Locate the persisted session in
   ADORE-owned job storage outside Git-tracked work. Use an explicit session path
   or identifier, never the account's most recent conversation. Reuse existing
   ownership/path checks and host/container path mapping. Keep settings, endpoint
   configuration and credentials isolated from conversation history.
2. **Resume through the existing executor interface.** The first invocation
   creates the conversation; later stage, continuation and correction invocations
   resume it. Support container Docker/Podman/WSL and native Windows/Linux through
   their existing process seams. Preserve ChatGPT access-token renewal and current
   RPC settlement, abort and shutdown behavior. Do not add a second executor backend.
3. **Make prompts describe continuation.** Supply the complete task context at
   initialization. Later prompts identify the current stage, next work and new
   instructions without repeatedly injecting the complete ticket and journal log.
   The durable AEGIS journal remains authoritative and stage transitions remain
   controlled by ADORE. Direct workflow continuations use the same job isolation.
4. **Preserve evidence, instructions and accounting.** Keep the current activity
   and stage/attempt recordings as execution segments of the conversation. Avoid
   duplicate historical messages and cumulative-token double counting. Preserve
   Send now/Queue message acknowledgements across boundaries. Keep current private
   permissions, redaction and bounded evidence handling. A new conversation viewer
   or dashboard is outside this change.
5. **Honor existing review and lifecycle policies.** The main conversation may
   coordinate Validate and receive corrections. Required independent reviewers
   keep separate contexts under the installed AEGIS review policy. Do not add
   mandatory reviews when that policy is disabled or absent. Preserve existing
   retry/reset/cancel/delete ownership and resource-release semantics; an explicit
   new job has its own conversation. Missing/corrupt required conversation evidence
   fails clearly instead of silently starting over or resuming another job.
6. **Document and commit.** Update affected component contracts, user guidance,
   prompt descriptions, CHANGELOG and user-facing release notes. Update all four
   help locales if a described behavior changes. Commit the completed implementation
   on `master`, including this plan and its status; never push.

## Focused acceptance

- [x] A later stage can use a fact introduced in an earlier stage after the RPC
  process has restarted; a continuation/correction retains that conversation too.
- [x] A separate job cannot select the first job's session, settings or credentials.
- [x] Native and container execution resolve their own explicit persistent paths.
- [x] Existing stage checkpoints, timeout/cancel handling and token renewal work.
- [x] Per-attempt usage excludes previously counted conversation turns; existing
  instruction delivery and stage/attempt evidence remain coherent.
- [x] Required review contexts stay independent; disabled review adds no new work.
- [x] Invalid ownership, unsafe paths and corrupt required state fail explicitly.
- [x] Current component/user documentation describes the implemented behavior.

Use targeted existing tests and focused checks. Retain the user's restriction
against adding new tests; adapt affected existing assertions/fixtures as needed
and record the resulting AEGIS testing deviation. Do not run the full test suite
or delivery-archive verification. The user will request final verification later.

## Boundaries

- No new convergence detector, semantic failure parser, retry policy or cycle cap.
- No changes to installed AEGIS source/policy, including its review-round limit.
- No recovery/import of old ephemeral Pi histories and no data migrations,
  compatibility readers or schema upgrades. Prefer the current stored model;
  any necessary breaking format change follows the repository's refusal rules.
- No new Pi/model dependency, optional session-mode setting or per-user Pi lookup.
- No package/image rebuild, deployment or restart of DCP jobs in this task.
- Leave the four pre-existing deleted `07_Delivery/adore-0.15.0-*` files untouched
  and outside the feature commit; generated delivery archives remain outside Git.

Begin with an implementation budget of 90 minutes and 45 changed files. Reassess
and report if concrete work exceeds that bound; do not silently broaden scope.

## Implementation evidence

The candidate uses explicit private Pi session paths, native/container RPC identity
checks, current-format corruption refusal, incremental prompts with acknowledged
ticket fingerprints and per-attempt usage baselines. Existing tests are adapted;
no new test functions, live model calls, delivery verification or deployment.
The file budget was reassessed to 52 to include required AEGIS evidence, current
manuals/component documentation and four help locales. The 90-minute time bound
remains. Final proof and commit are recorded in TASK-1d2c5b87.

Acceptance is supported by targeted offline fake-RPC restarts and current-source
inspection. No live model inference, real container acceptance or delivery-archive
verification was run; the user explicitly deferred live/delivery verification.
Independent review found and corrected stale-ticket fingerprint selection and
malformed Pi compaction validation. Valid ancestor and self-reference compaction
records remain accepted.
