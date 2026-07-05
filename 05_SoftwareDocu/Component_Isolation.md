<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Isolation (`ador/isolation.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/isolation.py` - file version 0.2.0.
> Design: Orchestrator_Design_And_Decisions.md sections 8b, 10, 10a.
> Image: `04_Software/docker/Dockerfile.executor` (see `docker/README.md`).

## 1. Purpose

The two isolation layers every run gets, both keyed by the stable run-id: a
**git worktree** (code isolation - one folder and branch per ticket, sharing
the local clone's object store) mounted into a **container** (execution
isolation - the real sandbox bounding what the executor can touch). Isolation
is mandatory once the human leaves the loop; the workflow's hooks are
guardrails, not a sandbox (design 10).

## 2. Responsibilities

- `WorktreeManager(repo_path, root)` - worktree lifecycle on the host:
  idempotent `create` (reuse -> re-attach branch -> create fresh from
  base_ref), idempotent `remove` (+ prune, optional branch delete), `fetch`,
  `admin_dir_name` (reads the worktree's `.git` pointer file),
  `changed_files` (committed + pending paths vs the base ref; feeds the
  max_files_touched budget), the delivery git plumbing - `merge` (conflict =
  data, left in progress for the executor), `merge_in_progress`, and `push`
  (the ONLY remote-writing git call in ADOR) - plus the committed-state
  checks `is_dirty` / `commits_ahead`, and `list_dirs` (every directory
  under the worktrees root, including husks deregistered but not deleted
  after the WSL bind-mount teardown race - the input `ador cleanup` sweeps).
- `ContainerManager(runtime, image, uv_cache_volume, npm_cache_volume,
  run_args=...)` -
  container lifecycle: `ensure_volumes`, idempotent `provision`
  (running -> no-op, stopped -> start, absent -> create), `start` / `stop`
  (park) / `remove` (reap), `status`, `list_containers(prefix)` (all
  containers in any state whose name starts with `<slug>-run-`; feeds
  `ador cleanup`'s orphan sweep), and `exec` (the seam the executor
  launcher runs commands through).
- `build_container_env(git_dir_name, git_name, git_email)` - the git
  environment injected at provision (see section 3).
- `IsolationError` - typed fail-closed error carrying argv + stderr.

Explicitly not owned: *when* to park/reap/resume (orchestrator policy, TTL
per design 8b), what runs inside the container (executor launcher), and any
remote git operation (push stays with the orchestrator on the host).

## 3. Implementation Overview

**The worktree-in-container problem and its solution.** A git worktree's
`.git` is a pointer *file* containing an absolute host path into the main
repo's `.git/worktrees/<id>` - meaningless inside the container. Instead of
rewriting pointer files or mirroring host layouts, the repo clone and the
worktree are mounted at fixed container paths (`/ador/repo`, `/ador/work`)
and git inside the container is directed by environment:
`GIT_DIR=/ador/repo/.git/worktrees/<admin-name>` and
`GIT_WORK_TREE=/ador/work`. Path discovery is bypassed entirely; the host
side keeps working normally with its absolute paths. The admin dir name is
*read* from the pointer file (git suffixes it on collision), never assumed.

- One long-lived container per run (`<slug>-run-<run-id>`), idling on
  `sleep infinity`; gates are launched into it via `exec`. Park = `stop`
  (filesystem and resolved dependencies kept, fast resume); reap = `rm -f`
  (worktree and `.ador` state always survive). `provision` returns what it
  did - "running" / "started" / "created" - so callers know when
  container-internal state (executor sessions) was lost (live finding
  2026-07-04).
- **Secrets never appear in argv:** `provision` passes env keys as bare
  `--env KEY` and the values travel via the runtime CLI's own process
  environment, so `docker run` command lines (process listings, journals)
  never contain a key.
- **Wrapped runtimes / Docker-in-WSL2:** `[container] runtime` may be a full
  command (e.g. `"wsl -d Ubuntu-24.04 -- docker"` when Docker Engine runs
  inside WSL2 without Docker Desktop). WSL mode is auto-detected from the
  first token and switches on two boundary fixes: mount sources are
  translated to the WSL view (`D:\x` -> `/mnt/d/x`, via `wsl_mount_path`),
  and the container env keys are listed in `WSLENV` so their Windows-side
  values actually cross into the WSL process (wsl.exe forwards no other env
  vars).
- `exec` returns the `CommandResult` as **data** - a failing gate command is
  a conductor signal, not an isolation failure. Only runtime-level failures
  (daemon down, image missing) raise `IsolationError`.
- Windows host paths are normalized (`Path.as_posix()`) for mount syntax.
- Commit authorship comes from `agent.name` / `agent.email` via
  `GIT_AUTHOR_*` / `GIT_COMMITTER_*` (setup doc section 4).

## 4. Dependencies

- Internal: `ador.util` (`CommandRunner`, `CommandResult`, `run_command`);
  values from `[worktree]` (`repo_path`, `root`) and `[container]`
  (`runtime`, `image`, cache volumes) config.
- External: `git` on the host; Docker or Podman - native or wrapped (Docker
  Engine inside WSL2 via `wsl -d <distro> -- docker`); the
  `ador-executor:latest` image (built from `docker/Dockerfile.executor`:
  Ubuntu 22.04, Python 3.11 + uv, Node 20, git with `safe.directory *`,
  opencode, glab/gh, non-root user `ador`).

## 5. Inputs And Outputs

- Inputs: run-id, branch and base ref, container name, the env mapping
  (git env + the executor's secret subset).
- Outputs: a worktree directory under `<root>/<run-id>`, a provisioned
  container, container state strings, and `CommandResult`s from `exec`.

## 6. Data Contracts

- Container mount contract (fixed constants, mirrored by the Dockerfile):
  repo -> `/ador/repo`, worktree -> `/ador/work` (working dir), the run's io
  exchange dir (`.ador/runs/<run-id>/io`) -> `/ador/io` (gate scripts in,
  event streams out; outside the worktree so the executor can never commit
  them), uv cache volume -> `/home/ador/.cache/uv`, npm cache volume ->
  `/home/ador/.npm`.
- `status()` returns the runtime's state string (`running`, `exited`,
  `created`, ...) or `"absent"`; "no such container/object" is absence, any
  other failure raises.
- Project dependencies resolve into the cache volumes / container paths,
  never into the bind-mounted worktree (cross-OS `.venv` breakage,
  design 10a).

## 7. Workflow Integration

The orchestrator (phase 3) calls this at run start (fetch, create worktree,
ensure volumes, provision container), on park (stop), on TTL expiry (reap =
stop + remove), on resume (provision = start or recreate; the durable
worktree + state make recreation seamless), and at terminal states (remove
container, remove worktree, optionally delete the branch). The executor
launcher (phase 2, next) runs the executor through `exec`.

## 8. Usage

```python
from ador.isolation import (
    ContainerManager, WorktreeManager, build_container_env,
)

worktrees = WorktreeManager("../cockpit-gcp", "worktrees")
containers = ContainerManager("docker", "ador-executor:latest",
                              "ador-uv-cache", "ador-npm-cache")

path = worktrees.create("gitlab-x-14", "ador/gitlab-x-14", "origin/develop")
env = build_container_env(worktrees.admin_dir_name("gitlab-x-14"),
                          "ADOR", "ador-bot@local")
env["ANTHROPIC_API_KEY"] = "..."          # executor's secret subset only
containers.ensure_volumes()
containers.provision("ador-run-gitlab-x-14", "../cockpit-gcp", path, env)
result = containers.exec("ador-run-gitlab-x-14", ["opencode", "--version"])
```

## 9. Validation And Tests

- `tests/test_isolation.py` (fake runner, fully offline): worktree create
  for new branch / branch re-attach / idempotent reuse, git failure ->
  `IsolationError`, idempotent remove + branch delete, admin-name read from
  the pointer (including collision suffix) and its fail-closed negatives;
  container env contract, provision when absent (mounts, workdir, bare
  `--env KEY`, secret value absent from argv but present in process env),
  provision idempotency, absent-vs-error status, idempotent-but-fail-closed
  stop/remove, volume creation, and exec-returns-data.
- Minimum validation after a change: `uv run --group dev pytest tests/test_isolation.py`.
- `docker/verify-runtime.sh` is the LIVE compatibility pass for a runtime:
  17 steps mirroring every runtime CLI call this component makes (mount/env
  shape, bare-key secrets, HOME inline, tool usability, in-container git
  with host-visible commits, park/resume, listing, reap, absence). Docker
  baseline green 2026-07-04 (17/17); run with `RUNTIME=podman` before
  pointing config at podman.
- **Live verification done 2026-07-03** (Docker Engine in WSL2, scratch repo,
  19/19 steps; Prerequisites_Check_Report.md section 12): image build and
  tooling checks, WSLENV secret propagation, git status/commit **inside** the
  container via the GIT_DIR/GIT_WORK_TREE model with the commit visible on
  the host under bot authorship, park -> resume with state intact, full
  teardown.

## 10. Limitations And Future Work

- The repo clone is mounted read-write into the executor container (commits
  need the shared object store). The executor cannot push (no credentials in
  the container; opencode denies push), but a misbehaving executor could
  damage the *local* clone - acceptable for v1 since the clone is
  disposable; re-clone recovers it.
- With `GIT_DIR` set container-wide, git inside the container always targets
  the run's repo regardless of cwd - harmless for the single-worktree
  executor, but surprising if a run ever needed a second repo.
- CPU/RAM/network limits (`--memory`, `--cpus`, `--network`) are not yet
  passed to `docker run`; add as `[container]` keys when the budgets phase
  lands.
- Podman VERIFIED 2026-07-04 (4.9.3 rootless, Ubuntu-24.04/WSL2): 17/17 on
  `docker/verify-runtime.sh`. Rootless mode requires
  `[container] run_args = ["--userns=keep-id"]` (without it, container uid
  1000 cannot write the bind-mounted worktree - caught live by the pass).
  Remaining: a disposable-ticket pilot with `runtime = "podman"`; SELinux
  hosts (Fedora/RHEL) may additionally need `:z`/`:Z` mount labels.
- With a WSL-wrapped runtime, `wsl.exe` re-joins arguments before the WSL
  shell re-parses them, so argv elements containing spaces can be split. The
  executor launcher must pass prompts through a file, never through argv
  (planned anyway for output capture).
