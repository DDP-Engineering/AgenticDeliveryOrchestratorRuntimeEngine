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

Native projects run managed Pi RPC, AEGIS and configured direct verification
under the current service account.
The orchestrator owns job state and delivery. The operator owns project tools,
Node availability and Linux delegation.

## Public interface

The installer exposes `install_pi`, `verify_pi`, `managed_pi` and typed
`PiInstallationError`. LocalBackend implements the shared lifecycle;
LocalTarget lends scoped RPC pipes through `pi_session` and retains the strict
AEGIS file transport. `LocalTarget.run_verification(command, *, timeout)` accepts
only the exact nonempty configured single-line NUL-free workflow command;
`probe_local_executor` reports closed readiness causes.

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
  evidence is refused. A worktree is not a host sandbox. Verification shell
  commands have service-account filesystem/credential/network authority, without
  container isolation; dedicated least-privilege accounts are recommended.
- Ordinary native argv still refuses shell/wrapper executables. Only configured
  direct verification selects the absolute bound SystemRoot/System32/cmd.exe
  on Windows or /bin/sh on Linux, never project PATH/COMSPEC.
- Native Python standard streams use authoritative `PYTHONIOENCODING=utf-8` on Windows/Linux. Ambient Python flags remain
  filtered; invalid UTF-8 evidence is still a typed failure, never replaced.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Managed Pi install/readiness | `pi_installation.py`, `probe_local_executor` | `test_pi_installation.py`, `test_local_execution.py` |
| Configured direct shell verification | `LocalTarget.run_verification`, `local_child.main` | native verification, quoted-command and malformed-transport tests in `test_local_execution.py` |
| Owned scopes, timeout and capture | `LocalProcessController.run_files`, `NativeScopes` | native capture/ownership/PID-birth/cleanup tests in `test_local_execution.py` |
| Explicit Retry identity refresh | `LocalBackend` retry revalidation | `test_retry_revalidation.py` |

## Key behaviors

- `REQ-PLAT-a39ffa22`, `REQ-SEC-d94baaf1`, `REQ-SEC-c81de547`: direct-only
  verification validates command and pinned identity before the owned release
  barrier, then uses worktree cwd and bound environment with caller timeout.
  Windows alone marks the trusted non-RPC envelope, validates its cmd transport
  and pins the executable while passing raw `/d /s /c` text inside one extra
  outer quote pair; ordinary argv/RPC retain list serialization. Invalid requests,
  unavailable shell, identity drift or malformed transport cannot launch work.
- `REQ-DATA-72e08277`, `REQ-REL-50474528`: verification opts into strict UTF-8
  rolling tails, at most 64 KiB per stream, with ANSI/NUL removal and known-value
  overlap/token/header redaction before eviction. Default prefix capture is
  unchanged. Success, failure and timeout confirm owned descendant drain;
  invalid UTF-8 or unconfirmed cleanup is a typed LocalExecutionError.
- `REQ-SEC-a751eb18`: operator/component guidance describes service-account
  permissions without host/container sandboxing and keeps ordinary shell refusal.

Native ChatGPT uses `chatgpt.helper_for` and managed Node/Pi, without Docker.
One ADORE-owned sign-in supplies temporary tokens to explicitly bound stage
and model targets, with native evidence redaction. Readiness reads the stored
status without refreshing or calling a model. Missing/rejected credentials
prevent Pi launch. Host network and owned-process scope policy stay in force.
Offline proof: `tests/test_native_chatgpt.py` and `tests/test_web_chatgpt.py`.

The shared Pi RPC client sends prompts via stdin, aborts on time limits or cancel
and retains bounded usage and output. Windows selects PowerShell and forwards the
three owned standard handles through the Job supervisor. The readiness probe
makes no model request. The explicit model probe uses the same managed RPC
scope, with up to 1 MiB of transient output to prove the shell and final reply.
Explicit Retry retains the durable worktree and rechecks native tools.
The effective encoding settings participate in the pinned environment;
explicit Retry refreshes this volatile fingerprint under existing ownership checks.

## Files

- `04_Software/adore/pi_installation.py` and `executor/adore-guard.ts`
- `04_Software/adore/local_execution.py`, `local_process.py`, `local_child.py`
- `04_Software/tests/test_pi_installation.py`, `test_local_execution.py`
- `05_SoftwareDocu/Component_Local_Execution.md`

## Explicit saved-ownership cleanup

LocalBackend.for_cleanup avoids current executable/environment resolution and grants no execution authority. remove_owned validates exact saved resource, saved policy fingerprint, current host/account, dedicated state/IO paths and durable process leases before interruption/drain and receipt removal. Normal execution and Retry identity checks remain unchanged. NUMBER_OF_PROCESSORS/PROCESSOR_* participate in volatile native environment identity. Proof: tests/test_drift_recovery.py and test_retry_revalidation.py.

Native Pi argv forwards the selected thinking level for stages and connection checks.
