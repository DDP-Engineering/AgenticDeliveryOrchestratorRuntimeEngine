<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-da26661c - Editable job branch naming and server-validated preview

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-UX-7b47e30e, REQ-FUNC-84f30174
parent:
branch: task/adore-web-interface
base: 0f8adf40de8a2aa7a77b7647ad5da4eda0bf6998
opened: 2026-10-09

## Done checklist (current stage)

- [x] Scope, requirements, design and error boundaries reviewed
- [x] Component knowledge, architecture, project/environment context reconciled
- [x] Requirements and documentation agree with implemented behavior
- [x] Final targeted checks and current evolution recorded
- [x] Both explicit review axes approved
- [x] Authorized delivery and DCP live acceptance

## Frame

Problem: STATED both branch naming fields are informational after the broad external worktree restriction.
Desired outcome: STATED both editable in Repository, clearer names and a generated sample with rule result.
Actors: Admin reviewed editor; scoped Dev read-only viewer.
Primary scenario: Open Repository -> edit template or optional regex -> see server-checked sample -> prepare -> review -> pause pickup -> apply to future jobs.
Examples: feature/{slug}-{iid} renders feature/adore-1 and matches ^feature/.*$; empty regex means no naming rule.
Counterexamples: Invalid Python formatting/regex, mismatching sample, stale revision and external worktree path edits must not apply.
In scope: Exact two-key authority exception, shared Python preview/validation, no-write revision-bound preview API, four-locale row/editor/review labels and help, offline trust tests, relevant documentation, DCP deploy.
Out of scope: Azure feature implementation, changing defaults, actual Git/forge calls for preview, active-job naming, environment selectors, release, full suite, push/PR/merge and planning material.
Constraints: 85 minutes, 32 tracked files, no children, targeted tests only; preserve DCP profiles/state/TLS and remove temporary rollback backup after acceptance.
Success signals: Editable Admin rows, read-only Dev, preview bound to current draft and revision, invalid input explicitly displayed/blocked, valid reviewed apply, existing environment restrictions retained.
Evidence: OBSERVED config.py validates a rendered example using Python regex; app.py external-environment policy includes all worktree keys; settings.ts adds a second blanket restriction. Existing reviewed candidate endpoints provide revision/idle/pause authority.
Assumptions: INFERRED existing single-setting candidates are retained; users edit one field while the other effective field remains visible in the preview.
Unknowns: DCP active source and inventory, resolved at preflight.
Decision-blocking questions: none.
Proposed behaviors: Preview only generates an example; it creates no branch and cannot guarantee every future iid/run_id meets a regex.
Path and reason: Full; observable new preview endpoint/edit authority. Criteria: new behavior=yes, interface=yes, dependency=no, existing complete requirement=no, authority change=yes. Existing task branch reused.

## Requirement coverage

| Outcome | Requirement | Positive | Boundary | Design |
|---|---|---|---|---|
| Reviewed localized edits | REQ-UX-7b47e30e | Two Repository rows, sample and reviewed apply | Dev read-only, stale/corrupt preview, external paths blocked | Existing candidate flow, exact exceptions, reactive preview |
| Shared Python contract | REQ-FUNC-84f30174 | Render allowed variables and Python regex result | Invalid format/Git example/regex, bounded matching and no writes | Shared config helper and revision-bound API |

## Design

REQ-UX-7b47e30e: preserve single-setting candidate/apply contracts and future-job/paused-idle semantics. Permit only worktree.branch_template and worktree.branch_rule in server external policy and frontend input routing; keep every other external key blocked. Shared four-locale labels are used by row/editor/review. SettingsList receives project/revision/CSRF, computes the active pair plus one edited field, debounces preview, rejects stale/malformed responses and disables branch candidate preparation without matching valid evidence. Preview shows fixed sample inputs and explicitly example-only result; developers see effective pair but no editors.
REQ-FUNC-84f30174: shared branch_naming_preview in config.py uses Formatter with only slug/run_id/iid fields (no attributes/conversions/specs), bounded source/name lengths, Git branch syntax and Python regex match semantics. Regex evaluation uses an isolated standard-library Python subprocess with one-second timeout and closed boolean JSON output; no shell, network or Git commands. validate_config consumes the same findings, including empty-rule behavior. Web POST /projects/{name}/config/branch-preview accepts strict bounded template/rule/revision, uses scoped session+CSRF, checks the active revision before/after and returns closed sample/result codes without mutation. Candidate validation remains authoritative. No persisted schema/default change.
Architecture: config validator -> shared preview <- scoped preview API <- SettingsList; existing candidate/apply flow unchanged. Runtime conductor remains template formatting for actual job identity. Correct malformed/unsupported templates before jobs start. Risks: regex subprocess availability fails closed; extra source-validation findings are deliberate. Alternatives: browser JS regex rejected because Python syntax differs; combined persisted candidate avoided to preserve existing one-key review. Expected files: config.py, web/app.py, App.tsx, settings.ts/settingsCopy.ts/settingHelp.ts/styles.css; focused config/web/helper/browser tests; operator/component docs and affected current knowledge/spec. No open product decisions.

