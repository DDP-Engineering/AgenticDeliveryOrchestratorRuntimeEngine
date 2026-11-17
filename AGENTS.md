# AGENTS.md - ADORE

Shared repository instructions. `claude.md` and `QWEN.md` link here and repeat only the managed AEGIS block.
A deeper AGENTS.md overrides this file for its subtree. User instructions take precedence.

## Scope and reading

- Use AEGIS only for product implementation and its tests, unless the user says otherwise.
  Repository maintenance, documentation, setup, dependencies, packaging and releases are direct work.
  This project scope overrides broader wording in the managed AEGIS instructions.
- Before code changes read [Code style](01_Documentation/Code_Style.md).
  For versions, changelog and release notes read [Releases](01_Documentation/Releases.md).
- Read only the current task, relevant requirements, component and source sections.
  `.agentic/context/project.md` routes to current contracts; `environment.md` routes to tools.
  Use searches and bounded reads rather than loading full histories or large modules.
- Keep plans in `00_Planning/`; change them only when explicitly requested.

## Repository ownership

- `01_Documentation/`: current user/operator manuals and specialized references.
- `02_Tools/`: all setup, installation, build, package, deployment and launch scripts,
  including Windows/Linux variants. Generated packages may contain copies.
- `04_Software/`: product code and tests. Keep the core portable Python.
- `05_SoftwareDocu/`: component contracts; update the relevant sections with implementation.
  Use its compact component template; link existing guidance instead of duplicating it.
- `07_Delivery/`: final user archives and optional SHA-256 files only.
  Build/verification scratch belongs in cleaned OS temporary directories; no reports there.
- Keep folders independent and names descriptive. Preserve useful specialized manuals;
  replace superseded statements rather than appending another account of the same behavior.

## Product boundaries

- One forge adapter interface: GitLab, GitHub, Gitea and Azure DevOps Services.
  One executor interface: Pi. Do not couple the conductor to a particular forge or OS.
- ADORE may publish configured draft/ready PRs or MRs. It never merges; humans decide.
- Pi owns implementation and reported repository checks. ADORE owns admission,
  isolation, recovery, candidate freshness, approval and publication.
- New jobs select automatic AEGIS detection or explicit AEGIS/Direct. Direct skips
  AEGIS even when installed; Retry retains the saved workflow and conversation.
- Keep changes simple, incremental and scoped. Bound autonomous runs explicitly.
  Preserve unrelated local work. Branches, commits, pushes and deployment follow user authorization.

## Stored data before delivery

- Support exactly one current format per store. No migrations, version upgrades,
  compatibility readers, old-layout fallbacks or automatic data resets.
- Web schema stays `1` during pre-release. Validate the complete current structure;
  a matching identifier alone is insufficient. Change current definitions in place.
- Refuse unsupported/corrupt stores with a typed error and explicit operator deletion guidance.
  Never guess, fill old fields or silently recreate data. Keep stored-format and release versions separate.
- Do not promise upgrade/downgrade paths in docs or notes. Breaking stored-format changes
  get one changelog line naming what to delete before starting the build.

## Verification

- Test implemented public behavior: one clear path and negative cases at trust boundaries.
  Cover forge/executor output, config, human comments, persisted state and process exit codes.
  Fail closed with typed errors. Test contracts, not private helpers or absence of retired features.
- Unit tests run offline with injected command runners, never real forge/Git/container commands.
- Keep mutable homes, databases, applications and credentials isolated per test.
- Run focused checks for affected behavior and consumers. Reuse passing proof when its inputs
  are unchanged; journal-only handoffs need no retesting. Full suites follow the user's gate.
- Do not add/run automated tests for deployment or environment setup scripts.
  Live forge, model, credentials and container checks require operator authorization.

## Documentation, help and release notes

- Update affected component docs and public instructions with implementation.
  Keep AEGIS knowledge as routing, invariants and focused-test pointers; details live in component docs.
  Requirements describe current product behavior/tests, not manuals, setup scripts or removed features.
  Preserve task journals as history; do not load them as current instructions.
- UI/workflow changes update affected help topics in `en`, `fr`, `de`, `ro` together.
  Follow `04_Software/web/src/help/README.md`; keep structure, anchors and interface terms aligned.
- Each notable change updates Unreleased in CHANGELOG; user-visible changes also update
  four-locale release notes. Format and release commands belong to Releases.md.
- Record help/release-note decisions in the AEGIS log when using AEGIS; otherwise in the handoff.

## Code and license

- Follow Code_Style.md; tools enforce formatting and lint. Keep contract documentation concise.
- `REUSE.toml` assigns licensing to project-owned files; `LICENSE.txt` and `LICENSES/`
  carry the license text. Do not add project copyright/license banners to source or documentation.
- Preserve third-party notices, bundled licenses and the managed AEGIS payload.
  Prompt resources retain the exact legal prefix required by their loader; it is excluded from Pi prompts.
  Generated standalone files and deployed Pi extensions retain required notices.
  Distribution tooling includes the license texts and metadata in delivered files and media.

<!-- AEGIS:BEGIN (managed by .agentic/aegis.py init) -->

## AEGIS workflow

This repository uses AEGIS for changes that add or change a durable product
rule: logic, data, security, performance, integrations, or a product-wide UI
rule such as a theme, layout system, accessibility or interaction
convention. For those, read `.agentic/AGENTS.md` first; it routes you to one
step file per stage.

Make other changes directly, with no journal or requirement: a bug fix that
restores intended behavior, a local UI adjustment (one element's position,
spacing, wording or style), a refactor with no behavior change, or a test,
docs or tooling fix. A fix that contradicts an active requirement, adds
behavior, or touches security or data handling uses AEGIS. The user's
explicit choice wins; otherwise start with one line,
`LANE: direct|aegis - <why>`.

- New AEGIS work: run `python .agentic/aegis.py status` (an open task may
  cover it), then follow `.agentic/steps/1_frame.md`.
- An existing task: run `python .agentic/aegis.py brief TASK-<id>` and read
  what its `Read next` line names.

Stages: frame -> specify -> design -> build -> validate -> done; specify and
design have skip rules for work that does not need them. The CLI writes the
journal state:
`advance` finishes a stage, `pause` stops for the user, `log` and `ruling`
record events and decisions. End every session with `advance` or `pause`.

AEGIS guides and never blocks; `python .agentic/aegis.py check` is advisory.
Commits, pushes, merges, tickets, releases and packaging follow the
repository's own procedures, not AEGIS.

Say a deviation when you record one, as one line -
`DEVIATION <stage>: <what> - <why accepted, or what it costs>` - then carry on.

<!-- AEGIS:END -->
