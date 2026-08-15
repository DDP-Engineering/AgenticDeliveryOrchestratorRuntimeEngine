<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Assisted-Config Wizard (`adore/wizard.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/wizard.py` - file version 0.5.0.
> Historical design source: `00_Planning/Assisted_Config_And_Profiles_Plan.md`.
> CLI: `adore init` (wired in `adore/cli.py`).

## 1. Purpose

Turn onboarding a new runtime project from "hand-write a config.toml and know
which of 15 sections matter" into a guided, explicit conversation that ends in a
**minimal, validated runtime-project profile**. Every prompt states what it is,
shows an example, offers a detected/sensible default, and validates the answer;
missing non-ADORE prerequisites (a platform CLI, a token, a container runtime)
get in-line, OS-specific guidance from `doctor`.

## 2. Responsibilities

- **The prompt primitive:** `FieldSpec` (label, description, example, default,
  choices, validator) + `ask()` (read -> default -> validate -> re-prompt).
- **Askers:** `ConsoleAsker` (interactive stdin/stdout) and `ScriptedAsker`
  (tests + `--answers FILE`; `interactive=False` fails fast instead of looping).
- **The flow:** `run_wizard()` walks the plan's Phase A-I - environment report,
  identity, platform/repo, local clone, branch conventions, runtime/executor,
  delivery, budgets/policy - and assembles a **minimal** config (only keys that
  matter; defaults omitted).
- **Emit + guard:** a stdlib TOML emitter (`_emit_config_toml`, no `tomli_w`
  dependency) and `_validate_or_raise()` - the assembled config is written to a
  temp file, loaded and validated the same way the engine does at startup, and
  only committed to the profile when clean (**never saves an invalid profile**).
- **Save:** writes `config.toml` into the profile dir and creates the
  `profile.json` metadata via `ProfileStore`.

Explicitly not owned: the profile store internals (`adore/profiles.py`),
detection/guidance text (`adore/doctor.py`), and the `adore profile` management
commands + `--profile` resolution.

## 3. Implementation Overview

- **Fully injectable** for offline testing: the prompt reader (`Asker`), the
  output sink (`out`), the command runner (for `doctor` probes), the OS key, and
  the profile name are all parameters. Tests drive the whole flow with a
  scripted asker + a fake runner and assert the emitted config passes
  `validate_config`.
- **Re-prompting vs fail-fast:** `ask()` re-prompts on an interactive asker and
  raises `WizardError` on a non-interactive one - so `--answers` fails fast on a
  bad value rather than looping.
- **Branch cross-check:** the branch-template validator renders a sample with
  `{slug}/{run_id}/{iid}` and, when a push rule is set, rejects a template the
  rule would reject (the exact check that bit the first pilot) - inline, before
  anything is written.
- **Minimal + valid output:** required-for-validation fields are always written
  (platform, repo, worktree, executor command/model, reviewers, runtime, image,
  profile-owned state_root); optional fields only when they differ from the
  dataclass default. The image prompt defaults to the generic executor base
  (`adore-executor-base:1.0.0`) and points project profiles at derived
  runtime-project images when needed. Rootless podman auto-adds
  `run_args=["--userns=keep-id"]`; Docker deployments rely on the image being
  built with `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)` so
  the container user/group match the host (no `run_args` needed for UID mapping). The executor `env_keys` are
  derived from the model's provider (names only, never secret values - D5).
- **Governance-aware file budget:** the recommended profile allows 120 touched
  files. AEGIS 0.5 task journals and evidence count toward the same bound as product
  files, and the CR6 full pilot occupied 45 paths before implementation; the
  older 40-file recommendation failed an otherwise healthy governed run.
- **TOML emission** prefers literal single-quoted strings, so regexes and
  Windows paths (backslashes) need no escaping.

## 4. Dependencies

- Internal: `adore.doctor` (detection/guidance), `adore.profiles`
  (`ProfileStore`, `Profile`), `adore.config` (`load_config`,
  `validate_config`), `adore.util` (`CommandRunner`, `run_command`).
- External: Python standard library only (`re`, `tempfile`, `pathlib`,
  `dataclasses`).

## 5. Inputs And Outputs

- Inputs: user answers (interactive) or a TOML `--answers` file keyed by field
  key; an injectable runner/OS-key; a profile name (asked if omitted).
- Outputs: `<home>/profiles/<name>/config.toml` (minimal, license-headered) +
  `profile.json`; printed environment report, summary, and next steps.

## 6. Data Contracts

- Answer keys (interactive prompts and `--answers`) are the `FieldSpec.key`
  values: `profile_name, description, agent_name, kind, hosting, host_url,
  login, visibility, repo, repo_path, worktree_root, target_branch,
  has_push_rule, branch_rule, branch_template, runtime, image, executor_cli,
  model, auth_mode, reviewers, budgets_choice, max_*, polling_mode,
  state_location, confirm`. `kind` accepts gitlab/github/gitea; for gitea the
  hosting/host questions are replaced by `login` (the tea login name, written
  to `[platform] login` when non-empty - tea binds host + token to a login),
  and the repo hint becomes `owner/repo` (Gitea has no subgroups).
- Interactive fixed choices are displayed as numbered options and accept either
  the number or the literal choice text; `--answers` files should use the
  literal choice text for readability.
- The emitted config always satisfies `validate_config` (enforced by the
  write-then-validate guard).

- **Workflow labels:** the wizard asks for the ready label,
  task-type labels (fix/change), and the quick framing hint, and writes
  non-defaults into `[labels.lifecycle]` and `[workflow]`.
  Accepting every default writes neither table, keeping the emitted config
  minimal. It also probes the named clone with `doctor.detect_aegis` and
  prints hard-break guidance when the target repository carries no usable
  AEGIS 0.5.x payload - informational like the rest of the environment check, so
  an operator can install the payload in another terminal and continue.
- **Fail-loud recovery and approval:** the wizard asks for the approval label,
  stage-attempt limit, transient-attempt limit and capped backoff list, then
  emits explicit `[delivery]` and `[recovery]` values. Defaults are
  `agent-approved`, `3`, `3`, and `[5, 30, 120]`.

## 7. Workflow Integration

`adore init [name] [--force] [--answers FILE]` (cli.py) builds a `ProfileStore`,
selects the asker (Console, or Scripted from the answers file), and calls
`run_wizard`. The resulting profile is consumed by `--profile` resolution:
`adore --profile <name> run|status|...`.

## 8. Usage

```bash
adore init                       # interactive; asks for a profile name
adore init <profile-name>           # interactive; name given
adore init <profile-name> --answers answers.toml   # non-interactive (CI / servers)
adore init <profile-name> --force   # overwrite an existing profile
```

`answers.toml` uses the field keys as TOML keys, e.g.
`kind = "gitlab"`, `reviewers = "reviewer.one, reviewer.two"`,
`runtime = "wsl -d Ubuntu-24.04 -- podman"`.

## 9. Validation And Tests

- `tests/test_wizard.py` (offline; scripted asker + fake runner): the golden
  happy-path test (emitted config passes `validate_config`, expected metadata,
  profile-owned state root); podman -> keep-id; re-prompt on an invalid clone
  path; re-prompt on a bad push-rule regex and on a branch template the rule
  rejects; refusal to overwrite without `--force`; abort-on-"no" writes nothing;
  non-interactive determinism (identical bytes) + fail-fast on a bad answer;
  numbered interactive choices; and the `_validate_or_raise` never-save-invalid
  guard.
- Live-verified via `adore init --answers` on Windows: environment check,
  minimal config emitted, `config validate` OK.
- Minimum validation after a change:
  `uv run --group dev pytest tests/test_wizard.py` + `ruff check .`.

## 10. Limitations And Future Work

- WSL-internal runtime probing (docker/podman INSIDE a distro) is left to the
  E2E task; the wizard suggests a WSL-wrapped string from the host detection and
  the user confirms.
- Version-vs-requirement checks (`required_tools`) are a separate backlog item;
  the wizard reports presence via `doctor`, not versions.
- The executor command template is fixed per known CLI (opencode proven);
  exotic executors get a generic `{prompt}` template to edit by hand.
