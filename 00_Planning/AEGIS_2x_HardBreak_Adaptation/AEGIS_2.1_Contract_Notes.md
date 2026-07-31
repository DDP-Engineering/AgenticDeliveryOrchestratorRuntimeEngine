<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 2.1 Contract Notes (orchestrator-facing snapshot)

Snapshot of the AEGIS contract facts ADORE 2.0 is built against, taken
2026-08-01 from `D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System`
at AEGIS payload **2.1.0** / WAEGIS **1.1.0** (plus `[Unreleased]`: waivers,
`--quick` profiles, concurrency-safe locking). Workflow and run-graph schema
**3**. Canonical sources are listed at the end.

**Re-verified 2026-08-01 against the live payload** (working tree at commit
`5a9d43d`) before WP1. The command inventory, stage sequences, exit codes,
and the four-key envelope hold exactly as written. Section 11 records the
detail-level divergences found during that pass; sections 2, 5, and 7 were
corrected in place. Waivers and `--quick` are implemented in the payload and
documented in `CLI_API_REFERENCE.md`; they are still accrued under the AEGIS
`[Unreleased]` heading, so ADORE targets the payload as shipped in the
working tree, not a tagged AEGIS release.

## 1. Invocation

- Wrappers in every payload-installed repo (both delegate to
  `.agentic/tools/run_aegis.py`, which needs Python 3.11+):
  - POSIX / container: `bash .agentic/tools/run.sh <group> <action> [args]`
  - Windows host: `.\.agentic\tools\run.ps1 <group> <action> [args]`
- Interpreter resolution: `$AEGIS_PYTHON` → `$WAEGIS_HOME/runtime-python`
  pointer → `python3`/`python` (POSIX) or `py -3`/`python` (Windows).
- Invoke with CWD = the repo root containing `.agentic/` (root discovery walks
  up from CWD). Guard hooks additionally require `node` on PATH.
- Global options, position-independent: `--run <run-id>` (pin a run without
  moving the pointer), `--json` (stable machine output). ADORE always passes
  both. `_normalize_global_options` moves them ahead of the group, so trailing
  placement is safe.
- **`run.sh` exits 2 with plain text on stdout/stderr when it cannot resolve a
  Python interpreter.** That is an unparseable exit-2 response and must be
  treated as a broken payload, not a workflow state.

## 2. Response envelope and exit codes

Every command returns (text: first four lines; `--json`: one object with the
same keys plus command-specific extras):

```
status:   ok | blocked | failed
stage:    <stage-or-none>
artifact: <path-or-none>
next:     <exact-next-command-or-none>
```

- Exit 0 — `status: ok`.
- Exit 1 — governance signal: `status: blocked` (typed error, always with
  `error`; **only `ConfigurationError` also carries the structured
  `code` / `config_path` / `key_path` / `received` / `expected` / `message` /
  `remediation` fields**) or `status: failed` (a verify/scope action found
  blocking findings).
