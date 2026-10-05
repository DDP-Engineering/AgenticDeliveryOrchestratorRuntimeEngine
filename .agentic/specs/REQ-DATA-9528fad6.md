<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable working-rules contract

## Behavior and compatibility

Export validates the authoritative active TOML snapshot, recognized declared
structure and the portable values. It projects resolved defaults as well as
declared settings. A source with unknown fields or malformed types fails closed;
the legacy lenient TOML loader and exact TOML enrollment remain unchanged.
Known excluded fields are intentionally omitted under this documented contract.
No redacted read model is an export source.

JSON has exactly `kind`, `schema_version`, `source`, `settings`, `checksum`.
Kind is `adore-project-settings`, schema_version is integer 1 (boolean rejected).
Source has exactly `product: "ADORE"`, `version: adore.__version__` and
`contract: "portable-rules-v1"`. Consumers accept only their exact installed
ADORE version and this contract. A different release requires an explicit
future compatibility decision; nothing is guessed, dropped or migrated.
No separate hardcoded release version or runtime state migration exists.

## Enumerated complete allowlist

Settings has exactly these four sections and all listed fields:

| Section | Fields and domains |
| --- | --- |
| polling | mode (`loop` or `once`); poll_interval_seconds (positive integer); poll_jitter_seconds (nonnegative integer); poll_backoff (boolean); max_concurrent_runs (positive integer) |
| readiness | require_acceptance_criteria, require_priority_label, require_known_component (booleans) |
| recovery | max_stage_failures, max_transient_retries (positive integers); retry_backoff_seconds (nonempty list of nonnegative integers) |
| budgets | max_iterations, max_wall_clock_seconds, per_gate_timeout_seconds, max_files_touched (positive integers); max_cost_usd (finite nonnegative JSON number; zero disables reported-cost enforcement) |

All integers are at most 1,000,000,000. Cost is at most 1,000,000,000 USD.
Retry lists have at most 100 entries. JSON input is UTF-8, at most 64 KiB.
Types are strict: booleans are not numbers; floats are not integer limits.
Source TOML is UTF-8, at most 512 KiB. Existing supported config validation
also applies to exports. The parser returns only a fresh validated settings
mapping and reproduces every included value; it never enrolls or writes a profile.
Consumers use these values as defaults for a **new** project, with explicit
target configuration, reviewed paused enrollment and human credential setup.
This work exposes no import/clone/enrollment UI or write endpoint.

## Exclusions and reconfirmation

Everything outside the enumerated allowlist is omitted: agent/profile/display
identity; forge/repository/login/branch ownership; state/worktree/metrics paths;
labels, free-text scope hints, quiet hours and timezone assumptions; commands,
models, environment, credential references/values, endpoints, images, mounts,
container/network policy; clarification, workflow, delivery, review, reconcile
and metric settings; jobs/history, users/grants/audit, pending revisions and
financial price history. `max_cost_usd` is a working limit, not price history.
No nonsecret credential or endpoint reference is exported. All target-host
credentials/endpoints must therefore be supplied and confirmed explicitly.
Nested unknown source fields cause rejection; recognized excluded fields may
contain data but are never copied into the envelope or error messages.

## Canonical encoding and checksum

Encode the envelope excluding checksum with Python JSON `sort_keys=True`,
`ensure_ascii=True`, separators `(',', ':')`, `allow_nan=False` and no newline;
SHA-256 lowercase hexadecimal becomes checksum. Serialize the completed envelope
the same way with one final LF. Source has no time, path or project identifier.
Equal resolved settings/source produce identical bytes. Key order or whitespace
on input does not affect checksum verification. SHA-256 detects changes;
an attacker can recompute it, so it provides **no authenticity**.

Unknown/extra/missing keys, duplicate JSON keys at any depth, incompatible
source/type/version, nonfinite numbers, invalid bounds, malformed nesting,
encoding/size/depth errors and checksum mismatches raise `PortableSettingsError`
with a stable value-free code. No partial result escapes.

## API and presentation

Administrator-only GET `/api/v1/projects/{name}/config/portable-settings`
returns the canonical envelope. `download=true` adds fixed attachment filename
`adore-project-settings.json`. Optional `checksum` binds the requested result
to the preview; mismatch returns 409 `portable_settings_changed`.
Authentication and Admin checks precede project lookup or config reading.
Invalid source returns 503 `portable_settings_invalid`; errors echo no values.
Responses use no-store. Project identity is rechecked after export; replacement
returns typed conflict. Reads perform no probes or writes and exclude pending edits.
The localized Settings panel explains purpose, exact included/excluded categories,
active-source semantics, checksum limits, new-project default and unsupported
import UI, then explicitly previews and downloads. Failed/empty reads present
corrective feedback and cannot download stale data. Scope changes invalidate late
responses. The browser downloads the validated server bytes only.

## Acceptance

Offline public export/parse roundtrip and trust-boundary corruption tests;
authenticated API happy, invalid source/session, Admin/Dev/unknown-project
non-disclosure and preview-change tests; existing TOML/CSV regression;
browser keyboard/390px/themes/locales and representative visual inspection.
Live infrastructure, novice participants and comprehensive WCAG remain human work.
