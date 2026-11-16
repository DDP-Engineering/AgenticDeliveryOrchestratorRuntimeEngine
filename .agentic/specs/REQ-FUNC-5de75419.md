<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Connect and verify a project repository account

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-5de75419](../requirements/functional/REQ-FUNC-5de75419.toml) — Connect and verify a project repository account

When an administrator submits a server and access token for a project in the GUI, ADORE shall verify the selected Gitea, GitHub or GitLab account and repository read access before saving project-scoped credentials, returning only secret-free identity evidence and retaining previous credentials on verification failure. The connection dialog offers one Cancel dismissal button beside Verify and connect; Cancel and Escape clear the draft token without submitting credentials.

Verification scope: Offline API tests fake CLI responses for all three providers, failed authentication, malformed identities and wrong repository; browser form submits a memory-only token and displays the actual account result. Dialog dismissal uses a single Cancel button; Cancel and Escape clear the draft token without submitting. The four-locale keyboard journey waits for successful language and theme preference responses before full navigation.

### [REQ-SEC-d5459298](../requirements/security/REQ-SEC-d5459298.toml) — Isolate repository credentials and reject corrupt evidence

While project-scoped repository credentials are configured, ADORE shall restrict them to that immutable project and its selected forge CLI under administrator and CSRF protection, excluding secrets from argv, API responses, command output, audit and executors, and refusing corrupt or mismatched stored credentials without fallback.

Verification scope: Offline API/runner tests assert role/CSRF rejection, scoped persistence and worker/probe binding, output redaction, stale/corrupt records, protected storage and failure preservation.

## Implementation

- `04_Software/adore/orchestrator.py`
- `04_Software/adore/repository_auth.py`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/static/`
- `04_Software/adore/web/static/index.html`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/ReadinessEvidence.tsx`
- `04_Software/web/src/RepositoryConnection.tsx`
- `04_Software/web/src/styles.css`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_repository_connection.py::test_connect_verifies_then_saves_scoped_account`
- `04_Software/tests/test_repository_connection.py::test_connection_requires_admin_csrf_and_idle_project`
- `04_Software/tests/test_repository_connection.py::test_corrupt_scoped_credentials_never_fall_back`
- `04_Software/tests/test_repository_connection.py::test_gitea_readiness_uses_supported_scoped_user_api`
- `04_Software/tests/test_repository_connection.py::test_saved_auth_binds_worker_and_readiness_without_executor_leak`
- `04_Software/web/e2e/jobs.spec.ts`
