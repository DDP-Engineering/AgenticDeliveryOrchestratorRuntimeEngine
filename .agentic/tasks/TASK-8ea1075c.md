<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-8ea1075c - Browse and control project tickets from the Jobs tab

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-6e125b14, REQ-FUNC-ba4eee4e, REQ-FUNC-2c8ef18a, REQ-FUNC-0035511a, REQ-UX-3d4a059e, REQ-SEC-f29221e6, REQ-UX-b309b302, REQ-UX-4200375b
parent:
branch: task/adore-web-interface
base: 4990e74a21723911cb4d9aad28d7b05954cf2d82
opened: 2026-10-10

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: The project Jobs tab only offers a ticket-number box; operators cannot see the forge backlog, its eligibility, description or comments before starting work (STATED: "se pot citi toate tichetele ... listate într-un tabel ... user-ul să selecteze ... citire să se facă când apasă un buton").
Desired outcome: Jobs tab with sub-tabs Tickets (default; read open tickets on button press, table, Start/Stop per ticket, expandable description + comments) and Jobs (current job search/filters/table/detail) (STATED + user answers: all open tickets with eligibility; Stop = cancel + remove ready label; Tickets default).
Actors: administrator and assigned developer (same roles as start/cancel); project forge (GitLab/GitHub/Gitea CLIs with project credentials); worker (executes start/cancel).
Primary scenario: user opens hub > Jobs -> Tickets sub-tab -> Read tickets -> ADORE reads open issues via forge CLI (bounded) -> table with eligibility/job state -> expand -> comments read on demand -> Start queues `start` operation / Stop queues `cancel` for the unfinished job and removes the ready label.
Examples: aegis ticket #12 labelled agent-ready + P2 -> "Ready to start", Start enabled; ticket #13 without agent-ready -> "Missing label agent-ready", Start disabled; ticket with running job -> job lifecycle shown, Stop enabled.
Counterexamples: Read tickets is never automatic (no polling of the forge); archived project shows tickets but no Start/Stop; forge text with <script> renders literally.
In scope: forge `list_open` in 3 adapters; shared eligibility function used by orchestrator and web; web endpoints GET tickets, GET ticket comments, POST ticket stop; TicketWorkspace UI with sub-tabs, four locales; route `?view=jobs`; e2e fixture forge answers; docs.
Out of scope: editing tickets other than removing the ready label on Stop; closing issues; markdown rendering; global Jobs page changes; full suite (STATED: at the end of refinements).
Constraints: forge output is a trust boundary - typed errors and negative tests (OBSERVED AGENTS.md Testing Rules); web probe runner pattern with deadlines (OBSERVED app.py:561-621); credentials via project_runner (OBSERVED repository_auth.py:335); start/cancel authorization and archived 409 (OBSERVED app.py:4220-4257); claim replaces ready with working (OBSERVED orchestrator.py:842).
Success signals: Tickets table from fixture forge in e2e; Start/Stop behave per eligibility; comments expand; malformed forge output yields typed errors; DCP shows real aegis tickets.
Evidence: OBSERVED forge Ticket/Comment base.py:53,70; list_ready per adapter gitlab.py:85, github.py:74, gitea.py:102; no unlabelled list exists; mappers raise KeyError/ValueError on malformed records (gitlab.py:423, github.py:461, gitea.py:542); eligibility rules orchestrator.py:740-781; derive_run_id state.py:393; e2e projects use gitlab `offline/<name>` (e2e/server.py:86).
Assumptions: 500 tickets is a sufficient bound (larger backlogs flagged as truncated); description travels with the list, comments load per ticket; manual start-by-number remains available in the Tickets sub-tab as a fallback.
Unknowns: none blocking. Decision-blocking questions: resolved by the user's answers.
Proposed behaviors: B1 list API (REQ-FUNC-ba4eee4e); B2 comments API (REQ-FUNC-2c8ef18a); B3 stop API (REQ-FUNC-0035511a); B4 sub-tab UI (REQ-UX-3d4a059e, revises REQ-UX-b309b302 placement, route spec REQ-UX-4200375b); B5 inert text (REQ-SEC-f29221e6).
Path and reason: full - new API, forge adapter capability, UI and security behavior.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| backlog visible | B1 open tickets + eligibility + job state | REQ-FUNC-ba4eee4e | admin/dev list | unassigned 404, CLI fail 503, malformed 502, >500 truncated | pytest forge + web | D1, D2, D3 |
| discussion visible | B2 comments on demand | REQ-FUNC-2c8ef18a | ordered human comments | missing 404, fail 503/502 | pytest web | D3 |
| control work | B3 stop = cancel + remove ready | REQ-FUNC-0035511a | job cancel + label removal + audit | archived 409, csrf 403, label failure reported after queued cancel | pytest web | D3 |
| UI | B4 sub-tabs, read button, table, Start/Stop, expand | REQ-UX-3d4a059e, REQ-UX-b309b302, spec REQ-UX-4200375b | e2e tickets flow | no read before click; ineligible Start disabled | e2e + routes unit | D4, D5 |
| safety | B5 inert ticket text, safe links | REQ-SEC-f29221e6 | literal markup | javascript: link not rendered | e2e | D4 |

