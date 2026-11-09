<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-1156ea0b - Fix scoped repository readiness and connection disclosure

stage: done
type: fix
path: quick
interaction: autopilot
requirements: REQ-FUNC-5de75419, REQ-SEC-d5459298
parent:
branch: task/adore-web-interface
base: 7a58519dd68ec33b77116bb20cf0c816b366e35b
opened: 2026-10-06

## Done checklist (current stage)

- [x] regression red, anchor, implementation and focused proof recorded
- [x] contracts/docs/requirements reconciled and scoped evolution reviewed
- [x] distinct current compliance/quality reviews approve
- [x] targeted final proof and strict catalog recorded
- [x] candidate and delivery authority presented
- [x] scoped product committed/pushed/deployed
- [x] close-out after delivery

## Frame

Problem: STATED successful Gitea GUI connection followed by failed sign-in readiness; connection layout/collapse confusing.
Desired outcome: STATED consistent sign-in evidence and adjacent action, aligned HTTP checkbox, closable connection dialog.
Actors: Administrator.
Primary scenario: Connect with token, close dialog, check prerequisites with saved project credentials.
Examples: OBSERVED DCP tea0.15.1 whoami succeeds with scoped defaults but rejects --login home.
Counterexamples: Failed HTTP/JSON identity must not become authenticated; closing clears drafts.
In scope: Existing readiness adapter correction and connection modal/layout, focused tests and docs, commit/push/deploy.
Out of scope: New authentication methods, Git transport, full regression, other epic work.
Constraints: Four hours/three fix cycles/twenty authored files; no agents; targeted tests only per user.
Success signals: Valid tea user API returns authenticated; malformed/rejected identity false; actions aligned and modal closable with keyboard.
Evidence: OBSERVED web/app.py bounded_runner appends unsupported whoami --login; RepositoryConnection.tsx form is inline and checkbox inherits full-width input styles.
Assumptions: INFERRED standing iterative commit/push/deploy authority applies.
Unknowns: Other real provider token permissions not supplied.
Decision-blocking questions: None.
Proposed behaviors: Bounded tea user API with configured login and strict identity/HTTP evidence; modal using native focus/Escape, clears token on close.
Path and reason: Quick; repairs existing REQ-FUNC-5de75419 and REQ-SEC-d5459298 behavior without new credential contracts.

## Design

Existing bounded readiness runner translates tea whoami to supported API user command and validates HTTP/JSON account identity; other providers unchanged. Native dialog keeps connection form and result together. Trigger lives in the existing action row. No credential persistence change.

## Log

- 2026-10-06 frame: Scope accepted under standing human authority; quick path selected, no children. DCP read-only scoped command confirms unsupported whoami --login error; default scoped whoami authenticates.

- 2026-10-06 build red: REQ-FUNC-5de75419/REQ-SEC-d5459298; pytest -q 04_Software/tests/test_repository_connection.py -k supported_scoped_user_api exit1/5 failures; missing supported API probe (including valid saved login rejection). Anchor recorded before source edits.

- 2026-10-06 build: Supported bounded Gitea user API and modal/inline consent implemented. Five regression cases passed; fixture corrected to explicit named login. Direct docs and existing requirement links reconciled.

- 2026-10-06 validate: Reviewed all scoped source/test/doc hunks, existing requirement/spec and knowledge contracts; no persistence changes, other providers retain authentication paths. Separate same-agent specification-compliance and implementation-quality verdicts approved round1; no subagents or independent-agent claim. Native dialog screenshot inspected in narrow dark layout; localized keyboard/close/Escape/token-clearing and action alignment tested.
- 2026-10-06 DEVIATION validate: Full suite deferred per standing user instruction. Substitute focused Python/browser/lint/typecheck/build plus strict catalog; whole-application regression remains unproven.
- 2026-10-06 final proof: pytest -q tests/test_repository_connection.py tests/test_web_readiness.py 51passed44.94s; focused Ruff exit0; typecheck/e2e build and production build exit0; playwright jobs.spec.ts grep repository connection|host check details collapse 4passed29.7s. Existing Vite bundle-size and Starlette deprecation advisories retained. No source edits after proof.

- 2026-10-06 deliver: Final evolution15paths (10authored plus5generated asset paths) reviewed; strict exit0/0errors6warnings25notes. Existing2tracked sidecars/four legacy journal findings and generated-bundle size scanning limitation accepted; no actual secret in generated candidate. Standing normal push/deploy authority repeated with targeted proof and full-suite deviation. No source changes after proof.

## Rulings

- RULING-001 | date=2026-10-06 | decision=Proceed through focused validation and normal commit/push/deploy | reason=Current correction request and standing iterative authority, full suite deferred | source=user | supersedes=none

## Handoff

current: done
status: ready
next: Human GUI recheck with saved token.
must_read: 04_Software/adore/web/app.py
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Supported Gitea sign-in probe and adjacent closable connection modal.
evidence: Python51/browser4 passed; lint/typecheck/build and strict catalog exit0; 7f5ceb4 deployed, live saved Gitea sign-in true; services active/HTTPS smoke passed.
issues: Full suite deferred; real GitHub/GitLab acceptance pending.
next: Human GUI recheck; deferred final full suite.
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-06)

- stage: deliver; type: fix; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-5de75419 - Connect and verify a project repository account
  - REQ-SEC-d5459298 - Isolate repository credentials and reject corrupt evidence
- deviations: 1 recorded
  - validate: Full suite deferred per standing user instruction. Substitute focused Python/browser/lint/typecheck/build plus strict catalog; whole-application regression remains unproven.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 7a58519: 19 file(s) changed, 259 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=7 notes=25
- checklist: 5/7 done; open: scoped product committed/pushed/deployed; close-out after delivery

## Delivery close-out (2026-10-06)

- Product 7f5ceb465e1eb6bd54c3c5f69e7dec17b8e6e73c normally pushed and remote head verified. Archive SHA256 409f263d4a6677dc975117748f9a0d4792bfc1cd88fe2d20289dde2953aad9f9 matched remotely before extraction. Deployment succeeded to /home/dpasare/apps/adore/web-ux-7f5ceb4, backup /home/dpasare/apps/adore/backups/web-ux-7f5ceb4-20261006195630.
- Served JS/CSS byte-identical; API/worker active with candidate PYTHONPATH; schema14 integrity ok/audit65. HTTPS root/health/readiness200, protected projects401. Actual saved aegis Gitea token and named login passed the deployed readiness authentication path (only tea API ran live; other prerequisites faked for isolated diagnostic). No credentials changed or printed, no executor/jobs launched. GUI full host-check refresh remains human action; GitHub/GitLab real credentials and final full suite remain pending.
- Delivery report advisory snapshot seven warnings includes open delivery checklist, now completed; legacy sidecars/journal and generated scanning advisory remain. Journal-only close-out follows successful push/deployment.
