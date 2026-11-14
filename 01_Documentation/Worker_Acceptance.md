<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Integrated worker acceptance

This inventory records WK-07 (#90, umbrella #83), TASK-50d7f4bf, against local
base `e0a62729cf0391ea5d1fb9ad56d064ec3fd3b636`, on 2026-11-14. The application
version remains 0.15.0. Every contract below was executed in this acceptance
pass. Reading earlier tests alone is not counted as acceptance. All homes,
workers, credentials and resources used by the proof are disposable fixtures.

## Contract matrix

Test names below are in `04_Software/tests/`. The seven-module command in the
next section executes every named worker/configuration/ownership/resource test,
including its parameterized negative cases, without collecting unrelated tests.

| Criterion | Executed test / observable oracle |
| --- | --- |
| A/B N=1; A N=2; third admission waits | `test_web_supervisor.py::test_actual_project_and_pool_overlap` (both parameters): file barriers, different live PID/birth pairs, no executor exit before release, third at capacity, B finishes while A is blocked. |
| B/global settings while A executes; scoped staging | `test_worker_acceptance.py::test_blocked_executor_keeps_scoped_settings_and_peer_execution_independent` (Direct and AEGIS): HTTP 202 then actual B save result/revision; global audit policy applies; A unsafe edit remains staged with 409 and original active bytes; real B completes before A's barrier is released. |
| Settings/control while A prepares/checks tools | `test_web_configuration_worker.py::test_managed_image_build_is_durable_lock_free_and_independent`, `test_slow_native_settings_plan_uses_long_lane_and_releases_edit_lock`, `test_blocked_probe_preserves_fast_project_global_and_admission_control`: controlled long boundaries keep B/global and admission controls progressing without edit/admission locks. |
| Manual/automatic duplicate admission | `test_run_concurrency.py::test_manual_and_automatic_admission_keep_ticket_unique_during_initialization`, `test_admission_only_is_atomic_and_pause_preserving`: one durable run during competing admission; explicit Start preserves monitoring pause. `test_web_commands.py::test_authorized_start_uses_explicit_ticket_and_deduplicates` executes one Start for the repeated request ID. |
| Retry/Restart, two commands on one run | `test_web_ownership.py::test_retry_and_restart_cannot_claim_same_job_concurrently`, `test_distinct_owners_racing_one_job_have_one_winner`; `test_run_concurrency.py::test_all_resume_boundaries_keep_capacity`, `test_retry_at_capacity_preserves_failed_state`: one claim, no executor at capacity, no destructive restart. |
| Request idempotency and full-pool Cancel | `test_worker_acceptance.py::test_cancel_at_full_real_pool_preserves_peer_and_deduplicates_request`: two real executors entered, duplicate request ID identical, real ProjectWorker dispatch selects only Cancel while another Start stays pending, durable Cancel succeeds, exactly one attempt per run, peer stays inside its executor and later completes. |
| Reduced N, queued initial reservations and pause | `test_web_project_status.py::test_reduced_limit_preserves_reservations_and_bounds_actual_executor_starts` (both parameters): pending reservations start serially under N=1; two already-started children both continue above N=1. `test_staged_reduction_fences_admission_and_preserves_existing_jobs` retains pending dispatch and blocks starts during cleanup. `test_web_supervisor.py::test_project_paused_start_admits_only_and_full_pool_defers_queue` proves explicit paused Start and queued N+1. |
| Busy cleanup still occupies capacity | `test_run_concurrency.py::test_cleanup_keeps_execution_slot_until_backend_stop_finishes`; `test_shared_resources.py::test_project_barrier_checks_terminal_and_removed_execution_slots`, `test_archive_and_profile_deletion_refuse_active_terminal_cleanup`: real held reservation remains authoritative through terminal/missing state. |
| Project-worker crash leaves peers alone | `test_web_supervisor.py::test_supervisor_starts_distinct_project_and_configuration_processes`: actual A replacement, unchanged live B/configuration processes. `test_failed_project_scope_cleanup_preserves_other_worker_processes` quarantines unconfirmed A drain. |
| Supervisor/control crash, fencing and no replay | `test_web_supervisor.py::test_parent_crash_quiesces_tree_and_preserves_uncertain_claim`, `test_transient_command_drains_cancel_or_recovers_after_death`, `test_wrapper_root_crash_does_not_leave_live_descendants`: actual death, bounded descendant drain, uncertain claims retained outside pending queue. `test_web_configuration_worker.py::test_confirmation_failure_after_settings_effect_is_uncertain`, `test_post_effect_deadline_crossing_is_uncertain` preserve unconfirmed external outcomes. |
| Live/unknown owners never become stale | `test_web_ownership.py::test_project_reconciliation_retains_live_and_unknown_run_owners`, `test_stale_heartbeat_and_shutdown_do_not_steal_live_work`; `test_run_concurrency.py::test_two_processes_conduct_one_project_without_stale_diagnosis`, `test_durable_foreign_owner_skips_all_reconciliation`: live peer bytes/lifecycle remain protected. |
| Queued time and retained budgets | `test_run_concurrency.py::test_queued_time_does_not_consume_active_budget`, `test_initial_queue_clock_is_zero_before_dispatch_and_after_cancel`, `test_start_crash_cannot_restore_queued_time_to_retry_budget`: no queued active time, consumed work survives recovery. |
| Simultaneous finalization, metrics and logs | `test_shared_resources.py::test_two_runs_provision_checkpoint_and_finish_without_resource_overlap`, `test_concurrent_metrics_updates_publish_atomic_complete_snapshot`, `test_concurrent_process_log_rotation_keeps_run_attribution`, `test_metrics_delete_and_upsert_publish_one_current_snapshot`: barriers/racing writers retain both rows, complete JSONL mirror and attributed log lines. |
| Resource/auth isolation | `test_shared_resources.py::test_project_namespaces_separate_same_ticket_resources`, `test_cancel_one_run_preserves_peer_worktree_and_runtime`, `test_native_release_preserves_peer_process_scope_and_receipt`, `test_refresh_is_serial_and_tokens_remain_call_scoped`, `test_refresh_failure_releases_common_lock_without_touching_peer_credentials`, `test_container_stop_and_bound_environment_are_run_scoped`: isolated identities, environments/tokens and exact owned cleanup. |
| Rights, revision and corrupt-input boundaries | `test_web_configuration_worker.py::test_queued_actor_revocation_fails_without_credential_disclosure`, `test_authority_revoked_during_model_probe_prevents_evidence_publication`, `test_corrupt_protected_request_is_a_closed_terminal_failure`; `test_web_project_status.py::test_corrupt_inputs_and_unauthorized_scope_fail_closed`, `test_staged_capacity_corruption_blocks_only_its_project`: explicit refusal; no secret disclosure or foreign-project failure. |
| Uncertain publication is never repeated | `test_run_concurrency.py::test_uncertain_publication_is_not_replayed_by_later_polls` refuses repeated remote effects; `test_dispatch_evidence_refuses_corrupt_input_and_uncertain_replay` retains consumed dispatch without granting another launch. |
| Windows state-sharing boundary | `test_state.py::test_state_sharing_contention_is_bounded_and_preserves_evidence` and `test_state_sharing_retry_rechecks_writer_authority`: brief sharing conflicts, including Windows CRT EACCES without winerror, recover within six attempts/250 ms scheduled waits; persistent denial preserves old bytes, removes unpublished temporaries and raises StateError; lost authority blocks delayed publication. Unrelated I/O still propagates. `test_state_listing_propagates_exhausted_sharing_denial` and `test_worker_acceptance.py::test_admission_refuses_storage_loss_between_capacity_scans` keep a pending slot unavailable only on a later scan from being omitted or admitting N+1. |
| Native execution boundary | Selected `test_local_execution.py` cases below: native AEGIS transport, real conductor Retry/park behavior with fake native controller, reused identity/credential refusal and environment filtering. No real Pi/model runs. |
| Container and WSL boundary | `test_shared_resources.py::test_container_stop_and_bound_environment_are_run_scoped` plus four selected `test_isolation.py` WSL tests below: exact runtime argv, drive/mount translation, environment forwarding and allowlist proxy routing. These are injected runtime boundaries, not live Docker/Podman acceptance. |
| GitLab, GitHub and Gitea | Twelve selected `test_forge.py` cases below use fake CLI runners: ready-ticket parsing, draft creation, malformed JSON/shapes, HTTP errors despite zero CLI exit and CLI failures. No live forge is contacted. |

The integrated AEGIS helper supplies quick frame/build/validate/done journal
snapshots on the run's actual branch and rejects independent `check` execution.
The Direct executor supplies its own change/summary. ADORE consumes their
completion evidence; these scenarios never run a target repository's suite.

## Commands and observed results

Run Python commands from `04_Software/`:

```text
uv run --frozen --extra web python -m pytest -q tests/test_worker_acceptance.py tests/test_web_supervisor.py tests/test_run_concurrency.py tests/test_web_configuration_worker.py tests/test_web_project_status.py tests/test_web_ownership.py tests/test_shared_resources.py
```

Result: **234 passed**, exit 0, 110.68 seconds. One existing FastAPI/httpx
Starlette deprecation warning remains.

```text
uv run --frozen --extra web python -m pytest -q tests/test_state.py
uv run --frozen --extra web python -m pytest -q tests/test_isolation.py -k "wsl_mount_path or wsl_runtime_prefixes or wsl_provision or wsl_allowlist"
uv run --frozen --extra web python -m pytest -q tests/test_local_execution.py -k "local_aegis_file_transport or local_conductor_pins_target or local_identity_and_auth_fail_closed or local_scope_control_refuses_reused_process_identity or local_environment_ignores_personal_auth"
uv run --frozen --extra web python -m pytest -q tests/test_forge.py -k "list_ready_maps or open_pr_draft or labels_and_mr or open_pr_wip or invalid_json or unexpected_json_shape or http_error_despite_exit_zero or tea_failure"
uv run --frozen ruff check adore/state.py tests/test_state.py tests/test_worker_acceptance.py tests/supervisor_helper.py
```

Results: **80**, **4**, **12**, **12** passed respectively; focused Ruff passed.
All commands exited 0. The first storage regression run failed with five
expected missing-retry/fencing failures before the product repair; the full
state rerun passed after preserving unrelated PermissionError propagation.

Review round 1 added storage-unavailability listing/admission tests and strengthened
Cancel to go through the actual ProjectWorker dispatch decision, with another
Start pending. The following affected recheck also executes the existing
Start-idempotency contract:

```text
uv run --frozen --extra web python -m pytest -q tests/test_state.py tests/test_worker_acceptance.py tests/test_web_supervisor.py tests/test_run_concurrency.py tests/test_web_project_status.py tests/test_web_commands.py::test_authorized_start_uses_explicit_ticket_and_deduplicates
```

That recheck returned **182 passed, 2 failed**: real Windows CRT opens reported
EACCES without winerror. Four added CRT-shaped cases reproduced the missing
classification (red: four failures). After covering that Windows representation,
the narrow final affected command was:

```text
uv run --frozen --extra web python -m pytest -q tests/test_state.py tests/test_worker_acceptance.py::test_cancel_at_full_real_pool_preserves_peer_and_deduplicates_request tests/test_worker_acceptance.py::test_admission_refuses_storage_loss_between_capacity_scans tests/test_web_project_status.py::test_reduced_limit_preserves_reservations_and_bounds_actual_executor_starts
```

Result: **90 passed**, exit 0, 13.16 seconds, including all **86** state cases.
The scheduler-driven full-pool Cancel and both real-process reduced-limit cases
passed. Storage-unavailable errors now have a StateError subtype propagated
through listings/admission, preserving pending occupancy. Unaffected green
contracts were retained instead of rerun; no scoped failure remains. Focused
Ruff passed again after the review repairs.

From `04_Software/web/`, `node --test tests/help.test.mjs` passed **13** tests.
`npm run build` passed, rebuilding and fingerprinting the committed static
bundle after all four Jobs help locales changed. Its existing large-chunk
advisory remains. No Chromium/global frontend validation ran in this pass.
From the repository root, `python 02_Tools/internal/check_release_notes.py
--since e0a62729cf0391ea5d1fb9ad56d064ec3fd3b636` passed. AEGIS static checking
reported no errors; existing historical path/test-link advisories remain.

## Bounded operational smoke

A one-off operator smoke was executed through host Python on Windows and
`wsl --exec python3 -` on Ubuntu Linux, using auto-cleaned OS temporary
directories. It is not an automated test of deployment/setup scripts.
Each platform used its own CPython/dependencies extracted from the existing
0.15.0 archive, with the current `adore/` application and portable launcher
staged into that disposable extraction. The temporary media inventory was
recomputed for those staged bytes. No final archive was rebuilt or changed.

For each platform, the smoke:

1. Created an isolated home and two paused projects with temporary empty clones.
2. Started the actual portable `launch.py --home <temp-home> --port <free-port> --no-browser --startup-timeout 40 --restart-limit 1` with bundled Python in isolated mode.
3. Observed loopback readiness plus separate supervisor, configuration and two project process identities.
4. Terminated only the configuration process and observed its replacement with both project PIDs unchanged.
5. Killed the supervisor (Windows process termination / Linux SIGKILL), observed the service-pair restart and verified the old tree's PID/birth identities were dead before accepting recovery.
6. Issued the portable `--stop`, observed exit 0 and verified all recorded owned process identities were gone.
7. Removed staging/home automatically and checked the original archive's SHA-256 was unchanged.

Both platforms printed **PASS** for Start/Stop, two-project worker trees and
configuration/supervisor recovery. Initial Windows staging retained obsolete
assets from the archive and failed startup; replacing the disposable application
directory completely corrected that staging error before the successful smoke.
The final Linux smoke used the rebuilt current help bundle.

## Acceptance boundaries and remaining work

Windows x64 ran natively. Linux x64 ran in the installed Ubuntu distribution
under WSL; this proves Linux processes/sessions there, not every bare-metal
Linux/service-manager environment. The smoke exercised the actual portable
launcher with current application bytes and bundled dependencies. It does not
certify the unchanged delivery archives as containing the new worker changes;
release packaging and final-media verification remain separate operations.

No DCP data/application, real forge, provider, Pi session or Docker/Podman daemon
was used. Native Jobs/cgroup and container ownership contracts are simulated
at their adapters; real project execution with host delegation, service-account
credentials and model/runtime access remains operator-owned acceptance.
Four-locale help grammar and the production bundle were verified in the first
acceptance phase. The coordinator activated the final umbrella pass after commit
`f3aa5384936c53cd864bb13b7375c27c552b4498`; the results below supersede the
initial full-suite deferral.

## Final umbrella validation

The full commands ran once each, separately so one failure could not suppress
another suite. No Pi-guard case or other Python case was deselected.

| Check | Observed initial result |
| --- | --- |
| `uv run --frozen --extra web python -m pytest -q -ra --tb=short --durations=15` | Exit 1: 3502 passed, 111 failed, 15 skipped, 0 deselected, 1 Starlette/httpx deprecation warning; 1555.89 s. |
| `uv run --frozen ruff check adore tests` | Exit 0, all passed. |
| `npm test` in `04_Software/web` | Exit 0: 181 passed, 0 failed/skipped/cancelled; includes 13 help tests. |
| `npm run build:e2e` | Exit 0: UI/E2E TypeScript and isolated Vite build/fingerprint; existing large-chunk advisory. |
| `npx playwright test` | Exit 1 at configured 1800 s bound: 175 passed, 24 failed, 116 did not run; 315 selected. Suite and teardown reported two global timeout errors. |
| `python 02_Tools/internal/check_release_consistency.py --require-artifacts` | Exit 0: 0.15.0 metadata, committed frontend fingerprint/fresh temporary build and archive integrity. |
| `python 02_Tools/internal/check_release_notes.py --since 50ac624` | Exit 0; later task-base comparison `--since e0a62729` also passed after the new note. |

The 15 Python skips are Windows prerequisites: unavailable symlink creation,
POSIX executable/PATH semantics and related clone/isolation/cleanup cases. They
were reported by pytest, not hidden through a selection expression. No automated
deployment/setup-script test, real forge, provider, executor or target repository
suite ran.

### Corrections and focused proof

The 111 Python failures included two pre-existing defects listed below. The other
109 now have focused green proof. Three product repairs preserve existing behavior:
queued models retain omitted fields distinctly from explicit null; confirmed
environment preparation keeps its declared 202 success status; private request
directory/write denial returns sanitized 503 before enqueue without changing saved
configuration or credentials. There is no schema change or legacy reader.

Fixtures now consume the actual durable configuration result, select domain audit
evidence independently of operation completion, assert schema 18, bind canonical
retry/container/worktree identities, model per-run CLI locks and queued Cancel,
provide native-plan probe inputs and isolate ambient statistics paths. The local
schema 0 metrics database that exposed the last issue was preserved unchanged.

Focused Python proof after repairs: 62 import/typed-input/credential cases; 126
passing domain/ownership cases plus 2 platform skips (the one remaining environment
status failure was then corrected); 8 CLI mutation cases; 8 native/container
readiness variants; 35 transport/status/role/metrics/configuration-worker cases;
and 9 actual worker overlap/capacity/storage cases. These commands overlap: they
are not added into a fabricated new full-suite total. Changed-file Ruff passed.

The browser fixture now gives project consumers their exact registered owners.
Its existing seed/reset lifecycle removes only terminal simulated Start 42/44
trials, under the same run locks as the fake conductor, with unfinished-operation
and active-owner refusal. It retains operation/audit history and all other runs.
Interceptors consume completed domain bodies; stale browser delivery is delayed
after the old operation releases its protected server resource. Layout checks
measure controls simultaneously and verify a scrolled summary panel's viewport
bounds, retaining its size/alignment limits. Draft and diagnostics tests follow
the current retained-draft and Technical details workflows.

Only the initial 24 failed and 116 unrun Chromium IDs were selected next:
`npx playwright test --last-failed` completed with 128 passed, 12 failed, 0 unrun
in 18.8 minutes. A 12-case focused selection then passed 11 and exposed one remaining role-text
selector error; the final 2-case run passed both the corrected audit selector and
changed malformed-workflow interceptor. The 12-case selection included a repeated
Start 44 across dashboard/jobs to prove fixture reset independence. Across these
recorded runs, 314 distinct original scenarios have green evidence and one baseline
scenario remains failed, with 0 unrun. This is aggregate coverage, not a new full
all-green run. Successful original cases were not rerun as a whole suite.

### Pre-existing failures kept outside WK-07

| Case | Evidence and boundary |
| --- | --- |
| Python `test_pi_installation.py::test_managed_pi_ships_the_reviewed_guard` | Native and container Pi guard sources differ at byte 689. Both sources and test are unchanged across 50ac624..f3aa538. An isolated temporary baseline snapshot reproduces the same assertion. |
| Python `test_web_setting_catalog.py::test_setting_catalog_lists_every_configuration_key` | Setting catalog ordering differs at index 35. Catalog/test are unchanged across the umbrella; an isolated baseline snapshot reproduces it. |
| Chromium `shell.spec.ts` / `glossary defines supported human actions with essential field help visible` | Missing `enrollment-help-url`, `enrollment-help-identity` and URL `aria-describedby`. Test blob is identical at 50ac624; the first-step rendering is identical (SHA256 `7da58849c668a269cf963b8739dcd27d789b58db59627fcd2943e84649e73748`). Active REQ-UX-072cf049/REQ-UX-2761363b and Web Interface guidance still require help. Classification uses identical source and the observed current failure, not a separately executed baseline browser run. |

These are recorded failures, not accepted green checks. Their requirements or
assertions were not weakened to make this worker acceptance appear green. The
complete Python suite and browser suite are therefore not reported as a single
all-green final run. Release acceptance or separately scoped baseline corrections
remain coordinator decisions. No commit, push, merge, delivery archive change or
DCP operation was performed by this validation task.
