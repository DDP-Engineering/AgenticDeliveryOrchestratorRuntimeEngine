<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# W10 / issue 14 verification

Baseline: task/adore-web-interface, f1aeefa0ca49038c2d70c9987bbaffa6644c61b5.
Authorized scope is exactly issue 14; no runtime migration, #15 layout work,
message counting, dependency/version change, publication or live acceptance.

Criterion | Observed contract and proof
--- | ---
1 Shared scope | API Scope, canonical half-open UTC bounds, matching metric/usage/CSV and empty-export metadata; DST fixture and Chromium statistics journey; cards/project/repository rows consume scoped totals.
2 Cross-period | First picked and matching terminal events supply lifecycle dates, consumption owns its event instant; checkpoint is not terminal. Half-open tests expect period 7, lifetime 18, started 0, failed/completed 1.
3 Honest coverage | Unknown token fields are individually null, zero explicit observations are 0, invalid legacy dates are unallocated, summary-only positive evidence retains source, read failures are typed; summary/runtime removal test preserves history without current stock.
4 Financial boundary | Assigned Dev metric/usage/per-job JSON and all project CSV exports contain no financial fields; forbidden/ungranted/global routes fail; browser pooling preserves absence. Admin reported/estimated values remain separate.
5 Replay/identity/DST | Existing duplicate usage/observation tests plus conflicting timestamp/state cursor tests; same run IDs in two immutable projects; 23/25-hour local-midnight fixtures; endpoint exclusion and composite CSV.
6 Typed corrupt inputs | Invalid range/zone/granularity/executor/model; strict raw JSONL/duplicate keys/nonobject/schema/type/amount/replay; read-only SQLite unsupported columns and unchanged hash; nonfinite accumulation and local-calendar overflow negatives return 422/503.
7 Rates/samples | First review/validation cohorts and reviewed human done cohort; actual terminal summary end selects measured zero/120 samples with mean/median 60. Node pools server sample arrays and denominators, rejects inconsistent samples.
8 Current stock | jobs/active/wait/review/terminal now use actual runtime states, independent of interval; historical summaries count no current jobs. Browser review card says Current state.

Commands during build: native uv run pytest -q (1077 passed, 1 skipped),
uv run ruff check . (exit 0), npm run typecheck and npm run build (exit 0),
focused API/pricing/metric suite (70 passed), new analytic suite after coverage
correction (31 passed), Node metric suite (7 passed), targeted Chromium
statistics/DST/CSV journey (1 passed). Final strict proof supersedes earlier
build results after the final source/test changes; see the task's proof JSON.

Pre-implementation failures: DST total 18 versus expected 7; server pooled
sample count 0 versus 3; overflow sum returned 200; retained summary history
missing; review-only period job omitted; local timestamp overflow escaped;
empty global CSV lacked scope; per-job period coverage showed 2 versus 1.
Each became a focused passing assertion. Superseded all-time tests were revised
only under the explicit #14 contract; replay fixtures now preserve identical
saved timestamps and merge samples require actual review/done evidence.

Semantic inspections: all touched executable hunks and new analytics reviewed;
financial field construction/redaction traced through nested JSON and CSV;
source validation precedes period/filter exclusion; CLI summary read/export
unchanged; readonly SQLite hash preserved. Python/Doxygen and legal prologues,
four-locale changed copy, generated assets and ownership boundaries reviewed.
Project/environment context reconciled; no toolchain change required.

The fixture browser and all unit tests use local retained data/faked runners.
No real executor, external API invocation, live credential/container/forge
acceptance, novice acceptance, or message telemetry was claimed. Human delivery
instruction and coordinator exact inventory verification remain required.

## Corrective review cycle 1

Round-1 strict proof: Python 1080 passed/1 skipped and lint passed; frontend
86 passed/1 failed. The new browser selector matched an administrator global
response mapping as well as the intended project response. It now binds the
exact immutable project API path, retaining all scope/CSV/current-state oracles.
A revision timestamp at the representable calendar edge separately reproduced
an unhandled local conversion (one failed negative case); shared Scope.local_day
now raises the same typed error for usage grouping and revision dates.
The old proof and round-1 candidate are historical; both current verdicts were
invalidated. Focused API/Chromium/Ruff proof and round-2 reviews precede fresh
strict proof. No contract, verification expectation or scope was weakened.
