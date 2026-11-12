<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-bea4c0aa — Configured direct verification

Status: active. This spec defines the verification state machine and evidence
semantics. The journal coverage table assigns each independently observable
response to its own requirement; referencing this shared state machine does not
merge those requirements.

## Authority and existing boundaries

- STATED (ticket #63 Decisions; direct-workflow plan sections 1 and 4.2–4.7):
  direct build completion enters conductor-owned validate; an optional command
  gates the candidate; failure returns to bounded fresh-session fixes; AEGIS
  ignores the setting. Human candidate-bound approval and the no-merge boundary
  remain unchanged.
- STATED (TASK-48ef7915 RULING-002): a dedicated owned native verification-only
  platform-shell operation is authorized. Ordinary native argv shell refusal,
  existing ownership supervision and process cleanup remain authoritative; no
  interpreter-wrapper bypass is authorized.
- STATED (repository Testing and Stored data rules): malformed external evidence
  fails closed with a typed error; there is one current stored shape, no migration
  or automatic repair of older/corrupt stores.
- OBSERVED (`adore/orchestrator.py::_conduct_direct`, `_successful_transition`,
  `_stage_failure`, `retry`): direct completion already persists implementation
  and validate together; ordinary successful transitions clear stage_failures;
  stage failures increment and retain history, and explicit retry re-arms the
  counter without resetting cumulative run budgets. The new direct remediation
  cycle must preserve verification failures without changing the AEGIS helper's
  accounting.

## State machine

All rows retain ordinary cancellation, handoff, overall budget and required
notification boundaries. Verification does not authorize extra launches after
an exhausted overall budget. The table concerns only a configured direct run.

| State / trigger | Required observable outcome |
|---|---|
| build, settled successful Pi attempt, no questions, changed non-exchange product progress | Persist implementation completion and validate before command execution. |
| build, questions or unsuccessful/unsettled/no-product-progress attempt | Existing direct clarification/failure behavior; no verification-based approval. |
| validate, retained completed implementation | Execute the configured command in the bound run environment from its worktree root, using the validate timeout. |
| validate, valid exit zero and no typed timeout | Save passing evidence; final checkpoint and candidate/target fingerprint precede done/awaiting-approval. |
| validate, valid nonzero exit without timeout, failed-attempt count below the configured limit | Save failing evidence and count one validate failure; return to build. |
| validate, authoritative timeout, failed-attempt count below the configured limit | Save explicitly timed-out evidence and count one validate failure; return to build. |
| build after verification failure | Launch a fresh Pi session carrying the failing command, exit code and retained output tail. |
| remediation build succeeds and enters validate again | Preserve the consumed stage-failure budget; run verification again. |
| failure count reaches recovery.max_stage_failures | Terminal failed/VERIFICATION_FAILED, retaining the last evidence; no further autonomous remediation launch. |
| explicit operator retry of exhausted verification | Existing retry guards re-arm stage_failures; retain worktree, history, last evidence and cumulative budgets. |
| corrupt execution or persisted result | Typed refusal through existing execution/state integrity handling; no fabricated pass or candidate approval. |

STATED (ticket Decisions): a timeout is one failed attempt, not a separate
infrastructure retry allowance. OBSERVED (`CommandResult.timed_out`): an ordinary
exit 124 is not proof of a timeout. A timeout flag overrides exit zero for pass
classification. The output evidence and remediation context explicitly say
`timed out` when that flag is true.

STATED (ticket limit and existing stage-failure accounting): at a limit of one,
the first failed verification is terminal. At a limit of three, repeated
verification failures cannot be erased by successful intervening fix sessions.
Successful independent validation may complete the existing transition/reset;
explicit retry is the existing operator-authorized re-arm boundary. This does
not introduce a second counter or a new AEGIS reset policy.

## Evidence and trust boundaries

STATED (ticket Evidence): `RunState.validation_evidence` retains the existing
summary/completed-implementation information plus the latest configured command,
exit code, duration and last at most 200 output lines through the existing
sanitiser. Evidence survives save/reload, failure and the start of remediation;
a subsequent invocation replaces the previous verification result, so fail then
pass exposes the pass, not stale failure data. A terminal failure keeps the last
result. Pi's own summary remains separately identified as agent-reported checks.

OBSERVED (`CommandResult` and `_sanitize`): backend outcomes provide integer
exit code, boolean timeout and separate text streams; `_sanitize` removes NUL
and redacts common credential forms, with existing character bounds.
INFERRED (ticket's command-output evidence and those backend fields): retained
output must account for captured stdout and stderr, without promising
inter-stream chronological ordering that the backend does not provide. The Design D7 in `../tasks/TASK-48ef7915.md` chooses deterministic
stdout-then-stderr composition and the exact configured-result field layout.
The 200-line tail and existing character/redaction bounds apply before evidence
is retained or sent to a fresh session or forge. A credential must not become
visible merely because a cut splits its marker from its value. The final character
cut may expose leading whitespace in the retained tail; readback preserves that
text while checking sanitation, normalized line endings and bounds independently,
without trimming or selecting the tail again.

STATED (repository fail-closed rule): a boolean is not an integer exit code;
a timeout flag is a boolean; streams are text; elapsed duration is finite and
nonnegative in seconds. Malformed result values are typed integrity failures,
not command failures to guess/coerce into a passing result. Missing, failed,
timed-out or malformed configured-result evidence never authorizes publication.
Existing unconfigured direct evidence remains an explicit unverified alternative,
not a successful configured command.

STATED (ticket Pass and existing approval contract): the candidate fingerprint
and target commit bind the evidence and fresh human approval. An intervening
candidate/target change cannot reuse an earlier pass to publish an unverified
integrated candidate. The final checkpoint/fingerprint follows successful
verification of the candidate being presented. Existing pre-integration/progress
checkpoints remain possible; they are not approval evidence.

## Examples and acceptance seeds

- STATED (ticket Done when): a fake product-changing Pi attempt followed by a
  passing command records command/exit/duration/output and reaches awaiting
  approval; the approval comment and subsequently published body retain command
  and result after state reload.
- STATED (ticket Done when): a verifier fails once and passes next time; the
  second fresh Pi session receives the sanitized first failure and final stored
  verification is the pass.
- STATED (ticket Done when): repeated failures at max_stage_failures stop with
  VERIFICATION_FAILED and preserved evidence; explicit retry re-arms, subject to
  the same cumulative run limits.
- STATED/OBSERVED (ticket and typed timeout contract): a timed_out result with
  captured output consumes one failure and says timed out; exit 124 alone is
  an ordinary failed command. A typed timeout with exit zero cannot pass.
- STATED (ticket configuration negatives and repository trust rules): bad config,
  corrupt backend results or corrupt saved configured-result evidence cannot
  produce approval, while a valid control input proves the clear path.
- STATED (ticket AEGIS boundary): configuring a command whose fake runner would
  fail on invocation does not change an AEGIS pass/failure/remediation sequence.

## Design handoff and non-goals

- OBSERVED (implemented in `orchestrator.py`, `local_execution.py`,
  `local_process.py` and `prompts.py`): Design D3–D8 in
  `../tasks/TASK-48ef7915.md` define the evidence keys, native verification-only
  operation/platform-shell selection, direct-only transition accounting,
  durable remediation context and opt-in native tail capture. Linked offline
  tests prove the targeted build candidate; final strict proof remains validate's
  responsibility.
- OBSERVED/INFERRED (existing prefix capture versus this tail contract): native
  tests must prove actual tail retention beyond the transient capture bound,
  with split credentials redacted before eviction and default AEGIS/preparation
  capture unchanged. Do not treat a bounded prefix as the end of the output.
- STATED (ticket and Frame): if that accounting cannot share existing
  max_stage_failures without changing AEGIS behavior, stop in the questions file.
- STATED (ticket Out and repository rules): no dedicated web field, suggestion,
  Jobs presentation, migration, new stored top-level workflow field or AEGIS
  payload change is part of this contract. Generic web config serialization
  preserves the key through its existing read/write/redaction/authority seams.
