<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-d5f346ed - Externalize executor environment setup

stage: deliver
type: change
path: full
interaction: autopilot
requirements: REQ-UX-01d189b8, REQ-FUNC-6b8494a7, REQ-UX-1b9b5789, REQ-REL-2cbd8d83, REQ-FUNC-a6a81d86, REQ-SEC-56f5f4a9, REQ-FUNC-6d6843ab, REQ-UX-94a97e70, REQ-UX-b75e1df8, REQ-UX-e6ed7168, REQ-SEC-3cf6cde4, REQ-UX-3b5b2257, REQ-UX-8186eea1
parent:
branch: task/adore-web-interface
base: 257a324
opened: 2026-10-08

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged
- [x] validation evidence, diff, exclusions and outcome presented
- [x] human local delivery and DCP replacement authorization confirmed from this session
- [ ] journal and report included in delivery commit
- [ ] agreed DCP replacement and read-only acceptance delivered
- [ ] close-out committed after outcome succeeds

## Frame

Problem: STATED environment configuration/build is too technical and difficult. User accepted the proposed external operator workflow and explicitly instructed implementation.
Desired outcome: Executor Configuration supplies a compact container notice, current effective image and expandable instructions identifying Dockerfile, recommended repository location and actual server profile configuration; environment setup is external.
Actors: Admin prepares the host/image externally; Admin/authorized Dev read guidance and configure executor/model through existing flows.
Primary scenario: externally configured container project -> open Executor Configuration -> see image and instructions -> operator prepares executor/Dockerfile and updates server config.toml -> ADORE retains readiness/runtime checks.
Examples: aegis uses installed Python/Pi image; no image mutation follows viewing instructions.
Counterexamples: Dev must not gain server config paths; local projects must not show container instructions; old browser/API requests must not build or apply environment settings; existing history and pending artifacts must remain recoverable.
In scope: remove environment controls from project settings and guided creation; localized read-only container guidance; actual Admin config path; refuse direct/pending/apply environment edits except existing dedicated AI endpoint; retire web build mutations and prevent old queued image builds executing; retain scoped historical reads/cancel/recovery; tests/docs/current knowledge and authorized DCP replacement.
Out of scope: changing runtime backend behavior, importing or automatically reading repository Dockerfiles, new manifests, installing tools, changing existing profiles/images, deleting history or artifacts, model/forge calls, release/remote Git operations.
Constraints: existing branch, no children; bounded 45 candidate files, three review correction rounds, 120-minute work interval; one replacement and read-only live acceptance.
Success signals: no environment editors in either UI flow, readable localized guidance, truthful effective image/Admin path, unauth/Dev scoping retained, retired mutation calls refused before side effects, old queued requests fail without invoking Docker, valid historical pending candidate remains discardable.
Evidence: OBSERVED App.tsx SettingsList/ProjectImage, EnrollmentWizard.tsx, app.py image/config routes, commands.py image worker and profiles.py config_path; STATED approved Romanian proposal.
Assumptions: human implementation approval covers the presented scope and direct completion; standing local delivery/DCP test replacement authorization remains.
Unknowns: actual deployment active state and saved paths will be checked freshly.
Decision-blocking questions: none.
Proposed behaviors: compact notice with one disclosure; no runtime controls; operator config contract remains portable TOML and standard external Dockerfile.
Path and reason: full; new public presentation and mutation refusals=yes, no schema replacement/dependency=yes; existing image requirements conflict and are explicitly retired by the accepted product change.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary | Verification | Design |
|---|---|---|---|---|---|---|
| Operator guidance | Conditional container notice and instructions | REQ-UX-01d189b8 | Admin sees effective image/path/examples | local hidden; Dev path withheld; narrow/localized | Browser/API/helper proof | Read-only component + current config response |
| External ownership | Web environment/build mutations refused | REQ-FUNC-6b8494a7 | Other executor edits and historical reads still work | direct/stage/old apply/old queue bypasses | HTTP/worker proof | Boundary guards before any side effects |
| Retire owned web definition/build/UI | Accepted removal | five retired IDs | History retained | no artifact deletion | Inspection and retention regression | Legacy persistence readers remain |

## Design

