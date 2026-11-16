<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Purpose-based catalog settings presentation

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-UX-2bea4ff1](../requirements/ux/REQ-UX-2bea4ff1.toml) — Purpose-based catalog settings presentation

When an authorized user opens project settings, the dashboard shall present redacted catalog settings in six purpose categories including Agent and model plus closed Technical details, with visible understandable labels and purpose/units/consequence help, active/default distinctions and catalog-derived type, editability, range and choices; Dev receives a read-only view without financial or secret disclosure.

Verification scope: Offline catalog/API tests and browser settings tests verify categories, visible help, catalog controls and defaults, unknown metadata fails closed, and Dev UI/API denial and redaction.

### [REQ-UX-d8745013](../requirements/ux/REQ-UX-d8745013.toml) — Project settings follow Git delivery flow

When an authorized operator opens Project Settings, ADORE shall present each visible setting once in Repository, Tickets, Implementation, PR/MR, Statistics, Agent and model or closed Technical details, with a single Repository integration-branch editor referenced from PR/MR, an informational Statistics database file configured externally and CLI/TOML-only JSONL/HTML paths omitted, localized clarification/recovery/advanced disclosures, informational installation fields and Agent and model in Settings with localized Pi model and launch-command controls, provider API keys, model testing and external execution guidance while omitting inactive controls and preserving reviewed administrator and redacted read-only developer authority.

Verification scope: Helper routing/visibility tests and offline browser journeys check exact category ownership/order, native subgroups, target-link opening without a second editor, inactive/external control absence, unchanged config revision, Admin candidate review, Dev redaction, four locales and narrow light/dark layout.

## Implementation

- `04_Software/adore/web/app.py`
- `04_Software/web/e2e/dashboard.spec.ts`
- `04_Software/web/e2e/images.spec.ts`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/e2e/settings.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/ExecutorCredentials.tsx`
- `04_Software/web/src/ReadinessEvidence.tsx`
- `04_Software/web/src/executorSettings.ts`
- `04_Software/web/src/i18n.ts`
- `04_Software/web/src/localExecution.ts`
- `04_Software/web/src/routes.ts`
- `04_Software/web/src/settingHelp.ts`
- `04_Software/web/src/settingKeys.json`
- `04_Software/web/src/settings.ts`
- `04_Software/web/src/settingsCopy.ts`
- `04_Software/web/src/styles.css`
- `04_Software/web/tests/routes.test.mjs`
- `04_Software/web/tests/settings.test.mjs`
- `04_Software/web/tsconfig.e2e.json`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_config.py`
- `04_Software/tests/test_web_pending_config.py`
- `04_Software/tests/test_web_setting_catalog.py`
- `04_Software/web/e2e/dashboard.spec.ts`
- `04_Software/web/e2e/executor-config.spec.ts`
- `04_Software/web/e2e/images.spec.ts`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/e2e/model-connection.spec.ts`
- `04_Software/web/e2e/settings.spec.ts`
- `04_Software/web/tests/routes.test.mjs`
- `04_Software/web/tests/settingHelp.test.mjs`
- `04_Software/web/tests/settings.test.mjs`
