<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Current project settings metadata and row editing

## Behavior and boundaries

### [REQ-FUNC-49b766fe](../requirements/functional/REQ-FUNC-49b766fe.toml)

When a signed-in user opens an authorized project's configuration, the web API shall return for every effective setting whether the project's configuration file sets it or ADORE's default applies, whether the browser can edit it, the file key that edits it and whether applying a change needs a restart, using the same key rule that accepts web configuration edits.

Verification scope: Automated web API tests read the configuration of a project whose file sets some keys and check the source of a set and a default key, that a boolean is editable, the executor command key mapping, that lists, unknown command entries, environment keys and keys outside the editable sections are not editable while supported command entries expose exact preset choices, the restart flag and developer access, and that staging accepts sampled editable keys and refuses unknown command entries, lowercase secret-like keys and keys outside the editable sections with setting_not_editable.

### [REQ-UX-9a625fc5](../requirements/ux/REQ-UX-9a625fc5.toml)

On a project's Configuration, the web interface shall label every setting as set for this project or default and give administrators an edit control on each browser-editable setting's own row that stages the change through the pending change flow, and, for administrators, the restart need and the way to change non-editable settings stated on the row.

Verification scope: Automated frontend tests check that rows carry the source, edit key, input kind, number step and restart flag, that purpose grouping retains each row once, and that only editable rows get an edit kind; Manual: in a browser, as administrator, edit a setting on its row, stage, apply and see its badge show set for this project; confirm a list shows the non-editable note; as developer, see the badges without edit controls or notes.

## Associated tests

- `04_Software/tests/test_web_config.py::test_config_view_reports_each_settings_source_and_editability`
- `04_Software/web/tests/settings.test.mjs`
