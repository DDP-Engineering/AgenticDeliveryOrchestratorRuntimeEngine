<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Identity

## Purpose

Builds stable hidden markers for ADORE-owned ticket/MR comments and derives
bounded names for branches, containers, worktrees, networks, and labels.

## Public contract

Marker creation/parsing identifies ADORE-owned remote records, while naming
helpers turn a validated run identity into deterministic, length-safe local and
forge resource names. The same identity is used for idempotent comments,
recovery lookup, and cleanup scope.

## Safety contract

Only marker-owned records may be edited or deduplicated; human discussion is
never treated as disposable ADORE state. Invalid/foreign markers do not confer
ownership, and resource names remain bounded so a remote platform cannot
reinterpret an unchecked ticket value as a new resource.

## Requirement coverage

- `REQ-FUNC-de3089bd` - marker ownership is slug-scoped and fail-closed.
- `REQ-FUNC-7b4caf58` - bounded derived resource naming.

## Files

- `04_Software/adore/identity.py`
- `04_Software/tests/test_identity.py`
