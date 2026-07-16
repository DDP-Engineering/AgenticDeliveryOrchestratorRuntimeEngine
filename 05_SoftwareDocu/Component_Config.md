<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Config (`adore/config.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/config.py` - file version 0.3.0.
> Setting-by-setting reference:
> `01_Documentation/Configuration_Reference.md`.

## 1. Purpose

Load `config.toml` into typed section objects and validate it before the
orchestrator runs. Every tunable in ADORE (labels, polling, budgets, delivery
boundary) flows through this component; secrets never do (they stay in the
environment / `.env`).

## 2. Responsibilities

- Parse `config.toml` (stdlib `tomllib`) into one dataclass per section
  (`AgentConfig`, `PlatformConfig`, ..., `MetricsConfig`) with the documented
  defaults for every missing key.
- Resolve slug-derived defaults at load time (`_derive_names`): `agent.slug`
  from `agent.name`; `agent.email` -> `<slug>-bot@local`;
  `state.store_root` -> `.<slug>`; `executor.questions_file` ->
  `<SLUG>_QUESTIONS.md`; metrics paths under the store root. Explicit values
  are never overridden.
- Validate structure and cross-field rules (`validate_config`) and return
  *all* problems as human-readable messages, not just the first.
- `[executor] env_keys` names the only environment variables injected into
  the executor container (secret scoping, design 12b).
- `[container] runtime_env` names non-secret runtime variables injected into
  both `run` and `exec` calls. ADORE-managed isolation variables
  (`HOME`, `GIT_*`, `CODEX_HOME`) and proxy variables are rejected if
  configured there.
- `[container] required_tool_checks` names shell-free commands that validate a
  runtime-project image contains its required build/test tools before gates run.
- `[container.egress]` names the executor network policy (`open`,
  `allowlist-proxy`, or `none`) plus proxy image, port, network prefix, and
  exact/wildcard host allowlist validation.

Explicitly not owned: reading secrets, writing config (`adore config set` is
future work), and any behavior driven by the values.

## 3. Implementation Overview

- Loading is deliberately **lenient**: unknown keys are skipped, missing keys
  default. Validation is the strict pass, so `adore config validate` reports
  everything in one run.
- `_build_section` populates any section dataclass from a raw mapping by
  field-name intersection; `_build_labels` and `_build_executor` handle the
  nested tables (`[labels.*]`, `[executor.<name>]`).
- `validate_config` checks, per section: enum values, positive bounds,
  parseable durations (via `parse_duration`), quiet-hours window format, slug
  shape, a matching `[executor.<default>]` table containing a `{prompt}`
  placeholder, unknown top-level sections, and non-empty
  `platform.repo` / `worktree.repo_path` / `delivery.reviewers`.
- Executor-specific command checks keep selectable engines headless and
  portable: Codex must use JSON output, a non-interactive sandbox mode, and
  `--ignore-user-config` plus `--disable plugins`; Qwen must not use yolo
  approval mode.
- Container runtime env defaults to `UV_LINK_MODE=copy`, which avoids
  hard-link/symlink behavior that is fragile on Windows/WSL bind mounts while
  remaining safe for monorepos. Projects that need stronger uv control can
  set additional non-secret keys such as `UV_PROJECT_ENVIRONMENT`.
- Container egress defaults to `open`. Validation
  requires a non-empty hostname allowlist in `allowlist-proxy` mode and
  rejects schemes, paths, whitespace, shell metacharacters, empty entries, and
  invalid hostnames.
- **Guardrail:** `delivery.draft = false` is rejected - ADORE must never open
  a mergeable (non-draft) MR (design doc section 11).

## 4. Dependencies

- Internal: `adore.util.parse_duration`.
- External: Python standard library only (`tomllib`, `dataclasses`, `re`).

## 5. Inputs And Outputs

- Input: a `config.toml` path.
- Outputs: a populated `Config` (typed sections + the raw mapping);
  `validate_config` returns a list of issue strings (empty = valid);
  `Config.to_dict()` powers `adore config show`.

## 6. Data Contracts

- Section names and key names match the current Configuration Reference
  one-to-one.
- Durations are stored as raw strings ("24h"); consumers parse them through
  helpers (`ClarificationConfig.answer_timeout_seconds()`), so an invalid
  duration is a *validation issue*, not a load crash.
- `labels.selection.priority_order()` returns priority labels highest-first;
  the orchestrator uses that order when ranking eligible tickets.

## 7. Workflow Integration

Loaded once at CLI startup (`adore.cli._load`); every other component receives
values from it (store root/slug -> `StateStore`, platform kind/repo ->
`build_forge`, identity values -> `AgentIdentity`). `adore config validate`
runs the same `validate_config` the engine will run at startup.

## 8. Usage

```python
from adore.config import load_config, validate_config

config = load_config("config.toml")
issues = validate_config(config)   # [] when valid
```

CLI: `adore config show`, `adore config validate`.

## 9. Validation And Tests

- `tests/test_config.py`: minimal-file defaults, slug-derived names, explicit
  values never overridden, bad enums / missing repo, missing executor table,
  invalid durations, `draft = false` rejection, unknown sections, invalid
  slug / non-positive interval / malformed quiet-hours, Codex command
  hardening, Qwen yolo rejection, `[container] runtime_env` validation, and
  `[container] required_tool_checks` plus `[container.egress]` validation.
- Minimum validation after a change: `uv run --group dev pytest tests/test_config.py`
  and `uv run adore -c config.example.toml config validate`.

## 10. Limitations And Future Work

- `adore config set` is not implemented (edit the file directly).
- Unknown *keys inside known sections* are silently ignored (only unknown
  sections are reported); tightening this is a possible follow-up.
- `quiet_hours` is validated here and enforced by the orchestrator before a
  normal poll pass begins.