## Design

- D1 forge (REQ-FUNC-ba4eee4e): `ForgeAdapter.list_open(limit)` in base + GitLab (`glab issue list --state opened` paged), GitHub (`gh issue list --state open --limit N`), Gitea (`tea api ... state=open&type=issues` paged). Records are mapped with the existing `_to_ticket`; KeyError/ValueError/TypeError become `ForgeError("malformed issue record")`. Returns at most `limit`.
- D2 shared eligibility (REQ-FUNC-ba4eee4e): new `adore/selection.py` `ineligibility(ticket, config, has_run) -> str | None` returning the first unmet rule (`not_open`, `missing_ready_label`, `held`, `excluded`, `has_job`, `missing_priority_label`, `missing_acceptance_criteria`). `Orchestrator._select` uses it (behavior-preserving refactor; `_ready` delegates).
- D3 web (`adore/web/tickets.py` helpers + routes in app.py): GET `/api/v1/projects/{name}/tickets` (principal + project access), GET `/api/v1/projects/{name}/tickets/{iid}/comments`, POST `/api/v1/projects/{name}/tickets/{iid}/stop` (mutation; idempotency_key; archived 409). Forge built with `build_forge(kind, repo, project_runner(profile_dir, config, bounded probe runner))` using the readiness deadline pattern. Errors: RepositoryAuthError -> 503 exc.code; ForgeError on CLI -> 503 `forge_read_failed` / `forge_write_failed`; malformed -> 502 `forge_response_invalid`. Stop: enqueue `cancel` for the unfinished run (derive_run_id; terminal/handoff-pending skipped) first, then remove the ready label if present; audit `ticket-stopped` with outcomes; response `{cancel_operation_id, ready_label: "removed"|"absent"|"failed", ready_label_error}`.
- D4 UI: new `TicketWorkspace.tsx` + `ticketCopy.ts` (en/ro/fr/de). Read button -> GET tickets; table columns #, title (safe http(s) link, rel noopener noreferrer), labels, status (eligibility text or job lifecycle), actions Start (startable && !archived; POST operations/start), Stop (unfinished job or ready label present; POST stop), Details toggle -> description (pre-wrap text) + comments (GET on first expand). Manual start-by-number form kept in the sub-tab. All forge strings rendered as React text (REQ-SEC-f29221e6).
- D5 hub/routes (REQ-UX-3d4a059e, REQ-UX-4200375b): Jobs tab shows sub-tabs Tickets|Jobs; `/projects/<id>/jobs` = Tickets, `?view=jobs` = Jobs list, `?run=` = Jobs with detail. JobWorkspace gets `startForm={false}` in the Jobs sub-tab.
- Compatibility: no schema/state change; orchestrator selection unchanged (refactor only). Security: read endpoints expose ticket text only to users with project access; forge writes limited to removing the configured ready label on explicit Stop.
- Test seams: tests/test_forge.py (list_open x3 + malformed), tests/test_selection.py (rules), existing orchestrator tests, tests/test_web_tickets.py (endpoints), web/tests/routes.test.mjs, web/e2e/tickets.spec.ts with fixture forge in e2e/server.py.
- Expected files: adore/forge/{base,gitlab,github,gitea}.py, adore/selection.py, adore/orchestrator.py, adore/web/{app,tickets}.py, tests/{test_forge,test_selection,test_web_tickets}.py, web/src/{App.tsx,TicketWorkspace.tsx,ticketCopy.ts,JobWorkspace.tsx,routes.ts,styles.css}, web/tests/routes.test.mjs, web/e2e/{tickets.spec.ts,server.py}, docs.
- Risks: forge CLI differences (GitLab state default) - state re-checked by eligibility; large backlogs - bounded; rate limits - reads only on explicit click.