REQ-UX-01d189b8: read-only ExecutorEnvironment component in Executor Configuration, conditional on container backend. Effective image comes from validated recipe plan when present, else container.image; resolved config path is Admin-only. Four locales; one details disclosure with recommended executor/Dockerfile and legal non-root template, external build/config/check steps. New-project wizard keeps existing canonical default container setup internally, hides environment fields and their technical help, and directs specialized setup to existing external TOML enrollment; runtime contracts are unchanged.
REQ-FUNC-6b8494a7: remove isolation group UI and ProjectImage mount. app.py metadata marks environment settings not editable; dedicated function gates direct/stage/apply paths, preserving dedicated AI endpoint edits. Legacy pending schema validation remains unchanged so read/discard works. Image definition save and build submission return 410 after authorization/project access, before loading/retaining source. Existing queue image-build dispatch finishes failed and preserves artifacts without launching runtime. Historical scoped read/export/cancel and interrupted owned cleanup are retained for compatibility and recovery. No migrations, image deletion or database action enum changes.
Architecture: ExecutorEnvironment -> validated config read; external operator -> profile config/image -> existing runtime/readiness. Historical ImageBuildService -> retained evidence/owned recovery only.
Tests: real API fixtures check truth/Admin path and Dev omission, local conditional, direct/staged/persisted bypasses and queue refusal; browser journeys check controls absent, disclosure/locale/mobile and guided creation. Existing unaffected executor/endpoint/readiness suites remain.
Risks: historical pending environment changes require discarding and external preparation; guided defaults may lack a installed base, which existing readiness reports honestly.
Open decisions: none.

## Log

- 2026-10-08 frame: user explicitly accepted the concrete proposal and instructed implementation; full path, same branch, no children. BMAD renderer and setup skill unavailable; repository AEGIS used directly. Scope/design accepted by the user instruction; continuous implementation under prior same-session autonomy, local delivery and DCP authority.
- 2026-10-08 specify/design: two atomic requirements drafted; three image GUI/build requirements retired under accepted product change. Retain historical evidence/recovery and runtime/readiness contracts; external ownership guards must cover direct, pending apply and durable queue. Approved proposal translated into the above design before source edits.

- 2026-10-08 build red: pytest tests/test_web_image_build.py exit=1 with 16 expected failures/one preserved budget happy-path pass: missing guidance metadata and permitted environment/build/queued mutations. Browser images.spec.ts exit=1: external instructions absent. Retired browser/API build journeys replaced with external ownership contracts; internal artifact/recovery tests remain.
- 2026-10-08 DEVIATION build: anchor was recorded after the first source edit rather than immediately after red; evolution will be supplemented with the complete git diff against base 257a324 so those initial paths cannot escape review. Anchor records 362 files at 2026-10-08T04:28:18Z.

- 2026-10-08 build/validate: external instructions and guards implemented; guided defaults retain canonical image, runtime/readiness/model contracts unchanged. Five image GUI/build capabilities now retired; recipe UX revised to external configuration/CLI preview and read-only evidence. Local web environment selection test replaced with refusal/context contract; native execution tests retained.
- 2026-10-08 focused proof: 60 config/image/legacy pending tests and 66 local tests passed. Browser run 28/30 passed; failures were obsolete endpoint-tab/corrupt-panel selectors, corrected without changing expected public outcomes. Mobile screenshot inspected: disclosure/code/path wrap within390px with readable spacing. Final complete proof follows after corrections.
- 2026-10-08 review round1: independent scope-compliance pass reviewed approved Frame, two new and five retired requirements, native/recipe compatibility, absence of editors, truthful Admin/Dev metadata and preserved evidence. Verdict approved. Separate implementation-quality pass reviewed all backend/frontend/test hunks against base257a324, authorization ordering, secret-key and dedicated-endpoint exceptions, strict legacy read/apply refusal, old queue no-launch and owned recovery. Verdict approved; no unrequested runtime/schema/profile changes. The late anchor is supplemented by complete base diff. Current project/component architecture, instructions and external operator contracts reconciled before final proof.

- 2026-10-08 correction round2: integration inspection found portable target enrollment tests also selecting the removed image field/old step heading. Corrected their existing stopped-ownership/reference-confirmation journeys to Agent and model with no environment inputs; portable source/target and stale-boundary expectations unchanged. Prior review verdicts cleared; final proof and reviewed final tree will follow.

