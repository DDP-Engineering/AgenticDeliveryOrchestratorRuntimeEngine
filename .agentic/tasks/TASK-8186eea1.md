<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-8186eea1 - Explain host prerequisites with honest verdicts and one timestamp

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-8186eea1
parent:
branch: task/adore-web-interface
base: 9a13fb3d47961a04832048fa4c3989b92a732c9e
opened: 2026-10-06

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged
- [x] evidence, concrete diff, exclusions and deviation presented
- [x] standing human delivery authority recorded
- [x] journal/report committed and product pushed
- [x] exact product deployed with backup and service/assets/HTTP verification
- [x] close-out recorded after successful deployment

## Frame

Problem: STATED duplicate timestamps and unexplained host-check results confuse novice users.
Desired outcome: STATED one checked-at line, comprehensible purposes, severity and next actions.
Actors: Administrator explicitly checks; authorized project readers see stored status.
Primary scenario: Summary check -> scoped API evidence -> clear verdict and seven explained rows.
Examples: OBSERVED forge_auth=false is a failed sign-in; Pi unsupported model probe is informational.
Counterexamples: A present Git executable does not prove push access; available Pi CLI does not prove a working model session.
In scope: Check presentation, response validation, localization, targeted offline tests, docs, normal commit/push and existing DCP deployment.
Out of scope: Fix credentials, run real probes/jobs, change backend check semantics, epic continuation, full suite, paid agents.
Constraints: STATED targeted proof only; four hours, three fix cycles, twenty authored files; preserve RBAC/CSRF and secrets.
Success signals: One metadata line; text plus color status; each check explains purpose and actionable failures; unavailable model probe is distinct from failure.
Evidence: OBSERVED app.py _probe_setup/_readiness_view and endpoint_probe.py only support configured OpenCode endpoint probing; App.tsx duplicates metadata.
Assumptions: INFERRED current interactive correction/deploy authority remains applicable.
Unknowns: Actual machine credentials and live model readiness; no check is run by this task.
Decision-blocking questions: None.
Proposed behaviors: Separate passed/failed/not-checked/unknown evidence; overall attention on any failure, partial on unknown runtime, otherwise performed checks passed with explicit coverage limit.
Path and reason: Full; new externally observable explanatory behavior. No new API, dependency or credential handling.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design |
|---|---|---|---|---|---|---|
| Clear evidence | Explained, scoped readiness report | REQ-UX-8186eea1 | passed checks | failed auth, unknown runtime, unsupported model, corrupt/wrong-scope response | offline browser tests | dedicated presentation |

## Design

App owns explicit Admin/CSRF request and stale-request suppression. A dedicated ReadinessEvidence component owns localized descriptions and textual/color status. A pure readiness reader validates the API status contract, identity, timestamp, exact check keys and allowed result types before evidence is shown. The existing backend owns probe execution and persistence. One metadata line prefers fresh checked_at/revision, otherwise persisted evidence. Fresh verdict also updates the verification tile; no stale result claims. Model unsupported/not-configured are informational omissions; other unsuccessful endpoint probes are failures. Coverage text explains this checks prerequisites, not an end-to-end job or Git push permission. Four locales and responsive row stacking preserve access. No architecture boundary changes.

## Log

- 2026-10-06 frame: Scope accepted under existing interactive implementation/deploy authority; full path, no child agents.
- 2026-10-06 specify: Created one readiness-presentation requirement covering clear/failed/partial/corrupt evidence; existing hub contract retained.
- 2026-10-06 design: Audited backend semantics and selected scoped reader plus explanatory presentation; no real probe execution or credential edits.

- 2026-10-06 build: Red browser test failed on missing Performed checks passed verdict (one test, exit 1), then anchored candidate before source edits.

- 2026-10-06 build: Added explained four-locale evidence and strict response reader; three reader tests pass. Browser passed/partial/corrupt/wrong-project journeys pass; corrected an ambiguous Git/GitHub test locator. Single metadata line prefers fresh evidence.

- 2026-10-06 validate round 1: Found API response differs from persisted sidecar: it omits schema and adds status. Corrected reader/fixtures to real status contract and added an unmocked offline API browser journey; bounded fix cycle 1.

