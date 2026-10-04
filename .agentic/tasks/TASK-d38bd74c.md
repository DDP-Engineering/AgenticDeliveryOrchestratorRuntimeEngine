<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-d38bd74c - Scope adore cleanup to the current project

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f, REQ-REL-2219035e
parent:
branch: task/adore-web-interface
base: 0cedbecc754d8c8c606c3d5aa9a751d2aab9c289
opened: 2026-10-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: `adore cleanup` protects only the current project's runs but sweeps
  host-wide: executor and proxy containers by the `<slug>-run-` prefix, egress
  networks by the `adore-egress` and configured prefixes, and every directory
  under `[worktree] root`. With the default slug `adore` and a shared worktree
  root, `adore --profile A cleanup` can force-remove project B's working or
  handed-off containers and delete B's worktrees.
Desired outcome: cleanup removes only resources that belong to the current
  project, still including that project's orphans (resources whose run state
  is gone), and leaves every other project's resources untouched.
Actors: operator running `adore [--profile P] cleanup`; other projects'
  conductors and humans working in handed-off worktrees on the same host.
Primary scenario: operator runs cleanup for project A -> ADORE identifies A's
  run IDs (recorded, corrupt, or named exactly like A's run IDs) -> removes
  the unprotected ones' containers, proxies, networks and worktrees -> JSON
  report lists them; B's resources are unchanged.
Examples: profiles A (gitea `dpasare/alpha`) and B (gitea `dpasare/beta`)
  share slug `adore` and root `worktrees`. B has a working run
  `gitea-dpasare-beta-3` and a handed-off worktree `gitea-dpasare-beta-2`.
  A has a cancelled run `gitea-dpasare-alpha-5` and an orphan container
  `adore-run-gitea-dpasare-alpha-9` with no state. Cleanup for A removes
  A's run 5 resources and the run 9 container; all of B's survive.
Counterexamples: `adore-run-gitea-dpasare-alpha-tools-4` (project
  `dpasare/alpha-tools`) is not A's, because the part after A's run-ID prefix
  must be a ticket number; a folder `notes` under the worktree root is not
  A's; A's failed, active and handed-off runs keep their resources (unchanged).
In scope: `Orchestrator.cleanup()` ownership rules and the isolation helpers
  it calls; tests with two projects sharing slug, worktree root and network
  prefix; CLI/component docs, knowledge pages, CHANGELOG.
Out of scope: container/proxy/network naming changes; `purge_resources()`;
  a host-wide cleanup mode; removing orphans of projects that no longer have
  a profile; the pre-existing name truncation and run-ID ambiguity (Unknowns).
Constraints: standard-library CLI; offline tests with fake runtime; existing
  protection of active, failed and human-owned runs; report keys stay
  (`containers_removed`, `proxy_containers_removed`, `egress_networks_removed`,
  `worktrees_removed`, `lock_*`, `corrupt_runs`); Doxygen docstrings.
Success signals: automated tests where a second project shares slug, root and
  network prefix: its working, handed-off and finished containers, proxies,
  networks and worktrees survive A's cleanup; A's terminal-run resources and
  name-matched orphans are removed; A's protected runs keep theirs; a
  look-alike project (`alpha-tools`) and an unrelated folder survive.
Evidence:
  - STATED: task note "Scope adore cleanup sweeps to the current project"
    (review finding in TASK-48ddbb7d); decide whether orphan detection needs a
    project-unique identifier and ask if container naming would change.
  - OBSERVED: `04_Software/adore/orchestrator.py` `cleanup()` uses prefix
    `f"{identity.slug}-run-"`, `cleanup_egress_networks(protected)` and
    `worktrees.list_dirs()` (whole root); `adore/branding.py` PRODUCT_SLUG
    `adore`, EGRESS_NETWORK_PREFIX `adore-egress`; `adore/config.py`
    `WorktreeConfig.root = "worktrees"` (relative, resolved against the
    process cwd in `isolation.py` WorktreeManager); `adore/wizard.py`
    `_slugify(agent_name)` defaults to `adore`; `adore/web/app.py`
    add_project gives each project its own worktree root but the same default
    slug.
  - OBSERVED: `adore/state.py` `derive_run_id` = `<platform>-<repo with / as
    ->-<iid>`; `identity.container_name` = `<slug>-run-<run_id>`; so names
    already carry a project-specific part. `isolation.py` truncates proxy names
    to 50 and network suffixes to 48 characters (`_safe_name`).
  - OBSERVED: `adore/cli.py` `_cmd_cleanup` states "corrupt run state is
    reported, never deleted", yet `cleanup()` protects only loadable runs, so
    a corrupt run's worktree and container are swept today.
  - OBSERVED (DCP, read-only): the six live profiles each set their own slug
    (`adore-<name>`) and a worktree root inside their profile folder, so DCP
    is not exposed today; container
    `adore-run-gitea-dpasare-adore-web-acceptance-20260930-1` belongs to a
    profile that no longer exists.
  - OBSERVED: tests `tests/test_orchestrator.py`
    `test_cleanup_preserves_failed_run_resources_and_reports_egress_gc`,
    `tests/test_isolation.py` cleanup sweep tests (630-690),
    `tests/test_smoke.py::test_cli_reset_guardrail_and_cleanup_report`;
    REQ-FUNC-39697089 covers force/lock guards only, not cleanup scope.
  - INFERRED: no naming change is needed; a run ID of project A matches
    `^<platform>-<safe repo>-<digits>$`, which a different repo path cannot
    match unless the two paths already map to the same run IDs.
Assumptions: the run-ID shape from `derive_run_id` is the only shape ADORE
  creates for worktree directories and executor containers.
Unknowns:
  - Repo paths that differ only by `/` versus `-` (`a/b-c`, `a-b/c`) already
    share run IDs, worktrees and containers; pre-existing, out of scope.
  - Truncated proxy/network names: for long repo paths every run of a project
    shares one proxy/network name, and two projects with a long common prefix
    can share one; pre-existing naming defect, reported separately.
  - Orphans of deleted profiles are outside every project's scope after this
    fix; removal stays manual (`docker rm`).
Decision-blocking questions: none. The naming question resolves to "no
  change" (INFERRED above). Proposed behavior 4 changes current behavior and is
  presented for scope acceptance.
Proposed behaviors:
  1. Cleanup owns a run ID when it is recorded in this project's state, is a
     corrupt run directory in this state, or exactly matches this project's
     run-ID shape (`<platform>-<safe repo>-<number>`), found as a worktree
     directory name or in an executor container name `<slug>-run-<run ID>`.
  2. For each owned, unprotected run ID it removes the executor container,
     its egress proxy, its egress networks (canonical and configured prefix)
     and its worktree, reporting them under the existing keys.
  3. It never removes a container, proxy, network or directory it cannot tie
     to an owned run ID, including other projects' resources under shared
     prefixes or the shared worktree root.
  4. Corrupt runs keep their worktree and container (reported, never
     deleted), matching the CLI's stated contract.
Path and reason: full - changes which resources the command destroys
  (data-handling) and lacks a covering requirement.

| quick-path criterion | met | evidence |
|---|---|---|
| no new externally observable behavior | no | cleanup removes a different set; report contents change |
| no new interface or data format | yes | same command, flags and report keys |
| no new dependency | yes | standard library only |
| existing requirement covers it | no | REQ-FUNC-39697089 covers force and lock guards only |
| no security or data-handling change | no | changes which resources are destroyed |

## Requirement coverage

Behavior inventory (spec `specs/REQ-SEC-4a3f81cb.md`):

| Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result |
|---|---|---|---|---|---|---|
| Other projects untouched | cleanup | `adore cleanup` for A | removes only A-owned names | B's working/handed-off/done resources stay | look-alike `alpha-tools`, unrelated folder, shared truncated name with a protected run | B's resources exist, absent from report |
| A's orphans collected | cleanup | same | removes done/cancelled/stale and state-less form-matching runs | runs 5 and 9 gone, listed | A's active/failed/handed-off kept; runtime failure skipped, exit 0 | report lists removed names only |
| Corrupt runs kept | cleanup | unreadable `state.json` | keeps run resources, reports ID | run 7 resources exist | corrupt run's form-matching container not removed | `corrupt_runs` lists it |

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Other projects untouched (behaviors 1, 3) | cleanup removes only names derived from A's eligible run IDs | REQ-SEC-4a3f81cb | B shares slug/root/prefix; all B resources survive | look-alike project, unrelated folder, truncated name shared with protected run | pytest, fake runtime | run_id_pattern + target-only sweeps; tests: test_orchestrator two-project, look-alike, truncation; test_isolation sweeps |
| A's orphans collected (behavior 2) | done/cancelled/stale and state-less form-matching runs lose container, proxy, networks, worktree; report lists them | REQ-FUNC-aae1904f | cancelled run 5, orphan 9 removed and listed | active/failed/handed-off kept; mode change still collects proxy/network | pytest, fake runtime | eligible = owned - protected; worktree loop over eligible IDs; tests: test_orchestrator finished/state-less runs, mode change |
| Corrupt runs kept (behavior 4) | corrupt run's resources kept and reported | REQ-REL-2219035e | run 7 kept, in `corrupt_runs` | form-matching name of a corrupt run is protected | pytest, fake runtime | corrupt run IDs owned and protected; test: test_orchestrator corrupt run |

## Design

Behavior lives in spec `specs/REQ-SEC-4a3f81cb.md`; this note fixes the shape.

- **Run-ID form (REQ-SEC-4a3f81cb; technical: one derivation source).**
  `adore/state.py` gains `run_id_pattern(platform, project) -> re.Pattern`
  beside `derive_run_id`, sharing one private safe-project helper, so a name
  matches only as `^<kind>-<safe repo>-\d+$`.
- **Ownership in `Orchestrator.cleanup()` (REQ-SEC-4a3f81cb, REQ-REL-2219035e).**
  Owned run IDs = recorded runs | `invalid_runs()` | worktree-root directory
  names matching the pattern | `list_containers("<slug>-run-")` names whose
  remainder matches (listing in `suppress(IsolationError)`). Protected =
  active/failed/handed-off/handoff-pending recorded runs | corrupt runs.
  Eligible = owned - protected. Executor names per run ID =
  `identity.container_name(id)` plus the recorded `run.container`.
- **Isolation sweeps take targets (REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f).**
  `ContainerManager.cleanup_orphan_containers(prefix, targets, retained)`,
  `cleanup_egress_proxies(prefix, targets, retained)` and
  `cleanup_egress_networks(targets, retained)` keep their listings and
  best-effort removal but remove only listed names equal to a name derived
  from `targets` (executor, `_proxy_name`, `_egress_network_name` under both
  prefixes, any egress mode) and not derived from `retained`. Only cleanup
  calls them; the old protected-set form is replaced, not kept beside it.
- **Worktrees (REQ-FUNC-aae1904f).** For each eligible run ID in sorted order,
  `worktrees.path_for(id)` that is a directory is deregistered
  (`worktrees.remove`, suppressed) and `force_rmtree`d; `list_dirs()` is used
  only for discovery.
- **Report and CLI (REQ-FUNC-aae1904f).** Keys unchanged; lists come from the
  sweeps (existing names only) and are sorted. `_cmd_cleanup` docstring and
  the `cleanup` help text describe project-scoped removal; the corrupt-run note
  is unchanged.
- **Failure and concurrency.** Best-effort per resource and exit 0 as today;
  lock handling unchanged. Other projects' conductors are unaffected because
  none of their names is ever a target.
- **Compatibility.** No naming, flag or report-key change. Narrower removal:
  orphans of other or deleted projects and non-run folders under the root are
  no longer collected (documented; manual removal). Rollback = revert.
- **Test seams.** `tests/test_state.py` (pattern vs `derive_run_id`,
  look-alike repo); `tests/test_isolation.py` sweep tests rewritten to the
  targets/retained form (exact match, filter overmatch, truncated name shared
  with a retained run, mode change, failure continues);
  `tests/test_orchestrator.py` new cleanup tests driving a real
  `ContainerManager` over a stateful fake runtime (two projects sharing slug,
  root and prefix; look-alike project; unrelated folder; finished and
  state-less runs; corrupt run; truncation) and the existing failed-run
  cleanup test updated to project-form orphan names; the `FakeContainers`
  sweep stubs follow the new signatures.
- **Alternatives rejected.** Recorded runs only (as `purge_resources`): loses
  state-less orphans (REQ-FUNC-aae1904f). Narrow prefix
  `<slug>-run-<kind>-<repo>-`: overmatches `alpha-tools`. Project labels or
  new names: naming change excluded by RULING-002.
- **Risks / open decisions.** Run-ID ambiguity (`a/b-c` vs `a-b/c`) and name
  truncation stay pre-existing (spec assumptions). No open decisions. No
  component structure change; no architecture drawing owed.
- **Expected files.** `04_Software/adore/{state,orchestrator,isolation,cli}.py`;
  `04_Software/tests/{test_state,test_isolation,test_orchestrator}.py`;
  `01_Documentation/{CLI_Reference,Operations_Guide,Recovery_And_Maintenance}.md`;
  `05_SoftwareDocu/Component_{Orchestrator,Isolation,CLI,State_Store}.md`;
  knowledge `orchestrator.md`,
  `isolation.md`, `cli.md`, `state-store.md`; `CHANGELOG.md`.

## Log

- 2026-10-04 frame: full path (changes which resources cleanup destroys; no covering requirement). Ownership by this project's run IDs, no naming change; proposed corrupt-run protection. Checkpoint mode; scope presented, awaiting acceptance.
- 2026-10-04 frame accepted: user chose "Autopilot to validate" - scope as framed including corrupt-run protection (behavior 4); interaction set to autopilot; stop before deliver.
- 2026-10-04 specify: 3 requirements created (draft), 0 revised, 0 reused, 0 retired; spec `specs/REQ-SEC-4a3f81cb.md` holds the ownership algorithm, truncation and orphan limits. REQ-FUNC-39697089 (force/lock guards) and REQ-FUNC-0bdb23d5 (fail-closed state) unchanged and consistent.
- 2026-10-04 design: note in `## Design` (shared run-ID pattern, project ownership in cleanup, target-only isolation sweeps); behavior in `specs/REQ-SEC-4a3f81cb.md`; no architecture change.
- 2026-10-04 build red: REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f, REQ-REL-2219035e; command=`.venv/Scripts/python.exe -m pytest -q tests/test_state.py::test_run_id_pattern_matches_only_one_projects_run_ids tests/test_isolation.py tests/test_orchestrator.py tests/test_checkpoint_handoff.py -k "cleanup or run_id_pattern or handoff_idle"` (from 04_Software); exit=1; expected missing behavior=no run_id_pattern, sweeps still take a protected set (TypeError on targets/retained), cleanup removed every resource of the other project on a shared host and the corrupt run's worktree. The finished/state-less removal and truncated-name tests already pass (existing behavior kept as regression guards).
- 2026-10-04 build green: REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f, REQ-REL-2219035e; command=`.venv/Scripts/python.exe -m pytest -q tests/test_state.py tests/test_isolation.py tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_smoke.py tests/test_profile_cli.py tests/test_release_consistency.py` (from 04_Software); exit=0 (273 passed, 1 skipped); `ruff check adore tests` exit=0. Requirements active with linked tests; docs (CLI_Reference, Operations_Guide, Recovery_And_Maintenance, Component_CLI/Isolation/Orchestrator/State_Store), knowledge (cli, isolation, orchestrator, state-store) and CHANGELOG updated. Evolution: 4 modified sources (cli, isolation, orchestrator, state) as designed; `check --task` shows only pre-existing warnings (tracked fingerprint sidecars, TASK-5e99ee1d/TASK-c765e6b4 journal headers). Advanced to validate.
- 2026-10-04 validate review round 1: spec_compliance=changes_required (MEDIUM: Operator_Cheat_Sheets/Failure_Recovery_And_Cleanup.md still describes the prefix-wide sweep; MEDIUM: REQ-SEC-4a3f81cb prose and CLI_Reference, Operations_Guide, Recovery_And_Maintenance, Component_CLI, Component_Orchestrator, knowledge isolation and CHANGELOG state an absolute other-project guarantee while proxy/network names shared through truncation can be removed (spec assumption); LOW: WorktreeManager.list_dirs docstring still says cleanup sweeps it; LOW notes: shared-host test docstring overstates the other project's state, state-less run split across runs 9/13, leftover proxy/network of a run without state, worktree or executor is not collected and undocumented, two line-wrap overruns); implementation_quality=approved (MEDIUM note: same truncation collision; LOW: docs overstate it, run_id_pattern relies on fullmatch, missing tests for a recorded non-form run ID, a recorded container name differing from container_name, and runtime listing failures at orchestrator level, worktrees_removed can list a directory force_rmtree failed to remove, stale lifecycle cleaned but undocumented, CRLF in the new untracked .agentic artifacts). Routed to build for fix cycle 1 of 4: fix all recorded findings except the truncation itself, which is documented as the stated exception (removal is the separate naming task the user requested next).
- 2026-10-04 build fix cycle 1 red: REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f; command=`.venv/Scripts/python.exe -m pytest -q tests/test_state.py::test_run_id_pattern_matches_only_one_projects_run_ids tests/test_orchestrator.py -k "cleanup or run_id_pattern"` (from 04_Software); exit=1; expected missing behavior=run_id_pattern matched a prefix via .match, and a worktree that survived force_rmtree was reported under worktrees_removed. New stale/legacy-ID/renamed-container cases and the runtime-failure test pass (existing behavior).
- 2026-10-04 build fix cycle 1: run_id_pattern anchored (`\Z`); cleanup lists a worktree only when its directory is gone; WorktreeManager.list_dirs and _cmd_cleanup docstrings current; tests added/extended (stale run, recorded non-form run ID, recorded container of another name, single state-less run with all four resources, runtime failure, surviving directory, anchored pattern); Operator_Cheat_Sheets/Failure_Recovery_And_Cleanup.md rewritten for project-scoped cleanup; the truncated proxy/network exception stated in REQ-SEC-4a3f81cb, spec, CLI_Reference, Operations_Guide, Recovery_And_Maintenance, Component_CLI, Component_Orchestrator, knowledge isolation and CHANGELOG; stale runs named in REQ-FUNC-aae1904f, spec and docs; leftover proxy/network without any run trace documented as manual; line wraps fixed. New .agentic artifacts already LF (0 CRLF). Focused `pytest -q tests/test_state.py tests/test_isolation.py tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_smoke.py tests/test_profile_cli.py tests/test_release_consistency.py` exit=0 (275 passed, 1 skipped); ruff exit=0; evolution refreshed. Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=approved; implementation_quality=approved (independent judges; quality judge observed full suite 721 passed/1 skipped, ruff clean, 0 CRLF in changed/new files). All round-1 findings resolved. Accepted LOW notes (changing them would invalidate both verdicts): cheat sheet and knowledge cli/orchestrator pages do not repeat the truncation exception (they promise nothing about other projects); Component_CLI.md:144 lists only active and failed runs as protected (pre-existing, incomplete not wrong); coverage row 1 omits the truncation exception; a few changed lines exceed 80 characters; Component_Orchestrator.md:50 attaches "of its run-ID form" to recorded runs too; the anchoring test does not distinguish `\Z` from `$`. Out of scope (pre-existing): cleanup racing a live conductor creating a worktree before its first state save; case-only run-ID collisions on Windows.
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-d38bd74c --strict --run`; exit=0; test ok 46.3s, lint ok, frontend ok; errors=0, warnings=3, all pre-existing (tracked fingerprint sidecars; TASK-5e99ee1d invalid Handoff status; TASK-c765e6b4 ruling record). Knowledge pages (cli, isolation, orchestrator, state-store) reconciled; requirements re-read; no manual verification owed; evolution refreshed after the last candidate edit. Validate complete; advanced to deliver; stopping for delivery approval (RULING-002).
- 2026-10-04 deliver: validation evidence, verdicts, accepted notes, diff (20 modified, 5 new files), exclusions and outcome presented; no deviations recorded. User approved "Deploy to DCP, then commit": outcome = DCP deployment of the validated candidate (adore/cli.py, orchestrator.py, isolation.py, state.py), then one repository-local commit (no push/PR).
- 2026-10-04 deliver DCP: archive SHA-256 9641e4953d614b789555e379f015fbcd213d94d3fc901de8369687ed4edaeda3 verified on host; live cli.py/orchestrator.py/isolation.py/state.py matched base 0cedbec; backups suffix .pre-cleanup-scope-20261004070256; services restarted and active; run_id_pattern probe (own, look-alike) -> True False; cleanup help shows project scope; installed modules equal the bundle; health/ready/UI 200; read-only `adore --profile nilo status` exit 0. No cleanup was run on the host.
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, spec, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-04 | decision=work stays on task/adore-web-interface | reason=user: "Do this task here"; the task note names this branch | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=frame scope accepted as written (behaviors 1-4, no naming change); autopilot through specify, design, build and validate with explicit review, then stop before deliver | reason=user chose "Autopilot to validate" at the frame checkpoint | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-d38bd74c.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 2 approved/approved; DCP deploy verified (pattern probe, help text, module hashes, health/ready 200, services active)
issues: accepted LOW review notes (see log); truncated proxy/network names stay a stated exception until the naming task
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-04)

- stage: deliver; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-SEC-4a3f81cb - Confine cleanup to the current project's resources
  - REQ-FUNC-aae1904f - Remove the current project's finished and orphaned run resources
  - REQ-REL-2219035e - Keep resources of runs with corrupt state during cleanup
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 0cedbec: 25 file(s) changed, 1044 line(s) added
- checks: errors=0 warnings=4 notes=31
- checklist: 4/6 done; open: agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
