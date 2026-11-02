<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration

## Routing

Use this page for typed TOML loading, executor/auth validation, budgets,
container settings and delivery policy. Start at `04_Software/adore/config.py`;
verify with `04_Software/tests/test_config.py`. Web config edits belong to
`web-interface.md` and assisted prompts to `wizard.md`.


`REQ-UX-34718dd6`: Reviewer configuration is an account list (empty requests no review) with bounded names and rejection of whitespace, controls and option prefixes; reviewers request forge review independently of publication approval and merge policy.

## Purpose and boundaries

Loads TOML into typed configuration for platform, selection, executor,
container, recovery, budgets, delivery, profiles, and metrics. Validation
fails closed at external trust boundaries before a poll starts.

## Branch naming contract

`branch_naming_preview(template, rule, slug)` returns the fixed identity (`iid=1`, `run_id=sample-run-1`), rendered name, optional Python `re.match` result and closed issue codes. `validate_config` uses this same result before CLI/web application. Only plain `{slug}`, `{iid}`, `{run_id}` substitutions are supported and an identity field is required. Limits are 512 characters per template/rule and 255 for the sample name. Invalid formatting, Git branch syntax, malformed regex, mismatch and unevaluable process output are explicit findings. Python regex matching runs in a one-second isolated subprocess via JSON stdin with no shell/network/Git. The example does not prove all future identities.

Focused public-contract proof: `04_Software/tests/test_branch_naming.py`, existing config and wizard tests, and `04_Software/tests/test_web_branch_naming.py` for HTTP authority.

## Public interface

- `REQ-FUNC-84f30174`: bounded shared branch-name example and Python regex findings.
- `load_config()` builds the dataclass model; `validate_config()` returns
  deterministic operator-facing problems.
- `ConfigError` distinguishes unreadable/malformed configuration from a valid
  model with reported validation issues.

## Invariants

Configuration establishes the permitted forge, executor, container, budget,
and delivery policy before an orchestration run begins. It forbids forge
credentials in executor environment allowlists, rejects unsafe executor modes,
requires boolean review-state delivery, and validates paths, labels, retries, duration,
and resource limits instead of letting a later component guess.
`validate_config()` refuses every key this build does not read, in every
section and subtable (`labels.*`, `[executor]`, `container.egress`), with
`[section] unknown key 'x': remove it from config.toml`; missing keys take the
documented defaults. `[state] channel`, `[executor] default`,
`[executor] stage_host_auth`, any `[executor.<name>]` table and
`[labels.executor]` are refused this way.
Pi is the only coding agent. `ExecutorConfig` holds `model` (required,
provider/model), `command` (default `branding.PI_NATIVE_COMMAND`,
`pi -p --mode json --model {model} {prompt}`, used only by a native run),
`mode`, `questions_file` and `env_keys`. The command must contain `{prompt}`,
must not contain the `--auto` token, and may use only the `{prompt}`, `{model}`
and `{worktree}` placeholders (a literal brace is doubled). `[container]
runtime_env` and `[local] environment` names starting `OPENCODE_`, `CODEX_` or
`QWEN_` (`REMOVED_AGENT_ENV_PREFIXES`) are refused with
`... configures a removed coding agent: remove it from config.toml`.
`delivery.publish_checkpoints` is a strict boolean, enabled by default for CLI
and web with explicit false respected; candidate-bound MR/PR
approval remains mandatory. The reported-cost cap accepts finite nonnegative
USD amounts, with zero disabling only that cap. Stage timeout overrides name
only `frame`, `specify`, `design`, `build` or `validate`, the stages that
launch an executor; any other key, `deliver` included, fails validation.

Shared CLI/web defaults are acceptance=false, priority=true and maximum additional revision rounds=5 (minimum one), with explicit overrides retained. The typed readiness model contains acceptance, priority and reserved scope hint.

`REQ-FUNC-c6c694cc`: Human-answer timeout is a positive parsed duration independent of reserved reminder timing. Both duration formats remain checked; runtime clarification expiry/round semantics are unchanged. Focused proof: `tests/test_config.py` and clarification cases in `tests/test_orchestrator.py`.

Both CLI and web use the same validated model before changing runtime policy.

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: LocalConfig supplies account/home/path/environment/cgroup_root. Explicit execution.backend=local rejects recipes, restricted egress, staging and container-only options. Non-secret local maps reject managed/forge variables and literal inline provider credentials. Container remains the default.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-e2b539d4`: Closed ExecutionConfig selection/backend/bounds; recipe mode permits empty profile image. Source authority belongs to preparation.md.

- `REQ-FUNC-ca17a8e8` - boolean review-state delivery and credential isolation.
- `REQ-FUNC-97e17737` - executor and egress policy validation.
- `REQ-FUNC-2df31adf` - Pi is the only executor; `[executor]` needs only a model.
- `REQ-FUNC-78b0ad95` - configuration of another coding agent is refused with the fix.
- `REQ-FUNC-7ce5b17a` - web-created and imported profiles share the typed
  validator.
- `REQ-REL-94e653aa` - checkpoint publication defaults to enabled and respects explicit overrides.
- `REQ-DATA-eebc4f88` - stage timeout overrides accept only the five executor stages.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/config.py`
- `04_Software/tests/test_config.py`
