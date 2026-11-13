<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-DATA-08ed925c — Direct job evidence reads

Status: active. This specification supplies the source, absence and error semantics
shared by the task's separate attempt and verification requirements. It changes
presentation and the authorized read allowlist, not execution or stored formats.

## Authority and boundaries

- STATED (ticket #66; direct-workflow plan sections 1 and 4): Jobs identifies the
  recorded workflow; a direct job has Implementation (`build`), Validation
  (`validate`), then Done, without an AEGIS task; details show the attempt and
  independent verification command, outcome, duration and output tail.
- STATED (ticket #66 and repository testing rules): unknown workflow is an error;
  malformed external/persisted evidence fails closed; no run-behavior changes,
  migration, compatibility readers or automatic repairs.
- OBSERVED (`adore/orchestrator.py::_launch_stage`): each executor launch journals
  `stage-launch` with `attempt = stage_failures + 1` after incrementing cumulative
  `iterations`. These are different measurements. The requested attempt number
  can be read directly rather than invented from cumulative budget consumption.
- OBSERVED (`adore/orchestrator.py::_verify_direct`, `_direct_result` and
  `specs/REQ-FUNC-bea4c0aa.md`): independent verification retains the latest result
  in `validation_evidence`, including failures/timeouts while the job returns to
  build; explicit absence of configuration is recorded as `not configured`.
- Authorized job reads expose only the narrow direct-evidence projection below.
  General validation payloads, agent summaries, raw transcripts and unrelated fields
  remain outside the read allowlist; `specs/REQ-FUNC-e8455ab6.md` records that exception.

## Source contract

### Recorded attempt

- Use the last saved `stage-launch` event in journal order for the direct job,
  not event timestamp sorting, current `stage_failures + 1`, cumulative
  `iterations`, preparation attempts or review rounds.
- A selected launch's `attempt` is a positive integer representable exactly by
  the browser (at most 2^53 - 1); booleans and fractional values are invalid.
  A present `stage-launch` without a valid attempt is corrupt journal evidence,
  not absence. Validate every projected launch's attempt rather than skipping
  an earlier malformed launch in favor of a later valid one.
- With no recorded launch, the attempt is explicitly unavailable. Zero saved
  launches do not imply attempt one, and a missing journal does not justify a
  fabricated number. This follows the existing honest-unknown read contract.
- This number describes the latest recorded executor attempt; it is not a new
  lifetime attempt counter or a new verification invocation counter. Retry and
  revisions keep their existing engine accounting.

### Independent verification

The current saved configured result is exactly:

```
validation_evidence.verification = "passed" | "failed" | "timed out"
validation_evidence.verification_result = {
  "command": text,
  "exit_code": integer,
  "seconds": finite nonnegative number,
  "timed_out": boolean,
  "output": text
}
```

- OBSERVED (`_direct_result`): result keys are closed; duration excludes booleans
  and numbers outside finite float conversion; output is at most 200 lines and
  6000 characters with normalized line endings and no NUL or ANSI escapes.
  Preserve valid leading whitespace and empty text; do not trim an existing tail
  into a different observation. Projected text must contain valid Unicode scalars.
- Validate the saved structure before redaction/projection. Apply the existing
  web credential masking to command and output for both roles; redact before any
  necessary display-bound cut. Keep the projected output within the same tail
  bounds. Render the result as inert text, never HTML, Markdown links or commands
  to execute. The command is saved evidence, not a link or a runnable web action.
- Status agreement is exact: `timed_out = true` means `timed out` regardless of
  exit code; otherwise exit zero means `passed` and nonzero means `failed`.
  An ordinary exit 124 without timeout means failed. Disagreement is corruption.
- Read the saved command, not today's configuration. Missing or changed project
  configuration does not erase valid saved evidence or replace the recorded
  command; existing budget-unavailable behavior remains separate.
- Only the latest saved result is displayed. A failed or timed-out verification
  remains visible during remediation; a later saved pass replaces it. Lifecycle,
  stage, agent-reported checks and the existence of a candidate do not establish
  an independent verification pass.

## Absence and presentation semantics

| Saved condition | Observable Jobs evidence |
|---|---|
| No verification status and no result | Verification unavailable; no invented command, duration or output. |
| `verification = "not configured"`, no result | Not configured: unverified; no invented command, duration or output. |
| Complete configured result with agreeing status | Saved redacted command first, localized outcome, recorded seconds and inert output tail. |
| Valid configured result with empty output | Explicit empty-output indication, not unavailable verification. |
| Configured status without result, result without status, unknown/nontext status, or unconfigured status with a result | Typed read refusal / browser error, not absence or an inferred result. |

STATED (ticket and repository localization rule): labels and status copy use the
interface's English, French, German and Romanian terms. Implementation and
Validation are direct-workflow display names only; AEGIS stage labels and
existing observed-only timeline behavior retain their current meaning. Done is
still a workflow stage, distinct from lifecycle Completed or human merge.
Unrelated timeline events can have unknown stage; no synthetic progress events
are added. A direct response naming a current or timeline stage other than
build/validate/done is refused, never filtered into a plausible valid timeline.

## Read boundary and error semantics

- Reuse authorized immutable project/run identity, captured state/journal bytes,
  source-revision checks and final grant/profile reinspection. Read no source
  for an unauthorized project. These reads run no external CLI or command and
  change neither source bytes nor operational journal recovery.
- A malformed selected persisted attempt produces `run_journal_corrupt`; malformed
  selected persisted verification produces `run_state_corrupt`. Both use the
  existing typed JobReadError / HTTP 503 secret-free envelope, without partial
  totals or raw source values. Missing evidence is not a corrupt source; present
  malformed evidence is not missing evidence.
- Browser readers validate workflow on list and detail reads before display and
  validate direct evidence on detail reads. Missing, nontext or unknown workflow
  and malformed direct evidence produce the existing unexpected-response/error
  presentation, with stale affected evidence hidden; no workflow default or
  implicit passing/unconfigured result is permitted.
- The read allowlist contains only attempt and verification evidence needed here.
  No AEGIS task binding or agent summary is exposed for a direct job. AEGIS jobs
  acquire only the requested workflow label, not a direct verification panel or
  reinterpretation of their stage/failure counters.

## Acceptance seeds

- First launch attempt 1; later launch attempt 2; cumulative launches 9 and
  current failure count 0 do not replace the recorded 2. No launch stays unknown.
- Passed command with zero/fractional duration and empty output; failed command
  with exit 124 and no timeout; timed out command even with exit zero; explicit
  unconfigured evidence; a pre-verification build with no status/result.
- Failure retained during a fresh build, followed by a saved pass; changing the
  saved project verification setting does not change either observed result.
- Invalid workflow, direct AEGIS-only stage, corrupt launch number, status/result
  contradiction, bad duration, invalid Unicode/NUL and 201-line/6001-character
  output are rejected; valid 200-line/6000-character controls are accepted.
- Admin and assigned Developer see authorized redacted evidence; cross-project
  reads fail without consulting foreign corrupt sources; source bytes are
  unchanged and a runner that fails on invocation proves reads execute nothing.

## Detail transport

A direct
composite detail carries exactly this new closed object within its job:

```
direct = {
  attempt: positive safe integer | null,
  verification: {
    status: "unavailable" | "not configured" | "passed" | "failed" | "timed out",
    result: null | { command, exit_code, seconds, timed_out, output }
  }
}
```

- `direct` and `verification` have exactly the displayed keys; result objects
  have exactly the five source-result keys. The first two statuses require null
  result; the last three require a complete agreeing result. A direct detail
  missing this object is invalid, not an alternate/older transport format.
- `attempt` is null only when the source has no launch. Saved explicit null or
  malformed attempt/status/result is corruption, not absence. Detect absence by
  key presence, not `.get()` treating null as an absent key.
- `command` and `output` are redacted valid Unicode strings; `seconds` is a finite
  nonnegative JSON number after overflow-safe validation, and `timed_out` is a
  boolean. No invented command or measurements accompany the null-result states.
- Named technical constraint: JavaScript cannot preserve arbitrary Python
  integers in a JSON number. The persisted integer `exit_code` therefore projects
  as exact canonical decimal text: `"0"` or optional minus plus nonzero-leading
  digits. This keeps the saved source integer domain unchanged; no plus, leading
  zeros or negative zero are admitted. Browser status agreement checks that text
  against `"0"` after the boolean timeout priority. This transport encoding does
  not change the stored result or normal displayed outcomes.
- Python and browser tail validation use Unicode scalar counts and LF line
  counts, including non-BMP characters; JS UTF-16 length is not a substitute for
  the 6000-character source bound. Preserve leading whitespace. Existing web
  masking precedes any necessary final 200-line/6000-scalar tail cut; malformed
  over-bound source is rejected before masking, not repaired through that cut.
- AEGIS details omit `direct`, and the browser refuses a direct object on AEGIS
  detail. List rows omit `direct` for either workflow; their only new browser
  input is mandatory saved workflow. Internally `_view` computes/validates direct
  evidence with the captured sources before any filter/totals; `jobs_page` strips
  the object alongside timeline. No result or output leaks through list paging.
- Model tests include ordinary and large signed source exit integers, normalized
  decimal-text refusal, non-BMP boundary controls and redaction growth at the tail
  bound. Public API tests retain byte preservation and no-command assertions.

## Implementation and proof

`adore/web/jobs.py::_direct_evidence` validates captured sources without invoking
the orchestrator; `app.py` removes the detail-only object from list results.
`jobModel.ts` validates the closed browser transport, and `JobWorkspace.tsx`
renders localized literal evidence. Existing run state supplies all values;
no stored datum, execution behavior or dependency is added. Offline public HTTP,
model, Jobs browser and four-locale help tests prove the contracts in this spec.
