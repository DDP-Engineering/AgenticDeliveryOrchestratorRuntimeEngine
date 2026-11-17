# Isolation boundary remediation (review findings C1, H1-H3)

Status: proposed on 2026-11-17; nothing is implemented.
Requested: 2026-11-17, as the follow-up to the read-only repository review of the same day
([review report](2026-11-17_Repository_Review_Report_cdecfcca_0.19.0-wip.md)).
Implementation changes security behaviour, so each work package runs as AEGIS work
(`AGENTS.md`, "AEGIS workflow"). This plan is not an AEGIS artifact.

## Analysed state

| Item | Value |
|---|---|
| Branch | `master`, equal to `origin/master` |
| Base commit | `cdecfcca98df2bd5447f9b9419cf2e869e382906` (2026-11-17 04:30 +02:00, ADORE 0.18.0) |
| Working tree | 96 uncommitted paths that prepare ADORE 0.19.0; the tree was changing while it was reviewed |
| Line numbers | Working tree on 2026-11-17 05:00 +02:00. Files marked (m) carry uncommitted changes; all other cited files equal the base commit |
| Method | Source reading only. No test, container or exploit was run |

## Decision and scope

STATED: plan the remediation of review findings C1 and H1-H3. Nothing else is requested.

In scope:

- **C1** - a run container can make the host execute code. Two routes, see Evidence.
- **H1** - the host follows links when it reads files a container can write.
  The same defect in host writes to those directories is included, because one helper fixes both.
- **H2** - the egress allowlist and the Git pointer are stored where the agent can write them.
- **H3** - run and proxy containers start without privilege or resource limits.

Not in scope (review findings that need their own decision): the factory `admin`/`admin`
account, the session cookie persisted in configuration requests, request body limits, the
`_sanitize` Bearer leak, image supply-chain pinning, recording redaction and local execution.
Local execution stays what `Security_And_Credentials.md` already says it is: not a sandbox.

## Boundary rules to establish

The four findings break the same rule in different places. The remediation is these rules,
applied everywhere, and the work packages below are how each one is reached.

- **R1** The host never executes a program, hook or configuration that a container can write.
- **R2** The host reads a container-writable path only as a bounded regular file, without
  following links, and only after proving the file it opened is the file it inspected.
- **R3** Whatever the host authors for a container (scripts, proxy configuration, Git pointer)
  lives where no container can write it.
- **R4** A container starts with no capabilities, no privilege gain and bounded processes,
  unless the operator opts out explicitly.

## Evidence behind the change

OBSERVED in source (read by the reviewer; none of it was reproduced):

| Finding | Where | What the code does |
|---|---|---|
| C1, route A | `isolation.py:1864` | Mounts the whole project clone, including `.git`, read-write at `/adore/repo` in every run container |
| C1, route A | `isolation.py:1304`, `:1325`, `:608`, `:632`, `:650`, `:743` | The host runs Git on that clone and its worktrees: `add`, `commit`, `merge`, `status`, `diff`, `fetch`, `push`, `worktree add`, `branch -D`, `reset` |
| C1, route A | `isolation.py:1225` | `git commit` runs hooks; no call passes `--no-verify` or overrides `core.hooksPath`, `core.fsmonitor` or any other command-bearing key |
| C1, route A | `isolation.py:1229-1277` | `scrub_container_worktree_config` removes only `core.worktree = /adore/...` |
| C1, route B | `orchestrator.py:1257-1269` (m), `:385` (m), `aegis.py:16` (m), `:408-409` (m) | Every poll runs `<aegis_python> .agentic/aegis.py --version` **on the host** with `cwd` set to the project clone, whose checkout is inside the read-write mount |
| H1 | `orchestrator.py:3578-3586` (m) | `_read_questions` uses `is_file()` and `read_text()`; both follow links; the text is posted to the ticket |
| H1 | `executor/launcher.py:345`, `:529`; `aegis.py:513` (m) | `_read` and `_read_exchange` open container-written files with a plain `open` |
| H1, writes | `executor/launcher.py:268`, `:292`, `:384`, `:446`; `aegis.py:473` (m); `executor/pi_rpc.py:261` | The host creates, truncates or copies fixed file names inside the run IO directory with plain `open`, `touch`, `write_bytes` and `copy2` |
| H2 | `isolation.py:2360`, `:1866` | `squid.conf` is written under `<io>/egress-proxy/`, and `<io>` is mounted read-write at `/adore/io` |
| H2 | `isolation.py:2410-2421` | The configuration is written only when the proxy container is absent; a stopped proxy is restarted on the file as it is |
| H2 | `isolation.py:1834` | `container.git` is also under `<io>`; it is read-only at `/adore/work/.git` but writable through `/adore/io` |
| H3 | `isolation.py:1860-1896`, `:2412-2419` | Neither `run` argv sets `--cap-drop`, `--security-opt`, `--pids-limit`, `--memory` or `--init` |
| H3 | `Dockerfile.executor-base:33`, `:150` | `sudo` is installed; PID 1 is `sleep infinity` |

