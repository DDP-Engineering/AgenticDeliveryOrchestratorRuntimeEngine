<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Isolation

## Routing

Use this page for Git worktrees, host-side checkpoint commits, container
provisioning, egress and cancellation. Start at
`04_Software/adore/isolation.py`; verify with
`04_Software/tests/test_isolation.py`. Run policy belongs to `orchestrator.md`.


`REQ-FUNC-93bd42af`: `remove_remote_branch` validates ref/target and exact published commit, deletes through host Git with an exact remote lease and verifies absence. Missing refs are idempotent success; malformed output, foreign commits and transport failures raise `IsolationError`.

## Purpose and boundaries

Creates one Git worktree and one executor container per run, mounts the
repository, worktree and bounded IO exchange plus explicit configured mounts,
and owns lifecycle cleanup.

## Public interface

`WorktreeManager` creates/removes ADORE-owned Git worktrees and
`ContainerManager` creates, executes in, stops, and removes the matching
container through a Docker, Podman, or WSL-wrapped runtime. Runtime commands
are injected for offline testing, and predictable branding names bind resources
to their run. `WorktreeManager` accepts the configured agent name/email for
host-side checkpoint commits, so a new clone needs no local Git identity.
Progress/checkpoint methods accept optional literal `exclude_paths=()`;
`read_summary(run_id, max_chars=...)` returns a transient SummaryArtifact or
None, and `remove_summary(run_id, artifact)` removes that unchanged artifact
only after the caller has durably retained its sanitized text.
`ContainerManager.spawn(name, argv, env=...)` starts a streaming `exec -i`
command with live binary pipes and exactly `exec`'s environment rules (safe
keys, including Pi's `PI_*` isolation variables, inline; secrets as bare keys
with values only in the client environment); the caller bounds and ends it.

## Invariants

- Supports Docker, rootless Podman, and WSL-wrapped runtimes.
- Applies the `EgressPolicy` it is given (`config.egress_policy`, default
  open): open, none or allowlist-proxy. The per-run squid.conf admits host
  names (exact or `*.`) with a `dstdomain` ACL and IP addresses with a `dst`
  ACL, then `http_access deny all`; the proxy container gets the `--add-host`
  options of `run_args`.
- Mounts the repository, worktree and bounded IO exchange. Explicit configured
  mounts may also provide executor credentials; forge credentials remain on
  the host.
- Every allowlist-proxy run has its own proxy and network name: a long name
  keeps its start and ends in a 10-hex SHA-256 digest of the executor name,
  within 63 characters for the proxy and 48 after the network prefix.
- Cleanup removes only listed per-run names derived from the target executors
  the orchestrator passes and keeps any name also derived from a retained one;
  it never deletes by prefix alone. It does not recognise the old cut proxy and
  network names of earlier ADORE builds; the operator removes those by hand
  (`01_Documentation/Recovery_And_Maintenance.md`).
- Git identity is applied only to ADORE checkpoint commits; it does not
  reconfigure the operator's clone.
- The worktree and container are per run; the conductor alone decides when to
  provision, interrupt or release them.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Native container Git selection or binding recovery | ContainerManager.provision/exec | test_container_git.py |
| Git worktree/checkpoint lifecycle | WorktreeManager | test_isolation.py, test_checkpoint_handoff.py |
| Direct exchange paths and summary safety | worktree_progress_fingerprint, commit_all_if_dirty, read_summary/remove_summary | test_isolation.py exchange/summary/direct_progress cases |
| Runtime, egress and pager transport | ContainerManager | test_isolation.py |

## Key behaviors

- `REQ-FUNC-337d0571`, `REQ-SEC-23063055`: optional direct exclusions use
  top-level literal Git pathspecs for both tracked and untracked progress.
  Checkpoints unstage exchange paths, exclude them from add -A and recheck the
  entire staged set. Exchange-only status is a no-op; empty defaults preserve
  AEGIS behavior. HEAD-owned collisions, escaping/Git paths, linked parents or
  roots, nonregular/multiply linked files and corrupt Git evidence fail typed.
- `REQ-REL-37072309`: summary reads decode the complete stable regular file
  as strict UTF-8, retaining only the positive caller bound. Identity checks
  surround reads/removal; stale or cross-worktree receipts and IO failures
  refuse without authorizing checkpoint. Missing summary is allowed. These
  helpers assume a settled executor boundary, not a concurrent authorized writer.

