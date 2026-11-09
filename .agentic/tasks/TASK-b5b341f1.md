<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-b5b341f1 - Choose remote target branches during repository enrollment

stage: build
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-b3251e39, REQ-FUNC-5de75419
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-16

## Done checklist (current stage)

- [x] Offline happy/boundary regression cases written before implementation.
- [x] Remote branch parser and enrollment dropdown implemented.
- [x] Four-locale help, notes and affected component/user documentation reconciled.
- [ ] Final automated verification deferred by explicit user instruction.

## Frame

Problem: STATED — Target branch is free text although users need the remote branches and forge default.
Desired outcome: Read repository populates a target-branch dropdown and selects the remote default.
Actors: Enrollment administrator; all supported GitHub, GitLab and Gitea remotes including self-hosted instances.
Primary scenario: Repository URL -> Read repository -> remote branch choices and selected default -> administrator optionally chooses another branch.
Examples: A remote whose HEAD points to develop selects develop even when main also exists; task/adore-web-interface is selectable.
Counterexamples: Corrupt/oversized remote output, detached HEAD, empty repository, changed URL, stale response and deleted prior selection must not fabricate a default or retain another repository's branch list.
In scope: Shared read-only Git remote boundary, additive branch-list API data, enrollment and clone-config UI, offline regression sources and four-locale documentation/notes; requested removal of the duplicate Close action in Connect repository.
Out of scope: Changing existing project Settings, new forge adapters/authentication, clone/publication changes, tests execution, frontend builds, delivery rebuilds.
Constraints: STATED — implement for every forge; implement only and defer tests/packages. OBSERVED — existing server Git credentials, administrator/CSRF route and request-generation guards.
Success signals: All forge kinds use the same remote read; advertised default selected; explicit existing selection survives reread; malformed output fails closed.
Evidence: OBSERVED adore/web/repository_source.py ls_remote asks only HEAD; app.py repository-source returns default_branch; EnrollmentWizard.tsx renders target_branch as input.
Assumptions: INFERRED — branch discovery through the forge's Git remote meets the request without separate vendor API authentication.
Unknowns: Actual deployment credential/access and remote branch count; no live forge calls are needed for implementation.
Decision-blocking questions: none.
Proposed behaviors: Bounded validated remote heads; dropdown marks default; no default means explicit choice; no branches means disabled empty choice with recovery guidance; same-URL reread preserves an explicitly selected still-existing branch.
Path and reason: full — new observable branch-selection interface and additive response field. No new dependency or permission.
Path criteria: no new observable behavior=no; no new interface/data format=no; no new dependency=yes; existing requirement coverage=yes (revise); no security/data-handling change=yes (retain access, validate added input).
Run limits: At most 30 source/doc/test files, 60 minutes, no live provider calls or publication; preserve all earlier working-tree changes.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision |
|---|---|---|---|---|---|---|
| Choose a remote target branch | Read-only discovery and default-aware selection | REQ-FUNC-b3251e39 | GitHub/GitLab/Gitea branches and non-main default | Corrupt refs/limits/duplicates, missing HEAD, empty repository, stale responses and URL changes | Offline API/browser regression sources; execution deferred | One Git ls-remote request; additive branches field; native select |
| One connection-dialog dismissal action | Retain Cancel and Escape; remove the duplicate heading button | REQ-FUNC-5de75419 | Cancel dismisses the dialog | Draft token cleared; Escape retained | Existing jobs browser case updated before source; execution deferred | Remove only the heading Close button |

## Design

