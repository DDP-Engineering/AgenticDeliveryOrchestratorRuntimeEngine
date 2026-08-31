<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Orchestrator

## Purpose

`04_Software/adore/orchestrator.py` is the deterministic conductor around an
agent-operated AEGIS task. It selects eligible tickets, provisions isolation,
runs one fresh executor session per stage attempt, and persists enough state to
recover visibly after interruption.

## Workflow ownership

The conductor owns ticket claiming, worktrees/containers, AEGIS task binding,
budgets, retries, clarification parking, notifications/outbox replay,
validation, candidate fingerprinting, and draft-only MR/PR publication. AEGIS
owns journal content and governance checks; the executor performs bounded code
work; forge adapters perform remote operations. ADORE never merges and never
hands forge credentials to an executor. Each stage prompt also forbids AEGIS
0.9.0 child task journals (`task --parent`): the conductor pins exactly one
task per run and reads only that journal, so work in a child would be invisible
to stage supervision.

## Recovery and delivery contract

Lifecycle state (`working`, parked, approval, publishing, review, terminal)
is separate from the AEGIS stage. Stage failures, transient infrastructure
retries, questions, typed AEGIS timeouts, and typed executor timeouts are
classified independently and journaled. Failed resources are preserved for
operator recovery. Strict verification and a fresh approval must match the
exact candidate fingerprint before a push or a draft MR/PR; any drift forces
re-conduction.

## Requirement coverage

- `REQ-FUNC-ff7dad34` - candidate-bound approval and draft-only publication.
- `REQ-FUNC-83133b5e` - deterministic stage failure and timeout recovery.
- `REQ-FUNC-1ec4a21d` - durable, idempotent notification outbox replay.

## Dependencies and verification

The `Orchestrator` composes config, state store, AEGIS client, executor,
isolation, forge adapters, identity, metrics, and utilities through injectable
seams. `04_Software/tests/test_orchestrator.py` covers full/quick paths,
recovery limits, clarification, outbox replay, ticket/MR reconciliation,
approval freshness, timeout classification, cleanup protections, and the
absence of merge behavior.
