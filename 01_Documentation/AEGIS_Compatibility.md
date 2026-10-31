<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS compatibility

ADORE consumes the target repository's installed AEGIS companion CLI. Supported
version/schema policy is declared in `04_Software/adore/aegis.py`. ADORE and AEGIS
have independent release versions; validating a new companion release does not
itself require changing ADORE's release number or migrating saved jobs.

## Verified delivery

The AEGIS 0.14.0 Windows core delivery rebuilt on 2026-10-22 was inspected against
the installed companion and replayed through ADORE's existing client. Its source
commit is `9e3d870cd1fe834a93e785008c69506bda954359`. The local rebuilt artifact is
used because the Gitea published-release list still names 0.13.0.

| Evidence | SHA-256 |
|---|---|
| Core Windows ZIP | e58fdaae59a00a4d2d49af0dd16e686104b9c1c9d6ff379adde310835616baff |
| Companion Python CLI | 87f87d0743555bdf49b2ac90a899e4c47f28383c34de411aa9ff25c126b777f6 |

| Surface | Result |
|---|---|
| Version and JSON schema | Existing supported version policy and schema 1 remain applicable. |
| Task creation and status | Same arguments and JSON identity/stage/header/checklist/log shapes. New journals retain an authoring-guide link. |
| Strict check | Same findings, summary, configured-run, dry-run and strict-result fields. |
| Evolution and report | Existing commands and response conventions remain applicable. |
| Workflow instructions | Expanded journal preservation, review/proof ordering and recovery guidance are delegated to installed AEGIS files. |
| Optional diagrams | Governed by the target's installed AEGIS configuration and steps; no additional ADORE gate. |

## Executor behavior

Every stage session reads the installed AEGIS step and `.agentic/templates/task.md`.
The prompt preserves the task's existing identity, legal prologue, retained
authoring link and append-only history; an unsuccessful edit repairs the same
journal. ADORE retains fresh one-stage sessions, bounded recovery and its existing
human publication approval. The instruction applies to every executor and forge.

## Verification and boundaries

`04_Software/tests/fixtures/aegis_0_14_0.json` contains captured official CLI output
and archive/source hashes. Capture uses a temporary isolated payload with injected
Git and verification boundaries. The captured successful command record is a
serialization fixture, not evidence that an application suite executed.
`test_aegis_014_compatibility.py` replays it entirely offline; existing client tests
cover the remaining version, malformed JSON, transport and timeout boundaries.

ADORE does not upgrade the managed payload or optional plugins of a target project.
Install an AEGIS release through its own process, preserving project-owned config,
requirements, task journals and knowledge. The ADORE development checkout's separate
CodeGraph extension is retained; it is outside the application companion API.
Live model, native OS and delivery-package acceptance are separate from these
targeted tests.

## Development checkout workflow

This repository's managed `.agentic` payload was upgraded to the rebuilt AEGIS
0.14.0 delivery on 2026-10-22. Existing configuration values, task journals,
history, requirements, specs, knowledge, context and plugin files were preserved.
The requested addition to `.agentic/aegis.toml` enables all supported diagram types:

```toml
[diagrams]
enabled = true
types = ["structure", "sequence", "state"]
```

During substantive Design stages, AEGIS writes
`.agentic/tasks/diagram_TASK-<id>.md`. Each configured type is drawn when applicable;
a type outside the design is recorded as Not drawn with its reason. Quick tasks
without Design do not generate diagrams. Existing task history is not regenerated.
The preserved CodeGraph files/configuration remain local; this upstream core
release no longer exposes the `know_graph*` CLI commands.

