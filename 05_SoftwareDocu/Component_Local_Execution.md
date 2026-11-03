<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Local execution

## 1. Purpose

Run the build's managed Pi on Windows or Linux using the existing native
process ownership and AEGIS contracts.

## 2. Responsibilities

- `pi_installation.py` resolves server Node, pins npm packages, verifies the
  candidate and publishes one versioned prefix. The install runner never needs
  a model credential.
- `local_execution.py` pins the native policy and binds AEGIS file execution
  and Pi RPC to an owned run. It builds the account environment and redacts
  only approved injected credentials.
- `local_process.py` and `local_child.py` enforce assignment and durable lease
  recording before releasing native argv. The controller owns final drainage.

## 3. Implementation Overview

`LocalTarget.pi_session` creates a fresh agent directory outside the worktree.
It writes ADORE-generated model and web documents only, then lends owned
binary pipes to the shared RPC launcher. Windows forwards explicit standard
handles through the supervisor and offers Pi's PowerShell tool. Linux execs
the exact native Node in the delegated scope. Normal exit, timeout and
cancellation all confirm process tree drainage.

## 5. Inputs And Outputs

The server configures Node and Linux delegation. The profile supplies only
the current account and optional project tool PATH in `[local]`, plus the
usual provider/model and credential selection. The backend retains no
personal Pi settings or auth and emits only closed prerequisite causes.

## 6. Data Contracts

The local plan binds machine/account, sanitized environment, Node and Pi
file identities and existing run ownership. Config and stored plan readers
refuse unsupported fields. ADORE does not repair stored data automatically.
AEGIS uses the existing strict file exchange; Pi uses shared bounded,
redacted RPC evidence and cumulative token accounting.

## 9. Validation And Tests

`test_pi_installation.py` uses fake npm and Node to prove install, validation,
publication failure and pin changes. `test_local_execution.py` exercises the
Windows/Linux control paths and fake Pi RPC, including hostile personal
configuration, redaction and closed readiness diagnostics. The native and
container model connection checks use the same RPC challenge contract.
