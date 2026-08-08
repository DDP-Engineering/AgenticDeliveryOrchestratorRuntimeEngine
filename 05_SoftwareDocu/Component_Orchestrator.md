<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Orchestrator (`adore/orchestrator.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/orchestrator.py` - file version 0.13.0.
> AEGIS contract: `00_Planning/AEGIS_3x_HardBreak_Adaptation/AEGIS_3.0_Contract_Notes.md`.
> Design: Orchestrator_Design_And_Decisions.md sections 5a, 7a, 8, 9, 10.

## 1. Purpose

The thick-conductor engine: poll for ready tickets, isolate work, drive the
executor through the AEGIS 3.x workflow stage by stage with objective
verification in between, park on clarification questions and resume on human
answers, enforce run budgets, and escalate instead of thrashing.
Deterministic Python only - every decision is an `if` on exit codes, envelope
fields, file presence, labels, and timestamps; all judgment lives in the
executor.

ADORE is AEGIS's **delegated approver**: the executor fills and applies the
stage forms, ADORE verifies objectively and issues `aegis stage close
--approver "ADORE 3.0 delegated conductor"` itself. The stable identity is
validated on the response and can never fall back to a Git user or imply a
human action. The real human approval stays at the draft MR review.

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
- **The AEGIS stage loop** (`_conduct_stages`, design 7a): start the AEGIS
  run once (`run start <kind> [--quick]`, persisting its id), then per
  iteration - budget check -> pinned `aegis run status` -> configured-profile
  allowlist/regression guard -> validated `aegis run context` -> bounded named
  bootstrap -> objective restart snapshot -> launch the executor only when
  work is still needed -> inspect (questions / exit code) -> verify (`aegis
  stage show` readiness, plus
  the committed-work check before validation verification, plus `aegis verify
  run` at validation and delivery) -> explicitly identified `aegis stage close` ->
  iterate. Failures retry the
  same stage with failure context, questions park, blocks and contract
  breaks escalate - all bounded by run budgets. Already-applied ready work is
  verified and closed without relaunch or form regeneration. Only a genuinely
  unprepared stage may follow context's exact `stage prepare` recovery; a
  missing prepared/applied form follows non-mutating `stage show`. Normal
  completion enters publication; abandoned completion never does. Each
  executor launch receives a
  stable archive stem (`NNN-stage` / `NNN-delivery-fix` / `NNN-revise`), and
  any returned archive directories are journaled as `executor-artifacts`.
  The validation cleanliness check deliberately runs before `verify run`:
  AEGIS verification writes durable graph/evidence/summary artifacts itself,
  and checking afterward would misclassify those conductor-generated records
  as uncommitted executor work and relaunch validation forever. The next stage
  commits those governed records before it finishes.
- **Clarification** (design 9): the exact park order (questions comment
  FIRST, then status, rounds cap, parked_at, container stop) and the exact
  resume order (marker/system-aware answer detection or the answered-label
  override, container back, relaunch at the parked stage with the full
  thread; the executor re-decides and may re-park). Questions reach ADORE
  through two channels and either fires: the AEGIS stage form's
  `control.unresolved_questions` (read from `graph.json`, the primary channel
  in 3.x) and the executor's questions file (the secondary one).
  A graph-backed question on a fresh pass parks before launch. On resume, an
  answered clarification thread bypasses that pre-launch park and reaches the
  executor with an explicit instruction to reconcile the answer into the
  applied form and clear only resolved questions. ADORE reads the graph again
  after the launch and parks again if the executor leaves any question open.
  Missing/malformed schema-3 question state is a typed contract failure,
  never an empty list. A run parked
  during publication resumes into publication, never back into the stage
  loop; `_conduct` fails closed when called on a publishing run (live
  findings 2026-07-04). Posting the questions first is a crash-ordering
  choice, but a forge failure is not a crash: a `ForgeError` on that post
  journals the questions as `park-post-failed` (the only copy left, truncated
  to 2000 chars) and **escalates** the run. Parking would strand it waiting
  for an answer to a question nobody was asked.
- **Parked lifecycle** (design 8b/9): container TTL reap (polls or seconds;
  never ends the run), one soft reminder, hard answer timeout that releases
  the ticket back to humans keeping state for audit.
- **Reconciliation** (design 8c, partial): deleted ticket -> orphan +
  teardown; closed ticket -> cancel. (hold/trigger-removed mid-run: later.)
- **Stale-`working` reaping** (`_stale_working` / `_escalate_stale`): a
  `working` run counts against `max_concurrent_runs`, so a conductor that
  died mid-run used to wedge pickup silently and forever. Reconciliation -
  which runs BEFORE the capacity check, so the slot is reusable in the same
  pass - now escalates any `working` run that (a) this process is not
  currently conducting and (b) last wrote state longer ago than
  `max_wall_clock_seconds + per_gate_timeout_seconds`. The event is journaled
  as `stale-working-detected`, the escalation is the ordinary one (failed +
  reason + ticket comment + metrics), and `adore retry` re-arms the run.
  In-flight runs are tracked on the instance by the `_conducting` context
  manager, which nests and unwinds on exceptions; a run with an unparseable
  `updated_at` is never reaped (fail closed toward a human).
- **Run budgets** (design 10): executor iterations, total wall clock
  (`max_wall_clock_seconds`), reported cost (`max_cost_usd`), files touched
  vs base ref - cheapest check first, so a run that blew its iteration count
  never pays for a journal read or a git call. Cost is summed from the run's
  journaled `usage` events (the append-only record `_journal_usage` writes
  after every launch, so it survives restarts and covers stage launches,
  delivery fixes, and revise rounds alike) and trips with
  `budget exceeded: cost $X.XX`. It is therefore only as good as what the
  executor reports: an executor that reports no cost - or
  `[metrics] capture_tokens = false` - leaves the cap inert, which
  `Configuration_Reference.md` states outright rather than implying a
  guarantee. A single executor launch is bounded separately by
  `per_gate_timeout_seconds` (independent from the whole-run ceiling, so
  per-gate and total budgets tune apart). Live-pilot refinements 2026-07-04:
  the files check is skipped while a target merge is in progress (staged
  upstream files are integration noise, not scope), and resume - like retry -
  restarts the active-work clock and iteration count (parked time is bounded by
  answer_timeout, not the work budget).
  The file count includes AEGIS's durable run artifacts as well as product
  changes; the default is therefore 120 after the AEGIS 3 CR6 pilot proved
  that a full run already owns 45 paths before implementation.
- **Ticket signaling** (design 5d): one status comment edited in place
  and/or lifecycle-label transitions, per `[state] channel`; signaling
  failures never break a run - local state is authoritative.
- **Operator commands** (design 8c), used by the CLI: `cancel` (teardown,
  keep state), `retry` (re-arm from the stored stage), `reset` (state
  surgery - force ADORE's own stage pointer to any AEGIS stage or
  `publication`, leave the run failed/retry-able; `adore retry` then
  re-enters the loop, where AEGIS still owns the governed run's stage.
  `reset` never touches AEGIS state),
  and `cleanup` (garbage collection - clear a stale instance lock, remove
  containers and worktree directories whose runs are terminal or unknown,
  including husk directories left by the WSL bind-mount teardown race).
  Cleanup never touches active runs (working/parked/in-review/validated)
  and only reports corrupt run state - deleting that is `delete`'s job.

- **Publication** (design 11a, exact order; ADORE's own phase after the
  AEGIS run completes, tracked as the `publication` stage): fetch + merge the
  target branch (conflicts -> executor resolves, budget-bounded), one
  authoritative post-merge `aegis verify run` (which in 3.x already includes
  the gate run plus the invariant, traceability, coverage and working-tree
  audits, so it replaces both 1.x steps; fix loop bounded by budgets),
  validate the durable summary against that response, compose the MR body
  from a required validated `aegis delivery report`, commit any
  AEGIS-generated run records, push the run
  branch (the only remote-writing git call; the executor cannot push), open
  the DRAFT MR (reviewers assigned, "Related to #N", never a merge flag),
  post the kind=delivery comment, and retain the environment (container
  stopped, worktree kept) for review. An already-open MR for the branch is
  adopted, never duplicated. The journal, ticket comment, and MR body preserve
  the exact `ok|waived|failed` verification vocabulary and name waived,
  not-enforced, and not-applicable results; none is rewritten as passed.
- **Post-MR outcomes** (design 11b): each poll checks in-review runs by MR
  iid - merged -> `done` + full teardown (state kept for audit); closed
  without merge -> `failed` + teardown. An MR that reads back as **deleted**
  (a real 404, distinct from a transient forge error, which is retried) is
  tolerated for a few polls, then ends the run - so an in-review run whose MR
  vanished cannot re-poll and re-log forever; a blip that resolves within the
  grace clears the counter. Legacy `validated` runs from before phase 4 are
  delivered by reconciliation.
- **Teardown** (`_teardown`): removes the container, then makes one call to
  `WorktreeManager.remove` for the worktree + branch. The WSL2 bind-mount
  teardown-race retry itself (transient mount-release signatures, ~7s
  backoff) lives entirely in the isolation layer now (ADORE-ARCH-009 -
  platform-specific glue does not belong in the core loop); `_teardown` only
  logs a husk message if that retry is exhausted, so `adore cleanup` can
  sweep it later. See `Component_Isolation.md` for the retry itself. Run
  state always survives.
- **The revise cycle** (design 11b): the `agent-revise` label on the open MR
  is the trigger - a plain comment never auto-reacts. Exact order: rounds
  cap (`max_review_rounds` -> failed), clear the trigger label FIRST,
  restart the retained environment, launch the executor with the MR review
  thread, then re-run the publication tail (merge, `aegis verify run`, push
  to the SAME branch - the MR updates in place and stays draft) and post the
  kind=delivery update comment. Revise questions park into the normal
  clarification flow. A revision does not reopen AEGIS stages: the governed
  run is already complete, so the revision's evidence lives in git history
  and the MR discussion. Trigger modes `comment-marker`/`auto` are treated as
  `label` until implemented.

Explicitly not owned: merging (structurally absent from the forge
interface) and metrics.

## 3. Implementation Overview

- Stage allowlists, not a hard-coded truth: `STANDARD_STAGES = intake ->
  alignment -> requirement -> design -> check -> implementation ->
  validation -> delivery` and `QUICK_STAGES = intake -> implementation ->
  validation -> delivery`. AEGIS owns the stage pointer; ADORE reads it from
  `run status` and checks it against the tuple for the run's profile
  (`run_profile: "quick"`, absent for full runs). A stage outside the tuple,
  or one at or before the last stage ADORE already closed (what an approved
  `route_to` produces), escalates. `PUBLICATION_STAGE = "publication"` is
  ADORE's own post-AEGIS phase and can never be reported by AEGIS.
- `DELEGATED_APPROVER = "ADORE 3.0 delegated conductor"` is passed on every
  close. The AEGIS client requires that the successful close response records
  the same value, making autonomous approval auditable and truthful.
- Status owns deterministic conductor progression; context owns every fresh
  live-stage executor session. `_stage_context` requires schema-1
  run/kind/profile/stage to match pinned status and ticket policy.
  `_validated_bootstrap` resolves every `required_reads` path inside the
  worktree, reads only those files for the size check, and enforces context
  wire bytes plus file bytes <= 30 KiB before launch. The prompt carries the
  validated context as data and arbitrary `next_commands` are never executed.
- `_validated_stage_show` validates pinned run/stage, lifecycle state,
  boolean readiness, string-list blockers/files/warnings, and consistency
  between ready and blockers. On restart, `applied + ready` skips the executor,
  performs stage-specific verification, and closes. `applied + blocked`
  relaunches with evidence but never prepares/regenerates the form.
- Live-stage `_STAGE_GOALS` are policy-thin. The validated `run context`, its
  exact `required_reads`, the generated form checklist, and the current-stage
  artifact own completion mechanics; ADORE does not duplicate AEGIS procedure
  or relay arbitrary `next_command` content. Standing policy keeps execution
  in the current stage and worktree, invokes the CLI with canonical global
  options (`bash .agentic/tools/run.sh --run <id> --json <group> <action>`),
  pins and never switches the run, enforces conductor budgets, reserves
  `stage close` for ADORE and `waive add` for a human, forbids remote actions,
  and requires governed changes to be committed. `revise` remains a separate
  post-publication instruction.
- Quick runs add `_QUICK_STAGE_GOALS` policy for all four live stages. A new
  quick implementation must create and register an executable AEGIS check,
  capture genuine RED before changing the implementation, capture genuine
  GREEN afterward, and link the active green evidence. Manual evidence cannot
  substitute for the executed check. Because a failed `check run` can still
  exit zero, the executor is told to inspect `execution_status` and every
  `evidence[].result`; nothing-ran is failure. Validation keeps INV-3 mandatory.
  Only INV-1, INV-2, INV-8, INV-10, and traceability/coverage tied solely to
  absent quick stages may be not-applicable; failed or nothing-ran evidence
  remains failure regardless of process exit or summary wording.
- Run kind and profile come from ticket labels through `[workflow]`
  (`kind_labels`, `default_kind`, `quick_label`); `--quick` is only produced
  for the kinds AEGIS permits (`fix`, `change`).
- Every collaborator is injected (`forge`, `store`, `worktrees`,
  `containers`, `executor`, `sleep`, `log`); `from_config` wires production
  implementations and pulls the executor secret subset
  (`[executor] env_keys`) from the environment / `.env`.
- `[executor] stage_host_auth` (pilot-only) supports OpenCode and Codex only.
  At provision, the corresponding host `auth.json` is copied through the io
  mount and scrubbed from io immediately. OpenCode uses
  `~/.local/share/opencode/auth.json`; Codex uses `~/.codex/auth.json` and is
  staged into `/home/adore/.adore-codex`, which is injected as `CODEX_HOME` so
  machine-local Codex plugin/config state is not reused. See
  `01_Documentation/Security_And_Credentials.md`.
- `_container_env` composes the environment used for both container creation
  and every `exec`: ADORE-managed Git/Home variables, non-secret
  `[container] runtime_env` values such as `UV_LINK_MODE=copy`, executor
  secrets from `[executor] env_keys`, and selected-executor runtime values
  such as Codex `CODEX_HOME`.
- `_provision` also asks the isolation layer to run
  `[container] required_tool_checks`, so a profile with the wrong
  runtime-project image fails before the executor starts a gate. On the FIRST
  creation of a run's worktree it fetches the remote first (best-effort - an
  offline fetch never blocks), so the run branches from an up-to-date base
  rather than a possibly stale local ref.
