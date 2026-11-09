<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-6be1f0bc - Manual ticket start while monitoring is paused and explicit failure reasons

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-6e125b14, REQ-FUNC-f9946b6b
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-20

## Done checklist (current stage)

- [x] Local implementation reviewed against both requirements and design.
- [x] Focused offline proof, TypeScript, Ruff and release-note checks recorded.
- [x] Component/user documentation, four-locale help and traceability updated.
- [x] Local working-tree outcome delivered; no packages, full suite, live ticket execution or publication.

## Frame

Problem: OBSERVED â€” manual Start reaches poll_once but the pause marker returns picked=null; worker discards CLI output and stores a generic rejection.
Desired outcome: STATED â€” explicit Start runs only the named ticket even while monitoring is paused, preserves pause, and shows concrete failure reasons.
Actors: Authorized assigned user, durable worker, existing CLI and conductor.
Primary scenario: Paused project -> Start IID -> normal locks/readiness/capacity/AEGIS gates -> conduct that IID; subsequent automatic poll still paused.
Examples: A ready ticket starts in pause; a held ticket or capacity limit gives a specific refusal without activating monitoring.
Counterexamples: Invalid IID, wrong ticket, revoked access, archive, held/excluded/closed ticket, missing workflow, live lock, corrupt CLI result and secret-bearing output.
In scope: Selected-ticket conductor path, bounded secret-free CLI/worker reason contract, localized operation presentation, focused offline tests and required docs.
Out of scope: Actual provider/forge execution, changing installed application or user settings, packages, full suite, merge/publication.
Constraints: STATED â€” implementations only, no package rebuild; latest user explicitly permits only targeted verification. Preserve all earlier changes. No new dependencies.
Success signals: Explicit IID runs while pause marker remains; automatic poll selects nothing; failure shows a localized safe reason; unknown/corrupt output never becomes success or raw text.
Evidence: orchestrator.py poll_once pause guard; cli.py _cmd_run nonzero when picked=null; web/commands.py captures then discards engine stdout/stderr.
Assumptions: INFERRED â€” pause governs automatic admission; manual admission retains all other existing guards and reconciliation behavior.
Unknowns: Live runtime acceptance deferred with packaging.
Decision-blocking questions: none.
Proposed behaviors: Strict positive manual IID; direct fresh ticket read with shared eligibility; structured terminal CLI result bound to IID and exit code; allowlisted reason codes only in web results.
Path and reason: full â€” changes manual admission semantics and adds a bounded CLI-to-worker result contract.
Run limits: 40 implementation/documentation/test files, 60 minutes, focused offline tests only; no external/provider calls or packages.

## Requirement coverage

- REQ-FUNC-6e125b14: paused manual admission retains ticket gates; orchestrator happy/pause preservation/negative boundary tests.
- REQ-FUNC-f9946b6b: concrete safe refusal through CLI/worker/UI; CLI and worker corrupt-output tests plus localized presentation helper test.

## Design

- REQ-FUNC-6e125b14: Bypass pause only for a validated positive explicit IID. Under the existing conductor lock, keep reconciliation, capacity and AEGIS checks; freshly get that ticket and run shared ineligibility. Never remove the pause marker or queue automatic admission.
- REQ-FUNC-f9946b6b: CLI manual runs append one bounded versioned terminal result line, with IID, exit code and allowlisted reason; no exception text or credentials. Existing human logs stay on the host. Default worker runner returns existing CommandResult, while injected integer runners remain compatible. Strictly parse the terminal result only for Start; bind to selected IID/exit, reject duplicates/unknown fields/codes/oversize/mismatches. Exit zero with invalid evidence is uncertain, not success.
- Known refusals include archive/config/engine setup, live lock, concurrency, workflow payload, ticket unavailable and each shared eligibility reason. Unexpected errors use a specific engine-fault indication directing inspection of host logs, without copying arbitrary stdout/stderr.
- Web operation result stores start:<reason>. A shared localized presentation helper resolves it in Tickets, Jobs and general operation status; old operation strings remain readable. Four locales explain manual Start independent of Monitoring and error details.
- Alternative raw stderr forwarding rejected because CLI/executor output may contain credentials; unpausing/repausing rejected because it temporarily enables automatic admission and races other processes.
- No state schema migration, API permission change, provider-specific code, new dependencies or packaging change.

## Log

- 2026-10-20 frame: Accepted explicit implementation scope, existing dirty checkout and autopilot authorization; selected full path for observable admission/protocol changes.
- 2026-10-20 specify/design: Revised existing Start and job-control requirements; recorded contract, trust boundaries and focused test seams above; entered build.
- 2026-10-20 DEVIATION validate: Full-suite final proof is replaced by focused tests and relevant static checks under the user's explicit timing constraint; packages and live execution are deferred.

