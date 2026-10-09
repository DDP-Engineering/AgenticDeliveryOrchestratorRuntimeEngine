<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# Purpose settings and exact candidate review

REQ-FUNC-d67a1d33 / REQ-UX-66547cbf: Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The six stage rows choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins prepare, inspect active/proposed values and apply only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

## Contract

Implementation uses shared four-locale names for reviewed settings, including **Active job limit**, **Maximum executor launches per job** and **Active work time limit (seconds)** names in rows, editors and candidate review. Help describes serial capacity with parked jobs excluded, lifetime launch counts, resettable active periods and between-attempt time/cost checks. Reported USD accounting depends on captured token usage; cost-only reports do not count. File guidance describes distinct committed/pending/new product and AEGIS paths, the unfinished-merge exception and continuation when Git counting is unavailable. Per-attempt timeout help preserves configured recovery and strict-check semantics; progress publication is enabled by default with local commits retained when disabled, and the quick label is an optional framing hint. Configuration keys, runtime enforcement and role/redaction contracts retain their current behavior.

REQ-UX-2bea4ff1 / REQ-UX-d8745013: Project Settings categories in order are Repository, Tickets, Implementation, PR/MR and review, Statistics, Agent and model, and closed Technical details. Agent and model owns complete reviewed agent selections, selected command/model, names-only authentication configuration, provider API keys and explicit model testing; external runtime setup stays operator-owned. Repository holds platform/author identity, the single integration-branch editor and reviewed branch naming. Tickets holds polling cadence except capacity; standalone CLI startup mode is configured in TOML. Tickets also holds eligibility, priority/type mappings and action/status labels. Implementation holds capacity, budgets, progress commits and quick-path hint, with closed clarification/recovery/stage-limit topics. PR/MR holds publication approval/state/reviewers, revision policy/rounds and merged-branch cleanup; its integration-branch reference opens/focuses Repository without a duplicate editor. Statistics holds recording/token controls with closed file-path details. Installation paths, resource prefix and workflow Python are informational Technical details. Worktree paths are read-only under external authority; branch_template and branch_rule are the exact reviewed-edit exceptions. Each safe visible catalog setting has one row; unknown fields fall back to read-only Technical details. Reserved channel/prefix/scope/type-feature, review method/reminder, clarification reminder/timeout outcome, reconcile reactions, resource measurement and executor mode have no GUI rows. Technical configuration/catalog contracts remain unchanged. Ready stays direct in Tickets; answered/clarify/done/failed/review/working share one initially closed Status labels disclosure with truthful human-reply semantics. Server metadata supplies type, choices and numeric min/max; existing reviewed Admin editing, read-only Dev redaction, catalog validation and one-candidate authority remain decisive.

REQ-UX-84025a2c: one project has one pending edit. Endpoint is the existing combined supported edit. Preparation writes only pending_config.json. Review uses safe effective active values and server-derived candidate values, not the browser draft; endpoint shows URL/model/protocol/credential variable name/timeout/CA together. Revisions are full SHA-256 details; stale active base prevents UI apply and server verifies exact reviewed candidate and stored base. Saved created_at is real; actor is unavailable and shown as not recorded. UI conditions are advisory; server rechecks conductor/config locks, nonterminal/corrupt runs, unfinished operations and paused pickup for restart changes. Discard removes only pending candidate. Retry after correction retains draft; stale/corrupt review requires reload or discard. No multi-edit, automatic activation or audit promise.

## Concurrency and security

Immediate mutation ref lock prevents duplicate prepare/apply/discard. Capture project, generation, config and candidate before await; ignore completions after scope/session changes. Pending GET failure cannot leave an old actionable review. Catalog/pending transport is validated before use. Unknown/malformed metadata disables edits rather than inferring controls. Safe copy contains only redacted review values. URL credentials and credential query parameters are redacted from active reads and rejected for newly edited URLs; raw provider JSON stays hidden. Dev API mutation denial remains server-owned.

## Verification

Focused Python config/pending/catalog/RBAC tests and settings helper/browser scenarios precede final pytest, Ruff, frontend typecheck/build/validate and strict task check. Inspect representative 390px/light/dark captures; full WCAG, novice and live acceptance remain human work.

Pending scalar candidate types match built-in configuration scalar types (integer excludes boolean/fraction; number accepts finite integer/float; executor model is text). Persisted review and apply revalidate that projection. The shared validator requires a positive answer duration independently of reserved reminder timing.

The browser sends both candidate_revision and base_revision on Apply. Optional base_revision is additive for old clients: when supplied it must match the stored reviewed base, else 409 stale_config_revision; candidate-only legacy requests retain stored-base/current-byte checks.

Preparation focuses the review heading; discard returns focus to the original edit control or endpoint. Frequent controls appear first inside each purpose category. Persisted key/value/restart contradictions fail closed before review/apply.

Restored endpoint CA paths are revalidated before review/apply against the same HTTPS, absolute executor path, bounded length and no traversal/control-character domain as preparation; malformed paths return `pending_config_corrupt`.
