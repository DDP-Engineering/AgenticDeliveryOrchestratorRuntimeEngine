<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-48ddbb7d - Projects table and per-row controls

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-3b7dd34e, REQ-FUNC-bcaf01be, REQ-SEC-a514d0b2, REQ-UX-772cb418
parent:
branch: task/adore-web-interface
base: 0d27b8233512a2a2093039318f4147012056a825
opened: 2026-10-01

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: Projects uses a redundant top-bar selector, search/filter controls, cards and a separate selected-project action panel.
Desired outcome: A single sortable and paginated project table with controls on each row.
Actors: Administrator; project-scoped developer.
Primary scenario: Open Projects, sort by a column, inspect a row and use its authorized action.
Examples: Nilo sorts first by descending job count; an administrator resumes pickup for a paused project from its row.
Counterexamples: A developer sees only authorized projects and no mutating row actions; a malformed project cannot bypass server checks.
In scope: Projects view layout, sorting, pagination, per-row pickup/archive/detail controls, and a removal action after its scope is clarified.
Out of scope: Editing repository integration files unless explicitly selected by the owner.
Constraints: Existing API authorization and operational gates; preserve history and the human merge boundary; four languages and responsive layout.
Success signals: No Projects top-bar selector or old cards/filters; sorting and pages work; actions target their own row.
Evidence: STATED in user request and screenshot; OBSERVED in App.tsx, scoped operations, archive and profile-store behavior.
Assumptions: Sorting is client-side over the already authorized project list; missing activity sorts last.
Unknowns: Meaning of “remove ADORE from project” and whether repository files or only installation membership are affected.
Decision-blocking questions: Removal semantics requested asynchronously; the table work can proceed independently.
Proposed behaviors: The project table keeps the existing server-owned pickup/archive checks.
Path and reason: Full path for new UI behavior; autopilot reflects the user's standing no-interruption preference.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Project table | Authorized rows, sorting, paging and row actions | REQ-UX-3b7dd34e | Sort Nilo by jobs and open its detail | Developer sees no mutators; empty list remains empty | Manual browser inspection | Reuse PagedTable and current API operations |
| Removal (RULING-001/002) | CLI/engine removes ADORE resources except human-owned, deletes profile, keeps external state | REQ-FUNC-bcaf01be (new, spec REQ-SEC-a514d0b2) | archived idle project fully removed | unfinished run, lock held, invalid config -> nothing deleted | pytest (fake runtime) | Orchestrator.purge_resources releases only recorded resources of this project's runs |
| Removal | Web delete only for confirmed archived idle project, worker rechecks | REQ-SEC-a514d0b2 (new, spec) | queued delete -> worker -> project gone | 403/409/422 cases; worker-side recheck | pytest | POST /projects/{name}/delete + worker action delete |
| Removal | Typed-name confirmation on archived rows | REQ-UX-772cb418 (new) | delete after exact name | partial/wrong name disabled; developer none | manual browser | Projects row action + inline confirmation panel |
| Project table | Delete action on archived rows | REQ-UX-3b7dd34e (revised) | archived row shows Delete | unarchived/developer rows none | manual browser | row action list |

## Design

Render one table from the authorized `GET /projects` list. Sort by a single column with reversible direction and a stable project-name tie break; use the shared `PagedTable`. Pass each row's immutable project ID directly to existing operation/archive endpoints. Hide the top-bar selector only on Projects, retaining it on details, Jobs, Metrics and Settings. Resolve removal separately before extending API or row menu.

Removal design (2026-10-04, RULING-001/002; spec `specs/REQ-SEC-a514d0b2.md`):
- REQ-FUNC-bcaf01be: a new `Orchestrator.purge_resources()` iterates only the
  runs recorded in this project's state: for each non-human run it removes the
  recorded container names (`identity.container_name(run_id)` and
  `run.container`, each with its egress proxy/network via `containers.remove`)
  and `worktrees.path_for(run_id)`; human-owned runs' worktrees are reported as
  `worktrees_retained`. It never sweeps by name prefix or worktree root (shared
  across projects); `cleanup()` is unchanged. CLI `profile delete --remove-resources` builds the
  engine through `_engine` for that profile (invalid config -> error), holds
  `_operator_lock`, refuses corrupt state or any unfinished run, purges,
  releases the lock, deletes the profile directory, and prints the JSON report
  with `state_retained` when `store_root` lies outside the profile directory.
