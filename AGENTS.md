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

## Testing Rules

- **Every public behavior gets one clear-path (happy) test plus negative tests
  at its trust boundaries.** A contract is proven twice: once that it works,
  once that it fails closed on bad input (corner cases).
- **Trust boundaries that require negative tests** are everything crossing into
  the orchestrator from outside: Git-platform CLI output (glab/gh JSON, URLs),
  config files typed by humans, ticket comments written by humans, persisted
  state read back after a crash, executor output, and container/git exit codes.
- **Fail closed on corrupt input:** raise a typed error (for example
  `StateError`, `ForgeError`) so the caller can skip or escalate
  deterministically. Never silently reinitialize, guess, or continue with
  partial data. Writing the negative test forces this decision at
  implementation time.
- **Test contracts, not internals.** Private helpers are covered through the
  public surface; do not test implementation details directly, and do not
  force a negative test onto branch-free plumbing.
- **Tests must run offline.** External CLIs are faked through the injectable
  command runner; no network and no real glab/gh/git/docker in unit tests.

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

Phase 1 (base services) implemented under `04_Software/`: util (command
runner), typed config + validation, marker-based identity, local state store,
forge adapters (GitLab/GitHub, live-verified read-only against GitLab), CLI
wiring (`config`/`status`/`runs`/`pause`/`resume`), and an offline test
suite. Phase 2 done and live-verified (Docker in WSL2): isolation (worktree +
container lifecycle, `docker/Dockerfile.executor`) and the executor launcher
(file-based gate protocol; mutating opencode spike passed). Phase 3 done: the
thick-conductor engine (polling, selection, per-gate loop with verification
and budgets, clarification park/resume, TTL/timeouts) wired to the CLI.
Phases 3 and 4 were live-piloted END TO END on a real ticket: #45 went from
the `agent-ready` label to draft MR !29 on the real repository, fully
conducted by ADOR (prereq report sections 15-16, including all ten hardening
findings fixed with regression tests along the way). The post-MR revise cycle was live-verified (MR !29 revised on request) and
the human merge closed the full lifecycle. Metrics (design 13) are
implemented: per-launch usage journaling, SQLite run summaries at terminal
states, `ador stats|report|export` + static HTML dashboard (pilot run
backfilled via `stats --rebuild`). Still pending: `reset`/`cleanup` CLI,
deployment scripts, and the security decisions in 00_Planning/TODO.md
(container egress allowlist, executor credentials).
