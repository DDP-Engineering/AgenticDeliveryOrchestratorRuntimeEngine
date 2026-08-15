<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AGENTS.md - Agentic Delivery Orchestrator & Runtime Engine

## Scope

These instructions apply to the repository rooted at:
`2026_AgenticDeliveryOrchestratorRuntimeEngine/`

A deeper `AGENTS.md` overrides this file for its subtree.

## Repository Rules

- Treat this repository as independent.
- Keep the runnable orchestrator implementation under `04_Software/`.
- Keep folder boundaries clear across planning, documentation, tools, software,
  software documentation, delivery, and support material.
- Keep folder ownership explicit:
  - `00_Planning/` holds planning, strategy, design-history, and TODO
    material. AI agents update it only when the user explicitly asks.
  - `01_Documentation/` holds project/user documentation such as manuals,
    setup guides, configuration references, presentations, and operational
    guidance. AI agents update it when software interfaces, user-visible
    behavior, or implementation-facing guidance changes.
  - `02_Tools/` holds scripts for development environment setup, delivery,
    packaging, and related repository automation.
  - `05_SoftwareDocu/` holds component implementation documentation. AI agents
    update it in the same change as component behavior, contracts,
    responsibilities, dependencies, or workflow integration.
  - `07_Delivery/` holds generated delivery packages and release handoff
    artifacts.
- Keep the orchestrator forge-agnostic (GitLab, GitHub and Gitea behind one
  adapter) and executor-agnostic (opencode, pi.dev, codex behind one launcher).
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
  the orchestrator from outside: Git-platform CLI output (glab/gh/tea JSON,
  URLs, HTTP status lines), config files typed by humans, ticket comments
  written by humans, persisted state read back after a crash, executor output,
  and container/git exit codes.
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
  `@file`, `@brief`, `@details` (add `@example` when relevant).
- **Section markers** where meaningful: `IMPORTS`, `CONSTANTS`,
  `DATA MODELS / TYPEDEFINITIONS`, `HELPER FUNCTIONS` / `LOCAL HELPERS`,
  `PUBLIC API` / `EXPORTED FUNCTIONS / PUBLIC API`, `END OF FILE`.
- **Callable docstrings** (functions, methods, classes, documented nested
  helpers) use Doxygen-like tags when non-trivial or part of the public API:
  `@brief`, `@param[in]`, `@param[out]`, `@param[in,out]`, `@return`, plus
  `@exception`, `@note`, `@todo`, `@retval`, `@example` as applicable.

### Release versioning and changelog rules

- The repository-root `CHANGELOG.md` is the canonical record of notable ADORE
  project updates. Accrue changes under `## [Unreleased]` using Keep a
  Changelog sections (`Added`, `Changed`, `Fixed`, `Removed`).
- The project release version is declared in both
  `04_Software/pyproject.toml` and `04_Software/adore/__init__.py`; keep these
  values aligned.
- When the user asks to assign or cut a release version, in the same change:
  1. roll `## [Unreleased]` into a dated `## [x.y.z] - YYYY-MM-DD` section in
     the root `CHANGELOG.md`;
  2. bump every release-version declaration to the same `x.y.z`;
  3. keep generated runtime package names in `02_Tools/package_runtime.*`
     derived from that version rather than hardcoding a separate one.
- Use Semantic Versioning: MAJOR for breaking CLI/config/state/executor
  contracts, MINOR for backward-compatible capabilities, and PATCH for fixes
  with no contract change.

## Documentation Rules

- **After every component creation or update, create or update that component's
  documentation** under `05_SoftwareDocu/`, based on the template at
  `05_SoftwareDocu/component_documentation_template.md`.
- Do this **in the same change** as the component's behavior, contracts,
  responsibilities, dependencies, or workflow integration changes.
- Keep only the template sections relevant to the component; remove empty
  sections rather than filling them with placeholder text.
- Component documentation **complements** the in-code Doxygen docstrings
  (Style Rules); it does not replace them.

## Status

ADORE 0.5 is the hard-break companion orchestrator for repository-installed
AEGIS 0.5.x. It invokes `python .agentic/aegis.py`, accepts AEGIS JSON schema 1,
and persists its own run state as schema 4. Executors advance the durable AEGIS
task journals; ADORE independently owns ticket selection, worktree/container
isolation, bounded recovery, validation, candidate-bound human approval, Git
publication, forge comments, and draft-only MR/PR creation. ADORE never merges
and has no compatibility or migration layer for the former ADORE 3.x contract.

The runnable implementation under `04_Software/` supports GitLab, GitHub and
Gitea adapters; Docker, Podman and WSL-wrapped runtimes; open/none/allowlisted
egress; assisted multi-project profiles; durable notification replay; metrics;
and operator recovery/cleanup commands. Failures become explicit terminal
state with preserved retry evidence, while cancel/delete are the explicit
resource-release boundaries. Verification is offline by default; live forge,
container and credential checks remain operator-authorized acceptance work.
