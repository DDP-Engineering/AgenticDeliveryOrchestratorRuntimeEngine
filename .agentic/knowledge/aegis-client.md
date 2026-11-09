<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS client

## Routing

Use this page for AEGIS version and schema probing, task creation and status
reads, strict-check decoding, the stage transition rules and the run-container
file exchange. Start at `04_Software/adore/aegis.py`; focused proof is
`04_Software/tests/test_aegis.py`. Conduction, approval and publication belong
to `orchestrator.md`, host readiness reporting to `doctor.md`, shared
execution/recipe policy to `execution.md` and `preparation.md`, and native
ownership/auth to `local-execution.md` (proof in
`04_Software/tests/test_local_execution.py`).

## Purpose and boundaries

`04_Software/adore/aegis.py` is ADORE's sole companion-governance boundary. It
speaks the installed AEGIS Python CLI at 0.15.0 or later within major 0 and its
schema-1 JSON contract; an older release or a major bump is refused at probe.
The executor advances the task journal through AEGIS itself, including the
validate stage's final check, `report` and `advance` to done; the orchestrator
decides what to do with the decoded task and check data.

## Public interface

`AegisClient` probes a target (`probe`), creates a task (`create_task`), lists
and reads task journals (`list_tasks`, `task_status`) and runs the advisory or
strict check (`check`); the executor runs `anchor`, `test`, `evolution` and
`report` itself. `allowed_transition`, `evidenced_transition` and
`logged_stages` rule on executor-authored stage moves. `AegisTask.deviations`
harvests the journal's `DEVIATION <stage>` entries with the marker rule AEGIS
uses for its own report. The validated value objects (`AegisProbe`,
`AegisTask`, `AegisCheck`, `AegisFinding` and `AegisCommandRun`) expose only
decision-safe data to the orchestrator.

## Invariants

- The conducted paths are frame -> specify -> design -> build -> validate ->
  done and, for fix and change, frame -> build -> validate -> done. A working
  stage may return to an earlier stage on its selected path; done returns only
  to validate. Other forward moves require journal evidence for every stage
  crossed.
- The pinned task decodes only at a conducted stage with the step file AEGIS
  0.15.0 names (none for done); a task at `deliver` fails closed. Status
  listings and deviation markers accept AEGIS's own vocabulary, including the
  legacy `deliver` stage and the adoption phases, so a foreign journal never
  blocks a probe.
- Host pre-pick probing uses direct argv. Calls from a run container write an
  LF-only, POSIX-quoted `aegis.sh` and invoke exactly the backend shell and
  native IO path (container default `sh /adore/io/aegis.sh`); bounded UTF-8
  exchange files replace wrapper output.
- Malformed JSON, path escapes, unknown schema or version, missing or oversized
  exchange files, unexpected exits and typed timeouts fail closed as typed
  AEGIS errors.
- The client never edits a journal, advances a stage, approves publication,
  commits, pushes or calls a forge.

## Key behaviors

Captured managed CLI output in tests/fixtures/aegis_0_15_0.json proves supported
serialization through injected execution; the older fixture proves refusal.
AEGIS owns backward routing to earlier stages on the selected path. A done
task returns only to Validate for governed revalidation; forward jumps retain
the journal-evidence rule.

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: AegisClient uses native run_files for local Python argv with the same bounded strict file/AEGIS JSON contracts. Container shell transport remains available. Native Python paths may contain spaces.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-8472a560` - AEGIS outside major 0 or older than 0.15.0 is refused at
  probe with an error naming 0.15.0.
- `REQ-FUNC-16237c6d` - pinned task identity, 0.15.0 stages and step files, and
  internally consistent strict-check evidence.
- `REQ-FUNC-faab24b2` - done -> validate is the legal return when ADORE must
  revalidate a candidate.
- `REQ-FUNC-ab65704b` - deviations are harvested with AEGIS's own marker rule.
- `REQ-FUNC-4fe259b0` - bounded container exchange and typed timeout handling.
- `REQ-FUNC-e397f7f6` - file transport uses the bound backend worktree, IO and
  shell paths, quoted, including spaces; direct host probes keep argv.
- `REQ-FUNC-ffb9ed29` / `REQ-UX-b75e1df8` - native `run_files` launches local
  Python argv under the same bounded file and JSON contracts.

## Files

- `04_Software/tests/test_aegis_compatibility.py`: captured supported and refused companion replay.
- `04_Software/tests/fixtures/aegis_0_14_0.json`: historical CLI evidence and release hashes.
- `04_Software/tests/fixtures/aegis_0_15_0.json`: supported managed CLI serialization.

- `04_Software/adore/aegis.py` - implementation.
- `04_Software/tests/test_aegis.py` - public boundary verification.
- `04_Software/tests/test_local_execution.py` - native integration and negative
  proof.