- 2026-10-06 final focused proof: node --test web/tests/readiness.test.mjs exit0/3tests; UI and E2E typecheck plus isolated build exit0; npx playwright test e2e/jobs.spec.ts --grep "host prerequisite|hub separates pickup" --workers=1 exit0/10passed27.8s. Covers passed/partial/failed/unsupported/unconfigured evidence, corruption/wrong project, explicit CSRF check, real offline API response, four locales, dark theme and 390px layout. Production build exit0, index-B0e_Fe9p.js/index-ONex4OQt.css. No backend product changes or real CLI/forge/container probes.
- 2026-10-06 visual review: desktop light and dark screenshots inspected; one metadata line, clear verdict and separated seven result rows with purposes and corrective instructions; colors/text legible and existing two major panels retained. Current project/environment responsibilities and architecture unchanged; component documentation names reader/presentation seams.
- 2026-10-06 DEVIATION validate: User forbids full suite before iterative deployment; final check--run replaced with focused browser/model/typecheck/build plus strict catalog. Does not establish full application regression coverage. Vite's existing large-bundle advisory retained.
- 2026-10-06 review round 2: Specification compliance approved; implementation quality approved through separate same-agent review lenses, not independent agents. Corrected transport mismatch from round1; real offline API test passes. Scoped evidence fails closed, model coverage honest, Admin/CSRF unchanged, no credentials or acceptance fabricated.

- 2026-10-06 final catalog: evolution 15 nonworkflow changed paths reviewed; strict catalog exit0,0errors6warnings25notes,strictpassed,run[]. Baseline tracked sidecars and four legacy journal findings retained; generated large JS scan limitation supplemented by reviewed source; no current-task catalog warning. git diff --check exit0. Final candidate SHA256 e0789be0623a719437b74d3fcdf9e6666b1c3e44b75f63b31f00eeebf8c9cb7a excluding journal, 13 authored paths plus journal/generated assets separate. No children.
- 2026-10-06 deliver: Concrete candidate, 10 browser/3 reader/typecheck/build evidence, exclusions and full-suite deviation presented. Standing human normal commit/push and existing DCP deployment authority applies. No PR/release/acceptance operations.

- 2026-10-06 delivery: Product 60e63c3fc6069bf23f5120bf1f4747670ef96c4f pushed to task/adore-web-interface; ls-remote confirms exact SHA. Deployed release /home/dpasare/apps/adore/web-ux-60e63c3, archive SHA256431d284eb226d1acf7d3ed0e4031ef5ef9acef61776bf4ed5c86feaa4573e19c. Backup /home/dpasare/apps/adore/backups/web-ux-60e63c3-20261006144632. Both services active with exact release PYTHONPATH; served JS/CSS bytes match release. SQLite schema14/integrityok/audit51. Post-deploy root200newassets,health200alive,ready200workerready,projects401authentication_required. No live readiness/executor/project actions run by this task. Full suite and human visual acceptance remain deferred; epic implementation remains stopped.
- 2026-10-06 close-out: Inventory clarification: twelve authored candidate paths plus one workflow journal, with five generated asset path changes counted separately (eighteen paths before Git rename presentation). Earlier thirteen-plus-journal wording overcounted authored inventory by one; scope is within the twenty-file bound.

## Rulings

- RULING-001 | date=2026-10-06 | decision=Proceed through scoped implementation, targeted validation, normal commit/push and existing DCP deploy without repeated checkpoints | reason=User iterative delivery authority and explicit full-suite restriction; no agents | source=user | supersedes=none

## Handoff

current: done
status: ready
next: Human live visual test.
must_read: .agentic/requirements/ux/REQ-UX-8186eea1.toml
blockers: none

## Stage report

stage: done
result: completed
current: done
changed: Clear host-check verdict, seven explained results, one timestamp and scoped response validation.
evidence: 10 browser/3 reader tests passed; builds exit0; exact60e63c3 pushed/deployed; assets/services/HTTP smoke confirmed.
issues: Full suite deferred by user.
next: Human live visual test.
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-06)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-8186eea1 - Explain scoped host prerequisites with honest severity
- deviations: 1 recorded
  - validate: User forbids full suite before iterative deployment; final check--run replaced with focused browser/model/typecheck/build plus strict catalog. Does not establish full application regression coverage. Vite's existing large-bundle advisory retained.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 9a13fb3: 18 file(s) changed, 479 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=6 notes=25
- checklist: 7/7 done
