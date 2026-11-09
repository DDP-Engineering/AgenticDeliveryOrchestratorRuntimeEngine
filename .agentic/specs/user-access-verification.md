<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# User access acceptance mapping

Issue #18 / TASK-287ae997; baseline d38b5b0fc2697cc4eae309f3126146f8045460c2.
Scope is only W14. All observations use isolated local fixtures and fake external
commands. No live acceptance, novice participants or full WCAG certification.

| Actual issue criterion | Observed proof seam and oracle |
| --- | --- |
| Valid Admin/Dev exact atomic privileges/grants | `test_atomic_create_assigns_exact_access_and_keeps_secrets_private`: authenticates created recipient, exact role/IDs/visible project set, Admin global and Dev cost/admin/cross-project denial; Dev browser creates exactly two reviewed IDs with one request. |
| Invalid/duplicate credentials/role/grants; unknown/archived/concurrent deletion; no partial user | `test_invalid_intent_leaves_no_partial_account_or_success_audit` (16 inputs), explicit empty/duplicate IDs, explicit required fields, archived/corrupt metadata; lifecycle races archive/delete/replace/rename during hashing and deletion after grant/audit insertion; trigger write fault after first grant; audit corruption/write fault. Accounts/grants/success audit remain unchanged. |
| Admin global explicit; deliberate Dev zero projects | Browser Admin global wording in access/review, no project checkboxes; zero Dev review disabled until deliberate checkbox, review and successful exact empty grants. API rejects implicit empty intent. |
| Admin-only create/disable/reset/edit; last Admin and disabled sessions | New creation trust-boundary test plus `test_web_auth.py`, `test_web_project_access.py`, `test_web_rbac.py`; missing CSRF/Dev/disabled denies, last Admin rejects disable, existing reset/session cases preserved. |
| Password never in audit/log/issues/persistent drafts/review | Public responses/errors/audit omit password/hash; Argon2id stored hash; source inspection: credential state separate from secret-free review model, no storage writes; browser reviews have no password input/value, storage has no synthetic password and reload clears input. Audit transaction receives only username; no issue publication with credentials. |
| UI cannot weaken direct project/admin/cost enforcement | Created Dev recipient cross-project config returns non-disclosing 404, user/admin and prices APIs deny; existing disjoint-multi-project/global endpoint security regressions and direct-route browser shell cases run in full proof. Grants survive rename/restart, and recycled names inherit none. |
| Existing auth/reset supported; no invitations | Legacy POST /users regression, existing hashed login/session/password/reset/change-required suites; only additive local role/grant endpoint and client UI. No dependency/schema/email service. |

Account and project access browser cases confirm before/after, cancellation without
mutation, actual result and retained correction after a rejected apply. Malformed
account/create/project reads fail closed; late unmounted create result is ignored.

## Focused results

- New public creation suite: 32 passed; Ruff selected files exit 0.
- Existing auth/access/RBAC regression: 46 passed, exit 0.
- Nine user browser cases passed, exit 0; the round-1 corrective post-disable
  malformed-refresh case separately passed, exit 0. TypeScript and isolated build passed.
- Production `npm run build` passed, including asset stamping.
- Four locales x two themes at 390px, plus English light/dark at 1440px: no
  document overflow, focused review heading, no review password. Retained synthetic
  captures: `user-access-users-en-light-390.png`, `user-access-users-ro-dark-390.png`,
  `user-access-users-en-light-1440.png`, `user-access-users-en-dark-1440.png`.
  Visual inspection: readable wrapped IDs/actions, preserved DDP logo, clear role
  limits and correction controls; no manual screen-reader/full contrast audit.

## Final proof

The authoritative full strict result is `.agentic/tasks/TASK-287ae997.validation-final.json`.
Observed final gate: strict exit 0, strict.passed=true, zero errors, 12 advisory
warnings and 29 unrelated manual notes. Python 1113 passed / one existing platform
symlink skip; configured Ruff passed; frontend Node, TypeScript, isolated build
and all 106 Chromium cases passed. Independent whole-04_Software Ruff passed;
production build passed before freeze. Candidate hashes remain unchanged.
The first full gate exposed the post-disable test's initial-load interception
race (105 Chromium passed / one failed); waiting for the target before injecting
the corrupt refresh fixes the test without changing product code. Final full
proof supersedes that failure; history remains in the task journal.

## Limits and advisories

Profile metadata is filesystem-owned. App archive threads serialize with creation;
external changes observed before SQLite commit reject and roll back. Lifecycle
changes after commit retain immutable grant filtering; this is no distributed
filesystem transaction. Human live infrastructure/novice/full accessibility
acceptance remains pending. The app retains existing compatible assignment APIs.
False-positive secret-pattern warnings identify credential parameter/default
expressions or synthetic test passwords; no real credential is introduced.
Pre-existing workflow-sidecar/journal advisories, Vite chunk size, Node colour
environment and Starlette/httpx deprecation are classified in final proof/journal.
No verification is weakened and no unrelated historical journal is edited.

Final advisory classification: four synthetic PNG captures and one generated
minified JS file are not line-scanned; all have known inspected provenance.
The redirected final JSON was not line-scanned during generation; its completed
UTF-8 JSON parses and contains only safe result tails/counts. Three possible-secret
patterns are credential parameter/default/empty expressions and synthetic test
inputs. Two historical tracked sidecars and two unrelated historical journal
warnings are unchanged. Vite chunk size, Node colour and Starlette deprecation
remain advisory; no relevant test failure, weakened proof or scope deviation is
accepted. Live infrastructure/novice/full accessibility acceptance is not claimed.
