<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-a83c4cd3 — Serve audit and job history one page at a time

## Behavior

- `GET /api/v1/audit-page` (administrators) returns one newest-first slice of
  the audit trail after applying the configured retention policy, together with
  the total number of retained rows.
- `GET /api/v1/projects/{name}/runs-page` accepts the `lifecycle` query
  parameter more than once; a run matches when its lifecycle equals any given
  value. One value behaves exactly as before; none means all lifecycles.
- `GET /api/v1/audit` keeps its current behavior for existing callers.

## Data / interface

- `GET /api/v1/audit-page?limit=<1-100|all>&offset=<n>`; defaults `limit=25`,
  `offset=0`. Response:
  `{"items": [AuditRow...], "total": int, "limit": int|null, "offset": int}`
  where `limit` is null for `all`. AuditRow keeps the existing fields
  `id, actor, action, project, detail, created_at`.
- Errors: limit outside 1-100 and not `all` -> 422 `invalid_audit_limit`;
  negative or non-integer offset -> 422 `invalid_request`; non-administrator
  -> 403 `admin_required`; unauthenticated -> 401; corrupt audit rows -> 503
  `web_store_corrupt` (existing store failure path).
- An offset past the end returns an empty `items` list with the real total.
- runs-page: `lifecycle` values are each validated against the existing
  lifecycle literal set; any invalid value -> 422 `invalid_request`.

## Examples

- 60 audit rows, `limit=25&offset=25` -> rows 26-50 newest-first, total 60.
- `limit=all` -> all 60 rows, `limit: null`.
- `limit=0` -> 422 `invalid_audit_limit`; developer -> 403.
- runs-page `lifecycle=awaiting-approval&lifecycle=in-review` -> runs in
  either lifecycle; `total` counts only those.

## Acceptance

- API tests for paging, totals, bounds, roles, offset past end and the
  multi-value lifecycle filter, plus a regression test that single-value and
  absent `lifecycle` behave as before.

## Assumptions and open decisions

- Page sizes in the interface are 10, 25, 50 or All, all within the 1-100
  bound.
