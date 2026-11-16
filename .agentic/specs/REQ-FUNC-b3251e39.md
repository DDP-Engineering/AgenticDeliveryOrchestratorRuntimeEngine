<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Enroll a project from its repository URL and clone it at creation

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-b3251e39](../requirements/functional/REQ-FUNC-b3251e39.toml) — Enroll a project from its repository URL and clone it at creation

When an administrator confirms a valid reviewed repository-URL enrollment, ADORE shall create the project using the selected existing target branch in a new or matching-origin local clone, irrespective of the presence of .agentic/aegis.py or .agentic/aegis.toml, within the validated URL, clone-ownership and failure-cleanup boundaries.

Verification scope: Offline repository-source/API/browser tests create stopped projects from fake clones without AEGIS, with aegis.py alone and with both files, and compare clone contents to prove no added files; existing-clone reuse succeeds only for matching origin. Preserve URL/kind/login/ID and all-forge branch-discovery cases, preview/check no-clone-write assertions, and negative occupied-folder, malformed/oversized remote advertisement, missing-target-branch and failed-publication cleanup cases described in the spec.

## Implementation

- `04_Software/adore/web/app.py`
- `04_Software/adore/web/repository_source.py`
- `04_Software/adore/wizard.py`
- `04_Software/web/e2e/enrollment.spec.ts`
- `04_Software/web/e2e/server.py`
- `04_Software/web/e2e/statistics.spec.ts`
- `04_Software/web/src/EnrollmentWizard.tsx`
- `04_Software/web/src/enrollmentCopy.ts`
- `04_Software/web/src/errors.ts`
- `04_Software/web/src/setupCopy.ts`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_repository_source.py`
- `04_Software/web/e2e/enrollment.spec.ts`
- `04_Software/web/e2e/statistics.spec.ts`
