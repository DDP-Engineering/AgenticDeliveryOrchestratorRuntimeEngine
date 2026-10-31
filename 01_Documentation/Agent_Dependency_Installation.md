<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agent-controlled dependency installation

## Enable direct installation

In Project Settings > Agent and model, an administrator can review and apply **Allow agent system package installation**. It defaults to false and is container-only. Pause monitoring and wait for idle jobs before applying, then start a fresh job. The CLI equivalent is `adore --profile <name> config set container.system_packages true`.

The agent installs dependencies directly, reads command outputs and exits, diagnoses missing prerequisites and retries within existing stage/job limits. ADORE configures permission, not a dependency list or installation broker. Existing optional recipes still run before the agent.

```toml
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See LICENSE.txt. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
[container]
system_packages = true
[container.egress]
mode = "none"
```

Installation rights and egress are independent: open permits reachable sources, allowlist-proxy permits configured HTTP/HTTPS domains, and none permits only available local sources. Enabling installation never changes network access. The model provider must also be reachable under that policy.

## Image and agent requirements

Rebuild the executor base image from the current Dockerfile, or use a compatible trusted image with root-owned `/usr/bin/python3`, `/usr/bin/id`, sudo, visudo and `/etc/sudoers.d`. ADORE installs none of these during a job. Missing tools cause an explicit authorization failure. Read-only host/model checks do not grant permission or prove package installation.

The agent remains the normal image user and runs, for example, `sudo -n apt-get update` and `sudo -n apt-get install -y <needed-package>` inside its job. Supported installed manager paths are `/usr/bin/apt-get`, `/usr/bin/apt`, `/usr/bin/dpkg`, `/usr/bin/dnf`, `/usr/bin/yum`, `/sbin/apk`, `/usr/bin/pacman` and `/usr/bin/zypper`. Agent tool permissions must allow these commands noninteractively. The Codex container preset uses the container as its sandbox; workspace-only sandbox presets are refused with this permission. Other executors retain their existing tool policies and forge deny rules; no global tool auto-approval is enabled.

Keep project libraries and code owned by the normal user. Respect lockfiles; changing project dependencies remains a reviewed product change. Administrative package scripts/hooks have effective root authority throughout the container. sudo is not a sandbox that limits what those package scripts can do. Provider credentials already available inside the container are also within that authority.

## Host and recovery boundaries

The managed mode refuses runtime overrides for extra mounts, host namespaces, devices, users, capabilities, environment, entrypoints or privileged mode. Memory/CPU/process limits and rootless Podman `--userns=keep-id` remain available. Standard repository/worktree/IO/cache mounts are shared host surfaces; container-root access is not a guarantee of complete host isolation. Forge credentials remain outside the container; publication and merge authority are unchanged.

An immutable execution plan binds the enabled permission, network configuration and exact container/image identities. Same-container stop/resume retains installed system packages. Changed policy, replaced/missing container or image drift fails closed; start a fresh job to reassess/install dependencies, or use existing explicit recipe recovery when applicable. The image itself is never updated by an installation. A not-required recipe status does not claim that dependencies are installed.

For enabled jobs, the launcher sanitizes known credential values and common Bearer credentials and retains at most 64 KiB per stdout/stderr stream in live exchange files and immutable launch archives after a gate. This is a UTF-8 byte limit; archives preserve the retained stream without host newline expansion. During execution the normal live gate transport still writes its files; this is a retention cap, not a filesystem quota. Complete original JSONL telemetry is streamed before truncation; retention limits do not reduce recorded token or cost totals. The agent sees its tool results before this retention step. Root authorization runs on the exact immutable container ID, uses fixed trusted code and receives no additional provider environment from ADORE.

When stage_host_auth is enabled, opted-in jobs require the approved host auth file. ADORE collects bounded redaction values from the exact staged snapshot, with strict duplicate/depth/size validation, and keeps them in memory only. Missing or corrupt snapshots stop the job before agent work; disable that bridge for API-key-only authentication.
