<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0 Contract Notes (orchestrator-facing snapshot)

This is the contract snapshot for the ADORE 3.0 hard break. It was
re-verified on 2026-08-08 from the clean checkout
`D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System`.
The authoritative source pin is
`676b754f438fd82f0f48692c874bd9c8340a96b0` on branch `master`.

- AEGIS release and payload version: **3.0.0**, released 2026-08-08
- WAEGIS version: **3.0.0**
- WAEGIS payload compatibility: **`>=3.0.0,<4.0.0`**
- Workflow and run-graph schema: **3**
- Fresh-session context schema: **1**

Only this checkout and commit are authoritative for the plan. The historical
`D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System_WAEGIS_V3`
feature checkout and its `a4a5308` pin are stale analysis metadata. The
authoritative checkout is clean on `master` and matches `origin/master`.

AEGIS 3.0.0 contains the governance behavior that previously accrued under
`[Unreleased]`. The development package discovers its Python package directly
from `template/.agentic/cli/src`, so tests and packaging use the exact source
copied into target repositories. AEGIS is a synchronous, standard-library-only
local CLI: no daemon, service, streaming protocol, or network runtime is part
of the command boundary.

## 1. Invocation and process boundary

- POSIX/container wrapper:
  `bash .agentic/tools/run.sh [global-options] <group> <action> [arguments]`
- Windows host wrapper:
  `.\.agentic\tools\run.ps1 [global-options] <group> <action> [arguments]`
- Global machine options are `--run <run-id>` and `--json`. ADORE pins the
  AEGIS run on every command after `run start` and never reads
  `.agentic/.workspace/state/current_run`.
- Although the CLI normalizes global-option placement, ADORE uses the
  canonical placement before the group. This avoids the syntactic collision
  between global `--run <run-id>` and the boolean `verify impact --run` flag.
- The command working directory is the governed repository root containing
  `.agentic/`.
- Runtime prerequisites are Python 3.11 or newer, Bash, Git, and Node. The
  wrapper resolves `AEGIS_PYTHON`, then the WAEGIS runtime pointer, then a
  system Python. If it cannot resolve Python, `run.sh` exits 2 with plain
  stderr rather than a JSON response.

## 2. Machine-response contracts

AEGIS exposes two JSON response families. They must not be parsed through one
universal dataclass.

### 2.1 Standard four-key envelope

Normal commands return the required string keys below, plus command-specific
extras:

```text
status:   ok | blocked | failed
stage:    <stage-or-none>
artifact: <repository-relative-path-or-none>
next:     <exact-next-command-or-none>
```

- Exit 0 means the command completed and carries an `ok` envelope. It does not
  universally mean the governed tool or check passed; `check run` is the
  important exception described in section 6.2.
- For the current nine ADORE wrappers, exit 1 is an expected governance result.
  It carries `blocked` for a typed inability to proceed or `failed` when
  verification found blocking results.
- Exit 2 is an argparse/wrapper defect from ADORE's perspective.
- For a command-specific ADORE wrapper, invalid JSON, missing envelope keys,
  invalid key types, unexpected statuses, and exit codes outside that wrapper's
  contract are protocol failures and must fail loud.
- Typed error names and codes normally appear inside the `error` string.
  Configuration errors additionally expose structured fields such as `code`,
  `key_path`, `received`, `expected`, `message`, and `remediation`.
- An unexpected programming exception may escape AEGIS's normal response
  boundary. ADORE must treat the resulting non-envelope response or unsupported
  exit code as a protocol failure.

The CLI as a whole is not limited to exit 0/1/2. `verify gates` and executable
`verify impact --run` propagate the failing gate tool's return code. This can
be an arbitrary non-zero value, including synthesized 124 for timeout and 127
for an unlaunchable executable. ADORE currently has no wrapper for either
command, so its existing unsupported-exit behavior remains correct. Any future
wrapper must add a command-specific exit contract instead of treating those
codes as generic workflow states.

Important extras used by ADORE include:

| Command | Contract fields in addition to the envelope |
|---|---|
| `run start` | `run_id`, `kind`, optional quick-profile fields, optional `warnings[]` when another selected run is incomplete |
| `run status` / `run resume` | `run_id`, `complete`, `readiness`, `evidence[]`, optional quick-profile fields, optional `outcome` |
| `stage show` | `run_id`, `stage`, `revision`, `imported_revision`, `state`, `files[]`, `ready`, `blockers[]`, `warnings[]`, optional `waived_blockers[]` |
| `stage close` | `complete`, `approver`, quick-profile details, optional `advisories[]` |
| `verify run` / `verify status` | `verification`, with `artifact` naming `validation-summary.json` |
| `delivery report` | `report`, naming the repository-relative `report.md` |
| `waive list` | `active_waivers[]`, `waiver_history[]`, `eligible_blockers[]` |
| `config validate` | `schema_version` and integration-schema information |

