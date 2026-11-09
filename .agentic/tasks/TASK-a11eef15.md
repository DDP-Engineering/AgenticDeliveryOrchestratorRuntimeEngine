<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-a11eef15 - Optionally remove the ADORE-made local clone when deleting a project

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-c0644d76
parent:
branch: task/adore-web-interface
base: 220d0c0b3a52a0aa0b383d7186496c0479a112a0
opened: 2026-10-13

## Done checklist (current stage)

- [x] failing test first (red recorded)
- [x] implementation green on focused tests
- [x] docs, help, requirement, CHANGELOG and release note updated

## Frame

Problem: since enrollment clones repositories into <ADORE home>/repos/<ID>, deleting a project keeps that ADORE-made clone forever (Delete keeps "the repository"), so clones pile up on the server. STATED (user, after my proposal of an opt-in, off-by-default option limited to clones under <ADORE home>/repos with the project's origin): "e ok, commite local, apoi adauga optiunea de stergere clona".
Desired outcome: the Delete project dialog offers "Also remove the local clone <path>" (unchecked) when that clone can be removed safely; otherwise it says why the clone is kept; deleting with the option removes the clone after the profile.
Actors: administrators (web dialog, `adore profile delete`).
Primary scenario: archive vera -> Delete project -> dialog shows the option for /home/dpasare/.config/adore/repos/vera -> tick, type the name -> Delete -> profile, resources and the clone are gone.
Examples: clone under <home>/repos with origin of the project's repository, clean, not used by another project -> removable.
Counterexamples (kept, with a reason): clone outside <home>/repos (the user's own folder); folder missing; not a git clone; origin of another repository; another project's repo_path points to the same folder; a handed-off job's worktree still linked to it; uncommitted changes in the clone.
In scope: shared decision module (adore/clone_cleanup.py), GET /api/v1/projects/{name}/delete-preview, ProjectDeleteInput.remove_clone, command worker and `adore profile delete --remove-clone`, delete dialog option (four locales), help (four locales), docs, requirement, CHANGELOG, release note, tests, deploy to DCP.
Out of scope: removing clones outside <home>/repos; checking unpushed local branches (runs push to the forge); bulk cleanup of orphan clones; full suite (STATED earlier: at the end).
Constraints: off by default; never follow a symlinked clone path; the server and the CLI both recheck; the profile delete stays the primary effect.
Success signals: focused pytest/node/e2e green; on DCP the dialog shows the option for an ADORE-made clone.
Evidence: OBSERVED delete_project enqueues `delete` with run_id "" and the worker runs `adore profile delete <name> --force --remove-resources`; purge_resources keeps handed-off worktrees (git worktrees of repo_path); enrollment clones into <home>/repos (profiles.home / "repos"); repository_source.read_origin/parse_repository_url exist.
Assumptions: INFERRED a clone's repository path (owner/name) matching config platform.repo identifies the project's repository (the host is implicit for github/gitlab). Unknowns: none blocking.
Decision-blocking questions: none (scope proposed and accepted).
Proposed behaviors: B1 removal decision with reasons; B2 preview + opt-in delete request; B3 CLI/worker removal after profile deletion (REQ-FUNC-c0644d76).
Path and reason: full - irreversible filesystem deletion across API, worker and CLI needs a requirement, design and review.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Opt-in clone removal on delete | B1-B3 | REQ-FUNC-c0644d76 (new) | ADORE-made clean clone removed | outside repos, missing, not a clone, other origin, shared, linked worktree, uncommitted, symlink, removal failure | pytest test_clone_cleanup, e2e delete dialog | D1-D4 |

## Design

- D1 `adore/clone_cleanup.py`: `clone_decision(store, name, repo_path, repo, runner, *, linked_worktrees_ok=False) -> CloneDecision(path, removable, reason)`; reasons `outside-repos`, `missing`, `not-a-clone`, `origin-mismatch`, `shared`, `worktrees`, `uncommitted`, plus `unknown` for malformed configuration or unreadable paths (review round 1); symlinks (the clone or any folder between repos and it) count as outside; another profile with an unreadable config, a relative clone path, or its clone/worktree root/state root inside this clone counts as `shared`; `git status --porcelain` via the injected runner; linked worktrees = entries under `.git/worktrees`. `project_clone_decision` (pre-purge) passes `linked_worktrees_ok=True` and keeps the clone only for worktrees the sweep keeps.
- D2 `GET /api/v1/projects/{name}/delete-preview` (administrator): `{clone: {path, removable, reason}}` for archived projects; before purge, handed-off runs whose worktree folder exists also give `worktrees`.
- D3 `ProjectDeleteInput.remove_clone` (default false): rechecks D1, 409 `clone_not_removable` when not removable; enqueues `delete` with run_id `remove-clone`; the worker adds `--remove-clone`.
- D4 `adore profile delete --remove-resources --remove-clone`: checks D1 before purge (not removable -> nothing deleted, error); after purge runs `git worktree prune` and rechecks; deletes the profile; then removes the clone. A clone that became unsafe after purge or fails to delete is kept and reported (`clone_retained` with reason); the JSON report gains `clone_removed`.
- D5 frontend `DeleteCloneOption` inside the delete dialog: loads the preview, unchecked checkbox when removable, muted localized reason for every kept clone, including outside-repos and unknown (amended in review round 1; the Kept text alone gave no reason); copy in four locales.

## Log

- 2026-10-13 frame: scope accepted (STATED "e ok, commite local, apoi adauga optiunea de stergere clona" after the proposal: opt-in, off by default, only clones under <ADORE home>/repos with the project's origin); autopilot as in this session's tasks; full path (irreversible deletion across API, worker, CLI); full suite deferred by the user.
- 2026-10-13 specify: 1 created (REQ-FUNC-c0644d76); 0 retired.
- 2026-10-13 design: see ## Design D1-D5.
- 2026-10-13 build red: REQ-FUNC-c0644d76 command=`.venv/Scripts/python.exe -m pytest -q tests/test_clone_cleanup.py` exit=2 (collection error: no adore.clone_cleanup); expected missing behavior=clone decision, delete-preview, remove_clone request, worker argument and `--remove-clone` absent.
- 2026-10-13 build green: pytest test_clone_cleanup 16 passed + 1 skipped (symlink unavailable on Windows), with test_web_delete, test_profile_cli, test_web_commands and test_repository_source 101 passed; 2 unrelated failures (test_profile_rename, test_replaced_profile_rejects_queued_developer_command: Windows "Access is denied" on rename, failing identically on the stashed base 220d0c0); ruff clean (new files formatted); node 94/94; tsc (src + e2e) clean; e2e jobs+shell 51/51 (lifecycle test: unticked option, keep reason, remove_clone sent). Built adore/clone_cleanup.py, GET delete-preview, ProjectDeleteInput.remove_clone with 409 clone_not_removable, worker target remove-clone -> --remove-clone, CLI check/prune/recheck/remove with clone_removed/clone_retained, DeleteCloneOption in the delete dialog (four locales), Kept text and error message in four locales.
- 2026-10-13 help: updated (projects.md Delete project paragraph, four locales, parity ok).
- 2026-10-13 release-notes: updated (New / Projects entry now mentions removing the clone on delete; no new entry because New and Improved are at the 10-entry limit); `python 02_Tools/check_release_notes.py --since 220d0c0` ok.
- 2026-10-13 docs: CLI_Reference, Web_Interface, Component_CLI, Component_Web_API, Component_Web_Worker, new Component_Clone_Cleanup (+ README index), knowledge cli.md and web-interface.md, CHANGELOG.
- 2026-10-13 build -> validate; deployed to DCP as a11a (health ok).
- 2026-10-13 validate review round 1: spec-compliance FAIL -> the dialog now always states why a clone stays (outside-repos and unknown reasons shown, path optional), so help/docs/CHANGELOG "says why" hold; validClonePreview and copy moved to deleteCloneCopy.ts with a node test (every reason in four locales). implementation-quality FAIL (two medium) -> pre-purge decision ignores ADORE's own linked worktrees (linked_worktrees_ok, as D1 named) and keeps the clone only for worktrees the sweep keeps (handed-off/handoff-pending and local-backend runs under a container project); removal counts only when the folder is gone, otherwise `removal-failed`; lows applied: relative or nested paths of another project count as shared, malformed configuration gives `unknown` instead of a 500, any symlinked folder between repos and the clone counts as outside (spec note). Accepted without change: ignored files and the repository host are not compared (documented in Component_Clone_Cleanup limitations). pytest test_clone_cleanup 21 passed + 2 skipped; ruff clean; node 96/96; tsc clean.
- 2026-10-13 DEVIATION validate: design D1 amended after review (added `unknown` reason and broader `shared`/symlink rules); behaviour is stricter than designed, never looser.
- 2026-10-13 DEVIATION validate: ignored files inside the clone are removed with it and the repository host is not compared - accepted, ADORE's clone under <home>/repos is not a working copy; documented as limitations.
- 2026-10-13 validate review round 2: implementation-quality PASS (lows applied: Windows junctions between repos and the clone count as outside; the dialog text for `worktrees` says a worktree that deletion keeps; the pre-purge decision also keeps the clone for a linked worktree that is not one of this project's runs, so the dialog promises only what deletion does). spec-compliance FAIL (D5 text and three docs) -> D5 amended (a reason for every kept clone), Web_Interface, CHANGELOG and CLI_Reference say "no linked worktree that deletion keeps", help (four locales) and Component_Clone_Cleanup updated. pytest test_clone_cleanup 22 passed + 2 skipped; ruff clean; node 96/96; tsc clean.
- 2026-10-13 validate review round 3: spec-compliance PASS (D5 and docs match; requirement met at the point of removal); implementation-quality PASS (junction probe with mklink /J kept the clone; low applied: a relative `gitdir` record is resolved against its record folder). pytest test_clone_cleanup 22 passed + 2 skipped; ruff clean; node 96/96; tsc clean; e2e lifecycle 1/1 (jobs+shell 51/51 at round 1); help parity and release-notes checks ok; `aegis.py check --task TASK-a11eef15 --strict` ok; DCP a11e. DEVIATION validate: full suite not run - deferred by the user to the end of the refinements.
- 2026-10-13 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-13 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-a11eef15.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: Delete project offers an unticked Also remove the local clone option for an ADORE-owned clone (under <ADORE home>/repos, no symlink or junction, origin of the project's repository, not used by another project, no worktree that deletion keeps, no uncommitted changes) and otherwise says why the clone stays; GET delete-preview, remove_clone with 409 clone_not_removable, worker --remove-clone, CLI check/sweep/prune/recheck/delete profile/remove clone with clone_removed/clone_retained (removal-failed when the folder remains); four-locale copy and help; docs, requirement, CHANGELOG, release note
evidence: pytest test_clone_cleanup 22 passed + 2 skipped (symlinks unavailable on Windows), delete/profile/commands suites green except 2 pre-existing Windows rename-lock failures; ruff clean; node 96/96; tsc clean; e2e jobs+shell 51/51 and lifecycle 1/1 after the last UI change; help parity and release-notes checks ok; DCP a11e
issues: DEVIATION full suite deferred by user; DEVIATION design D1/D5 amended after review (stricter); DEVIATION ignored files and forge host not compared (documented); a clone kept by the CLI's late check is reported only in the CLI JSON (web operation shows completed)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-13)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-c0644d76 - Optionally remove the ADORE-made local clone when deleting a project
- deviations: 3 recorded
  - validate: design D1 amended after review (added `unknown` reason and broader `shared`/symlink rules); behaviour is stricter than designed, never looser.
  - validate: ignored files inside the clone are removed with it and the repository host is not compared - accepted, ADORE's clone under <home>/repos is not a working copy; documented as limitations.
  - validate: full suite not run - deferred by the user to the end of the refinements.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 220d0c0: 32 file(s) changed, 1284 line(s) added
- checks: errors=0 warnings=23 notes=23
- checklist: 3/3 done
