<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Client Component

## 1. Purpose

`adore/aegis.py` is the sole AEGIS trust-boundary component. ADORE 0.5 speaks
only the Python companion CLI shipped by AEGIS 0.5.x and JSON schema 1.

## 2. Responsibilities

- invoke the host pre-pick probe with direct argv and every run-container
  operation through a shell-quoted file exchange;
- probe exact version series and schema before governed work;
- create/list/read task journals and pin exact task identity;
- expose advisory/strict check, anchor, evolution, configured test and report
  operations;
- validate bounded JSON, UTF-8, contained POSIX paths, headers, stage/path/type,
  checklist/log data, finding counts and verification command results;
- distinguish typed protocol, timeout and task failures;
- decide documented full/quick stage transitions.

It does not edit journals, transition stages, approve delivery, commit, push or
call a forge.

## 3. Implementation Overview

`AegisClient` composes the logical AEGIS argv and accepts injected execution.
Without an io directory it invokes that argv directly for the host-side
repository probe. With a run io directory it writes LF-only `aegis.sh`, quotes
every token with POSIX shell rules, redirects both streams to bounded exchange
files, and gives the wrapped runtime only `sh /adore/io/aegis.sh`. The exchange
files are read on the host and replace container-wrapper streams while keeping
the wrapper exit code and `timed_out` flag unchanged. A timeout remains typed
even if the killed command did not create its files; a completed invocation
requires both files to be readable and within bounds. If container execution
fails before either exchange file exists, the protocol error retains the real
exit and bounded wrapper stderr; a successful wrapper with absent files remains
an exchange-file protocol failure.

`AegisProbe`, `AegisTask`, `AegisCheck`, `AegisFinding`, and
`AegisCommandRun` expose only validated decision data. Unknown JSON fields may
be present, but ADORE does not use them for decisions.

## 4. Dependencies

Internal dependencies are the branding mount constants,
`adore.executor.base.ExecTarget`, and `adore.util.CommandResult`. The external
dependency is the target repository's unchanged `.agentic/aegis.py` payload
and Python runtime.

## 5. Data Contracts

- supported version: `aegis 0.5.x`;
- supported JSON schema: integer `1`;
- task ids: `TASK-<hex>` and exact `.agentic/tasks/<id>.md` path;
- repository status-list stages: the seven conduction stages plus AEGIS
  adoption stages `survey`, `components`, and `close`;
- active ADORE task stages: exactly `frame`, `specify`, `design`, `build`,
  `validate`, `deliver`, or `done`;
- paths: `full` or eligible `quick`;
- strict exit 0 must agree with `strict.passed=true`;
- non-skipped command runs require numeric duration and integer exit.
- run-container exchange files: `aegis.sh`, `aegis.stdout`, and
  `aegis.stderr` under the host run io directory mounted at `/adore/io`;
- stdout is bounded by `MAX_JSON_BYTES`; stderr by `MAX_TEXT_BYTES`.

Malformed output, invalid UTF-8 replacement, path escape, wrong task, unknown
stage/schema/version, timeout, and unexpected exit fail closed.

## 6. Workflow Integration

The orchestrator creates a task after branch creation, rereads status before
and after each executor attempt, runs strict verification at the validation
boundary, and invokes report/evolution only after approval.

## 7. Validation and Tests

`tests/test_aegis.py` covers every command, happy schema-1 payloads, malformed
JSON, wrong schema/version/task, corrupt journal structures, path escape,
timeouts, unexpected exits, verification contradictions and legal/illegal
transitions. It also proves adoption journals pass repository probing while an
active ADORE task at an adoption stage fails closed, and proves shell-sensitive
titles never enter container argv, LF script quoting, validated file stdout,
typed timeout preservation, and fail-closed missing/unreadable/oversized
exchange output, including bounded pre-script runtime diagnostics. Tests are
offline.