- REQ-SEC-a514d0b2: API `POST /api/v1/projects/{name}/delete` (admin_mutation)
  validates archive state, exact name, unfinished operations and run state,
  then `web.enqueue(..., "delete", "", key)` (store allows `delete`) and audits
  the request. Worker `run_pending` treats `delete` separately: admin actor,
  matching identity and archived profile required; argv
  `[python, -m, adore, profile, delete, <name>, --force, --remove-resources]`;
  audit `project-deleted` on success. `GET /operations/{id}` returns a
  `delete` operation to administrators when its project no longer resolves.
- REQ-UX-772cb418 / REQ-UX-3b7dd34e: Projects rows get a danger `Delete`
  text action for archived rows (admin); `deleteTarget` state opens an inline
  confirmation panel above the table (title, removed/kept explanation, name
  input, Delete enabled only on exact match, Cancel); submit calls the API,
  stores the returned operation (existing 2 s polling refreshes projects when
  it finishes) and shows a localized queued notice. New error codes get
  EN/FR/DE/RO messages in errors.ts.
Security: destructive action stays admin + CSRF + archived + typed name +
idle, rechecked by the worker; the API process never touches Docker/Git (the
worker runs the CLI). Concurrency: the conductor lock excludes a poll or
operator command during purge; queue ordering serializes worker actions.
Failure: purge errors are best-effort per resource (as cleanup); the profile
is deleted only after the sweep; a failed worker run leaves the archived
project in place for retry. Compatibility: `profile delete` without the flag
unchanged; no schema change. Test seams: tests/test_orchestrator.py
(purge), CLI profile tests, new tests/test_web_delete.py (API/worker/status);
manual browser for the UX. Alternatives rejected: deleting from the API
process (breaks the worker boundary); deleting human-owned worktrees or
external state (RULING-002). Expected files: adore/orchestrator.py,
adore/cli.py, adore/web/{app,store,commands}.py, web/src/{App.tsx,i18n.ts,
errors.ts,styles.css}, tests, bundle, docs (CLI_Reference, Web_Interface,
component docs), knowledge pages, CHANGELOG. No architecture change.

## Log