## Log

- 2026-10-11 frame: scope accepted via user answers (all open tickets with eligibility; Stop = cancel + remove ready label; Tickets sub-tab default; read on button press); autopilot under implement request; full path (new API, forge capability, UI, security); full suite deferred by user.
- 2026-10-11 specify: 5 created (REQ-FUNC-ba4eee4e, REQ-FUNC-2c8ef18a, REQ-FUNC-0035511a, REQ-UX-3d4a059e, REQ-SEC-f29221e6); REQ-UX-b309b302 and spec REQ-UX-4200375b revised in build with the sub-tab URL; 0 retired.
- 2026-10-11 design: see ## Design D1-D5.
- 2026-10-11 build red: REQ-FUNC-ba4eee4e (forge) command=`.venv/Scripts/python.exe -m pytest -q tests/test_forge.py -k list_open` (04_Software); exit=1; expected missing behavior=adapters have no list_open (AttributeError), so open listing, bounding and malformed-record rejection are absent.
- 2026-10-11 build green: REQ-FUNC-ba4eee4e forge `.venv/Scripts/python.exe -m pytest -q tests/test_forge.py` exit=0 (65 passed incl. 8 new list_open tests).
- 2026-10-11 build red: REQ-FUNC-ba4eee4e eligibility command=`.venv/Scripts/python.exe -m pytest -q tests/test_selection.py` exit=2; expected missing behavior=no shared `adore.selection` module. Green after adding it and refactoring Orchestrator._select: test_selection 9 passed, tests/test_orchestrator.py 107 passed, selection/pickup-related tests 175 passed.
- 2026-10-11 build red: REQ-FUNC-ba4eee4e, REQ-FUNC-2c8ef18a, REQ-FUNC-0035511a command=`.venv/Scripts/python.exe -m pytest -q tests/test_web_tickets.py` exit=1 (15 failed); expected missing behavior=ticket list, comments and stop endpoints return 404 not_found.
- 2026-10-11 build green: REQ-FUNC-ba4eee4e, REQ-FUNC-2c8ef18a, REQ-FUNC-0035511a `.venv/Scripts/python.exe -m pytest -q tests/test_web_tickets.py tests/test_forge.py tests/test_selection.py` exit=0 (89 passed); related web suites test_web_commands/test_repository_connection/test_web_jobs 156 passed; `ruff check adore tests` clean. Added `ForgeResponseError` (ForgeError subclass) so malformed forge output maps to 502 while CLI failures map to 503; audit detail is redacted by the store, so stop evidence is asserted through structured resource_id/operation_id/result.
- 2026-10-11 build red: REQ-UX-3d4a059e, REQ-SEC-f29221e6, REQ-UX-4200375b command=`node --test tests/routes.test.mjs` exit=1 (view=jobs route unknown; green after routes.ts change, 13 pass) and `npx playwright test e2e/tickets.spec.ts` after `npm run build:e2e` exit=1; expected missing behavior=no Tickets/Jobs sub-tabs in the project Jobs tab.
- 2026-10-11 build green: REQ-UX-3d4a059e, REQ-SEC-f29221e6, REQ-UX-b309b302, REQ-UX-4200375b `npx tsc -b` clean; `node --test tests/routes.test.mjs tests/jobs.test.mjs` 13 pass; `npm run build:e2e` + `npx playwright test e2e/tickets.spec.ts e2e/jobs.spec.ts e2e/shell.spec.ts e2e/statistics.spec.ts e2e/dashboard.spec.ts` 68 passed and `e2e/executor-config.spec.ts e2e/settings.spec.ts` 35 passed. The first e2e run exposed the fixture repo key (configs keep the example repo) and a missing `jobsView` URL-sync dependency; both corrected. The previous hub test now selects the Jobs sub-tab before job filters.
- 2026-10-11 validate review round 1: implementation-quality FAIL (malformed ticket during stop -> 500 after queued cancel; TicketWorkspace mounted ref never set under StrictMode; corrupt run blamed on forge; forge built before cancel) and spec-compliance FAIL (missing unassigned-developer comments test; e2e did not assert the Stop cancel line). All fixed: ForgeResponseError wrapping in remove_ready_label, mounted ref, RunReadError -> 503 run_state_corrupt, lazy forge after enqueue, 4 new API tests, e2e cancel-line assertion. Not changed: per-click idempotency key (same as existing cancel), 500-ticket payload bound. Round 2: implementation-quality PASS, spec-compliance PASS (doc wording for error codes applied). Post-fix proof: ruff clean; pytest test_web_tickets/test_forge/test_selection/test_orchestrator 200 passed; tsc clean; e2e tickets+jobs 34 passed.
- 2026-10-11 deliver (DCP, outside AEGIS scope but affecting this delivery): first deploy restarted the services and exposed that the completed Ubuntu 26.04 upgrade removed Python 3.12, so the r4 runtime venv could not start (`No module named 'encodings'`); the deploy script also aborted before rollback (curl under set -e). With user approval the runtime venv was rebuilt in place on system Python 3.14.4 with the release's pinned versions (offline wheels + cffi/pydantic_core from PyPI); smoke import passed and services became healthy. The corrected round-2 package was then deployed with a fixed script: ready 200, UI 200, tickets route 401 unauthenticated, services active; backups adore.pre-8ea1075c-20261011001353 (pre-task code) and adore.pre-8ea1075c-20261011002204 (round-1 candidate), runtime.py312-broken-*.
- 2026-10-11 validate final: `python .agentic/aegis.py check --task TASK-8ea1075c --strict` (catalog only) errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by focused pytest (200), ruff, tsc, route unit tests and e2e tickets/jobs/shell/statistics/dashboard/executor-config/settings runs; ADORE now runs on Python 3.14 on DCP while local tests use 3.11 (not yet verified by a 3.14 test run).
- 2026-10-11 deliver -> build: user reviewed DCP and asked to remove the "Start a ticket by number" panel from the Tickets sub-tab as redundant (RULING-001); DCP screenshot also showed disabled Start/Stop buttons styled like enabled ones (no :disabled style for .primary/.ghost), fixed for the ticket actions in the same pass.
- 2026-10-11 build red (RULING-001): REQ-UX-3d4a059e command=`npx playwright test e2e/tickets.spec.ts` after `npm run build:e2e`; exit=1; expected missing behavior=Tickets sub-tab still renders #job-ticket-number (and disabled actions keep full opacity).
- 2026-10-11 specify (RULING-002): REQ-FUNC-6e125b14 created; REQ-FUNC-ba4eee4e and REQ-UX-3d4a059e revised for start preparation fields, Retry and visibly disabled actions. DCP check: the user's Start clicks queued no operation because all three nilo tickets were ineligible (missing agent-ready/priority, or failed job) and the cached old bundle did not dim disabled buttons.
- 2026-10-11 build red (RULING-002): REQ-FUNC-6e125b14, REQ-FUNC-ba4eee4e command=`.venv/Scripts/python.exe -m pytest -q tests/test_selection.py tests/test_web_tickets.py`; exit=1/2; expected missing behavior=no `start_preparation`, no can_start/adds_ready_label/needs_priority/priority_labels fields and no POST tickets/{iid}/start endpoint (11 failed, 19 passed).
- 2026-10-11 build green (RULING-001/002): REQ-FUNC-6e125b14, REQ-FUNC-ba4eee4e, REQ-UX-3d4a059e - ruff clean; pytest test_selection/test_web_tickets/test_forge/test_orchestrator 221 passed; tsc clean; `npx playwright test e2e/tickets.spec.ts` passed (start-by-number absent, dimmed disabled actions, Start with label confirmation and priority choice, Retry, Stop); jobs+shell+dashboard 57 passed with one order-dependent failure of "incomplete corrupt and failed job reads" that passed alone and in two full jobs.spec reruns (33/33 each). The e2e run exposed that the status column showed the first unmet rule (missing label) for a held ticket; added `start_blocker`/`blocked_by` so the table and the 409 reason name the rule labels cannot fix. Missing localized messages for forge_read_failed, forge_write_failed, forge_response_invalid and ticket_not_found (claimed present by the round-2 quality review) were added with ticket_not_startable and priority_required in four locales.
- 2026-10-11 validate review round 4: implementation-quality PASS with notes (fixed: uncertain audit on label-write/enqueue failure, same-key replay returns the original start operation, Start/Retry disabled after queuing until the next read; accepted: members may apply the ready/priority labels on Start per RULING-002; label names cannot be stored in redacted audit evidence); spec-compliance FAIL (missing API test for missing acceptance criteria; malformed ticket on Start mapped to 503; stale developer wording in Web_Interface.md) - all fixed. Proof: ruff clean; pytest 225 passed; tsc clean; tickets e2e passed.
- 2026-10-11 validate review round 5: spec-compliance PASS, implementation-quality PASS for the final candidate (start preparation, Retry, removed start-by-number, dimmed disabled actions, error messages).
- 2026-10-11 validate final: `python .agentic/aegis.py check --task TASK-8ea1075c --strict` (catalog only) errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by ruff, pytest 225 (tickets/selection/forge/orchestrator), tsc, route unit tests and e2e tickets+jobs+shell 47 passed (plus earlier dashboard/statistics/executor-config/settings runs); one order-dependent jobs.spec failure observed once and not reproduced in two full reruns. Final package deployed to DCP: ready 200, UI 200, tickets/start routes 401 unauthenticated, services active (backups adore.pre-8ea1075c-*).
- 2026-10-11 deliver: user tested the final candidate on DCP ("este ok") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-11 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings

- RULING-002 | date=2026-10-11 | decision=Start from the ticket table adds the missing ready label and, when missing, a user-chosen configured priority label in the forge before queuing the start (confirmation step); missing acceptance criteria, hold, exclude, closed state or an existing run still block; failed jobs get a Retry action using the existing retry operation | reason=User answers: "Adaugă etichetele lipsă și pornește" and "Da, Retry în tabel" after Start appeared to do nothing on ineligible tickets | source=user | supersedes=none

- RULING-001 | date=2026-10-11 | decision=The Tickets sub-tab offers starting only from the ticket table; the start-by-number form is removed there (the global Jobs page keeps its own form); replaces the Frame assumption that kept start-by-number | reason=User: the ticket-number panel is redundant with the table | source=user | supersedes=none


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-8ea1075c.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Tickets sub-tab (read on request, eligibility/blocking rule/job state, Start adding missing ready+priority labels after confirmation, Retry for failed jobs, confirmed Stop, description+comments, dimmed disabled actions, no start-by-number) and Jobs sub-tab; forge list_open; shared selection rules; ticket list/comments/start/stop API; docs
evidence: ruff clean; pytest 225 passed; tsc clean; e2e tickets+jobs+shell 47 passed; review round 5 PASS/PASS; deployed to DCP (ready 200)
issues: DEVIATION full suite deferred by user; DCP runtime on Python 3.14 (not covered by local 3.11 tests)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 5

