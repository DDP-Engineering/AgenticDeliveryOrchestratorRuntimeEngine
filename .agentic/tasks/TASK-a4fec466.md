<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-a4fec466 - Show metrics.capture_tokens in Configuration

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-SEC-63767e17
parent:
branch: task/adore-web-interface
base: 204f49aa9c1eee994ba22567f4d94873eb6c91ec
opened: 2026-10-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: the web Configuration view drops every key whose name matches the
  secret-name pattern `_SECRET_KEY_RE` (04_Software/adore/cli.py:54), so the
  boolean ADORE setting `metrics.capture_tokens` (default true) never has a
  row, cannot be edited and its existing help text is never shown. The same
  pattern makes the web edit rule refuse it and `adore config set
  metrics.capture_tokens false` answer "secrets never go in config.toml".
Desired outcome: `metrics.capture_tokens` is listed with its value, source,
  help and default, administrators can edit it on its row, and the CLI can set
  it; secret-looking names a project chooses (runtime environment entries,
  unknown keys) stay redacted, unlisted and refused.
Actors: administrator (web edit), developer (read-only view), operator
  (`adore config set`).
Primary scenario: administrator opens Project details > Configuration ->
  the metrics group shows capture tokens = true (Default) with its help ->
  the administrator sets false -> the edit stages and applies like any other
  boolean setting.
Examples: metrics.capture_tokens listed and editable in the web;
  `adore config set metrics.capture_tokens false` succeeds.
Counterexamples: `container.runtime_env.API_KEY` and a
  `container.runtime_env.GITHUB_TOKEN` entry stay hidden and uneditable;
  `adore config set platform.api_token x` stays refused; TOML import still
  rejects embedded secret strings.
In scope: the secret-name decision used by `_redact_config` and
  `_editable_setting_key` (04_Software/adore/web/app.py) and by the CLI
  `config set` refusal (cli.py); regression tests; CHANGELOG.
Out of scope: import secret detection `_secret_config_keys` (already flags
  only non-empty string values, so the boolean is not flagged); journal and
  other redaction; renaming the setting.
Constraints: fail closed for secrets - no secret value is ever displayed or
  editable; existing redaction tests keep passing.
Success signals: tests show the setting listed and editable through the web
  and settable through the CLI, while secret-looking runtime environment
  entries stay hidden and refused.
Evidence:
  - STATED: follow-up offered from TASK-6222d45e review; user: "Do this task
    here".
  - OBSERVED: cli.py:54-58 pattern matches `token(s)`, `secret`, `password`,
    `api_key`, `credential`, `private_key` between `.`, `_`, `-` or the ends;
    app.py:369-373 `_redact_config` drops matching key segments at any depth;
    app.py:603-608 `_editable_setting_key` refuses matching dotted keys;
    cli.py:372 `config set` refuses them; app.py:708 import flags matching keys
    only with a non-empty string value.
  - OBSERVED: config.py:490 `capture_tokens: bool = True`; orchestrator.py:2930
    and 2961 read it; web/src/settingKeys.json catalogs it.
  - OBSERVED (probe): of the 103 catalog keys and of every default leaf, only
    `metrics.capture_tokens` matches the pattern.
  - INFERRED: ADORE's own setting names never hold secrets (config.toml keeps
    secret NAMES in executor.env_keys; values live in .env).
Assumptions: none beyond the inference above.
Unknowns: none.
Decision-blocking questions:
  - Q1 (answered): an explicit list of ADORE settings that are not secrets,
    today only metrics.capture_tokens (RULING-002).
Proposed behaviors:
  1. The Configuration view lists `metrics.capture_tokens` with its value,
     source, help and default, and administrators can edit it on its row.
  2. `adore config set metrics.capture_tokens <true|false>` is accepted.
  3. Other secret-looking names stay redacted, unlisted and refused by the web
     and the CLI.
Path and reason: full - it changes a security redaction rule.

| quick-path criterion | met | evidence |
|---|---|---|
| no new externally observable behavior | no | a hidden setting becomes visible and editable |
| no new interface or data format | yes | same API fields |
| no new dependency | yes | none |
| existing requirement covers it | no | REQ-SEC-c2298428 states redaction, not which names are secrets |
| no security or data-handling change | no | the secret-name rule changes |

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| capture_tokens visible and editable; other secret-looking names still hidden and refused (behaviors 1-3, deliberately one requirement: one secret-name rule decides the view, the web edit and the CLI refusal) | a credential-looking name is a secret unless it is on the non-secret list | REQ-SEC-63767e17 | metrics.capture_tokens listed, edited to false on the web and with `config set` | container.runtime_env.GITHUB_TOKEN hidden, web edit 400 setting_not_editable, `config set` refused | pytest (web and CLI) | `_is_secret_key` with `_NOT_SECRET_KEYS` in cli.py, used by `_config_set`, `_editable_setting_key` and a path-aware `_redact_config` |

## Behavior inventory

| Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result |
|---|---|---|---|---|---|---|
| visible | administrator, developer | open Configuration | metrics.capture_tokens row with value, source, help, default | listed, editable for administrators | developers read only (existing rule) | settings metadata entry |
| editable | administrator | edit capture_tokens to false | staged/applied like other booleans | 200, file says false | a non-boolean value refused by validation (added in fix cycle 1) | config value |
| settable | operator | `adore config set metrics.capture_tokens false` | written | exit 0 | a non-boolean value refused, file unchanged | config value |
| fail closed | administrator, developer | capture_tokens holds a string written by hand | key stays hidden | - | value absent from the response | no row, no value |
| still secret | administrator, operator | a runtime_env entry named GITHUB_TOKEN or API_KEY | not listed; web edit refused; CLI refused | - | refusal codes and messages unchanged | absent row; 400 setting_not_editable; CLI error mentioning .env |

## Design

- **One rule (REQ-SEC-63767e17, RULING-002).** `adore/cli.py` gains
  `_NOT_SECRET_KEYS = frozenset({"metrics.capture_tokens"})` next to
  `_SECRET_KEY_RE` and `_is_secret_key(dotted_key)`, true when the pattern
  matches and the key is not on the list. The pattern itself is unchanged.
- **Users.** `_config_set` (CLI refusal) and `_editable_setting_key`
  (web edit rule and per-setting editability) call `_is_secret_key` on the
  dotted key. `_redact_config` gains a dotted `prefix` so it can test each
  key's full path; because the pattern's words contain no dot, a full-path
  match is the same as the old per-segment match for every other key.
  `OPENCODE_CONFIG_CONTENT` stays dropped as before.
- **Out of scope.** The import check `_secret_config_keys` already flags
  only non-empty string values, so a boolean is never flagged; it keeps the
  plain pattern.
- **UI.** No frontend change: the catalog and help texts already include
  the setting, so the row appears once the API lists it.
- **Tests.** New `tests/test_secret_setting_names.py`: web view lists the
  setting (value, default, editable) and hides a `GITHUB_TOKEN` runtime entry;
  direct edit to false succeeds; editing the runtime entry answers 400
  `setting_not_editable`; CLI `config set` succeeds for the setting and is
  refused for the runtime entry. Existing redaction tests stay.
- **Security.** The list holds one boolean ADORE defines. Fix cycle 1:
  `validate_config` refuses a non-boolean `metrics.capture_tokens`, so the CLI
  and web edits cannot store a string there, and `_redact_config` keeps an
  exempt key hidden unless its value is a boolean, so a string written by hand
  never shows.
- **Alternatives.** Exempting every ADORE-defined name or every boolean was
  rejected by the user (RULING-002).

## Log

