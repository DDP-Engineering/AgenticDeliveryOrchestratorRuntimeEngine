# Explicit workflow selection for each job

Status: implemented locally on `master`, uncommitted and ready for review.
Requested: 2026-11-15. Work in the shared checkout on `master`, without a commit.

## User decisions

- A repository containing AEGIS must also support implementation without AEGIS.
- The operator must be able to choose **With AEGIS** or **Without AEGIS** for
  each new job, before it starts. A project default alone is insufficient.
- The executor receives a software implementation request. Do not add deadlines,
  remaining-time calculations or budget instructions to its prompts.
- Keep the existing orchestrator limits and controls; changing their enforcement
  is outside this feature. Remove budget/deadline wording from the reused Direct
  implementation prompt rather than introducing executor-facing scheduling.
- Reuse the existing Direct workflow and persistent Pi conversation. Do not
  replace Pi or introduce another agent loop, convergence controller or workflow
  framework.
- Do not change the workflow of a job already running. DCP job #25 remains an
  AEGIS job and continues independently of this local implementation.

## Current implementation

`adore/orchestrator.py` probes a present AEGIS payload before admission and selects
the actual workflow from the allocated worktree. A missing payload selects
Direct; a broken present payload is refused. Therefore a prompt change alone
cannot implement an explicit bypass.

The Direct conductor already implements job-owned conversations, implementation
completion evidence, candidate integration, questions, checkpoints and the
configured approval/publication flow. It does not create AEGIS tasks or claim
independent AEGIS verification. `RunState.workflow` already records the actual
`aegis` or `direct` workflow.

Manual web starts travel through an authenticated durable operation queue,
worker admission and run dispatch. The requested mode must survive this entire
path, including restarts and idempotent request replay; an in-memory UI choice is
not sufficient.

## Product behavior

### Project default and per-job choice

Add `workflow.mode` with exactly two project defaults:

| Value | Meaning for automatic admission or a manual request without an override |
|---|---|
| `auto` | Current detection: use AEGIS when present, otherwise Direct. A present unusable payload is refused. |
| `direct` | Use Direct even when AEGIS is present; do not probe or invoke AEGIS. |

The default value is `auto`. Keep this distinct from `workflow.default_kind`,
which selects an AEGIS task type and is not a workflow selector.

Before a manual **Start**, show a compact workflow selector with **With AEGIS**
and **Without AEGIS**. Prefill it from the effective project default and repository
observation. The request carries the explicit selected `aegis` or `direct` value.
Explain an unavailable AEGIS choice clearly; Direct must remain selectable.

Use the same start control for global Tickets and Projects > Tickets, and cover
other existing manual start entry points. Do not duplicate the settings page,
redesign navigation or introduce a separate workflow management screen.

Expose the equivalent explicit choice for CLI manual admission, for example
`run --once --ticket IID --workflow aegis|direct`. Reject unknown values and
ambiguous use in continuous polling. Normal polling uses the project default.

An existing **Restart** operation creates a new job: its confirmation should
also allow this choice and carry it through the existing restart path. An ordinary
**Retry**, continuation, resumed clarification or review correction continues the
recorded job workflow instead of resolving project defaults again.

### Workflow resolution and AEGIS bypass

Resolve the effective requested mode before any admission-time AEGIS probe.

- Explicit Direct uses the Direct conductor whether the payload is absent,
  present, unsupported or broken. Do not inspect AEGIS task journals, run its CLI,
  create tasks or execute its stages in this mode.
- Explicit AEGIS requires a usable installed payload. Failure is a clear refusal;
  never silently change an explicit AEGIS request to Direct.
- `auto` retains the existing detection and refusal behavior.
- Pin the actual workflow in the new run's existing workflow field after
  validating the admitted worktree and before executor dispatch.
- Keep project settings, CLI diagnostics, web readiness/observations and displayed
  job workflow consistent with this selection. A Direct run must not be blocked
  by an unrelated unusable AEGIS payload.

Use one small shared resolution policy where needed; avoid competing detection
rules in the CLI, web and conductor.

### Durable command contract

Carry the optional manual override as typed data across API input, queue storage,
worker command construction, CLI admission/restart and run creation.

- Validate the closed value domain at human and durable-data boundaries.
- Bind the selected override to idempotent request replay: the same key with a
  different requested workflow must be refused rather than reusing a different
  start or restart.
- Preserve the existing authorization, project ownership, dispatch fencing and
  immutable run identity checks.
- Use an appropriate structured durable field. Do not hide the choice in a
  delimiter-based ticket ID, an error/detail string or a process-global flag.
