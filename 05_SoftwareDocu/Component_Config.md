<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration Component

The nonempty `labels.selection.type_epic` value names the ticket label excluded from automatic pickup and manual Start.

## 1. Purpose

`adore/config.py` loads typed TOML and rejects unsafe or ambiguous ADORE
settings before a poll starts.


`delivery.reviewers` is a list of forge account names (empty requests no review), each 1–255 characters without whitespace, controls or a leading option prefix. Configuration validation rejects malformed lists before forge CLI invocation. Review requests are independent of candidate publication approval and repository merge permissions.

ReadinessConfig defaults acceptance checking to false and priority checking to true. ReviewConfig defaults maximum additional revision rounds to five; explicit valid overrides retain authority. The supported readiness model contains acceptance, priority and the reserved scope hint.

`ClarificationConfig.answer_timeout` accepts a positive parsed duration independently of the reserved reminder. Both duration formats remain validated; zero and malformed answer durations fail before execution. The runtime still fails an expired clarification and bounds question rounds. Public validation proof: `test_validation_accepts_answer_timeout_independently_of_reserved_reminder` in `test_config.py`, with existing clarification conductor tests.

## Branch naming contract

`branch_naming_preview(template, rule, slug)` returns the fixed identity (`iid=1`, `run_id=sample-run-1`), rendered name, optional Python `re.match` result and closed issue codes. `validate_config` uses this same result before CLI/web application. Only plain `{slug}`, `{iid}`, `{run_id}` substitutions are supported and an identity field is required. Limits are 512 characters per template/rule and 255 for the sample name. Invalid formatting, Git branch syntax, malformed regex, mismatch and unevaluable process output are explicit findings. Python regex matching runs in a one-second isolated subprocess via JSON stdin with no shell/network/Git. The example does not prove all future identities.

Focused public-contract proof: `04_Software/tests/test_branch_naming.py`, existing config and wizard tests, and `04_Software/tests/test_web_branch_naming.py` for HTTP authority.

## 2. Workflow Settings

`WorkflowConfig` maps ticket labels to `feature`, `fix`, or `change`, carries a
quick-path hint, selects the one-token Python executable, and permits timeout
overrides only for the five AEGIS stages that launch an executor (`frame`,
`specify`, `design`, `build`, `validate`); `deliver` is refused like any
unknown stage. Mapping values accept only
those three task kinds. Bug/fix mappings win over change, configured feature
labels follow, and an unmatched ticket uses `default_kind`.

`PollingConfig.max_concurrent_runs` is a capacity ceiling only. The current
conductor is synchronous and serial; values above one do not create parallel
gates or workers.

`RecoveryConfig` owns `max_stage_failures`, `max_transient_retries`, and a
nonempty nonnegative backoff list. Defaults are 3, 3 and `[5, 30, 120]`.

`DeliveryConfig.approval_label` defaults to `agent-approved`, must be nonempty
and cannot collide with lifecycle/control labels. `delivery.draft` is a strict boolean: true (default) creates drafts; false creates ready reviews. Fresh human approval is required when the project policy enables it.
`publish_checkpoints` is a strict boolean, on by default for CLI and web.
Explicit false keeps intermediate checkpoints local. When enabled, the
conductor may publish guarded ticket-branch checkpoints before approval;
MR/PR creation follows the project approval policy. The reported
cost budget accepts a finite nonnegative USD amount; zero disables that cap
for subscription or local execution while iteration, time and file caps remain.

## 3. Security Validation

Executor `env_keys` may contain additional model-provider keys but known
forge credential names are rejected. A provider's key is never a
configuration value: it reaches Pi only through its credential variable. Container-managed Git/proxy/home values cannot be
overridden. Commands remain noninteractive and shell control input is rejected
where appropriate. `container.selinux_relabel` accepts only the values in
`SELINUX_RELABEL_OPTIONS`, which maps each accepted mode to the per-mount
option it appends and from which `SELINUX_RELABEL_MODES` is derived, so a mode
can never be accepted without an option to apply. The modes are `off` and
`shared`; the private SELinux `Z`
label is refused because it would bind the shared repository clone to a single
container.
`[container] runtime_env` and `[local] environment` names starting with a
removed coding agent's prefix (`OPENCODE_`, `CODEX_`, `QWEN_`) are refused
with a message to remove them from `config.toml`.

`container.build_definition` is an optional scalar for Docker build export.
Validation accepts an empty string or a portable repository-relative JSON path
with a full Git commit ID. The export reader checks the commit and its contents
on request. Executor launch uses the configured image independently.
Managed image definitions are separate records under the ADORE home. The normal
export dialog retains these sources without changing this optional Git-source
setting or any execution policy. A managed association takes precedence during
source export; preparation selects its effective image in memory.

