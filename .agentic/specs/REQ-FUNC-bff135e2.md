<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Settle timed-out container commands before reuse

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-DATA-62052e16](../requirements/data/REQ-DATA-62052e16.toml) — Preserve the original timeout result after container recovery

After successful timeout recovery, the execution backend shall return the original command's timeout status and result data unchanged.

Verification scope: Public bound-target tests compare timeout, exit and captured stream fields before and after successful recovery, including a timeout carrying a nonstandard exit; normal non-timeout exit 124 remains a non-timeout result.

### [REQ-FUNC-bff135e2](../requirements/functional/REQ-FUNC-bff135e2.toml) — Settle timed-out container commands before reuse

When a bound container command reports a timeout, the execution backend shall quiesce that command's remaining container processes before admitting a subsequent bound command.

Verification scope: Offline public bound-target tests inject a timeout and observe verified quiescence before later execution; ordinary completion and a normal exit 124 do not trigger timeout recovery. Controlled disposable Docker acceptance confirms the original timed-out writer is absent before a later command.

### [REQ-REL-d8e08cca](../requirements/reliability/REQ-REL-d8e08cca.toml) — Preserve owned container state during timeout recovery

During timeout recovery, the execution backend shall preserve the original container identity, image, persistent filesystem and configured execution authority.

Verification scope: Offline lifecycle tests admit same-resource recovery without create/remove/policy mutations; controlled Docker acceptance compares resource/image/network/user identity and a filesystem marker before and after recovery.

### [REQ-REL-ea593cbb](../requirements/reliability/REQ-REL-ea593cbb.toml) — Reject unsafe container timeout recovery evidence

If container identity or timeout recovery cannot be confirmed, the execution backend shall reject further bound execution with a typed recovery error.

Verification scope: Injected runtime tests provide changed resource/image identities, corrupt receipts and failed interruption or restart; observe a typed recovery error without signalling a replacement or dispatching a later bound command.

## Implementation

- `04_Software/adore/execution.py`
- `04_Software/adore/executor/launcher.py`
- `04_Software/adore/orchestrator.py`
- `04_Software/adore/release_notes.toml`
- `04_Software/adore/web/static/assets/`
- `04_Software/adore/web/static/index.html`
- `04_Software/web/src/help/content/de/jobs.md`
- `04_Software/web/src/help/content/en/jobs.md`
- `04_Software/web/src/help/content/fr/jobs.md`
- `04_Software/web/src/help/content/ro/jobs.md`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_container_timeout.py::test_bound_commands_address_the_admitted_immutable_id`
- `04_Software/tests/test_container_timeout.py::test_changed_caller_pins_cannot_restart_pending_recovery`
- `04_Software/tests/test_container_timeout.py::test_failed_admission_stays_blocked_until_operator_uses_a_fresh_backend`
- `04_Software/tests/test_container_timeout.py::test_normal_provision_resumes_a_confirmed_timeout_resource`
- `04_Software/tests/test_container_timeout.py::test_operator_interrupt_during_restart_prevents_executor_dispatch`
- `04_Software/tests/test_container_timeout.py::test_operator_stop_cancels_pending_automatic_restart`
- `04_Software/tests/test_container_timeout.py::test_ordinary_exits_do_not_trigger_timeout_recovery`
- `04_Software/tests/test_container_timeout.py::test_pi_rpc_timeout_settles_container_before_next_gate`
- `04_Software/tests/test_container_timeout.py::test_recovery_preserves_timeout_result_fields`
- `04_Software/tests/test_container_timeout.py::test_rpc_timeout_does_not_interrupt_a_replacement_after_unpinned_spawn`
- `04_Software/tests/test_container_timeout.py::test_timeout_parks_then_resumes_the_original_container`
- `04_Software/tests/test_container_timeout.py::test_unconfirmed_recovery_is_terminal_without_another_executor_attempt`
- `04_Software/tests/test_container_timeout.py::test_unconfirmed_restart_blocks_the_next_executor`
- `04_Software/tests/test_container_timeout.py::test_unconfirmed_timeout_cleanup_blocks_later_bound_execution`
- `04_Software/tests/test_container_timeout.py::test_untrusted_initial_identity_dispatches_no_command`
