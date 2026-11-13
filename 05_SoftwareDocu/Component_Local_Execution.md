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

## Direct verification-only operation

Windows verification alone sets the controller's `windows_verification=True`
transport marker. The trusted child validates the dedicated non-RPC Windows
cmd envelope before release, pins the executable explicitly and passes a raw
command line to `CreateProcess`: only the executable uses C-runtime quoting;
`/d /s /c` receives the original configured text inside one extra outer quote
pair. This preserves quoted executable paths, nested quotes, compound commands
and backslashes without C-runtime backslash-quote escaping. Ordinary native argv
and RPC keep list serialization; neither infers shell authority from argv.
Malformed transport markers/commands are refused before project execution.

The opt-in controller `capture_tail=True` continuously decodes strict UTF-8,
removes ANSI/NUL and masks the union of overlapping known-secret spans, including
matches starting inside another credential and self-overlapping values. Raw
lookahead and already-masked coverage survive each safe-prefix cut, so an
incomplete overlapping match can extend the mask on the next read without
exposing a suffix or buffering an unbounded overlap chain. It also recognizes
credential tokens/Authorization headers across chunk and eviction boundaries.
Unfinished credential values are suppressed until their terminator, even on
long lines. Only redacted trailing bytes are retained (64 KiB per stream).
Ordinary AEGIS/preparation prefix capture and its existing bounds are unchanged.
Corrupt decoding, ownership or cleanup is a typed refusal, never a guessed pass.

Verification shell commands run with the **service account's permissions and
without container isolation**. A Job/cgroup controls process lifetime, not host
filesystem, credentials or networking. Operators should use a dedicated
least-privilege account. The ordinary native shell/wrapper refusal stays intact.
Public offline proof: `test_native_direct_verification_uses_only_owned_platform_shell`
and `test_native_verification_capture_keeps_true_sanitized_tail`, with
`test_native_verification_capture_masks_overlapping_secrets` proving exact
stdout/stderr tails across short reads, chunk/eviction boundaries and long overlap
chains on success/nonzero/timeout with confirmed owned cleanup, plus
`test_native_windows_verification_preserves_command_at_child_boundary` for exact
Windows command-line preservation on pass/nonzero/timeout/cleanup refusal and
`test_local_child_refuses_invalid_windows_verification_transport` for closed
transport validation. Cancellation remains covered at the child boundary, with existing
identity, scope/PID-birth and retry tests in `test_local_execution.py` and
`test_retry_revalidation.py`.

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

The controlled native environment sets `PYTHONIOENCODING=utf-8` for Python children on Windows and Linux. These values
are owned by ADORE; ambient or supplied Python settings cannot override them.
This keeps standard-stream encoding consistent with strict UTF-8 evidence capture.
Invalid byte output still fails closed; no replacement decoding is introduced.

## 9. Validation And Tests

`test_pi_installation.py` uses fake npm and Node to prove install, validation,
publication failure and pin changes. `test_local_execution.py` exercises the
Windows/Linux control paths and fake Pi RPC, including hostile personal
configuration, redaction and closed readiness diagnostics. The native and
container model connection checks use the same RPC challenge contract.

## Native ChatGPT subscription


Native ChatGPT projects use `chatgpt.helper_for` with verified managed
Node/Pi. They share the ADORE-owned sign-in with container projects on that
home. Only a temporary access token reaches the bound Pi stage or model
probe, with explicit secret redaction. No refresh credential is placed in the
fresh executor agent directory. Native readiness reads stored sign-in status
without calling a model. Stage limits remain at most 3000 seconds.
WSL2 uses the Linux backend and delegated cgroup v2. Host networking remains
separate from the container internet switch. See
[ChatGPT sign-in](Component_ChatGPT_Sign_In.md).

## Explicit cleanup after drift

`LocalBackend.for_cleanup` constructs process controls without resolving current installed tools. `remove_owned` compares the exact saved resource and saved local-policy fingerprint against the runtime receipt; current host/account, state-root path and process-scope leases are still required. It interrupts and drains only verified scopes before unlinking the receipt. Missing receipts are idempotent only without an active-process record. This path is available only through explicit owned deletion/restart and grants no execution/Retry identity exception. Offline proof: `tests/test_drift_recovery.py`, with ordinary Retry covered by `tests/test_retry_revalidation.py`.


The managed native Pi argv carries the selected thinking level to stages and model diagnostics.