`run resume` remains an alias of `run status`. It is not the fresh-session
orientation contract.

### 2.2 `run context --json`

A successful `run context --json` response is intentionally a direct,
versioned context object. It does **not** contain the four envelope keys
`status`, `stage`, `artifact`, and `next`.

The fixed context schema contains:

```text
context_schema_version
run_id
kind
profile
stage
reference
skill
artifact
unavailable_current_artifact
previous_stage_artifacts
unavailable_previous_stage_artifacts
required_reads
next_commands
human_gate
```

Contract details:

- `context_schema_version` is `1`.
- `human_gate` is exactly `stage close`; it tells the executor where to stop
  and must never be forwarded as an executable next command.
- `required_reads` is the bounded, authoritative bootstrap set. It includes
  repository instructions, the relevant skill/reference, the current form,
  and an immediately preceding form when retained. It excludes the whole
  graph, journal, evidence store, workflow configuration, and delivery report.
- Standard and quick `delivery` route through
  `.agentic/skills/agentic-delivery/SKILL.md`. The context reports that same
  path as both `reference` and `skill`, and `required_reads` includes the
  shared router only once; it does not invent a development
  `reference/delivery.md` path.
- Successful JSON context is bounded to 4 KiB; the complete bootstrap pack is
  bounded to 30 KiB.
- If the current stage has no record, the safe recovery command is
  `stage prepare`. If an applied or prepared stage artifact is unavailable,
  recovery is `stage show`; ADORE must not prepare an already applied stage.
- Exit-1 context failures still use the standard blocked envelope. ADORE must
  discriminate by exit code before choosing the success response parser.

The executor bootstrap defined by AEGIS is: read repository instructions,
obtain `run context --json`, follow only a named recovery step when required,
read only `required_reads`, perform the current stage, and stop before
`stage close`.

## 3. Current command inventory

```text
aegis run start <feature|fix|change|adoption> [--quick]
aegis run status
aegis run context
aegis run resume
aegis run list
aegis run select <run-id>
aegis run abandon --reason <text>

aegis stage prepare
aegis stage add [--category <category>]
aegis stage show
aegis stage apply
aegis stage close [--approver <identity>]

aegis requirement list
aegis requirement show <requirement-id>

aegis check create
aegis check register
aegis check prepare
aegis check record
aegis check run [<check-id>...]

aegis evidence prepare <add|supersede>
aegis evidence apply
aegis evidence show

aegis waive add <blocker-id> --reason <text> [--approver <identity>]
aegis waive list

aegis verify run
aegis verify status
aegis verify gates [build|typecheck|lint|test|security]...
aegis verify invariants
aegis verify traceability
aegis verify coverage
aegis verify impact [<paths-file>] [--run]
aegis verify working-tree

aegis delivery show
aegis delivery report

aegis adoption component-status
aegis adoption scope-check <path>...
aegis adoption baseline
aegis adoption coverage-waivers [--write]

aegis config validate
aegis config show
```

Content crosses into AEGIS through generated forms under the current run.
Stage completion checklists are emitted in form comments and stage reference
documents. An executor must use that generated guidance rather than an ADORE
prompt duplicating an independently maintained stage procedure.

## 4. Run profiles and stage progression

- Full feature/fix/change profile:
  `intake -> alignment -> requirement -> design -> check -> implementation -> validation -> delivery`.
- Quick fix/change profile:
  `intake -> implementation -> validation -> delivery`.
- Adoption profile:
  `adoption-intake -> adoption-alignment -> repo-discovery -> component-map -> component-adoption -> baseline-review -> adoption-delivery`.
- Quick is invalid for `feature` and `adoption`.
- A normal stage moves through `not-prepared`, `prepared`, `applied`, and
  `closed`. `stage close` advances the AEGIS-owned stage pointer and normally
  prepares the next stage.
- `run status` plus a profile-specific ADORE allowlist is the conductor's
  source of progression. `run context` is the executor's fresh-session
  bootstrap source.
- A completed normal run has `complete: true` and `next: "none"`.
- A run can instead be abandoned. Its status has `complete: true`,
  `outcome: "abandoned"`, and `next: "none"`. Completion alone therefore does
  not authorize publication.