- REQ-FUNC-b3251e39: Extend the existing `git ls-remote --symref -- <url> HEAD` with `refs/heads/*`; Git remains the forge-independent read boundary using the existing noninteractive account credentials and 20-second limit.
- Parse at most 2 MB and 10,000 heads; validate object IDs and Git ref names, reject duplicate/malformed refs and inconsistent advertised default with typed RepositorySourceError/502. Empty output is an empty repository; a missing symbolic HEAD leaves default_branch null.
- API adds sorted `branches: string[]`; default_branch comes from remote symbolic HEAD, never from main/master heuristics. No persistence, schema migration or new endpoint.
- Enrollment validates the branch data before showing it, places the default first with a localized marker and uses a required native dropdown. Empty branches disable the control and block continuation with guidance. Existing saved/project Settings are unchanged.
- Retain generation/unmount guards. Track explicit selection per normalized URL; preserve it only on rereading that URL while the branch still exists; clear metadata immediately on URL edit. Failed reads clear stale discovery rather than permitting creation from an old list.
- Existing backend clone-time target branch validation remains authoritative if the remote changes after discovery. No component/dependency architecture change; no new diagram needed.
- Regression seams: test_repository_source.py API all-forge/empty/detached/corrupt/bounds cases; enrollment.spec.ts default selection/manual reread/URL changes/malformed or stale responses; shared e2e fake advertises real head refs.
- All four projects-help locales, release notes, Repository Source/API/Frontend component docs, Web Interface guide and knowledge are updated with implemented behavior.
- Alternative vendor-specific branch APIs add auth/pagination coupling without improving the existing Git boundary; retained optional tea login detection does not gate branch discovery for other forges.
- REQ-FUNC-5de75419: Remove the heading Close button from RepositoryConnection; retain existing Cancel, Escape and token-clearing handlers. The user's incremental request changes no API, authentication or persistence contract. Update existing browser expectations and four-locale help/notes; no new architecture impact.

## Log

- 2026-10-16 frame: Accepted requested branch dropdown within the ongoing implementation-only UI work; retained current dirty branch, all-forge support and deferred tests/packages. Full path selected.
- 2026-10-16 specify: Revise REQ-FUNC-b3251e39 for validated remote branch choices and default; no new or retired requirements.
- 2026-10-16 design: Shared Git discovery and native dropdown contract recorded above; transition to build under the user's continuing implementation-only authorization.
- 2026-10-16 DEVIATION build: Regression sources were written before implementation, but no red/green execution or automatic validation is performed; the user explicitly deferred all tests until the final batch. No automated proof is claimed.
- 2026-10-16 build: Anchored the dirty checkout before product edits. Implemented bounded strict all-forge Git ref discovery, additive branches response, localized default-aware dropdown, retained explicit selections, stale/failed read invalidation and empty/missing-default guidance. Offline API/browser regression sources extended; no external forge/model calls, test commands, builds or package changes.
- 2026-10-16 release-notes: updated (merged remote branch/default selection with the existing four-locale Projects improvement).
- 2026-10-16 help: updated (Projects topic in en/fr/de/ro; shared enrollment and Clone project config guidance).
- 2026-10-16 build inspection: Reviewed the changed source for noninteractive argv, full-advertisement validation, CRLF handling, default/empty state, selection ownership and request-generation guards. Reconciled the e2e fake and four-locale help. Evolution covers 19 source/documentation/test paths within the 30-file bound; all earlier edits and delivery archives preserved. This is source inspection only; tests, type checking, release-note checks and builds remain unexecuted.
- 2026-10-16 scope/build: User requested removing Close from Connect repository. Updated the existing jobs browser assertions before removing that one button; retained Cancel/Escape token clearing. Revised the existing connection requirement and component/user documentation. No tests or builds executed.
- 2026-10-16 release-notes: updated (existing four-locale Interface fix includes the single Cancel action).
- 2026-10-16 help: updated (four Projects locales name Cancel/Escape and draft-token dismissal).
- 2026-10-16 local delivery: User authorized opening the updated application or creating a test package. Production frontend compilation/type checking and release metadata checks completed; targeted repository-source tests passed 52 cases after shortening oversized parametrization IDs for Windows fixture paths. Created the updated Windows archive and adjacent hash in 07_Delivery (31,044,682 bytes), with a separate extracted copy under D:/Downloads/adore-0.13.0-windows-x64-test. No Linux rebuild. Partial archive verification was stopped immediately when the user requested archive only; no complete package-verification result is claimed. App startup was rejected by automatic approval policy before execution; user then cancelled further startup/verification work.
- 2026-10-16 authentication diagnosis: Fresh saved/enrollment checks still reported forge_auth=false while direct and isolated HTTP-route calls returned valid HTTP 200 identity. Observed the real API child using the expected tea binary, matching account/environment/cwd, and rapid completion; no confirmed root cause yet. User restarted ADORE and explicitly allowed live diagnosis while retaining settings/credentials. Added secret-free failure metadata to the existing bounded launcher log and extended the existing negative API regression source before implementation; no automated suite run. Prepare a diagnostic Windows archive for the actual failing process rather than infer the missing response.
- 2026-10-16 release-notes: none (internal diagnostic logging; existing user-facing boolean response unchanged).
- 2026-10-16 help: none (no interface or workflow change in the diagnostic increment).
- 2026-10-16 diagnostic delivery: Created Windows ZIP plus adjacent hash with value-free failure logging (31,045,072 bytes). No full archive verifier or unit suite ran. User action requested: stop old instance, extract the new archive to a new folder and start it, retaining the existing user-data directory. Root cause remains unconfirmed pending the actual failing response metadata.

