<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Persist Direct implementation completion before validation settlement

This specification describes the current implemented contract.

## Behavior and boundaries

### [REQ-FUNC-21ae8007](../requirements/functional/REQ-FUNC-21ae8007.toml) — Persist Direct implementation completion before validation settlement

When a Direct implementation attempt settles successfully, makes product progress and has no blocking questions, the conductor shall durably record completed implementation and enter validate before checkpointing the candidate and reaching done. Recovery after that durable completion shall settle the candidate without launching another implementation.

Verification scope: Exercise successful Direct implementation and interrupted completion settlement; inspect saved completion, validate/done progression and recovery without another Pi launch. Executor failures, questions and absent product progress cannot authorize completion.

## Implementation

- `04_Software/adore/orchestrator.py`

## Associated tests

These links identify test definitions; they are not a claim that a test run passed.

- `04_Software/tests/test_orchestrator.py::test_direct_artifact_and_git_failures_preserve_cause`
- `04_Software/tests/test_orchestrator.py::test_direct_completion_save_interruption_recovers_at_launch_limit`
- `04_Software/tests/test_orchestrator.py::test_direct_one_session_reaches_unverified_approval_and_publication`