## Delivery report (2026-10-11)

- stage: deliver; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-6e125b14 - Prepare and start a ticket from the ticket browser
  - REQ-FUNC-ba4eee4e - List a project's open tickets on demand with pickup eligibility
  - REQ-FUNC-2c8ef18a - Read one ticket's comments on demand
  - REQ-FUNC-0035511a - Stop a ticket by cancelling its job and removing its ready label
  - REQ-UX-3d4a059e - Split the project Jobs tab into Tickets and Jobs sub-tabs
  - REQ-SEC-f29221e6 - Display forge ticket text as inert plain text
  - REQ-UX-b309b302 - Show project jobs inside the project hub
  - REQ-UX-4200375b - Address every web view by a stable URL
- deviations: 2 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by focused pytest (200), ruff, tsc, route unit tests and e2e tickets/jobs/shell/statistics/dashboard/executor-config/settings runs; ADORE now runs on Python 3.14 on DCP while local tests use 3.11 (not yet verified by a 3.14 test run).
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by ruff, pytest 225 (tickets/selection/forge/orchestrator), tsc, route unit tests and e2e tickets+jobs+shell 47 passed (plus earlier dashboard/statistics/executor-config/settings runs); one order-dependent jobs.spec failure observed once and not reproduced in two full reruns. Final package deployed to DCP: ready 200, UI 200, tickets/start routes 401 unauthenticated, services active (backups adore.pre-8ea1075c-*).
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=5
- diff vs task base 4990e74: 42 file(s) changed, 2740 line(s) added
- checks: errors=0 warnings=15 notes=23
- checklist: 3/6 done; open: journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
