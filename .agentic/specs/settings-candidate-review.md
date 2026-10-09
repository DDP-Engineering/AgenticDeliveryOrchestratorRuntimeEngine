<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# Purpose settings and exact candidate review

## Contract

REQ-UX-2bea4ff1 / REQ-UX-d8745013: Project Settings categories in order are Repository, Tickets, Implementation, PR/MR and review, Statistics, and closed Technical details. Executor configuration remains separate; external runtime setup stays operator-owned. Repository holds platform/author identity, the single integration-branch editor and reviewed branch naming. Tickets holds polling except capacity, eligibility, priority/type mappings and action/status labels. Implementation holds capacity, budgets, progress commits and quick-path hint, with closed clarification/recovery/stage-limit topics. PR/MR holds publication approval/state/reviewers, revision policy/rounds and merged-branch cleanup; its integration-branch reference opens/focuses Repository without a duplicate editor. Statistics holds recording/token controls with closed file-path details. Installation paths, resource prefix and workflow Python are informational Technical details. Worktree paths are read-only under external authority; branch_template and branch_rule are the exact reviewed-edit exceptions. Each safe visible catalog setting has one row; unknown fields fall back to read-only Technical details. Reserved channel/prefix/scope/type-feature, review method/reminder, clarification reminder/timeout outcome, reconcile reactions, resource measurement and executor mode have no GUI rows. Technical configuration/catalog contracts remain unchanged. Ready stays direct in Tickets; answered/clarify/done/failed/review/working share one initially closed Status labels disclosure with truthful human-reply semantics. Server metadata supplies type, choices and numeric min/max; existing reviewed Admin editing, read-only Dev redaction, catalog validation and one-candidate authority remain decisive.

REQ-UX-84025a2c: one project has one pending edit. Endpoint is the existing combined supported edit. Preparation writes only pending_config.json. Review uses safe effective active values and server-derived candidate values, not the browser draft; endpoint shows URL/model/protocol/credential variable name/timeout/CA together. Revisions are full SHA-256 details; stale active base prevents UI apply and server verifies exact reviewed candidate and stored base. Saved created_at is real; actor is unavailable and shown as not recorded. UI conditions are advisory; server rechecks conductor/config locks, nonterminal/corrupt runs, unfinished operations and paused pickup for restart changes. Discard removes only pending candidate. Retry after correction retains draft; stale/corrupt review requires reload or discard. No multi-edit, automatic activation or audit promise.

## Concurrency and security

Immediate mutation ref lock prevents duplicate prepare/apply/discard. Capture project, generation, config and candidate before await; ignore completions after scope/session changes. Pending GET failure cannot leave an old actionable review. Catalog/pending transport is validated before use. Unknown/malformed metadata disables edits rather than inferring controls. Safe copy contains only redacted review values. URL credentials and credential query parameters are redacted from active reads and rejected for newly edited URLs; raw provider JSON stays hidden. Dev API mutation denial remains server-owned.

## Verification

Focused Python config/pending/catalog/RBAC tests and settings helper/browser scenarios precede final pytest, Ruff, frontend typecheck/build/validate and strict task check. Inspect representative 390px/light/dark captures; full WCAG, novice and live acceptance remain human work.

Pending scalar candidate types match built-in configuration scalar types (integer excludes boolean/fraction; number accepts finite integer/float; executor model is text). Persisted review and apply revalidate that projection. Core and CLI validation contracts retain their behavior.

The browser sends both candidate_revision and base_revision on Apply. Optional base_revision is additive for old clients: when supplied it must match the stored reviewed base, else 409 stale_config_revision; candidate-only legacy requests retain stored-base/current-byte checks.

Preparation focuses the review heading; discard returns focus to the original edit control or endpoint. Frequent controls appear first inside each purpose category. Persisted key/value/restart contradictions fail closed before review/apply.

Restored endpoint CA paths are revalidated before review/apply against the same HTTPS, absolute executor path, bounded length and no traversal/control-character domain as preparation; malformed paths return `pending_config_corrupt`.