## 4. Inputs and Outputs

Input is a TOML file plus derived profile paths. Output is a `Config` dataclass
and a stable list of validation problems. Missing keys take the documented
defaults. There is no compatibility with earlier builds: an unknown top-level
section is an error, and `validate_config` refuses any key the build does not
read, in every section and subtable (`labels.*`, `container.egress`), with
`[section] unknown key 'x': remove it from config.toml`; `[local]` and
`[execution]` have their own strict validators. The removed `[state] channel`
key is refused like any other unknown key.

`ExecutorConfig` (`[executor]`) configures Pi, ADORE's only coding agent:
`provider` (required), `model` (required, the model ID within the provider),
`internet` (strict boolean, default false: "Internet access for the agent"),
`endpoint` (`ExecutorEndpointConfig`), `web` (`ExecutorWebConfig`,
`[executor.web]`: `search` is `exa` (default, no key), `brave`, `tavily` or
`none`, the `WEB_SEARCH_CHOICES` of `pi_providers.py`), `command`, `mode`
(`thick` or `headless`), `questions_file` and `env_keys` (default empty:
additional secret names; the provider's key variable is always passed, and
with internet on and `brave` or `tavily` search the `SEARCH_KEY_VARIABLES`
entry `BRAVE_API_KEY` or `TAVILY_API_KEY`). The removed
`default` and `stage_host_auth` keys and every other `[executor.<name>]` table
are refused as unknown `[executor]` keys, and the removed `[labels] executor`
table as an unknown `[labels]` key. Unknown keys inside `[executor]` and
`[executor.endpoint]`, such as an inline `api_key`, are refused by name. There
is no migration.

`_provider_issues` checks the provider rules against the shipped Pi catalog
(`adore/pi_providers.py`, `pi_catalog.json`): `provider` is a Pi API-key
provider id from the catalog, `chatgpt` or `custom`; `model` matches
`MODEL_ID_RE` (`[A-Za-z0-9~][A-Za-z0-9._:/@+~-]{0,199}`: no whitespace,
quotes or control characters, at most 200 characters). `[executor.endpoint]`
(`base_url`, `api`, default `openai-completions`; also `openai-responses`,
`anthropic-messages`, `google-generative-ai`) is required for `custom` and,
when the table is present in the file, refused for any other provider.
`base_url` is an http(s) address with a host and no user name, password,
query or fragment, as seen from the selected execution environment. Both
backends use a managed agent directory for Pi's generated `models.json`.
An unreadable catalog is reported as
an `[executor] provider` issue. `_provider_issues` also refuses a non-boolean
`internet`, a non-table `[executor.web]` and a `search` outside
`WEB_SEARCH_CHOICES`.

`ContainerEgressConfig` (`[container.egress]`) holds the per-run proxy of an
internet-off run: `allowlist` (extra hosts besides the model provider, exact
or `*.` wildcard names; default empty), `no_proxy`, `proxy_image`,
`proxy_port` and `network_prefix`. It has no mode: `_unknown_key_issues`
refuses `mode` with `[container.egress] unknown key 'mode': remove it from
config.toml; [executor] internet decides the agent's network access`.
`egress_policy(config)` derives the run's `EgressPolicy`, never read from a
file: internet on gives mode `open`; internet off gives mode `allowlist-proxy`
whose allowlist is `pi_providers.provider_hosts(executor)` plus
`[container.egress] allowlist`, deduplicated and sorted. `provider_hosts` is
the catalog's `hosts` for an API-key provider (generated from every `baseUrl`
of Pi's pi-ai provider data by `02_Tools/generate_pi_catalog.py`), the
`openai` hosts for `chatgpt`, and the `base_url` host (a name or an IP
address) for `custom`. `EgressPolicy` still supports mode `none`, but no
configuration selects it. The orchestrator, Test AI connection and the
readiness probe use `egress_policy`; a local run is not restricted by it.

`_chatgpt_issues` refuses what a ChatGPT subscription (`provider = "chatgpt"`)
cannot run, because ADORE mints a short-lived ChatGPT access token before every
stage through the selected trusted helper and does not refresh it during a stage:

- `[budgets] per_gate_timeout_seconds` above 3000 is refused;
- each `[workflow] stage_timeout_overrides.<stage>` above 3000 is refused.

