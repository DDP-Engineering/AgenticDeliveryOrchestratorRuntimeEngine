<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-1b5748ba - Jobs filter guidance and aligned text fields

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-e96a5dd4
parent:
branch: task/adore-web-interface
base: 4317ff03547388c5d482f5603682fd98631ac004
opened: 2026-10-01

## Done checklist (current stage)

- [x] Implement localized filter Help and aligned wider fields.
- [x] Update frontend and user documentation.
- [x] Inspect localized/responsive UI and filter behavior.
- [x] Verify offline suite and deploy/commit.

## Frame

Problem: Observed executor and Outcome contains lack guidance and appear on different rows with narrow text fields.
Desired outcome: Explain their actual data sources and matching rules; align wider fields.
Actors: Administrators and assigned developers filtering job history.
Primary scenario: Open Help, enter a recorded executor or outcome fragment, inspect matching authorized jobs.
Examples: pi matches journal executor exactly; executor_timeout matches EXECUTOR_TIMEOUT in outcome, ignoring case.
Counterexamples: These fields do not search the full AEGIS log or configured-but-unobserved executor; legacy jobs without recorded executor do not match that filter.
In scope: Frontend filter layout, localized Help/placeholders, documentation and DCP static delivery.
Out of scope: Search API or persisted-state changes, new job execution.
Constraints: Exact case-sensitive executor; case-insensitive substring outcome; 200/80 character bounds and project authorization preserved.
Success signals: Shared aligned two-column text-filter row, responsive stacking, Help for each field.
Evidence: STATED alignment/size/Help request; OBSERVED app.py runs-page filters journal executor identities and RunState.outcome; OBSERVED orchestrator.py writes outcome codes and saved summaries. INFERRED size means wider text inputs.
Assumptions: Standing uninterrupted commit/deploy authorization applies.
Unknowns: None blocking.
Decision-blocking questions: None.
Proposed behaviors: GuidedField for both text filters, a wider shared grid below status/stage/date filters, localized matching/source guidance.
Path and reason: Full path for new visible guidance/layout, with existing API and security contracts unchanged. No child tasks.

## Requirement coverage

- REQ-UX-e96a5dd4: aligned wider filters, localized guidance and retained search contracts.

## Design

Reuse GuidedField and existing controlled filter state. Separate basic four-column filters from two equal-width text fields. Stack text fields on phones, and wrap basic controls at breakpoints. Guidance distinguishes ADORE journal identity and persisted outcome from full AEGIS output; inputs preserve the API limits and blank-filter behavior.

## Log

- 2026-10-01 frame/specify/design: Explained observed journal executor identity and saved ADORE outcome filtering to the user. Scope is wider aligned text fields and Help, without changing backend contracts.
- 2026-10-01 build: Equal-width executor/outcome fields now sit below a four-column basic-filter grid, with phone stacking and compact breakpoints. Both reuse GuidedField, localized help and literal example placeholders; lengths and query semantics unchanged. Build passed and user/component/knowledge docs updated.
- 2026-10-01 validate: Local browser fixtures prove pi matches its observed journal, PI returns no rows, lowercase executor_timeout finds the saved uppercase outcome, and clearing restores both jobs. Desktop fields both measured 677px with the same y position; compact 768px fields also aligned, and 390px fields stacked within viewport. Each phone Help inspected separately and stayed within the page. en/fr/de/ro guidance inspected; no actual jobs started. Existing test_web_rbac.py tests cover invalid whitespace/overlong input, unauthorized project access and corrupt outcome/journal identity.
- 2026-10-01 validate: Final evolution records 11 product paths. `python .agentic/aegis.py check --task TASK-1b5748ba --strict --run` exited 0: offline suite passed in 41.5s, lint passed, strict check found zero errors. Seven advisory warnings concern manual frontend verification, generated-asset coverage/scan notes and unrelated tracked fingerprints/older journal metadata. Semantically reviewed final diff; no API, data or authorization change. No verification failures remain.
- 2026-10-01 deliver: Standing user authorization covers commit and DCP frontend deployment without another prompt. Browser QA closed and local server stopped; no production job actions or repository changes.
- 2026-10-01 deliver: DCP frontend deployed successfully before close-out commit. Transferred archive SHA-256 eada7ba9f15ae448fff468628c94b0fdb01bd068543866c375dad424f57f61ab matched; JS index-s2A0PI7w.js and CSS index-DwWAgvnu.css installed. UI, both assets, API health and readiness returned HTTP 200; web and worker services active. Prior frontend retained in `static.pre-jobs-filters-20261001` alongside installed static files for rollback.

## Rulings


## Handoff


current: done
status: ready
next: None; implementation and deployment complete.
must_read: 04_Software/web/src/App.tsx, 04_Software/adore/web/app.py, 04_Software/tests/test_web_rbac.py
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: Wider aligned text filters with localized Help, examples and docs.
evidence: Build, GUI, offline suite, lint and strict check passed; DCP UI/assets/health/readiness 200, services active.
issues: None.
next: None.
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

## Delivery report (2026-10-01)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-e96a5dd4 - Explain and align Jobs text filters
- deviations: none recorded
- explicit review: disabled; existing validation remains required
- diff vs task base 4317ff0: 14 file(s) changed, 174 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=8 notes=10
- checklist: 3/4 done; open: Verify offline suite and deploy/commit.
