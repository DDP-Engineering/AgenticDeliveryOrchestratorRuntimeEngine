<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-9c1f728e — Return stable web API error codes

## Behavior

- Every error response under `/api/v1` has the body
  `{"detail": {"code": <code>, "message"?: <text>}}` and keeps its existing
  HTTP status.
- `code` matches `^[a-z][a-z0-9_]{0,63}$`. `message`, when present, is an
  English diagnostic string for display after the localized code message; it
  never contains secrets, password values or hashes.
- Request-body or query validation failures return 422 `invalid_request`
  with `message` listing each failing field location and reason, separated by
  `; ` (input values are omitted).
- Framework errors with plain-text detail return `not_found` (404),
  `method_not_allowed` (405), or `request_failed` (any other status), with the
  original text in `message`.
- Store failures surfaced by account, membership, price and operation routes
  map to codes:

| Store message | Code |
|---|---|
| password must contain at least 8 characters | `password_too_short` |
| current password is incorrect | `current_password_incorrect` |
| username already exists | `username_exists` |
| invalid username | `invalid_username` |
| invalid role | `invalid_role` |
| user not found | `user_not_found` |
| cannot disable the last administrator | `last_administrator` |
| project not found / project does not exist | `project_not_found` |
| price version already exists or actor is invalid | `price_exists` |
| invalid price / invalid price identity / price exceeds limit | `invalid_price` |
| invalid effective date | `invalid_effective_date` |
| idempotency key belongs to another operation | `idempotency_conflict` |
| invalid operation | `invalid_operation` |
| any other message at these routes | `request_rejected` |

  For `request_rejected`, the store text is returned in `message`.
- Project creation (`POST /api/v1/projects`) wizard or profile failures return
  400 `project_setup_invalid` with the wizard diagnostic in `message`.
- Existing snake_case codes are unchanged.

## Data / interface

- HTTP statuses at each route are unchanged, including 404 for
  `user_not_found`/`project_not_found` on membership and reset routes and 409
  for a duplicate price, last administrator and operation conflicts.

## Examples

- `POST /api/v1/users` `{"username":"bob","password":"short"}` -> 400
  `{"detail":{"code":"password_too_short"}}`.
- `POST /api/v1/users/1/reset-password` `{"replacement":"short"}` -> 422
  `{"detail":{"code":"invalid_request","message":"replacement: String should have at least 8 characters"}}`.
- `GET /api/v1/nope` -> 404 `{"detail":{"code":"not_found","message":"Not Found"}}`.
- `POST /api/v1/projects` with an invalid answer -> 400
  `{"detail":{"code":"project_setup_invalid","message":"<wizard diagnostic>"}}`.

## Acceptance

- Each row of the table and each special case has an API test asserting status
  and code; a test asserts the code regex for every case.

## Assumptions and open decisions

- The bundled web interface is the only API client; replacing English
  sentences in `detail.code` with identifiers is compatible for it.
