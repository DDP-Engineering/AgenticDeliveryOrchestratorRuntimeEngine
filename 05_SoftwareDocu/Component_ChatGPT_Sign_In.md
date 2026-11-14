<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: ChatGPT sign-in

## 1. Purpose

One ADORE-owned ChatGPT Plus/Pro sign-in supplies temporary access tokens to
container and native Windows/Linux Pi projects. Pi implements OAuth. ADORE
owns transport, typed failures, access controls and launch-only injection.

## 2. Responsibilities

- Read server credential status without a model call.
- Run login and token operations through the selected trusted helper.
- Keep one state-bound pending login for at most 900 seconds.
- Disconnect credentials while retaining the installation device ID.
- Keep secret values outside argv, cause messages, audit and retained evidence.

## 3. Implementation Overview

`helper_for(config, manager, runner=...)` selects NativeHelper for a local
project and retains ContainerManager for a container project. SignIn and
bearer_token retain the same protocol on both transports.

Container helpers mount only the server credential directory read-write.
No run container mounts it. Native helpers execute the packaged
`adore/executor/adore-chatgpt.mjs` with verified absolute managed Node/Pi
paths. The child uses the credential directory as cwd and a filtered
environment with ADORE-owned Pi/home paths. Personal Node options, Pi
resources, project PATH and forge credentials are excluded. The trusted
helper runs no project code. Timeout, cancellation and failed sign-in kill
and reap its directly owned process. Native sign-in needs no container runtime.

Packaged and image helpers have an offline byte-parity test. Both import
the pinned Pi OAuth and AuthStorage modules by absolute file URL.
The OAuth store and Pi lock stay outside the fresh executor agent directory.
Native service-account access remains governed by host permissions, not a sandbox.

## 4. Dependencies

- pi_installation.verify_pi supplies verified managed native paths.
- ContainerManager supplies the existing helper-container transport.
- util.run_command and injected Popen provide bounded native execution.
- Web API owns administrator/CSRF, pending-login locking and sanitized audit.
- Orchestrator/model diagnostics own token lifetime and target binding.
- Node 22.23.4+ in the 22.x line, Pi 1.4.0 and pi-web-access 0.46.0.

## 5. Inputs And Outputs

credential_dir, prepare, status, disconnect, check_redirect, SignIn and
bearer_token keep their public inputs and outputs. The helper transport can
be native or container. Errors use value-free ChatGptError cause codes.

The login operation emits an authorization URL/state event, reads the checked
redirect on stdin, stores credentials through Pi and emits signed-in or an
error code. The token operation returns status, token and expiry or a closed
failure status. Acceptance requires a successful exit, a 16–16384 character
token and a numeric expiry satisfying the requested lifetime. A refresh token
is never returned. Missing/corrupt credentials and non-string error codes fail closed. Login
completion also requires a successful helper exit and a readable stored sign-in.

The current directory contains auth.json, Pi's auth.json.lock, device-id and
optional sign-in-again. POSIX directory permissions are 0700, private files
0600. Windows operators protect the service home with account ACLs.
No persisted format changes.

## 6. Workflow Integration

Administrators select ChatGPT subscription in Agent and model, start Sign in
with ChatGPT, open the provider link and return to ADORE. Pi may finish through its own
native loopback callback. SignIn.poll observes that completion without a new
process or network request. The administrator-only status route finalizes and
audits success or a typed refusal once. The visible panel polls every second
only while pending, bounded to 15 minutes, and clears temporary URL/address
on completion. If the callback cannot reach Pi, paste the matching redirect
only into ADORE. Foreign state is refused while a valid attempt stays pending.
Restart replaces pending login. Cancel/expiry end it. Disconnect deletes the
credential/refusal mark while preserving device identity.

Stages request their limit plus 300 seconds, with the same 3000-second ceiling
on both backends. Pi gets only OPENAI_API_KEY through the explicitly bound
launch target. LocalTarget redacts it and ignores ambient subscription keys.
A failed token request starts no Pi stage and follows bounded recovery.

The explicit model/shell probe uses the same source and owned native scope.
Native readiness reads stored status without refreshing or calling a model.
Native networking remains the host policy.

Status reads and sign-in mutations are serialized in the browser. Manual completion waits for an in-flight status observation and accepts its confirmed automatic completion without sending an obsolete redirect.

## 7. Validation And Tests

test_native_chatgpt.py covers trusted argv/environment, login/state/cancel,
expiry/output failures, Windows/Linux token injection, readiness, model/shell
checks and conductor wiring. Existing chatgpt, web, stage, model and native
suites prove container regressions and shared trust boundaries offline.
Live Windows/WSL2 model acceptance needs an ADORE-owned sign-in and verified
native prerequisites.

## 8. Limits

One sign-in per ADORE home. Tokens refresh between stages only. Pending login
is web-server memory and ends on restart. Pi requires its local callback port 1455 to be available during native login.
An unreachable browser callback retains the manual redirect fallback. WSL2 runs the Linux native backend inside the distribution with a
delegated cgroup v2. There is no wrapper fallback around process ownership.


## Concurrent resource ownership

A dedicated credential-directory lock serializes refresh helpers, their status
marks and Disconnect across run processes, independently of repositories and
executors. A separate lock atomically publishes the stable device identity.
Pi retains its own credential-store lock and atomic credential persistence.
Helpers have unique names; access tokens stay in the requesting stage's memory
and bound environment, while temporary native settings stay in that run's control
folder. A refresh error releases the lock and cannot alter another credential
store. Existing stages continue while another run waits for refresh.

Focused proof: `04_Software/tests/test_shared_resources.py` and the component’s existing offline contracts.
