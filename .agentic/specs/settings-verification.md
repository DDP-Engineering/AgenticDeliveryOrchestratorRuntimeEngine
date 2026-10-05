<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Issue 13 validation evidence

Task: TASK-6461cd25. Branch: `task/adore-web-interface`.
Base/unchanged HEAD: `6665bb72dc0dae1f3e50abf9e2ba50d515e1496a`.
Scope: only W09 P1, issue #13. No child tasks or additional executors.

## Acceptance mapping

| #13 criterion | Implementation and observed proof |
|---|---|
| 1. Purpose categories, clear labels, visible help, active/default/proposed | Seven groups in settings.ts, English labels and four-locale copy in settingsCopy.ts, SettingsList and PendingReview. Node complete-group/catalog tests; browser seven-group, four-locale and read-only journeys; screenshots inspected. |
| 2. Safe before/after, project and effect, copy | Typed proposed_value comes from saved TOML; review compares safe effective active values. Browser compares repository and complete endpoint fields, project/effect, copy without provider JSON; API credential URL redaction/rejection. Saved time is real; absent actor/connection facts remain not recorded. |
| 3. Prepare preserves active; exact apply | Existing dashboard journey prepares, compares active revision/value, explicitly applies and verifies changed revision/value. API tests compare original bytes; explicit reviewed base mismatch rejects, exact base/candidate succeeds. |
| 4. Fail closed and recover | API negative scalar types/bounds, stale revisions, corrupt persisted key/value/restart/digest/time, restored endpoint protocol/credentials/CA, CSRF/locks/active/unfinished operations. Browser invalid correction retains draft, blocked apply retains review, stale/malformed reads disable actions and offer discard/refresh. |
| 5. Paused identity/runtime and idle/locks | Existing state/conductor/config locks remain server-owned for all applies. Python pending tests cover active run, conductor lock, unfinished work and unpaused identity; browser identity review disables apply and displays stop/wait guidance. |
| 6. Honest one-setting candidate | Visible prepare-one-at-a-time text; server one pending candidate; editing and endpoint fields disabled during pending/mutation/read uncertainty. Existing endpoint combined edit remains supported. |
| 7. Dev denial, financial/secret redaction | API granted Dev omits max_cost_usd, credential URL value and raw provider JSON; POST/DELETE/GET-pending denial. Browser Dev view has no edit controls or financial/provider content, light/dark/keyboard/390px checked. |
| 8. Candidate-only discard | API and browser compare active bytes/revision before/after discard, then pending is absent. Browser keyboard focus returns to the edited row. |

## Focused proof and failure ledger

- Python config/pending/catalog/RBAC: 53 passed, 23.31s; `uv run ruff check .`: passed.
- `node --test tests/settings.test.mjs`: 8 passed.
- `npm run typecheck` and `npm run build`: passed; generated static files inventoried separately.
- `npx playwright test e2e/settings.spec.ts e2e/dashboard.spec.ts`: 16 passed, 34.4s before the final additional row badge/value assertion. The configured final browser run proves that additional assertion.
- Meaningful pre-implementation red cases and exact selectors are retained in the journal: missing typed proposed/domain data (2 failures), absent purpose/server-choice behavior (1 failure), boolean/fraction accepted for iteration integer (2 failures), Dev financial disclosure (1 failure), ignored reviewed base (1 failure), corrupt active scalar read accepted (1 failure).
- Initial browser fixture failures (9 passed/4 failed, later 7 passed/1 failed) came from pending-read synchronization and the account route/theme selector; corrected without weakening assertions, followed by 16 passed. An initial Python expected metadata equality was reconciled to exact role-filtered rows. These are retained rather than overwritten as a clean first run.
- Final full-suite, independent review dimensions, strict result, warnings and exact unchanged inventory checks are recorded in the journal and `TASK-6461cd25.validation-final.json`. This page records observations available before that final gate.

## Inspection and preserved captures

Inspected the endpoint before/after review at 390px: six fields stack without clipping, active unknowns stay not recorded, proposed auth shows only an environment name, and action guidance/buttons remain readable. Inspected Dev light/dark 390px screenshots: visible purpose/help/source/active/default, no edit controls, readable wrapped text. Automated overflow assertion is <=1px. Browser journeys exercised keyboard Space on categories, review heading focus and discard return focus.

- [Endpoint review](settings-evidence/settings-endpoint-review-390.png)
- [Dev light](settings-evidence/settings-light-390.png)
- [Dev dark](settings-evidence/settings-dark-390.png)

PNG captures are binary generated evidence; comment headers are technically impossible. All textual new artifacts carry the project license header. The REQ-UX-9a625fc5 row-edit/source contract is exercised by the real apply journey, including source badge/value assertions; noneditable notes are rendered by SettingsList and covered through existing catalog read-only metadata and Dev journeys. Inspection complements automated proof; it does not replace a missing runtime test.

## Supplemental correction

A supplemental boundary review after the first green strict gate found saved CA metadata could expose a credential URL or relative path. Two new negative cases failed (2 failed/2 passed); the existing public projection now enforces the fresh preparation CA domain. The original strict evidence is preserved as validation-round1.json and is superseded by the final corrected inventory/proof.

The second strict gate passed Python/Ruff but failed the existing discard return-focus assertion (66 browser passed/1 failed). Render timing could leave the target button disabled at the animation frame. Focus restoration now runs after the busy-state render commits, retaining the captured-scope guard. validation-round2.json preserves the failed gate; assertion unchanged.

The third strict gate passed Python/Ruff but the dashboard apply assertion matched both success and transient loading status regions (66 browser passed/1 failed). The assertion is scoped to the success notice with its text unchanged; no product behavior was changed for this fixture correction. validation-round3.json preserves the gate. Third and final authorized corrective cycle.

## Reviewed boundaries and limitations

Backend semantic review checked every changed hunk against config model/validator, candidate byte/digest checks, locks, paused pickup, typed errors, URL redaction and legacy candidate-only compatibility. Frontend review checked catalog authority, one candidate, captured view/session/request identities, ref locking, safe copy and fallback facts. Component knowledge and project context match the built code; environment setup is unchanged. Historical requirements that named replaced bundle hashes now reference the actual generated files; their behavior and verification were not changed.

DEVIATION build: backend needed scalar-type enforcement, optional explicit reviewed-base binding and Dev financial filtering beyond the initial projection estimate. Baseline negative tests reproduce criteria 4/7 violations. Corrections remain in existing web routes; core/CLI/state schema/dependencies unchanged.

Offline Windows/Chromium proof is bounded implementation evidence. No full WCAG claim, novice five-participant acceptance, live forge/container/credential acceptance, release or deployment. Those human acceptance boundaries remain open. Issue #13 and epic #3 remain open pending coordinator inventory verification and delivery instruction.
