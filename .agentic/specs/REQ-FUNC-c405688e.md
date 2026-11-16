<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Direct agent package installation

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-c405688e](../requirements/functional/REQ-FUNC-c405688e.toml) — Direct agent package installation

When container system-package permission is enabled for a run, ADORE shall authorize the executor guard only in its verified owned container and confirm the change before further execution. The permission is part of the pinned execution policy and does not grant host installation, network changes or unrelated privilege overrides.

Verification scope: Exercise enabled/disabled package permission and owned-container confirmation with injected runtime results; reject missing/failed confirmation and host or privilege overrides.

### [REQ-REL-6922cfe5](../requirements/reliability/REQ-REL-6922cfe5.toml) — Pinned package-enabled execution recovery

When a package-enabled job is resumed, ADORE shall bind installation authority to its persisted policy and exact container/image identities, failing explicitly on drift or resource loss rather than assuming the prior installed environment exists.

Verification scope: Offline conductor and persisted-state tests cover same-container resume, policy changes, replaced/missing resources and corrupt package permission fields, with both enabled and disabled current package-permission policies.

### [REQ-SEC-c5d56d9f](../requirements/security/REQ-SEC-c5d56d9f.toml) — Independent package and network authority

When administrative package installation is enabled for a container, ADORE shall preserve its separately configured open, none or allowlist-proxy egress and host/forge credential boundaries.

Verification scope: Offline Docker, Podman and WSL argv tests cover all three egress modes with package authorization; unsafe container overrides and local-backend elevation are refused.

### [REQ-UX-812acd4b](../requirements/ux/REQ-UX-812acd4b.toml) — Reviewed package installation permission

When an administrator configures a container project, ADORE shall expose a separately reviewed boolean permission for agent system package installation, defaulting to disabled without changing network settings.

Verification scope: Offline API tests inspect metadata, stage/apply an exact boolean candidate with paused idle guards, and reject malformed/unauthorized/stale requests; frontend tests verify localized container-only visibility.

## Implementation

- `04_Software/adore/config.py`
- `04_Software/adore/execution.py`
- `04_Software/adore/executor/base.py`
- `04_Software/adore/executor/launcher.py`
- `04_Software/adore/isolation.py`
- `04_Software/adore/orchestrator.py`
- `04_Software/adore/package_permissions.py`
- `04_Software/adore/preparation.py`
- `04_Software/adore/state.py`
- `04_Software/adore/web/app.py`
- `04_Software/docker/Dockerfile.executor-base`
- `04_Software/tests/test_system_packages.py`
- `04_Software/web/e2e/system-packages.spec.ts`
- `04_Software/web/src/App.tsx`
- `04_Software/web/src/executorSettings.ts`
- `04_Software/web/src/settingHelp.ts`
- `04_Software/web/src/settingKeys.json`
- `04_Software/web/src/settings.ts`
- `04_Software/web/tests/systemPackages.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_system_packages.py::test_package_authority_fails_closed_on_missing_or_failed_confirmation`
- `04_Software/tests/test_system_packages.py::test_package_authority_uses_owned_container_without_network_or_host_installs`
- `04_Software/tests/test_system_packages.py::test_package_execution_policy_fingerprints_permission`
- `04_Software/tests/test_system_packages.py::test_package_only_state_preserves_exact_resource_without_claiming_recipe_success`
- `04_Software/tests/test_system_packages.py::test_package_permission_rejects_host_or_privilege_overrides`
- `04_Software/tests/test_system_packages.py::test_package_permission_rejects_native_host_but_accepts_rootless_keep_id`
- `04_Software/tests/test_system_packages.py::test_package_plan_rejects_noncanonical_opt_in`
- `04_Software/tests/test_system_packages.py::test_package_setting_refuses_non_boolean_candidates`
- `04_Software/tests/test_system_packages.py::test_package_setting_requires_review_and_preserves_network`
- `04_Software/tests/test_system_packages.py::test_public_retry_pins_package_authority_and_container`