- Exit 2 — argparse usage error (also the wrapper's "no Python" code). For
  ADORE this means the orchestrator built a bad command or the payload is
  broken: an ADORE/payload defect, never a workflow state.

`next` is the machine-actionable "what to do now" command and is the primary
progress signal. Completion = `complete: true` and `next: "none"` after
delivery close.

### Per-command `--json` extras ADORE relies on

| Command | Extra keys |
|---|---|
| `run start <kind> [--quick]` | `run_id`, `kind`, `run_profile` (only when quick) |
| `run status` / `run resume` / `run select` / `delivery show` | `run_id`, `complete`, `readiness` (the whole `stage show` mapping, `{}` once complete), `evidence[]` (compact: `id`, `kind`, `result`, `status`, `check_id`), `run_profile`/`bypass_status`/`bypassed_stages` on quick runs |
| `stage show` | `run_id`, `stage`, `revision`, `imported_revision`, `state`, `files[]`, `ready` (bool), `blockers[]` (human-readable strings), `warnings[]`, `artifact`, optional `waived_blockers[]` |
| `stage apply` | `revision`, `digest` |
| `stage close` | `complete`, quick details, optional `advisories[]` |
| `verify run` / `verify status` | `verification` (the full validation summary), `artifact` = the `validation-summary.json` path |
| `delivery report` | `report` (repo-relative `report.md` path) |
| `waive list` | `active_waivers[]`, `waiver_history[]`, `eligible_blockers[]` |
| `config validate` | `schema_version` (3), `integration_schema_versions` |

`run resume` returns **the same payload as `run status`** — there is no prose
orientation brief in AEGIS 2.x (see section 11.1).

## 3. Command inventory (full)

```
aegis run start <feature|fix|change|adoption> [--quick]
aegis run status | resume | select <run-id>
aegis stage prepare | add | show | apply | close
aegis requirement list | show <id>
aegis check prepare | record | run [<check-id>...]
aegis evidence prepare <add|supersede> | apply | show
aegis waive add <blocker-id> --reason "<text>" | waive list
aegis verify run | status | invariants | traceability | coverage | working-tree
aegis verify gates [build|typecheck|lint|test|security]... | impact [paths-file]
aegis delivery show | report
aegis adoption component-status | scope-check <path>... | baseline
aegis config validate | show
```

Content enters through generated forms (TOML/MD under
`.agentic/runs/<id>/stages/<stage>/`), not CLI flags. Per-stage cycle:
`prepare` (generate form) → agent fills form → `apply` (validate + import) →
`close` (approval; advances and prepares the next stage).

## 4. Stage sequences

- Standard (`full` profile, 8 stages):
  `intake → alignment → requirement → design → check → implementation → validation → delivery`
- Quick (`--quick`, only for `fix`/`change`, 4 stages; the four skipped
  stages are journaled `bypassed`):
  `intake → implementation → validation → delivery`
- Adoption (7 stages): `adoption-intake → adoption-alignment →
  repo-discovery → component-map → component-adoption → baseline-review →
  adoption-delivery`
- Run kinds: `feature`, `fix`, `change`, `adoption`.
- `--quick` with `feature` or `adoption` returns a typed `blocked` response
  before any run state is created.

## 5. State files (per target-repo worktree)

| Path | Notes |
|---|---|
| `.agentic/workflow.toml` | policy, strict closed schema 3 |
| `.agentic/.workspace/state/current_run` | active-run pointer, git-ignored. ADORE 2.0 does **not** read it — it pins `--run` instead |
| `.agentic/.workspace/locks/` | OS process locks; never delete |
| `.agentic/runs/<id>/graph.json` | authoritative run graph, schema 3, strict/closed |
| `.agentic/runs/<id>/journal.jsonl` | `{"time","event","data"}` per line |
| `.agentic/runs/<id>/design.md` | authoritative design (INV-10) |
| `.agentic/runs/<id>/stages/<stage>/` | stage input forms |
| `.agentic/runs/<id>/validation-summary.json` | written by `verify run` |
| `.agentic/runs/<id>/report.md` | delivery report |

Run-ID pattern:
`^(feature|fix|change|adoption)-(YYYY-MM-DDTHHMMSSZ)-[0-9a-f]{8}$`.

`graph.json` keys ADORE consumes: `run_id`, `stage`, `complete`, `profile`,
`evidence[]`, `stage_records{}`, `waivers[]`.

- `evidence[]` items: `id`, `kind` (`test-run|diff|scan|gate|decision|note`),
  `result` (`pass|fail|info`), `summary`, `status` (`active|superseded`),
  `failure_kind`, `command`, `path`, `stage`, `check_id`, `gate_name`,
  `exit_status`, `output_log`, `created_at`.
- `stage_records{}` items: `status` (`not-prepared|prepared|applied|closed`),
  `unresolved_questions[]`, `requested_access_mode`, `route_to`, `revision`,
  `artifact`, `payload`, …
- **`profile` is omitted from `graph.json` when it equals `"full"`**, and
  `waivers` is omitted when empty. Absence means the default; readers must
  not treat a missing `profile` as corruption.

`validation-summary.json` (written by `verify run`): `schema_version` (3),
`run_id`, `generated_at`, `sequence[]`, `regression_selection`, `impact`,
`gates{name: {status, commands, …}}` (`status` ∈ `passed|failed|disabled|
waived`), `security_note`, `invariants[]` (`id`, `name`, `holds`, `policy`,
`message`, optional `status: "not-applicable"`, optional `waived`),
`traceability[]`, `coverage[]`, `working_tree{entries, untracked,
blocking_findings[]}`, `human_diff_review`, plus `run_profile` /
`bypass_status` / `bypassed_stages` / `waived` where applicable.

## 6. Verification and gates

- `aegis verify run` executes: impact selection → all enabled gate groups
  (fixed order: build, typecheck, lint, test, security) → invariants
  INV-1..INV-10 → traceability → coverage → working-tree review; writes
  `validation-summary.json`; exit 1 on blocking findings. Its response
  `status` flips from `ok` to `failed` when the exit code is non-zero.
- Gate group modes: `disabled` | `enforce`. Disabled reports `disabled`,
  waived reports `waived` — never `passed`.
- Quick runs report absent-stage invariants as `not-applicable`.
- The internal per-gate-command timeout is 300 s; a whole `verify run` can
  take considerably longer, so ADORE gives it the long wrapper timeout.

## 7. Blockers, waivers, escalation triggers

- Waivable blockers (IDs from `aegis waive list --json` →
  `eligible_blockers[]`): e.g. `INV-10`, `gate:test`,
  `red-before-green:<check-id>`, traceability/coverage/working-tree findings.
  Cleared only by a human-approved `aegis waive add <id> --reason "..."`;
  renders `waived`, never passed.
- Non-waivable integrity floor (state repair or human only):
  schema-corrupt state, `PERSISTENCE-LOCK-TIMEOUT` (15 s lock wait),
  `GRAPH-STALE-UPDATE`, `REQUIREMENT-STALE-UPDATE`, journal/publication
  integrity failures.
- Run-resolution errors: `RUN-POINTER-MISSING|INVALID|STALE`,
  `RUN-ID-NOT-FOUND`.
- **These codes are not separate JSON fields.** Except for configuration
  errors (which carry `code`), the code is embedded in the `error` string:
  `RunResolutionError` and `LockTimeoutError`/`GraphConflictError` render as
  `"<CODE>: <message>…"`, while `RequirementConflictError` renders as
  `"<path>: stale_update: REQUIREMENT-STALE-UPDATE: …"`. A classifier must
  scan the whole `error` text for the code, not just its prefix.
- Human-attention state inside the graph: non-empty `unresolved_questions` /
  `open_questions`, alignment `decision = "pause"`, `requested_access_mode =
  "repo-wide"`, `route_to` requests. **`stage show` does not expose
  `unresolved_questions` as its own key** — the questions are folded verbatim
  into `blockers[]`. The structured list lives in
  `graph.json` → `stage_records[<stage>].unresolved_questions`.

## 8. Delivery boundary

AEGIS delivery close marks `complete: true` and **never pushes, publishes,
merges, or creates an MR/PR**. AEGIS has no forge client; Git is read-only
(secret scan over diffs, working-tree audits). Publication is entirely the
orchestrator's job — unchanged division of labor from ADORE 1.x.

## 9. Runtime prerequisites (executor container)

Unchanged from ADORE 1.x expectations: Python ≥ 3.11 resolvable as
`python3`, `node` on PATH (guard hooks fail closed at transport level but
their absence is otherwise silent), `git`, `bash`. The AEGIS CLI itself is
stdlib-only.

## 10. Canonical sources (AEGIS repo)

- `05_Software/aegis/template/.agentic/documents/CLI_API_REFERENCE.md`
- `05_Software/aegis/template/.agentic/documents/WORKFLOW_CONFIGURATION.md`
- `05_Software/aegis/template/.agentic/cli/src/aegis/cli.py` (envelope, exit codes)
- `05_Software/aegis/template/.agentic/cli/src/aegis/store.py`, `models.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/stage_forms.py` (`next`, `show_stage`, `stage_blockers`)
- `05_Software/aegis/template/.agentic/cli/src/aegis/verification.py` (validation summary)
- `05_Software/aegis/template/.agentic/cli/src/aegis/persistence.py` (lock codes)
- `05_Software/aegis/template/.agentic/tools/run.sh` (wrapper exit 2)
- `06_SoftwareDocu/AEGIS_PERSISTENCE_AND_CONCURRENCY.md`

## 11. Divergences found during the 2026-08-01 re-verification

Nothing in the plan's locked design decisions (section 3 of the adaptation
plan) is invalidated. The following details differ from the first snapshot
and are already corrected above; each names the ADORE-side consequence.

