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

- invoke `python .agentic/aegis.py` without a shell;
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

`AegisClient` composes argv and accepts injected container execution.
`AegisProbe`, `AegisTask`, `AegisCheck`, `AegisFinding`, and
`AegisCommandRun` expose only validated decision data. Unknown JSON fields may
be present, but ADORE does not use them for decisions.

## 4. Dependencies

Internal dependencies are `adore.executor.base.ExecTarget` and
`adore.util.CommandResult`. The external dependency is the target repository's
unchanged `.agentic/aegis.py` payload and Python runtime.

## 5. Data Contracts

- supported version: `aegis 0.5.x`;
- supported JSON schema: integer `1`;
- task ids: `TASK-<hex>` and exact `.agentic/tasks/<id>.md` path;
- stages: `frame`, `specify`, `design`, `build`, `validate`, `deliver`, `done`;
- paths: `full` or eligible `quick`;
- strict exit 0 must agree with `strict.passed=true`;
- non-skipped command runs require numeric duration and integer exit.

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
transitions. Tests are offline.