- **Executor sessions live inside the container**: provision reports
  created/started/running, and a "created" container resets the stored
  session id (journal: `session-reset`) - a fresh container can never be
  asked to continue a dead session (live finding 2026-07-04).
- `_read_aegis_artifact` is the single direct-file trust boundary: only strict
  UTF-8 regular files under the worktree, addressed by contained
  repository-relative POSIX paths and bounded to 4 MiB, may enter ADORE.
  `graph.json` is validated as the closed schema-3 shape with the pinned run,
  documented optional omissions, profile/red-green policy, human waivers, and
  terminal outcome. `validation-summary.json` validates the pinned run and
  exact top-level/gate vocabularies, rejects `nothing-ran` success, and is
  cross-checked against the verify response plus active executed evidence.
  A successful `delivery report` must name the exact existing report for the
  pinned run, whose heading identifies that run. Any violation raises
  `AegisArtifactError` and escalates; no empty-string fallback exists.
- Stage failures, not-ready stages, and failed verifications relaunch the
  same stage with the reason plus read-only AEGIS failure evidence as added
  prompt context; the iterations budget ends the loop. Evidence sources, in
  order and each bounded (5000 characters, 5 items): the blocked/failed
  response itself (`error`, `remediation`, stage `blockers[]`, the exact
  `next` command), `validation-summary.json` (failing gate groups, invariants
  that do not hold, traceability/coverage/working-tree findings - waived and
  not-enforced gates are reported as such, never as passed), the schema-3
  `graph.json` `evidence[]` rows (`id`, `kind`, `stage`, `summary`, `command`,
  `failure_kind`), and the `report.md` excerpts. All of it lives under
  `.agentic/runs/<aegis-run-id>/`, addressed by the run id ADORE persisted and
  never by the worktree's `current_run` pointer (design decision 4). Reading
  invokes no extra AEGIS command and changes no pass/fail decision. Journal
  scraping is gone: the AEGIS 1.x `gate.output` event no longer exists, and the
  envelope plus the validation summary cover the need. Malformed persisted
  evidence is a conductor trust-boundary failure and escalates rather than
  being described to the executor or yielding an empty evidence block.
