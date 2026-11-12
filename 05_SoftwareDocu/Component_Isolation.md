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

The two isolation layers for container-backed runs, both keyed by the stable run-id: a
**git worktree** (code isolation - one folder and branch per ticket, sharing
the local clone's object store) mounted into a **container** (execution
isolation - the real sandbox bounding what the executor can touch). Isolation
is mandatory once the human leaves the loop; the workflow's hooks are
guardrails, not a sandbox.


`WorktreeManager.remove_remote_branch(branch, expected, target)` uses host Git authentication to delete one exact merged run ref with `--force-with-lease`. It rejects the target branch, malformed identities and a changed remote commit through `IsolationError`, verifies remote absence after pushing, and treats an already absent ref as success. By default an empty or malformed published commit is refused like a changed one; arbitrary remote output is rejected.

## 2. Responsibilities

- `WorktreeManager(repo_path, root, runner=..., sleep=...,
  git_name=..., git_email=...)` - worktree
  lifecycle on the host: idempotent `create` (reuse -> re-attach branch ->
  create fresh from base_ref), idempotent `remove` (+ prune, optional branch
  delete; retries past the WSL2 teardown race, see section 3), `fetch`,
  `admin_dir_name` (reads the worktree's `.git` pointer file),
  `changed_files` (committed + pending paths vs the base ref; feeds the
  max_files_touched budget; a rename counts as ONE file - its destination - and
  git's path quoting is stripped), the delivery git plumbing - `merge` (conflict =
  data, left in progress for the executor), `merge_in_progress`, `push`
  (approved review delivery), and `push_checkpoint` (configurable guarded WIP branch
  publication) - `commit_all_if_dirty` for
  conductor-generated stage/delivery artifacts with the configured agent's
  host-side Git identity, plus the committed-state checks
  `is_dirty`; `ref_head`, `commit_series`, and
  `candidate_fingerprint` bind approval to the target, tree and exact commit
  sequence; `worktree_progress_fingerprint` detects source progress across an
  executor gate; and `list_dirs` (every directory under the
  worktrees root, including husks deregistered but not deleted after the WSL
  bind-mount teardown race - which `adore cleanup` reads to find the project's
  state-less run IDs).
- `ContainerManager(runtime, image, uv_cache_volume, npm_cache_volume,
  run_args=..., egress=..., selinux_relabel=..., pull_never=...)` -
  container lifecycle: `ensure_volumes`, idempotent `provision`
  (running -> no-op, stopped -> start, absent -> create), `start` / `stop`
  (park) / `interrupt` (bounded cancellation stop) / `remove` (reap),
  `status`, `list_containers(prefix)` (all
  containers in any state whose name starts with `<slug>-run-`),
  `list_executors(prefix)` (the same without egress proxy containers; `adore
  cleanup` reads it to find the project's run IDs and the executors still
  using a proxy or network), `list_egress_networks(prefix)`,
  `remove_egress(name)`, the best-effort
  `cleanup_orphan_containers(prefix, targets, retained)`,
  `cleanup_egress_proxies(targets, retained)` (lists proxies by their
  `-egress-proxy` suffix), and `cleanup_egress_networks(targets, retained)`
  methods (each removes only listed current per-run names derived from the
  `targets` executor names and not from `retained`),
  `verify_required_tools` (project-image checks run inside the provisioned
  container), and `exec` (the seam the executor launcher runs commands through).
- `build_container_env(git_dir_name, git_name, git_email)` supplies managed Git
  binding metadata and author/committer identity to provision (see section 3).
- `IsolationError` - typed fail-closed error carrying argv + stderr.

`pull_never=True` adds `--pull=never` to executor and allowlist-proxy container
creation. The web readiness check and the explicit AI connection test use it
after local image inspection so an explicit check cannot fetch images at
first use. The default keeps
the conductor's existing image policy.

`interrupt(name)` uses a two-second runtime stop grace with a 20-second host
command bound. It targets the exact run container and raises `IsolationError`
on a real runtime failure; the conductor still owns final state and teardown.
An Ubuntu Docker-in-WSL acceptance probe stopped a running `docker exec sleep`
in 2.24 seconds through this method; the executor exited nonzero.

`push_checkpoint()` validates the exact local and remote ticket ref, verifies
ancestry, and uses a compare-and-update lease. A foreign branch or rejected
lease raises a typed conflict; malformed Git output raises a protocol error.
It never pushes the target branch or opens an MR/PR.

Explicitly not owned: *when* to park/reap/resume (orchestrator lifecycle
policy), what runs inside the container (executor launcher), and any remote git
operation (push stays with the orchestrator on the host).

## 3. Implementation Overview

**Native Git discovery.** The host worktree keeps its original `.git` pointer.
Fresh repository containers mount a generated run-IO `container.git` file
read-only at `/adore/work/.git`; it points to the existing mounted linked-worktree
administration directory under `/adore/repo/.git/worktrees/`. Native Git then
honors the current directory, `-C`, nested repositories and temporary repositories.
The three `GIT_DIR`/`GIT_COMMON_DIR`/`GIT_WORK_TREE` mapping fields are provisioning
metadata, filtered from fresh container and explicit exec environments. Image
and runtime defaults for these selectors are cleared at creation. Git author,
committer, pager and other runtime settings retain their normal scope.

The generated pointer is admitted as bounded exact regular-file data; links,
foreign paths, control characters, wrong mount metadata and corrupt saved files
raise `IsolationError`. The data file is outside the candidate worktree, and its
Git format cannot include a license comment. Provision confirms actual selector
absence, pointer contents and native worktree discovery with an exact bounded
runtime receipt. It raises a typed error when confirmation fails.

Creation label `io.ddp.adore.git-binding=pointer-v1` identifies this mode. Warm
provision reads bounded selected-label JSON, checks saved evidence and confirms
runtime behavior before reuse. Empty/null labels identify historical containers,
which retain their original binding and filesystem. Unknown labels fail closed.
The component preserves container identity and installed dependencies rather than
replacing resources to change a mount.

- **`WorktreeManager.remove` retries past the WSL2 bind-mount teardown
  race**: `docker/podman rm` returns before the kernel
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
- **Safe runtime values go inline:** ADORE-managed Git/Home/Pi variables
  (`PI_CODING_AGENT_DIR`, `PI_OFFLINE`, `PI_TELEMETRY`,
  `PI_SKIP_VERSION_CHECK`), proxy variables and common uv runtime controls (`UV_LINK_MODE`, `UV_CACHE_DIR`,
  `UV_PROJECT_ENVIRONMENT`) are non-secret and are passed as
  `--env KEY=value`. This keeps wrapped Docker/Podman runtimes from dropping
  them between create-time and exec-time launches. Other configured env still
  uses the bare-key path.
- **Wrapped runtimes / Docker-in-WSL2:** `[container] runtime` may be a full
  command (e.g. `"wsl -d Ubuntu-24.04 -- docker"` when Docker Engine runs
  inside WSL2 without Docker Desktop). WSL mode is auto-detected from the
  first token. Standard prefixes normalize to WSL `--exec` so argument data
  reaches the command directly. Launch options and their operands are parsed
  before the command; only that command selects the Docker/Podman dialect.
  Incomplete or unsupported launch options fail before runtime calls. Custom wrappers use an explicit `--` or
  `--exec` boundary. Mount sources are
  translated to the WSL view (`D:\x` -> `/mnt/d/x`, via `wsl_mount_path`),
  and secret container env keys are listed in `WSLENV` so their Windows-side
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
- **Executor egress:** the `egress` argument is the `EgressPolicy` that
  `config.egress_policy` derives from `[executor] internet`; this component
  does not read the switch. Mode `open` (internet on) provides unrestricted
  network access. `allowlist-proxy` (internet off) creates an internal per-run
  network, starts a per-run proxy container from `Dockerfile.egress-proxy`,
  connects it to that network as `adore-egress-proxy`, starts the executor
  only on the internal network, and injects uppercase/lowercase proxy
  environment variables at provision and exec time. The generated
  `squid.conf` admits host names (exact, or `*.` wildcards as `.domain`) with a
  `dstdomain` ACL and IP-address entries (such as `192.168.1.20` or `::1`) with
  a `dst` ACL, then `http_access deny all`. The proxy container also gets the
  `--add-host` options of `run_args` (`_proxy_host_args`), so an alias such as
  `host.docker.internal:host-gateway` resolves where the connection is opened.
  `none` adds `--network none`; it is still supported here, but no
  configuration selects it. Squid writes inside its owned `/var/log/squid`
  directory so it can start after dropping privileges to the `proxy` user.
- Windows host paths are normalized (`Path.as_posix()`) for mount syntax.
- Commit authorship comes from `agent.name` / `agent.email` via
  `GIT_AUTHOR_*` / `GIT_COMMITTER_*`; credential boundaries are
  documented in `01_Documentation/Security_And_Credentials.md`.

## 4. Dependencies

- Internal: `adore.util` (`CommandRunner`, `CommandResult`, `run_command`);
  values from `[worktree]` (`repo_path`, `root`) and `[container]`
  (`runtime`, `image`, cache volumes) config, and the `EgressPolicy` from
  `config.egress_policy`.
- External: `git` on the host; Docker or Podman - native or wrapped (Docker
  Engine inside WSL2 via `wsl -d <distro> -- docker`); the
  `adore-executor-base:1.0.0` image (built from
  `docker/Dockerfile.executor-base`: Ubuntu 22.04, Python 3.11 + uv, Node
  22.23.4, git with `safe.directory *`, Pi 1.4.0 and pi-web-access 0.46.0
  under `/opt/pi` with ADORE's guard extension (Pi is the only coding agent),
  glab/gh, non-root user `adore`) or a runtime-project image derived from it.
  `ContainerManager.spawn` starts a streaming `exec -i` command with `exec`'s
  environment rules (Pi's RPC launch); the caller bounds and ends it.

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
- SELinux relabel contract: `[container] selinux_relabel` is `off` (default)
  or `shared`. Under `shared`, `_bind_mount` appends `z` to the HOST bind
  mounts only - repo, worktree, io, and the generated egress-proxy config,
  which becomes `ro,z`. The uv/npm entries are NAMED VOLUMES and are never
  relabeled, because the runtime already creates them with a container-readable
  label. The private `Z` label is refused by both config validation and the
  `ContainerManager` constructor: it labels content per container, and the
  clone is shared across runs and with host git, so `Z` would bind the clone to
  one container and break the next run. An operator who accepts that trade can
  still express it through `run_args`.
- Fresh repository containers use the read-only native Git pointer and the
  creation-mode label described above. `build_container_env` retains its three
  managed selection fields as binding metadata; `provision` and `exec` consume
  them without forwarding selector values to descendants. Docker clears image
  defaults with bare unset keys and a sanitized CLI environment; Podman uses
  `--unsetenv`. No profile option or run-state schema field is added.
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
- The `allowlist-proxy` policy writes generated Squid config under the
  run IO directory, uses one proxy container named
  `<bounded executor name, at most 50>-egress-proxy` (at most 63 characters),
  and one network named `<network_prefix>-<bounded executor name, at most 48>`.
  A runtime-safe executor name that fits is used as is; a longer one keeps its
  start and ends in `-` plus 10 hex characters of the SHA-256 of the full
  executor name, so every run has its own proxy and network. Reaping removes
  executor, proxy container, and network; `adore cleanup` also removes the
  listed executors, proxies, and networks derived from the target executor
  names the orchestrator passes, recognising only the current per-run bounded
  proxy container and egress network names and keeping any name also derived
  from a retained executor. Containers and networks named by earlier builds are
  not recognised; an operator removes such leftovers by hand (see
  `01_Documentation/Recovery_And_Maintenance.md`). The network sweep checks the
  canonical `adore-egress` prefix even after the profile switches internet on,
  plus the current configured prefix; it never guesses arbitrary other
  prefixes.

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
result = containers.exec("adore-run-gitlab-x-14", ["pi", "--version"])
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
  translation and wrapped-runtime mount construction on both host OSes;
  `test_proxy_config_admits_names_by_domain_and_addresses_by_dst` covers the
  generated Squid ACLs.
- `tests/test_orchestrator.py` covers the conductor's use of these seams:
  checkpoint commits after each stage and after its own verification, the
  candidate fingerprint that binds validation and optional approval, and one push of the validated
  candidate at publication.
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
- **Internet switch, live 2026-11-03** (Docker Engine in WSL2): internet off
  reached the model provider through the per-run proxy, while
  `curl https://example.com` got 403 from the proxy, `npm install` was refused
  and `web_search` was not available; internet on searched through Exa, read a
  Wikipedia page with `fetch_content`, and `npm install` and `pip install`
  succeeded.

## 10. Limitations And Future Work

- The repo clone is mounted read-write into the executor container (commits
  need the shared object store). The executor cannot push (no credentials in
  the container; ADORE's Pi guard blocks `git push`), but a misbehaving executor could
  damage the *local* clone - acceptable for v1 since the clone is
  disposable; re-clone recovers it.
- Historical containers keep their creation-time environment during warm reuse.
  Their Git selectors continue targeting the managed worktree. The pointer mode
  applies to newly created repository containers; existing resources are released
  only through the established lifecycle and operator actions.
- Container-runtime limits can be supplied through `[container] run_args`, for
  example `--memory=2g` or `--cpus=2`. Egress networking is separately owned
  by `[executor] internet` and `[container.egress]`; dedicated first-class CPU/RAM configuration keys are
  not implemented.
- Docker UID/GID mapping: the executor base image is built with
  `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)` so the
  container's `adore` user and group match the host account. Without this, files
  written to bind-mounted volumes (worktree, IO, caches) are owned by the wrong
  UID/GID on the host and the host service cannot read/write the shared per-run
  directories. The Dockerfile defaults to `USER_UID=1000`/`USER_GID=1000`; pass
  the host user's UID and GID at build time.
- Rootless Podman commonly uses `[container] run_args = ["--userns=keep-id"]`
  to map the container user to the host account. SELinux hosts may additionally
  select shared relabeling. Pointer-mode live acceptance is performed separately
  on each installed runtime; offline tests exercise Podman CLI construction.
- WSL commands use direct `--exec` transport. Standard Docker/Podman prefixes
  normalize automatically; a custom wrapper identifies its command boundary
  explicitly. Container paths, scripts and argument values stay literal.

## Authoritative execution identity

`resource_identity(name)` validates bounded inspect JSON, duplicate fields, exact name, actual container ID, image ID and status; foreign/missing/malformed data raises `IsolationError`. `image_identity(image)` reads a local image ID without pulling. `ContainerBackend` supplies shared lifecycle/command ownership and verifies IDs before commands or cleanup. Focused proof: `tests/test_execution.py`.

## Automatic pager environment

`ContainerManager.exec` forces `GIT_PAGER=cat` and `PAGER=cat` after caller
values. Both non-secret keys use inline `--env KEY=cat` arguments, so native
Docker/Podman and WSL receive the same policy. Executor, preparation and model
probe descendants inherit it. Provider secrets retain bare-key forwarding and
existing redaction/WSL transport. Host runtime commands use the shared hidden
Windows command runner. Focused proof: container exec/env and WSL tests in
`tests/test_isolation.py`.

## Agent-controlled system packages

ContainerManager.authorize_system_packages uses fixed code and root-owned OS Python on the exact owned container ID, measures a non-root UID and requires exact success output. It grants direct package-manager sudo without installing packages or modifying egress. See [Package permissions](Component_Package_Permissions.md) and the operator dependency-installation guide.

Interactive Pi RPC spawn shares exec environment filtering: inherited repository selectors are removed, automatic child pager settings apply, secrets travel only through the client environment and Windows clients suppress console allocation.

## Recovery ownership checks

`verify_removal` rejects aliased/missing Git ownership, another common Git directory, branch or working directory. `release_owned` verifies actual dedicated executor/proxy mounts and internal network membership independently of current egress/backend settings, and removes only immutable IDs with absence verification. Name replacements, foreign members and unproven empty orphan networks are retained. `remove_remote_branch(..., allow_absent=True)` permits an empty saved checkpoint only when the remote ref is absent; a present ref still fails closed. Known checkpoints retain exact leases and post-delete absence verification. Offline proof: `tests/test_drift_recovery.py` and `tests/test_merged_branch_cleanup.py`.

## Fresh branch generations

`fresh_branch` checks local and exact remote absence for the configured base and at most three random `-g` plus twelve lowercase hexadecimal alternatives. Occupied refs are preserved; malformed output, failed Git status and naming-policy refusal are typed errors. `create(..., new_branch=True)` refuses existing worktree paths and uses atomic `git worktree add -b`, preventing adoption of a local ref appearing after the checks. Saved-run recovery retains its established reattachment behavior. Remote empty/exact publication leases remain mandatory. Proof: tests/test_drift_recovery.py.

## Checkpoint path guard

Before staging, `commit_all_if_dirty` queries untracked non-ignored files and
staged additions with NUL-delimited Git output and rename detection disabled.
It inspects staged additions again after staging and before committing.
A whole `%NAME%` segment or case-insensitive `ProgramData/Microsoft/Windows/Caches`
sequence raises `SuspiciousCheckpointPathError` with the path for operator
inspection; no file is deleted. Invalid or incomplete bounded Git evidence
raises `IsolationError`. Existing tracked modifications and ignored paths keep
Git semantics. This common host checkpoint applies to both execution backends.
