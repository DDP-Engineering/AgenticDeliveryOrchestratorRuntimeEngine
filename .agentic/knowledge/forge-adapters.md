<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Forge adapters

## Purpose

Defines the forge-neutral data model and adapter boundary for GitHub (`gh`),
GitLab (`glab`), and Gitea (`tea`): tickets, comments, labels, branches, and
draft MR/PRs.

## Public contract

The `Forge` interface normalizes ticket selection, claims, comments, labels,
branch state, push, and draft MR/PR operations. Concrete GitHub, GitLab, and
Gitea adapters translate their CLIs through an injectable command runner and
return typed domain data, leaving orchestration policy above the boundary.

## Safety contract

All CLI output, URLs, status lines, and JSON are parsed as untrusted input and
malformed responses raise `ForgeError`. Adapters expose no merge action and
cannot use a human comment without a valid ADORE marker as mutable state.

## Requirement coverage

- `REQ-FUNC-f699f84a` - malformed forge response data fails closed.
- `REQ-FUNC-e7a89a6d` - publication creates draft records only and has no merge capability.

## Files

- `04_Software/adore/forge/`
- `04_Software/tests/test_forge.py`