- 2026-10-20 live diagnosis: User started the diagnostic Windows ZIP. Actual failures recorded exit 1, no HTTP response, empty stdout and stderr lengths 26 (default login) then 39 (named login). The same installed tea and bundled Python succeed in unrestricted read-only terminal probes with the API process environment; a constrained shell reproduces missing-login errors of those exact lengths. API account SID/integrity match the terminal; its parent chain originates in Total Commander. These observations do not yet establish the actual API error or its config-file access. No credentials/settings changed, no provider request or suite executed.
- 2026-10-20 build: Extend existing negative regression source before adding exact missing-login reason classification and value-free host config-presence metadata. This diagnostic increment intentionally does not guess a runtime authentication fix.
- 2026-10-20 release-notes: none (internal failure diagnostics only).
- 2026-10-20 help: none (no interface or workflow change).

- 2026-10-20 diagnostic delivery/live observation: Built the Windows ZIP and adjacent hash (31,046,206 bytes), production compilation and release metadata checks completed; no automated suite or archive verifier ran. Extracted a separate copy under D:/Downloads/adore-auth-diagnostic-20261020 and used the official stop/start commands with approved elevated execution, preserving existing data and credentials. Fresh UI host check on the restarted copy reports Verified: repository sign-in, Git, forge CLI, native execution and AEGIS files all Passed. Model endpoint remains Not checked; no model call was made. The authentication policy was unchanged, so this is observed recovery after restart, not proof of a permanent authentication fix or the original launch-context cause. Current application remains running for the user. Evolution reviewed: 30 paths including authorized generated frontend/archive outputs, preserving pre-existing edits.

## Rulings

- RULING-001 | date=2026-10-16 | decision=Continue implementation without intermediate stage stops; defer all test execution, builds and packages | reason=Standing user instructions to complete implementations and test everything at the end | source=user | supersedes=none
- RULING-002 | date=2026-10-16 | decision=Use one discovery path for GitHub, GitLab and Gitea including self-hosted remotes | reason=Explicit latest user clarification | source=user | supersedes=none
- RULING-003 | date=2026-10-16 | decision=Remove the redundant Connect repository heading Close button and keep Cancel | reason=Explicit user screenshot and request during the same implementation-only batch | source=user | supersedes=none
- RULING-004 | date=2026-10-16 | decision=Diagnose the repeated fresh Gitea readiness failure with safe metadata and the user-authorized running instance; retain configured credentials and settings | reason=User reports the same validation errors and agrees to keep ADORE open | source=user | supersedes=none

## Handoff


current: build
status: waiting
next: User can test the running copy; retain diagnostics for any recurrence and run deferred focused regression tests in the final batch
must_read: .agentic/tasks/TASK-b5b341f1.md; 04_Software/adore/web/app.py; 04_Software/tests/test_repository_connection.py; 05_SoftwareDocu/Component_Repository_Auth.md
blockers: Original launch-context cause remains unconfirmed because the restarted copy passes; automated regression execution remains deferred by the user

## Stage report


stage: build
result: paused
current: build
changed: expanded safe diagnostics packaged for Windows; application restarted with existing data
evidence: fresh live UI host check Verified, repository sign-in and workflow files Passed; Windows ZIP built; no automated suite or archive verifier
issues: original launch-context cause unconfirmed; model endpoint not checked; automated regressions and Linux rebuild deferred
next: user acceptance on running application; capture diagnostics if failure recurs; deferred focused tests at final batch
needs_user: yes
spec_compliance:
implementation_quality:
review_round:
