<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE 3.0 - AEGIS 3.x Hard-Break Adaptation Plan

Plan refreshed: 2026-08-08. Target: **ADORE 3.0.0**. This is a hard break:
ADORE implements exactly the current AEGIS 3.x contract and contains no AEGIS
1.x/2.x compatibility, fallback, or migration layer.

Pinned analysis basis:

- Authoritative source pin, resolved from checkout:
  `D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System`, commit
  `676b754f438fd82f0f48692c874bd9c8340a96b0` on `master`.
- AEGIS release 3.0.0, WAEGIS 3.0.0 with payload compatibility
  `>=3.0.0,<4.0.0`, run-graph schema 3, context schema 1.
- ADORE commit `80b0f06559e668c165060313d3d58f4e2230a351` on the existing local
  `master` branch. This work does not create, rename, or switch branches.
- Companion contract: `AEGIS_3.0_Contract_Notes.md`.

## 1. Goal

Deliver a lightweight, forge-agnostic and executor-agnostic conductor for
Windows and Linux. It conducts one bounded AEGIS-governed stage at a time,
escalates deterministically from typed process and artifact evidence, and
opens a draft MR/PR after a normally completed governance run. ADORE never
merges. No conductor decision depends on LLM interpretation.

## 2. Current implementation baseline

The 2026-08-01 plan's WP1-WP7 are already implemented on the branch. The
offline suite is green at **371 tests** on the refreshed-plan baseline. This
plan does not repeat that work; it records the corrections required by the
current AEGIS source before WP8 can begin.

| Existing package | Baseline status |
|---|---|
| WP1 grouped AEGIS client and removal of 1.x gates client | Implemented |
| WP2 persisted `aegis_run_id` | Implemented |
| WP3 next/status-driven full and quick conduction | Implemented |
| WP4 schema-3 failure evidence and block classification | Implemented, but artifact parsing needs fail-closed hardening |
| WP5 grouped-CLI executor prompts | Implemented, but quick and bootstrap instructions are now obsolete |
| WP6 workflow config, wizard, doctor, runtime checks | Implemented, requiring current WAEGIS/context verification |
| WP7 component/user documentation under `[Unreleased]` | Implemented for the earlier snapshot; must be corrected with behavior |
| WP8 cross-platform and live end-to-end acceptance | Completed 2026-08-08; evidence in `Prerequisites_Check_Report.md` section 19 |

The project version remained 1.2.0 during correction and acceptance. CR1-CR6
became green on 2026-08-08, after which the distinct final action cut the
user-selected ADORE 3.0.0 release and aligned all release declarations.

## 3. Contract gaps in the current branch

| Current ADORE behavior | Current AEGIS contract | Required hard-break correction |
|---|---|---|
| Every successful response is parsed as a four-key envelope | Successful `run context --json` is a direct schema-1 context object | Add a distinct typed context response and parser |
| Fresh-session orientation is composed from `run resume`/status | `run context` supplies the bounded authoritative bootstrap and safe recovery | Bootstrap every live stage executor from context; retain status for conductor diagnostics |
| Executor prompts duplicate stage procedures and may prepare intake | Stage forms/references carry completion checklists; preparing applied work is invalid | Reduce prompts to policy and context instructions; use only context-named recovery |
| Quick prompt accepts manual evidence and says INV-3 is not applicable | Quick requires create/register plus real red and green; INV-3 applies | Rewrite quick contract and tests |
| Disabled gates are treated as successful `disabled`; exit-0 verification is described as passed | Current vocabulary is `not-enforced`, and top-level success may be `waived` | Preserve exact outcome vocabulary in journals, escalation, and MR text |
| `complete: true` always proceeds to publication | An abandoned run is complete with `outcome: abandoned` | Make outcome part of the terminal-state decision and forbid publication |
| `stage close` relies on AEGIS's default approver | AEGIS now accepts `--approver`; fallback identity can imply human approval | Pass and validate a stable truthful delegated-ADORE identity |
| Stage-close extras are ignored | Quick close can return structured non-blocking advisories | Validate, journal, and surface advisories |
| Missing/malformed AEGIS artifacts can become empty strings/lists | External persisted state is a trust boundary | Raise a typed artifact error and escalate |
| Global options are appended after the command | `verify impact --run` also owns a subcommand boolean | Canonically place global options before group/action |

## 4. Locked design decisions

1. **One contract only.** The pinned AEGIS 3.x source is the only supported
   governance interface. No version negotiation or old-command fallback is
   added. The schema-3 doctor probe verifies readiness; the WAEGIS payload pin
   establishes the AEGIS 3 product identity.
2. **Status drives the conductor; context drives the executor.** ADORE uses
   pinned `run status` and a full/quick stage allowlist for deterministic
   progression. Every fresh live-stage executor session receives a validated
   `run context` bootstrap. `run resume` remains only a status alias.
