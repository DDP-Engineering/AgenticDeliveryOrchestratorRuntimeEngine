<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-654e2ef2 — Adopt ADORE repository governance

stage: done
type: adopt
path: full
requirements: REQ-FUNC-308299d1,REQ-FUNC-1aa7a007,REQ-FUNC-2613bf7d,REQ-FUNC-ca17a8e8,REQ-FUNC-97e17737,REQ-FUNC-de3089bd,REQ-FUNC-7b4caf58,REQ-FUNC-0bdb23d5,REQ-FUNC-51f9c365,REQ-FUNC-1a2c56fe,REQ-FUNC-f699f84a,REQ-FUNC-e7a89a6d,REQ-FUNC-fcb2448b,REQ-FUNC-42b1c98a,REQ-FUNC-0ad8ba4f,REQ-FUNC-59ccdb74,REQ-FUNC-c6e5282d,REQ-FUNC-4fe259b0,REQ-FUNC-16237c6d,REQ-FUNC-ff7dad34,REQ-FUNC-83133b5e,REQ-FUNC-1ec4a21d,REQ-FUNC-db248962,REQ-FUNC-41265a32,REQ-FUNC-5771eecc,REQ-FUNC-6c82ad42,REQ-FUNC-69bfe896,REQ-FUNC-8a2e5904,REQ-FUNC-39697089,REQ-FUNC-3557ecdf,REQ-FUNC-f5aaaa62,REQ-FUNC-ef74f46e,REQ-FUNC-d9453193,REQ-FUNC-e3daac09,REQ-FUNC-78969e20
branch: master
base: ca41f76896a31db77d216fa5c9aba46be9672a89
opened: 2026-08-15

## Components

- [x] branding - `04_Software/adore/branding.py`; canonical names, paths, and runtime mounts; audit `05_SoftwareDocu/Component_Branding.md`.
- [x] util - `04_Software/adore/util.py`; command execution, timing, and shared value helpers; audit `05_SoftwareDocu/Component_Util.md`.
- [x] config - `04_Software/adore/config.py`; typed operator configuration and validation; audit `05_SoftwareDocu/Component_Config.md`.
- [x] identity - `04_Software/adore/identity.py`; marker identity and derived names; audit `05_SoftwareDocu/Component_Identity.md`.
- [x] state-store - `04_Software/adore/state.py`; schema-4 durable state, locks, and journals; audit `05_SoftwareDocu/Component_State_Store.md`.
- [x] forge-adapters - `04_Software/adore/forge/`; normalized GitHub, GitLab, and Gitea boundary; audit `05_SoftwareDocu/Component_Forge_Adapters.md`.
- [x] isolation - `04_Software/adore/isolation.py` and `04_Software/docker/`; worktrees, containers, and egress resources; audit `05_SoftwareDocu/Component_Isolation.md`.
- [x] executor-launcher - `04_Software/adore/executor/`; bounded executor gate protocol and output archive; audit `05_SoftwareDocu/Component_Executor_Launcher.md`.
- [x] aegis-client - `04_Software/adore/aegis.py`; AEGIS 0.5/schema-1 trust boundary; audit `05_SoftwareDocu/Component_Aegis_Client.md`.
- [x] orchestrator - `04_Software/adore/orchestrator.py`; polling, lifecycle, recovery, approval, and draft publication; audit `05_SoftwareDocu/Component_Orchestrator.md`.
- [x] profiles - `04_Software/adore/profiles.py`; multi-project profile storage and resolution; audit `05_SoftwareDocu/Component_Profiles.md`.
- [x] wizard - `04_Software/adore/wizard.py`; assisted project-profile setup; audit `05_SoftwareDocu/Component_Wizard.md`.
- [x] doctor - `04_Software/adore/doctor.py`; local environment and AEGIS readiness detection; audit `05_SoftwareDocu/Component_Doctor.md`.
- [x] cli - `04_Software/adore/cli.py`; operator command surface; audit `05_SoftwareDocu/Component_CLI.md`.
- [x] metrics - `04_Software/adore/metrics.py`; run summaries, reporting, export, and dashboard; audit `05_SoftwareDocu/Component_Metrics.md`.
- [x] process-log - `04_Software/adore/process_log.py`; rotating conductor log; audit `05_SoftwareDocu/Component_Process_Log.md`.
- [x] deployment-and-packaging - `04_Software/deploy/` and `02_Tools/package_runtime.*`; service installers and runtime bundle; audit `05_SoftwareDocu/Component_Deployment.md` and `Component_Packaging.md`.

