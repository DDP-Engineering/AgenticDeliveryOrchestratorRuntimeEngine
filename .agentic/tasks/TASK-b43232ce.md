<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# TASK-b43232ce - Remove merged run branches across all forges

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-93bd42af
parent:
branch: task/adore-web-interface
base: 292ee182562774aa3e051ae45283b346d9cc44ca
opened: 2026-10-08

## Done checklist (current stage)

- [x] Validated candidate unchanged and concrete delivery scope recorded
- [x] Standing human authority for local commit and DCP replacement recorded
- [x] Source commit and report
- [x] DCP replacement and live verification
- [x] Close-out

## Frame

Problem: STATED user expects Remove branch after human merge on all three forges; OBSERVED current GitLab-native flag is ignored by GitHub/Gitea adapters.
Desired outcome: Shared conductor cleanup after authoritative human merge, with matching help in four locales.
Actors: Human reviewer, CLI/web conductor, forge adapter, host Git transport.
Primary scenario: Human merges PR; next poll deletes the unchanged run branch and completes the run.
Examples: GitLab already removed the branch: successful no-op. GitHub/Gitea unchanged branch: leased deletion.
Counterexamples: Closed unmerged PR or false setting: no remote deletion. Changed remote commit: preserve branch and report warning.
In scope: Shared leased cleanup, exact boolean config, Gitea merge-evidence trust boundary, tests and direct docs.
Out of scope: Merging, repository-wide auto-delete settings, arbitrary branch cleanup, modifying existing configs.
Constraints: User requires targeted tests only until final settings review. Bound 60 minutes, 30 candidate files; no children, no push/PR. Reuse existing task branch and standing local commit/DCP test replacement authority.
Success signals: Offline tests prove every forge and trust boundary; updated deployed help.
Evidence: forge adapters create_merge_request, orchestrator _reconcile_review/_push_branch, isolation push_checkpoint, settingHelp.ts.
Assumptions: INFERRED host push credentials can delete its own branch subject to server permissions.
Unknowns: Server permissions may refuse deletion; report bounded warning and preserve evidence.
Decision-blocking questions: None.
Proposed behaviors: See requirement and Design.
Path and reason: Full. New observable cross-forge deletion and data handling; no dependency or state schema change.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary/failure | Verification | Design |
|---|---|---|---|---|---|---|
| Shared branch removal | Remove unchanged owned branch after human merge | REQ-FUNC-93bd42af | All forges | Closed/false/foreign SHA/malformed output/transport | Offline public poll and Git contract tests | Shared conductor + exact lease |

## Design

REQ-FUNC-93bd42af: Conductor observes normalized merge, checks stored MR ID and configured run branch ownership, then uses existing bounded transient retry helper for WorktreeManager.remove_remote_branch. Host Git checks target/ref and exact remote SHA, deletes with force-with-lease, verifies absence. Every successful final publication pins checkpoint_remote_commit even when progress publication is false. Legacy runs resolve their local branch if remote still exists; an absent branch succeeds without local state. Native GitLab flag remains an early optimization. False requests no ADORE removal; repository policy stays independent.
Failures: Completed human merge remains done, outcome contains branch-retained warning; local worktree stays for operator remediation. Normal success removes local resources. No additive persisted fields or schema change; crash after deletion is idempotent. Gitea merged must be a boolean to prevent truthy text from authorizing deletion.
Architecture: forge.get_merge_request -> conductor -> bounded retry -> WorktreeManager -> host Git origin exact leased ref deletion. Forge create API remains compatible.
Alternative: Per-forge deletion APIs add three redundant transport implementations; shared existing Git authentication is portable and consistent.

## Log

- 2026-10-08 delivery outcome: Source commit 07c20456a8f2b277e097e71b8a7f49df25291a91 installed at /home/dpasare/apps/adore/dcp-branch-b43232ce/04_Software; backup /home/dpasare/apps/adore/backups/dcp-branch-b43232ce-20261008T180739Z. Package SHA256 f5d337f3721d7663be3237e804ef5f9affd69ccb4ae24ddbd144cc8079452831; compiled asset index-BSiG9x16.js SHA256 9070e4f4de9336c7675f95e03d67f1685339e0f998e46972a6e85c5a14a11d23. Both services active and worker ready; LAN health/pages 200, protected APIs 401, existing TLS certificate pinned unchanged. Before/after inventories exactly equal: schema 14, one user, audit 105, 18 completed operations, all six configuration/state hashes and pause flags intact. Authenticated live settings show GitHub/GitLab/Gitea help; screenshot dcp-branch-help.png saved; no GUI configuration writes. SSH/SCP sessions exited. No real remote branch deletion/merge performed during acceptance, and no Git push/PR. Targeted offline proof covers branch transport; full suite remains deferred.

