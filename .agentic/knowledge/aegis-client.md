<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS client

## Purpose

`04_Software/adore/aegis.py` is ADORE's sole companion-governance boundary. It
speaks the installed AEGIS Python CLI at 0.5 or later within major 0 and its
schema-1 JSON contract; it does not support older or alternate governance
APIs, and a major bump is refused at probe rather than guessed at.

## Public interface

`AegisClient` probes a target, creates and reads task journals, runs checks,
records evolution, and appends the delivery report; the executor runs `anchor`
and `test` itself during its stages. `AegisTask.deviations` harvests the
journal's `DEVIATION <stage>` entries with the marker rule AEGIS uses for its
own delivery report. Its validated value objects
(`AegisProbe`, `AegisTask`, `AegisCheck`, `AegisFinding`, and
`AegisCommandRun`) expose only decision-safe data to the orchestrator.

## Contract and safety boundary

Host pre-pick probing uses direct subprocess argv. Calls made from a run
container instead write a LF-only, POSIX-quoted `aegis.sh` and invoke exactly
`sh /adore/io/aegis.sh`; bounded UTF-8 exchange files replace wrapper output.
The client accepts only `aegis` major 0 at 0.5 or later, schema `1`, expected task ids, legal
stages/paths, contained artifact paths, and internally consistent strict-check
results. Malformed JSON, path escapes, unknown schema/version, missing or
oversized exchange files, unexpected exits, and typed timeouts fail closed as
typed AEGIS errors.

The client never edits a journal, advances a stage, approves publication,
commits, pushes, or calls a forge. Those remain explicitly owned by the
orchestrator and human delivery policy.

## Requirement coverage

- `REQ-FUNC-4fe259b0` - bounded container exchange and typed timeout handling.
- `REQ-FUNC-16237c6d` - pinned AEGIS task, stage, and strict-check validation.

## Dependencies and verification

It depends on the target repository's `.agentic/aegis.py`, an injected command
or container exec seam, `adore.util.CommandResult`, and branding mount paths.
`04_Software/tests/test_aegis.py` covers valid and corrupt schema data,
transition rules, protocol/containment failures, shell-sensitive inputs, and
typed timeout preservation offline.