1. **`run resume` is not an orientation brief.** `_dispatch` routes every
   `run` action other than `start`/`select` to `_run_status`, so `resume`
   returns the status envelope. *Consequence:* WP4's
   `_workflow_orientation()` composes the brief itself from the envelope
   (run-id, stage, `next`, readiness state/blockers, recent evidence)
   instead of quoting free text.
2. **`stage show` has no `unresolved_questions` key.** Questions are
   readiness blockers (`_stage_readiness_descriptions` seeds the list from
   `record.unresolved_questions`). *Consequence:* the structured question
   list is read from `graph.json` → `stage_records[<stage>]`; `stage show`
   only tells ADORE whether the stage is `ready`.
3. **Typed error codes are inside the `error` string.** Only
   `ConfigurationError` contributes structured `code`/`key_path`/
   `remediation` fields. *Consequence:* `classify_block()` scans the whole
   `error` text; `AegisResponse.remediation` falls back to the trailing text
   when the structured field is absent.
4. **`graph.json` omits `profile` for full runs and `waivers` when empty.**
   *Consequence:* readers default a missing `profile` to `"full"` and must
   not treat the absence as a malformed graph.
5. **`run status` is richer than assumed.** It already embeds the whole
   `stage show` mapping under `readiness` plus a compact `evidence[]`.
   *Consequence:* the conduction loop can take stage, readiness, blockers,
   and completion from one call; `stage_show` stays available for the
   dedicated readiness re-check and is used where the plan names it.
6. **`run.sh` can exit 2 with non-JSON output** when no interpreter resolves.
   *Consequence:* exit 2 is treated as a protocol/payload defect (escalate),
   which is what the plan already prescribes — worth stating because it is
   reachable without any ADORE bug.
7. **`verify run` flips `status` to `failed`** (from `ok`) when its exit code
   is non-zero; the envelope is otherwise a normal success payload with a
   `verification` summary. *Consequence:* verification failure is read from
   the exit code plus `status`, and the evidence comes from
   `validation-summary.json`, not from an `error` field.
