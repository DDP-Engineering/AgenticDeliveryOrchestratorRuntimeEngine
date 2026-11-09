<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Bounded container timeout recovery

Shared implemented protocol for the four requirements linked by TASK-f6de6c0b.

## Observable behavior

A bound container timeout is a distinct outcome from an ordinary nonzero exit,
including exit 124. Recovery confirms that no process from the timed-out
execution remains before permitting another bound command. The original command
result retains its exit, timeout and captured stream fields.

The existing owned container, image, persistent files, user and egress authority
remain intact. Recovery does not remove or replace resources or install tools.
Normal command completion retains its established behavior.

Identity drift, corrupt runtime evidence, or failed cleanup/restart produces a
typed recovery error; the active recovery sequence does not admit a new command
under unconfirmed ownership or quiescence. Existing native execution behavior,
operator cancellation/release and preparation replay contracts remain separate.

## Authority and data

The public shared bound target receives the run name and optional expected
container/image identity. Runtime evidence is authoritative only after the
existing bounded strict identity parser accepts it. Control commands address the
admitted immutable resource rather than a replaceable name. No new profile or
persisted run-state field is intended; the existing
lifecycle and fatal recovery paths are retained.

## Verification

Offline public bound-target fixtures use injected command runners and inspect
normal/timeout ordering, preserved result values and same-resource recovery.
They reject changed IDs/images, corrupt or unexpected status evidence, failed
interrupt/restart and subsequent unsafe execution. Native/preparation, package
policy and ordinary exit controls are regression seams.

A controlled Docker fixture uses a temporary IO mount and cached image under
network none. A deliberately timed-out child writer establishes current runtime
behavior; the fixed path must prevent that writer continuing into a later
command, preserve the resource/image/network/user and an installed-state marker,
and clean up only the disposable fixture. This acceptance is operator work,
never real Git/Docker in unit tests.

## Recovery protocol

The current running identity is captured before dispatch. Supplied pins must
match it; legacy unpinned commands still capture an immutable invocation target.
The command addresses that ID. Normal non-timeout results do not change runtime
lifecycle.

On timed_out, the backend marks admission blocked while verifying the original
identity, requests bounded interruption of that exact ID and requires a same-ID,
same-image exited receipt. It then retains a pending restart and returns the
original result. A later bound command/provision verifies the stopped original,
starts that ID and verifies running identity before dispatch. Unconfirmed or
failed recovery remains a typed error with blocked active admission.

Operator stop/interrupt/remove cancels pending automatic restart. The conductor
checks cancellation before finalizing an infrastructure recovery failure. No
new persisted state or configuration is added; existing crash and explicit
operator recovery contracts remain authoritative.
