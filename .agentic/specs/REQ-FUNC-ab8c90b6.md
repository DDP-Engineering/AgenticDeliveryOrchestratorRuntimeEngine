<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Report local executor prerequisite failure causes

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-ab8c90b6](../requirements/functional/REQ-FUNC-ab8c90b6.toml) — Report local executor prerequisite failure causes

When a native prerequisite check fails, ADORE shall persist a bounded closed diagnostic cause and optional exit code for managed Node/Pi, credentials, process launch or cleanup. Diagnostic reads shall refuse malformed or contradictory current-format evidence instead of inferring readiness.

Verification scope: Offline local/API tests cover stdout/stderr version success, missing executable/auth, corrupt auth, timeout/nonzero status, account/permission/cleanup failure, roundtrip and corrupt/contradictory persisted evidence.

## Implementation

- `04_Software/adore/local_execution.py`
- `04_Software/adore/web/app.py`
- `04_Software/web/src/readiness.ts`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_local_execution.py::test_readiness_reports_managed_pi_prerequisite`
- `04_Software/tests/test_web_readiness.py::test_readiness_persistence_is_closed`
