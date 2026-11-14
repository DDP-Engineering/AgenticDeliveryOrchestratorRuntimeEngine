<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Instruction delivery contract

STATED: Gitea #91/#94 and the explicit child delegation authorize this contract.
OBSERVED: pinned @earendil-works/pi-coding-agent@1.4.0 docs/rpc-commands.md accepts
steer/follow_up with response command, id and success; success acknowledges acceptance,
not model execution. The existing RPC writer queue stays the only stdin writer.

## HTTP and storage

POST /api/v1/jobs/{project_id}/{run_id}/instructions takes exactly text and mode.
Existing principal, CSRF and project-stop grants apply. Non-working returns 409
job_not_working. Invalid text/mode returns 422. Read/list responses include exact
project/run identity, literal text, queued/delivered status and no-store headers.
An archived profile refuses new writes under the existing project_archived rule.
GET at the same location returns bounded records and value-free notices.

Implementation bounds: 256 retained instruction records per run, each at most
32 KiB UTF-8 JSON (at most 8 MiB total). Capacity refusal is 409 instruction_limit.
A short separate crash-released inbox lock serializes atomic enqueue/ack writes;
contention is 409 instruction_busy. No run lifecycle lock is held by the web writer.
These are implementation safety limits, no new setting. Files remain until run delete.
Current schema 1 files have a UUID-hex filename/id, user id/name, UTC created time,
mode, text, delivery null or {at,how}, and a closed value last_error. Unknown shapes
are refused with explicit deletion guidance; no migrations or automatic resets.
Symlink/reparse/hardlinked, oversized, malformed and mismatched files remain unsent;
only value-free filename/reason evidence is returned/journaled. Atomic write uses a
same-directory temporary file, fsync and replacement. Readers see old or new records.

## Pi delivery and recovery

The conductor snapshots valid pending records before composing a fresh AEGIS or
direct prompt; wrappers follow the human thread and precede execution notices.
Only a successful matching started prompt acknowledgement marks this snapshot delivered
with how=prompt. New arrivals are polled next to cancel and sent once per session
with unique instruction ids and steer/follow_up; only success:true for the matching
id AND command persists how=steer/follow_up. Failure records pi_rejected without
raw provider text. Missing/rejected acknowledgement remains queued across exit/restart.
No instruction is sent after cancellation/timeout has begun. No new agent loop exists.

The shipped live/instruction.md loader wrapper names the author and ADORE interface;
literal instruction text is inserted once. The session recording remains literal.
Operational logs, delivery journal metadata, diagnostics and forge-facing evidence
keep existing sanitization; the required ticket comment copies the authorized text.

Acknowledgement updates the inbox first; the conductor reconciles delivered records
into an outbox record with deterministic notification id before appending one
instruction-delivered event (id, user, mode, how). It sends/replays the comment through
existing marker lookup and retry machinery after RPC completes. A failed forge write
retains the outbox without failing the job or undoing delivery. Reconciliation before
replay reconstructs effects after a process interruption; stable markers suppress a
second forge comment even if posting succeeded before the client saw failure.
Pi acceptance and host persistence are separate systems: a crash after remote
acceptance but before local receipt may cause a retry; ADORE never fabricates an ack.

## Browser

A composer below SessionView in Agent sessions remains available for a working job
with no live session. It lists Queued/Delivered and explains Delivered means Pi
acknowledged receipt (not completion). Send now waits for current tools and never
interrupts them. All text/help is en/fr/de/ro. Request/response project/run identities
are checked; component keys and request generations fence old-job completions.
The saved compact header, existing scopes/list controls and Projects remain intact.
