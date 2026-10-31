<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local execution component

## 1. Purpose

Run installed native executors and AEGIS through ExecutionBackend; the existing
conductor owns stages, budgets, questions, approval and draft delivery.

## 2. Responsibilities

`local_execution.py` selects/pins actual machine/account/environment/executable,
binds paths and reuses auth in place. `local_process.py` owns durable leases,
Windows Jobs and Linux delegated cgroups. `local_child.py` joins its scope and
holds a durable release barrier before project commands. Project tools are user-owned.

## 3. Implementation Overview

LocalBackend provisions a receipt outside worktree/IO. LocalTarget validates/redacts
bounded UTF-8 files and delegates argv. LocalProcessController creates a random
scope, spawns isolated Python, persists immutable ownership and active lease, then
releases the child. Bounded stream drains redact known secrets. Timeout and normal
completion terminate/drain descendants. Recovery verifies scope and PID birth.

## 4. Dependencies

Python standard library, execution/util and bounded stream-drain helper. Windows
uses kernel32/advapi32/secur32; Linux requires delegated cgroup v2 with kill.
Native boundaries are injectable. No dependency install or container invocation.

## 5. Inputs And Outputs

Validated profile/context, argv, worktree/IO, approved in-memory provider values
and positive finite timeout. Outputs: CommandResult, redacted files, runtime.json,
per-launch command.json/ownership.json and atomic active-process.json.

## 6. Data Contracts

Closed resource: kind=local, id (32 hex), host (64 hex), account, name, worktree, io.
Runtime receipt: schema=1, resource, policy_sha256. Lease: schema=1, run_id, host,
pid, birth, scope. Scope is a random named Windows Job or delegated cgroup path/
device/inode. Immutable launch ownership must exactly match the active lease.
Corruption/drift/control failures raise LocalExecutionError (ExecutionRecoveryError).
Windows accounting must show zero active processes; Linux requires populated 0
before rmdir. Failures preserve evidence; no recovered PID-only control or reset.

## 7. Workflow Integration

Config/preparation fingerprint local plans. Orchestrator persists native resource
and retains normal AEGIS/gate/retry/parking/cancel/delete flows. Launcher/AegisClient
use run_files; readiness/model/endpoint checks use local_probe and verified cleanup.
Container policy and legacy recovery remain separate.

## 8. Usage

See [Local execution](../01_Documentation/Local_Execution.md) for account/tool ownership,
platform controls, auth locations, reviewed configuration and safe recovery.

## 9. Validation And Tests

`tests/test_local_execution.py` injects positive/negative configuration, native
ownership, process/scope, auth/output, transports, lifecycle and probe/settings
boundaries. Native enrollment is in `web/e2e/enrollment.spec.ts`; closed browser
plans/readiness/help have focused helper proof.

## 10. Limitations

Native Windows/Linux only; WSL must satisfy Linux delegation. Windows shell shims
reject. Worktrees are not host sandboxes. Live OS/executor/provider acceptance and
full epic integration remain operator work; offline proof does not prove real
Job/cgroup availability.

Native AEGIS stdout preserves the established 4 MiB JSON exchange bound; gate
stdout, stderr and questions remain bounded at 64 KiB. Native stream decoding
rejects invalid UTF-8; truncated JSON cannot become successful AEGIS evidence.
The shared drain retains container defaults. Saved local readiness checks reuse
approved profile .env values in memory through the same native environment.

## Installed launch selection

Local enrollment and command editing use the read-only host discovery and manual
executable picker described in [Installed Executor Discovery](Component_Executor_Discovery.md).
Actual execution retains native policy validation, installed identities and existing
account authentication; discovery does not execute agents or test model access.

## Automatic native setup

Enrollment uses the current process account and displays the discovered account
as read-only Runs as. Default home and PATH come from the process environment. The system-variable
allowlist also preserves inherited `PATHEXT` for Windows shell executable
resolution; absent values stay absent and forge credential variables remain filtered.
The new executor process reuses saved authentication; open terminal processes
are independent. Full command, manual executable and home/PATH/delegation
overrides are under closed Advanced controls. Settings retains saved assertions
and reviewed overrides. Native policy and platform isolation remain authoritative.

## Background native processes

The selected native account environment forces `GIT_PAGER=cat` and `PAGER=cat`
after profile/provider selection; the controller reapplies these values to a
child-only copy. Ordinary executor children inherit them. Both the Windows
supervisor and its released executor use `CREATE_NO_WINDOW`, preserving the
non-breakaway Job, ownership receipts, captured streams and timeout/cancel
handling. Linux keeps its existing cgroup membership and `execve` contract.
The isolated standalone child carries the stable Win32 flag directly because
`-I` excludes package imports. Already running operations are unaffected.
Focused proof: environment, native launch, ownership and child release tests in
`tests/test_local_execution.py`.

## Native prerequisite diagnostics

`probe_local_executor` returns closed `{ready, reason, exit_code}` after owned
native cleanup. Version output may be on stdout or stderr, but must be a version
line from a clean, non-timeout command. `LocalPrerequisiteError` preserves the
measured command status. Missing executable, account/home mismatch, absent or
corrupt auth, permission failure, process scope preparation, command/version
failure, timeout and failed cleanup have separate safe causes. Auth remains
reused in place; probes install nothing and change no global settings.
`validate_local_probe` rejects extra/unknown fields, non-integer exit values,
unknown causes and inconsistent ready/status combinations. No command output,
provider values or filesystem exception text is persisted in this diagnostic.

## Windows supervisor stream transport

The released Windows child explicitly binds stdin to DEVNULL and stdout/stderr
to its current parent-owned streams when starting the executor with
CREATE_NO_WINDOW. Windows implicit stream inheritance with this flag can return
exit zero while discarding output. Explicit binding preserves version/JSON/error
bytes for the existing controller drain/redaction/limit checks. Job ownership,
release/cancel, cwd, argv and real exit propagation remain authoritative; Linux
continues through execve. Focused proof: Windows supervisor captured-stream,
child release/cancel and native file-gate contracts in test_local_execution.py.

## Explicit Retry revalidation

For every native job and supported executor, explicit Retry may refresh the inherited
environment, resolved executable and installed executable identity on the same host
and account. Stable execution settings, runtime resource, branch and worktree stay
pinned. The conductor validates the saved plan; revalidate_for_retry validates the
owned receipt and recovers only its verified scope before atomically updating its
policy fingerprint. Previous/current receipt fingerprints allow a repeated explicit
Retry after an interrupted refresh. Automatic resume retains strict drift checks.
The ordinary bounded --version prerequisite runs before AEGIS; version, exit and
timeout failures retain their measured cause. No provider request or installation
is added. Focused proof: tests/test_retry_revalidation.py.
