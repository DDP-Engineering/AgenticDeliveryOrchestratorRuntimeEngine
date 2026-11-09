<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project settings Save

## User flow

One project-scoped Save owns all edited configuration rows. Opening Edit does not dirty an unchanged value. Several row editors may remain open. Invalid edits retain their input and prevent Save. Cancel resets a row; Discard changes resets the complete draft. Saving does not require the user to manage preparation or revision identifiers.

Save uses the existing pending/apply authority for all changed values. Ordinary changes apply immediately after preparation. Important changes first use admin/CSRF POST config/preview for the same validated candidate without changing active/pending data, then show one accessible confirmation dialog with the project, changed labels/values and concise effects. Confirm prepares the same candidate hash and execution plan before exact apply; Cancel keeps the editable local draft without creating a server candidate. No permanent prepare/apply panel, duplicate comparisons, raw revision hashes or timestamps appear in the ordinary flow.

The important set is identity/runtime changes already classified for restart, all execution-budget settings, and publication policy settings (draft/ready, progress publication, integration target and automatic CI repair). Existing pause/idle/lock gates remain. The UI explains an unmet gate; it does not pause monitoring or stop jobs automatically.

## Batch candidate contract

A configuration edit with `key = "settings.batch"` carries `value` as a JSON array of 1 to 100 exact objects `{"key": <editable setting key>, "value": <existing wire string>}`. Keys are unique and nonoverlapping. Nested batches and overlap with the synthetic executor connection's underlying provider/model/endpoint keys are rejected.

The complete batch is applied to TOML in memory using the existing setters, preserving unrelated values, comments and newline style. All member types, edit authority and external-environment restrictions are checked; complete configuration validation runs on the final combined document, permitting interdependent edits. No intermediate document is published. The candidate uses the current schema-1 record, one candidate text/hash and one audit attempt; no migration or alternate stored format is introduced.

Public batch proposed_value is a safe key-to-typed-value mapping; value is its canonical JSON serialization. Every read verifies the wire edits, selected values, exact complete candidate meaning, revision and runtime-plan authority, rejecting corrupt evidence with the existing pending_config_corrupt response.

## Replacement and failure

Preparation accepts an optional `pending_revision`. An existing candidate is replaced only when this matches its inspected candidate revision and the supplied base revision matches its unchanged base. A missing binding retains pending_config_exists; mismatches use stale_pending_revision or stale_config_revision. Supplying a binding without a matching candidate is stale_pending_revision. Malformed transport remains request-validation failure. Invalid batch content returns 400 invalid_config or setting_not_editable/environment_managed_externally as appropriate, with active and pending bytes unchanged.

Existing scalar/connection/collection operations remain current API capabilities. The web treats any valid prepared candidate as recoverable edits. For GUI-editable keys, Save uses one bound replacement rather than silently discarding evidence. A candidate containing an API-only or hidden key stays an exact read-only recovery: normal row edits are disabled, Save rereads and binds the complete stored candidate, shows its safe values for confirmation and applies the exact existing revisions without replacement. Stale or corrupt evidence disables Save and remains explicitly discardable. Corrupt/stale pending state stays explicitly discardable. Apply reuses current managed-state, lock, pause, activity, operation, plan and revision checks and one atomic file replacement; errors preserve candidate/draft evidence.

A browser project change or revision change must not apply edits to another identity. Drafts survive failures; a stale active revision blocks saving until the operator explicitly discards/reloads. Navigation/reload while dirty requests explicit discard. In-app navigation and browser Back stay blocked during Save/confirmation, including exact recovery without local dirty fields, until the decision resolves. No personal keys or passwords enter this draft.

## Layout

Opened groups span the settings panel. Desktop rows have a left label/description and a full right value/control column, with actions at the right edge. Typed editors fill their column and retain normal control height. At narrow widths rows stack in reading order without horizontal overflow. Keep the current typography, colors, categories, disclosures and read-only developer view. One visible Save bar identifies unsaved changes and remains usable on desktop and mobile. On narrow screens the Settings heading sits above the raw configuration actions so its words remain readable.

## Verification

Offline API happy/negative tests prove final combined validation, atomic apply, corrupt/duplicate/external member refusals, replacement binding and existing access/runtime gates. Frontend unit tests cover canonical dirty state and public batch protocol validation. Chromium journeys cover normal and important multi-edit Save, cancel/retry, persisted-candidate recovery, stale/external updates, navigation and desktop/mobile geometry in four locales. Reference screenshots supplied by the user ground the flow/layout comparison; screenshots alone do not prove accessibility.