- The post-merge `aegis verify run` fix prompts use the same evidence
  enrichment, while merge-conflict prompts remain based on git merge output.
  Configured executor secret values are redacted from all appended failure
  context, from escalation reasons, and from the MR body.
- Every AEGIS-facing failure fails loud, and `classify_block` is the single
  place that decides what "loud" means for a blocked response. Precedence:
  a live persistence lock (`PERSISTENCE-LOCK-TIMEOUT`) is the one transient
  AEGIS failure and earns exactly one bounded retry after a short delay - a
  `stage close` retries the close itself rather than relaunching the executor
  - after which it escalates; the rest of the non-waivable integrity floor
  (`GRAPH-STALE-UPDATE`, `REQUIREMENT-STALE-UPDATE`, schema corruption) and
  every run-resolution error escalate, because state repair is a human task;
  human-attention state recorded in the stage (unresolved questions, an
  alignment `pause`, a `repo-wide` access request, a `route_to` request) parks
  through the normal clarification flow; everything else escalates with the
  AEGIS error, its remediation, and - looked up from `waive list` - the exact
  `aegis waive add <id> --reason "..."` command a human could run. The waive
  hint is advisory: if `waive list` is unusable the escalation still carries
  the original error. `AegisProtocolError` / `AegisTimeoutError` escalate
  tagged as a contract failure. ADORE never waives, never routes, and never
  repairs AEGIS state.