- 2026-10-04 frame: full path (security redaction rule changes). Checkpoint mode; scope and Q1 (exemption rule) presented; runs after TASK-3922c5e8 and TASK-65ce7ba5 because it shares web/app.py and CHANGELOG.md with them.
- 2026-10-04 frame accepted: user chose Q1 "Explicit list" and "Autopilot to validate"; waits for TASK-3922c5e8 and TASK-65ce7ba5 to be delivered, then resumes at specify.
- 2026-10-04 resumed after TASK-3922c5e8 and TASK-65ce7ba5 were delivered; base moved to 204f49a (no file of this task had been changed).
- 2026-10-04 specify: 1 requirement created (draft; no spec - the rule fits the prose), 0 revised, 0 reused, 0 retired. REQ-SEC-c2298428 (scoped redacted reads) stays true; behaviors 1-3 map to one requirement because one rule decides the view, the web edit and the CLI refusal.
- 2026-10-04 design: note in `## Design` (`_NOT_SECRET_KEYS` and `_is_secret_key` in cli.py; path-aware `_redact_config`; no UI change); advanced to build (autopilot).
- 2026-10-04 build red: REQ-SEC-63767e17; `.venv/Scripts/python.exe -m pytest -q tests/test_secret_setting_names.py` (from 04_Software; exit=1, 2 failed): the configuration view has no `metrics.capture_tokens` row (KeyError) and `adore config set metrics.capture_tokens false` exits 1 (refused as a secret).
- 2026-10-04 build green: REQ-SEC-63767e17; `_NOT_SECRET_KEYS` and `_is_secret_key` in cli.py used by `config set`, `_editable_setting_key` and a path-aware `_redact_config`. `.venv/Scripts/python.exe -m pytest -q tests/test_secret_setting_names.py tests/test_web_config.py tests/test_web_pending_config.py tests/test_web_rbac.py tests/test_smoke.py tests/test_config.py tests/test_web_setting_catalog.py tests/test_config_line_endings.py tests/test_web_readiness.py` (from 04_Software) 143 passed; ruff clean. Redaction probe over the default config, the example config and a synthetic map: the only key newly shown is metrics.capture_tokens (look-alikes such as metrics.capture_tokens_extra and secrets.capture_tokens stay hidden). Docs: CLI_Reference, Component_CLI, Component_Web_API, knowledge web-interface.md and cli.md, CHANGELOG Fixed; REQ-SEC-63767e17 active with linked tests. No frontend change (catalog and help already cover the key), so no manual browser increment.
- 2026-10-04 validate review round 1: spec_compliance=changes_required (MEDIUM: the exemption went by name only and nothing kept the value boolean - a string set with `config set`, a web edit or by hand at metrics.capture_tokens was accepted and shown, against the Frame's fail-closed constraint and the Design's security note; LOW: a literal dotted key would also be exempt, unreachable from `to_dict()`); implementation_quality=approved (LOW: same value-type gap; LOW: list and dotted-key shapes, unreachable; LOW: path built twice; LOW: the negative case did not check the value is absent from the response). Routed to build for fix cycle 1 of 4.
- 2026-10-04 build fix cycle 1 red: REQ-SEC-63767e17; `.venv/Scripts/python.exe -m pytest -q tests/test_secret_setting_names.py` (from 04_Software; exit=1, 3 failed: a web edit with a string answered 200, a string written in the file was shown, `config set` with a string exited 0).
- 2026-10-04 build fix cycle 1 green: `validate_config` refuses a non-boolean `metrics.capture_tokens`; `_redact_config` builds each path once and hides an exempt key unless its value is a boolean, and documents that it expects `to_dict()` output; tests check values are absent from the response. Requirement prose and verification, Behavior inventory, Design, knowledge and CHANGELOG updated. Same suites plus test_web_import 148 passed; ruff clean. Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=approved (LOW: affected_paths lacked config.py; LOW: three docs name the exemption without the boolean condition); implementation_quality=approved (LOW: same docs; LOW: bracket the and/or condition; LOW: a hand-written non-boolean now fails validation, stated in the CHANGELOG, none in the repo or on DCP). Both reran their probes (164,772-tree classification probe: redaction unchanged outside the exempt path; the exempt key shows only for true/false). Taken as fix cycle 2 of 4.
- 2026-10-04 build fix cycle 2: brackets around the exemption clause in `_redact_config`; CLI_Reference, Component_CLI and Component_Web_API state the boolean condition; REQ-SEC-63767e17 affected_paths adds config.py. No behavior change; tests and lint rerun. Returned to validate for review round 3.
- 2026-10-04 validate review round 3: spec_compliance=approved, no findings; implementation_quality=approved (cosmetic LOW left as is: two edited doc lines are 85 columns in files that already have wider lines). Full suite 748 passed, 1 skipped (judge run); classification probe unchanged.
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-a4fec466 --strict --run`; exit=0; test ok 48.9s, lint ok, frontend ok; errors=0, warnings=3, all from before this task (tracked sidecars; TASK-5e99ee1d and TASK-c765e6b4 journal headers). Knowledge web-interface.md and cli.md updated; REQ-SEC-63767e17 re-read active with paths and linked tests true; no manual increment (no UI change); evolution refreshed after the last edit; DCP read-only check: all six live profiles hold a boolean capture_tokens. Advanced to deliver; stopped for delivery approval (RULING-003).
- 2026-10-04 deliver: validation evidence, verdicts, diff (9 modified, 2 new files), exclusions (TASK-2ea6c7cb journal belongs to the next task) and outcome presented; no deviations recorded. User approved "Deploy to DCP, then commit (Recommended)": outcome = DCP deployment of adore/cli.py, adore/config.py and adore/web/app.py (static UI reinstalled unchanged), then one repository-local commit (no push/PR).
- 2026-10-04 deliver DCP: archive SHA-256 eca7310f2d27bbd295236a3f2a8ebd83e5cc30b8d587a5c0604d5ca0beca9e81 verified on host; live files matched base 204f49a; schema 13; 0 running operations; backups suffix .pre-tokens-20261004165014 (cli.py, config.py, app.py, static, web.db); services restarted and active; secret-name probe (capture_tokens shown, GITHUB_TOKEN and a string capture_tokens hidden) -> True True; health/ready/UI 200; read-only metadata over the six live profiles: 0 validation issues, 101 settings each (was 100), metrics.capture_tokens editable.
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirement, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-04 | decision=work stays on task/adore-web-interface and runs after TASK-3922c5e8 and TASK-65ce7ba5 | reason=user: "Do this task here"; it shares web/app.py and CHANGELOG.md with them | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=exempt an explicit list of ADORE settings that are not secrets, today only metrics.capture_tokens; the secret-name pattern keeps applying to every other name | reason=user answered Q1 "Explicit list (Recommended)" | source=user | supersedes=none
- RULING-003 | date=2026-10-04 | decision=autopilot through specify, design, build and validate with explicit review, then stop before deliver | reason=user chose "Autopilot to validate (Recommended)" | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-a4fec466.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 3 approved/approved; DCP deploy verified (secret-name probe, health/ready 200, live metadata 101 settings)
issues: none
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-04)

- stage: done; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-SEC-63767e17 - Treat only secret-looking names outside ADORE's non-secret list as secrets
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 204f49a: 13 file(s) changed, 546 line(s) added
- checks: errors=0 warnings=3 notes=31
- checklist: 6/6 done
