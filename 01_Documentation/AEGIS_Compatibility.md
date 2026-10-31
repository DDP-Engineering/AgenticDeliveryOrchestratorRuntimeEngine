<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS compatibility

ADORE consumes each target repository's installed AEGIS companion CLI. Supported
version/schema policy is declared in `04_Software/adore/aegis.py`. ADORE and AEGIS
have independent release versions. This checkout retains the managed 0.15
payload and the local executor, container and recovery capabilities.

## Workflow contract

The full path is Frame, Specify, Design, Build, Validate and Done; the quick
path is Frame, Build, Validate and Done. A working stage may return to an earlier
stage on its selected path. ADORE saves that stage before checkpointing and
continues in a fresh bounded executor session. A done task returns to Validate
when ADORE requires fresh evidence. Older Deliver journals remain readable as
history and do not authorize new execution.

Validate finishes with the companion's strict check, report and advance to Done.
ADORE independently checks the candidate and requests fresh candidate-bound
human approval. It owns publication; executors never commit, push or open reviews.

Every stage session reads the installed step and `.agentic/templates/task.md`.
It preserves existing task identity, legal prologue, retained guide links and
append-only history. Journal transitions, Log, Rulings and State are written
through the installed CLI. Failed edits repair the same journal.

## Verification and boundaries

`04_Software/tests/fixtures/aegis_0_15_0.json` records actual managed CLI output
and its source hash. Capture used automatically cleaned temporary storage and a
local fixture repository. Its strict-check command runs only Python's version
probe, so the fixture proves serialization rather than application validation.
`test_aegis_compatibility.py` replays supported responses entirely offline and
rejects corrupt identity/schema/path and contradictory check data. The historical
0.14 fixture and its original provenance remain as evidence for version refusal.

ADORE never upgrades a target project's payload. Companion installation preserves
project-owned configuration, requirements, task journals and knowledge. Live model,
OS and delivery-package acceptance remain separate from these product tests.

## Development checkout

The managed payload matches the remote 0.15 payload. Project-owned configuration,
requirements, tasks and local capabilities are reconciled independently. Optional
structure, sequence and state diagrams remain enabled for applicable Design
stages. Quick tasks do not require a Design stage. CodeGraph is absent.