- **Every escalation reaches the ticket** (`_escalate`): besides the edited
  status line (which only ever says "failed"), one dedicated comment carries
  the full reason - AEGIS error, remediation, waive hint - plus the
  `adore logs` / `adore retry` commands, under a `kind=escalation` marker.
  Without it an operator watching the forge saw a run stop with no
  actionable information and the composed waive hint was invisible to anyone
  without host access. The post is best-effort (`suppress(ForgeError)`):
  local state is authoritative, so a forge outage must not stop a run from
  reaching its terminal state. The reason is redacted by the callers that
  build it, and stays that way.
- Live-stage sessions never use a status-composed orientation: every first
  attempt and retry gets validated `run context`. `_workflow_orientation`
  remains deliberately separate for completed-run publication fixes and
  revise rounds, where there is no live stage/context to bootstrap. It uses
  bounded pinned status evidence and never reopens the completed graph.
- After every executor `GateRun`, `_journal_artifacts` appends immutable
  archive paths to the run journal when the launcher returned any. This makes
  `adore logs <run-id>` the index into raw gate evidence without changing the
  current live io exchange files.
- The status comment is posted once (id in state.json) and edited in place
  afterwards; comment identity is marker-based throughout.
- `poll_once(dry_run=True)` selects and reports without any side effect.

