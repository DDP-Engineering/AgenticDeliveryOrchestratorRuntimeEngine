<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-02c8b00b - Integrate AEGIS 0.15 with local executor and container capabilities

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-FUNC-16237c6d, REQ-FUNC-8472a560, REQ-FUNC-faab24b2, REQ-FUNC-8adb68f9, REQ-FUNC-ffb9ed29, REQ-FUNC-c405688e, REQ-FUNC-0d0625e1, REQ-FUNC-bff135e2
parent:
branch: task/adore-web-interface
base: 4cbf0d02ccd52ce2d36e61c3c25ba59c47ab0348
opened: 2026-10-31

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [x] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [x] knowledge pages of changed components current with the reviewed code
- [x] project and environment context reconciled with the candidate
- [x] requirements re-read: status, prose, verification, paths and links true
- [x] manual or inspection verification recorded where applicable
- [x] explicit review approved, when enabled
- [x] final `check --strict --run` result logged truthfully after the last edit
- [x] remaining warnings and pre-existing failures explained
- [x] `report` appended

## Frame

Problem: OBSERVED: local WIP 4cbf0d0 and remote dc7062a diverge from 7a58890; the merge has conflicting AEGIS, conductor and documentation contracts.
Desired outcome: STATED: integrate remote and local changes, retain AEGIS 0.15 and all local functionality, resolve conflicts and validate.
Actors: STATED: repository operator; OBSERVED: ADORE conductor, executor backend and AEGIS companion.
Primary scenario: INFERRED from the request: a local merge preserves both parents and runs offline product validation on their reconciled tree.
Examples: OBSERVED: remote validate closes to done; local system-package authority remains independent of network; native retry, Git binding and timeout recovery remain present.
Counterexamples: STATED: do not push or restart ticket #25. OBSERVED: reverting to AEGIS 0.14 or discarding local package permission would violate the outcome.
In scope: STATED: integration and validation; INFERRED: compatibility corrections, existing regression fixtures and directly affected current-state docs/static assets.
Out of scope: STATED: push and #25 execution; repository rule: no merge of external review requests, no automated deployment/setup-script tests.
Constraints: STATED: preserve local functionality and AEGIS 0.15; repository rules: offline injected product tests, forge/executor independence, legal headers, existing branch.
Success signals: INFERRED: no unmerged paths/markers; exact remote managed 0.15 payload; both source histories retained; focused regressions and final configured product proof pass.
Evidence: OBSERVED: git status, merge-tree and merge; sources adore/aegis.py, orchestrator.py and existing container/native tests; remote dc7062a changes.
Assumptions: none needed for scope.
Unknowns: UNKNOWN: semantic integration failures until focused proof; live provider/forge/container acceptance is not rerun by this integration.
Decision-blocking questions: none; user explicitly authorized integration and validation.
Proposed behaviors: none beyond established contracts.
Path and reason: quick: reconcile existing behavior without introducing an interface or dependency.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | yes | existing remote and local functionality retained |
| no new interface or data format | yes | existing 0.15 schema-1 protocol and local settings |
| no new dependency | yes | existing Python/npm environments |
| an existing requirement already covers the behavior | yes | requirement header covers protocol/packages/Git/timeout |
| no security or data-handling change | yes | preserve existing authority and fail-closed boundaries |

## Requirement coverage

| Existing behavior | Requirement | Integration proof |
|---|---|---|
| Pinned schema/stages and selected-path backward routing | REQ-FUNC-16237c6d | test_aegis, test_orchestrator retry/backward cases |
| Supported companion floor and captured serialization | REQ-FUNC-8472a560 | test_aegis and test_aegis_compatibility |
| Fresh validation from done | REQ-FUNC-faab24b2 | test_orchestrator done/approval cases |
| Installed journal guide and CLI-owned State | REQ-FUNC-8adb68f9 | shared stage prompt tests |
| Native execution and explicit retry | REQ-FUNC-ffb9ed29 | test_local_execution and test_retry_revalidation |
| Direct package permission with independent egress | REQ-FUNC-c405688e | test_system_packages |
| Native Git discovery and transport | REQ-FUNC-0d0625e1 | test_container_git |
| Settled timeouts and retained dependencies | REQ-FUNC-bff135e2 | test_container_timeout |


## Design

Preserve the remote-managed AEGIS 0.15 payload byte-for-byte. Combine local backward routing with the remote done-to-validate revalidation contract. Retain native retry revalidation before any retry path and retain the independently configured package permission prompt. Remote done replaces local deliver in existing conductor/fixture contracts. Reconcile current-state documentation and rebuild static assets. Keep the merge uncommitted until its combined candidate passes validation. Bounds: 8 active hours, 6 review rounds, 180 integration paths; no live jobs or publication.


