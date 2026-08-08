<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: AEGIS Client (`adore/aegis.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/aegis.py` - file version 0.1.0.
> Contract: `00_Planning/AEGIS_3x_HardBreak_Adaptation/AEGIS_3.0_Contract_Notes.md`.
> Plan: `ADORE_3.0_Adaptation_Plan.md` WP1.

## 1. Purpose

The single place in ADORE that knows how to talk to AEGIS. ADORE 3.0 speaks
exactly one governance contract - the grouped AEGIS 3.x CLI - and this
component owns the invocation shape, the response envelope, the exit-code
discrimination, and the typed errors that turn a broken contract into an
escalation instead of a silent degradation.

## 2. Responsibilities

- Compose the invocation: `bash .agentic/tools/run.sh <group> <action> [args]
  [--run <id>] --json`, as single argv tokens (WSL-safe), executed inside the
  run's container through the injected exec seam.
- Pin the run explicitly. The AEGIS run id captured at `run start` is stored
  on the client and passed as `--run` on every later call, so the worktree
  pointer `.agentic/.workspace/state/current_run` is never read.
- Parse the stable four-key envelope into the frozen `AegisResponse`
  (`status`, `stage`, `artifact`, `next_command`, `exit_code`, `raw`, `argv`)
  with helpers `ok` / `blocked` / `failed` / `complete` / `error` / `code` /
  `remediation` / `detail(key)`.
- Discriminate outcomes: exit 0 and exit 1 are workflow signals returned as
  data; every other exit code, unparseable output, or malformed envelope
  raises.
- Expose exactly the conductor-facing wrappers: `run_start`, `run_status`,
  `run_resume`, `stage_show`, `stage_close`, `verify_run`, `delivery_report`,
  `waive_list`, `config_validate`.

Explicitly not owned: what to do with a result (the orchestrator decides
retry / park / close / escalate), and the stage work itself (the executor
runs `stage prepare|apply`, `check`, `evidence`). The client never calls
`waive add` - waiving is a human decision (plan design decision 3).

## 3. Implementation Overview

`AegisClient` holds the bound exec seam plus the current `run_id`. All
wrappers funnel through `invoke()`:

1. Build `["bash", WORKFLOW_CLI, *argv]`, append `--run <id>` unless the
   command is `run start` or `config validate`, append `--json`.
2. Refuse a run-scoped command when no run id is known
   (`AegisProtocolError`) - there is no pointer fallback.
3. Run through the exec seam with the command family's timeout.
4. Map the exit code: `124` -> `AegisTimeoutError`; anything outside `{0, 1}`
   -> `AegisProtocolError` (argparse usage error, or the wrapper's own exit 2
   when it cannot resolve a Python interpreter).
5. Decode stdout as JSON and validate structurally: object, all four envelope
   keys present and string-typed, a known `status`, and a status consistent
   with the exit code.

`run_start` additionally validates the minted `run_id` against the documented
pattern before storing it, which also guarantees it is a single safe path
segment under `.agentic/runs/`.

`AegisResponse.code` scans the whole `error` text for a known stable code
because AEGIS exposes `code` as a JSON field only for configuration errors;
run-resolution and persistence failures embed it in the message (contract
notes 11.3). A declared `code`/`remediation` field always wins.

## 4. Dependencies

- Internal: `adore.executor.base.ExecTarget` (the exec-seam protocol).
- External: the AEGIS 3.x payload inside the target repo worktree
  (`.agentic/tools/run.sh`, needing Python >= 3.11 and bash in the container).

## 5. Inputs And Outputs

- Inputs: group/action argv, an exec seam bound to the run's container, the
  AEGIS run id, per-command timeouts.
- Outputs: an `AegisResponse` per successful invocation, or one of
  `AegisProtocolError` / `AegisTimeoutError`.

## 6. Data Contracts

- Entry point: `.agentic/tools/run.sh` (`WORKFLOW_CLI`).
- Envelope keys: `status` (`ok|blocked|failed`), `stage`, `artifact`, `next`.
- Exit codes: `0` = ok, `1` = governance signal (blocked/failed), `2` = usage
  or missing-runtime defect, `124` = ADORE-side timeout.
- Run kinds: `feature`, `fix`, `change`, `adoption`; `--quick` is valid only
  for `fix` and `change` and is rejected client-side otherwise.
- Run-id pattern:
  `^(feature|fix|change|adoption)-YYYY-MM-DDTHHMMSSZ-[0-9a-f]{8}$`.
- Timeouts: `STATUS_TIMEOUT` 300 s (status/resume/show/list/config),
  `DEFAULT_TIMEOUT` 600 s (start/close/report), `VERIFY_TIMEOUT` 1800 s
  (`verify run`).
- Recognized stable error codes: `PERSISTENCE-LOCK-TIMEOUT`,
  `GRAPH-STALE-UPDATE`, `REQUIREMENT-STALE-UPDATE`, `RUN-POINTER-MISSING`,
  `RUN-POINTER-INVALID`, `RUN-POINTER-STALE`, `RUN-ID-NOT-FOUND`.

## 7. Workflow Integration

The conductor builds one client per run from the container exec seam and the
run id persisted in `RunState.aegis_run_id`. It drives the AEGIS stage cycle
through this component and reads failure evidence from the run-local files
the same run id addresses.

## 8. Usage

```python
aegis = AegisClient(execute, run_id=run.aegis_run_id or "")
if not aegis.run_id:
    aegis.run_start("fix", quick=True)
    run.aegis_run_id = aegis.run_id
status = aegis.run_status()
if status.complete:
    ...
```

## 9. Validation And Tests

- `tests/test_aegis.py` (16 tests): happy envelope with `--run`/`--json`
  pinning; blocked envelope with code and remediation recovery; declared
  configuration code preferred over the text scan; failed `verify run` as data
  with the long timeout; run-id capture and later pinning; `--quick` argv;
  client-side rejection of unsupported kind/profile combinations; missing or
  malformed `run_id`; run-scoped command with no run id; exit 2; timeout exit
  124; unparseable JSON; non-object payload; missing and mistyped envelope
  keys; unknown status and exit-code/status contradictions; wrapper-to-verb
  mapping.
- Minimum validation after a change: `python -m pytest -q` from `04_Software`.

## 10. Limitations And Future Work

- Only the conductor-facing subset of the AEGIS surface is wrapped.
  `requirement`, `check`, `evidence`, `adoption`, and the granular `verify`
  actions are executor-facing and intentionally absent.
- `waive add` is deliberately not wrapped; escalations carry the exact command
  for a human instead.
- No AEGIS 1.x support, detection, or migration exists anywhere in this
  component - an unsupported payload escalates.