3. **ADORE is an explicit delegated approver.** The operator's configured
   ready/kind/quick-label policy delegates stage conduction to ADORE. After
   objective readiness checks, ADORE calls `stage close --approver` with a
   stable identity that names ADORE, never an inferred Git user. The executor
   never closes a stage. The final draft MR/PR review and merge remain human.
4. **Never auto-waive.** ADORE preserves `waived` as an observable governance
   outcome and may show the exact eligible `waive add` command, but it never
   executes that command.
5. **Explicit run pinning.** The run ID returned by `run start` is persisted
   in `RunState` and supplied as a canonical global option on every later
   command. The selected-run pointer is never read.
6. **Quick means bounded, not evidence-free.** The label-selected quick
   profile still requires registered executable checks, a real red result,
   a real green result, and INV-3. A nothing-ran result is a failure.
7. **Fail closed at every AEGIS trust boundary.** Process responses and
   persisted artifacts are schema/type/run/path validated. Corruption,
   ambiguity, unexpected values, and missing required files become typed
   escalation, never empty evidence or a guessed default.
8. **Adoption remains outside ADORE 3.0 conduction.** New adoption commands do
   not broaden this release.
9. **Run abandonment is not coupled to ADORE cancellation.** `run list`,
   `select`, and `abandon` remain operator commands. A cancellation-time
   abandon would need a separate dirty-worktree/persistence design. ADORE
   nevertheless recognizes externally abandoned runs and never publishes
   them.

## 5. Remaining correction work packages

Execute CR1-CR6 in order. Every public behavior receives a happy-path test
and negative tests at its external trust boundaries. Unit tests remain fully
offline through injectable command runners. Component documentation changes
land with the corresponding implementation change.

### CR1 - Split response families in `adore/aegis.py`

Refactor transport without weakening the existing envelope boundary.

- Keep `AegisResponse` for normal envelopes. Add a frozen `AegisContext` for
  successful `run context --json` responses and a `run_context()` wrapper.
- Dispatch the response parser by command and exit code: exit 0 context uses
  the direct schema-1 parser; exit 1 still requires a valid blocked envelope;
  exit 2, malformed JSON, and unsupported exit codes raise
  `AegisProtocolError`.
- Scope that exit contract to the nine conductor wrappers. Document that
  future wrappers for `verify gates` or executable `verify impact --run` must
  handle propagated tool return codes, including 124/127, explicitly.
- Validate all context fields and allowed values, including schema version,
  run ID, kind, profile, current stage, `human_gate == "stage close"`, string
  lists, and current/previous artifact availability. Enforce the 4 KiB JSON
  bound and ensure all repository-relative reads remain in the worktree.
- Reject a context whose run ID, profile, or stage disagrees with the pinned
  ADORE state/status. Treat `next_commands` as data, never as arbitrary shell
  text to execute.
- Emit global `--run`/`--json` before the command group.
- Extend `stage_close()` with a required approver. Validate the returned
  approver and the shape of optional advisories.
- Validate optional `run start` warnings as bounded strings and preserve them
  for operator-visible journaling instead of silently discarding them.
- Add typed helpers for run terminal outcome and verification summary status
  rather than allowing callers to infer success from exit 0 alone.
- Tests: context success, blocked context, wrong schema, missing/wrong-typed
  fields, oversized response, run/stage/profile mismatch, invalid human gate,
  escaping paths, malformed JSON, exit 2, unsupported 7/124/127 on the current
  wrappers, canonical argv order, explicit approver, malformed advisories, and
  unchanged envelope happy/negative paths.

### CR2 - Make the stage loop context-driven and restart-safe

Update `orchestrator.py` so a fresh executor sees exactly the current AEGIS
stage contract and already-applied work is not repeated.

- Read pinned `run status` at each loop boundary and validate stage/profile
  against the configured allowlist.
- Before every fresh live-stage launch or retry, call `run context`, validate
  it against status, provide the validated context to the executor, and direct
  it to read only the named `required_reads`. Validate the complete named
  bootstrap surface against the 30 KiB aggregate bound before launch.
- Follow a context recovery command only when it is one of the exact safe
  state-derived operations: prepare a genuinely unprepared stage, or show an
  unavailable prepared/applied artifact. Never prepare an applied stage.
- If a restart finds the current stage already applied and `stage show` says
  it is ready, skip the executor launch, perform the stage-specific objective
  verification, and close. If it is applied but blocked, use validated failure
  evidence to retry or escalate; do not regenerate its form.
- Keep completed-run revise/publication orientation separate from live-stage
  context. A completed run has no live stage to bootstrap; revise retains the
  existing bounded status/report path and re-verification policy.
- Keep structured clarification extraction from the pinned schema-3 graph,
  but make malformed/missing question state a typed error rather than an empty
  list.
