<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Installed Executor Discovery

## 1. Purpose

Provide an administrator-only inventory of Pi executables on the ADORE host.

## 2. Responsibilities

`adore/executor_discovery.py` reads bounded absolute PATH and conventional user/npm
locations. It locates Pi native executables or installed Node with known JS
entrypoints. The discovery endpoint returns these paths for inspection.

## 3. Implementation Overview

`discover_executors` reads at most 64 roots and returns at most 12 canonical launches
per agent. Relative paths, project/.git/.agentic trees, unsafe formatting characters,
missing files and Windows shell wrappers are omitted. Known npm layouts supply real
executables or explicit Node/JS argv; no shim contents or credential files are read.
The administrator-only GET route returns Cache-Control: no-store. No command runs.

## 4. Dependencies

Standard library and administrator web authorization. Native execution uses
`local_policy`, the verified managed Pi installation and native process scopes.

## 5. Inputs And Outputs

Host platform, account home and PATH produce `{system, machine, account, executors}`.
Each executor has `agent` and `installations`; each launch has `executable`, nullable
`entrypoint`, `command` with placeholders and `source` (PATH or npm). API routes use
the actual current service account. Injectable filesystem locations support offline
Windows/Linux fixtures.

## 6. Data Contracts

Only administrators can read server launch paths. Discovery has no durable state.

## 7. Workflow Integration

Enrollment and Settings use the ADORE-managed Pi installation. Server projects
show the current account and optional project tools PATH. Linux cgroup delegation
is configured in the service environment.

## 9. Validation And Tests

`tests/test_executor_discovery.py`: filesystem and HTTP trust boundaries, including
POSIX executable bits and symlinks on Linux. `web/e2e/local-executors.spec.ts`
checks that enrollment uses managed Pi and skips discovery.
`02_Tools/verify_package.py` checks the final native archives' authenticated discovery
API against an inert fixture without running an agent or contacting a provider.
