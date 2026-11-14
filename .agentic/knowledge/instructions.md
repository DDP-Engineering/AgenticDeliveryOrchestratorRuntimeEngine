<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Instructions

## Routing

Use for operator instructions, the per-run inbox, Queued/Delivered and Pi receipt
matching. Start at `04_Software/adore/instructions.py`, verify with
`04_Software/tests/test_instructions.py`. API/composer route to web-interface.md;
RPC transport to executor-launcher.md; journal/comment replay to orchestrator.md.

## Purpose and boundaries

InstructionInbox owns bounded physical current-schema records and atomic receipts.
InstructionDelivery snapshots fallback text and matches live acknowledgements. The
conductor owns prompt ordering, journal/outbox and forge replay; Pi owns scheduling.

## Public interface

`InstructionInbox(run_dir).enqueue(user,text,mode)` returns a queued literal record;
`read()` returns sorted valid records and value-free notices. `acknowledge(id,how)`
is idempotent; `reject(id)` preserves Queued with pi_rejected. InstructionError is a
StateError. InstructionDelivery exposes suffix, poll, prompt_accepted and
command_response with local on_delivery/report callbacks.

## Invariants

- 256 retained files per run, 32 KiB each, no NUL, 1..4000 Unicode characters.
- All directory ancestors, reparse/symlink and single-link regular-file boundaries
  are checked before reads/writes; lock storage uses StateStore's canonical location.
- Strict UTF-8, duplicate-key and schema/identity validation preserve malformed
  files unsent with explicit filename evidence; no reset, migration or old readers.
- Atomic same-directory temporary/fsync/replace writes use a short crash-released
  inbox lock, independent of the long conductor lifecycle lock.
- Only matching successful Pi command/prompt acknowledgements persist delivery.
  Construction, rendering and spawn never acknowledge; missing/failed ack survives.
- PromptCatalog inserts user/text once as literal data; operational evidence uses
  only bounded metadata and value-free notices. Authorized text stays literal.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Durable record/input boundaries | InstructionInbox, validate_instruction | test_instructions.py |
| Snapshot and live acknowledgement | InstructionDelivery | test_instructions.py, test_pi_rpc.py |
| Loader wrapper | live/instruction.md, PromptCatalog | test_prompts.py |

## Key behaviors

- REQ-DATA-2777f139: atomic bounded records survive reopening/restart.
- REQ-DATA-1d84dc79: invalid human text/mode is refused without publication.
- REQ-REL-6dd5a689: malformed/unencodable/linked records remain unsent with notices.
- REQ-REL-c6354595: failed or absent acknowledgements retain Queued.
- REQ-FUNC-84b2d01e: now and after map to the existing Pi steer/follow_up commands.
- REQ-FUNC-5942c3b1: pending wrappers follow the human thread in the next accepted prompt.

## Files

- `04_Software/adore/instructions.py`: storage, receipt matching and literal rendering.
- `04_Software/tests/test_instructions.py`: reopening, corruption, bounds and locks.
- `04_Software/adore/prompts/live/instruction.md`: shipped author/source wrapper.
- `05_SoftwareDocu/Component_Instructions.md`: protocol and recovery reference.