- Invoke `stage close` only after fresh readiness/verification, with the
  explicit delegated approver, and validate that AEGIS records that identity.
- Tests: fresh stage, missing-form recovery, prepared stage, applied-ready
  restart, applied-blocked restart, context/status mismatch, unknown recovery,
  context bounds, questions park, close identity, complete normal outcome,
  and no executor launch when objective readiness is already established.

### CR3 - Replace the obsolete quick-run prompt contract

Make executor prompts policy-thin and generated-context-led.

- Remove independently maintained step-by-step stage mechanics from
  `_STAGE_GOALS`. Direct the executor to the validated context,
  `required_reads`, generated form checklist, and current-stage artifact.
- Retain only ADORE control constraints: remain within the current stage,
  never call `stage close`, never add a waiver, do not change the pinned run,
  obey budgets, and commit governed work.
- For a new quick run, require `check create`, completion of the generated
  definition, `check register`, a genuine red execution before the fix, a
  genuine green execution afterward, and active linked green evidence.
- Explicitly forbid manual evidence as a substitute and explain that INV-3
  applies. Only INV-1, INV-2, INV-8, INV-10, traceability, and coverage tied to
  intentionally absent stages can be not applicable.
- State that `nothing-ran` is failed execution and cannot satisfy readiness.
- State that an executed failing `check run` still exits 0. The executor must
  read `execution_status` and `evidence[].result`, preserve the red witness,
  fix the implementation, and rerun to obtain structured green evidence.
- Tests: prompt snapshots for all full/quick stages, context field inclusion,
  required-read bounding, close/waive prohibition, quick create/register,
  failing-check-exit-0 interpretation, red/green ordering, INV-3, and absence
  of the obsolete manual shortcut.

### CR4 - Preserve governance truth and fail closed on artifacts

Introduce one typed AEGIS-artifact boundary, for example
`AegisArtifactError`, and use it for every direct AEGIS file read.

- Validate `graph.json` as schema 3 with the pinned run ID and required
  container/value shapes. Accept the documented omissions for full profile,
  empty waivers, and normal outcome; validate `red_green_policy` for new quick
  runs and `outcome` when present.
- Validate `validation-summary.json` schema/run ID and outcome vocabulary.
  Interpret top-level `ok`, `waived`, and `failed` exactly. Interpret gate
  `passed`, `failed`, `waived`, `not-enforced`, and `not-run` exactly.
- Never render `waived` or `not-enforced` as passed. `waived` is non-blocking
  but must be named in metrics/journal/ticket/MR text; `not-enforced` is
  neither evidence of a pass nor a failure.
- Reject `execution_status: nothing-ran` as stage/verification success even
  when encountered in nested evidence.
- Treat executed-check `evidence[].result` as the red/green truth. Never infer
  a check pass from exit 0 or the envelope's `status: ok`.
- Require a successful `delivery report` response to name an existing,
  contained, valid report file. Do not silently omit a missing report from the
  draft MR body.
- Validate `stage close` advisories. Journal and surface
  `QUICK-SCOPE-ADVISORY` with its restart command in operator-facing output,
  while preserving its AEGIS-defined non-blocking status.
- Journal and surface validated `run start` warnings without treating them as
  blockers; the newly minted explicit run ID remains authoritative.
- Branch terminal handling on outcome. A normal completion may enter
  publication; `outcome: abandoned` records a terminal non-publication result;
  an unknown outcome escalates.
- Rewrite claims such as "every stage passed" and "verify passed" so the MR
  body truthfully distinguishes accepted waived results.
- Tests: valid full/quick graphs, historical quick omission, malformed graph,
  wrong run ID, missing summary/report, escaping report path, every validation
  and gate status, nothing-ran, executed red/fail and green/pass evidence under
  exit 0, waived MR wording, advisory propagation, abandoned no-publication,
  and unknown outcome.

### CR5 - Update implementation and operator documentation

Update documentation in the same change as CR1-CR4 behavior. At minimum:

- `01_Documentation/Integrating_A_Runtime_Project.md`
- `01_Documentation/Operations_Guide.md`
- `01_Documentation/Configuration_Reference.md` where policy identity or
  profile behavior changes
- `01_Documentation/Getting_Started.md` and `CLI_Reference.md`
- `05_SoftwareDocu/Component_Aegis_Client.md`
- `05_SoftwareDocu/Component_Orchestrator.md`
- any affected config, doctor, executor-launcher, or state component page
- root `README.md`, `AGENTS.md` status, and `CHANGELOG.md` under `[Unreleased]`

Document the two response families, status-versus-context ownership, explicit
delegated approver identity, current quick evidence, nothing-ran behavior,
truthful waived/not-enforced outcomes, advisories, abandoned runs, and the
operator-only abandonment boundary. Ensure every current-facing product label
in implementation and operator documentation names AEGIS 3.x; no runtime
compatibility branch accompanies that terminology update.

