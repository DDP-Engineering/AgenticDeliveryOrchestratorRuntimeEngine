<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Native local execution, version 1 (#21)

## Selection

`[execution] backend = "local"` is explicit; omitted backend stays container.
Local mode rejects nonempty preparation, container egress other than open,
container run_args/required_tool_checks/SELinux relabel and
explicit container runtime_env customization. These cannot silently become host
commands or pretend local containment. Ignored default image/cache settings
have no local effects. Existing #24 container plans keep their exact policy
shape/fingerprints; optional new `[local]` settings are included only in local
plans. No schema migration or release assignment.

`[local] account = "current"` selects the ADORE process account, never impersonates;
a named account must match. `home = ""` and `path = ""` use that account's
current home/PATH; explicit values select an already prepared environment.
`environment = {}` is an explicit non-secret string map; managed account/home/
PATH/forge credential variables are refused. `cgroup_root = ""` must be set to
an absolute, operator-delegated writable cgroup-v2 root on Linux; it is unused
on Windows. Unknown local fields/types fail closed. No tool/version manifest.

Native Windows supports Windows Job Objects and executable CLI entrypoints
(.exe, or an explicit node executable plus installed JavaScript entrypoint).
Windows .cmd/.bat/PowerShell/shell wrappers are refused; prompts never pass through
cmd.exe. Native Linux requires delegated cgroup v2 with cgroup.kill; this includes
ADORE inside WSL2 only when those controls exist. Windows-to-WSL local wrapping,
macOS, cgroup v1 and uncontained process-group fallbacks are unsupported before
project code execution. OS details stay in the local process adapter.

## Native target and pinned identity

The shared ExecutionBackend owns provisioning, bound paths, commands, parking,
interruption and removal. Local provisioning creates only authoritative runtime
control records outside the ticket worktree/mounted IO, with a random run UUID,
host/account identity, exact native worktree/IO paths and normalized policy.
It never creates a container/image, performs recipe setup or installs tools.
Machine/account, effective non-secret environment and selected executable identity
are pinned with the reviewed local plan. Missing/corrupt/replaced records, changed
backend/config/home/PATH/executable or incompatible active legacy runs fail closed;
restore the original environment or start a fresh run. Legacy container recovery
retains its previous behavior. Local records are a closed alternative within
schema 1. Portable working-rule exports omit
backend/machine/account/path/runtime identity and local environment.

## Process ownership and recovery

Each native command uses a random owned scope plus an atomic durable lease with
host/run identity, supervisor PID and OS birth identity, and exact scope identity.
A trusted Python child waits for a release marker; ADORE persists ownership before
releasing any project command. Windows assigns it to a non-breakaway named Job
with kill-on-close. Linux places it in the owned cgroup before exec; cgroup.kill
terminates descendants regardless of process groups. Native control operations
verify machine/run, scope and any still-live PID birth before control. Reused PID,
wrong scope, corrupt evidence or failed kill/cleanup raises a typed error; no
PID-only kill or best-effort success claim. Timeouts are authoritative and bounded;
all scopes are drained after each command. Cancellation watcher uses the same
owned control. Parking leaves no live gate; retry/restart preserve the worktree,
archive and pinned resource. Crash recovery reconciles only verified owned scopes;
Windows parent death closes the Job, while Linux durable cgroup evidence supports
explicit cleanup. Absent owned processes are idempotent. Shared tools/auth/home and
unrelated processes/scopes are never cleanup targets.

## Gates and credentials

Local gates use argv templates tokenized before placeholder substitution; quoted
paths/spaces and prompt text remain one argument. Shell compounds and wrappers are
unsupported locally. AEGIS commands use the configured native Python argv through
the same target. No shell transport, stale sessions or second conductor. Retain
questions/result semantics, timestamped immutable launch archives, usage coverage,
limits, candidate-bound approval and draft-only delivery. ADORE never merges.

Only an explicit system/user-environment allowlist plus `[local].environment` and
approved `[executor].env_keys` is passed, including the selected home/PATH and
executor credential/config locations. Forge token names are refused. Existing
Pi account store (`$PI_CODING_AGENT_DIR/auth.json`, default `~/.pi/agent/auth.json`)
is reused in place; no login flow, auth-file copy or credential archive. Known approved environment/auth-store string values
are redacted before bounded retained output. Corrupt supported auth JSON fails
closed before a command. Missing auth is a readiness finding; actual provider/model
access is proved only by an explicit bounded nonce challenge using the same
configured CLI/account/environment as gates. Model checks never start login.

A worktree is not a host sandbox. The executor can access files and credential
helpers available to its OS account. Recommend a dedicated least-privilege account
without forge publication credentials; environment filtering and prompt rules do
not create filesystem isolation. Container egress restrictions are unenforceable
locally and rejected.

## Operator surfaces and verification

CLI config validation/plan, assisted setup, executor/project settings and host/
model checks select the backend. Local checks never invoke Docker/Podman, image
checks or preparation. Basic executor availability/auth-state is allowed; no
project tool discovery, automatic install, dependency bootstrap or catalogue.
GUI/setup state the execution machine/account and that the user must decide and
independently install/prep project tools, versions, SDKs and libraries there.
Installing them on a remote browser laptop is insufficient.

Offline injectable process/runtime boundaries prove happy and negative config,
identity/PID/scope/control, native argv/path/file/timeout/auth, conductor and UI/
readiness contracts. Focused regressions only; entire Python/frontend suites,
aggregate strict --run, complete epic #23 integration and live OS/executor/provider/
forge acceptance remain explicitly deferred by user instruction.
