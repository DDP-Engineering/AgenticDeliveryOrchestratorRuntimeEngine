<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE 2.0 — Hard-Break Adaptation to AEGIS 2.x

Plan date: 2026-08-01. Target: **ADORE 2.0.0** (MAJOR — AEGIS contract
break). No compatibility layer, no migration, no dual-version support:
ADORE 2.0 speaks only the AEGIS 2.x grouped CLI. AEGIS 1.x repos are simply
unsupported.

Companion document: `AEGIS_2.1_Contract_Notes.md` (the pinned AEGIS-facing
contract this plan is built against). Analysis basis: AEGIS payload 2.1.0 +
`[Unreleased]` (waivers, `--quick`), ADORE 1.2.0 + `[Unreleased]` (Gitea).

## 1. Goal restated

A lightweight, self-contained, forge- and executor-agnostic orchestrator,
running on Windows and Linux, that guides AEGIS-governed executors to
implement tickets, raises draft MRs, drives the revise cycle, and escalates
to a human on errors, hard-to-solve situations, or exhausted budgets.
Every ADORE decision stays an `if` on exit codes, JSON fields, labels, and
timestamps — no LLM logic in the conductor.

## 2. What the hard break changes (delta summary)

| ADORE 1.x assumption | AEGIS 2.x reality |
|---|---|
| CLI = `bash .agentic/tools/run.sh <verb>` with verbs `invariants`, `status`, `resume`, `gates run`, `delivery-preflight`, `report` | Grouped CLI `run.sh <group> <action>`: `run`, `stage`, `requirement`, `check`, `evidence`, `waive`, `verify`, `delivery`, `adoption`, `config`. Old verbs gone. |
| Output = free text used as prompt filler; exit code only objective signal | Stable envelope `status/stage/artifact/next` (+ extras) via `--json`; exit 0/1/2 discriminated; `next` names the exact next command |
| 6 conducted gates (intake…validation), executor freely drives workflow | 8 stages (adds `design`, `delivery` as a stage); per-stage `prepare → fill form → apply → close` cycle; forms are the sole input boundary |
| Active run found via `.agentic/.workspace/state/current_run` pointer (the fragile seam that already broke once) | `run start --json` returns the run-id; every later call can pin `--run <id>`. The pointer becomes irrelevant to ADORE. |
| Failure evidence scraped from graph/journal with 1.x event shapes (`gate.output`) | Schema-3 `graph.json` `evidence[]`, `validation-summary.json`, and `--json` verify output are the evidence sources; journal event names changed |
| Delivery verification = `gates run` + `delivery-preflight`; MR body from `report` verb | Verification = `aegis verify run`; report = `aegis delivery report` + `.agentic/runs/<id>/report.md`; delivery is now a workflow stage that ends the run (`complete: true`) |
| Version drift degrades silently (empty brief, skipped evidence) | Hard break: silent-degrade paths must fail loud and escalate |

## 3. Design decisions (locked for this plan)

1. **`next`-driven conduction with a stage allowlist.** The conductor no
   longer hard-codes the gate list as truth; AEGIS's `stage` + `next`
   fields drive the loop. A static allowlist of expected stages per run
   kind/profile (from the contract notes) guards against loops or unknown
   stages — anything outside it escalates. Budgets remain per-stage.
2. **ADORE issues `stage close` itself.** In AEGIS, `close` is the approval
   action. In a conducted run, ADORE is the delegated approver: executor
   fills forms and runs `apply`; ADORE verifies objectively
   (`stage show --json` readiness, `verify` exit codes, blocker absence) and
   then closes. The real human approval stays where it always was: the draft
   MR review. This keeps executor = content, conductor = control.
3. **Never auto-waive.** `waive add` is human-only. A waivable blocker that
   the executor cannot fix within budget escalates with the exact
   `aegis waive add <blocker-id> --reason ...` hint in the ticket comment.
4. **Explicit `--run` everywhere.** The AEGIS run-id is captured at
   `run start` and persisted in ADORE's `RunState`; all subsequent CLI calls
   and file reads use it. No reads of the `current_run` pointer anywhere.
5. **Fail loud, stay lean.** Unparseable JSON, exit 2, unknown stage, or a
   missing artifact are typed errors that end in escalation — not silent
   degradation. But no version negotiation, capability probing, or
   compatibility shims: exactly one supported contract.