## Done checklist (current stage)

- [x] component breakdown reviewed by the owner
- [x] every agreed component has a complete behavioral requirement register
- [x] every knowledge page links its active requirements
- [x] requirement templates contain no placeholder behavior, verification, or draft status
- [x] final full check recorded
- [x] refreshed report recorded
- [x] adoption changes committed
- [x] close-out recorded after the agreed Git outcome

## Log

- 2026-08-15 survey: created on master at the owner's instruction; existing component documentation is baseline evidence to audit rather than proof of current behavior.
- 2026-08-15 survey: proposed 17 components from source boundaries, test grouping, and the existing `05_SoftwareDocu` inventory; no production behavior changes are in scope.
- 2026-08-15 survey: owner authorized uninterrupted completion; the proposed component map is accepted and adoption continues on master.
- 2026-08-15 components: audited source, existing focused tests, and the component documentation inventory; recorded 17 detailed knowledge pages and active requirements without changing production behavior.
- 2026-08-15 close: full strict AEGIS check passed with the configured test and lint commands; direct focused-suite evidence was 382 passed.
- 2026-08-15 components: correction after owner review: the prior one-requirement-per-component pass was representative only, so the adoption returned from close to components for complete behavior coverage.
- 2026-08-15 components: branding source and its complete focused test were read end to end; its single shared identity behavior is covered by REQ-FUNC-308299d1.
- 2026-08-15 components: completed the behavior register with 35 active requirements linked to focused automated tests or an explicit installer inspection; each component knowledge page lists its coverage.
- 2026-08-15 close: refreshed full strict check passed; the only governance note is the explicit manual deployment-installer inspection and the task has no errors or warnings.
- 2026-08-15 done: committed the complete adoption record on master as 9c6ede0; no remote push was requested or performed.

## Delivery report (2026-08-15)

- stage: close; type: adopt; path: full; branch: master
- requirements:
  - REQ-FUNC-308299d1 - Provide stable runtime identities
  - REQ-FUNC-1aa7a007 - Execute external commands with typed outcomes
  - REQ-FUNC-ca17a8e8 - Validate typed runtime configuration
  - REQ-FUNC-de3089bd - Identify marker-owned remote records
  - REQ-FUNC-0bdb23d5 - Persist schema-4 run state safely
  - REQ-FUNC-f699f84a - Normalize forge platform operations
  - REQ-FUNC-fcb2448b - Isolate worktrees and containers
  - REQ-FUNC-59ccdb74 - Launch bounded executor sessions
  - REQ-FUNC-4fe259b0 - Validate the AEGIS companion protocol
  - REQ-FUNC-ff7dad34 - Conduct governed ticket delivery
  - REQ-FUNC-db248962 - Resolve runtime-project profiles
  - REQ-FUNC-5771eecc - Create assisted project configuration
  - REQ-FUNC-69bfe896 - Detect runtime environment readiness
  - REQ-FUNC-39697089 - Expose guarded operator commands
  - REQ-FUNC-f5aaaa62 - Summarize operational metrics
  - REQ-FUNC-d9453193 - Record conductor process events
  - REQ-FUNC-e3daac09 - Package and deploy the runtime
- diff vs task base ca41f76: 35 file(s) changed, 1916 line(s) added
- checks: errors=0 warnings=0 notes=1
- checklist: 3/5 done; open: report recorded and adoption changes committed; close-out recorded after the agreed Git outcome
- components: 17/17 adopted

## Delivery report (2026-08-15)