- `REQ-FUNC-0d0625e1`: fresh repository containers use a read-only native Git pointer, clear inherited repository selectors and transport WSL arguments through direct execution. Independent and nested Git operations select their own repositories.
- `REQ-REL-e1ecfbd5`: exact managed metadata, regular pointer bytes, bounded creation-mode JSON and a runtime discovery acknowledgement are required; corrupt evidence raises IsolationError.
- `REQ-REL-b8c5946a`: warm resources keep their creation-time binding, identity and installed contents; historical containers retain their original environment until normal release.


- REQ-FUNC-c405688e / REQ-SEC-c5d56d9f: authorize_system_packages measures the non-root UID and uses fixed root OS-Python code on a container ID to grant package-manager sudo. No installation or network mutation is performed by ADORE.

- `REQ-REL-d8fd134e`: `resource_identity`/`image_identity` validate authoritative bounded runtime output, actual IDs/name/status and duplicate fields. ContainerBackend verifies owned identity before bound commands and lifecycle controls.

- `REQ-FUNC-fcb2448b` - isolated container/worktree provisioning and egress modes.
- `REQ-SEC-19b768d6` - proxy admits names by domain and addresses by `dst`.
- `REQ-FUNC-67d99144` - the proxy gets the executor's `--add-host` options.
- `REQ-FUNC-42b1c98a` - idempotent, fail-closed Git worktree lifecycle.
- `REQ-FUNC-0ad8ba4f` - WSL runtime mount translation and command prefixing.
- `REQ-FUNC-f9946b6b` - an active executor gate can be interrupted for a
  worker-authorized cancellation.
- `REQ-REL-94e653aa` - guarded ticket-branch pushes verify exact remote
  identity and ancestry; worktree progress is measured between gates.

## Files

- `04_Software/tests/test_container_git.py`: fresh/warm binding and trust-boundary contracts.


- `04_Software/tests/test_system_packages.py`: package authority, independent egress, recovery and reviewed settings contracts.

- `04_Software/adore/isolation.py`
- `04_Software/tests/test_isolation.py`
- `04_Software/tests/test_checkpoint_handoff.py`

## Pager-free executor environment

ContainerManager.exec forces GIT_PAGER/PAGER=cat after caller values and forwards
both inline as non-secret environment. Docker/Podman/WSL commands share the policy;
executor/preparation/model descendants inherit it. Secret bare-key transport,
timeouts and isolation remain unchanged. Focused proof: exec/env and WSL cases
in test_isolation.py. Host runtime commands use the shared background runner.

Interactive Pi RPC spawn shares exec environment filtering: inherited repository selectors are removed, automatic child pager settings apply, secrets travel only through the client environment and Windows clients suppress console allocation.

## Recovery ownership verification

WorktreeManager.verify_removal checks unaliased paths, actual Git common directory, branch and top-level directory before deletion. ContainerManager.release_owned verifies dedicated executor/proxy mounts and actual internal network membership independently of current backend/egress policy; only immutable IDs are removed and absence is verified. remove_remote_branch allow_absent=True permits an empty checkpoint only for an absent ref, never a present branch. Recorded commits always retain exact leases and absence verification. Proof: tests/test_drift_recovery.py and test_merged_branch_cleanup.py.

`fresh_branch` preserves occupied local/remote refs and chooses the base or at most three `-g` twelve-hex alternatives, subject to actual-name policy. Fresh `create(new_branch=True)` refuses an existing path and atomically creates the ref through Git, so a late local ref is never adopted. Existing recovery reattachment remains separate. Proof: tests/test_drift_recovery.py.

## Checkpoint path guard

`REQ-REL-d31b1a6e`: before staging, the shared host checkpoint inspects Git's
untracked non-ignored paths and staged additions (including rename destinations), and rechecks additions after staging.
Literal environment-variable segments and the Windows system cache path stop
with a path-specific `SuspiciousCheckpointPathError`; invalid bounded Git
evidence raises `IsolationError`. The operator inspects preserved files.
Focused offline proof: `tests/test_isolation.py`.


## Concurrent resource ownership

Shared worktree registry operations and checkpoint sequences use a bounded lock
keyed by the resolved Git common directory, including linked-worktree clones.
Remote fetch has a separate key; network publication and executor sessions do not
hold the registry lock. Git config repair respects `config.lock` and atomically
publishes only the unchanged inspected source. Run removal never prunes other
worktree registrations. Production worktree directory names include a stable
project suffix derived from the canonical state root. Invalid/escaping/linked run
paths fail with `IsolationError`. Warm container provisioning verifies repository,
worktree and IO mounts before reuse and starts its immutable ID. `release_owned`
returns exact removed executor/proxy/network names after full path/identity proof.

Focused proof: `04_Software/tests/test_shared_resources.py`. Shared primitive and inventory: `05_SoftwareDocu/Component_Resource_Locks.md`.
