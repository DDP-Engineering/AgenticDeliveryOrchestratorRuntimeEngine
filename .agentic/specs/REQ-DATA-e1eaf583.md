<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Guided enrollment contract

Status: active. The UX sequence is repository/identity,
environment, eligibility/reviewers/limits, verification, review/create.

## Candidate boundary

Guided setup publishes a stopped profile and returns offline findings. Draft operations
use secret-free request/response data without durable draft storage. Exact import
retains its separate established contract.

- ProjectInput accepts supported workflow labels, four run limits and credential
  environment names. Existing callers retain existing defaults.
- setup-preview returns a SHA-256 candidate revision binding exact config bytes,
  identity and description, plus config revision and secret-free canonical review.
- POST projects/setup-check accepts the full draft and required revision, prepares
  it offline and rejects stale/invalid candidates before an explicit bounded probe.
  Results remain response-only, with config revision, draft revision, UTC time,
  typed checks, redacted model reason and honest status.
- POST projects/setup-create accepts the frozen draft and required revision,
  regenerates the candidate, compares revision and atomically publishes stopped.
  Existing POST projects remains compatible. No durable draft/token store.
- Unknown fields, literal secrets, malformed references, corrupt config and invalid
  clone/runtime fail closed. All three setup routes require Admin and mutation CSRF.
- Advisory ID availability never reserves an ID. Atomic publication owns race handling.

## Wizard state

Only guided existing-clone method is active here. Existing exact TOML import remains
accessible through its established route; portable/clone methods are not offered.
Draft state lives only in the mounted wizard. Any changed answer clears preview,
verification and review; request generation rejects late results. Back retains values.
Review Change links focus the matching step and retain all answers.
No browser secrets are collected or local/session storage drafts written.
Dirty navigation and beforeunload require a loss warning; sign-out clears the draft.

Verification explains host CLI/auth checks and the disposable offline executor
container check before the button. No probe occurs on typing or preview.
Failed/partial/unverified states remain textually explicit. Structural validity gates
creation; incomplete readiness does not pretend to be success and does not invent a new
mandatory readiness gate for stopped enrollment. Review includes verification status.

Final review is built from canonical server preview and the unchanged local draft.
Creation freezes the exact reviewed draft/revision. An immediate ref lock prevents
double submit before React rerenders. Failed creation remains explicit and requires a
deliberate retry; unknown response is not silently treated as success.
Completion remains in the wizard and explains stopped pickup and separate activation.

## Verification and compatibility

Offline API tests cover supported fields, revision mutation, stale probe, failed and
unverified checks, no artifacts, Dev/CSRF and credential redaction. Browser tests use the
real fixture API with injectable external runners plus delayed/corrupt response cases.
All supported locales supply visible wizard copy; no fake image/provider inventory.
Keyboard field/error/step focus, retained corrections, refresh/history/menu/cancel loss,
double submit and 390px themes are observed. Screenshots establish layout evidence,
not novice-user testing or full WCAG compliance.
