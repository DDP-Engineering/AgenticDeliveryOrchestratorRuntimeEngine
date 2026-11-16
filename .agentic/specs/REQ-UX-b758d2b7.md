<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# present complete authorized scoped current-state

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-25dc0271](../requirements/functional/REQ-FUNC-25dc0271.toml) — Return a validated redacted observed timeline in job detail

When a caller requests a job's composite detail, the API shall return a validated redacted observed timeline, rejecting an empty, malformed or naive activity time as run_state_corrupt.

Verification scope: Offline test_web_jobs API tests cover the observed timeline, invalid identities, unsafe links, redaction, authorization and changed revision; corrupt input fails closed without partial totals.

### [REQ-UX-78923e00](../requirements/ux/REQ-UX-78923e00.toml) — Concise project directory and role-appropriate project hub

When an operator opens Projects or an authorized project hub, the dashboard shall show one dedicated project identity/navigation band ordered Summary, Settings, Jobs, Statistics, History, Access with role-permitted tabs and lifecycle actions confined to Summary, where Summary comprises an information/actions panel with separated container/executor/monitoring/verification facts and validated project job counts, plus one compact attention/active jobs panel; explicit host checking and evidence live in the information panel while retaining existing deep links.

Verification scope: Offline browser journeys inspect directory columns without Actions/verification, confirm the single ordered hub tab navigation (Jobs and Statistics as in-hub tabs) and dedicated administrator lifecycle actions with exact-name confirmation and project-change reset, traverse hub and old URLs with Back/keyboard/390px/themes, and confirm developer-denied Access/direct project routes. Summary tests prove two panels, actual scoped counts and branded facts, compact active/attention rows, explicit-only CSRF host checking and unknown counts/hidden rows after corrupt evidence. A held older project-list snapshot cannot overwrite a newer explicit host-check result; a subsequent fresh poll can update the verification fact.

### [REQ-UX-a7969a9d](../requirements/ux/REQ-UX-a7969a9d.toml) — Distinguish accepted job commands from their outcomes

When an authorized operator requests Start, Retry or Cancel, the interface shall distinguish accepted or queued work from its actual asynchronous completion, failure or uncertain result, showing the concrete recorded reason when available.

Verification scope: Offline browser journeys submit real API starts against fake worker commands, observe pending and final success/failure, prevent duplicate submits and invalid/human-owned/archive actions, and reject CSRF/revoked grants through existing API tests.

### [REQ-UX-b758d2b7](../requirements/ux/REQ-UX-b758d2b7.toml) — present complete authorized scoped current-state

When an authenticated operator opens Overview or Jobs, the dashboard shall present complete authorized scoped current-state and attention evidence with composite job identity, observed next action and explicit missing/stale evidence.

Verification scope: Offline browser and model tests open lifecycle groups, colliding IDs, quick-path events and source changes; observe scoped totals and actual safe links, with incomplete/corrupt/unauthorized responses hiding data.

## Implementation

- `04_Software/adore/web/app.py`
- `04_Software/adore/web/jobs.py`
- `04_Software/adore/web/static/`
- `04_Software/adore/web/static/index.html`
- `04_Software/tests/test_web_jobs.py`
- `04_Software/web/e2e/dashboard.spec.ts`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/e2e/server.py`
- `04_Software/web/e2e/shell.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/JobWorkspace.tsx`
- `04_Software/web/src/i18n.ts`
- `04_Software/web/src/jobCopy.ts`
- `04_Software/web/src/jobModel.ts`
- `04_Software/web/src/routes.ts`
- `04_Software/web/src/styles.css`
- `04_Software/web/tests/jobs.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_jobs.py::test_global_projected_timeline_corruption_fails_closed`
- `04_Software/tests/test_web_jobs.py::test_job_list_has_no_advanced_filters_and_detail_keeps_safe_timeline`
- `04_Software/tests/test_web_jobs.py::test_project_summary_refuses_a_run_without_an_aware_activity_time`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/tests/jobs.test.mjs`
