<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project the recorded Direct attempt to authorized job details

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-DATA-08ed925c](../requirements/data/REQ-DATA-08ed925c.toml) — Project the recorded Direct attempt to authorized job details

When an authorized job detail read succeeds for a Direct run, the service shall expose only its validated recorded build-attempt number, using null when no launch was recorded, through read-only local snapshots with the existing project authorization and redaction boundaries.

Verification scope: Read a saved Direct run as an authorized administrator and assigned developer; assert the recorded attempt or null. Refuse malformed selected state or journal evidence without writes or external commands; deny unauthorized project reads.

### [REQ-UX-1b6f2a83](../requirements/ux/REQ-UX-1b6f2a83.toml) — Keep an unrecorded direct attempt explicitly unavailable

When a direct job has no recorded executor stage-launch attempt, its Jobs page shall identify the attempt number as unavailable rather than invent an ordinal from failed attempts or cumulative launches.

Verification scope: Persist/read a direct job with no launch journal and nonzero cumulative launches or failure count, then open its offline Jobs detail; assert the localized unavailable attempt indication rather than zero, one or a derived count, while a present malformed launch attempt is rejected instead of treated as absent.

### [REQ-UX-46c09118](../requirements/ux/REQ-UX-46c09118.toml) — Reject malformed direct evidence in the browser

If a direct job detail response contains malformed attempt or verification evidence, the Jobs browser reader shall reject that response into the existing error state without presenting a fabricated result.

Verification scope: Read valid absent, unconfigured, passed, failed and timeout controls; mutate evidence types, required fields, status agreement, counter range, text bounds and duration independently in model tests, then inject corrupt direct evidence in Jobs e2e after a valid detail to assert an error and hidden stale evidence.

### [REQ-UX-ef06a3c7](../requirements/ux/REQ-UX-ef06a3c7.toml) — Show the recorded direct attempt number

When a direct job has a recorded executor stage-launch attempt, its Jobs page shall show the latest recorded attempt number with a localized label in English, French, German and Romanian.

Verification scope: Persist direct stage-launch events with known attempt values, read detail through the offline API/model and open Jobs; assert the latest saved attempt, including a first attempt and a later attempt whose number differs from cumulative launches and current failed-attempt count, and reject boolean, zero, fractional or unsafe numeric attempt evidence.

## Implementation

- `04_Software/adore/web/app.py`
- `04_Software/adore/web/jobs.py`
- `04_Software/tests/test_web_jobs.py`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/e2e/server.py`
- `04_Software/web/src/JobWorkspace.tsx`
- `04_Software/web/src/jobCopy.ts`
- `04_Software/web/src/jobModel.ts`
- `04_Software/web/tests/jobs.test.mjs`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_jobs.py`
- `04_Software/tests/test_web_jobs.py::test_direct_absent_launch_does_not_guess_from_other_counters`
- `04_Software/tests/test_web_jobs.py::test_direct_corrupt_evidence_refuses_lists_and_details_without_repair`
- `04_Software/tests/test_web_jobs.py::test_direct_saved_evidence_is_authorized_redacted_and_read_only`
- `04_Software/web/e2e/jobs.spec.ts`
- `04_Software/web/tests/jobs.test.mjs`
