<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# Structured change evidence contract

REQ-DATA-34ed1530: add nullable structured JSON evidence and unique server event key to schema14 audit. Preserve compact columns/API compatibility. Snapshot actor username with numeric ID; project immutable ID where observed; resource typed account/config/project/operation ID.
REQ-SEC-9415d21d: audit.py owns a closed evidence schema and recursive redaction. Never persist request credentials, environment, arbitrary errors or caller idempotency strings. Hash server correlations. Known scalar nonsecret configuration diffs only; arbitrary string/compound settings explicitly redacted.
REQ-REL-1dc9b68c: SQLite-owned account/access/queue/policy mutations and evidence share BEGIN IMMEDIATE. Filesystem-owned config/enrollment uses a durable initially uncertain attempt, finalized after owning mutation, before removing pending config. Crash leaves uncertain; replay uses server key, retaining original before. Precondition rejections produce no applied event. Interrupted command becomes uncertain; completion update/evidence share transaction, terminal replay is exact or rejected.
REQ-DATA-196dcd48: upgrade 13->14 inside existing initialization transaction. Validate audit rows before upgrade/commit; null evidence marks legacy, before/after/revisions/result unrecorded. Legacy project name never fabricates stable identity or Dev visibility. No runtime state migration.
REQ-UX-0ae52a96: admin global audit-page accepts actor_id/project_id/action/from/to; Dev only exact assigned project_id. WHERE selection before COUNT/LIMIT in one snapshot. Strict UTC half-open period. Project History adds change evidence alongside existing job history. No export.
REQ-FUNC-a6d68c4a: policy lives in System status administrative settings; independent nullable bounds retain existing maxima. Return deleted count and stored-text impact. Audit policy update evidence shares its transaction.
Architecture: audit.py -> store.py (SQLite) <- API and worker; AuditHistory -> authorized audit-page. API retains RBAC/CSRF and current locks.
Expected files: audit.py, store.py, app.py, commands.py, App.tsx, AuditHistory.tsx, auditCopy.ts, styles.css; test_web_audit_evidence.py, audit.spec.ts; Web_Identity/API/Frontend contracts, Web_Interface.md, CHANGELOG.md. Workflow/knowledge/context and generated static inventoried separately.
Risks: SQLite and filesystem cannot commit atomically; conservative uncertainty is required. Arbitrary historic details require redacted projections rather than fabricated diff. No new dependencies. Open decisions: none.

Behavior inventory: each requirement coverage row is a separately observable response; evidence fields/redaction are inseparable projections. SQLite rollback returns no applied evidence; filesystem interruptions retain uncertain attempt with after absent. Legacy result/phase/base/candidate/before/after are null. New phases prepare/apply/discard and results prepared/applied/discarded/rejected/uncertain. Server-generated correlation is opaque; caller strings and exception text excluded. Audit text byte bound includes structured JSON and event key; SQLite allocation is separate. Period endpoints are timezone-aware UTC and half-open.

Audit actor IDs and offsets are bounded to SQLite signed 64-bit integers; oversized filters fail with typed invalid input rather than a numeric binding exception.
