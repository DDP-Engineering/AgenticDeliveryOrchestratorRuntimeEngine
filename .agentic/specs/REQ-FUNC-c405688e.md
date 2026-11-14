<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agent-controlled system packages

## Interface and authority

`[container] system_packages = false` is a strict boolean, enabled only by explicit operator configuration. Native execution rejects true. False retains the image authority; it does not claim to revoke arbitrary custom-image privileges. True authorizes direct noninteractive `sudo -n` package managers, retaining agent reasoning, command outputs and existing stage limits. It never changes egress or exposes forge credentials.

The runtime measures a non-root numeric UID and configures a root-owned 0440 sudoers file inside the owned container. Supported installed absolute manager paths are apt-get, apt, dpkg, dnf, yum, apk, pacman and zypper. Package-manager hooks/scripts have effective container-root authority. Privileged containers, host namespace overrides, additional mounts/devices/capabilities and user/environment/entrypoint overrides are incompatible with this managed mode. Normal rootless Podman keep-id is supported.

## State and recovery

Only enabled policies add `system_packages = true` to the container policy; disabled policies omit this optional true marker. Enabled jobs use the existing execution record, status not-required without a recipe, and actual container/image IDs. The status describes recipe execution only, never installed package readiness. Resource/policy drift fails closed; an absent resource requires a fresh job or existing explicit recipe recovery. Same-resource authorization may be repeated, never package installation itself. Existing custom images must supply sudo, visudo and a supported manager; ADORE does not download them.

## Verification

Offline injected commands prove authorization uses only the owned container, preserves all egress modes, and never executes an installation on the server. Negative cases cover root/malformed UID, missing tools, root bootstrap nonzero/timeout, drift/corrupt state, local mode and unsafe runtime arguments. API/frontend tests prove reviewed boolean configuration, local hiding, four locales and independent network values. Live installation is separate operator acceptance; do not claim it from mocked commands.

## Retained output and authentication

Enabled RPC gates keep returned operational tails, stderr and questions sanitized and bounded at 64 KiB. Their separate session stdout preserves literal bounded events, including known API keys and ephemeral stage access tokens that the agent printed, and archives without post-gate rewriting. The shared reader authorizes job readers and excludes system messages. Complete original usage remains authoritative. Native RPC shares this policy; non-RPC file-protocol streams retain their sanitized 64 KiB bounds. The refresh token and server sign-in stay outside the job container.

Operational limits count encoded UTF-8 bytes after sanitization. RPC archives copy the literal bounded session file, independently of returned operational tails. Non-RPC archives encode sanitized retained streams without newline expansion. Original usage remains authoritative.
