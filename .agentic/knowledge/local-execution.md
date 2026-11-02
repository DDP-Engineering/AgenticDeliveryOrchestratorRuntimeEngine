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

LocalBackend provision/bind/resource_identity/verify_required_tools/stop/interrupt/remove;
LocalTarget run_files/call/read_output/redact/auth_available and `output_limit` (64 KiB default for non-AEGIS output; Test AI connection raises it to 1 MiB); local_policy,
local_environment, local_argv and local_probe. LocalProcessController launch/interrupt/
recover delegates to NativeScopes; child.main enforces scope membership and release.

## Invariants

Explicit selection and same actual account/environment for probes/gates; closed
pinned runtime/lease/scope, immutable ownership and PID birth before control.
Scope assignment and durable ownership precede project code. Confirm descendants
drained before release; corruption/control failure preserves evidence/worktrees.
No recovered PID-only kill, login, credential copies, forge env or tool installs.
Worktrees are not host sandboxes; container egress/recipes cannot be selected.
Gates and probes share one bound target and one `local_environment` result; the
conductor remains the stage owner. The environment is an explicit allowlist:
`SYSTEM_ENV_KEYS` everywhere plus `WINDOWS_SYSTEM_ENV_KEYS` (PATHEXT, PROCESSOR_*,
NUMBER_OF_PROCESSORS, OS, SystemDrive, ProgramData, ProgramFiles*, CommonProgramFiles*,
ALLUSERSPROFILE, PUBLIC) on Windows, then `[local].environment` (explicit
values replace inherited ones), then the managed account names, home and PATH,
then `PI_CODING_AGENT_DIR` defaulting to `<home>/.pi/agent` when neither the
process nor `[local].environment` sets it, then the approved provider keys.
The installed Pi reuses its existing sign-in in place: `auth_available()` is
true when `$PI_CODING_AGENT_DIR/auth.json` exists or an approved
`[executor] env_keys` value is set; ADORE never logs in or copies credentials,
and reads the auth file only to redact its values from retained output.
`local_policy` (also `config plan`) writes nothing; its pinned environment
digest covers the whole built environment, so changing the allowlist,
`[local].environment` or the account context makes runs started earlier drift.

## Change map

| Request | Start | Focused proof |
| --- | --- | --- |
| Profile/auth/argv/policy | local_execution.py | local environment/drift/output selectors |
| Tree lifecycle/recovery | local_process.py | scope/process/Job/cgroup selectors |
| Launch ordering | local_child.py | child release/cancel selectors |
| Native conductor/GUI | orchestrator.py, web/app.py | retry/cleanup/readiness/settings selectors |

## Key behaviors

- REQ-FUNC-ffb9ed29: pinned local selection/resource and default container compatibility.
- REQ-REL-50474528: scoped lifecycle with immutable launch/PID-birth checks.
- REQ-FUNC-5e2fe079: same fresh gate/AEGIS file contract through native argv.
- REQ-SEC-f7b9111e: allowlisted account environment (Windows system names included),
  bounded strict/redacted evidence and auth reused in place.
- REQ-UX-b75e1df8: native probes and actual machine/account/tooling notice.
- REQ-FUNC-78b0ad95: `[local].environment` names starting `OPENCODE_`, `CODEX_`
  or `QWEN_` are refused by configuration validation.

## Files

- `04_Software/adore/local_execution.py`: policy/account/auth/path and file transport.
- `04_Software/adore/local_process.py`: OS scopes/durable ownership and bounded control.
- `04_Software/adore/local_child.py`: trusted scope/release launcher.
- `04_Software/tests/test_local_execution.py`: offline positive/negative boundary proof.
- `05_SoftwareDocu/Component_Local_Execution.md`: component contract.
- `01_Documentation/Local_Execution.md`: operator setup/security/recovery.
