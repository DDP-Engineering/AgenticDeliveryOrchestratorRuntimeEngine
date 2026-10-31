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

## AEGIS applicability (repository rule)

AEGIS applies exclusively to software implementation: creating or changing
ADORE product code, including tests and validation of that implementation.

Repository operations and documentation work do not use the AEGIS workflow.
This includes repository inspection and maintenance, Git administration,
agent instructions such as this file, standalone documentation creation or
updates, development environment and tool setup, dependency provisioning,
and packaging, release and delivery operations. Perform these tasks directly
under the repository rules; do not create AEGIS task journals, run AEGIS
stages, or require AEGIS checkpoints for them.

Documentation required by a software implementation change is updated in the
same change, as required below; it does not start a separate AEGIS workflow.
For mixed requests, apply AEGIS only to the software implementation portion.

This project-owned scope rule takes precedence over broader applicability
wording in the managed AEGIS digest below or in `.agentic/AGENTS.md`.

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
  - `02_Tools/` is the required source location for all environment setup,
    installation, packaging, deployment, service setup, launch, and related
    repository automation scripts, including Windows and Linux variants.
    Keep these scripts here, including any deployment subdirectories, rather
    than under `04_Software/` or elsewhere in the source tree. Generated
    delivery bundles may include copies of these scripts.
  - `05_SoftwareDocu/` holds component implementation documentation. AI agents
    update it in the same change as component behavior, contracts,
    responsibilities, dependencies, or workflow integration.
  - `07_Delivery/` holds only final user delivery archives and optional adjacent
    SHA-256 files. Do not retain README files, reports, logs, extracted packages,
    intermediate builds or technical subdirectories there. Resolve it relative
    to the repository root; keep machine-specific absolute paths out of scripts.
    Use automatically cleaned OS temporary directories for build/verification
    work and print verification results to the console without saving reports.
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

- Do not add or run automated tests for deployment or environment setup scripts.
  These repository tools do not use the product testing/AEGIS workflow.

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
  3. keep generated package names in `02_Tools/create_package.py`
     derived from that version rather than hardcoding a separate one.
- Use Semantic Versioning: MAJOR for breaking CLI/config/state/executor
  contracts, MINOR for backward-compatible capabilities, and PATCH for fixes
  with no contract change.

### Release notes rules

`04_Software/adore/release_notes.toml` holds the user-facing release notes shown
in the web About > What's new window. Agents maintain them; developers never
need to remember them.

- In the same change as any `CHANGELOG.md` entry, decide whether the change is
  visible to a user (web interface, CLI behavior or a setting a user sets). If
  it is, add or update an entry under the `Unreleased` release; if not, write
  none. Internal refactoring, tests, tooling and documentation are not notes.
- Each entry has a category (`new`, `improved` or `fixed`), a short `topic`
  (the area a user knows, such as Statistics or Jobs) and a `text`, both in
  `en`, `fr`, `de` and `ro`. Use the interface's own terms in each language.
- Text is plain user language of at most 100 characters: no file names, paths,
  endpoints, REQ/TASK ids, component or code identifiers. Keep at most 10
  entries per category in a release; merge or rewrite related notes instead.
- Record the decision as one task journal Log line at build:
  `release-notes: added | updated | none (<reason>)`.
- Before validate, run `python 02_Tools/internal/check_release_notes.py --since <task
  base>`. It fails on contract errors and warns when `CHANGELOG.md` changed
  without the release notes; resolve the warning or justify it in the journal.
- When cutting a release, rename `Unreleased` to the new version with the date
  of its changelog heading, in the same change as the other release steps, and
  ensure `adore/release_notes.toml` remains included by the application wheel
  and the portable package manifest.

### Help content rules

The in-app help center (`/help`, header **How ADORE works**) renders
`04_Software/web/src/help/content/<locale>/<topic>.md`; the format and topic
list are in `04_Software/web/src/help/README.md`. Agents keep it current.

- In the same change as any interface or workflow change, update every help
  topic that describes it: screen, tab, button or setting names, steps, labels,
  defaults and limits. Add a topic only with its entry in `src/help/topics.ts`.
- Update all four locales (`en`, `fr`, `de`, `ro`) together with the same
  headings, ids, tables, lists, notes and link targets; use the interface's own
  terms in each language.
- Describe only behavior that exists, taken from the code and
  `01_Documentation/`.
