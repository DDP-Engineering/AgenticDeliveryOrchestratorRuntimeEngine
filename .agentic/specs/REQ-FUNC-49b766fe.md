<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-49b766fe — Report each project setting's source, editability and restart need

Also governs REQ-UX-9a625fc5 (row badges and editing) and REQ-UX-a62e69a9
(project-set filter), which render this metadata.

## Behavior

`GET /api/v1/projects/{name}/config` keeps `config`, `revision`, `issues` and
`local_endpoint_timeout_seconds` and adds `settings`: one entry per leaf of the
redacted effective configuration (`config`), sorted by `key`.

1. **Leaves.** Nested mappings are walked; a non-empty mapping is never a leaf,
   an empty mapping, a list or a scalar is. `key` is the dotted path.
2. **Edit key.** The key in the project's TOML file that holds the value: the
   leaf key itself, except `executor.commands.<name>.<field>`, which is
   `executor.<name>.<field>`.
3. **Source.** `project` when the project's TOML file contains the edit key as
   a leaf (whatever its value), otherwise `default`.
4. **Editable.** True only when the edit key passes the same key rule that
   accepts a web configuration edit (dotted lowercase key in an editable
   section, not secret-like, with command entries limited to supported exact launch-preset keys) **and** the effective
   value is a single string, number or boolean (lists, tables and empty values
   from mappings are not editable in the browser).
5. **Restart.** True when applying a change to the edit key needs a restart
   (agent, platform, worktree, container or executor settings), the same rule
   the pending change reports.
6. Developers and administrators get the same metadata; whether controls are
   shown is the browser's role check, and edits stay administrator-only and
   CSRF-protected as today.

## Data / interface

```json
"settings": [
  {"key": "polling.poll_interval_seconds",
   "edit_key": "polling.poll_interval_seconds",
   "source": "default", "editable": true, "restart": false},
  {"key": "executor.commands.opencode.model",
   "edit_key": "executor.opencode.model",
   "source": "project", "editable": true, "restart": true},
  {"key": "container.egress.allowlist",
   "edit_key": "container.egress.allowlist",
   "source": "default", "editable": false, "restart": true}
]
```

The shared key rule moves into one helper used by the edit endpoints and the
metadata, so they always agree on which keys may be edited; the metadata adds
the single-value condition, so the browser offers no edit for lists and tables.
Staging, validation, revision checks, locking and applying edits are
unchanged.

## Examples

- A web-created project: `platform.repo` and `budgets.max_iterations` (the
  setup wizard writes both) source `project`; `polling.poll_interval_seconds`
  source `default`, editable, no restart.
- `executor.commands.opencode.command`: editable through the documented launch-preset choices; arbitrary command text is refused.
- A secret-like key such as `container.runtime_env.GITLAB_TOKEN` is removed by
  redaction, so it is never listed; an uppercase environment key such as
  `container.runtime_env.UV_LINK_MODE` is listed but not editable.
- `state.store_root`, `clarification.*`: not editable (sections outside the
  editable set).

## Acceptance

- API tests cover a set and a default key, a boolean, the executor mapping, a
  list, a command entry, an uppercase environment key, a non-editable section,
  the restart flag and developer access, and that staging accepts sampled
  editable keys and refuses unknown command entries, lowercase secret-like keys and
  keys outside the editable sections with `setting_not_editable`.

## Assumptions and open decisions

- A value written in the file equal to the default still counts as `project`.