## Log

- 2026-10-31 frame: journal opened
- 2026-10-31 frame: completed; next build - Existing-contract integration on the quick path (7 Done checklist item(s) left unticked)
- 2026-10-31 build: red: pytest test_aegis.py -k transition_allowlist exit 1 (6 failures, 16 passes); remote routing loses established local backward transitions (REQ-FUNC-16237c6d). Initial merge conflict resolution is repository administration; anchor precedes product compatibility edits.
- 2026-10-31 build: green: focused AEGIS/conductor/native-retry/packages/Git/timeout regression command exit 0, 431 passed; supported and refused captured CLI replay exit 0, 7 passed. Remote legacy semantics were updated only in local fixture stages, not removed coverage.
- 2026-10-31 build: release-notes: updated (combined imported and local Interface notes to retain the ten-entry category limit; existing workflow note covers integration). help: updated (all four Jobs locales retain backward routing plus the current completion/approval flow).
- 2026-10-31 build: integrated scope audit complete; expanded focused command exit 0 (904 passed, one upstream httpx warning); npm test 117 passed; production build, Ruff, release-note and release-identity checks exit 0. No deployment/setup behavioral tests or live jobs ran.
- 2026-10-31 build: inspection: managed AEGIS 18 files match remote after line-ending normalization and removed deliver step stays absent; Git has no unmerged paths or whitespace errors. Catalog: 0 errors, 53 warnings, 22 notes: inherited stale paths/legacy journals, imported traceability/layout heuristics and minified-asset scan omission; no strict promotions. Existing delivery artifacts remain unchanged.
- 2026-10-31 build: completed; next validate
- 2026-10-31 validate: review: independent specification and implementation-quality verdicts approved round 1 on tree b5374412; reviewers additionally passed 34 and 155 focused tests respectively. No findings and no source edits.
- 2026-10-31 validate: final: python -X utf8 .agentic/aegis.py check --task TASK-02c8b00b --strict --run --json exit 0 after both reviews and last source edit; 2290 Python passed, 8 existing skips, one upstream Starlette/httpx warning; Ruff passed; frontend command passed (117 helpers and 226 Chromium journeys). 1219.97s overall. Catalog0errors53warnings22notes,0promotions; legacy journal/path and imported layout/coverage heuristics, minified asset scan omission remain recorded.
- 2026-10-31 validate: completed; next done

## Rulings

- RULING-001 | date=2026-10-31 | decision=Integrate remote and local changes with AEGIS 0.15; retain autopilot; no push and no restart of #25 | reason=Explicit current user request and session autopilot preference | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: Create the local integration commit; no push or #25 restart
must_read: .agentic/tasks/TASK-02c8b00b.md
changed: Integrated AEGIS 0.15 and preserved local capabilities
evidence: Strict proof exit 0: 2290 Python, 117 helpers, 226 Chromium; Ruff passed
issues: 53 catalog warnings; 8 existing skips; live acceptance not rerun
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-31)

- stage: validate; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-16237c6d - Validate AEGIS tasks and strict check evidence
  - REQ-FUNC-8472a560 - Refuse AEGIS releases older than 0.15.0
  - REQ-FUNC-faab24b2 - Return an unverified done task to validate
  - REQ-FUNC-8adb68f9 - Guide executor journal edits with the installed AEGIS authoring contract
  - REQ-FUNC-ffb9ed29 - Select native local execution with pinned machine account policy
  - REQ-FUNC-c405688e - Direct agent package installation
  - REQ-FUNC-0d0625e1 - Preserve native Git repository discovery in fresh executor containers
  - REQ-FUNC-bff135e2 - Settle timed-out container commands before reuse
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 4cbf0d0: 145 file(s) changed, 4705 line(s) added
- checks: errors=0 warnings=53 notes=22
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended

## Delivery report (2026-10-31)

- stage: validate; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-16237c6d - Validate AEGIS tasks and strict check evidence
  - REQ-FUNC-8472a560 - Refuse AEGIS releases older than 0.15.0
  - REQ-FUNC-faab24b2 - Return an unverified done task to validate
  - REQ-FUNC-8adb68f9 - Guide executor journal edits with the installed AEGIS authoring contract
  - REQ-FUNC-ffb9ed29 - Select native local execution with pinned machine account policy
  - REQ-FUNC-c405688e - Direct agent package installation
  - REQ-FUNC-0d0625e1 - Preserve native Git repository discovery in fresh executor containers
  - REQ-FUNC-bff135e2 - Settle timed-out container commands before reuse
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 4cbf0d0: 145 file(s) changed, 4723 line(s) added
- checks: errors=0 warnings=53 notes=22
- checklist: 9/9 done