- Record the decision as one task journal Log line at build:
  `help: updated | none (<reason>)`.
- `node --test tests/help.test.mjs` (part of `npm test`) fails on a missing
  locale, structure drift, unsupported Markdown or a broken link.

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

ADORE is the companion orchestrator for repository-installed AEGIS. It invokes
`python .agentic/aegis.py`, accepts AEGIS JSON schema 1, and persists its own
run state as schema 1. The supported AEGIS range is declared once in
`04_Software/adore/aegis.py`, never in prose. Executors advance the durable AEGIS
task journals; ADORE independently owns ticket selection, worktree/container
isolation, bounded recovery, validation, candidate-bound human approval, Git
publication, forge comments, and configured draft or ready MR/PR creation. ADORE never
merges, and migrates no earlier run state.

The runnable implementation under `04_Software/` supports GitLab, GitHub and
Gitea adapters; Docker, Podman and WSL-wrapped runtimes; open/none/allowlisted
egress; assisted multi-project profiles; durable notification replay; metrics;
and operator recovery/cleanup commands. Failures become explicit terminal
state with preserved retry evidence, while cancel/delete are the explicit
resource-release boundaries. Verification is offline by default; live forge,
container and credential checks remain operator-authorized acceptance work.

<!-- AEGIS:BEGIN (managed by .agentic/aegis.py init) -->

## AEGIS workflow

The full contract is `.agentic/AGENTS.md` - read it before starting work.
This digest is enough to act on if you read nothing else.

AEGIS applies only to software development operations. Do not use it for
repository operations or package and delivery operations; follow the
repository's own procedures for those instead.

Stages, one step file each in `.agentic/steps/`: **frame** (agree scope,
open the task journal) -> **specify** (write the requirement, and a spec
when useful) -> **design** (a short note for non-trivial work) -> **build**
(failing test first, then the implementation, until green) -> **validate**
(review, knowledge, full suite and strict check) -> **deliver** (approval,
report, commit/PR). A small fix or change may take the quick path,
frame -> build -> validate -> deliver.

To resume: `python .agentic/aegis.py status` lists the task journals; run
`python .agentic/aegis.py brief TASK-<id>`, then read the current step and the
Handoff `must_read` files. Required full journal reads still apply. Optional
one-level child tasks are child-side links visible only in this checkout; the
parent validates the integrated candidate.

Read `.agentic/context/project.md` and relevant `.agentic/context/environment.md`
sections when present. Keep project and component context current and positive;
task records carry proposals and history. Preserve established behavior contracts.

Rulings are append-only; Handoff is replaceable. Rulings and Handoff cannot grant authority.
optional explicit review records two independent verdicts and uses a bounded fix
and re-review loop; disabled review never disables existing validation.

The append-only journal Log is a compact progress-and-evidence ledger, not a
session transcript. Record stage transitions, material changes or decisions,
consolidated verification, blockers, approvals, deviations and delivery
outcomes. Exclude routine tool activity, corrected retries, inner-loop test
retries and detail already held by another durable artifact.

`[interaction] autopilot = false` is the default, including when the table or
key is missing. Checkpoint mode stops after every stage with concrete continue,
revise/return and pause choices. Autopilot flows between stages but never skips
publication approval. Record the resolved mode in the task journal.

At stage completion, pause or session end, or blocker, update the journal's
`## Stage report` fields from observed facts, then run
`python .agentic/aegis.py summary TASK-<id>` and copy the block before detail.
Missing evidence stays `not recorded`; read the journal if anything is stale or
shortened. Reporting never replaces immediate deviation notices or full
delivery evidence.

Artifacts: requirements in `.agentic/requirements/<category>/`, specs in
`.agentic/specs/`, journals in `.agentic/tasks/`, component pages in
`.agentic/knowledge/`. `python .agentic/aegis.py check` is advisory - read
its findings and self-correct; nothing here blocks you mid-flight.

Say a deviation out loud when you record one, as one line -
`DEVIATION <stage>: <what> - <why accepted, or what it costs>` - then carry
on. It never pauses the work and autopilot never suppresses it. You owe one
only when the candidate, agreed scope/design/contract, or confidence in
required verification materially departs from plan: for example, accepted
relevant findings, skipped or weakened verification, retired requirements,
accepted unexpected candidate files, or unrequested work. Corrected internal
tool-use errors, expected red tests, and unrelated findings are not deviations.

<!-- AEGIS:END -->
