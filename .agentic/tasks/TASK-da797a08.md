<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-da797a08 - Job details operational evidence and safe executor diagnostics (#35)

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-cceb7c05, REQ-UX-c50979cf, REQ-FUNC-e4bc1830, REQ-SEC-97e45ffb, REQ-SEC-e9720eb9, REQ-UX-72873d9f, REQ-REL-3c89dba2, REQ-UX-ce64af73
parent:
branch: task/adore-web-interface
base: 2d62e00c9d26af8727410569dae218858f6b6a8a
opened: 2026-11-05

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

Problem: STATED issue #35 reports misleading normal-state copy, hidden failures, missing stages/seconds, executor evidence, flattened questions and intermittent consumption errors.
Desired outcome: STATED implement all six acceptance criteria in four locales with trustworthy evidence.
Actors: STATED authorized admins and project developers.
Primary scenario: STATED inspect working/parked/failed jobs without starting real execution.
Examples: STATED working with one failed build attempt; a parked Markdown question; consumption returning 503.
Counterexamples: STATED corrupt sources remain errors; no transcript, credentials or developer financial data exposed.
In scope: STATED job presentation, safe latest executor diagnostics, consumption investigation/fix and affected documentation.
Out of scope: STATED other tickets, planning, live acceptance, service/data changes, migrations, push and merge.
Constraints: STATED same branch, autopilot, local signed-off commit; targeted tests only. Run bounds: 3 hours, 45 files, 3 correction rounds, no paid/model calls.
Success signals: STATED all six issue criteria pass focused offline public-boundary checks.
Evidence: OBSERVED tea issues --comments --login ddp --repo dpasare/AgenticDeliveryOrchestratorRuntimeEngine 35; JobWorkspace.tsx, jobs.py, analytics.py, store.py and launcher.py.
Assumptions: INFERRED operational diagnostics can omit arbitrary transcripts and classify unsafe stderr while preserving failure categories.
Unknowns: UNKNOWN historical live 503 cause; controlled concurrent-source reproducer will establish the code defect, not claim historical certainty.
Decision-blocking questions: None.
Proposed behaviors: None pending.
Path and reason:
| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | new diagnostic viewer |
| no new interface or data format | no | scoped read endpoint |
| no new dependency | yes | reuse existing renderer |
| an existing requirement already covers behavior | unknown | focused additions |
| no security or data-handling change | no | operational evidence projection |

## Requirement coverage

| Requirement | Behavior | Design | Verification |
|---|---|---|---|
| REQ-UX-cceb7c05 | While a job is working, parked for clarification or failed, the job detail shall explain its actor, location and conditional next step in English, French, German and Romanian without presenting normal activity as missing evidence. | Scoped job projection / existing renderer / transactional cursor | Browser fixtures inspect normal working, parked and failed cards in four locales, including missing parked question evidence. |
| REQ-UX-c50979cf | While the current job stage has failed attempts, the status card shall display their saved count independently of the lifecycle label. | Scoped job projection / existing renderer / transactional cursor | Browser working fixture with one failed attempt shows the count outside Technical details; zero failures shows no warning. |
| REQ-FUNC-e4bc1830 | When displaying a job timeline, the interface shall show second-precision timestamps and the stage explicitly recorded by that event in stage, stage context or current transition destination, leaving unrelated events unassigned. | Scoped job projection / existing renderer / transactional cursor | API fixtures exercise stage/context/current and corrupt stage values; browser checks seconds and unassigned events. |
| REQ-SEC-97e45ffb | When an authorized user requests the latest recorded executor archive, the service shall return a bounded operational stdout/stderr projection that excludes transcripts, reasoning, configuration, credentials and financial amounts. | Scoped job projection / existing renderer / transactional cursor | Offline API creates Pi archive with protocol statuses, errors, thinking, secrets and cost; response exposes only closed diagnostic facts, bounded to existing stream limits. |
| REQ-SEC-e9720eb9 | If executor evidence identity, links, path, file type, size or contents are unsafe or corrupt, the service shall refuse the evidence with a typed safe error. | Scoped job projection / existing renderer / transactional cursor | API tests foreign paths, links, missing/corrupt/oversized archive and revoked project access; no source bytes escape. |
| REQ-UX-72873d9f | When displaying an observed agent clarification, the job detail shall render safe Markdown with literal HTML, permitted links and images represented without automatic loading. | Scoped job projection / existing renderer / transactional cursor | Browser question includes heading/list/code, unsafe link, image and HTML; inspect semantic markup and no resource request. |
| REQ-REL-3c89dba2 | When a consumption snapshot precedes a concurrently projected longer journal, the projection shall preserve that snapshot only after verifying the current source and saved cursor prefix without rolling back the cursor. | Scoped job projection / existing renderer / transactional cursor | Public reconcile_usage test projects long then short source; verify old totals and durable cursor, and reject changed or truncated current prefixes. |
| REQ-UX-ce64af73 | When job consumption cannot be loaded, the interface shall provide a visible localized reload action beside the error. | Scoped job projection / existing renderer / transactional cursor | Browser intercepts 503, clicks visible reload, then observes actual fixture consumption without losing job actions. |

## Design

### Approach
REQ-UX-cceb7c05/c50979cf/ce64af73: locale-specific normal-state guidance, explicit current-stage failure count and consumption reload control. Preserve existing conditional forge actions and recovery.
REQ-FUNC-e4bc1830: prefer explicit stage; interpret context only on usage/executor-artifacts, current only on transitions. Do not infer past stages from current run state. Display seconds.
REQ-UX-72873d9f: reuse ForgeMarkdown and ticket locale labels for observed questions; share forge-scroll styles with job questions, including 390px dark-theme checks.
REQ-SEC-97e45ffb/e9720eb9: capture concrete canonical missing-module and pytest-result diagnostics on the host from Pi error fields, failed tool results and stderr, after credential redaction. Exclude assistant content, reasoning, prompts, arguments and arbitrary private text. Carry optional diagnostics through GateRun; the conductor writes a host-owned schema-1 snapshot outside IO and binds its digest/run/attempt/context in executor-artifacts. The lazy scoped endpoint reads only that snapshot with exact identity, schema, canonical grammar, regular-file, link, size and stability checks. Every completed attempt records an evidence marker, including absent archives/capture, so older output never appears as latest. Missing provenance is explicit; raw IO is never read. Recognized token-shaped module identifiers are suppressed; diagnostic ring writes and snapshots use the existing evidence lock. Each diagnostic ring keeps at most 500 records and 64 KiB.
REQ-REL-3c89dba2: use an optional strict selected-run reread without rescanning other jobs inside the transaction; reproduce older snapshot after newer SQLite cursor; accept only verified immutable prefixes of the fresh strict source, preserve cursor and projection; reject changed or truncated prefixes. No blind retry or tolerant reader.

### Interfaces and data
New authenticated GET /api/v1/jobs/{project_id}/{run_id}/executor-output returns project/run identity, availability missing/observed, normalized stdout/stderr, exit_code, timed_out; no filesystem paths. A unique schema-1 capture file binds run/attempt/context and canonical streams with exit/timeout; its digest reference is journaled. Existing project authorization before reads and fresh grant recheck after. Invalid sources raise JobReadError; read caps use existing Pi stdout/stderr retention caps and 64 KiB projected output. No existing stored format changes or migrations.

### Files and test seams
executor/diagnostics.py plus base/launcher/pi_rpc capture, orchestrator host snapshot; jobs.py timeline projection; executor_evidence.py scoped snapshot read; app.py endpoint and strict fresh journal callback; store.py cursor race. JobWorkspace/jobCopy/jobModel and existing safe Markdown renderer. Public API tests in test_web_jobs, projection tests in test_web_metrics, targeted jobs helper/browser tests. Component docs, help four locales, release notes, changelog and AEGIS knowledge updated together.

### Risks and open decisions
Historical 503 remains UNKNOWN; controlled race proof establishes a preventable false-corruption path, not the historical root cause. Stable malformed JSON remains refused. Host-side diagnostic normalization deliberately withholds arbitrary lines to enforce privacy for both roles. No live resource/model acceptance.

### Requirement map
All eight requirements map to the approach paragraphs above and focused public API/helper/browser assertions. No new runtime dependency or state schema.
Diagrams: [diagram_TASK-da797a08.md](diagram_TASK-da797a08.md)


## Log

- 2026-11-05 frame: journal opened
- 2026-11-05 frame: completed; next specify - Autopilot frame recorded from complete issue and user constraints (7 Done checklist item(s) left unticked)
- 2026-11-05 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-05 design: completed; next build (6 Done checklist item(s) left unticked)
- 2026-11-05 build: red: targeted jobs/metrics pytest exit 1; endpoint absent (404), context/current stages missing, and long-then-short concurrent snapshot raises WebStoreError (REQ-SEC-97e45ffb/e9720eb9, REQ-FUNC-e4bc1830, REQ-REL-3c89dba2). Fixture grant corrected separately.
- 2026-11-05 build: red: node --test 04_Software/web/tests/jobs.test.mjs exit 1; missing lifecycle guidance and strict executor projection reader (REQ-UX-cceb7c05/c50979cf, REQ-SEC-97e45ffb/e9720eb9).
- 2026-11-05 build: red: focused Playwright issue35 exit 1; current-stage failure absent from normal Working card. Candidate browser assertions also cover seconds, consumption reload and safe Markdown (REQ-UX-c50979cf/cceb7c05/ce64af73/72873d9f).
- 2026-11-05 build: Design correction from coordinator review: retain concrete normalized operational diagnostics captured host-side during Pi RPC; bind a host-owned snapshot to launch/journal digest. Existing archives without provenance are unavailable and never read raw. Scope adds executor base/launcher/pi_rpc, diagnostics module, orchestrator journal binding and shared Markdown scroll CSS; no schema migration or live work.
- 2026-11-05 build: red: pytest test_pi_rpc.py -k concrete_operational exit 1; missing host-side diagnostics. Concrete missing yaml dependency and pytest counts must survive while prompts/thinking/scripts/configuration/credentials do not.
- 2026-11-05 build: green: focused public jobs evidence tests exit 0 (9); RPC/retry/HTTP interleaving/stage boundary tests exit 0 (6); node jobs helpers exit 0 (11); focused issue35 browser journeys exit 0 (2), including 390px dark long code/table scrolling and four locales. Screenshot inspected; private streams stay excluded.
- 2026-11-05 build: release-notes: updated (merged Jobs note in four locales; category already at ten entries)
- 2026-11-05 build: help: updated (Jobs topic in en/fr/de/ro, same structure; focused help tests pass)
- 2026-11-05 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-05 validate: Review round 1: parked actor fallback unknown; completed attempt without archives could retain older evidence; fresh usage callback rescans full inventory; diagnostics ring lacks locked snapshot; recognized token-shaped module name can pass canonical grammar. Correct all five with focused regressions.
- 2026-11-05 validate: returned to build - Independent review round 1 corrections within accepted scope
- 2026-11-05 build: red review corrections: focused RPC/retry/usage-IO pytest exit 1 (3); recognized token survives as module, missing later archive retains prior marker, two-run usage performs six state reads instead of four.
- 2026-11-05 build: red/green privacy boundary: RPC concrete diagnostic test initially exposed a count parsed from private_price text (exit 1); normalization now admits only complete test-summary lines, not arbitrary prose/config values; targeted RPC diagnostics pass.
- 2026-11-05 build: Verification correction: an overlapping runner startup refused occupied 18765 but removed the first runner's trace directory, producing ENOENT rather than a product assertion failure. Both invocations ended; rerun browser proof strictly serially. Acceptance listener 18769 untouched.
- 2026-11-05 build: Focused review corrections: 17 backend tests and 31 jobs/help/ForgeMarkdown helpers pass; delayed-reader, token/config-as-module, private financial prose, per-run IO count, latest-missing marker and snapshot identity/schema/content cases covered. Browser regression subset passed six cases; mobile assertion now queries the current two scroll regions atomically because detail refresh replaces DOM nodes, retaining the same overflow oracle.
- 2026-11-05 build: green review correction: isolated Playwright issue35 normal lifecycle/390px dark local scrolling exit 0 (1 test, 57.8s), after six other focused browser regressions passed. No browser runner remains active.
- 2026-11-05 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-05 validate: DEVIATION validate: full Python/web suites and check --strict --run are prohibited by the standing user instruction; final proof uses only directly affected targeted files/selectors, scoped lint, helper tests, isolated typecheck/Vite build and seven serial browser journeys. Live acceptance and historical 503 attribution remain unverified; no blind retries or fabricated evidence.
- 2026-11-05 validate: final: cwd 04_Software: .venv/Scripts/python.exe -m pytest -q tests/test_web_jobs.py tests/test_web_metrics.py tests/test_web_scoped_metrics.py tests/test_pi_rpc.py tests/test_executor.py tests/test_drift_recovery.py::test_deleted_identity_gets_fresh_usage_and_terminal_metrics tests/test_drift_recovery.py::test_deleted_source_and_projection_reset_share_transaction tests/test_drift_recovery.py::test_projection_reset_rolls_back_when_source_removal_fails --tb=short exit 0 (261 passed, existing Starlette/httpx warning); pytest -q tests/test_orchestrator.py -k "clean_full_and_quick_paths or launch_telemetry or no_stage_progress_evidence or clarification_resume_preserves_active_work_consumed" --tb=short exit 0 (15 passed); node --test web/tests/jobs.test.mjs web/tests/help.test.mjs web/tests/forgeMarkdown.test.mjs exit 0 (31); scoped Ruff 13 Python paths exit 0; git diff --check exit 0; check_release_notes.py --since 2d62e00c9d26af8727410569dae218858f6b6a8a exit 0; AEGIS check --task TASK-da797a08 --full exit 0 (0 errors, 33 existing advisories, 23 notes); cwd web npm run build:e2e exit 0 (both typechecks, Vite and stamp, existing chunk-size warning); playwright test e2e/jobs.spec.ts -g "issue35|all real lifecycle|clarification candidate|missing evidence|observed timeline|job budgets" exit 1 (6 passed; 11-navigation case hit 30s test deadline); after runner exit, same candidate playwright test e2e/jobs.spec.ts -g "all real lifecycle groups explain exact stage evidence and protected handoffs" --timeout=60000 exit 0 (1 passed in 17.9s; same assertions and product limits). No candidate source/docs edits after proof began.
- 2026-11-05 validate: completed; next done

## Rulings


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-da797a08.md
changed: 45 files: localized job details, host-captured diagnostics and verified usage cursor race
evidence: 276 targeted Python, 31 Node, 7 Chromium passed; Ruff, typechecks, isolated Vite build, release notes and diff checks passed
issues: Targeted offline proof only by request; exact historical 503 attribution and live acceptance remain unverified
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-05)

- stage: validate; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-cceb7c05 - Explain normal job lifecycle states
  - REQ-UX-c50979cf - Expose failed current stage attempts
  - REQ-FUNC-e4bc1830 - Project recorded event stages
  - REQ-SEC-97e45ffb - Expose bounded operational executor evidence
  - REQ-SEC-e9720eb9 - Refuse unsafe executor evidence sources
  - REQ-UX-72873d9f - Render agent clarification Markdown safely
  - REQ-REL-3c89dba2 - Preserve concurrent consumption snapshots
  - REQ-UX-ce64af73 - Provide consumption reload action
- deviations: 1 recorded
  - validate: full Python/web suites and check --strict --run are prohibited by the standing user instruction; final proof uses only directly affected targeted files/selectors, scoped lint, helper tests, isolated typecheck/Vite build and seven serial browser journeys. Live acceptance and historical 503 attribution remain unverified; no blind retries or fabricated evidence.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 2d62e00: 45 file(s) changed, 1530 line(s) added
- checks: errors=0 warnings=33 notes=23
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
