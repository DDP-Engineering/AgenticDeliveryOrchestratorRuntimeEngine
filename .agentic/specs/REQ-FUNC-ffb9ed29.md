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
Ordinary native argv transport refuses Windows .cmd/.bat/PowerShell/shell
wrappers; stage prompts never pass through cmd.exe. Configured direct-workflow
verification has a separately authorized, owned platform-shell operation, not
an ordinary-argv or interpreter-wrapper bypass. Its draft contracts are
REQ-PLAT-a39ffa22, REQ-SEC-d94baaf1 and REQ-SEC-c81de547; ordinary transport keeps
its shell refusal. Native Linux requires delegated cgroup v2 with cgroup.kill; this includes
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
backend/config/account/host or incompatible runs fail closed. An
explicit Retry may refresh effective environment and resolved executable identity
on the same machine/account after verifying the saved plan and runtime ownership.
The same job, task journal, branch, worktree, history and cumulative budgets remain.
The existing bounded version check runs before AEGIS; unavailable, timed-out or
invalid-version executors remain failed with the actual cause. Automatic polling
and other resume paths retain pinned identity. This applies to every supported
native executor on Windows/Linux and every forge, without job-specific rules. Local records are a closed alternative
within the current schema. Portable working-rule exports omit
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

Local gates run the fixed Node/Pi RPC command in the dedicated worktree. ADORE
sends the stage prompt over the owned stdin pipe, retains bounded redacted
evidence, and records questions, usage and the authoritative exit/timeout result.
AEGIS commands keep the native Python file transport through the same target.

Only an explicit system/account allowlist and approved provider credentials are
passed. The optional project tool PATH does not select Node or Pi. A fresh
ADORE-owned agent directory excludes personal Pi credentials/settings and
untrusted project resources. The model test uses the same bounded RPC shell
challenge; neither readiness nor a native model test initiates login.

A worktree is not a host sandbox. The executor can access files and credential
helpers available to its OS account. Recommend a dedicated least-privilege account
without forge publication credentials; environment filtering and prompt rules do
not create filesystem isolation. Container egress restrictions are unenforceable
locally and rejected.

## Operator surfaces and verification

CLI config validation/plan, assisted setup, executor/project settings and host/
model checks select the backend. Local checks never invoke Docker/Podman, image
checks or preparation. Basic executor availability/auth-state is allowed; no
project tool discovery, dependency bootstrap or catalogue. The explicit Pi install
command manages Pi only.
GUI/setup state the execution machine/account and that the user must decide and
independently install/prep project tools, versions, SDKs and libraries there.
Installing them on a remote browser laptop is insufficient.

Offline injectable process/runtime boundaries prove happy and negative config,
identity/PID/scope/control, native argv/path/file/timeout/auth, conductor and UI/
readiness contracts. The configured Python/frontend product suites and aggregate
strict check validate an integrated candidate. Live OS/executor/provider/forge
acceptance remains a separate operator action.
