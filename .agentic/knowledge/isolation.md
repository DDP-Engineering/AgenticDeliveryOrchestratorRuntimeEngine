<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Isolation

## Purpose

Creates one Git worktree and one executor container per run, mounts only the
worktree and bounded IO exchange, and owns lifecycle cleanup.

## Public contract

`WorktreeManager` creates/removes ADORE-owned Git worktrees and
`ContainerManager` creates, executes in, stops, and removes the matching
container through a Docker, Podman, or WSL-wrapped runtime. Runtime commands
are injected for offline testing, and predictable branding names bind resources
to their run.

## Key behaviors

- Supports Docker, rootless Podman, and WSL-wrapped runtimes.
- Manages optional open, none, or allowlist-proxy egress resources.
- Mounts only the worktree and bounded IO exchange; executor credentials and
  host state are outside its container contract.
- Cleanup preserves resources owned by active and failed runs and rejects
  uncertain ownership rather than broad deletion.

## Requirement coverage

- `REQ-FUNC-fcb2448b` - isolated container/worktree provisioning and egress modes.
- `REQ-FUNC-42b1c98a` - idempotent, fail-closed Git worktree lifecycle.
- `REQ-FUNC-0ad8ba4f` - WSL runtime mount translation and command prefixing.

## Files

- `04_Software/adore/isolation.py`
- `04_Software/tests/test_isolation.py`