- If a stored schema must change, support only its new current shape. Add the
  repository-required explicit operator deletion message and CHANGELOG reset
  instruction. Implement no migration, old-format reader or automatic deletion.
- Do not alter any DCP store as part of this local implementation.

### Direct implementation prompt and completion

The Direct prompt must explicitly state that the operator selected implementation
without AEGIS even if repository instructions normally require it. This instruction
comes from the trusted selection, not from a substring in ticket content.

Preserve all other repository coding, licensing and relevant verification rules.
Ask the executor to implement the ticket, perform appropriate checks, ask blocking
questions through the existing exchange and write the existing completion summary.
Do not require Frame/Specify/Design artefacts, AEGIS requirements, task journals or
AEGIS review ceremonies. Leave installed AEGIS files intact.

Retain the existing rule that ADORE owns Git checkpoints and publication. Preserve
the same Pi conversation through Direct continuations and corrections. Retain the
honest distinction between executor-reported checks and independent review; do
not add a replacement reviewer system or promise the same AEGIS assurances.

## Implementation sequence

1. Inspect applicable instructions and current tests. Use this accepted plan as
   the design input; keep any required implementation journal concise and refer
   to the plan instead of duplicating it into speculative documents.
2. Add and validate the project default and per-job override. Trace manual Start
   and Restart end to end through durable admission and idempotency.
3. Apply the shared selection before probing, pin the actual run workflow and
   dispatch the existing conductor. Preserve existing-job Retry behavior.
4. Update the Direct prompt and necessary workflow observations/diagnostics.
5. Add the compact web selection and settings copy in all four locales. Reuse
   shared controls across Tickets and project-scoped Tickets.
6. Update current user/configuration/CLI documentation, affected component pages,
   relevant in-app help in all locales, CHANGELOG and user-facing release notes.
7. Run focused checks, review the complete change and leave it uncommitted on
   `master`, with a clear report of checks and any remaining limitations.

## Acceptance and focused verification

- A manual Direct job in a repository with AEGIS starts without invoking AEGIS,
  including when its payload/journals would be unusable in automatic mode.
- An explicit AEGIS job uses AEGIS; a missing/broken payload fails clearly.
- Automatic admission retains current behavior; a Direct project default affects
  new jobs only. Persisted jobs keep their actual workflow on Retry/continuation.
- The operator can choose the mode in global and project-scoped Tickets and when
  an existing Restart creates a fresh job. CLI selection reaches the same policy.
- A queued selection survives worker restart, retains authorization/fencing and
  rejects idempotent replay with a different mode.
- Malformed configuration, API values and persisted overrides fail closed.
- Direct prompts override only AEGIS procedure, preserve repository rules and do
  not add executor deadline/budget instructions.
- Job details display the actual selected workflow. Direct completion retains
  summary/check evidence, conversation persistence and existing publication gates.

Use existing focused tests and fixtures where possible; respect the user's
standing restriction against new tests, the full suite and delivery-archive
verification. Adapt existing cases/parameterizations for the affected contracts
and record any required deviations honestly. Do not run deployment/setup tests.

## Handoff constraints

- Shared repository, `master`, no new branch or worktree.
- No commit, push, merge, deployment, package regeneration or archive verification.
- Preserve the four pre-existing unstaged deletions of 0.15.0 delivery files.
- Do not modify DCP job #25, its source worktree, service configuration or state.
- Follow repository instructions for software implementation. Planning itself
  does not start a separate AEGIS workflow.
- Report the candidate as ready for review, with changed behavior, checks and
  limitations; do not turn a partial implementation into a completion claim.

## Implementation result — 2026-11-15

Implemented the accepted scope with existing Direct conduction and Pi conversation:
explicit Start/Restart choice in both ticket scopes, auto/direct project default,
CLI overrides, structured schema-19 durable operation workflow and idempotency,
worker/CLI identity fences, admission bypass/refusal and preserved Retry workflow.
Direct instructions override only mandatory AEGIS procedure and omit executor
budget/deadline wording. Current manuals, component pages, help and interface copy
in four locales, CHANGELOG and release notes are updated; static web assets rebuilt.

Evidence and focused commands are recorded in `.agentic/tasks/TASK-63b6559f.md`.
Only existing tests/fixtures were adapted. Full suites, external model/forge calls,
independent model review and delivery archive verification were not performed.
Web schema 19 requires an operator-managed fresh web store (delete web.db and
web.db.initialized when stopped); no store was reset and no conversion was added.
DCP job #25 and its host were not accessed. No commit, branch, worktree, publication,
deployment or delivery archive regeneration was performed. The four pre-existing
0.15.0 delivery deletions and the coordinator’s planning changes remain intact.
