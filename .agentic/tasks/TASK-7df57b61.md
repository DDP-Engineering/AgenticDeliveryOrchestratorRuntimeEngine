<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-7df57b61 - Display saved audit limits and explicit unlimited defaults

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-a8a3e280
parent:
branch: task/adore-web-interface
base: 638d7ee28bdc55a01ff5b1ddbcb5d1a139077b9d
opened: 2026-10-01

## Done checklist (current stage)

- [x] Scope, requirement and design recorded.
- [x] Test audit form conversion, implement explicit limits and document.
- [x] Browser saved/default values and canonical final verification pass.
- [x] Commit/deploy and verify DCP.

## Frame

Problem: Unlimited audit retention appears as empty boxes rather than explicit values.
Desired outcome: Saved limits populate fields, with zero representing unlimited for unset limits.
Actors: Platform administrator.
Primary scenario: Open Audit; saved day/MiB values or zero appear; save and reopen preserves policy.
Examples: Null limits display 0/0; 30 days and 64 MiB display 30/64.
Counterexamples: Negative, fractional days or excessive limits fail closed; zero never imposes immediate deletion.
In scope: Audit form representation/conversion, localized guidance, tests and deployment.
Out of scope: Changing existing policies or audit records, schema/API changes, new retention defaults that purge history.
Constraints: Backend null remains unlimited, positive integer bytes/days retained, admin/CSRF boundaries unchanged.
Success signals: Explicit defaults and persisted values displayed; save zero maps to null.
Evidence: STATED show defaults or saved values; OBSERVED App.tsx uses null-to-empty defaultValue and backend stores nullable limits; INFERRED show zero to preserve unlimited policy visibly.
Assumptions: Standing autonomous implementation/commit/deployment applies.
Unknowns: None blocking.
Decision-blocking questions: None.
Proposed behaviors: Zero for unlimited; saved values from API; accept blank as unlimited; preserve arbitrary byte policies through fractional MiB.
Path and reason: Full path; new input representation/conversion, existing API/data/RBAC contract preserved.

## Requirement coverage

- REQ-UX-a8a3e280: Explicit/default/saved audit form values and safe conversion.

## Design

Display API null as numeric zero; existing limits display their saved days and bytes converted to MiB. Accept zero or blank as unlimited without modifying the backend schema. Convert bounded input through a small pure helper: integer days 1..36500 and finite MiB <=1024, rounded to positive whole bytes. Fractional MiB preserves backend policies smaller than one MiB. Reject invalid/negative/oversized values before requests with localized guidance. Existing native validation remains; saved response refreshes the form key. Offline Node tests cover positive, unlimited, saved fractional and negative inputs; GUI saves/reopens only disposable local policy. Live DCP verification is read-only so no real audit pruning occurs.

## Log

- 2026-10-01 frame/specify/design: Numeric zero is the visible unlimited default; existing saved limits remain authoritative. This preserves the user-selected indefinite-retention contract. Standing autonomous delivery applies; live checks will not save a pruning policy.
- 2026-10-01 build: `node --test tests/auditPolicy.test.mjs` exited 1 before conversion implementation (required auditPolicy module absent). After implementation, both audit tests pass for positive/max/saved fractional values, zero/blank unlimited input, rounding and invalid/negative/oversized/nonfinite input; seven frontend tests pass together. Native form defaults now show saved limits or zero, with fractional MiB support and localized explanation/errors. Successful response resets the form's saved/default display. Production build passed; user/component/knowledge/changelog reconciled.
- 2026-10-01 validate: Disposable local GUI showed 0/0 defaults; saving 30 days/64 MiB and navigating away/back or reloading restored 30/64. Negative days failed native validation. Saving zero restored unlimited; saving blanks for an already-unlimited policy normalized both fields to 0 after response. 390px screenshot inspected without clipping/overlap; local policy restored to unlimited. All real-server verification remains read-only.
- 2026-10-01 validate: Final diff/evolution reviewed against numeric and persistence contracts. `check --task TASK-7df57b61 --strict --run` exited 0: offline suite 47.8s, lint 0.1s, seven frontend tests 0.2s; strict zero errors. Seven advisory warnings are generated/package/test traceability and generated-bundle scanning limitations, plus unrelated tracked sidecar/old ruling metadata. Direct conversion tests and GUI evidence prove the requested behavior; no material deviation. Local server stopped and viewport reset.
- 2026-10-01 deliver: Candidate is audit form/converter, localized guidance, offline tests/test commands, requirement/journal/docs/changelog and bundled assets. Standing authority covers commit and DCP frontend deployment, with unchanged server audit policy/data. Archive digest: 63cc9cdbb7f58821e2c5d334e2b7659212b947514dbc4b3a401236b012bf5a75.
- 2026-10-01 deliver: DCP archive digest verified and static frontend installed; rollback retained as `static.pre-audit-defaults-20261001`. UI, JS, health and readiness HTTP 200; API/worker active. Live Audit displays 0 days / 0 MiB for existing unlimited policy. No live policy save performed; existing audit records unchanged. Screenshot retained locally, test tabs closed. Deployment succeeded before delivery close-out commit.

## Rulings


## Handoff


current: done
status: ready
next: None; implemented and deployed.
must_read: 04_Software/web/src/App.tsx, 04_Software/web/src/auditPolicy.ts, 05_SoftwareDocu/Component_Web_Frontend.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Explicit audit defaults, saved-value form, safe conversion, tests/docs and DCP assets.
evidence: Build, offline suite/lint, seven frontend tests and strict validation passed; GUI save/reopen/reload and DCP endpoint/display checks passed.
issues: Seven explained advisory warnings; no material deviation.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-a8a3e280 - Show explicit audit retention limits in the form
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 638d7ee: 15 file(s) changed, 197 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=14
- checklist: 3/4 done; open: Commit/deploy and verify DCP.
