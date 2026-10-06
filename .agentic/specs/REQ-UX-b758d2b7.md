<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Authorized action workspace specification

Status: active. Covers the four TASK-60c83db1 requirements.

## Evidence and compatibility

The scope is project hubs, attention/global jobs/detail and existing commands.
jobs-page validates complete authorized sources; composite detail has waiting and coverage; legacy runs-page owns advanced filters, and operations expose asynchronous status.
Global filters and strict detail timeline retain advanced capabilities over complete authorized history.
Consumption/named actor and unobserved AEGIS stages remain unknown; completed job status does not establish human merge.

## Additive read contract

jobs-page adds attention (boolean; clarification, approval, in-review, failed, stale or handoff-pending), executor (1-200, exact case-sensitive observed journal identity), outcome (trimmed 1-80 case-insensitive fragment), updated_from/updated_to (inclusive UTC stored update day; ordered date range). Validate every selected source before filters; no source repair. Missing update stamps do not match a date filter. Counts/groups retain searched scope before secondary filters. Existing q, lifecycle, stage, status_group, project_id, snapshot semantics unchanged.

Project summary treats empty legacy update timestamps as absent; malformed nonempty values remain typed errors. This permits navigation to strict job evidence with unknown activity.

Strict detail adds timeline [{ts: UTC|null, event: redacted string, stage: valid persisted stage|null}], from captured JSONL bytes. Only these fields are displayed; omitted timestamps stay unknown. Global list excludes timeline and internal observed executor identities. Invalid executor/stage evidence fails closed even when unrelated to the chosen filter. No state/schema migration, external read or usage implementation.

## Views and semantics

Overview default covers all authorized enrolled/archived history, with a project scope selector and Needs attention first (clarification, approval, review, failed, stale, handoff-pending). Compact attention and actual working/publishing tables share one Project selector; Details opens the composite Jobs route. Worker faults remain visible; reporting and technical evidence stay in dedicated views. Pickup state and revision/time-bound verification are independent on Projects and hub Summary. Hub includes Jobs/Statistics links, read-only Settings for Dev, Admin Access and job History (terminal filtered history); preserve legacy Configuration/Prices URL and ability.

Jobs simple search/project/status-group filters are always visible. Advanced exact lifecycle/stage/executor/outcome/UTC dates use actual server filters. Ten-row pagination passes the source revision on continuation. Source change clears old totals/detail and explicitly requests reload at page zero. Loading, failed, incomplete, empty and no-match states differ; malformed responses fail closed. Requests guard scope/session and cancel superseded presentation.

Details lead with current lifecycle explanation, exact stage, observed reason, role/person/location and conditional following behavior. Evidence links are optional valid HTTP(S) saved locations. Stage progress is never inferred; timeline shows only actual events, including quick-path omitted stages. done is Completed, regardless of arbitrary outcome strings. Handoff pending and handed off remain distinct. Technical details expose safe IDs/counters/coverage; duration is unavailable unless a supported final-duration contract exists, consumption unknown.

## Commands and authorization

Manual start is available only for a selected authorized current project; explain that worker runs existing ticket selection/readiness/approval gates. Retry appears only for failed current jobs; cancel only nonterminal jobs excluding handoff-pending. Effects remain visible, ref lock prevents duplicate submission. Queue acceptance is pending, not completion; poll existing operations and display succeeded/failed/uncertain with actual redacted result. Worker heartbeat states readiness only, not per-job execution or forge reachability. Pickup stop explains active jobs continue. Admin pickup buttons remain project operations.

## Verification

Real API offline fixture persists genuine RunState/journal/ticket evidence for all exact lifecycle groups, quick path, colliding IDs and missing metadata. Browser/API/model tests cover trust-boundary failures, asynchronous worker failure, routes/Back, keyboard/390px/both themes/locales, source revisions and no telemetry invention. Full required strict proof applies to exact final tree; representative screenshots provide visual inspection only. No new dependency or live acceptance.
