<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable settings candidate review

Task TASK-c4655839; W05 #9 only. Two separate primary-agent passes, no external reviewer, subagent or additional executor. Human maximum: three corrective cycles; used one. Current round: 2.

Exact current bound candidate: `31a9c5bd01e59c041f1f4b5140562f35aa01fb5d568ff0f6c8ce5824ff3655e1`. Base HEAD: `7b4caea6f031f3f535456671baa8eb4640baa434`. Inventory: portable-candidate-inventory.json. Reporting metadata is excluded to avoid circular binding; it changes no behavior or contract.

## Specification compliance: approved

Re-read live issue and epic history, three active requirements, pre-build exact format spec, Frame and Design; reviewed the complete scoped diff and new files. All seven live criteria map to public tests/inspection in portable-verification.md. Complete 16-field closed allowlist, deterministic export and compatible roundtrip, strict typed rejection, exact installed source version and no migration/version duplication are implemented. No portable enrollment/import/clone write or later-ticket scope. Exact TOML/CSV remain distinct; pending/profile/state/access data and credential/endpoint references are omitted. Product/component/context/knowledge and generated-directory traceability agree with the candidate. Architecture diagrams match the component seams and retained proposal.

## Implementation quality: approved

Separately reviewed source structure recognition before the lenient loader, existing configuration validation, finite numeric/list bounds, duplicate rejection at all JSON depths, complete field validation, canonical digest and value-free errors. Temporary snapshots are bounded and cleaned; runtime code is portable stdlib. Reviewed Admin guard before lookup, fixed attachment/no-store and stale-checksum rejection, immutable project identity recheck after snapshot, and tests that simulate replacement. Scoped React state/ref/abort/unmount controls reject late results, errors clear previews, download saves freshly verified exact server bytes; strict helper handles fractional/exponent integer folding. Reviewed all new public Python/helper/browser tests and existing-contract regression evidence. Representative 390px theme captures and four-locale keyboard assertions support bounded usability evidence. No weakened assertions, new dependencies, unrelated code or planning edits. Full proof must still pass after these verdicts.

## Round 1 retained history

Candidate `72e493f8cc7607f9376a85a7014d02043e05a3da89500062ce5ba7f15fcbb3fc`: spec approved; quality changes_required. Findings: recheck immutable ownership after snapshot/export; replace dense nested scalar-validation ternary. One scoped correction cycle introduced the genuinely failing HTTP race test (200 instead of 409), then implementation/docs correction and 55 passing public Python tests, two helper tests, typecheck/build/Ruff. Both verdicts were invalidated during editing and freshly issued above for round 2.

## Limits

The earlier unchanged heartbeat timing failure and successful isolation rerun remain recorded, with final serial strict proof decisive. Existing deprecation/build-size/color and historical workflow advisories are classified separately. No live infrastructure, participant study or comprehensive WCAG/external-review claim. No publication approval is inferred from a verdict; coordinator inventory verification and delivery instruction remain pending.

## Final bound proof

Final strict command exited 0 with strict.passed=true, zero errors and seven
classified advisories: 1013 Python passed/1 platform skip, Ruff passed, frontend
validate passed with 73 Chromium scenarios. Full proof and bundle scan gaps were
independently inspected; historical advisories and earlier unchanged heartbeat
failure are retained in portable-verification.md/journal. All 35 bound entries
remain byte-identical to the reviewed candidate after proof. Reporting updates
here change no candidate source, tests, requirement, spec, knowledge or build.
