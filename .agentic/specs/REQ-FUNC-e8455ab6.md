<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Read globally ordered authorized job pages

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-DATA-0ba9e469](../requirements/data/REQ-DATA-0ba9e469.toml) — Expose persisted job evidence with honest unknowns

When a job read succeeds, the service shall expose exact persisted lifecycle, AEGIS stage, outcome, last activity and available ticket/title/wait/action/responsibility/evidence links, with explicit unknown coverage for evidence and consumption that was not recorded, using local snapshots without invoking external commands. A run state with an empty created_at or updated_at shall fail closed as run_state_corrupt.

Verification scope: Persist ticket and parked/approval evidence and read the public endpoints with a runner that fails on calls; assert observed evidence, safe links, exact stage/outcome, unknown person/consumption and missing wait timestamps; a project summary over a run without an aware updated_at answers 503 run_state_corrupt.

### [REQ-FUNC-e8455ab6](../requirements/functional/REQ-FUNC-e8455ab6.toml) — Read globally ordered authorized job pages

When an authenticated caller reads jobs, the service shall return a complete globally filtered and deterministically ordered page across authorized current and archived projects, identified by project_id and run_id, with matching totals, status groups and an optimistic source revision that rejects changed sources on continuation.

Verification scope: Create colliding runs across projects, request pages/search/groups and compare exact identities/totals; deny unassigned direct/project/search reads and reject stale revision, invalid filters and concurrent source changes.

### [REQ-SEC-5d0f86e7](../requirements/security/REQ-SEC-5d0f86e7.toml) — Fail closed on corrupt job read evidence

If any authorized job source is malformed, unsafe or unreadable, the job service shall reject the read with a typed secret-free error and no partial totals, while keeping persisted state and existing operational journal recovery unchanged.

Verification scope: Corrupt state, ticket, journal, timestamps and URLs independently; public reads return 503 codes without sensitive source values or totals; compare original bytes and verify unauthorized corrupt run sources are never read.

## Implementation

- `04_Software/adore/web/app.py`
- `04_Software/adore/web/jobs.py`
- `04_Software/adore/web/static/`
- `04_Software/adore/web/static/index.html`
- `04_Software/tests/test_web_jobs.py`
- `04_Software/web/src/errors.ts`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_web_jobs.py::test_all_lifecycle_groups_exact_stage_review_and_redaction`
- `04_Software/tests/test_web_jobs.py::test_bad_state_metadata_is_typed`
- `04_Software/tests/test_web_jobs.py::test_broken_runs_root_symlink_fails_closed`
- `04_Software/tests/test_web_jobs.py::test_corrupt_authorized_evidence_has_no_partial_totals_or_secrets`
- `04_Software/tests/test_web_jobs.py::test_corrupt_profile_decoding_is_typed_on_global_project_and_direct_reads`
- `04_Software/tests/test_web_jobs.py::test_developer_scope_precedes_reads_counts_search_and_details`
- `04_Software/tests/test_web_jobs.py::test_direct_corrupt_evidence_refuses_lists_and_details_without_repair`
- `04_Software/tests/test_web_jobs.py::test_empty_project_and_absent_default_state_root`
- `04_Software/tests/test_web_jobs.py::test_free_text_masks_entire_quoted_and_authorization_credentials`
- `04_Software/tests/test_web_jobs.py::test_global_pages_search_groups_and_collision_identity`
- `04_Software/tests/test_web_jobs.py::test_invalid_job_queries_fail_closed`
- `04_Software/tests/test_web_jobs.py::test_page_revision_rejects_source_changes`
- `04_Software/tests/test_web_jobs.py::test_persisted_wait_evidence_unknowns_archive_and_last_activity`
- `04_Software/tests/test_web_jobs.py::test_project_summary_refuses_a_run_without_an_aware_activity_time`
- `04_Software/tests/test_web_jobs.py::test_source_mutation_during_read_is_rejected`
- `04_Software/tests/test_web_jobs.py::test_stale_parked_questions_are_unknown_for_new_wait`
- `04_Software/tests/test_web_jobs.py::test_unreadable_source_and_orphan_run_are_not_empty_success`
- `04_Software/tests/test_web_jobs.py::test_unsafe_urls_fail_closed_without_exposure`
- `04_Software/tests/test_web_jobs.py::test_wait_locations_respect_forge_and_reads_launch_no_commands`