## 4. Dependencies

- Internal: config, identity, state store, forge adapters, isolation,
  executor launcher, the AEGIS client (`adore/aegis.py`), util (durations,
  timestamps, quiet hours, dotenv).
- External: only what the collaborators need (git, container runtime,
  glab/gh/tea, and the selected executor base/runtime-project image).

## 5. Inputs And Outputs

- Inputs: `config.toml`, ready tickets and comments from the platform,
  executor GateRuns, `.env` secrets.
- Outputs: per-run state + journal under `<store>/runs/<run-id>/`, executor
  archive path journal events, worktrees and containers, ticket
  comments/labels, log lines; draft MR delivery state.

## 6. Data Contracts

- Poll summary mapping: `resumed` / `reaped` / `timed_out` counters,
  `picked` iid or None, `paused` / `at_capacity` flags (CLI prints it as
  JSON). `stale` appears only in passes that reaped an abandoned `working`
  run, and counts them.
- Lifecycles: `working`, `parked`, `validated`, `failed`, plus terminal
  outcomes (`cancelled`, `ticket-closed`, `orphaned`, `answer-timeout`,
  `deleted`).
- Label transitions per state are a fixed table (`_apply_lifecycle_labels`).
- Resume threshold: comments with id greater than the recorded question
  comment id, non-system, without the agent marker.

## 7. Workflow Integration

