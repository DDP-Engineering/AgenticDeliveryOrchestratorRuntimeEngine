<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AGENTS.md - Agentic Delivery Orchestrator

## Scope

These instructions apply to the repository rooted at:
`2026_AgenticDeliveryOrchestrator/`

A deeper `AGENTS.md` overrides this file for its subtree.

## Repository Rules

- Treat this repository as independent.
- Keep the runnable orchestrator implementation under `04_Software/`.
- Keep folder boundaries clear across planning, documentation, tools, software,
  software documentation, delivery, and support material.
- Keep the orchestrator forge-agnostic (GitLab and GitHub behind one adapter)
  and executor-agnostic (opencode, pi.dev, codex behind one launcher).
- Keep the delivery boundary strict: the orchestrator may open a draft MR/PR but
  must never merge. Merge is a human decision.
- Prefer portable Python; do not add OS-specific glue to the core loop.

## Working Rules

- Prefer simple, maintainable changes over speculative abstraction.
- Make changes incrementally.
- Update documentation in the same change when behavior, commands, folder
  layout, or contracts change.
- Bound every autonomous run with explicit limits (iterations, wall-clock,
  cost, files touched).

## License Header

- **Every generated file must carry the project legal/license header**, adapted
  to that file's comment syntax. Canonical text:

  ```text
  Copyright (c) 2026 DDP Engineering
  This software is licensed under the PolyForm Noncommercial License 1.0.0.
  Commercial use requires a separate commercial license.
  See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
  ```

- Use the file type's comment style, for example:
  - Markdown / HTML: wrap the header in `<!-- ... -->`.
  - Python / TOML / Bash / PowerShell: prefix each line with `#`.
  - cmd (`.bat`/`.cmd`): prefix each line with `::` (or `REM`).
- For Python files the header is part of the file prologue defined in the Style
  Rules (the banner lines before the module docstring).
- Apply the header even to small generated files; omit only where a header is
  technically impossible (for example pure data files that must not contain
  comments).

## Style Rules

Code style and Python documentation style are defined in
`01_Documentation/Code_Style.md`; follow that file for implementation and
documentation conventions. Use the referenced
`settings_service.py` (AudioMancer) as the canonical example of the exact format.

### Doxygen documentation (Python source and test files)

- **File prologue:** `#!/usr/bin/env python3`, `# -*- coding: utf-8 -*-`, the
  copyright/license banner, then a module docstring with aligned Doxygen tags:
  `@file`, `@brief`, `@details`, `@author`, `@date`, `@version` (add `@example`
  when relevant).
- **Author tag value:** `Eng. Dan Dumitru Pasare` unless explicitly requested
  otherwise.
- **Section markers** where meaningful: `IMPORTS`, `CONSTANTS`,
  `DATA MODELS / TYPEDEFINITIONS`, `HELPER FUNCTIONS` / `LOCAL HELPERS`,
  `PUBLIC API` / `EXPORTED FUNCTIONS / PUBLIC API`, `END OF FILE`.
- **Callable docstrings** (functions, methods, classes, documented nested
  helpers) use Doxygen-like tags when non-trivial or part of the public API:
  `@brief`, `@param[in]`, `@param[out]`, `@param[in,out]`, `@return`, plus
  `@exception`, `@note`, `@todo`, `@retval`, `@example`, `@author`, `@date`,
  `@version` as applicable.

### Versioning system (required)

Two independent revision markers, both bumped in the same change that causes them:

- **Function-level `@version`.** Every documented callable carries a local
  `@version` tag in its docstring. **When the implementation of a function,
  method, or documented nested helper is touched/changed, bump that callable's
  own `@version`** in the same change.
- **File-level `@version`.** The module header docstring carries a `@version`
  tag. **When a function, method, class, or documented nested helper is added to
  or removed from a file, bump that file-level `@version`** in the module header
  in the same change.
- These are local revision markers only. Do **not** sync callable-level or
  file-level `@version` tags to `pyproject.toml` / the release version; they need
  not match the release number.

## Documentation Rules

- **After every component creation or update, create or update that component's
  documentation** under `05_SoftwareDocu/`, based on the template at
  `05_SoftwareDocu/component_documentation_template.md`.
- Do this **in the same change** as the component's behavior, contracts,
  responsibilities, dependencies, or workflow integration changes.
- Keep only the template sections relevant to the component; remove empty
  sections rather than filling them with placeholder text.
- Component documentation **complements** the in-code Doxygen docstrings and the
  file/function `@version` markers (Style Rules); it does not replace them.

## Status

Early scaffold: folder structure, per-folder READMEs, and a stubbed `04_Software`
package skeleton (interfaces and Doxygen headers; logic not implemented).