AEGIS documents `stage close` as a human approval action. In ADORE's conducted
model, ADORE may act as a delegated approver only under an explicit operator
policy. It must pass a stable truthful value through `--approver`; allowing
AEGIS to fall back to Git identity would falsely imply a human performed the
approval. The executor must never close a stage or add a waiver.

## 5. Persisted state read by ADORE

| Path | Relevant contract |
|---|---|
| `.agentic/workflow.toml` | Strict workflow configuration, schema 3 |
| `.agentic/.workspace/state/current_run` | Mutable selected-run pointer; ADORE never reads it |
| `.agentic/.workspace/locks/` | AEGIS process locks; ADORE never deletes or edits them |
| `.agentic/runs/<id>/graph.json` | Authoritative schema-3 run graph |
| `.agentic/runs/<id>/journal.jsonl` | AEGIS event journal; not a primary ADORE evidence interface |
| `.agentic/runs/<id>/stages/<stage>/` | Generated and applied stage forms |
| `.agentic/runs/<id>/validation-summary.json` | Structured verification result |
| `.agentic/runs/<id>/report.md` | Delivery report |

Run IDs match
`^(feature|fix|change|adoption)-(YYYY-MM-DDTHHMMSSZ)-[0-9a-f]{8}$`.

The shipped workflow default is `stage_form_retention = "latest"`, so the
immediately preceding primary form is normally available to `run context`.
The context contract still reports an unavailable predecessor explicitly when
a target uses `discard` or a retained file is missing.

Relevant `graph.json` properties include `run_id`, `stage`, `complete`,
`stage_records`, and `evidence`. `profile` is omitted for a full run;
`waivers` is omitted when empty. New quick graphs carry
`red_green_policy: "required"`. Only historical schema-3 quick graphs without
that field may be treated as `legacy-not-applicable`. An abandoned graph may
carry `outcome: "abandoned"`; a normal run omits `outcome`.

ADORE reads AEGIS files across a trust boundary. It must validate the schema
version, run ID, required object/list shapes, allowed values, and path
containment. Missing, malformed, mismatched, or out-of-worktree artifacts are
typed failures; they are never interpreted as empty evidence or no questions.

## 6. Checks, evidence, and verification

### 6.1 Quick-run evidence is real evidence

Quick no longer permits a manual-evidence shortcut. A new quick run must:

1. define the check with `check create` and fill its generated form;
2. register the check;
3. obtain a real red result before the implementation change;
4. obtain a real green result after the change, through an external or
   AEGIS-managed execution path; and
5. retain active green evidence linked to the check.

INV-3 applies to new quick graphs. The quick profile makes only the invariants
whose absent stages are intentional not applicable: INV-1, INV-2, INV-8, and
INV-10, together with traceability and coverage requirements tied to those
absent stages. ADORE must not describe INV-3 as not applicable.

### 6.2 Nothing-ran is a failed execution

When `check run` or `verify gates` launches no command, AEGIS returns exit 1
with an envelope whose `status` is `failed`. The response includes
`execution_status: "nothing-ran"`, `executed_count: 0`, and a reason. It does
not create passing evidence. ADORE must never promote that response to a
successful stage or verification.

An executed `check run` is different: it exits 0 whether the managed check
passes or fails. Its actual result is carried by `execution_status` and by each
item in `evidence[] -> result` (`pass` or `fail`). Only `nothing-ran` exits 1.
Quick red/green logic must therefore inspect the structured evidence and must
never infer a pass from process exit 0 or envelope `status: ok`.

### 6.3 Verification result vocabulary

`verify run` executes impact selection, enabled gate groups, invariants,
traceability, coverage, and working-tree review, then writes
`validation-summary.json`.

- Top-level validation status: `ok`, `waived`, or `failed`.
- Gate status: `passed`, `failed`, `waived`, `not-enforced`, or `not-run`.
- A disabled aggregate gate is reported as `not-enforced`, not `disabled`.
- `waived` is non-blocking but remains waived; it must never be called passed.
- `not-enforced` is neither passing evidence nor a failure.

`verify impact [paths-file] --run` performs the focused test selection or a
safe full-test fallback. It is execution, not merely a recommendation.

## 7. Blockers, waivers, and advisories

- Waivers are explicit human governance actions. ADORE lists eligible waivers
  and may surface an exact suggested command, but never invokes `waive add`.
- Integrity failures such as `PERSISTENCE-LOCK-TIMEOUT`,
  `GRAPH-STALE-UPDATE`, and `REQUIREMENT-STALE-UPDATE` are not normal executor
  retry prompts. The lock timeout receives at most one bounded retry; the rest
  escalate.
