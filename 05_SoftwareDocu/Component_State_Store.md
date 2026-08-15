<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# State Store Component

## 1. Purpose

`adore/state.py` persists the local source of operational truth and append-only
audit log. ADORE 0.5 introduces closed state schema 4.

## 2. Responsibilities

- atomically save/load run state and ticket snapshots;
- append/read JSONL events;
- own pause and single-instance lock files;
- preserve active/historical task ids, stage/path/type, counters, incidents,
  outbox, validation evidence, candidate fingerprint, approval and MR state;
- report corrupt runs without silently reinitializing them.

## 3. Data Contract

Every `state.json` contains `schema_version: 4`. Missing/wrong schema and unknown
keys raise `StateError`. ADORE 3.x state is rejected with a no-migration
diagnostic. Outbox/failure/task histories are lists and validation evidence is
an object.

Writes use temporary-file replacement. JSONL is append-only; a torn trailing
line may be skipped because `state.json`, not the log, drives decisions.

## 4. Workflow Integration

The conductor saves before every remote notification, after every counter or
lifecycle change, and at every stage boundary. Explicit retry resets only the
active counter/clock; history remains.

## 5. Validation and Tests

`tests/test_state.py` covers schema-4 round trips, task history, hard-break
rejection, corrupt state, snapshots, JSONL, locking, pause and cleanup support.
