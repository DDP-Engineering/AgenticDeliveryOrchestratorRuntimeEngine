<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Gates (`adore/gates.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/gates.py` - file version 0.1.2.
> Design: Orchestrator_Design_And_Decisions.md section 7/7a.

## 1. Purpose

The conductor's own verification layer: thin wrappers around the target
repository's `.agentic` workflow CLI. The executor runs the CLI itself during
a gate; the orchestrator re-checks with the same CLI afterwards - the
objective signal is the exit code, never the executor's word.

## 2. Responsibilities

- `run_workflow_cli(execute, *args)` - one CLI invocation inside the run's
  container (`bash .agentic/tools/run.sh <args>`; bash because run.sh uses
  `pipefail`, spike finding 2026-07-03; single-token argv, WSL-safe).
- Named wrappers for the design verbs: `invariants` (the between-gates
  check), `workflow_status`, `workflow_resume` (the read-only bootstrap brief
  used to orient a freshly launched executor session on a relaunch),
  `gates_run` (post-merge retest, delivery step 3), `delivery_preflight` (the
  authoritative "done" signal, delivery step 4).
- `workflow_resume` is best-effort and payload-agnostic: a workflow CLI that
  predates the `resume` verb exits non-zero, which the orchestrator treats as
  "no brief" rather than an error - so the wrapper stays compatible with older
  target-repo payloads.
- `GateResult(ok, exit_code, output)` - failure is data; the conductor
  decides retry/escalate.

Explicitly not owned: what to do with a result (orchestrator) and running
gates themselves (executor).

## 3. Implementation Overview

One function, three named wrappers; no state. Commands run through the
injected exec seam in the container working dir (`/adore/work`), where the
target repo's Python/uv toolchain exists.

## 4. Dependencies

- Internal: `adore.executor.base.ExecTarget`, `adore.util.CommandResult`.
- External: the `.agentic` CLI shipped inside the target repo worktree.

## 5. Inputs And Outputs

- Inputs: CLI verb + arguments, a bound exec seam, a timeout.
- Outputs: `GateResult` per invocation.

## 6. Data Contracts

- Entry point constant: `.agentic/tools/run.sh` (`WORKFLOW_CLI`).
- Exit code 0 = pass; anything else = fail (data, not an exception).

## 7. Workflow Integration

Called by the orchestrator after every executor gate (design 7a step 4) and,
in phase 4, as the delivery-preflight loop condition (design 11a step 4).

## 9. Validation And Tests

- `tests/test_gates.py`: bash + single-token argv shape, failure-as-data,
  wrapper-to-verb mapping (`invariants`/`status`/`resume`/`delivery-preflight`).
- **To confirm in the live pilot:** the exact CLI verbs (`invariants`,
  `delivery-preflight`) against the real workflow CLI; only `status` is
  live-verified so far (spike section 14).
- Minimum validation after a change: `uv run --group dev pytest tests/test_gates.py`.

## 10. Limitations And Future Work

- Verbs beyond `status` are design-doc names pending live confirmation.
- `gates run` / audit verbs join with the delivery phase.
