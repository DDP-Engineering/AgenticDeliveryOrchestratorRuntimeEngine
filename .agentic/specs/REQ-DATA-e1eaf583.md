<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Exact revision-bound reviewed enrollment

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-DATA-e1eaf583](../requirements/data/REQ-DATA-e1eaf583.toml) — Exact revision-bound reviewed enrollment

When guided enrollment is confirmed, the system shall submit the frozen reviewed draft once and publish its exact revision with pickup stopped, rejecting a changed or duplicate candidate and exposing ambiguous failures without automatic resubmission.

Verification scope: Preview then confirm and inspect exact configuration bytes; mutate identity/setup or omit/wrong revision on guarded route, race duplicate calls, double-click UI and delay responses; verify one profile or explicit conflict.

### [REQ-FUNC-49e89542](../requirements/functional/REQ-FUNC-49e89542.toml) — Explicit pre-create environment verification

When an authorized administrator explicitly checks a structurally valid reviewed draft revision, the backend shall return bounded redacted revision/time-bound prerequisite evidence without persisting a draft, rejecting stale revisions and invalid setup before probes.

Verification scope: Fake tool/container/model responses; verify calls only on explicit draft probe, current failed/partial/verified evidence, mismatched revisions and no profile creation or durable draft.

### [REQ-FUNC-702b0fce](../requirements/functional/REQ-FUNC-702b0fce.toml) — Complete offline enrollment candidate preview

When an administrator previews a guided draft, the backend shall return structural findings or an exact candidate revision and complete secret-free review including identity, environment, eligibility/reviewers/limits and server paths without publishing profiles or probing external tools.

Verification scope: Preview explicit fields with a runner that fails if called; inspect generated candidate fields, paths and digest; reject malformed references/limits/clone/runtime without profile artifacts.

### [REQ-SEC-dc4bd0c3](../requirements/security/REQ-SEC-dc4bd0c3.toml) — Secret-reference-only administrator draft operations

When guided draft preview, verification or guarded creation is requested, the backend shall require administrator CSRF authorization and accept credential reference names only, with redacted fail-closed rejection of invalid references or secret values.

Verification scope: Admin happy calls and Dev/no-session/missing-CSRF failures for all draft routes; inject bad credential names and inspect redacted findings with no probes/artifacts.

### [REQ-UX-002cbd25](../requirements/ux/REQ-UX-002cbd25.toml) — Corrective enrollment errors and focus

If guided enrollment input or a setup operation is rejected, the frontend shall show accessible field and summary findings linked to corrective steps and move focus to the corrective context.

Verification scope: Reject empty/malformed fields, ID collisions and invalid server clone/runtime; navigate error links by keyboard and observe focused field/heading and corrected retry.

### [REQ-UX-072cf049](../requirements/ux/REQ-UX-072cf049.toml) — Five-step supported enrollment guidance

When an administrator opens guided enrollment, the frontend shall present five ordered steps starting at repository and identity with visible mandatory-concept guidance, actual supported explicit choices, a repository URL that fills the repository details, a derived project ID instead of an ID field, optional reviewers, preserving existing routes, locales, themes and branding.

Verification scope: Complete supported five-step enrollment; inspect essential instructions, absence of invented presets, keyboard operation and screenshots at 390px and desktop in both themes.

### [REQ-UX-3609c9ed](../requirements/ux/REQ-UX-3609c9ed.toml) — Memory draft correction and navigation protection

While an enrollment draft is edited, the frontend shall retain entries across Back and review correction in memory, invalidate dependent preview/verification/review on changes and warn before navigation or refresh discards them.

Verification scope: Fill then go Back and Change, edit upstream fields during pending responses, cancel/accept navigation and refresh warnings, observe retained or discarded values and stale-response rejection.

### [REQ-UX-7f8fde2c](../requirements/ux/REQ-UX-7f8fde2c.toml) — Honest stopped-pickup enrollment completion

After guided enrollment succeeds, the frontend shall display the created stable identity and pickup-stopped outcome with a separate activation explanation, without promising a particular issue starts.

Verification scope: Create offline profile; observe stopped server state and completion with identity, activation guidance, project link and no automatic resume/start request.

## Implementation

- `04_Software/adore/profiles.py`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/static/`
- `04_Software/adore/web/static/index.html`
- `04_Software/web/e2e/enrollment.spec.ts`
- `04_Software/web/e2e/server.py`
- `04_Software/web/e2e/shell.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/EnrollmentWizard.tsx`
- `04_Software/web/src/enrollmentCopy.ts`
- `04_Software/web/src/styles.css`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_enrollment.py`
- `04_Software/tests/test_web_readiness.py`
- `04_Software/web/e2e/enrollment.spec.ts`
- `04_Software/web/e2e/shell.spec.ts`