- 2026-10-01 frame/specify/design: Projects table behavior accepted from explicit user request and linked to REQ-UX-3b7dd34e. Removal is separated because `adore profile delete --force` irreversibly deletes state, while repository integration-file removal is a different action.
- 2026-10-01 build correction: Live DCP inspection found the nine-column table pushed action controls off-screen even at 1920px. Reduced the directory to five sortable data columns plus Actions; forge, runtime and executor remain on Project details.
- 2026-10-01 build proof: TypeScript/Vite passed after the layout correction. A local 12-project browser fixture verified 10/25/50/All controls, Next, descending numeric job sorting and reset to page one; mocked row pickup/archive requests used the clicked project ID, and a developer saw only View. Live DCP showed all six real projects, Nilo sorting first by job count, actions visible without desktop horizontal scrolling, and no page-wide overflow at 360px. HTTPS health, ready, UI and the compiled asset returned 200. The full offline suite and Ruff passed before the column-only correction; no backend behavior changed.
- 2026-10-01 build partial delivery: Hash-verified UI assets switched on DCP with separate rollback directories; real project settings, run state and repositories were unchanged. The removal action remains pending the owner's meaning of “remove ADORE from project.”
- 2026-10-01 build pause: Commit `93765f7` records the tested table. The removal action awaits the owner choice between detaching this ADORE profile with history preserved and changing integration files in the repository; the existing destructive profile-delete command is not used.
- 2026-10-04 resume: owner resolved removal semantics (RULING-001); RULING-002 records the safety boundary. Returned to specify for the removal behavior (deletion of data and a new API/worker/CLI contract need requirements and a spec); interaction stays autopilot; explicit review now enabled by aegis.toml; deliver (DCP deploy + commit) will stop for approval. Base 0d27b82 predates later branch tasks, so diff-vs-base reports include their files; evolution uses a fresh anchor.
- 2026-10-04 specify: 3 requirements created (REQ-FUNC-bcaf01be, REQ-SEC-a514d0b2, REQ-UX-772cb418) with spec specs/REQ-SEC-a514d0b2.md; REQ-UX-3b7dd34e revised to add the archived-row delete action; 0 retired; advanced to design (autopilot).
- 2026-10-04 design: removal design appended to ## Design (shared sweep + purge_resources, CLI --remove-resources, API delete + worker action, admin status fallback, Projects confirmation panel); advanced to build (autopilot).
- 2026-10-04 build red: REQ-FUNC-bcaf01be; command=`.venv\Scripts\python.exe -m pytest -q tests/test_orchestrator.py -k purge_resources tests/test_profile_cli.py -k "purge_resources or remove_resources"`; exit=1; expected missing behavior=Orchestrator.purge_resources and the --remove-resources deletion path do not exist (AttributeError).
- 2026-10-04 build red: REQ-SEC-a514d0b2; command=`.venv\Scripts\python.exe -m pytest -q tests/test_web_delete.py`; exit=1; expected missing behavior=no POST /projects/{name}/delete route (405 method_not_allowed), no delete operation for the worker.
- 2026-10-04 build green: REQ-FUNC-bcaf01be + REQ-SEC-a514d0b2; commands=`pytest -q tests/test_profile_cli.py tests/test_profiles.py` exit=0 (27), `pytest -q tests/test_orchestrator.py` exit=0 (91), `pytest -q tests/test_web_*.py` exit=0 (175 incl. 3 new delete tests).
- 2026-10-04 build red: REQ-UX-772cb418 (error messages); command=`node --test tests/errors.test.mjs` (in 04_Software/web); exit=1; expected missing behavior=new API codes project_not_archived and delete_confirmation_mismatch lack EN/FR/DE/RO messages.
- 2026-10-04 build deviation: DEVIATION build: wrapped label text and required marker in one span for Field and plain labels - fixes a TASK-87ebb7d6 layout defect (marker rendered on its own row because labels are column flexboxes); unrequested, markup only, re-verified in the browser.
- 2026-10-04 build green: REQ-UX-772cb418 messages; `node --test tests/*.test.mjs` exit=0 (23); `npx tsc -b` exit=0; `npm run build` exit=0 (assets LF-normalized).
- 2026-10-04 build manual observation: REQ-UX-772cb418, REQ-UX-3b7dd34e (delete row action), REQ-SEC-a514d0b2 end to end; method=Playwright-driven Chrome against a local server plus the real command worker (scratch verify_delete.py, seed6.py with alpha done + handed-off runs and two worktrees); 13/13: Delete only on archived rows; confirmation lists removed/kept; Delete enabled only for exact name (partial and wrong case disabled); queued notice, worker ran `adore profile delete alpha --force --remove-resources`, status succeeded, row left the table; profile directory gone, finished worktree removed, handed-off worktree kept, other project untouched; audit has project-delete-requested and project-deleted; developer sees no Delete; French texts; Cancel closes. Required-marker layout fix re-verified (marks_probe.py): markers inline on sign-in, Users, My account, Add project and delete confirmation.
- 2026-10-04 build: RULING-002 source corrected from the invalid "agent" to "technical" (format fix of an uncommitted record written in this session; decision unchanged); Ruff E501 x2 in tests/test_web_delete.py fixed. Docs updated (CLI_Reference, Web_Interface, Component_Web_API/Worker/Orchestrator/CLI, knowledge web-interface/cli, CHANGELOG). Evolution 22 files; edited test_orchestrator.py/test_profile_cli.py predate the anchor (taken after red) and are part of the candidate.
- 2026-10-04 build complete (removal); advanced to validate (autopilot); explicit review round 1 next.
- 2026-10-04 validate review round 1: spec_compliance=changes_required (missing tests: worker role recheck, developer 404 on deleted-project status, API 503 run_state_corrupt, CLI corrupt-state refusal; note: same-key retry returns 409); implementation_quality=changes_required (HIGH: purge reused prefix sweeps - "adore-run-" container prefix is product-wide and list_dirs covers a possibly shared worktree root, so deleting one project could remove other projects' containers/worktrees, verified in identity.py/isolation.py; MEDIUM: profile delete after lock release without error handling; notes: missing tests incl. handoff-pending and cross-project, refreshSelected not-found banner after deleting the selected project). Routed back to build for fix cycle 1 of 4; fixing only recorded findings. Pre-existing: `adore cleanup` has the same cross-project prefix sweep (out of scope; offered as a separate task).
- 2026-10-04 build fix cycle 1: purge_resources now releases only containers and worktrees recorded for this project's own runs (no prefix or worktree-root sweep), keeping handed-off/handoff-pending resources; cleanup() restored verbatim; CLI reports {deleted:null,error} and exits non-zero if profile removal fails; finished delete refreshes only the project list; spec/REQ-FUNC-bcaf01be wording corrected (the "same sweep as cleanup" clause was the defect) and same-key retry documented as 409; added tests: cross-project + handoff-pending purge, CLI corrupt state, API 503 run_state_corrupt, worker demoted-actor and replaced-identity refusal, developer 404 on a deleted project status. Focused `pytest -q tests/test_web_delete.py tests/test_profile_cli.py tests/test_orchestrator.py` exit=0 (108 passed).
- 2026-10-04 build fix cycle 1 proof: requirement links updated; `npx tsc -b`/`npm run build` exit=0; ruff exit=0; E2E rerun with real worker 13/13 (seeded unrelated other-project-run directory under the same worktree root kept, handed-off worktree kept, finished worktree removed); marker layout re-verified. Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=changes_required (journal Design/coverage still describe the removed shared _sweep_resources; knowledge cli.md says "sweeps"); implementation_quality=approved (both HIGH and the MEDIUM finding fixed; LOW notes: containers_removed may list already-absent containers, force_rmtree hides partial failures, no test for the profile-removal OSError path). Routed to build for fix cycle 2 of 4: correct stale design/knowledge wording and close cheap notes (OSError test, cancelled run in purge test, disabled actor case, API doc 503, requirement updated dates).
- 2026-10-04 build fix cycle 2: journal Design and coverage now describe the implemented purge (own recorded runs only, cleanup unchanged); knowledge cli.md wording fixed; Component_Web_API lists 503 run_state_corrupt; requirement updated dates corrected; tests added: cancelled run in purge test, CLI profile-removal OSError report, disabled-actor worker refusal. `ruff check adore tests` exit=0; focused pytest (delete/profile CLI/orchestrator) exit=0; web suite exit=0. Returned to validate for review round 3.
- 2026-10-04 validate review round 3: spec_compliance=approved; implementation_quality=approved (independent judges; full suite 713 passed/1 skipped observed by the quality judge). Accepted LOW notes: residual "sweep" wording in a test name/docstring/log, new CLI tests placed after the END OF FILE marker (cosmetic; moving them would invalidate both verdicts), containers_removed may list already-absent containers, force_rmtree hides partial failures. REQ-FUNC-bcaf01be now links the OSError test (journal-side). DCP read-only check: live cli.py, orchestrator.py, web/commands.py, isolation.py, state.py, profiles.py match base c9f56f5.
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-48ddbb7d --strict --run`; exit=0; test ok 47.3s, lint ok, frontend ok; errors=0, warnings=17: uncovered-source for web modules/tests from later tasks because this task base 0d27b82 predates them (covered by their own tasks' requirements); secret-in-diff = test-only passwords in test_web_delete.py and the unscanned bundle; 3 pre-existing journal/fingerprint WARNs. Validate complete; advanced to deliver; stopping before publication (DCP deploy + local commit need approval).
- 2026-10-04 deliver approval: user chose "Deploy to DCP, then commit" (local commit on task/adore-web-interface, no push). Bundle D:/Temp/adore-dcp-delete.tar.gz sha256=e61444b7213fe441e0d187c2217d081d7cab8214c458097eeb411a14024e7e6d (cli.py, orchestrator.py, web/app.py, web/store.py, web/commands.py, web/static; base-hash check against c9f56f5, backups, auto-rollback).
- 2026-10-04 deliver DCP: archive SHA-256 e61444b7213fe441e0d187c2217d081d7cab8214c458097eeb411a14024e7e6d verified on host; live cli.py/orchestrator.py/web/app.py/web/store.py/web/commands.py matched base c9f56f5; schema 13; 0 running operations; backups suffix .pre-delete-20261004062209; services restarted and active; signed-out POST /api/v1/projects/x/delete -> authentication_required; CLI profile delete --remove-resources present; index serves index-DsocgGes.js/index-CUpUbG48.css (bundle contains deleteProjectConfirm); live module hashes equal the local candidate; health/ready 200. No live project was deleted (destructive; left to the owner).
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, spec, journal and report (no push or PR requested).

## Rulings
- RULING-001 | date=2026-10-04 | decision=removal means deleting an archived project from the web UI: administrators only, typed project-name confirmation, removes the ADORE profile with its profile-owned state and ADORE worktrees/containers, keeps audit history; repository integration files are not touched | reason=user: "add delete project to the web UI as you suggested" | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=deletion never removes human-owned (handed-off or handoff-pending) worktrees or a project state folder outside ADORE home; both are retained and reported | reason=preserve the established human-owned worktree protection and avoid deleting arbitrary external paths | source=technical | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-48ddbb7d.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 3 approved/approved; DCP deploy verified (delete route and CLI flag live, module hashes equal candidate, health/ready 200, services active)
issues: accepted LOW review notes (see log); no live project deleted
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-04)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-3b7dd34e - Sort and page authorized projects with row actions
  - REQ-FUNC-bcaf01be - Remove an archived project's ADORE resources on deletion
  - REQ-SEC-a514d0b2 - Restrict web project deletion to confirmed archived projects
  - REQ-UX-772cb418 - Confirm project deletion by typing its name
- deviations: 1 recorded
  - build: wrapped label text and required marker in one span for Field and plain labels - fixes a TASK-87ebb7d6 layout defect (marker rendered on its own row because labels are column flexboxes); unrequested, markup only, re-verified in the browser.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 0d27b82: 108 file(s) changed, 7336 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=18 notes=31
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
