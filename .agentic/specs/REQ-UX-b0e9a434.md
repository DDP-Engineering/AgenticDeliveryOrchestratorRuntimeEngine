<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-UX-b0e9a434 — Explain every project setting in the selected language

Also governs REQ-FUNC-c6c71dbd (the default value the help shows).

## Behavior

1. **Setting catalog.** `04_Software/web/src/settingKeys.json` lists every
   setting key the configuration view can return. Variable parts use `*`:
   `container.runtime_env.*`, `workflow.kind_labels.*` and
   `workflow.stage_timeout_overrides.*`; the bare map keys
   `container.runtime_env`, `workflow.kind_labels` and
   `workflow.stage_timeout_overrides` cover an empty map. The executor keys
   are `executor.command`, `executor.env_keys`, `executor.mode`,
   `executor.model` and `executor.questions_file`. A Python test keeps the catalog equal to the keys ADORE's
   configuration produces, so a new setting fails the build until it is
   catalogued.
2. **Help texts.** `04_Software/web/src/settingHelp.ts` holds one text per
   catalog key in each locale (en, fr, de, ro). A text says what the setting
   controls, its unit or allowed values and the effect of changing it. A
   setting the current conductor accepts but does not use says it is
   reserved. Texts match the implementation (adore/config.py and the code that
   reads the setting), not intent. `settingHelp(key, locale)` returns the text
   for an exact key, else for the matching `*` pattern.
3. **Rendering.** Each Configuration row's Help shows the type line, the
   setting's help text in the selected locale and "ADORE default:" with the
   default value from REQ-FUNC-c6c71dbd (or "none" when ADORE has no default).
   The generic reference sentence remains only as a fallback for a key the
   catalog does not know.
4. **Defaults (REQ-FUNC-c6c71dbd).** Each `settings` entry of
   `GET /api/v1/projects/{name}/config` gains `default`: the value at the same
   key in a default configuration after ADORE's name derivation
   (`agent.slug` `adore`, `agent.email` `adore-bot@local`, `state.store_root`
   `.adore`, `executor.questions_file` `ADORE_QUESTIONS.md`, metrics paths
   under `.adore`), with the redaction the configuration view applies, or
   `null` when the default configuration has no such key (for example a
   `container.runtime_env.*` name it does not define).

## Data / interface

- `settings[i].default`: JSON value or `null`; all other fields unchanged.
- `settingKeys.json`: sorted JSON array of strings.
- `settingHelp.ts`: `SETTING_HELP: Record<Locale, Record<string, string>>`
  and `settingHelp(key: string, locale: Locale): string | undefined`.

## Examples

- `recovery.max_stage_failures`, en: explains attempts per stage, that the
  last one fails the run, and that the count resets when the stage advances;
  "ADORE default: 3".
- `executor.command` shows "ADORE default: pi -p --mode json --model {model}
  {prompt}".
- `metrics.db_path` shows "ADORE default: .adore/metrics.db".

## Acceptance

- Python tests: catalog equals the configuration's keys; defaults returned
  for a scalar, a derived path and an executor command field.
- Node tests: every catalog key has a non-empty text in every locale, no text
  exists for a key outside the catalog, and pattern keys resolve.
- Manual: in a browser, Help on several rows (common, list, reserved,
  executor command) shows the specific text and default in two locales.

## Assumptions and open decisions

- Texts are reviewed against the code at writing time; a later behavior
  change must update them (the catalog test only guarantees presence).
