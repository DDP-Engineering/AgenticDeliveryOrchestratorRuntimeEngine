<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Native container Git discovery

Protocol shared by REQ-FUNC-0d0625e1, REQ-REL-e1ecfbd5 and
REQ-REL-b8c5946a.

## Behavior and data

The existing `build_container_env` mapping carries Git mount metadata to the
container manager. Its three selection keys (`GIT_DIR`, `GIT_COMMON_DIR`,
`GIT_WORK_TREE`) are control inputs, filtered from fresh container configuration
and explicit exec environment. Author/committer identity and pager settings
retain their existing meanings.

For a repository job, a fresh container receives a read-only file mount at
`/adore/work/.git`. Its source is the run IO directory's `container.git` file,
containing exactly `gitdir: /adore/repo/.git/worktrees/<admin-name>\n` in UTF-8.
This pure Git data format cannot carry a license comment. The actual host
worktree pointer remains untouched. Git follows its ordinary directory discovery
and the existing relative `commondir` in the mounted administration directory.
Probes without Git metadata receive their existing mounts and behavior.

The admin name is one nonempty filesystem component, excluding dot/dot-dot,
slash, backslash and control characters. GIT_DIR must have the exact managed
prefix; supplied common/worktree paths must agree with their fixed mounts.
Incomplete or invalid metadata raises IsolationError before container creation.
Existing pointer files must be regular, non-symlink files with exact expected
bytes; creation is exclusive and idempotent. Corrupt files are preserved for
diagnosis and rejected rather than overwritten.

Fresh repository containers are labelled
`io.ddp.adore.git-binding=pointer-v1`. They explicitly clear the three selection
variables from image defaults and sanitized runtime environment: Docker uses
bare unset `--env` keys, standard Podman commands use `--unsetenv` keys.
An in-container fixed shell check confirms all three variables are absent;
success has the exact acknowledgement `adore-git-binding-v1`. The check also confirms native main Git directory and worktree discovery. Any failed, timed-out or
contradictory receipt raises IsolationError. Environment output and secrets are
never printed by that check.

## Recovery and compatibility

An existing repository container's selected label is read through a bounded
JSON-formatted runtime inspect. Empty/null means the historical binding mode;
`pointer-v1` requires intact expected pointer evidence and successful environment
confirmation before reuse. Unknown types/values and runtime failure are typed
errors. Existing resources are started or retained with their original mounts,
identity and filesystem; provision never replaces them to retrofit a mount.

Historical containers therefore retain historical Git environment behavior until
normal resource release. The operator guide explicitly states this rollout
limit. The active issue implementation continues in its pinned resource. Fresh
containers use native discovery without a new profile option or image rebuild.

## Verification

Offline tests call public provision/exec surfaces with injected runners and
temporary filesystem fixtures. They inspect the read-only pointer mount,
unforwarded selection metadata, sanitized process environment, Docker/Podman/WSL
argument transport, unchanged egress, creation/reuse ordering and typed failures.
Negative cases cover path traversal/control input, wrong expected mounts,
nonregular/symlink/mismatched pointer files, malformed/oversized/failed label
receipts, missing new-mode evidence and failed environment acknowledgements.

Controlled live Docker acceptance uses temporary independent source and linked
worktree repositories: ordinary Git in the main worktree succeeds, temporary
and nested repositories receive their own commits, and original main HEAD,
index and host Git pointer remain unchanged. This is operator-authorized manual
acceptance, never a real CLI call from unit tests.

## Evidence supporting the design

A local Docker image with all three wrong image-default selection variables
retained them normally; bare unset arguments with a sanitized runtime process
removed all three. The temporary probe image was removed. The current owned
legacy container's selected label formats as the JSON empty string.
Docker's CLI documents bare-key unset semantics; Podman documents explicit
unsetenv. Live Podman acceptance is unavailable on this host and is not claimed.

- [Docker run environment](https://docs.docker.com/reference/cli/docker/container/run/)
- [Podman run](https://docs.podman.io/en/stable/markdown/podman-run.1.html)


## WSL transport

Standard WSL runtime prefixes use `--exec` internally, preserving an explicit
`--exec` or `-e`. A configured `--` boundary becomes direct execution; a standard
Docker/Podman command without that boundary receives one. A custom WSL wrapper
requires an explicit command boundary and otherwise raises ValueError before
runtime commands. This preserves literal shell expressions and path data across
the Windows/WSL process boundary.

WSL launch options are consumed with their operands before locating the command.
Distribution, user and directory values are preserved as data even when named
like a container executable. Only the selected command determines the standard
Docker/Podman dialect; wrapper arguments cannot override the WSL boundary.
Incomplete or unsupported WSL launch options raise ValueError before execution.
