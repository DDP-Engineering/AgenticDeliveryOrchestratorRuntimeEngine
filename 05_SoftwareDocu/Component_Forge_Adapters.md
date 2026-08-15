<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Forge Adapter Components

## 1. Purpose

`adore/forge` hides GitHub, GitLab and Gitea CLI/API differences behind one
ticket, comment, label and draft MR/PR contract.

## 2. Responsibilities

- list/read tickets and comments;
- post/edit marker-owned ticket comments;
- add/remove ticket labels;
- read draft MR/PR state and discussion;
- post/edit marker-owned MR/PR comments;
- remove review-trigger labels;
- open a draft MR/PR.

The base interface deliberately has no merge operation. GitHub and Gitea use
their issue-comment surface for MR/PR comments; GitLab uses merge-request
notes. CLI JSON, URLs, HTTP statuses and not-found behavior fail closed through
`ForgeError` or an explicit missing resource.

## 3. Notification Integration

The orchestrator persists an outbox record before calling comment operations.
Stable hidden markers make crash replay idempotent. A confirmed deleted MR/PR
falls back to the source ticket; if both are gone, the local audit marks the
record undeliverable.

## 4. Validation and Tests

`tests/test_forge.py` covers the three offline adapters, command/JSON trust
boundaries, labels, comments, draft creation and resource lookup. Conductor
tests cover incident editing, routing, fallback, redaction and outage replay.
