<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Prompts

## Routing

Use for shipped agent text, dollar placeholders, legal-header removal and
`PromptError`. Start at `04_Software/adore/prompts.py` and verify with
`04_Software/tests/test_prompts.py`. `orchestrator.md` owns composition and
recovery selection; `executor-launcher.md` owns system-notice selection and
transport. Delivery assembly belongs to `deployment-and-packaging.md`.

## Purpose and boundaries

The catalog reads application-owned AEGIS-stage, direct implementation,
recovery, review, live instruction and system fragments
from fixed package resources and renders literal caller data. Conditions, order,
joins, sanitization and thread rendering remain in the callers. Pi's own prompt,
repository instructions, AEGIS payload and model-connection challenge have other
owners.

## Public interface

- `PromptCatalog()` eagerly reads every path in `FRAGMENTS`, rooted at
  `Path(__file__).with_name("prompts")`; no alternate-location setting exists.
- `render(fragment, **values)` returns a body using strict `string.Template`
  substitution. Extra values are ignored; empty values are valid.
- `PromptError(RuntimeError)` identifies the fragment for file/encoding/header/
  syntax errors, unknown keys and omitted required values.
- Production `Orchestrator.from_config` shares one catalog with `PiExecutor`.
  Direct conductor and standalone launcher construction load one unless injected.

## Invariants

- Construction validates the entire fixed inventory, including unused branches,
  before publishing the private read-only template mapping; rendering never reads.
- Strict UTF-8 decoding and exact `LEGAL_PREFIX` removal preserve body bytes,
  including leading spaces and absent final LF. No trimming or newline conversion.
- Values are inserted once, never reparsed. `$name` and `${name}` are placeholders,
  `$$` is a literal dollar, and ordinary braces need no escaping.
- Missing/unreadable/non-UTF-8 files, malformed headers/dollar syntax and missing
  values fail closed with a file-named error, never fallback or partial output.
- The resource directory is not a Python package and does not shadow `prompts.py`.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Resource/render boundary | `PromptCatalog`, `LEGAL_PREFIX`, `FRAGMENTS` | `test_prompts.py` loader and negative contracts |
| Prompt wording/inventory | `adore/prompts/{direct,stage,recovery,review,live,system}/` and callers | `test_prompts.py` original-byte and caller matrices |
| Packaging inclusion | Hatch wheel tree and `02_Tools/package/create_delivery_package.py` | Manual complete wheel path/byte check; inspect unchanged-wheel portable install |

## Key behaviors

## Files

- `04_Software/adore/prompts.py` — fixed eager loader, typed errors and renderer.
- `04_Software/adore/prompts/` — the fixed licensed Markdown catalog.
- `04_Software/tests/test_prompts.py` — loader boundaries, byte/caller proof and shared ownership.
- `04_Software/tests/fixtures/prompts/{baseline,network-baseline}.json` — original-code expected text; never regenerate from the extracted renderer.
- `05_SoftwareDocu/Component_Prompts.md` — resource and integration contract.

## Live instruction resource

REQ-FUNC-84b2d01e: the fixed inventory includes live/instruction.md.
InstructionDelivery renders user/text once as literal data for both live commands
and next-prompt fallback. The wrapper names the author and ADORE interface.
Resource/header/UTF-8/template refusal remains eager. Explicit inventory/live body
and placeholder oracles in test_prompts.py preserve all historical captures.

## Continued job context

REQ-FUNC-22de3595: stage/resume.md supplies continuation context without unchanged
ticket replay; current stage, installed AEGIS procedure and new recovery/thread/
inbox input remain explicit. A changed ticket is resent until acknowledged.
Partial-work continuation points to current journal State without appending the
previous Log to every prompt. Single-stage return remains mandatory; RPC restarts
resume the same conversation. Required independent reviewers use separate contexts
under existing policy. Direct prompts retain repository-owned workflow authority.
Existing byte fixtures deliberately update only the changed conversation fragments.

## Explicit new-job workflow

The Direct implementation prompt carries trusted operator selection overriding only mandatory AEGIS procedure. All other coding/licensing/verification rules remain, installed payload is untouched and no executor budget/deadline wording is supplied.

## Current contract

Current Direct prompts ask the executor to implement the ticket and choose repository checks while bypassing AEGIS obligations only when Direct is selected. Later launches add changed ticket/thread/correction content to the persistent job conversation. The active licensed catalog is `adore/prompts/`; REQ-FUNC-889f30ed and REQ-FUNC-22de3595 own composition.
