<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Isolation (`adore/isolation.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/isolation.py`.
> Design context: `00_Planning/ADORE_System_Overview.md`.
> Images: `04_Software/docker/Dockerfile.executor-base`,
> `04_Software/docker/Dockerfile.egress-proxy`, plus runtime-project images
> such as `Dockerfile.executor-project`
> (see `docker/README.md`).

## 1. Purpose

The two isolation layers every run gets, both keyed by the stable run-id: a
**git worktree** (code isolation - one folder and branch per ticket, sharing
the local clone's object store) mounted into a **container** (execution
isolation - the real sandbox bounding what the executor can touch). Isolation
is mandatory once the human leaves the loop; the workflow's hooks are
guardrails, not a sandbox (design 10).

## 2. Responsibilities

- `WorktreeManager(repo_path, root, runner=..., sleep=...)` - worktree
  lifecycle on the host: idempotent `create` (reuse -> re-attach branch ->
  create fresh from base_ref), idempotent `remove` (+ prune, optional branch
  delete; retries past the WSL2 teardown race, see section 3), `fetch`,
  `admin_dir_name` (reads the worktree's `.git` pointer file),
  `changed_files` (committed + pending paths vs the base ref; feeds the
  max_files_touched budget; a rename counts as ONE file - its destination - and
  git's path quoting is stripped), the delivery git plumbing - `merge` (conflict =
  data, left in progress for the executor), `merge_in_progress`, and `push`
  (the ONLY remote-writing git call in ADORE) - `commit_all_if_dirty` for
  conductor-generated stage/delivery artifacts, plus the committed-state checks
  `is_dirty`; `ref_head`, `commit_series`, and
  `candidate_fingerprint` bind approval to the target, tree and exact commit
  sequence; `product_diff_fingerprint` detects product mutation while allowing
  expected `.agentic/` delivery bookkeeping; and `list_dirs` (every directory under the
  worktrees root, including husks deregistered but not deleted after the WSL
  bind-mount teardown race - the input `adore cleanup` sweeps).
- `ContainerManager(runtime, image, uv_cache_volume, npm_cache_volume,
  run_args=..., egress=...)` -
  container lifecycle: `ensure_volumes`, idempotent `provision`
  (running -> no-op, stopped -> start, absent -> create), `start` / `stop`
  (park) / `remove` (reap), `status`, `list_containers(prefix)` (all
  containers in any state whose name starts with `<slug>-run-`; feeds
  `adore cleanup`'s orphan sweep), `list_egress_networks(prefix)`,
  `remove_egress(name)`, the best-effort `cleanup_orphan_containers`,
  `cleanup_egress_proxies`, and `cleanup_egress_networks` methods,
  `verify_required_tools` (project-image checks run inside the provisioned
  container), and `exec` (the seam the executor launcher runs commands through).
- `build_container_env(git_dir_name, git_name, git_email)` - the git
  environment injected at provision (see section 3).
- `IsolationError` - typed fail-closed error carrying argv + stderr.

Explicitly not owned: *when* to park/reap/resume (orchestrator lifecycle
policy), what runs inside the container (executor launcher), and any remote git
operation (push stays with the orchestrator on the host).

## 3. Implementation Overview

**The worktree-in-container problem and its solution.** A git worktree's
`.git` is a pointer *file* containing an absolute host path into the main
repo's `.git/worktrees/<id>` - meaningless inside the container. Instead of
rewriting pointer files or mirroring host layouts, the repo clone and the
worktree are mounted at fixed container paths (`/adore/repo`, `/adore/work`)
and git inside the container is directed by environment:
`GIT_DIR=/adore/repo/.git/worktrees/<admin-name>` and
`GIT_WORK_TREE=/adore/work`. Path discovery is bypassed entirely; the host
side keeps working normally with its absolute paths. The admin dir name is
*read* from the pointer file (git suffixes it on collision), never assumed.

- **`WorktreeManager.remove` retries past the WSL2 bind-mount teardown
  race** (ADORE-ARCH-009): `docker/podman rm` returns before the kernel
  releases the container's 9P/drvfs bind mount on the worktree, so an
  immediate `git worktree remove` can fail with ENOSYS/EBUSY/ENOTEMPTY until
  the mount clears (a few seconds). `remove` retries the whole operation with
  backoff (`1s, 2s, 4s`, ~7s ceiling) ONLY on those transient signatures - a
  real git error is raised on the first attempt, never masked. If the race
  still hasn't cleared after every retry, `remove` re-raises and the caller
  (the orchestrator's `_teardown`) logs a husk message for `adore cleanup` to
  sweep later. Native docker/Linux succeeds on the first try (no sleeps).
  This handling moved here from the orchestrator's core loop, which is not
  the place for platform-specific glue (`AGENTS.md` section "Repository
  Rules").
- One long-lived container per run (`<slug>-run-<run-id>`), idling on
  `sleep infinity`; gates are launched into it via `exec`. Park = `stop`
  (filesystem and resolved dependencies kept, fast resume); reap = `rm -f`
  (worktree and `.adore` state always survive). `provision` returns what it
  did - "running" / "started" / "created" - so callers know when
  container-internal state (executor sessions) was lost (live finding
  2026-07-04).
- **Secrets never appear in argv:** `provision` passes env keys as bare
  `--env KEY` and the values travel via the runtime CLI's own process
  environment, so `docker run` command lines (process listings, journals)
  never contain a key.
- **Safe runtime values go inline:** ADORE-managed Git/Home/Codex variables
  plus common uv runtime controls (`UV_LINK_MODE`, `UV_CACHE_DIR`,
  `UV_PROJECT_ENVIRONMENT`) are non-secret and are passed as
  `--env KEY=value`. This keeps wrapped Docker/Podman runtimes from dropping
  them between create-time and exec-time launches. Other configured env still
  uses the bare-key path.
- **Wrapped runtimes / Docker-in-WSL2:** `[container] runtime` may be a full
  command (e.g. `"wsl -d Ubuntu-24.04 -- docker"` when Docker Engine runs
  inside WSL2 without Docker Desktop). WSL mode is auto-detected from the
  first token and switches on two boundary fixes: mount sources are
  translated to the WSL view (`D:\x` -> `/mnt/d/x`, via `wsl_mount_path`),
  and the container env keys are listed in `WSLENV` so their Windows-side
  values actually cross into the WSL process (wsl.exe forwards no other env
  vars). `wsl_mount_path` normalizes Windows separators explicitly instead of
  relying on the current host's `Path` flavour, so the same Windows path
  contract is testable and stable on both Windows and Linux. WSL mount-source
  construction recognizes an absolute Windows drive path before asking the
  current host to resolve it; a Linux test host therefore cannot accidentally
  prefix its own working directory to `D:\...`.
- `exec` returns the `CommandResult` as **data** - a failing gate command is
  a conductor signal, not an isolation failure. Only runtime-level failures
  (daemon down, image missing) raise `IsolationError`.
- **`exec` is always bounded.** Its `timeout` defaults to
  `util.DEFAULT_COMMAND_TIMEOUT` (600 s) and an explicitly passed `None`
  resolves to that same default - at this seam `None` means "use the default
  bound", never "no bound". `run_command`'s own default applies only when a
  caller omits the keyword, so forwarding a `None` would reach
  `subprocess.run(timeout=None)`: a wedged container runtime or an
  interactive `required_tool_checks` command would then block `_provision`,
  and with it the single-threaded poll loop, forever. Callers needing more
  room pass their own budget (an executor gate launch passes
  `[budgets] per_gate_timeout_seconds` or its `[workflow]` stage override).
- **Executor egress:** `[container.egress] mode = "open"` provides unrestricted
  network access. `none` adds `--network none`. `allowlist-proxy` creates an
  internal per-run network, starts a per-run proxy container from
  `Dockerfile.egress-proxy`, connects it to that network as
  `adore-egress-proxy`, starts the executor only on the internal network, and
  injects uppercase/lowercase proxy environment variables at provision and
  exec time. Squid writes inside its owned `/var/log/squid` directory so it
  can start after dropping privileges to the `proxy` user.
- Windows host paths are normalized (`Path.as_posix()`) for mount syntax.
- Commit authorship comes from `agent.name` / `agent.email` via
  `GIT_AUTHOR_*` / `GIT_COMMITTER_*`; credential and host-auth boundaries are
  documented in `01_Documentation/Security_And_Credentials.md`.

## 4. Dependencies

- Internal: `adore.util` (`CommandRunner`, `CommandResult`, `run_command`);
  values from `[worktree]` (`repo_path`, `root`) and `[container]`
  (`runtime`, `image`, cache volumes, `egress`) config.
- External: `git` on the host; Docker or Podman - native or wrapped (Docker
  Engine inside WSL2 via `wsl -d <distro> -- docker`); the
  `adore-executor-base:1.0.0` image (built from
  `docker/Dockerfile.executor-base`: Ubuntu 22.04, Python 3.11 + uv, Node
  24, git with `safe.directory *`, opencode/pi/codex/qwen CLIs as configured,
  glab/gh, non-root user `adore`) or a runtime-project image derived from it.

## 5. Inputs And Outputs

- Inputs: run-id, branch and base ref, container name, the env mapping
  (git env + `[container] runtime_env` + executor-specific runtime env + the
  executor's secret subset).
- Outputs: a worktree directory under `<root>/<run-id>`, a provisioned
  container, container state strings, and `CommandResult`s from `exec`.

## 6. Data Contracts

- Container mount contract (fixed constants, mirrored by the Dockerfile):
  repo -> `/adore/repo`, worktree -> `/adore/work` (working dir), the run's io
  exchange dir (`.adore/runs/<run-id>/io`) -> `/adore/io` (gate scripts in,
  event streams out; outside the worktree so the executor can never commit
  them), uv cache volume -> `/home/adore/.cache/uv`, npm cache volume ->
  `/home/adore/.npm`.
- Git env contract inside the container: `GIT_DIR` points at the mounted
  linked-worktree admin dir, `GIT_COMMON_DIR` at `/adore/repo/.git`, and
  `GIT_WORK_TREE` at `/adore/work`. This keeps Git usable even though the
  worktree's `.git` pointer file contains a host path.
- `status()` returns the runtime's state string (`running`, `exited`,
  `created`, ...) or `"absent"`; "no such container/object" is absence, any
  other failure raises.
- Project package caches resolve into the cache volumes / container paths.
  The default `UV_LINK_MODE=copy` avoids fragile cross-OS hard-link behavior;
  repos that need to move uv virtualenvs out of the worktree can set a
  project-specific non-secret `UV_PROJECT_ENVIRONMENT` in `[container]
  runtime_env`.
- `[container] required_tool_checks` is a list of shell-free command strings
  run inside the provisioned container. Failure raises `IsolationError`, so a
  profile with the wrong runtime-project image fails before any executor gate
  starts.
- `[container.egress] allowlist-proxy` writes generated Squid config under the
  run IO directory, uses one proxy container named
  `<executor-container>-egress-proxy`, and one network named
  `<network_prefix>-<safe-executor-container-name>`. Cleanup removes executor,
  proxy container, and network; `adore cleanup` also sweeps exact-prefix orphan
  executors, proxies, and networks while retaining companions computed from
  active and failed persisted container names. The network sweep checks the
  canonical `adore-egress` prefix even after the current profile changes mode,
  plus the current configured prefix; it never guesses arbitrary historical
  names.

## 7. Workflow Integration

The orchestrator (phase 3) calls this at run start (fetch, create worktree,
ensure volumes, provision container), on park (stop and retain), on resume
(provision = start or recreate; the durable worktree + state make recreation
seamless), and at explicit cleanup or completed terminal boundaries (remove
container, remove worktree, optionally delete the branch). The executor
launcher (phase 2, next) runs the executor through `exec`.

## 8. Usage

```python
from adore.isolation import (
    ContainerManager, WorktreeManager, build_container_env,
)

worktrees = WorktreeManager("../project", "worktrees")
containers = ContainerManager("docker", "adore-executor-base:1.0.0",
                              "adore-uv-cache", "adore-npm-cache")

path = worktrees.create("gitlab-x-14", "adore/gitlab-x-14", "origin/develop")
env = build_container_env(worktrees.admin_dir_name("gitlab-x-14"),
                          "ADORE", "adore-bot@local")
env["UV_LINK_MODE"] = "copy"              # non-secret runtime behavior
env["ANTHROPIC_API_KEY"] = "..."          # executor's secret subset only
containers.ensure_volumes()
containers.provision("adore-run-gitlab-x-14", "../project", path, env)
result = containers.exec("adore-run-gitlab-x-14", ["opencode", "--version"])
```

## 9. Validation And Tests

- `tests/test_isolation.py` (fake runner, fully offline): worktree create
  for new branch / branch re-attach / idempotent reuse, git failure ->
  `IsolationError`, idempotent remove + branch delete, admin-name read from
  the pointer (including collision suffix) and its fail-closed negatives;
  the WSL teardown-race retry (transient ENOSYS signature retried with
  backoff to success) and its negative (a real error raised on the first
  attempt, never retried);
  container env contract, provision when absent (mounts, workdir, bare
  `--env KEY`, secret value absent from argv but present in process env),
  provision idempotency, absent-vs-error status, idempotent-but-fail-closed
  stop/remove, volume creation, and exec-returns-data; Windows drive-path
  translation and wrapped-runtime mount construction on both host OSes.
- `tests/test_orchestrator.py` covers the delivery integration case where
  conductor-owned task/report commands generate final workflow artifacts,
  fingerprint approval and commit them before push.
- Minimum validation after a change: `uv run --group dev pytest tests/test_isolation.py`.
- `docker/verify-runtime.sh` is the LIVE compatibility pass for a runtime. Its
  open-egress path covers 17 steps and its allowlist-proxy path covers 21,
  mirroring every runtime CLI call this component makes: mount/env shape,
  bare-key secrets, HOME inline, executor-base tool usability, proxy allow and
  deny behavior, optional runtime-project tool checks, in-container git with
  host-visible commits, park/resume, listing, reap, and absence. The ADORE
  1.0.0 images passed Docker open mode (17/17), Docker allowlist-proxy mode
  (21/21), and rootless Podman open mode (17/17) on 2026-07-16.
- **Live verification done 2026-07-03** (Docker Engine in WSL2, scratch repo,
  19/19 steps): image build and
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
- Container-runtime limits can be supplied through `[container] run_args`, for
  example `--memory=2g` or `--cpus=2`. Egress networking is separately owned
  by `[container.egress]`; dedicated first-class CPU/RAM configuration keys are
  not implemented.
- Docker UID/GID mapping: the executor base image is built with
  `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)` so the
  container's `adore` user and group match the host account. Without this, files
  written to bind-mounted volumes (worktree, IO, caches) are owned by the wrong
  UID/GID on the host and the host service cannot read/write the shared per-run
  directories. The Dockerfile defaults to `USER_UID=1000`/`USER_GID=1000`; pass
  the host user's UID and GID at build time.
- Podman VERIFIED 2026-07-04 (4.9.3 rootless, Ubuntu-24.04/WSL2), re-verified
  2026-07-06 with a runtime-project image plus required tool checks, and
  re-verified for the ADORE 1.0.0 executor image on 2026-07-16 (17/17).
  Rootless mode requires
  `[container] run_args = ["--userns=keep-id"]` (without it, container uid
  1000 cannot write the bind-mounted worktree - caught live by the pass).
  Podman maps the container UID to the host UID at runtime; no image rebuild
  needed. Remaining: a disposable-ticket pilot with `runtime = "podman"`;
  SELinux hosts (Fedora/RHEL) may additionally need `:z`/`:Z` mount labels.
- With a WSL-wrapped runtime, `wsl.exe` re-joins arguments before the WSL
  shell re-parses them, so argv elements containing spaces can be split. The
  executor launcher must pass prompts through a file, never through argv
  (planned anyway for output capture).