`adore run --loop` (service) or `--once` (cron/Task Scheduler) enters here.
Delivery and review reuse the same executor-launch archive mechanism for
conflict/preflight fixes and reviewer-requested revise work.

## 8. Usage

```bash
adore run --dry-run   # what would be picked, no side effects
adore run --once      # one poll pass (cron / Task Scheduler)
adore run --loop      # the long-running poller
adore cancel <run-id> && adore retry <run-id>
adore logs <run-id>
```

## 9. Validation And Tests

- `tests/test_orchestrator.py` (118 tests; all collaborators faked, real
  store/config). A scripted `FakeAegis` answers the grouped CLI with
  conforming envelopes and advances its own stage pointer on `stage close`,
  so the loop is exercised as it would be against a live payload.
  Coverage: the full eight-stage happy path to a draft MR (ADORE issuing
  every close, session continuity, journal, single edited status comment);
  the quick four-stage path; the quick label ignored for kinds AEGIS
  rejects; the AEGIS run started once and resumed afterwards; direct context
  on every fresh launch/retry; missing-form prepare/show recovery; prepared,
  applied-ready, and applied-blocked restart behavior; no executor replay when
  objective readiness is established; context/status mismatch, unknown
  recovery, aggregate overflow, malformed questions, and malformed stage
  snapshots failing closed; a stage AEGIS
  will not call ready relaunched with its blockers; a failed
  `aegis verify run` relaunching validation; a blocked `stage close`
  escalating with the AEGIS remediation; an unknown stage and a stage
  regression escalating before any launch; fresh-context prompt inclusion and
  a non-conforming `run context` escalating; evidence
  addressed by the persisted run id while a decoy `current_run` pointer is
  ignored; the validation summary and graph rows appearing in a retry prompt;
  damaged artifacts reported rather than hidden; a started run without a
  graph escalating; every `classify_block` branch; a held lock retried once
  then escalating; the exact waive command in an escalation and an
  unavailable `waive list` never hiding the original error; recorded stage
  questions parking the run, an answered graph question reaching the executor
  and being cleared before close; per-stage prompt contract tests (policy-thin live
  goals, canonical CLI option order, stage confinement, budgets, close/waive
  and remote prohibitions, run pin with switching forbidden, executable quick
  RED-before-GREEN evidence, INV-3 and nothing-ran semantics, both question
  channels); secret redaction; selection
  ordering, control labels and readiness negatives; idempotent re-poll skip;
  park order (question before status); resume filtering; answered-label
  override; round-cap escalation; TTL reap vs run survival; answer timeout
  release; pause/capacity; deleted/closed reconciliation; cancel/retry round
  trip; `reset` touching no AEGIS state; labels-channel transitions;
  publication ordering including artifact commit-before-push; valid
  full/quick/historical-quick graphs; malformed/wrong-run/unknown-outcome
  graphs; strict validation-summary and every gate status; nothing-ran and
  executed red/green evidence under exit zero; truthful waived journal,
  ticket, MR, and metrics surfaces; missing/escaping reports blocking
  publication; warning/advisory propagation; abandoned no-publication;
  archive-stem passing and executor-artifact journal entries.
- Minimum validation after a change: `python -m pytest -q` from
  `04_Software`.
- Live pilot pending (plan WP8): one supervised ticket end to end against a
  repository carrying the AEGIS 3.0 payload.

## 10. Limitations And Future Work

- Nothing stops a misbehaving executor from running `aegis stage close` or
  `aegis waive add` itself; the prompts forbid both and AEGIS journals every
  close, so MR review catches abuse (plan risk 7.1).
- A stage regression (`route_to`) and a `repo-wide` access escalation both
  escalate to a human rather than being conducted.
- Adoption runs are not conducted.
- Readiness checks `known_component` / `max_scope_hint` are config intent,
  not yet enforced.
- Reconciliation of hold/trigger-removed mid-run and content-hash drift
  reactions (design 8a/8c) are not yet wired.
- Crashed `working` runs are escalated (not resumed) once they go stale, so
  they no longer wedge pickup; continuing one is still a deliberate
  `adore retry`. Automatic crash-resume is a later refinement.
- The executor cost budget is enforced from what the executor reports, so it
  is inert for executors that report no usage; ADORE has no independent way
  to price a launch.
