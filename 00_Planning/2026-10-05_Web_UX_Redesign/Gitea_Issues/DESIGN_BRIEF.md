<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Web UX redesign reference

Prepared 2026-10-05. Historical screenshots are visual references with Romanian demonstration copy; production requirements and new specifications/documentation are English. This archive contains no credentials, real project data or discarded AI logo trials.


## Problem and target behaviour
The current dashboard exposes configuration and orchestration concepts before explaining the user's task. The redesigned interface must let a person unfamiliar with ADORE and AEGIS understand projects, jobs, waiting states, configuration changes and consumption without verbal training.

Keep the useful Overview direction. Use a dark #102F29 navigation panel, neutral content surfaces, green action accents and the approved transparent DDP Engineering mark in muted sage #B8D1C4, without a white logo panel. Keep company branding separate from the ADORE product name. The reference prototype is illustrative, not production code.

## Delivery scope
- Clear navigation: Overview, Projects, Jobs, Statistics; administrator-only Users, Change history and System status; account/preferences remain accessible.
- Guided new enrollment and exact host-specific TOML enrollment; new projects begin with pickup stopped.
- Portable settings export/import and copying settings to a new project.
- Project hub, globally scoped jobs, evidence-based waiting reasons and next actions.
- Purpose-based configuration and candidate before/after review.
- Consistent project/period/timezone statistics, per-job consumption and honest measurement coverage.
- Explicit message definitions and source capabilities before message collection.
- Admin/dev accounts with project-scoped developer access and structured redacted audit history.
- Keyboard, responsive, light/dark theme and novice-user acceptance verification.

## Shared product boundaries
ADORE may publish draft MR/PRs and never merges. Approval remains on the forge and bound to the current validated candidate. Project pickup stopped does not pause an active job. Preserve forge/executor/runtime independence, server-side RBAC, admin-only financial data, CSRF, revision checks, lock/idle requirements and fail-closed corrupt-input handling.
The backend role remains developer; the UI may call it Dev. Unknown measurements are not zero. No live forge calls on every page refresh, fabricated progress percentages, browser secrets, automatic repository cloning or email invitation system.

## Priority and release policy
P1: core clarity, safe enrollment, operational flows and final acceptance gate. P2: complete the configuration portability, statistics and administration capabilities. Priority does not override dependencies.
The backlog is not an authorization to start autonomous execution. Before pickup, verify blockers, remove agent-hold where appropriate and let the operator explicitly apply the configured ready label. Native Gitea dependencies must also be checked; do not assume ADORE enforces them.

## Dependency graph and rollout
| Work item | Priority | Deliverable | Dependencies |
| --- | --- | --- | --- |
| BASE | P1 | [Web UX] Publish the implementation baseline and approved design assets | None |
| W01 | P1 | [Web UX] Introduce the accessible dashboard shell, branding and plain-language vocabulary | BASE |
| W02 | P1 | [Web UX] Add stable display identity and safe paused-enrollment backend contracts | BASE |
| W03 | P1 | [Web UX] Build guided project enrollment with explicit verification and review | W01, W02 |
| W04 | P1 | [Web UX] Make exact host-specific TOML enrollment understandable and revision-safe | W03 |
| W05 | P2 | [Web UX] Define and export a versioned portable project-settings package | W02 |
| W06 | P2 | [Web UX] Implement portable settings import and settings-based project cloning | W03, W05 |
| W07 | P1 | [Web UX] Expose an authorized global job read model with actionable evidence | BASE |
| W08 | P1 | [Web UX] Rework project hubs, attention queues and job details around the next action | W01, W07 |
| W09 | P1 | [Web UX] Organize project settings by purpose and review candidate changes before applying | W01 |
| W10 | P2 | [Web UX] Make statistics scope, per-job usage and measurement coverage consistent | BASE |
| W11 | P2 | [Web UX] Present scoped statistics and per-job consumption with honest coverage | W01, W07, W10 |
| W12 | P2 | [Web UX] Specify message-count semantics and executor/forge source capabilities | BASE |
| W13 | P2 | [Web UX] Collect and expose message counts from approved real evidence sources | W12, W10 |
| W14 | P2 | [Web UX] Create users with explicit role and project access in one reviewed operation | W01, W02 |
| W15 | P2 | [Web UX] Record structured redacted change evidence and build useful audit history | W02, W06, W09, W14 |
| W16 | P1 | [Web UX] Verify the integrated redesign with offline regression and novice-user acceptance | W04, W06, W08, W09, W11, W13, W14, W15 |

## Acceptance criteria
- [ ] All child deliverables and their negative trust-boundary tests pass; no blocked implementation is claimed complete.
- [ ] Every public mutation explains its effect, shows a meaningful result and enforces authorization on the server.
- [ ] Novice acceptance evidence meets the final verification issue's targets, or a human records the actual shortfall and remediation.
- [ ] No merge button, arbitrary job pause/resume, fabricated message count or all-time card mislabeled as period data.
- [ ] Operator and component documentation, changelog and applicable AEGIS knowledge reflect the delivered behaviour.
- [ ] The baseline and approved asset bundle are available remotely before child implementation starts.

## Baseline and design assets
Inspected local branch: task/adore-web-interface at 6fed00c. Remote branch was 450798e when this backlog was prepared; bootstrap must publish/reconcile the validation tooling commit before implementation. Do not use master as an equivalent web baseline.
The approved local design history is 00_Planning/2026-10-05_Web_UX_Redesign/. A portable reference archive is attached to this epic when available; its English README and the issue requirements are authoritative for implementation. Historical screenshots may contain Romanian copy; all new tickets, implementation specs and documentation are English.
No release version or deadline is assigned by this epic.


## Assets and provenance

The original company logo was isolated from the user-supplied business-card raster at D:/ProjectsDDP/DDP_Engineering/Carti de vizita/BunDeTipar3/. Source layout SVG SHA-256: 0fb248353b7844cc08a5e500593b81021cf9b1c862055ed2ca37e63989a1b9e3. The selected variant keeps the original geometry, removes pale paper using a native SVG luminance-to-alpha filter and uses #B8D1C4. DDP_Engineering_logo_dark.png is the production-reference transparent 630x300 asset, not a vector logo. Keep the project legal header in authored assets and preserve provenance.
