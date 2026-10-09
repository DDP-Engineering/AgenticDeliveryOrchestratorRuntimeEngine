<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration Component

## 1. Purpose

`adore/config.py` loads typed TOML and rejects unsafe or ambiguous ADORE
settings before a poll starts.


`delivery.reviewers` is a nonempty list of forge account names, each 1–255 characters without whitespace, controls or a leading option prefix. Configuration validation rejects malformed lists before forge CLI invocation. Review requests are independent of candidate publication approval and repository merge permissions.

ReadinessConfig defaults acceptance checking to false and priority checking to true. ReviewConfig defaults maximum additional revision rounds to five; explicit valid overrides retain authority. The supported readiness model contains acceptance, priority and the reserved scope hint.

`ClarificationConfig.answer_timeout` accepts a positive parsed duration independently of the reserved reminder. Both duration formats remain validated; zero and malformed answer durations fail before execution. The runtime still fails an expired clarification and bounds question rounds. Public validation proof: `test_validation_accepts_answer_timeout_independently_of_reserved_reminder` in `test_config.py`, with existing clarification conductor tests.

## Branch naming contract

`branch_naming_preview(template, rule, slug)` returns the fixed identity (`iid=1`, `run_id=sample-run-1`), rendered name, optional Python `re.match` result and closed issue codes. `validate_config` uses this same result before CLI/web application. Only plain `{slug}`, `{iid}`, `{run_id}` substitutions are supported and an identity field is required. Limits are 512 characters per template/rule and 255 for the sample name. Invalid formatting, Git branch syntax, malformed regex, mismatch and unevaluable process output are explicit findings. Python regex matching runs in a one-second isolated subprocess via JSON stdin with no shell/network/Git. The example does not prove all future identities.

Focused public-contract proof: `04_Software/tests/test_branch_naming.py`, existing config and wizard tests, and `04_Software/tests/test_web_branch_naming.py` for HTTP authority.

## 2. AEGIS Settings

`WorkflowConfig` maps ticket labels to `feature`, `fix`, or `change`, carries a
quick-path hint, selects the one-token Python executable, and permits timeout
overrides only for the six working AEGIS stages. Mapping values accept only
those three task kinds. Bug/fix mappings win over change, configured feature
labels follow, and an unmatched ticket uses `default_kind`.

`PollingConfig.max_concurrent_runs` is a capacity ceiling only. The current
conductor is synchronous and serial; values above one do not create parallel
gates or workers.

`RecoveryConfig` owns `max_stage_failures`, `max_transient_retries`, and a
nonempty nonnegative backoff list. Defaults are 3, 3 and `[5, 30, 120]`.

`DeliveryConfig.approval_label` defaults to `agent-approved`, must be nonempty
and cannot collide with lifecycle/control labels. `delivery.draft` is a strict boolean: true (default) creates drafts; false creates ready reviews. Fresh human approval remains mandatory.
`publish_checkpoints` is a strict boolean, on by default for CLI and web.
Explicit false keeps intermediate checkpoints local. When enabled, the
conductor may publish guarded ticket-branch checkpoints before approval;
MR/PR creation still waits for fresh candidate-bound approval. The reported
cost budget accepts a finite nonnegative USD amount; zero disables that cap
for subscription or local execution while iteration, time and file caps remain.

## 3. Security Validation

Executor `env_keys` may contain model-provider keys but known forge credential
names are rejected. Container-managed Git/proxy/home values cannot be
overridden. Commands remain noninteractive and shell control input is rejected
where appropriate. `container.selinux_relabel` accepts only the values in
`SELINUX_RELABEL_OPTIONS`, which maps each accepted mode to the per-mount
option it appends and from which `SELINUX_RELABEL_MODES` is derived, so a mode
can never be accepted without an option to apply. The modes are `off` and
`shared`; the private SELinux `Z`
label is refused because it would bind the shared repository clone to a single
container.
`stage_host_auth` is valid only with the OpenCode or Codex executor, whose
host OAuth files ADORE knows how to stage. Pi and Qwen must use provider-key
configuration; validation rejects their host-auth setting before a run starts.

## 4. Inputs and Outputs

Input is a TOML file plus derived profile paths. Output is a `Config` dataclass
and a stable list of validation problems. An unknown top-level section is an
error; unknown keys inside legacy sections are ignored; unknown `[execution]` keys fail closed.

## 5. Validation and Tests

`tests/test_config.py` covers defaults, recovery bounds, AEGIS stage names,
approval-label collisions, forge credential denial, container trust boundaries
and existing cross-platform configuration rules.

## Reviewed preparation settings

`ExecutionConfig` is a closed `[execution]` table: container backend, optional exact Git selection, step/total timeout and attempt cap. Image may be empty only with preparation. Grammar/source validation belongs to `preparation.py`. Defaults preserve old profiles. See [Container preparation](../01_Documentation/Container_Preparation.md) and `tests/test_preparation.py`.

## Native execution contract

LocalConfig supplies account/home/path/environment/cgroup_root. Explicit execution.backend=local rejects recipes, restricted egress, staging and container-only options. Non-secret local maps reject managed/forge variables and literal inline provider credentials. Container remains the default.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.
