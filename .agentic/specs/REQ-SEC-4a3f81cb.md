<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-SEC-4a3f81cb — Confine cleanup to the current project's resources

Also governs REQ-FUNC-aae1904f (removal of the project's finished and orphaned
run resources) and REQ-REL-2219035e (corrupt runs keep their resources).

## Behavior

`adore [--profile P] cleanup` retains active, failed, human-owned and corrupt runs.
Stateless resources remain because a name or matching run-ID prefix alone does
not prove ownership. A saved done, cancelled or stale run is eligible only while
its lifecycle lock is exclusively owned and its configuration-derived branch,
container, worktree and native IO identities match the saved run.

Container release validates the exact executor/proxy mounts, immutable IDs and
complete network membership; no foreign network member is removed. Destructive
runtime commands use immutable IDs. Worktree release verifies the expected Git
common directory, top level and branch. Unconfirmed runtime release preserves
the worktree. Git registry mutation is serialized, without pruning unrelated
registrations or force-deleting unproven husks.

The report lists actual verified removals under `containers_removed`,
`proxy_containers_removed`, `egress_networks_removed` and `worktrees_removed`.
A preserved or missing resource is not reported as removed. A readable local
operator lock is reclaimed only after proven owner death; live/unknown owners
are retained. Kernel files remain under the server's resource-lock directory.

## Failure and recovery

Unproven, corrupt or changed evidence produces typed refusal and preserves
resources for inspection. The operator handles stateless resources explicitly;
a prefix match grants no cleanup authority. Other projects remain independent,
including profiles for the same repository using separate project resource suffixes.

## Verification

Offline injected public cleanup and runtime ownership tests cover terminal removal,
peer preservation, stateless/corrupt refusal, runtime failure, invalid mounts and
foreign network members. No live Git, container or forge command is used.
