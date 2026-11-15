<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Git and container isolation

## Purpose and source ownership

`04_Software/adore/isolation.py` owns worktree/Git mechanics and container-runtime
operations. `WorktreeManager` prepares owned branches/worktrees, fingerprints and
checkpoints candidates and handles lease-bound host publication/deletion.
`ContainerManager` provides runtime inventory, mounts, egress companions and
bounded commands. The conductor decides when to provision, wait, publish or
release. [Execution](Component_Execution.md) binds immutable runtime ownership;
[Local execution](Component_Local_Execution.md) implements native process control.

## Worktrees, branches and checkpoints

Each admitted run gets an isolated worktree and derived ticket branch. Production
resource names carry stable project identity so profiles targeting the same
repository/ticket cannot share mutable resources accidentally. Git operations
validate bounded output and fail with typed `IsolationError` on invalid evidence.

Fresh admission checks exact local/remote absence of the configured base branch,
then at most three random -g plus twelve-hex alternatives. Occupied refs are
preserved. Creation uses atomic git worktree add -b and refuses existing paths;
recovery reattaches only under the saved ownership contract. Branch naming and
repository policy are validated before destructive cleanup.

Host checkpoints use configured author/committer identity. Before staging and
again before committing, NUL-delimited Git evidence checks untracked additions
and the complete staged path set without rename inference. Suspicious whole
percent-variable path segments or the Windows cache-path signature raise
`SuspiciousCheckpointPathError`; no source file is deleted to hide the problem.

Progress push verifies exact refs, ancestry and compare-and-update leases; it
never pushes the target or creates a review itself. Remote deletion requires a
saved checkpoint lease and verified absence afterwards. An absent remote can
succeed with allow_absent; an unproven present branch remains untouched.
See [Orchestrator](Component_Orchestrator.md) for publication/merge policy.

## Direct exchange files

Progress fingerprints and checkpoints accept explicit repository-relative literal
exclusions for ADORE_SUMMARY.md and the configured question path. Exchange text
alone is not product progress. Absolute/traversing/control or Git-administration
paths, linked parents, nonregular/multiply-linked files and collisions with source
already in HEAD are refused before exclusion.

Exchange-aware staging resets only the literal index paths, excludes them from
add -A and rechecks the entire staged set. It does not delete working files or
hide repository-owned source. Summary reads require strict UTF-8 and stable owned
file evidence. `remove_summary` accepts only that run's unchanged transient receipt
and verifies absence. Read/remove errors never authorize completion or checkpoints.
These operations run after the executor has settled.

## Container contract

Fixed mounts are repository → /adore/repo, worktree → /adore/work, run IO →
/adore/io, uv cache → /home/adore/.cache/uv and npm cache → /home/adore/.npm.
IO is outside the candidate worktree. Runtime-project images supply the reviewed
toolchain. Shared named caches survive job cleanup.

A run container idles between bounded exec/RPC commands. Provision reports created,
started or running. Park stops the owned resource while retaining its filesystem;
resume verifies the pinned resource before reuse. Fresh container/image identity,
name, mount bindings and status come from bounded strict inspect evidence.
Unexpected identity or malformed output is a refusal, not a replacement decision.
Local image inspection does not pull an image. Explicit diagnostic checks use
pull_never after inspection. See [Project images](Component_Project_Images.md).

### Native Git discovery in containers

Fresh repository containers mount a generated regular container.git file read-only
at /adore/work/.git, pointing to the mounted linked-worktree administration directory.
The host worktree's own pointer is unchanged. Managed GIT_DIR/GIT_COMMON_DIR/
GIT_WORK_TREE provisioning metadata is consumed rather than inherited by descendants;
image/runtime selector defaults are cleared. Native Git therefore honors cwd,
-C and nested repositories. A bounded runtime receipt verifies the pointer,
selector absence and actual discovery.

The creation label io.ddp.adore.git-binding=pointer-v1 selects pointer validation
on reuse; unknown labels are refused. The current runtime code also accepts an
empty/null binding label and leaves that container's creation-time Git environment
unchanged. This is a remaining unlabelled-container reuse branch, not a stored-data
conversion or a guarantee that an earlier build is supported. This document records that remaining code path without authorizing a format conversion.

### Environment and wrapped runtimes

Secrets travel through the runtime CLI environment using bare --env KEY, never
inline values in process argv. Approved non-secret Git/Home/Pi/cache/proxy values
use inline runtime flags. Both exec and spawn clear inherited repository selectors
and force GIT_PAGER=cat/PAGER=cat. Windows runtime commands suppress new consoles.

Runtime argv may be Docker, Podman or a checked WSL prefix. Standard WSL forms
normalize to direct --exec; custom wrappers require an explicit command boundary.
Launch options are parsed before the runtime command. Invalid/incomplete wrappers
are refused before invocation. Windows mount paths become WSL paths where needed;
secret names are explicitly forwarded via WSLENV. Paths and script values remain
literal single argv arguments.

SELinux shared relabel appends z to host binds only, including generated read-only
proxy config. Named cache volumes are not relabelled. Private Z is not an accepted
selinux_relabel value. UID/GID or rootless keep-id mapping remains operator-owned
image/runtime configuration so host and container can read their shared files.

## Egress and package authority

Configuration derives open when executor internet is on and allowlist-proxy when
off. The latter creates a dedicated internal network and proxy companion, writes
bounded Squid host/IP allowlist rules with deny-all remainder and supplies proxy
environment to the executor. Host aliases needed by the proxy are passed where
the proxy opens connections. The lower-level none policy remains available to
callers but is not selected by current configuration.

Companion names use bounded run-derived hashes. Release verifies actual mounts,
internal network membership and immutable IDs, then confirms absence. Foreign
members, replacements, unproven orphan networks and companions shared with retained
executors are protected. Cleanup recognizes current configured/canonical names,
not arbitrary historic prefixes. Full path-bound release belongs to the conductor;
backend-only removal does not infer companion ownership.

Optional package authority uses fixed trusted code on the exact owned container
ID, verifies non-root executor identity and confirms its bounded success receipt.
It grants package-manager permission without installing packages or changing
network policy. See [Package permissions](Component_Package_Permissions.md).

## Timeouts, teardown and limitations

Container exec is always bounded; an omitted/None timeout uses the default command
bound. Nonzero project exit is CommandResult data; runtime/control failures are
typed isolation errors. Interrupt uses a short stop grace and bounded host command.
Verified same-container timeout settlement is described in
[Execution](Component_Execution.md#timeout-recovery).

Removal verifies exact Git common directory, worktree path and branch ownership.
Known transient WSL bind teardown failures get bounded retries; unrelated Git
errors fail immediately. Busy/foreign/corrupt evidence is preserved. Active,
failed and human-owned resources are protected by conductor lifecycle/run locks.

The repository object store is writable inside a container because commits need
it; a malicious executor could damage the local clone. The guard and absence of
injected forge credentials are not a general host-security sandbox. Native jobs
have the server account's permissions. Runtime CPU/RAM restrictions use explicit
run_args; this component does not infer them from observed resource use.

## Dependencies and validation coverage

The implementation uses the injectable command runner, typed configuration,
branding/identity, strict JSON and platform-aware path helpers. Existing offline
coverage includes `04_Software/tests/test_isolation.py`, `test_execution.py`,
`test_drift_recovery.py`, `test_merged_branch_cleanup.py`, `test_container_timeout.py`
and `test_shared_resources.py`. Actual runtime provisioning and host credentials
remain separate operator acceptance work; dated local acceptance receipts are not
part of the component contract.