- 2026-10-08 full verification attempt: strict configured check exit1; Python1486pass/3fail/3skip, lint one new long line, frontend62pass/one missing-message catalog failure. Corrected new invalid-recipe fake to SourceRunner and line wrapping. DEVIATION validate: baseline raw-configuration fixture produced doubled CRLF on Windows; normalize input before intentionally forming CRLF. Added new external-owner error and seven existing missing localized execution/model/credential errors in four locales, preserving diagnostics/generic fallback. Two additional candidate files are included to make complete proof possible, within45-file bound. Exact-byte/concurrent-write and catalog contracts retained; no runtime validation weakened.

- 2026-10-08 correction round2 focused proof: 29 raw/image API tests and targeted Ruff passed; frontend63/63 passed and type/build passed. Portable transfer13/13 and Settings10/11 passed; remaining test referenced a button inside a remounted collapsed category after revision refresh. Open the category before preserving disabled/re-enable assertions; focused stale-base/corrupt-candidate journey then passed.
- 2026-10-08 final round2 reviews: scope compliance approved after reviewing guided/portable defaults, external guidance, both atomic requirements, retired records and the two disclosed baseline corrections. Separately assessed implementation quality approved: unchanged exact-byte raw output/concurrent-source and auth negatives, SourceRunner bad-recipe refusal, localized code coverage/diagnostics, safe collapsed-category reinspection and retained native/image artifact boundaries. Both criteria assessed by this agent on the same final candidate; no separate reviewers or children claimed. Complete43-file diff against257a324 reviewed; evolution refreshed before fresh configured proof. Baseline historical manual UI checks are unchanged; current guidance screenshot and automated four-locale/role/mobile proof provide candidate-specific presentation evidence.

- 2026-10-08 correction round3: full Python and Ruff pass. Full browser suite exposes the same doubled-CRLF fixture construction in exact TOML import: five valid-file journeys return config_invalid. Normalize checkout line endings before intentional CRLF conversion in import.spec.ts, retaining exact copied-source and failed/mismatched/stale-import boundaries. This extends the disclosed Windows fixture correction by one file;44 candidate files remain within45 bound. Verdicts cleared; focused import and complete final proof follow.

- 2026-10-08 correction round3 focused proof: strict attempt2 Python and Ruff succeeded; frontend143 passed/7 failed. Five import fixture failures corrected as above. DEVIATION validate: two baseline Jobs expectations referenced pre-existing removed inline technical evidence and omitted the existing Executor configuration tab. Corrected navigation/state assertions against base257a324 and retained corrupt timestamp rejection; no Summary behavior changed. Focused import/Jobs proof12/12 passed.45 candidate Git files remain within bound; delivery helpers are generated handoff material.
- 2026-10-08 final round3 reviews: specification compliance independently assessed approved against Frame/design, all selected requirements including exact import and scoped prerequisite presentation, preserved native/recipe/runtime/config/history contracts and four disclosed baseline fixture/catalog/navigation corrections. Separate implementation-quality assessment approved on the same final tree: authorization before retired mutation refusal, secret and dedicated endpoint exceptions, strict corrupt legacy reader, no queued runtime invocation, Dev path omission, invalid recipe image withholding, unchanged byte-copy/corrupt timestamp negatives, responsive four-locale guidance. Both assessments by this agent; no separate reviewers claimed. Complete Git diff against257a324 supplements late anchor and covers commands.py plus all45 candidate paths. Evolution refreshed at05:17Z (29 observed paths including generated helpers); source edits complete before fresh final configured proof.

