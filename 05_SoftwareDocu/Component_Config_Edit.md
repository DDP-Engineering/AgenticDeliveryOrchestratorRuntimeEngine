<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration edit coordination

## 1. Purpose

`adore.config_edit` coordinates configuration writes made by the CLI and web
API on one host, so neither ADORE process overwrites another ADORE edit.

## 2. Responsibilities

`config_edit_lock(path)` holds an exclusive, per-directory process lock for the
whole read, validate, and replace operation. A competing editor receives
`ConfigEditLockedError`. The CLI maps that error to exit code 1, and the web
API maps it to HTTP 409 `config_edit_locked`.

## 3. Implementation Overview

The component uses `StateStore(path.parent, "adore-config")` and its existing
PID-aware stale-lock recovery. It releases only a lock it acquired, including
when validation or writing fails. Web edits also use their SHA-256 revision
check, which detects a stale browser form or an intervening direct file edit.

## 4. Dependencies

The only runtime dependency is the stdlib-backed `adore.state.StateStore`.

## 6. Data Contracts

All ADORE CLI and web edits to the same configuration directory must use this
lock. Direct host edits do not participate; operators should stop ADORE edits
before changing a configuration file outside ADORE.

## 9. Validation And Tests

`tests/test_web_config.py` holds the lock in one process and verifies both CLI
and web edits fail closed, leave the file unchanged, and succeed after release.

## 7. Workflow Integration

Web preparation, apply and discard use this same configuration-directory lock.
Preparation saves a single pending candidate with active TOML unchanged. Apply
checks its candidate revision, optional explicit reviewed base, current bytes and
conductor idle/paused conditions before replacement. Discard removes only pending
state. Contention returns typed `config_edit_locked` recovery feedback to the
settings review; the API owns revision/candidate validation and StateStore owns
conductor safety. See `Component_Web_API.md` for the complete endpoint contract.
