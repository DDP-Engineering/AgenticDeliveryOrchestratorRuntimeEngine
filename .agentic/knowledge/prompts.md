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
recovery, review and system fragments
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
| Prompt wording/inventory | `adore/prompts/{direct,stage,recovery,review,system}/` and callers | `test_prompts.py` original-byte and caller matrices |
| Packaging inclusion | Hatch wheel tree and `02_Tools/create_package.py` | Manual complete wheel path/byte check; inspect unchanged-wheel portable install |

## Key behaviors

- `REQ-FUNC-1f56bfac`, `REQ-FUNC-e8d63a5c`: fixed Markdown catalog, eagerly checked once per conductor.
- `REQ-FUNC-889f30ed`: direct/implementation.md requests whole-ticket work,
  repository instructions/tests, no Git publication/forge credentials, questions
  and root summary. Direct composition reuses literal ticket/thread/recovery and
  identical shared permission/network notices without AEGIS journal procedure.
- `REQ-FUNC-5dfb0e8d`, `REQ-FUNC-e5899386`: direct/verification.md names the
  configured command and asks Pi to run it before finishing.
  direct/verification-failure.md binds sanitized command, exit, status and output
  independently as literal data from the retained result for fresh fixes/Retry.
  The conductor selects these only for configured direct runs; empty-command and
  AEGIS prompts retain their own behavior. Inventory, literal placeholder and
  missing-value controls are in `test_prompts.py`; public selection/context
  assertions are in `test_orchestrator.py`.
- `REQ-FUNC-5bd765bb`, `REQ-SEC-66431463`: named single-pass substitution with literal external data.
- `REQ-FUNC-8256ca8e`: legal comments stay local; body whitespace stays exact.
- `REQ-REL-6fc1aa99`, `REQ-REL-d0663c1d`, `REQ-REL-3eb9bb9e`: file-named missing/read/encoding refusal.
- `REQ-REL-ab48c99a`, `REQ-REL-87abf8e4`: eager syntax refusal and strict render-time missing-value refusal.
- `REQ-FUNC-14872c0d`: frozen original outputs prove byte identity, including effective open/proxy/native policies; injected none cases prove interpolation only, not configured reachability.
- `REQ-PLAT-661c3027`, `REQ-PLAT-e0597722`: all resources ship in the wheel and its unchanged installation into portable Python.

## Files

- `04_Software/adore/prompts.py` — fixed eager loader, typed errors and renderer.
- `04_Software/adore/prompts/` — 28 licensed Markdown fragments in five groups.
- `04_Software/tests/test_prompts.py` — loader boundaries, byte/caller proof and shared ownership.
- `04_Software/tests/fixtures/prompts/{baseline,network-baseline}.json` — original-code expected text; never regenerate from the extracted renderer.
- `05_SoftwareDocu/Component_Prompts.md` — resource and integration contract.
