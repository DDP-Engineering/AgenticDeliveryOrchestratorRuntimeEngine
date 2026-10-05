<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Exact server enrollment contract

The browser selects a UTF-8 file from an existing ADORE profile or an operator-prepared config.example.toml. Its bytes round-trip through fatal UTF-8 decode (preserving BOM) and encode; incompatible encodings fail before submitting. The browser keeps a File reference and rereads it before preview, probe and confirmation, rejecting a changed or unreadable source. File replacement and edits invalidate evidence. No paths are rewritten.

import-preview accepts existing ProjectImportInput and returns config_revision (raw SHA-256), revision (SHA-256 of canonical file digest, profile name/display/description, resolved physical server paths, state evidence and ownership snapshot), structured validation, unverified state and allowlisted review. Invalid/secret documents have no review. Review contains exact config destination, declared and resolved repository/worktree/state and metrics paths, forge/repo/branch, agent identity, executor/model/runtime/image/egress and credential reference names. No raw runtime environment, commands or unknown values are echoed.

import-check is additive Admin/CSRF, requires current revision and structurally valid candidate, reuses _probe_setup with its 30-second bound and returns status/checks/context/time/config_revision/revision. It reinspects after probing. Evidence is memory-only and does not activate/publish. Failed/partial/unverified results remain visible in review and permit stopped enrollment of structurally valid data; activation remains separate.

import rechecks candidate and rejects mismatched identity/file/ownership/state revision. Publication holds shared enrollment/config lock, then conductor lock, reinspecting with its own conductor lock ignored before writing. Existing lock, corrupt or active runs reject; roots on every consequential path reject; state roots overlap neither equal, ancestor nor descendant. State/ownership changes during inspection are caught by locked reinspection. Source file never transfers history; existing server terminal history is retained. No persisted state format change.

Six steps retain memory draft. Back/Change from review invalidates obsolete evidence and returns to corrections; revalidation is required. Busy/ref generation guards prevent double submit and late completions. Findings show safe code, configuration key/location, remediation and a focusable correction action. Leaving/refresh warns; unmount discards. Invalid response or failed enrollment retains draft and never emits completion. EN/FR/DE/RO reuse the accessible shell/theme.
