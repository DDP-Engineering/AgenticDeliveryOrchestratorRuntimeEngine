<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration

`labels.selection.type_epic` is a nonempty configured label; shared selection excludes tickets bearing it from pickup and manual admission.

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
- `WorkflowConfig.verify_command` is an exact string with empty default;
  resolved serialization includes it. The conductor uses it only for direct
  runs, with the validate override or general gate timeout.

## Invariants

Configuration establishes the permitted forge, executor, container, budget,
and delivery policy before an orchestration run begins. It forbids forge
credentials in executor environment allowlists, rejects unsafe executor modes,
requires boolean review-state delivery, and validates paths, labels, retries, duration,
and resource limits instead of letting a later component guess.
`validate_config()` refuses every key this build does not read, in every
section and subtable (`labels.*`, `[executor]`, `[executor.web]`,
`container.egress`), with `[section] unknown key 'x': remove it from
config.toml`; missing keys take the documented defaults. `[container.egress]
mode` is refused with the added hint that `[executor] internet` decides the
agent's network access.
`ExecutorConfig.internet` (bool, default false) and `ExecutorConfig.web`
(`ExecutorWebConfig.search`: `exa` default, `brave`, `tavily`, `none`) are
validated in `_provider_issues` ("[executor] internet must be true or false",
"[executor.web] search must be one of ..."). `ContainerEgressConfig` holds
`allowlist` (extra hosts while internet is off; may be empty), `no_proxy`,
`proxy_image`, `proxy_port`, `network_prefix`. `egress_policy(config)` derives
the runtime `EgressPolicy`: internet off -> `allowlist-proxy` with the sorted
union of `pi_providers.provider_hosts(executor)` and the allowlist; internet
on -> `open`. A local profile refuses a non-empty allowlist. `[state] channel`, `[executor] default`,
`[executor] stage_host_auth`, an inline `[executor] api_key`, unknown
`[executor.endpoint]` keys, any other `[executor.<name>]` table and
`[labels.executor]` are refused this way.
Pi is the only coding agent. `ExecutorConfig` holds `provider` (required: a Pi
API-key provider id from the shipped catalog `adore/pi_catalog.json`,
`chatgpt` or `custom`), `model` (required, the model ID within the provider,
matching `pi_providers.MODEL_ID_RE`), `endpoint` (`ExecutorEndpointConfig`:
`base_url`, `api` default `openai-completions`), `command` (default
`branding.PI_NATIVE_COMMAND`, `pi -p --mode json --model {model} {prompt}`,
retained as the container preset), `mode`, `questions_file` and `env_keys` (default
empty; additional secret names, the provider's key variable is always passed).
`_provider_issues` requires `[executor.endpoint]` for `custom` and refuses the
table for any other provider; `base_url` is http(s) with a host and no user
info, query or fragment, and `api` is one of `openai-completions`,
`openai-responses`, `anthropic-messages`, `google-generative-ai`. Both backends
place generated endpoint settings in a managed agent directory. Native profiles
omit `command` and use fixed managed Pi RPC. `_chatgpt_issues` refuses `chatgpt`
with `[execution] backend = "local"` and explains that ChatGPT sign-in is
available only for container projects. It refuses
`[budgets] per_gate_timeout_seconds` above 3000 with `chatgpt`, and refuses each
`[workflow] stage_timeout_overrides.<stage>` above 3000 with `chatgpt`; 3000 is
`chatgpt.MAX_STAGE_SECONDS`, because a ChatGPT access token lasts about an hour
and is not refreshed during a stage. A `chatgpt` model is not checked against
the catalog's `chatgpt_models`. The command must contain `{prompt}`,
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

- `REQ-FUNC-222a0416`, `REQ-FUNC-381fdaaa`, `REQ-FUNC-fc7eac7a`,
  `REQ-FUNC-f980b054`: workflow.verify_command preserves shell text without
  trimming or coercion. Exactly empty means absent; nonstring, CR/LF and NUL
  values produce a key-named validation issue. AEGIS ignores the setting.
- `REQ-DATA-71366af6`: existing web resolved/raw reads and unrelated reviewed
  edits preserve it, with existing authorization/redaction. Metadata marks the
  key noneditable and frontend settings hide it; there is no dedicated web field.
  Proof: `test_config.py`, `test_web_config.py`, `test_web_config_raw.py` and
  exact catalog/settings tests.

- REQ-FUNC-bf8a9a47 / REQ-FUNC-cad97f4d / REQ-REL-8fe70d7b: `load_config` retains runtime-only absolute `source_path`, excluded from resolved serialization and equality. `validate_budgets` checks the closed table, positive integer limits, finite nonnegative cost and ChatGPT attempt cap without subprocesses. Startup includes this same check; conductor rereads bind parsed/resolved non-budget values to the validated configuration without rerunning the branch matcher. Proof: test_config.py, test_chatgpt.py and public Retry cases in test_orchestrator.py.

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: LocalConfig supplies the current account and optional tools PATH. The local backend rejects recipes, a non-empty container egress allowlist and container-only options. Reserved launch overrides and unknown local fields are refused. Container remains the default.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-e2b539d4`: Closed ExecutionConfig selection/backend/bounds; recipe mode permits empty profile image. Source authority belongs to preparation.md.

- `REQ-FUNC-ca17a8e8` - boolean review-state delivery and credential isolation.
- `REQ-FUNC-97e17737` - executor and egress policy validation.
- `REQ-FUNC-06b861ec` / `REQ-FUNC-77b798cf` - `[executor] internet` and
  `[executor.web] search` defaults and validation.
- `REQ-FUNC-f5e692dc` - `[container.egress] mode` is refused naming the switch.
- `REQ-SEC-e2ca6d05` / `REQ-FUNC-f801e9f3` - `egress_policy`: provider hosts
  only while off, open while on.
- `REQ-FUNC-2df31adf` - Pi is the only executor; `[executor]` needs a provider and a model.
- `REQ-FUNC-78b0ad95` - configuration of another coding agent is refused with the fix.
- `REQ-FUNC-7ce5b17a` - web-created and imported profiles share the typed
  validator.
- `REQ-REL-94e653aa` - checkpoint publication defaults to enabled and respects explicit overrides.

- `REQ-DATA-eebc4f88` - stage timeout overrides accept only the five executor stages.
- `REQ-FUNC-a5d65a57` - `chatgpt` is accepted on native and container backends and refused for a stage limit above 3000 s.

## Files

- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/config.py`, `04_Software/adore/pi_providers.py`
- `04_Software/adore/chatgpt.py` (`MAX_STAGE_SECONDS`)
- `04_Software/tests/test_config.py`, `04_Software/tests/test_pi_providers.py` (the `chatgpt` refusals)

## Actual branch admission names

`branch_naming_preview(..., run_id=..., iid=...)` permits actual identity checks using the same bounded one-second rule evaluation, with unchanged default example output. Fresh admission validates each generated actual name and refuses invalid identity types or rules. Proof: tests/test_drift_recovery.py and test_branch_naming.py.

The optional executor.thinking setting accepts only a level proven for the exact provider/model in the pinned Pi catalog; blank uses Pi default. Custom endpoint models support off.
