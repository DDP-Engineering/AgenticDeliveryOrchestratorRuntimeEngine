<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Structured committed redacted audit evidence

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-DATA-34ed1530](../requirements/data/REQ-DATA-34ed1530.toml) — Structured committed redacted audit evidence

When a web mutation is prepared, applied or discarded, the service shall record actor/time, stable known project/resource identities, action/result, server operation correlation, known revisions and known redacted before/after evidence at its owning mutation boundary.

Verification scope: Offline config, enrollment/import/clone, account/access and pickup success/prepare/discard tests inspect persisted structured rows.

### [REQ-FUNC-a6d68c4a](../requirements/functional/REQ-FUNC-a6d68c4a.toml) — Administrative independent retention policy

When an administrator changes audit retention in administrative settings, the service shall enforce independent nullable age and stored-text byte bounds with an explicit deletion/limit impact summary.

Verification scope: Policy success, bounds, CSRF/RBAC and browser separation tests verify saved limits, deletion count and unlimited values.

### [REQ-REL-1dc9b68c](../requirements/reliability/REQ-REL-1dc9b68c.toml) — Truthful audit rollback and replay

When a mutation fails, rolls back or is interrupted, the service shall preserve truthful non-applied or uncertain evidence and make asynchronous completion replay idempotent with its durable owning operation.

Verification scope: Inject transactional audit faults, interrupted filesystem attempts and worker completion replay; assert no false or duplicate applied row.

### [REQ-SEC-9415d21d](../requirements/security/REQ-SEC-9415d21d.toml) — Redacted audit projections

The service shall persist and project audit evidence through a closed redaction contract that excludes credentials, passwords, environment values, arbitrary errors and caller correlation metadata at every nesting depth.

Verification scope: Inject nested secret payloads and malformed persisted evidence; inspect database and public projection for exclusion and typed rejection.

### [REQ-UX-0ae52a96](../requirements/ux/REQ-UX-0ae52a96.toml) — Authorized filtered change history and administrative retention

For an authenticated administrator or an authorized project-history reader, the service shall return correctly scoped actor/project/type/UTC period filtered audit rows and counts with server paging and a readable who/what/when/result browser view.

Verification scope: Offline API and browser tests cover filters, counts, pages, empty/error states and denial of global or unassigned history to Dev.

## Implementation

- `04_Software/adore/web/app.py`
- `04_Software/adore/web/audit.py`
- `04_Software/adore/web/commands.py`
- `04_Software/adore/web/static/`
- `04_Software/adore/web/store.py`
- `04_Software/web/e2e/audit.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/AuditHistory.tsx`
- `04_Software/web/src/auditCopy.ts`
- `04_Software/web/src/styles.css`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_audit_evidence.py`
- `04_Software/tests/test_web_audit_evidence.py::test_corrupt_project_fails_closed_on_public_reads`
- `04_Software/tests/test_web_commands.py`
- `04_Software/tests/test_web_enrollment.py`
- `04_Software/tests/test_web_errors.py`
- `04_Software/tests/test_web_paging.py`
- `04_Software/tests/test_web_pending_config.py`
- `04_Software/tests/test_web_rbac.py`
- `04_Software/tests/test_web_transfer.py`
- `04_Software/tests/test_web_user_creation.py`
- `04_Software/web/e2e/audit.spec.ts`
- `04_Software/web/e2e/shell.spec.ts`
- `04_Software/web/tests/auditPolicy.test.mjs`