Route B was found while preparing this plan. It is not in the review report and needs no Git
knowledge: the agent overwrites `/adore/repo/.agentic/aegis.py` and the next poll runs it.

OBSERVED - patterns already in the code that satisfy R2 and R3 and should be reused, not reinvented:

- `isolation.py:884-946` `read_summary`: `lstat`, `O_NOFOLLOW`, identity before/during/after the read.
- `executor/launcher.py:477-518` `_retain_package_output` and `isolation.py:314-341` `_admit_git_pointer`.
- `isolation.py:1873-1874`: a read-only file mount layered over a writable mount (the Git pointer).
- `execution.py:427-435`: linked-parent refusal before writing preparation files.

OBSERVED in documentation: `Component_Isolation.md:164-166` says a malicious executor
"could damage the local clone". The code allows more than damage.

INFERRED:

- A denylist of dangerous Git keys cannot close route A. Hooks, `core.fsmonitor`,
  `core.sshCommand`, `credential.helper`, `filter.*`, `diff.*.textconv`, `merge.*.driver`,
  `gpg.program`, `url.*.insteadOf` and `include.path` all make Git run or contact something.
  The control data must be unreachable for writing instead.
- Concurrent runs of one project mount the same `.git`, so one run can alter another run's
  administration directory. A check made by the host just before it calls Git can be raced.
  Only a read-only mount is reliable.
- The agent does not need to write refs or configuration: `prompts/stage/closing.md:7` and
  `prompts/direct/implementation.md:13` tell it never to commit, and ADORE owns checkpoints
  (`isolation.py:1117` `commit_all_if_dirty`). This has to be proven against a real AEGIS
  payload and Pi before refs become read-only (WP5).
- On a Windows host, links created inside a Linux container may not resolve for Python.
  That is unverified and must not be relied on.

## Work packages

Order: WP1, WP2 and WP3 are independent and small; do them first. WP4 follows. WP5 starts
with a spike and a decision.

### WP1 - Repository mount denies by default (C1, R1)

Replace the single read-write clone mount with a read-only base and the few writable parts
Git needs inside a container.

| Container path | Host source | Mode |
|---|---|---|
| `/adore/repo/.git` | `<clone>/.git` | read-only |
| `/adore/repo/.git/objects` | `<clone>/.git/objects` | read-write |
| `/adore/repo/.git/refs`, `/adore/repo/.git/logs` | same under `<clone>/.git` | read-write until WP5 |
| `/adore/repo/.git/worktrees/<id>` | the run's own administration directory | read-write |
| `/adore/repo/.git/worktrees/<id>/commondir` | the same file | read-only file mount |
| `/adore/work/.git` | generated pointer (unchanged) | read-only |

Effects: the checkout is no longer mounted, which closes route B. `config`, `hooks/`, `info/`,
`packed-refs` and every other run's administration directory become read-only, which closes
the execution vectors of route A and the cross-run case.

Steps:

1. `ContainerManager.provision` (`isolation.py:1793`) builds the mounts above. The host creates
   `logs/` first, because a runtime cannot create a mount point inside a read-only parent.
2. Update the identity checks that name the repository binding: `resource_identity` call at
   `isolation.py:1840-1844`, `mounts_match` at `:1512`, and the orchestrator resource records at
   `orchestrator.py:627-640` (m) and `:3630-3639` (m).
3. Raise `_GIT_BINDING_VERSION` (`isolation.py:63`). A container created with the old layout is
   then refused by `_require_git_binding_label` and recreated, never silently reused.
