<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local execution

## Routing

Native backend/account/auth/Job/cgroup/run_files requests start at
`04_Software/adore/local_execution.py`, `local_process.py` and `local_child.py`.
Focused proof: `04_Software/tests/test_local_execution.py`. Core stages belong to
orchestrator.md, recipes to preparation.md and guarded GUI apply to web-interface.md.

## Purpose and boundaries

Implement shared native execution and verified process ownership. The conductor
owns ticket/worktree/stage/budget/approval/draft delivery; the operator owns project
tools and interactive account authentication.

## Public interface

LocalBackend revalidate_for_retry/provision/bind/resource_identity/verify_required_tools/stop/interrupt/remove;
LocalTarget run_files/call/read_output/redact/auth_available; local_policy,
local_environment, local_argv and local_probe. probe_local_executor returns closed
ready/reason/exit_code diagnostics; validate_local_probe protects persisted evidence. LocalProcessController launch/interrupt/
recover delegates to NativeScopes; child.main enforces scope membership and release.

## Invariants

Explicit selection and same actual account/environment for probes/gates; closed
pinned runtime/lease/scope, immutable ownership and PID birth before control.
Scope assignment and durable ownership precede project code. Confirm descendants
drained before release; corruption/control failure preserves evidence/worktrees.
No recovered PID-only kill, login, credential copies, forge env or tool installs.
Worktrees are not host sandboxes; container egress/recipes cannot be selected.

## Change map

| Request | Start | Focused proof |
| --- | --- | --- |
| Profile/auth/argv/policy | local_execution.py | local environment/drift/output selectors |
| Tree lifecycle/recovery | local_process.py | scope/process/Job/cgroup selectors |
| Launch ordering | local_child.py | child release/cancel selectors |
| Native conductor/GUI | orchestrator.py, web/app.py | retry/cleanup/readiness/settings selectors |

## Key behaviors

Native environments preserve inherited PATHEXT alongside PATH for Windows shell
command resolution. Missing PATHEXT stays absent; the same allowlist filters forge
credentials and unrelated secrets. Offline proof uses injected Windows/Linux
contexts in test_local_environment_preserves_executable_extensions.

Explicit Retry validates the saved plan and same host/account/configuration, then
revalidate_for_retry recovers the owned scope and atomically refreshes the runtime
policy receipt. Only environment_sha256, resolved executable and executable_sha256
may change. Previous/current fingerprints support repeating an interrupted refresh.
The normal bounded version check precedes AEGIS; automatic resume stays strict.
All native executors and jobs share this contract. Task/worktree/history and
cumulative budgets remain intact. Focused proof: test_retry_revalidation.py.


- REQ-FUNC-ffb9ed29: pinned local selection/resource and default container compatibility.
- REQ-REL-50474528: scoped lifecycle with immutable launch/PID-birth checks.
- REQ-FUNC-5e2fe079: same fresh gate/AEGIS file contract through native argv.
- REQ-SEC-f7b9111e: bounded strict/redacted evidence and auth reused in place.
- REQ-UX-b75e1df8: native probes and actual machine/account/tooling notice.

Ownership is persisted and scope established before release. Shared gates/probes
use the same bound target; the existing conductor remains the stage owner.

## Files

- `04_Software/tests/test_retry_revalidation.py`: explicit Retry and bound outcome proof.

- `04_Software/adore/local_execution.py`: policy/account/auth/path and file transport.
- `04_Software/adore/local_process.py`: OS scopes/durable ownership and bounded control.
- `04_Software/adore/local_child.py`: trusted scope/release launcher.
- `04_Software/tests/test_local_execution.py`: offline positive/negative boundary proof.
- `05_SoftwareDocu/Component_Local_Execution.md`: component contract.
- `01_Documentation/Local_Execution.md`: operator setup/security/recovery.

## Installed executor suggestions

Local enrollment and launch-command editing use the admin-only filesystem
discovery and manual path picker described in [Installed executor discovery](executor-discovery.md).
Existing saved/manual commands retain authority; selected paths are revalidated
by native policy and applied through the existing reviewed configuration flow.

## Simple native setup

Enrollment uses current-account defaults and displays read-only Runs as identity.
Detected installations remain visible; a closed Advanced disclosure holds full
command/manual executable and home/PATH/Linux delegation. Settings retains saved
account assertions and overrides in Advanced. Manual/saved command authority,
existing authentication and native launch validation remain unchanged.

## Background launch policy

Native account construction and the controller force child-only GIT_PAGER/PAGER
cat values after caller settings; ordinary executor descendants inherit them.
Windows supervisor and isolated child request CREATE_NO_WINDOW without changing
Job ownership/release/timeout handling; Linux retains its cgroup/execve flow.
Source and public proof remain local_execution.py, local_process.py,
local_child.py and environment/native launch/child tests in test_local_execution.py.
Requirements: REQ-PLAT-989c6478, REQ-PLAT-967d0c80.

## Native prerequisite causes

Version checks accept a recognizable version line on stdout or stderr, including
standard CLI prefixes and ANSI styling, after clean non-timeout exit. Typed
LocalPrerequisiteError preserves the exit code. probe_local_executor separates
missing executable, account/home, auth presence/corruption, permissions, version,
command exit/timeout, scope preparation and cleanup. No raw diagnostics escape;
failed cleanup prevents success. Schema-1 web readiness optionally carries the
closed evidence; legacy absence remains explicit. REQ-FUNC-ab8c90b6 and
REQ-UX-4d08dee5; focused native/API/readiness and source-render Node tests.

## Windows captured streams

The Windows local_child supervisor explicitly passes sys.stdout/sys.stderr to
the released subprocess and DEVNULL for stdin with CREATE_NO_WINDOW. These are
the existing parent-owned pipes; the controller still drains, redacts and bounds
them. Implicit Windows stream inheritance is insufficient for this launch mode.
Existing Job/release/cancel and exit contracts remain unchanged; Linux uses
execve. REQ-FUNC-5e2fe079; focused test_windows_supervisor_preserves_redirected_output
covers clean/nonzero status and both streams, alongside child cancel/envelope proof.