- stage: close; type: adopt; path: full; branch: master
- requirements:
  - REQ-FUNC-308299d1 - Provide stable runtime identities
  - REQ-FUNC-1aa7a007 - Execute external commands with typed outcomes
  - REQ-FUNC-ca17a8e8 - Validate typed runtime configuration
  - REQ-FUNC-de3089bd - Identify marker-owned remote records
  - REQ-FUNC-0bdb23d5 - Persist schema-4 run state safely
  - REQ-FUNC-f699f84a - Normalize forge platform operations
  - REQ-FUNC-fcb2448b - Isolate worktrees and containers
  - REQ-FUNC-59ccdb74 - Launch bounded executor sessions
  - REQ-FUNC-4fe259b0 - Validate the AEGIS companion protocol
  - REQ-FUNC-ff7dad34 - Conduct governed ticket delivery
  - REQ-FUNC-db248962 - Resolve runtime-project profiles
  - REQ-FUNC-5771eecc - Create assisted project configuration
  - REQ-FUNC-69bfe896 - Detect runtime environment readiness
  - REQ-FUNC-39697089 - Expose guarded operator commands
  - REQ-FUNC-f5aaaa62 - Summarize operational metrics
  - REQ-FUNC-d9453193 - Record conductor process events
  - REQ-FUNC-e3daac09 - Package and deploy the runtime
- diff vs task base ca41f76: 35 file(s) changed, 1943 line(s) added
- checks: errors=0 warnings=0 notes=1
- checklist: 4/6 done; open: adoption changes committed; close-out recorded after the agreed Git outcome
- components: 17/17 adopted

## Delivery report (2026-08-15)

- stage: close; type: adopt; path: full; branch: master
- requirements:
  - REQ-FUNC-308299d1 - Provide stable runtime identities
  - REQ-FUNC-1aa7a007 - Execute external commands with typed outcomes
  - REQ-FUNC-2613bf7d - Parse durations and execute commands safely
  - REQ-FUNC-ca17a8e8 - Validate typed runtime configuration
  - REQ-FUNC-97e17737 - Validate executor and egress policy
  - REQ-FUNC-de3089bd - Identify marker-owned remote records
  - REQ-FUNC-7b4caf58 - Derive bounded ADORE resource names
  - REQ-FUNC-0bdb23d5 - Persist schema-4 run state safely
  - REQ-FUNC-51f9c365 - Recover only a provably stale conductor lock
  - REQ-FUNC-1a2c56fe - Preserve and replay durable run journal evidence
  - REQ-FUNC-f699f84a - Normalize forge platform operations
  - REQ-FUNC-e7a89a6d - Open only forge draft delivery records
  - REQ-FUNC-fcb2448b - Isolate worktrees and containers
  - REQ-FUNC-42b1c98a - Manage isolated Git worktree lifecycle
  - REQ-FUNC-0ad8ba4f - Translate runtime mount paths for WSL
  - REQ-FUNC-59ccdb74 - Launch bounded executor sessions
  - REQ-FUNC-c6e5282d - Park executor gates on questions and preserve artifacts
  - REQ-FUNC-4fe259b0 - Validate the AEGIS companion protocol
  - REQ-FUNC-16237c6d - Validate AEGIS tasks and strict check evidence
  - REQ-FUNC-ff7dad34 - Conduct governed ticket delivery
  - REQ-FUNC-83133b5e - Recover governed stage failures deterministically
  - REQ-FUNC-1ec4a21d - Preserve notification delivery through an outbox
  - REQ-FUNC-db248962 - Resolve runtime-project profiles
  - REQ-FUNC-41265a32 - Persist isolated profile metadata atomically
  - REQ-FUNC-5771eecc - Create assisted project configuration
  - REQ-FUNC-6c82ad42 - Fail assisted setup safely on invalid answers
  - REQ-FUNC-69bfe896 - Detect runtime environment readiness
  - REQ-FUNC-8a2e5904 - Report host and forge tool readiness
  - REQ-FUNC-39697089 - Expose guarded operator commands
  - REQ-FUNC-3557ecdf - Resolve CLI profiles and report runtime state
  - REQ-FUNC-f5aaaa62 - Summarize operational metrics
  - REQ-FUNC-ef74f46e - Render metrics output from durable summaries
  - REQ-FUNC-d9453193 - Record conductor process events
  - REQ-FUNC-e3daac09 - Package and deploy the runtime
  - REQ-FUNC-78969e20 - Install unattended ADORE polling safely
- diff vs task base ca41f76: 53 file(s) changed, 3321 line(s) added
- checks: errors=0 warnings=0 notes=2
- checklist: 5/8 done; open: refreshed report recorded; adoption changes committed; close-out recorded after the agreed Git outcome
- components: 17/17 adopted
