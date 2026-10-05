<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# [Web UX] Deliver a self-explanatory ADORE operator interface

## Tracking
Work item: EPIC. Priority: P1. Parent: Not applicable: this is the epic..
Dependencies: [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4), [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6), [W03 #7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7), [W04 #8](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/8), [W05 #9](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/9), [W06 #10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10), [W07 #11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11), [W08 #12](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/12), [W09 #13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13), [W10 #14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14), [W11 #15](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/15), [W12 #16](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/16), [W13 #17](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/17), [W14 #18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18), [W15 #19](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/19), [W16 #20](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/20).
Implementation baseline: task/adore-web-interface; bootstrap records the remotely available commit. New specs/docs and acceptance copy are English.

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
| Work item | Priority | Deliverable | Blocked by |
| --- | --- | --- | --- |
| [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) | P1 | [Web UX] Publish the implementation baseline and approved design assets | None |
| [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5) | P1 | [Web UX] Introduce the accessible dashboard shell, branding and plain-language vocabulary | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) | P1 | [Web UX] Add stable display identity and safe paused-enrollment backend contracts | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| [W03 #7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7) | P1 | [Web UX] Build guided project enrollment with explicit verification and review | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) |
| [W04 #8](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/8) | P1 | [Web UX] Make exact host-specific TOML enrollment understandable and revision-safe | [W03 #7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7) |
| [W05 #9](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/9) | P2 | [Web UX] Define and export a versioned portable project-settings package | [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) |
| [W06 #10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10) | P2 | [Web UX] Implement portable settings import and settings-based project cloning | [W03 #7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7), [W05 #9](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/9) |
| [W07 #11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11) | P1 | [Web UX] Expose an authorized global job read model with actionable evidence | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| [W08 #12](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/12) | P1 | [Web UX] Rework project hubs, attention queues and job details around the next action | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W07 #11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11) |
| [W09 #13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13) | P1 | [Web UX] Organize project settings by purpose and review candidate changes before applying | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5) |
| [W10 #14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14) | P2 | [Web UX] Make statistics scope, per-job usage and measurement coverage consistent | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| [W11 #15](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/15) | P2 | [Web UX] Present scoped statistics and per-job consumption with honest coverage | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W07 #11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11), [W10 #14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14) |
| [W12 #16](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/16) | P2 | [Web UX] Specify message-count semantics and executor/forge source capabilities | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| [W13 #17](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/17) | P2 | [Web UX] Collect and expose message counts from approved real evidence sources | [W12 #16](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/16), [W10 #14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14) |
| [W14 #18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18) | P2 | [Web UX] Create users with explicit role and project access in one reviewed operation | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) |
| [W15 #19](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/19) | P2 | [Web UX] Record structured redacted change evidence and build useful audit history | [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6), [W06 #10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10), [W09 #13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13), [W14 #18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18) |
| [W16 #20](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/20) | P1 | [Web UX] Verify the integrated redesign with offline regression and novice-user acceptance | [W04 #8](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/8), [W06 #10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10), [W08 #12](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/12), [W09 #13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13), [W11 #15](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/15), [W13 #17](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/17), [W14 #18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18), [W15 #19](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/19) |

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

## Code and documentation orientation
Cross-component delivery; this issue coordinates the child issues.

## Execution bounds
Keep this operation to the stated planning/repository scope. Max four hours per session and three corrective attempts; record unresolved blockers. No product implementation, automatic pickup, merge or fabricated approval.


## Approved reference assets

- [English design brief, provenance manifest, logo variants and visual references](http://192.168.1.15:3001/attachments/a3006796-ce57-452a-8497-c1e38b102a09) — ADORE_Web_UX_Reference.zip.
- [Approved transparent DDP Engineering mark](http://192.168.1.15:3001/attachments/79f13809-2d28-47da-9870-6bd8007776f2) — 630x300 PNG; #B8D1C4 on #102F29 without a white panel.
- [Overview visual reference](http://192.168.1.15:3001/attachments/e9f32c44-3369-4589-b95f-1197b86a195a).

The archive is available through this Gitea issue rather than only the local untracked planning folder. Extract it and verify asset-manifest.json hashes. Historical screenshot copy is Romanian; implement English issue/specification copy and preserve supported localization.

![Approved dashboard branding](http://192.168.1.15:3001/attachments/e9f32c44-3369-4589-b95f-1197b86a195a)
