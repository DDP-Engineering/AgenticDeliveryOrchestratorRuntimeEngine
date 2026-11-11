<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Prompts (`adore/prompts.py`, `adore/prompts/`)

## 1. Purpose

Keep all application-owned stage, recovery, review and system-notice text in
reviewable Markdown fragments without changing the text Pi receives.

## 2. Responsibilities

- Load and validate the complete fixed catalog eagerly, including fragments not
  selected by the current stage or backend.
- Remove the leading project legal comment without trimming the body.
- Substitute named values once, as literal data, and report resource/render
  failures with a file-named `PromptError`.

The orchestrator still owns selection, conditions, ordering, joining and evidence
sanitization. The launcher still owns notice selection and transport. This module
does not own Pi's own prompt, repository instructions, AEGIS step files, the
model-connection challenge, logs or forge status comments.

## 3. Implementation Overview

`PromptCatalog()` loads the 25 filenames in `FRAGMENTS` from
`Path(__file__).with_name("prompts")`. There is no configurable alternate path,
process-global cache or reload mechanism. The `prompts/` resource directory is
not a Python package; the sibling `prompts.py` is the importable module.

Each file is read as bytes, decoded strictly as UTF-8, checked for the canonical
`LEGAL_PREFIX`, then checked with `string.Template.is_valid()`. Only a complete
successful load publishes the private read-only template mapping. Reconstruct a
catalog to read changed resources; rendering performs no filesystem access.

## 4. Dependencies

Only Python standard-library `pathlib`, `string` and `types` are used.
`Orchestrator.from_config` creates one catalog and shares it with the conductor
and `build_executor` / `PiExecutor`. Direct conductor and standalone Pi launcher
construction each defaults to eager loading, or accepts an already loaded catalog.
The executor-neutral gate interface and RPC protocol do not depend on the catalog.

## 5. Inputs And Outputs

- Inputs: required application-relative Markdown files and caller-supplied named
  string values.
- Output: `render(fragment, **values)` returns the substituted body string.
- Errors: `PromptError(RuntimeError)` names the fragment for missing/unreadable
  files, invalid UTF-8, malformed legal prefix, invalid dollar syntax, an unknown
  fragment key, or an omitted required value. No fallback or partial result is
  returned.

## 6. Data Contracts

Resources are grouped by use:

| Directory | Contents |
|---|---|
| `stage/` | Eight opening paragraphs, frame/quick hints, recovery/thread wrappers, package-permission variants, network suffix and closing rules |
| `recovery/` | Revalidation route, integration conflict, continuation, no progress and strict-verification context |
| `review/` | Pipeline brief and ticket-content-change note |
| `system/` | Internet-off and native-server notices |

Every resource starts with the exact project Markdown license comment followed
by one LF delimiter (`LEGAL_PREFIX`). That prefix is removed exactly. Body
spaces and newlines, including the leading space in `stage/network.md`, remain
significant; most bodies intentionally have **no final newline**. Do not wrap,
trim or add newlines while editing unless changing agent wording deliberately.
The loader performs no universal-newline conversion.

Values use `string.Template`: `$name` or `${name}` is a named placeholder, `$$`
is a literal dollar, and ordinary braces such as `{x}` need no escaping. Extra
supplied values are ignored; an explicitly empty string is valid. Values are not
parsed again, so ticket text containing `$name`, `${name}`, `$$` or `{x}` remains
literal. Existing caller-side `description.strip()` and `_sanitize` remain in
place. Add new required files to `FRAGMENTS` and its inventory proof together.

## 7. Workflow Integration

Construction checks every resource before stage execution. The conductor renders
fragments at their existing call sites and joins stage paragraphs with `\n\n`.
Permission and network text remain one paragraph. The launcher renders the native
notice for native RPC, the offline notice for internet-off container RPC, and no
notice for internet-on container RPC. No stored format or run lifecycle changes.

Hatchling includes the complete resource directory in the application wheel.
`02_Tools/create_package.py` installs that wheel into portable Python unchanged;
its cleanup targets scripts, metadata and bytecode, not Markdown resources. The
portable manifest hashes every included file.

## 8. Usage

```python
from adore.prompts import PromptCatalog

prompts = PromptCatalog()
text = prompts.render("stage/ticket.md", iid="7", title="A title",
                      description="Ticket data containing $name and {x}")
```

No setting or environment variable selects another catalog location.

## 9. Validation And Tests

`tests/test_prompts.py` compares rendered UTF-8 bytes with the frozen original
outputs in `tests/fixtures/prompts/baseline.json`. The fixture was captured before
extraction from the original code at `ff76a56088d6d047543e7b544721c60c1b2648a5`;
do not regenerate it from the file-backed implementation. It covers all stages,
frame quick-label variants, recovery/thread, package permissions, each egress
mode and native execution. Each original fragment has its own expected text.

Tests also cover all five recovery callers, review texts, native/container notice
transport, production catalog sharing and exactly-once reads, literal dollar and
brace data, strict missing-value errors, UTF-8, permission/missing-file failures,
invalid syntax/header failures, unknown keys and precise whitespace/header removal.
`tests/test_orchestrator.py`, `tests/test_executor.py` and `tests/test_pi_rpc.py`
retain conductor and transport regression contracts.

Build the wheel in temporary storage and compare every `adore/prompts/` path and
byte with the source inventory. Portable inclusion is inspected through its
unchanged-wheel installation route; deployment tools have no automated tests.
