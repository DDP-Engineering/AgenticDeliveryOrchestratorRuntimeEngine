<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-daec305a - Simplify project settings guidance and retain project defaults

stage: done
type: change
path: quick
interaction: autopilot
requirements: REQ-UX-81bae624
parent:
branch: task/adore-web-interface
base: c7fdfcbd9b7341ab238f78a27ba53bcfd260dcd6
opened: 2026-10-06

## Done checklist (current stage)

- [x] red browser tests, anchor, implementation
- [x] docs/requirements reconciled
- [x] focused proof and scoped reviews
- [x] standing authorized local commit
- [x] push/deploy after DCP connectivity returns

## Frame

Problem: STATED per-row Help duplicates permanent descriptions; project/default filter suggests platform scope.
Desired outcome: STATED all per-project settings, including defaults, permanent descriptions only; global controls in Administration.
Actors:
Primary scenario:
Examples:
Counterexamples:
In scope: SettingsList removes Help/filter, retains all project catalog rows, edit accessibility and existing global Administration controls.
Out of scope: No migration of per-project defaults into global policy or configuration schema changes.
Constraints: Four hours/three fix cycles/twenty authored files; targeted tests, no paid calls/subagents; standing commit/push/deploy authority.
Success signals:
Evidence: OBSERVED SettingsList/project Config catalog per-profile; Administration has global audit retention and capacity.
Assumptions:
Unknowns:
Decision-blocking questions:
Proposed behaviors:
Path and reason: Quick, presentational interactive simplification without backend behavior change.

## Requirement coverage


## Design


## Log

- 2026-10-06 frame: User selected all per-project settings including defaults. Standing iterative authority continues through validation and normal commit/push/deploy; full regression deferred.


- 2026-10-06 build red: scoped Chromium2 tests fail with101 per-row Help disclosures before implementation. Anchor recorded before source edits; removed Help/override filter/dead type helper, preserved all catalog rows and editing.
- 2026-10-06 deviation validate: full suite deferred by user; targeted browser admin/developer plus candidate edit/discard, typechecks/build and strict advisory catalog substitute.

- 2026-10-06 final validation: Two separate scoped review passes approved specification compliance and implementation quality, round1: retained every per-project catalog/default row, permanent accessible descriptions, server edit domains and developer read-only behavior, with global audit policy remaining Administration. Three focused Chromium journeys exit0; typechecks/e2e and production builds exit0; diff whitespace and strict advisory catalog exit0 (no --run). Existing Vite size/history catalog warnings accepted. No backend changes; no paid/external calls.
- 2026-10-06 delivery: Candidate presented under standing user commit/push/deploy authority; six authored files plus workflow/generated assets. Full regression deferred per user; DCP22/3001/18443 each timed out on two bounded connectivity inspections. Prior AI commit c7fdfcb could not push on forge SSH2222; no deployment performed. Local publication proceeds; remote delivery remains blocked, without repeated retries.

- 2026-10-06 delivery completed after VPN restoration: Gitea branch push verified at c9156672c55e2e3d4534386804f908a11e3bcf57, containing AI c7fdfcb and Settings c915667. DCP deployment exit0; backup /home/dpasare/apps/adore/backups/web-ux-c915667-20261006203839. API/worker active with matching PYTHONPATH, served JS/CSS byte comparisons passed, database schema14/integrity ok (audit68). Root/health/ready200; unauthenticated projects401. Deployed module lists OpenCode/Pi/Codex/Qwen. No full-suite rerun or paid model inference; real model acceptance remains operator-triggered.

## Rulings


## Handoff

current: done
status: ready
next: Human live acceptance of the GUI and explicit model test.
must_read: 05_SoftwareDocu/Component_Model_Connection.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: Single project-setting guidance and all project defaults.
evidence: Focused proof retained; push verified, DCP deploy/served assets/services/health/database verified.
issues: Full regression and real paid model acceptance remain deferred as authorized.
next: Human live acceptance; delivery complete.
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 1


## Delivery report (2026-10-06)

- stage: deliver; type: change; path: quick; branch: task/adore-web-interface
- requirements:
  - REQ-UX-81bae624 - Project settings without duplicated help or override filter
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=1
- diff vs task base c7fdfcb: 12 file(s) changed, 183 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=10 notes=25
- checklist: 4/5 done; open: push/deploy after DCP connectivity returns
