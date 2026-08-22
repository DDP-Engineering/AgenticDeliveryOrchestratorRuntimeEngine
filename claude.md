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

To resume: `python .agentic/aegis.py status` lists the task journals; open
`.agentic/tasks/TASK-<id>.md`, read its `stage:` line and `## Log`, open
that stage's step file, and continue at the first unticked item of
`## Done checklist`.

Artifacts: requirements in `.agentic/requirements/<category>/`, specs in
`.agentic/specs/`, journals in `.agentic/tasks/`, component pages in
`.agentic/knowledge/`. `python .agentic/aegis.py check` is advisory - read
its findings and self-correct; nothing here blocks you mid-flight.

Say a deviation out loud when you record one, as one line -
`DEVIATION <stage>: <what> - <why accepted, or what it costs>` - then carry
on. It never pauses the work and autopilot never suppresses it. You owe one
for an accepted `check` warning, a non-zero exit or a verification you
skipped, an unexpected `anchor`/`evolution` report, a manual method standing
in for an automatable test, a retired requirement, and unrequested work found
in review.

<!-- AEGIS:END -->