- Run-resolution errors include `RUN-POINTER-MISSING`, `RUN-POINTER-INVALID`,
  `RUN-POINTER-STALE`, and `RUN-ID-NOT-FOUND`. Explicit `--run` prevents ADORE
  from depending on pointer state, but the pinned run can still be missing or
  corrupt.
- Codes generally occur anywhere in the `error` text, not in a dedicated
  field. A classifier must scan the complete error string.
- `stage show` folds unresolved questions into human-readable `blockers[]`.
  The structured question list is in
  `graph.json -> stage_records[stage].unresolved_questions`.
- A successful quick implementation close can include structured
  `advisories[]`, including `QUICK-SCOPE-ADVISORY` with `status`,
  `changed_path_count`, `max_paths`, `message`, and `restart_command`. It is
  intentionally non-blocking, but ADORE must journal and surface it rather
  than silently discard it.
- A blocked `stage close` response currently carries the error and next
  command but does not repeat all readiness fields. The preceding validated
  `stage show` remains ADORE's authoritative readiness snapshot.

## 8. Delivery and ownership boundary

AEGIS delivery close rechecks blocking invariants and completes the governance
run. AEGIS never pushes, creates an MR/PR, publishes, or merges. After a normal
completed outcome, ADORE owns integration, final verification, push, and draft
MR/PR creation. Merge is always a human decision.

`run list`, `run select`, and `run abandon` are operator lifecycle commands,
not conductor progression commands. Automatically abandoning an AEGIS run as
part of ADORE cancellation would require a separate persistence and dirty-tree
design; it is not implicit in this contract adaptation. ADORE must nevertheless
recognize an externally abandoned run and must never publish it.

## 9. Delta and 3.0 release re-pin

The original 2026-08-01 plan targeted AEGIS commit `5a9d43d`, payload 2.1.0,
and WAEGIS 1.1.0. The first refresh targeted `be77ead`, payload 2.1.0, and
WAEGIS 1.2.0. The current 3.0 source retains all of the following
ADORE-facing behavior identified in that refresh:

1. `run context --json` is the bounded versioned fresh-session contract and is
   not a four-key envelope on success.
2. Stage forms contain authoritative completion checklists; ADORE prompts must
   stop duplicating stage mechanics.
3. Quick runs require registered checks and actual red/green execution; INV-3
   applies.
4. Nothing-ran outcomes fail explicitly and never create passing evidence.
5. Validation can be `waived`; disabled aggregate gates are `not-enforced`.
6. AEGIS supports abandoned terminal outcomes, which completion-only ADORE
   logic would otherwise publish.
7. `stage close` accepts an explicit approver and can return non-blocking
   structured advisories.
8. New run-lifecycle and adoption commands exist, but they do not broaden the
   conductor's 3.0 scope.
9. WAEGIS 3.0.0 is the current provisioner/runtime companion and accepts only
   stable AEGIS payloads in `>=3.0.0,<4.0.0`.
10. The shipped stage-form retention default is now `latest`.

The AEGIS CLI contract summarized here is unchanged between the historical
`a4a5308` feature pin and authoritative `master`. Their payload diff is limited
to RepoWise integration messaging/normalization and related prompt/hook
documentation; `stage_context.py`, the grouped CLI response shapes, wrappers,
and WAEGIS 3 implementation are unchanged. This re-pin therefore corrects the
source-of-truth and pilot baseline without changing CR1-CR5's technical design.

The review-supplied candidate `0a1bdbe` is an ancestor of the authoritative
master pin. Subsequent commits complete WAEGIS remediation, record its owner
GO, and promote the release tree to `master`. Pinning the promoted commit
matters for CR6 even though the conductor-facing governance contract is
unchanged.

WAEGIS itself was replaced by WAEGIS 3. It has no editions, RepoWise
management, cloning, branch creation, staging, or commits. Its mutating flows
require a clean committed repository, a complete reviewed plan, and explicit
consent; the operator owns staging and committing the resulting payload.

## 10. Canonical AEGIS sources

- `05_Software/aegis/template/AGENTS.md`
- `05_Software/aegis/template/.agentic/documents/CLI_API_REFERENCE.md`
- `05_Software/aegis/template/.agentic/documents/WORKFLOW_CONFIGURATION.md`
- `05_Software/aegis/template/.agentic/cli/src/aegis/cli.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/stage_context.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/stage_forms.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/verification.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/models.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/store.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/persistence.py`
- `05_Software/aegis/template/.agentic/tools/run.sh`
- AEGIS tests that lock the JSON schemas, quick profile, nothing-ran results,
  abandoned runs, retention behavior, and context size limits.