## Log

- 2026-10-09 frame: Explicit implementation and DCP replacement authorized; full path, 85-minute/32-file bounds and targeted-only verification. BMAD renderer/setup absent; repository AEGIS used as prior authorized fallback.
- 2026-10-09 specify: Two atomic requirements cover branch-only reviewed edits and shared bounded Python preview/validation; runtime defaults and environment ownership retained.
- 2026-10-09 design: Shared server semantics, fixed sample, exact authority exceptions and existing single-setting candidate flow; no schema/dependency change.

- 2026-10-09 build red: settings helper exit 1 (branch fields none rather than text), public preview import exit 1 (missing interface), API exact branch editability exit 1; post-red anchor 367 files at 0f8adf4, 2026-10-09T07:06:41.016672Z. Added closed-preview red helper (missing validator) before transport implementation. Shared bounded config/API and four-locale UI implemented; preview creates no branches or writes.

- 2026-10-09 build proof: 170 targeted config/wizard/branch/API tests passed; settings helpers 15 passed; TypeScript/Vite build passed. Browser branch editor, late/corrupt response and narrow Dev journeys passed; corrected UTF-8 translation handling. A later full focused browser run reported one transient restored-candidate HTTP 500, while four consecutive isolated branch apply/restore runs passed. Preview source/profile reads now share the apply lock to avoid atomic replacement contention; final complete focused proof follows. Direct operator/component docs, active settings spec and current knowledge reconciled; no dependency/default/schema change.

- 2026-10-09 validate review round 1: Specification compliance=approved for exact two-key edits, localized names, sample/rule feedback, no writes from preview and existing reviewed apply/role/runtime boundaries. Implementation quality=approved independently after source/test hunk review: closed bounded transport, Python regex process timeout/output checking, coherent preview reads, late-response suppression, candidate-bound pair and template-before-rule order. Invalid source field types, changing/corrupt source, external paths, scoped Dev and CSRF tests cover trust boundaries. Documentation/current architecture reconciled; unchanged environment; no children. Final focused proof follows.
- 2026-10-09 DEVIATION validate: Full check --strict --run replaced by targeted branch/config/wizard/web configuration tests, settings helper/browser journeys, TypeScript/Vite build, scoped Ruff and strict catalog under the standing user instruction; full repository suite remains deferred.

- 2026-10-09 validate final proof: 174 targeted Python tests passed (one existing Starlette deprecation warning); 23 settings browser journeys passed; 15 settings helpers passed; scoped Ruff and TypeScript/Vite build passed. Current evolution recorded at 07:23:21 UTC. Both round-1 review axes approved. Full suite deferred by user instruction. No children. Validated candidate unchanged.
- 2026-10-09 deliver authorization: User explicitly requested implementation and DCP deployment, with standing local commit authority; validation results and intended deployment presented. Local delivery commit then replacement of DCP test source, preserving profiles/state/TLS; no push, PR or merge.

- 2026-10-09 deliver outcome: Product commit 2b71d80fc4d009ababf380b5ea4ba13528658f87 deployed to /home/dpasare/apps/adore/dcp-branch-da26661c/04_Software. Package SHA256 0f2bdfbe37f1eca47071d38632494b36e5f7897c8003da8182ef4087dde06b6d; asset index-D1XxS8xt.js matched locally and remotely. Both services active, worker ready, health/pages 200 and protected unauthenticated APIs 401; existing certificate pinned. Six profiles and state/pause/config hashes, schema 14, one user, audit 106 and 18 terminal operations unchanged. Live authenticated aegis Repository showed two Edit actions and adore/pi-1; invalid regex blocked preparation, valid regex matched, edited template rendered feature/adore-aegis-1. Drafts cancelled, configuration unchanged; screenshot retained. Temporary rollback backup removed and backups directory empty. No push/PR/merge. Close-out journal commit follows.

## Rulings

- RULING-001 | date=2026-10-09 | decision=Autonomous implementation/local commit and DCP test deployment, focused tests only | reason=Explicit current user request and standing test/deploy instructions | source=user | supersedes=none

## Handoff

current: done
status: ready
next: none
must_read: .agentic/requirements/ux/REQ-UX-7b47e30e.toml, .agentic/requirements/functional/REQ-FUNC-84f30174.toml
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Editable branch naming and server-validated preview deployed to DCP
evidence: 174 Python, 23 browser, 15 helper tests; build/Ruff; DCP ready and live draft validation passed
issues: Full suite deferred by user; historical catalog findings and existing Starlette warning
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1

## Delivery report (2026-10-09)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-7b47e30e - Reviewed branch naming edits in Repository
  - REQ-FUNC-84f30174 - Shared bounded branch naming preview and validation
- deviations: 1 recorded
  - validate: Full check --strict --run replaced by targeted branch/config/wizard/web configuration tests, settings helper/browser journeys, TypeScript/Vite build, scoped Ruff and strict catalog under the standing user instruction; full repository suite remains deferred.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base 0f8adf4: 24 file(s) changed, 850 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 5/6 done; open: Authorized delivery and DCP live acceptance
