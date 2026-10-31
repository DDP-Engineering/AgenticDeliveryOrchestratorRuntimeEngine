<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage 3 — design

**Purpose:** Write a short design note for non-trivial work, so that
`build` has a sufficiently constrained implementation path, material open
decisions remain explicit, and a reviewer can see why the shape was chosen.

**Checkpoint response:** assemble it from saved artifacts, in this order:

1. The actual summary stdout inside a plain text fence.
2. When this stage generated diagrams, read their saved file and copy each
   diagram's complete Mermaid fence into the response, preserving its content.
3. The Design boundary choices, including pause.

Finish this assembly before sending; a path or description does not supply
part 2. Autopilot reports the saved diagram path without displaying diagrams.

**Read first:**

- The task journal `.agentic/tasks/TASK-<id>.md`.
- Every requirement listed on its `requirements:` line, and their specs.
- `python .agentic/aegis.py components` when boundaries or adjacent ownership
  leave an in-scope component page unnamed.
- The knowledge page for each component you will touch:
  `.agentic/knowledge/<component>.md`. Use `## Change map` for the relevant
  edit-and-test seam when present, then check the named exact source and tests.
  For a legacy page without Routing, use its available sections only as
  provisional orientation and leave migration to validate.

**Reporting and resume:** Follow `.agentic/AGENTS.md` sections "Resume a task",
"Rulings and handoffs", and "Stage reporting". At transitions and pauses,
update the current checklist, minimal Handoff and Stage report, then show
`summary TASK-<id>`. Read required durable evidence; missing or shortened
context requires review. This adds no approval stop and never defers a material
deviation notice. Reuse unchanged instructions already read in this session.
If a journal edit fails an exact-text match, reread the current section and
repair that same journal using the task template's fallback. Finish the saved
Design and pause/transition records before responding; do not abandon a
permitted record update because one text fragment was stale.

**Steps:**

1. Decide whether a note is needed; see Skip when. If not, record the reason in
   `## Design` and mark every coverage-table row `no design impact`.
2. **Analyze** the Frame, requirements, specs, current component knowledge,
   and representative implementation seams. Preserve the page's boundaries
   and invariants; use its `## Change map` only as a route, then verify the
   exact implementation. **Challenge** contradictions, infeasible constraints,
   implicit coupling, missing failure behavior, and unresolved decisions
   before choosing a shape.
   Separate a proposed new interface from an existing function it calls:
   their different invocation styles alone are not conflicting contracts.
   Resolve component paths from journal links or `components`, then read the
   owning page; do not infer a missing page from a guessed filename.
3. Write the note under the journal's existing `## Design` heading. 30 lines is the default,
   not a hard limit: use the shortest record that makes
   the known implementation path sufficiently constrained. Add proportionate
   depth when the task changes an interface, data or state, trust boundary,
   concurrency, dependency, migration, compatibility, deployment, or recovery.
4. Cover the applicable parts in this order:

   - **Requirements coverage** - each ID maps to a decision or `no design impact`.
   - **Component responsibilities** - ownership and boundaries.
   - **Interfaces and contracts** - inputs, outputs, defaults, and errors.
   - **Data ownership and state transitions** - persistence, lifecycle, and units.
   - **Execution flow** - the primary path and material asynchronous work.
   - **Failure recovery** - partial failure, retries, cleanup, and idempotency.
   - **Security and trust boundaries** - only where relevant.
   - **Concurrency and ordering** - only where relevant.
   - **Compatibility and migration** - rollout, rollback, or deliberate break.
   - **Observability and operations** - evidence needed to diagnose behavior.
   - **Test seams** - where each requirement's failing and regression tests attach.
   - **Alternatives and tradeoffs** - meaningful rejected options and reasons.
   - **Expected files**, **Risks**, and **Open decisions**.

5. Cite the forcing requirement ID next to every requirement-driven decision;
   cite a named technical constraint for decisions that no requirement forces.
   Never convert an open product decision into an implementation choice.
6. Update the journal's `## Requirement coverage` table so every requirement
   names its design decision, test seam, or `no design impact`.
7. List expected files and update each requirement's `affected_paths`.
   For child tasks, define non-overlapping child scopes and requirement links;
   integration ownership remains with the parent.
8. Keep the proposal in the task journal. Leave every
   `.agentic/knowledge/<component>.md` page unchanged during design; validate
   reconciles those current-state pages with the reviewed implementation.
9. Keep requirement-specific format, protocol, algorithm, or edge behavior in
   the linked spec rather than duplicating it in the task design.
10. **Audit** traceability, feasibility, interfaces, state ownership, failure
    behavior, compatibility, verification seams, risks, and open decisions.
    Run `python .agentic/aegis.py check` and fix format errors.
11. If `.agentic/aegis.toml` sets `[diagrams] enabled = true` (a TOML boolean),
    read `.agentic/steps/diagrams.md` and apply its types gate before generating.
    An empty types list generates no file or link. Any other enabled value,
    or no `[diagrams]` table, means no diagrams. An explicit stop after Design
    still includes enabled applicable artifacts, while keeping `stage: design`
    and its checklist; do not advance to Build.
12. Preserve the current journal and its existing `## Log` section verbatim.
    A full rewrite starts from that current file, never a fresh template;
    verify the old Log prefix is still present and unchanged before summary.
    Insert the outcome at the following heading without recopying old entries.
    Append one concise `design` outcome line pointing to `## Design` and any
    linked spec; do not copy decisions into the Log. In checkpoint mode, show
    the summary, then the diagrams of any diagram file this stage wrote, then
    the `design` Stage-boundary choices from `.agentic/AGENTS.md`; refresh the
    waiting Handoff and paused Stage report, then stop before transition. After
    the user chooses to continue, or immediately in autopilot when no explicit
    stop forbids the transition, tick the
    checklist, set `stage: build`, and replace `## Done checklist` with the
    build stage's Done when list. Save and reread the matching Handoff/Stage
    report and repair any summary format error before reporting the transition.
    A bounded autopilot request to transition only stops before Build work with
    ready/completed/needs_user=no when no human decision is pending. Before build work, read
    `.agentic/steps/4_build.md`. If the user instead returns to Specify, read
    `.agentic/steps/2_specify.md` before Specify work.

**Outputs:**

- `## Design` section in the task journal.
- `.agentic/tasks/diagram_TASK-<id>.md`, only when `[diagrams] enabled = true`.
- Updated `affected_paths` on the linked requirements.
- Updated spec sections where the detail belongs to the behavior.

**Done when:**

- [ ] design note written, or its absence justified in one line
- [ ] applicable component, interface, state, failure, security, concurrency,
      compatibility, migration, observability, and operational effects covered
- [ ] each decision cites a requirement ID or named technical constraint
- [ ] every requirement maps to a decision and test seam, or no design impact
- [ ] meaningful alternatives, risks, and open decisions recorded
- [ ] `affected_paths` match the expected file list
- [ ] current component knowledge remains true during design
- [ ] `stage: build`

**Skip when:** The quick path; or the work is a single-file change with no
new interface, data format, or dependency; or the spec already answers
"how". Skipping is a judgement recorded in `## Design` and the concise design
outcome, not a step silently dropped.