3000 is `chatgpt.MAX_STAGE_SECONDS`: an access token lasts about an hour, Pi
keeps a 3-minute margin and ADORE asks for 5 minutes more. The model is not
checked against the catalog's `chatgpt_models`.

```toml
[executor]
provider = "openai"
model = "gpt-5.5"
```

A ChatGPT subscription (container or native run; the server signs in once in the
web interface):

```toml
[executor]
provider = "chatgpt"
model = "<a model from chatgpt_models>"
```

An OpenAI-compatible endpoint (container run only):

```toml
[executor]
provider = "custom"
model = "qwen3-coder"

[executor.endpoint]
base_url = "http://192.168.1.20:1234/v1"
api = "openai-completions"
```

`command` retains the container preset `branding.PI_NATIVE_COMMAND`
(`pi -p --mode json --model {model} {prompt}`). A container run drives the
image's pinned Pi over RPC. Native profiles omit this key and use managed
Pi RPC. Configured templates require `{prompt}`, refuse `--auto` and permit
only `{prompt}`, `{model}` and `{worktree}` placeholders.

## 5. Validation and Tests

`tests/test_config.py` covers defaults, recovery bounds, AEGIS stage names,
approval-label collisions, forge credential denial, container trust boundaries
and existing cross-platform configuration rules. `tests/test_pi_providers.py`
covers the shipped catalog (including `chatgpt_models`), provider/model/endpoint
validation, endpoint model generation, the local-run and stage-limit
refusals of `chatgpt`, `secret_names` and `models_json`. The internet switch
is covered by `test_internet_defaults_off_with_exa_search`,
`test_internet_and_search_values_are_validated`,
`test_container_egress_mode_is_refused_naming_the_switch`,
`test_egress_policy_off_admits_only_the_provider_hosts` and
`test_search_key_reaches_only_an_internet_on_run`.

## Reviewed preparation settings

`ExecutionConfig` is a closed `[execution]` table: container backend, optional exact Git selection, step/total timeout and attempt cap. Image may be empty only with preparation. Grammar/source validation belongs to `preparation.py`. Missing keys take the documented defaults. See [Container preparation](../01_Documentation/Container_Preparation.md) and `tests/test_preparation.py`.

## Native execution contract

The local backend uses the pinned ADORE-managed Pi and accepts only the current account and optional tools PATH. Config refuses a local executor command, unknown local fields, reserved launch environment overrides and container-only options. OpenAI-compatible endpoints are supported by a fresh managed agent directory.

## Background branch rule evaluation

The one-second isolated Python regex subprocess uses shared automatic-process
options and pager defaults. Its JSON stdin remains the only rule/name transport;
stdout parsing and closed timeout/process-error findings retain their contract.
Focused proof: `tests/test_automatic_processes.py` and `tests/test_branch_naming.py`.

## Agent-controlled system packages

Strict boolean container.system_packages defaults false. Enabled mode is container-only, rejects host-oriented runtime overrides and retains ADORE's managed package permissions. Egress remains independent. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.

## Actual branch-rule checks

`branch_naming_preview` optionally accepts actual `run_id` and positive `iid` identities while retaining its default example response. Admission validates each actual selected name through this same bounded Python regex/Git-name check. Invalid types, timeout and rule mismatch fail closed; rules are never bypassed to allocate a generation. Proof: tests/test_drift_recovery.py and tests/test_branch_naming.py.

## Budget source metadata

`load_config` retains an absolute `Config.source_path` for boundary rereads. It is
runtime metadata, excluded from `to_dict`, equality and all stored configuration.
`budgets.max_iterations` defaults to 20; the conductor owns the validated budget-only
reread and non-budget drift refusal. No other settings are hot-rebound.

`validate_budgets(config)` is the shared pure check for the closed budget table,
positive integer limits, finite nonnegative cost and ChatGPT stage-timeout cap.
Startup `validate_config` includes it. Boundary refresh reuses it with exact parsed
and resolved non-budget binding to the startup-validated configuration; it launches
no regex matcher, host check or CLI. Unknown sections/keys outside budgets fail
the binding; unknown budget keys fail the closed table check.

Non-budget binding preserves scalar types as well as values: boolean false and numeric zero are distinct. Canonical typed JSON comparison launches no probes.


Pi thinking is optional; explicit values are validated against the pinned provider/model catalog, with custom endpoints limited to off. Invalid or unproven levels fail configuration validation.

## Publication approval policy

`delivery.require_human_approval` is a strict boolean, default true. It selects
whether human candidate approval precedes publication; it does not change
validation, draft state, guarded publication, or the human merge boundary.