Do not cut 3.0.0 as part of these corrections. The requested release cut is a
distinct final action after CR6 acceptance: roll the changelog and align
`04_Software/pyproject.toml` and `04_Software/adore/__init__.py` to 3.0.0;
packaging remains version-derived.

### CR6 - Acceptance verification and live pilot

WP8 starts only after CR1-CR5 are green.

1. Run the complete offline suite on Windows and Linux.
2. Provision a scratch target from the authoritative WAEGIS 3.0.0 source or an
   artifact built from that exact commit. For an existing scratch clone, begin
   from a clean committed repository, run `waegis adopt` with a complete
   answers file and `--dry-run --json`, review the full plan and recovery
   evidence, then give explicit consent for the real adoption. Use `waegis
   new` only for an absent target. WAEGIS must not create a branch, stage, or
   commit: the operator reviews `git status`, stages and commits the approved
   payload, returns the repository to clean state, runs `waegis check`, and
   records the manifest payload version/digest. Finally verify `adore doctor`
   accepts schema 3. Do not use WAEGIS 1 editions, RepoWise management, or
   Git-history automation assumptions.
3. Conduct one full-profile Gitea ticket from ready label to draft PR.
4. Conduct one quick fix/change ticket. Prove check create/register, actual
   red then green, active linked evidence, and INV-3.
5. Exercise restart after an applied stage and prove ADORE does not relaunch
   or re-prepare work unnecessarily.
6. Exercise and record `not-enforced`, an explicitly human-created waiver,
   and a quick-scope advisory; confirm all operator and MR wording remains
   truthful.
7. Externally abandon a disposable run and prove ADORE never publishes it.
8. Run one post-draft revise cycle, then leave merge to a human.
9. Record commands, versions, run IDs, artifacts, defects, and outcomes in the
   prerequisites/live-verification report.

**Completion record - PASS, 2026-08-08.** CR1-CR5 landed incrementally before
WP8. The final offline suite passed **427 tests** on native Windows and Ubuntu
24.04/WSL2. The exact pinned AEGIS/WAEGIS 3.0.0 source provisioned and checked a
disposable Gitea repository; ADORE's doctor probe accepted schema 3. Full issue
#7 reached draft PR #8 with truthful human-waived and not-enforced outcomes,
including an applied-ready restart that skipped the executor. Quick issue #9
reached draft PR #10 with a real linked RED/GREEN pair, INV-3, four bypassed
stages, and a non-blocking four-path `QUICK-SCOPE-ADVISORY`; a review request
updated that same draft PR in revise round 1. Disposable issue #11 ended as
`aegis-abandoned`; its branch was never pushed and no PR was created. No pilot
PR was merged. Exact commands, pins, run ids, commits, artifacts, live defects,
and remote identifiers are recorded in `00_Planning/Prerequisites_Check_Report.md`
section 19.

## 6. Explicitly out of scope

- AEGIS 1.x/2.x compatibility, fallback, or state migration.
- Automatic waivers, automatic merge, or AEGIS graph/state surgery.
- Automatic AEGIS abandonment during ADORE cancellation.
- Adoption-run conduction.
- Automatic `route_to` regression or repo-wide access approval; both park or
  escalate.
- WAEGIS provisioning automation; doctor validates the installed target.
- Interpreting arbitrary `next_commands` as executable shell instructions.
- Redesigning post-completion AEGIS revision semantics.

## 7. Risks and explicit acceptance

- **Delegated approval semantics:** native AEGIS describes `stage close` as a
  human gate. ADORE's autonomous close is an explicit operator delegation,
  made auditable through `--approver`; it is not represented as human action.
- **Executor authority:** prompts prohibit close/waive, but the target payload
  does not technically deny those commands to an executor. ADORE detects
  unexpected advancement and the journal remains auditable; stronger command
  separation is a future isolation concern.
- **Context response exception:** successful `run context --json` is not an
  envelope even though broad CLI documentation describes machine output in
  envelope terms. The dedicated parser is pinned to context schema 1.
- **Pinned WAEGIS source:** AEGIS 3.0.0 is released and the earlier
  `[Unreleased]` contract risk is resolved. Acceptance used a detached scratch
  checkout of authoritative `master` at exact commit `676b754f...`, WAEGIS
  3.0.0, and payload digest `c08b148c...`; the concurrently changing source
  checkout was never modified. Those pins and the complete digest are recorded
  in the live report.
- **Completed-run revisions:** AEGIS has no reopen/amend workflow. ADORE's
  existing revise cycle re-verifies before updating the draft MR/PR but does
  not falsify the completed graph.
- **Cancellation versus abandonment:** automatically abandoning before
  teardown could strand or lose uncommitted governance state. It stays an
  operator action until persistence and cleanup semantics are designed.
