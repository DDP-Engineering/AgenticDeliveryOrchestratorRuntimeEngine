<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# CLAUDE.md

Claude Code should treat `AGENTS.md` as the authoritative workflow contract for
this repository. Read `AGENTS.md` first, then use this file only as the Claude
Code adapter note.

If this file and `AGENTS.md` disagree, follow `AGENTS.md`.

Claude direct skill invocation uses `/skill-name`. Existing Codex-style
references such as `$documentation-audit` mean the matching Claude Code skill,
for example `/documentation-audit`.

Release notes: every user-visible `CHANGELOG.md` entry gets a matching
four-locale entry in `04_Software/adore/release_notes.toml` in the same change,
and the journal records `release-notes: added | updated | none (<reason>)`; see
`AGENTS.md` "Release notes rules".

Help: an interface or workflow change also updates the affected in-app help
topics in `04_Software/web/src/help/content/` (all four locales) in the same
change, and the journal records `help: updated | none (<reason>)`; see
`AGENTS.md` "Help content rules".

<!-- AEGIS:BEGIN (managed by .agentic/aegis.py init) -->

## AEGIS workflow

This repository uses AEGIS to guide software implementation, one feature,
fix or change per task. Before changing the product, read
`.agentic/AGENTS.md`; it routes you to one step file per stage.

- New work: run `python .agentic/aegis.py status` (an open task may cover
  it), then follow `.agentic/steps/1_frame.md`.
- An existing task: run `python .agentic/aegis.py brief TASK-<id>` and read
  what its `Read next` line names.

Stages: frame -> specify -> design -> build -> validate -> done; the quick
path is frame -> build -> validate -> done. The CLI writes the journal state:
`advance` finishes a stage, `pause` stops for the user, `log` and `ruling`
record events and decisions. End every session with `advance` or `pause`.

AEGIS guides and never blocks; `python .agentic/aegis.py check` is advisory.
Commits, pushes, merges, tickets, releases and packaging follow the
repository's own procedures, not AEGIS.

Say a deviation when you record one, as one line -
`DEVIATION <stage>: <what> - <why accepted, or what it costs>` - then carry on.

<!-- AEGIS:END -->