6. **Quick profile is label-driven.** Ticket labels map to run kind and
   profile (config-defined). Default: kind `feature`; labels for
   `fix` / `change`; an additional quick label opts into `--quick` (valid
   for fix/change only — config validation enforces this).
7. **Adoption runs are out of scope** for ADORE 2.0.0 conduction (they are
   interactive/human-led by nature). `requirement`/`evidence`/`check`
   subcommands are used by the executor, not the conductor; ADORE only
   needs `run`, `stage`, `verify`, `delivery`, `waive list`, `config
   validate`.

## 4. Architecture after the change

Unchanged (AEGIS-agnostic, keep as-is): `forge/*` (GitLab/GitHub/Gitea),
`isolation.py`, `state.py` (one added field), `config.py` framework,
`identity.py`, `metrics.py`, `process_log.py`, `util.py`, `profiles.py`,
`branding.py`, `executor/base.py` + `executor/launcher.py` transport,
polling/selection/park/resume/review/escalation skeleton in
`orchestrator.py`, deploy scripts, egress proxy.

Replaced/reworked:

```
adore/gates.py                -> adore/aegis.py        (new AEGIS 2.x client)
orchestrator GATES + _conduct -> next-driven stage loop
orchestrator _GATE_GOALS      -> per-stage form-first prompts (8 stages)
orchestrator _agentic_* block -> evidence from --json + schema-3 files, by run-id
config [workflow] section     -> new: kind/profile label mapping, per-stage timeouts
docs + component docu         -> rewritten contract pages
```

## 5. Work packages

Execute in order; each WP is a self-contained agent task with its own tests
green before moving on. Follow repo rules (AGENTS.md): license headers,
Doxygen prologues, `@version` bumps, component docu in the same change,
offline tests through the injectable command runner.

### WP1 — AEGIS 2.x client (`adore/aegis.py`, replaces `gates.py`)

The single place that knows how to talk to AEGIS.

- Invocation: `["bash", ".agentic/tools/run.sh", *argv, "--run", <id>,
  "--json"]` in the container at `/adore/work` (same exec seam as today).
  `--run` omitted only for `run start` and `config validate`.
- Parse the envelope into a frozen dataclass `AegisResponse` — `status`,
  `stage`, `artifact`, `next`, `exit_code`, `raw` (full decoded object),
  plus helpers `ok`, `blocked`, `failed`, `error`, `remediation`.
- Exit-code discrimination: 0 → ok; 1 → governance (blocked/failed envelope
  still parsed); 2 or JSON parse failure → raise typed `AegisProtocolError`
  (ADORE defect / broken payload → escalation, never retry-with-prompt).
  Timeout → existing timeout handling.
- Wrappers used by the conductor: `run_start(kind, quick)` (returns run-id
  extracted from response), `run_status`, `run_resume`, `stage_show`,
  `stage_close`, `verify_run`, `delivery_report`, `waive_list`,
  `config_validate`. Sensible per-command timeouts (verify_run gets the
  long one, default 1800 s).
- Delete `gates.py`; update all imports.
- Tests (offline, fake runner): envelope happy path; blocked envelope with
  remediation; exit 2 raises; malformed JSON raises; `--run` injection;
  run-id extraction from `run start`.

### WP2 — State: persist the AEGIS run-id

- `RunState` gains `aegis_run_id: str | None` (set after `run start`,
  cleared never; part of the stored JSON). Loading legacy state files
  without the field yields `None`, which the conductor treats as
  "AEGIS run not started yet" — no migration code beyond the default.
- Tests: round-trip with and without the field.

### WP3 — Conduction loop rework (`orchestrator.py`)

- Replace `GATES` with per-(kind, profile) expected-stage tuples matching
  the contract notes (`STANDARD_STAGES`, `QUICK_STAGES`).