4. Route every host Git call through one builder. Today there are two helpers and four raw
   `runner([...])` calls. The builder always adds `-c core.hooksPath=<empty host-private dir>`
   and `-c core.fsmonitor=false`, and before a worktree command asserts that `commondir` is
   `../..` and that `HEAD` names the run branch. A mismatch raises a typed `IsolationError`
   and fails the run; nothing is repaired automatically.
5. Update `02_Tools/build/verify_container_runtime.sh:207-213`, which reproduces the old mount.
6. `scrub_container_worktree_config` becomes unnecessary once no container can write
   `config`. Remove it only after the live check in Verification passes.

Residual after WP1, removed by WP5: objects, refs and the run's own index stay writable from
a container. That allows corruption and misleading state, not host execution.

### WP2 - One safe exchange helper (H1, R2)

1. Add one small module for host access to container-writable directories:
   - read: `lstat` is a regular file with one link, no linked parent below the exchange root,
     open with `O_NOFOLLOW | O_NONBLOCK`, compare `fstat` with `lstat`, read at most the limit;
   - write: refuse linked parents, unlink the name, create with `O_CREAT | O_EXCL | O_NOFOLLOW`;
   - on Windows, where `O_NOFOLLOW` is absent, also refuse reparse points
     (`st_file_attributes & 0x400`), as `web/host_folders.py:50` and
     `executor/launcher.py:75` already do.
   Move the existing logic of `read_summary` and `_retain_package_output` into it instead of
   writing a third copy.
2. Use it at every site in the Evidence table for H1, plus the `exists()`/`is_file()` probes
   on the questions file at `orchestrator.py:1534` (m) and `executor/launcher.py:350`.
3. A refused file is a failed stage with a typed code. Its content is never read, logged,
   journalled or posted. The ticket comment says only that the handoff file was unusable.
4. Find the remaining sites with one search during the build stage, and treat every hit as
   either converted or justified in the task journal:
   `read_text(|read_bytes(|.open(|write_text(|write_bytes(|touch(|copy2(` in
   `orchestrator.py`, `aegis.py`, `execution.py` and `executor/`.

### WP3 - Host-authored control files leave the IO directory (H2, R3)

1. Add a per-run directory beside `io`, for example `<run dir>/control`
   (`orchestrator.py:3649` (m) defines the `io` sibling). It is never mounted writable.
2. Move `egress-proxy/squid.conf` (`isolation.py:2360`) and `container.git` (`:1834`) there.
   `provision` and `_ensure_proxy_context` take the control path instead of deriving both
   from `io_path`.
3. `_ensure_proxy_context` always computes the expected configuration and compares it with a
   digest label on the proxy container. On a difference it recreates the proxy; it never
   restarts one on unverified configuration. This also applies an allowlist change to a
   parked run.
4. Optional, same file, decision D4: add `Safe_ports`/`CONNECT` limits and a
   `to_localhost`/link-local deny ahead of the allow rules. Allowlisted private endpoints
   with custom ports are a supported case and must keep working.

### WP4 - Containers start hardened (H3, R4)

1. Default argv for the run container: `--cap-drop=ALL`, `--security-opt=no-new-privileges`,
   `--pids-limit=<default>`, `--init`. Defaults come first and `run_args` after, so an operator
   override still wins.
2. The same for the proxy container, with whatever capabilities Squid in
   `Dockerfile.egress-proxy` proves to need.
3. `container.system_packages = true` relies on `sudo` (`package_permissions.py:27-60`), which
   cannot work with `no-new-privileges`. That mode gets a documented reduced profile: no
   `no-new-privileges` and only the capabilities package installation needs. The default mode
   keeps the full profile.
4. Include the profile in the binding label raised by WP1, so containers created without
   it are recreated.
5. Memory and CPU limits stay operator choices through `run_args`; state that plainly in
   `Configuration_Reference.md`.

Until WP4 ships, an operator can already set
`run_args = ["--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=2048", "--init"]`
on projects that do not use `system_packages` (`config.py:1176-1193` (m) accepts single option tokens).

### WP5 - Nothing the host trusts is writable in a container (C1 residual)

Target: the container gets a read-only view of the repository and a private scratch for
what its own Git writes.

- `refs` and `logs` become read-only, like the rest of `.git`.
- The run's real administration directory is no longer mounted. The container gets a
  host-private copy of it (its own `HEAD`, `index`, `commondir`), refreshed by the host at
  each stage start through the WP2 writer.
