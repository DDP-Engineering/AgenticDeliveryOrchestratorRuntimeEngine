<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Prompt catalog

## Purpose and sources

`04_Software/adore/prompts.py` loads the application-owned Markdown resources
under `04_Software/adore/prompts/`. Stage, Direct implementation, recovery,
review, system notice and live instruction text are reviewable resources.
The conductor owns selection/ordering/context; the launcher owns notice selection
and transport. Pi's own prompt, repository instructions, AEGIS step files and
model-connection challenges are outside this catalog.

## Loading and rendering contract

`PromptCatalog()` eagerly reads exactly the fixed `FRAGMENTS` inventory, including
resources not selected by the current workflow/backend. It reads strict UTF-8
bytes, requires the canonical legal prefix and validates string.Template syntax.
Only a complete successful load publishes the read-only mapping. Missing,
unreadable, malformed or invalid resources raise file-named `PromptError`.
There is no alternate-path setting, process-global reload cache or partial fallback.

The leading legal comment and its one LF delimiter are removed exactly. Body
whitespace is significant, including the leading space in stage/network.md and
resources intentionally without final newline. Rendering performs no file reads.
Reconstruct the catalog to observe edited resources.

`render(fragment, **values)` substitutes named string values once using $name or
${name}; $$ means a literal dollar. Values are data and are never reparsed, so
ticket text containing dollar signs/braces stays literal. Extra supplied values
are ignored, an empty string is valid and a missing required value is an error.
The caller remains responsible for context sanitization and paragraph joins.

## Current resource groups

| Directory | Ownership |
|---|---|
| direct | Agent implementation request, repository checks, questions and summary |
| stage | AEGIS stage opening, task/ticket/context, quick hint, authority and closing rules |
| recovery | Revalidation routing, integration conflicts, continuation and no-progress context |
| review | Pipeline context and changed ticket text |
| system | Internet-off container and native-server notices |
| live | Authenticated user's instruction wrapper |

Direct uses implementation.md. There are no independent verification-command or
verification-failure fragments. The agent chooses repository checks for either
workflow. The full exact filename list is `FRAGMENTS`, not a second prose inventory.

The live instruction wrapper substitutes user/text literally for both captured
initial-prompt fallback and live delivery. Composition does not establish receipt;
that belongs to [Instructions](Component_Instructions.md).

## Integration and distribution

`Orchestrator.from_config` shares one catalog with the conductor and Pi launcher.
Direct conductor/standalone launcher construction also validates a catalog eagerly.
Stage composition joins selected paragraphs; Direct omits AEGIS journal instructions.
Native RPC always gets the server notice. Internet-off container RPC gets the
offline notice; internet-on container RPC gets neither.

Hatchling includes the complete resource directory in the wheel. Portable packaging
installs that wheel unchanged and inventories the resources in its manifest.
See [Executor launcher](Component_Executor_Launcher.md) and
[Portable distribution](Component_Portable_Distribution.md).

## Validation coverage and limitations

Existing `04_Software/tests/test_prompts.py` verifies inventory, literal substitution,
eager errors, legal prefixes and significant bytes against captured fixtures under
`tests/fixtures/prompts/`. Conductor/executor/RPC tests cover selection and transport.
Captured baselines are independent expected outputs; do not regenerate them from
the implementation under test. New resources must update the fixed inventory and
its existing contract coverage together. The catalog itself uses only Python's
standard library and performs no model, Git or forge calls.
