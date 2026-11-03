<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local execution

## Routing

Use `pi_installation.py` for the installer or Node diagnostics;
`local_execution.py` for the account, managed Pi and native readiness;
`local_process.py` and `local_child.py` for owned process control.
Focused proof: `test_pi_installation.py` and `test_local_execution.py`.

## Purpose and boundaries

Native projects run managed Pi RPC and AEGIS under the current service account.
The orchestrator owns job state and delivery. The operator owns project tools,
Node availability and Linux delegation.

## Public interface

The installer exposes `install_pi`, `verify_pi`, `managed_pi` and typed
`PiInstallationError`. LocalBackend implements the shared lifecycle;
LocalTarget lends scoped RPC pipes through `pi_session` and retains the strict
AEGIS file transport. `probe_local_executor` reports closed readiness causes.

## Invariants

- The service environment selects an absolute Node 22 executable. The build
  selects a versioned Pi prefix under ADORE home. No global Pi or npm shim.
- Installation invokes npm with exact package pins in a temporary sibling
  directory and publishes only after verification. Existing pins stay intact.
- The project config selects the current account and optional project tool PATH.
  Linux delegation comes from the service. The policy pins the effective
  environment, Node and managed CLI file identity.
- The native release barrier records scope ownership before project code runs.
  A fresh agent directory outside the worktree disables personal and untrusted
  project resources. Approved provider credentials are injected and redacted.
- An owned process scope must drain before reuse; unknown or foreign scope
  evidence is refused. A worktree is not a host sandbox.

## Key behaviors

The shared Pi RPC client sends prompts via stdin, aborts on time limits or cancel
and retains bounded usage and output. Windows selects PowerShell and forwards the
three owned standard handles through the Job supervisor. The readiness probe
makes no model request. The explicit model probe uses the same managed RPC
scope, with up to 1 MiB of transient output to prove the shell and final reply.
Explicit Retry retains the durable worktree and rechecks native tools.

## Files

- `04_Software/adore/pi_installation.py` and `executor/adore-guard.ts`
- `04_Software/adore/local_execution.py`, `local_process.py`, `local_child.py`
- `04_Software/tests/test_pi_installation.py`, `test_local_execution.py`
- `05_SoftwareDocu/Component_Local_Execution.md`
