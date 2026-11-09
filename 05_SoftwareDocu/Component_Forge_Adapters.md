<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Forge Adapter Components

## 1. Purpose

`adore/forge` hides GitHub, GitLab and Gitea CLI/API differences behind one
ticket, comment, label and draft or ready MR/PR contract.


The conductor performs leased post-merge branch cleanup through host Git on all three forges. GitLab additionally receives its native removal hint at MR creation; GitHub/Gitea creation delegates cleanup to the conductor. Gitea accepts only a boolean `merged` field when supplied; malformed merge evidence raises `ForgeError` before destructive cleanup can be authorized.

## 2. Responsibilities

- list/read tickets and comments, including every open ticket for browsing
  (`list_open(limit)`, at most `limit` tickets, no label filter);
- post/edit marker-owned ticket comments;
- add/remove ticket labels;
- list repository label names and create a label (`list_labels()`, `create_label(name,
  color, description)`): GitHub `gh api repos/<repo>/labels` (colour without `#`), GitLab
  `glab api projects/<id>/labels` and Gitea `tea api repos/<repo>/labels` (colour with `#`),
  read page by page; the base class raises `ForgeError` for adapters without them.
  `adore/forge_labels.py` builds the project's label list from its settings and creates only
  the missing ones (`ensure_labels`), never changing existing labels;
- read draft or ready MR/PR state and discussion;
- post/edit marker-owned MR/PR comments;
- remove review-trigger labels;
- open a draft or ready MR/PR.

The base interface deliberately has no merge operation. For MR/PR comments,
GitLab uses merge-request notes, which already include diff notes; GitHub and
Gitea combine their issue-comment surface with the submitted reviews and inline
diff comments, merged onto one timeline, so the revise loop sees the feedback a
reviewer left from the diff view. CLI JSON, URLs, HTTP statuses and not-found
behavior fail closed through `ForgeError` or an explicit missing resource.
Output that a CLI returned successfully but in the wrong shape (invalid JSON,
an unexpected top-level type, or an open-ticket record without a positive
number, list labels and text fields) raises `ForgeResponseError`, a
`ForgeError` subclass, so callers can tell malformed forge data from an
unavailable CLI.

`pipeline_status(mr_iid)` is the one deliberate exception to failing closed. It
normalizes each platform's own vocabulary onto `PIPELINE_STATES` and is
contracted NEVER to raise: it is read by the post-MR poll, which is watching a
run doing no code work, so an unreadable verdict must degrade to `"unknown"`
(silent) rather than disturb the poll. GitLab reads the verdict inline from the
MR document; GitHub requests `statusCheckRollup` in its own `gh pr view` call so
a gh that does not know the field cannot break the MR read the whole poll
depends on; Gitea reads the pull for `head.sha` and then that commit's combined
status.

## 3. Notification Integration

The orchestrator persists an outbox record before calling comment operations.
Stable hidden markers make crash replay idempotent. A confirmed deleted MR/PR
falls back to the source ticket; if both are gone, the local audit marks the
record undeliverable.

## 4. Validation and Tests

`tests/test_forge.py` covers the three offline adapters, command/JSON trust
boundaries, labels, comments, draft and ready creation and resource lookup. Conductor
tests cover incident editing, routing, fallback, redaction and outage replay.
