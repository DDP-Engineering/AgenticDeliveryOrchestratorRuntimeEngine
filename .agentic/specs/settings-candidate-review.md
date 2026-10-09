<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# Purpose settings and exact candidate review

## Contract

REQ-UX-2bea4ff1: categories in order are Repository and tickets; Agent and model; Isolated environment; Rules and approvals; Limits and recovery; Measurement and notifications; Advanced. Platform, polling and selection map to repository/tickets; executor to agent/model; container/worktree to isolation; delivery/readiness/workflow/review/labels to rules, with review.max_review_rounds in limits; budgets/recovery/clarification/reconcile to limits; metrics to measurement; agent/state to Advanced. Server metadata supplies type, choices and numeric min/max from the current config validation domain; empty choices mean text/domain explained in help, not unrestricted semantic validation. Server validation remains decisive. Defaults and editability retain their existing authority. Dynamic named keys resolve catalog patterns. Permitted redacted catalog keys render once in their purpose view; absent financial/secret fields have no rows. State channel, inactive executor-label prefix and ticket-scope hint are omitted from controls, while technical config/catalog compatibility is preserved. Ready/answered action labels stay in the main Rules and approvals list; clarify/done/failed/review/working are in an initially closed native Status labels disclosure, with the existing administrator reviewed editing flow and developer read-only access.

REQ-UX-84025a2c: one project has one pending edit. Endpoint is the existing combined supported edit. Preparation writes only pending_config.json. Review uses safe effective active values and server-derived candidate values, not the browser draft; endpoint shows URL/model/protocol/credential variable name/timeout/CA together. Revisions are full SHA-256 details; stale active base prevents UI apply and server verifies exact reviewed candidate and stored base. Saved created_at is real; actor is unavailable and shown as not recorded. UI conditions are advisory; server rechecks conductor/config locks, nonterminal/corrupt runs, unfinished operations and paused pickup for restart changes. Discard removes only pending candidate. Retry after correction retains draft; stale/corrupt review requires reload or discard. No multi-edit, automatic activation or audit promise.

## Concurrency and security

Immediate mutation ref lock prevents duplicate prepare/apply/discard. Capture project, generation, config and candidate before await; ignore completions after scope/session changes. Pending GET failure cannot leave an old actionable review. Catalog/pending transport is validated before use. Unknown/malformed metadata disables edits rather than inferring controls. Safe copy contains only redacted review values. URL credentials and credential query parameters are redacted from active reads and rejected for newly edited URLs; raw provider JSON stays hidden. Dev API mutation denial remains server-owned.

## Verification

Focused Python config/pending/catalog/RBAC tests and settings helper/browser scenarios precede final pytest, Ruff, frontend typecheck/build/validate and strict task check. Inspect representative 390px/light/dark captures; full WCAG, novice and live acceptance remain human work.

Pending scalar candidate types match built-in configuration scalar types (integer excludes boolean/fraction; number accepts finite integer/float; executor model is text). Persisted review and apply revalidate that projection. Core and CLI validation contracts retain their behavior.

The browser sends both candidate_revision and base_revision on Apply. Optional base_revision is additive for old clients: when supplied it must match the stored reviewed base, else 409 stale_config_revision; candidate-only legacy requests retain stored-base/current-byte checks.

Preparation focuses the review heading; discard returns focus to the original edit control or endpoint. Frequent controls appear first inside each purpose category. Persisted key/value/restart contradictions fail closed before review/apply.

Restored endpoint CA paths are revalidated before review/apply against the same HTTPS, absolute executor path, bounded length and no traversal/control-character domain as preparation; malformed paths return `pending_config_corrupt`.