- 2026-10-08 validate final: Final targeted pytest on cleanup/conductor/checkpoint/forge/config exit=0, 284 passed; changed Python Ruff exit=0; TypeScript/build and focused Chromium help journey exit=0 (1 passed). Strict catalog exit=0, 0 errors / 9 historical warnings / 25 unrelated manual notes. Full suite deferred per user. Candidate 22 files within bound; both verdicts approved round 2.
- 2026-10-08 deliver: Concrete candidate is shared leased cleanup, exact boolean validation, strict Gitea merge evidence, four-locale help and directly affected docs/tests. Existing configs/state remain intact; no push/PR. Use standing user-authorized local commit and DCP test replacement; full-suite substitution remains recorded.

- 2026-10-08 validate review round 2: Both independent verdicts approved on final candidate including ownership/Git trust tests. One test fake required returning a mismatched review explicitly; default fake correctly returns missing for unknown IDs. Production unchanged.

- 2026-10-08 build red: pytest test_merged_branch_cleanup.py exit=1, 24 failed / 5 passed; missing cross-forge cleanup, missing leased transport method, unpinned final SHA and unchecked boolean choices. Gitea fake was corrected to include required HTTP status; invalid merge evidence then covered against the implementation. Anchor recorded at base 292ee18.
- 2026-10-08 build green: 279 targeted Python tests passed across cleanup/conductor/checkpoint/forge/config; browser help test passed (1 Chromium). TypeScript and deployable isolated build passed. Added ownership/Git failure boundary coverage for final proof. No full suite run.
- 2026-10-08 validate: Direct component docs, knowledge diagrams, requirements and project context reconciled; environment toolchain unchanged. Two independent assessments by executing agent: spec compliance approved and implementation quality approved, round 1. Shared exact lease protects remote changes; bounded failures retain worktree and human merge outcome; no merge operation or configuration rewrite.
- 2026-10-08 DEVIATION validate: Full configured suite deferred by explicit standing user instruction; final evidence uses targeted Python regression, one Chromium help journey, changed-file lint and strict catalog.

- 2026-10-08 frame: Full path accepted from explicit request and standing autonomy; 60-minute/30-file bound; current branch retained, no children.
- 2026-10-08 specify: REQ-FUNC-93bd42af defines merged cleanup and trust boundaries.
- 2026-10-08 design: Shared Git lease deletion with bounded retries, durable published SHA and retained evidence on failure; no state format change.

## Rulings

- RULING-001 | date=2026-10-08 | decision=Targeted tests only, full suite deferred | reason=Explicit standing user instruction | source=user | supersedes=none
- RULING-002 | date=2026-10-08 | decision=Autonomous implementation/local commit/DCP test deployment | reason=Standing authority in this settings session | source=user | supersedes=none

## Handoff

current: done
status: ready
next: Continue settings analysis; full suite deferred until requested
must_read: .agentic/requirements/functional/REQ-FUNC-93bd42af.toml
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Shared human-merged branch cleanup and all-forge help implemented
evidence: 284 focused Python tests, 1 Chromium help test and build/lint passed; DCP services/worker ready, live help verified, config/state preserved
issues: Full suite deferred by user
next: Continue settings analysis; full suite deferred until requested
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-08)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-93bd42af - Remove owned merged branches on every forge
- deviations: 1 recorded
  - validate: Full configured suite deferred by explicit standing user instruction; final evidence uses targeted Python regression, one Chromium help journey, changed-file lint and strict catalog.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 292ee18: 22 file(s) changed, 464 line(s) added
- checks: errors=0 warnings=10 notes=25
- checklist: 2/5 done; open: Source commit and report; DCP replacement and live verification; Close-out
