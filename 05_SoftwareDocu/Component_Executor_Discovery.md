<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Installed Executor Discovery

## 1. Purpose

Offer current-host native agent launch suggestions and manual path selection for
local project enrollment and reviewed Agent and model Settings.

## 2. Responsibilities

`adore/executor_discovery.py` reads bounded absolute PATH and conventional user/npm
locations. It locates Pi native executables or installed
Node plus known JS entrypoints. The shared React `LocalExecutorPicker` displays
host/account and installed choices, with optional refresh/manual executable/full
command under the initially closed Advanced disclosure.
Tools, authentication, model access and project dependencies remain operator-owned.

## 3. Implementation Overview

`discover_executors` reads at most 64 roots and returns at most 12 canonical launches
per agent. Relative paths, project/.git/.agentic trees, unsafe formatting characters,
missing files and Windows shell wrappers are omitted. Known npm layouts supply real
executables or explicit Node/JS argv; no shim contents or credential files are read.
The administrator-only GET route returns Cache-Control: no-store. No command runs.

## 4. Dependencies

Standard library and existing wizard command presets; existing administrator web
authorization; frontend React and reviewed configuration flows. Actual execution
continues to use `local_policy` and the existing native process ownership controls.

## 5. Inputs And Outputs

Host platform, account home and PATH produce `{system, machine, account, executors}`.
Each executor has `agent` and `installations`; each launch has `executable`, nullable
`entrypoint`, `command` with placeholders and `source` (PATH or npm). API routes use
the actual current service account. Injectable filesystem locations support offline
Windows/Linux fixtures. Unknown installations remain manually configurable.

## 6. Data Contracts

Only Admin can read server launch paths. Discovery has no durable state. During
enrollment the first installed launch replaces an empty/default/earlier automatic
command. A manually edited command survives refresh and late responses. Settings
preserves existing saved commands until an explicit choice. Use executable rebuilds
standard agent arguments; the full command remains editable for custom arguments.
Requests are bounded in the browser and stale unmounted results are ignored.

## 7. Workflow Integration

Enrollment and imported/cloned guided configurations share the picker. Existing
projects expose it in direct command edits and the atomic agent selection editor.
Existing candidate review, revision, CSRF and apply authority remain unchanged.
The model identifier and authentication are configured independently. Linux cgroup
preparation and Windows native executable rules remain required.

## 9. Validation And Tests

`tests/test_executor_discovery.py`: filesystem and HTTP trust boundaries, including
POSIX executable bits/symlinks on native Linux. `web/tests/localExecutors.test.mjs`:
manual argv and malformed HTTP data. `web/e2e/local-executors.spec.ts`: enrollment,
agent changes, manual override, late/unavailable responses and saved Settings.
`02_Tools/verify_package.py` checks the final native archives' authenticated discovery
API against an inert fixture without running an agent or contacting a provider.

## Automatic and advanced presentation

The administrator discovery endpoint inventories files only. Guided enrollment and Settings use the managed Pi installation and do not call this endpoint or offer detected executables for launch.
