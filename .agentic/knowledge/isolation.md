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

## Invariants

- Supports Docker, rootless Podman, and WSL-wrapped runtimes.
- Manages optional open, none, or allowlist-proxy egress resources.
- Mounts the repository, worktree and bounded IO exchange. Explicit configured
  mounts may also provide executor credentials; forge credentials remain on
  the host.
- Cleanup removes only listed names derived from the target executors the
  orchestrator passes and keeps any name also derived from a retained one; it
  never deletes by prefix alone. Proxy and network names are cut to 50 and 48
  characters, so another project's run can share, and lose, such a name.
- Git identity is applied only to ADORE checkpoint commits; it does not
  reconfigure the operator's clone.

## Key behaviors

- `REQ-FUNC-fcb2448b` - isolated container/worktree provisioning and egress modes.
- `REQ-FUNC-42b1c98a` - idempotent, fail-closed Git worktree lifecycle.
- `REQ-FUNC-0ad8ba4f` - WSL runtime mount translation and command prefixing.
- `REQ-FUNC-f9946b6b` - an active executor gate can be interrupted for a
  worker-authorized cancellation.
- `REQ-REL-94e653aa` - guarded ticket-branch pushes verify exact remote
  identity and ancestry; worktree progress is measured between gates.

## Architecture

```mermaid
flowchart LR
    conductor([Orchestrator]) --> worktree[WorktreeManager]
    conductor --> container[ContainerManager]
    worktree --> git[(Host Git clone and worktree)]
    container --> runtime[(Docker, Podman or WSL runtime)]
    runtime --> gate([Executor gate])
```

The worktree and container are per run; the conductor alone decides when to
provision, interrupt or release them.

## Files

- `04_Software/adore/isolation.py`
- `04_Software/tests/test_isolation.py`
- `04_Software/tests/test_checkpoint_handoff.py`
