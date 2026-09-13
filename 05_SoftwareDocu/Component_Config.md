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
and cannot collide with lifecycle/control labels. Draft delivery remains
mandatory.

## 3. Security Validation

Executor `env_keys` may contain model-provider keys but known forge credential
names are rejected. Container-managed Git/proxy/home values cannot be
overridden. Commands remain noninteractive and shell control input is rejected
where appropriate.

## 4. Inputs and Outputs

Input is a TOML file plus derived profile paths. Output is a `Config` dataclass
and a stable list of validation problems. An unknown top-level section is an
error; unknown keys inside a known section are ignored.

## 5. Validation and Tests

`tests/test_config.py` covers defaults, recovery bounds, AEGIS stage names,
approval-label collisions, forge credential denial, container trust boundaries
and existing cross-platform configuration rules.