- `_conduct()` new shape:
  1. If `state.aegis_run_id` is `None`: `aegis.run_start(kind, quick)`
     (kind/profile resolved from ticket labels via config), persist run-id.
  2. Loop while budgets allow:
     a. `status = aegis.run_status()` → current stage; if `complete` →
        proceed to delivery/publication.
     b. Stage must be in the expected tuple, and must not regress except
        via an explicit `route_to` (which escalates in 2.0.0) — else
        `AegisProtocolError` → escalate.
     c. Launch executor for the stage (prompt from WP5); executor fills
        forms, runs `stage apply`, `check run`, `evidence`, `verify` as the
        stage requires, commits its work.
     d. ADORE verifies: `stage_show` → `ready` true and no blockers; for
        the validation stage additionally `verify_run` exit 0.
        (Re-verification 2026-08-01: `stage show` exposes `ready` /
        `blockers[]` and folds unresolved questions into `blockers[]`;
        there is no separate `unresolved_questions` key — contract notes
        11.2.)
     e. Questions present → existing clarification park flow (structured
        questions read from `graph.json` →
        `stage_records[<stage>].unresolved_questions` instead of the 1.x
        questions file — keep the file protocol as a secondary channel;
        union both).
     f. Verified → `aegis.stage_close()`; iterate.
     g. Failure → `_failure_context()` (WP4) and retry same stage within
        budgets, else escalate.
  3. Delivery stage: executor prepares the delivery form; ADORE runs
     `verify_run` one final time, closes delivery (AEGIS run complete),
     then the existing publication path: integrate target branch, push,
     open draft MR.
- `_deliver()` internals: replace `gates_run` + `delivery_preflight` with
  `verify_run`; MR body composed from `delivery_report` JSON plus
  `report.md` content (bounded), keeping existing marker/format.
