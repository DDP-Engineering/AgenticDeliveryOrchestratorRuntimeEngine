<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Independent positive clarification answer duration

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-c6c694cc](../requirements/functional/REQ-FUNC-c6c694cc.toml) — Independent positive clarification answer duration

ADORE shall validate a positive clarification answer duration independently of the reserved reminder duration while retaining duration-format validation and unchanged expiration behavior.

Verification scope: Config tests accept a 12-hour answer timeout with the default 24-hour reserved reminder and reject zero/invalid answer durations. Existing conductor clarification expiry tests retain the runtime contract.

### [REQ-FUNC-d67a1d33](../requirements/functional/REQ-FUNC-d67a1d33.toml) — Reviewed clarification and recovery collection settings

When an administrator prepares an Implementation setting, ADORE shall review and apply clarification.answer_timeout, clarification.max_rounds, the complete nonempty nonnegative integer retry schedule and the complete five-stage (frame, specify, design, build, validate) positive integer timeout map through the existing single-candidate revision, role and idle gates, rejecting malformed or corrupt collection input without changing active configuration.

Verification scope: Offline HTTP tests verify exact prepare/read/apply values, absent/inline/nested/multiline TOML, unrelated configuration preservation, malformed types/unknown or deliver stage/duplicate JSON/corrupt persisted value rejection and developer denial.

### [REQ-UX-66547cbf](../requirements/ux/REQ-UX-66547cbf.toml) — Human duration retry schedule and five-stage timeout editors

In Implementation, the dashboard shall provide localized administrator editors for answer duration with unit, question-round count, one integer retry delay per line and five per-stage timeout choices (frame, specify, design, build, validate) using the general limit or a positive seconds override, displaying exact active/proposed values through single-candidate review while developers remain read-only.

Verification scope: Settings helper and offline browser tests prove canonical serialization, invalid drafts and malformed candidate rejection, five stages with add/remove overrides, review/apply/discard, developer controls absent four-locale names, normal control height and actions below the stack at desktop/mobile widths.

## Implementation

- `04_Software/adore/config.py`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/implementation_settings.py`
- `04_Software/web/e2e/settings.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/implementationSettings.ts`
- `04_Software/web/src/settingHelp.ts`
- `04_Software/web/src/settings.ts`
- `04_Software/web/src/settingsCopy.ts`
- `04_Software/web/src/styles.css`
- `04_Software/web/tests/settings.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_config.py`
- `04_Software/tests/test_orchestrator.py`
- `04_Software/tests/test_web_config.py`
- `04_Software/tests/test_web_pending_config.py`
- `04_Software/web/e2e/settings.spec.ts`
- `04_Software/web/tests/settings.test.mjs`
