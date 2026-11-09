<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Issue 8 review record

Round 2. Stable candidate fingerprint: `8f4edfd8cfa479840664b8d1674f914044c5a4698dbff76d9d71e22aca18f1ad` (definition/table in ISSUE-8-final-ownership.md). Reviews were separately considered by the primary agent against the same candidate; no subagents or external reviewers were launched. Corrective review cycles: 1 of the authorized maximum 3.

## Specification compliance: approved

Question: Does the candidate implement only the authorized exact server TOML enrollment, preserve its constraints and satisfy each current requirement/spec/design?

Evidence: Whole task/requirement/spec reads and complete authored diff inspection map the six ordered steps to source, unchanged UTF-8 copy, server paths, structural validation, explicit environment check, consequential review and stopped completion. The additive import-check and full candidate revision close the observed prepublication gaps using existing services. Correction retains the memory draft while invalidating evidence, and leaving discards it. Existing terminal history comes only from server data. All six declared/resolved locations, agent identity, recognized runtime/model/egress and reference names are reviewed. Documents and current component architecture/context agree. The 12 authored paths stay below 20; five generated paths are deployable UI assets. No unrelated ticket, migration, portability/cloning, dependency/version/publication expansion is present.

## Implementation quality: approved

Question: Does the candidate fail closed at its trust boundaries, preserve security/concurrency contracts and provide sufficient maintainable offline verification?

Evidence: Hunk-by-hunk API/UI/test review confirms Admin/CSRF before probes; typed malformed input and revision rejection; secret-free allowlist; absolute/non-root paths; corrupt/active/locked state rejection and overlapping ownership checks; reinspection under enrollment/conductor locks before exact-byte write, pause and metadata publication; retained rollback. Browser generation/ref guards, frozen reviewed input, fatal UTF-8 and File rereads reject late/mutated sources and double submit. Existing Pydantic validation rejects malformed UTF-8 description on all three routes (new boundary test; no implementation fix required). Tests exercise public routes and offline injectable command boundaries, including concurrent changes and honest failed/partial evidence. Focused import proof previously 41 passed, supplementary description case passed; 12 import browser journeys, production build/typecheck and whole-software Ruff passed. Final canonical full proof follows this review.

## Inspection and limits

Desktop light and 390px dark review screenshots inspected: readable full locations/settings, focused heading/correction summary and no horizontal overflow; all four locale guidance/focus and other theme widths are automated. This does not establish novice live usability, full WCAG conformance or live forge/container/model acceptance. Physical path-target change is simulated through Path.resolve to avoid platform symlink privilege requirements.

Full generated JS/CSS/HTML scanned using the four built-in AEGIS secret patterns. Zero private-key, AWS-style or bearer/API-token matches. Five password-literal matches in JS are the React password input type map and four translated password labels; no credential values. Generated legal stamping is preserved. Vite's existing chunk-size advisory remains nonfatal; no chunk threshold/config was weakened.

No relevant accepted defect, scope/design deviation or weakened verification. Historical catalog advisories are outside this candidate and will be named in final proof.

## Round 2 correction and renewed verdicts

The first final gate passed Python (865 passed, 1 skipped) and lint but failed frontend (42 passed, three locale failures). Import locale tests incorrectly used localStorage while the full-suite shared account already had a saved English preference. Tests now set the real account language through the authenticated CSRF-protected preference API, assert its success, and reset to English after each locale case. Focused Playwright last-run diagnostic is passed with no failedTests; no test process remains. No timeout, assertion or product localization behavior was weakened.

Generated asset traceability is refreshed in the existing styling requirement and the new exact-enrollment requirement; this changes filename references only. Eight stable workflow paths now match the production build.

Specification compliance: approved after rereading the bounded correction, current requirements and original scope; candidate remains issue #8 only with identical product behavior. Implementation quality: approved after separately inspecting the corrected test/account boundary, preserved assertions and unchanged API/UI candidate; full canonical proof is required again. Round 1 verdicts were invalidated before these edits. Corrective cycles used: 1 of 3.