- Revise cycle (`_revise`): unchanged flow; orientation brief now from
  `run_resume`; a revision does not reopen AEGIS stages in 2.0.0 — the
  executor works, ADORE re-runs `verify_run` before pushing the update
  (record follow-up: reopening a completed AEGIS run is an AEGIS-side
  question, out of ADORE's hands).
- Tests: scripted fake AEGIS walking a full 8-stage happy path to draft-MR;
  quick-profile 4-stage path; unknown stage escalates; blocked close
  retries then escalates; questions park; completion detection.

### WP4 — Failure evidence and orientation rewrite

- Delete `_AGENTIC_CURRENT_RUN` and `_safe_agentic_run_id`; all file reads
  use `state.aegis_run_id` directly.
- `_failure_context()` sources, in order, bounded as today (5000 chars /
  5 items): the blocked/failed `AegisResponse` (`error`, `remediation`,
  blockers from `stage_show`), `validation-summary.json` (failing gates /
  invariants), schema-3 `graph.json` `evidence[]` (active `result: fail`
  entries: `id`, `kind`, `stage`, `summary`, `command`, `failure_kind`),
  `report.md` tail only if it exists.
- Journal scraping (`_journal_failure_evidence`) is dropped — the 1.x
  `gate.output` event no longer exists and the envelope + summary cover the
  need. Less code, one fewer schema to track.
- `_workflow_orientation()` uses `aegis.run_resume()`; a failure to obtain
  the brief is now a logged warning + empty brief only when the run has not
  started; once a run exists, a blocked `resume` escalates (fail loud).
  (Re-verification 2026-08-01: AEGIS 2.x `run resume` returns the `run
  status` envelope, not prose — contract notes 11.1. ADORE composes the
  orientation block itself from run-id, stage, `next`, readiness state and
  blockers, and recent evidence.)
- Escalation classification in one helper `classify_block(response)`:
  - questions / pause / `requested_access_mode` / `route_to` → PARK (human
    ticket comment, existing clarification machinery).
  - waivable blocker unresolved after retries → ESCALATE with waive hint.
  - non-waivable integrity floor (`PERSISTENCE-LOCK-TIMEOUT` → one retry
    after short delay first; `GRAPH-STALE-UPDATE`, schema corruption, run
    resolution errors) → ESCALATE.
  - `AegisProtocolError` → ESCALATE tagged as orchestrator/payload defect.
- Tests: each classification branch; evidence extraction from a real-shape
  schema-3 graph fixture; missing graph escalates instead of silently
  returning "".

### WP5 — Executor prompts (8-stage, form-first vocabulary)

- Rewrite `_GATE_GOALS` → `_STAGE_GOALS` for: intake, alignment,
  requirement, design, check, implementation, validation, delivery — each
  telling the executor the AEGIS 2.x way: run `aegis stage prepare` /
  `show`, fill the generated form at the `artifact` path, `stage apply`,
  use `check prepare/record/run`, `evidence prepare/apply`, respect
  red-before-green, never run `stage close` or `waive add` (conductor and
  humans own those), commit all work including `.agentic` run records.
- Quick-profile variants for implementation/validation (mention bypassed
  stages so the executor doesn't look for missing artifacts).
- Generic frame (`_gate_prompt`): resume brief prepended (WP4), `--run`
  pin communicated to the executor, budget text unchanged.
- Tests: prompt snapshot tests per stage asserting the AEGIS 2.x command
  vocabulary and the close/waive prohibition.

### WP6 — Config, wizard, doctor, image

- New `[workflow]` config section (validated, all defaulted):
  `kind_labels` (label→kind map), `quick_label`, `stage_timeout_overrides`
  (optional per-stage seconds), plus validation that quick maps only to
  fix/change kinds. Existing `[budgets]` semantics unchanged.
- `config.example.toml` / `Configuration_Reference.md` updated; wizard
  (`wizard.py`) asks for the ready/kind/quick labels; doctor (`doctor.py`)
  target-repo probe becomes: `.agentic/tools/run.sh` exists +
  `aegis config validate --json` returns ok + schema 3 (replaces any 1.x
  verb probe).
- `docker/Dockerfile.executor-base`: prereqs unchanged (python3 ≥ 3.11,
  node, git, bash) — update comments to name the AEGIS 2.x CLI; refresh
  `required_tool_checks` example.
- Tests: config validation happy/negative; doctor probe against fake
  runner.

### WP7 — Documentation and release

- Update in the same change as the code lands per WP, then finalize:
  `01_Documentation/Integrating_A_Runtime_Project.md` (the new contract
  page: grouped CLI, envelope, run-id pinning, stage cycle, escalation
  semantics), `Operations_Guide.md` (new escalation kinds, waive hint),
  `05_SoftwareDocu/Component_Aegis_Client.md` (new, from template; retire
  `Component_Gates.md`), `Component_Orchestrator.md`, `README.md`,
  `AGENTS.md` status paragraph.
- CHANGELOG: everything under `[Unreleased]`; on user command cut
  **2.0.0** (pyproject + `__init__.py` + packaging scripts aligned).

### WP8 — End-to-end verification

- Full offline suite green on Windows + Linux (CI-equivalent local runs).
- Smoke: `adore doctor` against a scratch repo provisioned with WAEGIS
  (AEGIS 2.1 payload).
- Live pilot (the real acceptance test): one ticket on the Gitea scratch
  setup (`dpasare/adore-gitea-pilot`, tea login `home`) conducted
  end-to-end — `agent-ready` label → AEGIS 2.x run → draft PR — plus one
  revise round and a human merge. Repeat once with `--quick` on a `fix`
  ticket. Record findings in `Prerequisites_Check_Report.md` style.

## 6. Explicitly out of scope (keep it lean)

- No AEGIS 1.x support, detection, or migration of any kind.
- No auto-waive, no auto-merge, no AEGIS state surgery from ADORE.
- No adoption-run conduction; no RepoWise awareness (advisory sidecar is
  invisible to the orchestrator).
- No orchestration of `route_to` stage regressions or `repo-wide` access
  escalation — both park/escalate to a human in 2.0.0.
- No WAEGIS provisioning automation (operators install the payload; doctor
  only checks it is there and valid).

## 7. Risks and open follow-ups

- **Executor discipline:** prompts forbid `stage close`/`waive add`, but
  nothing hard-stops a misbehaving executor from closing stages itself.
  Accepted for 2.0.0 (AEGIS journals every close; MR review catches abuse).
- **Revise vs completed AEGIS run:** post-MR revisions happen after
  `complete: true`; evidence for revision work lands in git history and MR
  discussion rather than the AEGIS run. Acceptable now; revisit if AEGIS
  grows a reopen/amend concept.
- **`[Unreleased]` AEGIS features:** waivers and `--quick` are unreleased
  at plan time — re-verify verb names against the shipped AEGIS version
  before WP1 lands.
- **Windows-host execution:** conduction runs the CLI inside the Linux
  container (`bash run.sh`), so `run.ps1` is only relevant to doctor hints
  on host-side checks — keep doctor container-based to avoid a second code
  path.