- New objects go to a private scratch directory through `GIT_OBJECT_DIRECTORY`, with the
  shared store read-only through `GIT_ALTERNATE_OBJECT_DIRECTORIES`.

The host keeps doing every commit, merge and push on the real administration directory,
which no container can reach.

Start with a spike, because the target makes these fail inside a container: `git commit`,
`git stash push`, branch creation and `git config --local`. The spike answers one question
with a real AEGIS 0.16 payload and Pi: does a complete job (frame to validate, a
clarification, a target-integration conflict) still pass? If not, record which write is
needed and decide D1.

## Verification

Focused tests, offline with injected runners (`AGENTS.md`, "Verification"):

- `tests/test_isolation.py`, `tests/test_container_git.py`: the exact `run` argv for the new
  mounts and the hardening flags; no mount of the clone root; old-label containers refused;
  proxy configuration outside `io`; proxy recreated on a digest difference.
- A new test module for the exchange helper: symlink, hard link, FIFO, directory, oversized
  file and a file replaced between inspect and open. Use the `symlink_support` fixture
  (`tests/conftest.py:51`) so the link cases also run on Windows.
- `tests/test_orchestrator.py`, `tests/test_executor.py`, `tests/test_aegis.py`: a linked
  questions file or AEGIS output fails the stage, and no part of the target's content
  reaches a comment, journal or outcome.
- Host Git builder: every call carries the two overrides; a redirected `commondir` or `HEAD`
  fails closed.

Live checks need operator authorization and are not automated tests (`AGENTS.md`). Run each
on Docker Engine, rootless Podman and a WSL-wrapped runtime, from inside a run container:

| Attempt | Expected |
|---|---|
| Write `/adore/repo/.git/hooks/pre-commit` or `/adore/repo/.git/config` | Read-only file system |
| Write `/adore/repo/.agentic/aegis.py` | Path does not exist |
| Replace the questions file with a link to a host file | Stage fails; nothing posted |
| Edit the Squid configuration | No path to it |
| `capsh --print`; start 5000 processes | No capabilities; stopped at the process limit |
| `git status`, `git diff`, `git add` in `/adore/work` | Work as before |

## Documents to update with the implementation

- `05_SoftwareDocu/Component_Isolation.md`: mount table (line 80) and the limitation at lines 164-166.
- `05_SoftwareDocu/Component_Executor_Launcher.md`, `Component_Aegis_Client.md`: exchange rules.
- `01_Documentation/Security_And_Credentials.md`: container boundary and package authority (lines 361-375).
- `01_Documentation/Configuration_Reference.md`: `[container] run_args` and the hardening defaults.
- `CHANGELOG.md` Unreleased; four-locale release notes, because operators will see containers
  recreated and a changed `system_packages` profile.

Related requirements to read when framing: REQ-SEC-23063055, REQ-SEC-3e1a4ea4,
REQ-SEC-553ebd62, REQ-SEC-19b768d6, REQ-SEC-a6d32441, REQ-SEC-c5d56d9f, REQ-SEC-fc949861.

## Upgrade behaviour

The project supports one stored format and no migration (`AGENTS.md`, "Stored data before
delivery"). WP1, WP3 and WP4 change where run files live and how containers are created.
Jobs that are active when the new build starts are refused with a typed error; they are not
adapted. The changelog names what to do: finish or cancel active jobs before starting the
build. Containers and proxies are disposable and are recreated.

## Open decisions

- **D1** After the WP5 spike: go to the read-only view with private scratch, or keep WP1 as
  the final state and accept that a run can corrupt refs and objects of its project.
- **D2** The pre-pick AEGIS probe still executes repository code on the host
  (`orchestrator.py:1257` (m)). After WP1 that code is the host's own checkout, not agent
  output. Keep it, or run the probe in a disposable container (`helper_command`,
  `isolation.py:2158`) with the checkout mounted read-only.
- **D3** The default process limit, and whether a default memory limit is wanted at all.
- **D4** Squid baseline rules (WP3 step 4).
- **D5** Whether WP1 to WP4 ship as one release, so operators recreate containers once.

## Until this ships

- Let only trusted authors label tickets ready: every route starts from ticket or repository text.
- Run ADORE under a dedicated account that holds nothing beyond the forge login it needs.
- Set the `run_args` shown in WP4.
- Prefer `container.egress` allowlist mode over open egress.