- 2026-10-08 final validation: `python .agentic/aegis.py check --task TASK-d5f346ed --strict --run` exit0; configured full pytest success363.7s, Ruff success0.1s, npm validate (helper tests, type/build and complete offline Chromium) success413.2s. Focused corrected import/Jobs12/12; earlier Python Windows symlink-privilege skips retained and Linux/full-job acceptance not inferred. Inspected final desktop/390px guidance screenshots: readable spacing, wrapped code/path and no horizontal clipping.43 candidate non-journal path SHA256 values match before/after final proof; actual complete candidate is44 Git paths, correcting the earlier45 estimate and remaining below45 bound.12 advisory warnings accepted: two unchanged obsolete asset links, tracked historical sidecars, six unrelated historical journal-header findings, fake offline test-only password literal, and two generated delivery helpers in the designated delivery area.25 historical manual reminders are unchanged and are not claimed newly accepted; in-scope role/locale/mobile/API boundaries are covered above. No candidate test failure remains.
- 2026-10-08 delivery presentation: unchanged44-path candidate is external notice/guarded boundaries, guided simplification, contract tests, operator/component/current-state documentation and requirement retirement. No children. Exclusions remain profile/image/schema/history changes, model/forge operations and remote Git publication. Deviation recap: late anchor supplemented by complete base diff; bounded baseline CRLF fixtures, error catalog and obsolete navigation/status assertions corrected with trust negatives retained. Reuse explicit same-session implementation/local commit/DCP test-instance replacement authority; no new confirmation requested. Planned source commit, trimmed source plus newly compiled UI package, root-private consistent backup, one rollback-protected replacement and read-only LAN/browser acceptance. Generated delivery helpers compile successfully and inspect profile/config/run/pause integrity before/after; no runtime package/dependency/TLS/profile changes.

## Rulings


- RULING-001 | date=2026-10-08 | decision=Implement approved external environment proposal through local delivery and authorized DCP test replacement | reason=User explicitly accepted the detailed proposal and instructed implementation; standing same-session local delivery/deployment authority persists | source=user | supersedes=none

## Handoff

current: deliver
status: ready
next: Commit the validated candidate and perform authorized DCP replacement and read-only acceptance.
must_read: .agentic/tasks/TASK-d5f346ed.md, .agentic/steps/6_deliver.md
blockers: none

## Stage report

stage: validate
result: completed
current: deliver
changed: conditional external container instructions; removed environment controls; guarded retired mutations and queue
evidence: strict configured full pytest, Ruff and npm validation exit0; final desktop/mobile images inspected; candidate hashes unchanged
issues: twelve accepted advisory warnings; three Windows symlink-privilege skips; disclosed anchor/fixture/catalog/nav corrections
next: authorized local commit and rollback-protected DCP test replacement
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-08)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-01d189b8 - Present externally prepared executor environment guidance
  - REQ-FUNC-6b8494a7 - Keep executor environment mutations outside the web application
  - REQ-UX-1b9b5789 - Provide compact backend-aware project image flow
  - REQ-REL-2cbd8d83 - Build project images through bounded durable owned operations
  - REQ-FUNC-a6a81d86 - Define a bounded project Dockerfile artifact
  - REQ-SEC-56f5f4a9 - Apply only a current verified project image through reviewed configuration
  - REQ-FUNC-6d6843ab - Verify project image executor tools and identity
  - REQ-UX-94a97e70 - Review execution plans through project configuration
  - REQ-UX-b75e1df8 - Configure and check local execution with user-owned tooling notice
  - REQ-UX-e6ed7168 - Display localized web error messages
  - REQ-SEC-3cf6cde4 - Administrator original configuration read
  - REQ-UX-3b5b2257 - Explain exact server TOML enrollment and review
  - REQ-UX-8186eea1 - Explain scoped host prerequisites with honest severity
- deviations: 3 recorded
  - build: anchor was recorded after the first source edit rather than immediately after red; evolution will be supplemented with the complete git diff against base 257a324 so those initial paths cannot escape review. Anchor records 362 files at 2026-10-08T04:28:18Z.
  - validate: baseline raw-configuration fixture produced doubled CRLF on Windows; normalize input before intentionally forming CRLF. Added new external-owner error and seven existing missing localized execution/model/credential errors in four locales, preserving diagnostics/generic fallback. Two additional candidate files are included to make complete proof possible, within45-file bound. Exact-byte/concurrent-write and catalog contracts retained; no runtime validation weakened.
  - validate: two baseline Jobs expectations referenced pre-existing removed inline technical evidence and omitted the existing Executor configuration tab. Corrected navigation/state assertions against base257a324 and retained corrupt timestamp rejection; no Summary behavior changed. Focused import/Jobs proof12/12 passed.45 candidate Git files remain within bound; delivery helpers are generated handoff material.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 257a324: 44 file(s) changed, 884 line(s) added
- checks: errors=0 warnings=11 notes=25
- checklist: 3/6 done; open: journal and report included in delivery commit; agreed DCP replacement and read-only acceptance delivered; close-out committed after outcome succeeds
