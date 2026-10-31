<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-ab8c90b6 — Local prerequisite evidence

## Data and behavior

Schema-1 readiness optionally includes executor_probe with exactly ready (boolean),
reason (closed string) and exit_code (null or integer -2147483648..4294967295).
It is valid only in executor-local context. ready equals checks.executor_cli and
is true exactly for reason ready. ready, version-invalid and credential-missing
carry exit code 0; executor-exit requires a nonzero integer. Legacy absence remains
readable and never fabricates a cause. Unknown fields/reasons, duplicate JSON,
boolean/fractional exit codes and contradictory status fail closed as readiness_corrupt.

Reasons: ready, executable-missing, credential-missing, credential-invalid,
executor-exit, version-invalid, timeout, account-mismatch, permission-denied,
scope-error, cleanup-failed, runtime-error. They represent measured native phases;
no arbitrary external text enters the result. Failed cleanup prevents success.

## Acceptance

Offline native runners prove version on stdout/stderr, finite command timeout,
missing executable/auth, corrupt auth, nonzero exit, account, permission and
cleanup failure. API roundtrip and strict corrupt/legacy records are tested.
The frontend mirrors this contract and renders a localized cause/exit code.
