# Container environment administration

## 1. Purpose

Let Pi install dependencies and configure its owned Linux container, with no project-specific environment profiles or conductor dependency broker.

## 2. Responsibilities

`container.system_packages` remains a strict opt-in boolean. The web label is **Allow agent environment administration**. `package_permissions.py` installs a root-owned, visudo-checked `NOPASSWD: ALL` rule for the measured non-root UID. An explicit `sudo id -u` confirmation must return root. The fixed bootstrap runs via the image OS Python with a cleared environment, never worktree code. Package-manager availability remains an image prerequisite; normal project files stay non-root owned.

`container_security.py` supplies a bundled Moby-derived seccomp allowlist with nested namespace operations enabled. Newly provisioned enabled agent containers get 512 MiB shm unless overridden and, when runtime security metadata says AppArmor is enabled, the named `adore-executor` policy. Invalid metadata, absent seccomp or missing assets fail with IsolationError. The runtime rejects missing AppArmor policy; there is no unconfined fallback. Windows/WSL translates the client-side policy path through the existing path mapper.

## 3. Dependencies and contracts

Image: root-owned OS Python/id, sudo/visudo, a supported package manager and a safe sudoers directory. Host: working user namespaces and, where enabled, the installed AppArmor policy with userns support. See [security and host preparation](../01_Documentation/Security_And_Credentials.md#agent-package-installation-authority).

Opted-in sudo has container-root authority, including mounted project data and injected tooling. It is not a fine-grained security boundary. Host mounts/socket/capabilities are not added. Network policy stays independent. No host policy installation, syscall disabling, migration or reset happens automatically.

## 4. Workflow integration

Execution plans pin the permission and owned resource before granting authority. Same-container resume retains dependencies. Runtime security arguments apply only when creating an enabled agent container, never to existing containers, proxies or credential helpers. Project permission changes require idle reviewed settings and a fresh job. Read-only connection checks do not grant sudo.

## 5. Evidence and verification

Existing targeted package-permission, isolation and prompt tests use injected runners. Live image and sandbox acceptance is separate; no setup-script tests or full suite are required for a focused change. Operational/session retention and redaction remain governed by the executor/session contracts.