- 2026-10-20 build red: REQ-FUNC-6e125b14; command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_orchestrator.py -k manual_start --tb=short --no-header`; exit=1; 9 expected failures: paused manual ticket not picked, invalid IID accepted and refusal reasons absent.

- 2026-10-20 build red: REQ-FUNC-f9946b6b; command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_commands.py::test_worker_reports_bound_manual_start_reason 04_Software/tests/test_smoke.py::test_cli_manual_start_emits_safe_terminal_reason --tb=short --no-header`; exit=1; 11 expected missing terminal-result/worker reason failures. Frontend red: `node --test 04_Software/web/tests/manualStart.test.mjs`; exit=1; missing localized result export.
- 2026-10-20 build: Implemented strict selected-ticket admission preserving pause and gates, versioned secret-free terminal CLI evidence, worker outcome binding and four-locale presentation across Tickets/Jobs/status. First focused backend run passed 23 tests (176 deselected); no full suite or package build.

- 2026-10-20 build green: Both requirements; command=`04_Software/.venv/Scripts/python.exe -m pytest -q 04_Software/tests/test_web_commands.py 04_Software/tests/test_smoke.py 04_Software/tests/test_orchestrator.py -k 'manual_start or default_worker_runner or explicit_ticket_start or public_pickup_obeys_optional or cli_run_once_reports_an_unexpected_fault or worker_heartbeat or revoked_membership or queued_command_follows_project_id or pause_is_admin_only or busy_worker or polling' --tb=short --no-header`; exit=0, 51 passed / 154 deselected. Includes paused manual admission, selected identity/readiness, closed failure reasons, default runner, timeout uncertainty and access/cancellation/polling regressions. Existing Starlette/httpx deprecation warning remains outside this change.
- 2026-10-20 frontend proof: `node node_modules/typescript/bin/tsc -p tsconfig.json --noEmit` exit=0; `node --test tests/manualStart.test.mjs tests/help.test.mjs` exit=0, 14 passed. Four locales preserve help structure/links and unknown/prototype reason keys use safe fallback. No Vite or package build.
- 2026-10-20 release-notes: added (four-locale Tickets fix under Unreleased; safe manual Start and refusal feedback).
- 2026-10-20 help: updated (all Tickets locales; paused manual admission, automatic-pickup distinction and failed-result recovery).
- 2026-10-20 build to validate: Affected component/user docs and knowledge reconciled; project context updated, environment/setup unchanged. Scope remains local implementation only with user-authorized focused proof replacing the full suite.

- 2026-10-20 validation review round 1: Specification question — does manual Start select only the requested eligible ticket while preserving paused automatic admission and every other conductor/permission/publication boundary? Verdict approved after inspection of explicit IID validation, fresh ticket binding, shared eligibility, lock/payload/capacity and unchanged pause persistence. Implementation-quality question — do result parsing, worker compatibility and localized presentation fail safely without secrets or unrequested effects? Verdict approved after separate inspection of exact schema/IID/exit/code binding, duplicate/size/unknown rejection, timeout uncertainty, integer-runner compatibility, own-property locale fallback and focused regression results. These are two question-scoped self-reviews, not external reviewers.
- 2026-10-20 advisory inspection: No catalog errors; pre-existing repository warnings concern retired tool/asset paths, older journals, tracked sidecars and earlier delivery artifacts. Current help/test traceability and review-record gaps were corrected; unrelated files were preserved. Full --run proof is deliberately omitted under RULING-001.

- 2026-10-20 final validation: 51 selected backend tests passed (154 deselected), 14 frontend/help tests passed, TypeScript no-emit and changed-file Ruff passed, release-note check passed. Scoped advisory check exit=0 with no errors and no current-candidate findings; 131 unrelated pre-existing warnings and 22 manual-verification notes remain (old paths/journals/sidecars, earlier delivery artifacts and unrelated coverage). Reviewed final evolution: 23 paths, two added, no removed paths; delivery archives, compiled frontend and all earlier changes preserved. Full-suite proof, browser/provider acceptance and package rebuild were not performed, as explicitly requested.
- 2026-10-20 delivery: Delivered the requested implementation as local uncommitted working-tree changes. No commit, push, PR, archive rebuild, application restart or live ticket start was requested or performed in this task. User-requested local outcome is complete; later package/live acceptance remains deferred rather than claimed.

## Rulings

- RULING-001 | date=2026-10-20 | decision=Implement through local review without stage pauses, run only targeted tests and do not rebuild packages | reason=User explicitly requests implementation only and forbids the full suite | source=user | supersedes=none

## Handoff

current: done
status: ready
next: Local implementation complete; package/live acceptance only when requested
must_read: .agentic/tasks/TASK-6be1f0bc.md; 04_Software/adore/orchestrator.py; 04_Software/adore/cli.py; 04_Software/adore/web/commands.py
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: paused manual Start and localized closed failure reasons implemented
evidence: 51 focused backend tests and 14 frontend/help tests passed; TypeScript and Ruff passed
issues: full suite and packaging deferred by user request; pre-existing catalog/Starlette warnings
next: none for the requested local implementation; package/live acceptance deferred
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1
