<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Explain every project setting in the selected language

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-c6c71dbd](../requirements/functional/REQ-FUNC-c6c71dbd.toml) — Report each project setting's ADORE default

When a signed-in user opens an authorized project's configuration, the web API shall return for every effective setting the value ADORE uses when the project's file does not set it, after ADORE's name derivation and redaction, or null when ADORE has no default for that key.

Verification scope: Automated web API tests check the default of a scalar setting, of a derived path such as metrics.db_path, and null for an executor command field the default configuration does not define.

### [REQ-UX-b0e9a434](../requirements/ux/REQ-UX-b0e9a434.toml) — Explain every project setting in the selected language

On a project's Configuration, the web interface shall show for every setting a help text in the selected language that states what the setting controls, its unit or allowed values and the effect of changing it, or that it is reserved, together with ADORE's default value.

Verification scope: Automated tests check that the setting catalog equals the keys ADORE's configuration produces and that every catalog key has a non-empty help text in English, French, German and Romanian with no text for unknown keys and with pattern keys resolving; Manual: in a browser, open Help on a common, a list, a reserved and an executor command setting in two languages and read the specific text and default.

## Implementation

- `04_Software/adore/config.py`
- `04_Software/adore/web/app.py`
- `04_Software/adore/web/static/`
- `04_Software/tests/test_web_setting_catalog.py`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/i18n.ts`
- `04_Software/web/src/settingHelp.ts`
- `04_Software/web/src/settingKeys.json`
- `04_Software/web/src/settings.ts`
- `04_Software/web/tests/`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_config.py::test_config_view_reports_each_settings_source_and_editability`
- `04_Software/tests/test_web_setting_catalog.py::test_setting_catalog_lists_every_configuration_key`
- `04_Software/web/tests/settingHelp.test.mjs`
- `04_Software/web/tests/settings.test.mjs`
