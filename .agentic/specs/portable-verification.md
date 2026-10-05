<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable settings verification and limits

Task TASK-c4655839; live W05 #9 under epic #3. Base/HEAD before delivery:
`7b4caea6f031f3f535456671baa8eb4640baa434`, branch `task/adore-web-interface`.
Authenticated tea login `ddp` confirmed seven live criteria, #6 dependency closed,
#13 delivered/closed with 8/8 and epic #3 open. No issue/label write before delivery.

| Live criterion | Concrete implementation and offline evidence |
| --- | --- |
| Deterministic type/version/allowlist and portable roundtrip | Pre-build exact spec REQ-DATA-9528fad6; `export_settings` and `parse_settings`; `test_portable_public_export_exists_and_roundtrips`, boundary-value and otherwise-valid-duplicate tests. Exact current package source version; complete 16-field allowlist. |
| No secret or excluded nested identity/state/access | Source structural validation plus closed numeric/boolean/enum projection; recognized `container.runtime_env` sentinel omitted byte-identically; unexpected nested fields reject. No arbitrary strings/references in settings. UI/API source/pending omission tests. |
| Typed strict schema/types/duplicates/limits/nesting rejection | Public Python tests for malformed envelope, nonfinite/invalid/recomputed checksums, exact integer/list domains, duplicates at valid nested fields, encoding/size/depth, malformed known source maps/scalars; helper transport tests include JS fractional/exponent folding rejection. |
| Explicit source compatibility | Source has exact ADORE version and portable-rules-v1; parser rejects changed version/product/contract/unknown/missing fields with PortableSettingsError. No guessed/dropped unsupported fields. |
| Admin/session and unauthorized metadata boundary | `administrator` resolves before `project` lookup; monkeypatched public profile IO must not execute for unauthorized requests; assigned/unassigned Dev and invalid/revoked sessions receive fixed errors. Browser Dev control and direct API absence; ownership replacement rejects after snapshot. |
| Exact TOML and metrics CSV distinct and compatible | 123 targeted module/API/import/metrics tests passed before final correction; full strict suite includes their existing contracts. Export-only API/UI and parser write no profile/pending/state/measurement record. Copy/import controls are deliberately unavailable. |
| No runtime migration/hardcoded release | Only additive module/read route/panel; no state/profile schema or dependency/version declarations change. Source version imports actual `adore.__version__`; runtime migration is absent. |

## Observed focused verification

55 module/API Python tests passed after one scoped review correction; 2 helper
tests passed; 6 portable Chromium scenarios passed in the isolated fixture before
the final branch-only helper readability correction, then repeated in final full
proof. Typecheck and production build passed; `uv run ruff check .` from
`04_Software` passed. Exact TOML/metrics regression was 123 passed. Full final
proof and both current candidate-bound verdicts are recorded in the task journal,
strict JSON and candidate review/inventory rather than inferred from these reads.

Initial explicit `uv run pytest` was exit 1: 1011 passed/1 platform skip with one
failure in unchanged worker heartbeat test at its 100-ms freshness assertion
while a frontend build was concurrent. Unchanged worker/store/test have no diff;
isolated selector rerun passed. Scheduling sensitivity is inferred, not proven;
the failure is retained, assertions/timeouts untouched and final serial strict
proof remains decisive. Initial typecheck and browser overflow findings plus the
scoped identity-race red test/correction are preserved in the journal.

## Final strict proof

`python .agentic/aegis.py check --task TASK-c4655839 --strict --run --json`
exited 0; strict passed, zero errors, seven classified advisories. Configured
serial commands: Python 1013 passed/1 existing platform skip/1 TestClient
deprecation warning (168.8 s command); Ruff passed (0.1 s); frontend validate
passed (153.2 s), including helpers, typecheck, isolated build and all 73
Chromium scenarios. Production build and explicit whole-workdir Ruff also passed
for this exact candidate. The earlier unchanged heartbeat failure passed in the
complete final proof, without changing or weakening it.

Final JSON: `.agentic/tasks/TASK-c4655839.validation-final.json`; SHA-256
`28d7c0eaad0f8be0abe2f215eff54d3689c70cfaeee318019e5dfd5fb6e6638f`.
Windows console JSON was losslessly normalized to UTF-8/ASCII escapes after
successful execution; JSON values and actual command outcomes were preserved.
All 35 bound raw-byte hashes/deletions still matched after proof; local and remote
HEAD remained the exact baseline. Current round-2 verdicts are both approved.

The seven catalog warnings are: two synthetic PNG scan gaps (directly inspected),
one minified generated JS scan gap (complete scan: no private keys/AWS keys/tokens;
five password matches are four translated field labels and a React type table),
one final-proof scan gap (all four complete credential-pattern scans return zero),
and three historical workflow warnings: two already tracked sidecars, invalid
Handoff in TASK-5e99ee1d and old ruling in TASK-c765e6b4. Historical records were
not rewritten. No relevant unresolved finding or weakened verification is accepted;
no material deviation. Existing nonfatal deprecation/chunk-size/color warnings
remain documented. No external reviewer/participant/live acceptance is claimed.

## Visual and accessibility scope

Viewed `portable-evidence/portable-light-390.png` and `portable-dark-390.png`
directly. The entire purpose/exclusion/compatibility copy wraps within the panel,
the checksum fits, the primary focus ring is visible in both themes and JSON
scroll remains within the panel. Keyboard activation/Tab focus and no document
overflow at 390 px are automated; all four supported locales expose translated
purpose/controls. Screenshots are offline synthetic fixture evidence without
operator secrets. PNG headers are technically impossible; this report carries
their project provenance. These checks establish neither full WCAG conformity
nor five-participant novice or live infrastructure acceptance.

## Scope, warnings and ownership

No live forge/container/executor acceptance, new dependency/version, planning
edit, later ticket implementation, import/clone/enrollment write, merge, PR,
release, tag or deployment. Additional paid API/executor/subagent budget ZERO;
reviews are independent primary-agent passes. One of three corrective review
cycles used. Existing TestClient deprecation, Vite chunk-size and color-env
warnings are visible and do not justify an unrelated dependency/refactor.

Generated static filenames change on build. Four existing requirement metadata
lists now reference the stable static directory instead of obsolete hashed
assets, preserving all behavioral prose/tests; new UX coverage includes the
generated directory. This is workflow traceability reconciliation, separately
inventoried. Historical journal/sidecar warnings remain untouched. Binary PNG
and minified generated JS scan warnings are covered by direct visual/source and
asset-stamp inspection; the final JSON lists exact remaining warnings.

The ownership inventory records authored product/test/doc, generated/static,
workflow/context/requirements/spec and report evidence separately. It excludes
its own hash and replaceable journal/review/proof/report metadata from the bound
candidate to avoid circular hashes, and names every exclusion explicitly.
Delivery stops at this unchanged validated candidate for coordinator inventory
verification and explicit delivery instruction; #9 and epic #3 remain open.
