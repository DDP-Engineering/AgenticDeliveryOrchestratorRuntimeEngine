<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage 1 — frame

**Purpose:** Turn the ask into an agreed scope and a chosen path, and open
the task journal that every later stage reads and updates.

**Read first:**

- The prompt itself, and anything it points at.
- `.agentic/AGENTS.md` (stage table, artifact locations, interaction modes).
- `.agentic/templates/task.md` before creating or editing the journal. Generated
  journals link this guide but omit its authoring notes. Reuse it if already read.
- `.agentic/context/project.md` and relevant sections of
  `.agentic/context/environment.md`, when present. Follow their authoritative
  references; confirm facts against this checkout. Missing context is an
  invitation to inspect, not a blocker. Populate only confirmed current facts
  within scope; keep proposed features and unresolved questions in the Frame.
- `python .agentic/aegis.py status` — an open task may already cover this.
- `python .agentic/aegis.py components` when the prompt does not already name
  an exact component page; use its title-and-path list to choose candidates.
- The knowledge page for the area named in the ask, if one exists:
  `.agentic/knowledge/<component>.md`. Read its `## Routing` selection signals
  first to confirm ownership or follow the named adjacent route. If it is a
  legacy page without Routing, use its available sections only to locate the
  exact source and tests, and include page reconciliation in the task scope.

**Reporting and resume:** Follow `.agentic/AGENTS.md` sections "Resume a task",
"Rulings and handoffs", and "Stage reporting". At transitions and pauses,
update the current checklist, minimal Handoff and Stage report, then show
`summary TASK-<id>` before detail. Use `.agentic/templates/task.md`: one plain
`key: value` per line, with comma-separated paths on the single `must_read:`
line. If summary reports a format error, repair the record and rerun it.
Read required durable evidence; missing or shortened
context requires review. This adds no approval stop and never defers a material
deviation notice. Reuse unchanged instructions already read in this session.

## Decisions before drafting

A new interface or data format requires the full path even when the core logic
stays unchanged. Inspect what exists before describing the current problem;
do not describe a requested interface as an existing one without evidence.
The chosen path must agree in the header, Frame, Log and continuation choices.

`Problem` describes the reported or observed undesirable condition; `Desired
outcome` describes what should hold after the change. Their difference is the
reason for a fix. Read the accepted outcome, scope, requirements and Rulings
before declaring a contract conflict. A bug description does not authorize
preserving the bug, and a historical problem may already be fixed in the checkout.

Unspecified behavior stays in Unknowns across every Frame field. An example,
constraint or exclusion cannot settle an open decision. Only user instructions
or an established contract can settle it; label unaccepted options as proposed.

## Frame card

Use the semantic analysis protocol in `.agentic/AGENTS.md`, then fill the
journal's `## Frame` section. Keep entries concise, but preserve every material
unknown instead of completing the picture by invention:

```text
Problem:
Desired outcome:
Actors:
Primary scenario: trigger -> system action -> observable result
Examples:
Counterexamples:
In scope:
Out of scope:
Constraints:
Success signals:
Evidence: STATED; OBSERVED with paths; INFERRED; UNKNOWN
Assumptions:
Unknowns:
Decision-blocking questions:
Proposed behaviors:
Path and reason:
```

**Steps:**

1. **Analyze.** Extract the user's problem, desired outcome, actors, primary
   scenario, examples, constraints, success signals, explicit scope, and
   exclusions. Preserve the user's terms where changing them could change
   meaning.
2. Locate the smallest sufficient repository evidence. Use
   `python .agentic/aegis.py components` to narrow broad discovery when the
   owning page is not already known, then use each current component page's
   `## Routing` selection signals to confirm ownership and its
   starting seams. For a legacy page, use the available sections as provisional
   orientation and record the missing routing contract for validation. Then
   inspect the exact interfaces, representative source, and tests. Record
   each claim under its own source label; a sentence may need separate labels:

   | Label | Required source |
   |---|---|
   | STATED | The user's actual words or an explicitly cited authoritative clause; no added example values or conclusions |
   | OBSERVED | A file, test definition or command result actually inspected, with its path or command |
   | INFERRED | A conclusion or constructed example derived from stated/observed premises; name those premises |
   | UNKNOWN | A claim for which the available sources do not establish an answer |

   A requested output shape is `STATED`; applying it to an example input chosen
   by the agent is `INFERRED`. Even when a normalizer's input/output pair appears
   in a test, projecting that pair into a new interface is an inferred example.
   Cite the test pair as an `OBSERVED` assertion, not an observed execution.
   A repository's lack of an interface is an observation within the inspected
   scope, not a user statement. Do not label a whole mixed-origin line `STATED`
   merely because one part came from the request. Split the claims instead.
   A request to add behavior does not establish a current defect, existing
   storage, or accumulated data. In `Problem`, state the requested capability
   and keep unverified current conditions `UNKNOWN`. An `INFERRED` label cannot
   supply missing premises; omit an unsupported assertion instead.
   Do not edit product files.
3. **Challenge.** Look for contradictions between the request, existing
   behavior, requirements, and repository rules. Identify missing triggers,
   observers, boundaries, failure cases, permissions, compatibility effects,
   security or data concerns, and assumptions. Ask only decision-blocking
   questions; carry other gaps as `UNKNOWN`.
   A question blocks Frame when its answer changes the desired outcome,
   authorized scope, destructive-data policy, or path decision. Keep details
   needed only to specify an already understood outcome as explicit later
   unknowns. Distinguish the product's automatic trigger from its exact cadence;
   do not demand a schedule, option ordering or formatting preference merely
   to complete the Frame. If a detail does block scope, say what decision it changes.
   For destructive cleanup, ask which records are authorized targets and whether
   removal must be recoverable when those choices are unresolved. Put the actual
   policy question in Decision-blocking questions and both next fields; asking
   permission to defer it is not resolving it. Acknowledge the requested feature
   without claiming its destructive scope is accepted. Exact scheduling and
   implementation details can wait; an undecided deletion policy cannot.
   An inference is not an agreed behavior. Keep any unspecified observable
   outcome in `Unknowns`, even when a convention suggests an answer. Do not
   choose error responses, exit codes, output formatting, data thresholds or
   reversibility by convention. If useful, list alternatives under `Proposed
   behaviors` as unaccepted options linked to the open question. Do not also
   state one as a scope commitment, success signal or normative example.
   Apply this to `Constraints` and `Assumptions` too: a convenient library,
   dependency restriction or successful exit code is not user authority.
   An assumption stays tentative; repeat it elsewhere only as an unaccepted
   option. Quick-path criteria without evidence remain unknown.
   Distinguish a current fact from a scope or policy decision:

   | Observation | What it establishes | What remains open |
   |---|---|---|
   | A component or store is absent here | No implementation found in this checkout | Whether the feature uses an external component or introduces one; absence does not exclude it from scope |
   | Current verification uses no external dependencies | That verification runs with the current environment | Whether the requested feature needs a dependency; a setup fact is not a prohibition on adding one |

   Apply the same source check to `Out of scope` as to `In scope` and
   `Constraints`. An exclusion must follow from the request, an agreed
   boundary or an explicit policy; absence or implementation convenience is
   insufficient. Keep unresolved boundaries in `Unknowns`. Every proposed
   option must still meet the stated outcome: a manual-only operation cannot
   satisfy a request for automatic behavior.
4. Draft the Frame card before performing branch or journal administration.
   Include at least one concrete example or record that none was supplied,
   and add a counterexample when it materially clarifies the boundary.
   Success signals describe observable product outcomes. Keep entries short;
   edit the relevant section instead of rewriting the whole journal.
   Every normative example or counterexample must hold under the agreed contract.
   If eligibility depends on an unknown age basis or threshold, do not call a
   record eligible or exempt merely because it was recently saved or used.
   Record the unknown boundary or label alternatives as unaccepted options.
5. Choose the path. Take the **quick path** only when all of these hold: no
   new externally observable behavior, no new interface or data format, no
   new dependency, an existing requirement already covers the behavior, and
   no security- or data-handling behavior changes. Otherwise take the full
   path. "New" means a change to the intended contract; restoring required
   behavior is not a new contract. Record one row per criterion as
   `criterion | yes/no/unknown | evidence`;
   any `no` or unknown selects the full path.
   Keep the criteria's negative wording in those rows: `yes` means the
   no-new-change condition holds. One disqualifying row does not settle the
   others. A new interface alone does not establish a security or data-handling
   change, and current dependencies do not establish a ban on new dependencies.
6. Decide whether the work is large enough for optional children. Use children
   only for independently scoped work that can remain an ordinary governed
   task; keep small or tightly coupled work in the parent.
7. Establish the branch. If instructed to keep the existing branch, record
   that choice and do not attempt branch creation. Otherwise, create a task
   branch only when on the repository's default branch
   (`git checkout -b task/<short-slug>`, or the repository's convention).
   The journal's `branch:` header must match `git branch --show-current`.
8. Create the journal:
   `python .agentic/aegis.py task "<title>" --type feature`
   (`--type fix` or `--type change` as appropriate).
   Retain the returned TASK ID and path and use that journal for all subsequent
   edits. Create only one journal for this task: an incomplete scaffold or a
   rejected edit requires repair of that same file, not another `task` call.
   If creation's outcome is uncertain, inspect status and the task directory
   before deciding whether creation needs retrying. List directories with the
   directory tool; read only named files. Do not delete or regenerate journals
   to hide a failed operation.
9. Fill the journal header and copy the provisional Frame card into its
   `## Frame` section. Leave `requirements:` empty until `specify`
   (quick path: fill it now with the existing requirement IDs).
   Save the Frame even when policy questions remain open: record the known
   request, explicit unknowns and blocking questions. An unresolved decision
   pauses scope acceptance, not these authorized record writes. Finish and
   reread the saved Frame, checklist, Handoff and Stage report before summary;
   an intended edit or a Log entry does not establish that those sections exist.
   For an existing-contract quick fix, write those IDs into the authoritative
   header now; citing them only in Frame or coverage is insufficient. Preserve
   existing IDs on a limited refresh. Check the saved header before summary.
   Keep the generated copyright/license block before the title unchanged.
   Preserve the generated journal's visible authoring-guide paragraph after the
   header, even if replacing sections or recovering from a failed edit. It is
   part of the journal, not an authoring comment to strip after reading.
10. Keep the detailed scope, exclusions, unknowns, path analysis, and proposed
    behaviors in `## Frame`. Append one concise `frame` outcome line to
    `## Log`, naming the chosen path and whether scope was accepted or paused.
    Put durable authority or scope decisions in Rulings instead of repeating
    them in the Log.
11. **Audit.** Check that every material claim is classified, every proposed
    behavior supports a success signal, no unknown became invented behavior,
    and scope, exclusions, examples, and path agree. Copy this stage's complete
    Done checklist and reread the saved section to confirm the placeholder was
    replaced. After a rejected edit, reread the current text, repair that same
    section using its exact content, and verify success before running summary
    or claiming the checkpoint is complete.
    For every `STATED` claim, locate the exact supporting words in its cited
    source. If the source gives only a rule and the claim computes an example,
    relabel that example `INFERRED`; do not use "based on the contract" to turn
    a deduction into a statement. Check the saved Examples and Problem fields
    as well as Evidence. Confirm the original license block is still present.
    Distinguish the requested outcome from proposed details: an `INFERRED`
    label does not resolve an `UNKNOWN` or authorize a default. Keep decisions
    open until supported by the user or an established requirement; record
    which source settles them. Ask blocking questions now, rather than saying
    a later stage will ask them.
    For each added constraint or observable detail, name its stated or
    established-contract source; otherwise move it to the open questions or
    unaccepted options. Conventional exit codes, argument ordering and output
    formatting still affect the observable contract.
12. At a checkpoint or explicit stop after frame, keep the header at frame.
    Save Handoff `current: frame`, `status: waiting` and Stage report
    `current: frame`, `result: paused`, `needs_user: yes`. Name the pending scope
    decision in both `next` fields; scope acceptance remains pending.
    If a destructive-policy or authorized-target question still blocks Frame,
    ask it first in both fields and the response. Request general scope
    acceptance only after those blocking choices are resolved; do not treat
    acceptance of an unresolved feature description as acceptance of its policy.
    Ask the specific scope question there, such as whether to accept the framed
    restoration and continue to build. Keep the checkpoint menu in the response,
    not in `next`. Read the review setting: when disabled, set both verdicts to
    `disabled` and leave `review_round` blank, including at Frame.
    Run summary after these edits and show its output first in one code block.
    A stop after Frame still permits completing and repairing its record writes;
    it prevents starting specification or implementation. Follow the task guide's
    write-recovery method instead of leaving a repairable text mismatch unresolved.
    If it reports missing Stage report or a format error, repair the saved
    records from the task template and rerun it before responding. An exit zero
    with missing records is not a completed checkpoint.
    If summary omits an existing requirement that this quick fix restores,
    repair the header and rerun summary; do not publish that omission as the result.
    Then present the concise Frame, path, assumptions, decision-blocking
    questions and `frame` Stage-boundary choices. Stop before specification or build.
    An explicit stop also applies in autopilot. Otherwise autopilot records
    the frame outcome and continues without the intermediate menu.
13. After the user chooses to continue, or immediately in autopilot, record
    scope acceptance, set `stage: specify` (full path) or `stage: build`
    (quick path), and replace `## Done checklist` with the next stage's Done
    when list. Before work in that stage, read `.agentic/steps/2_specify.md`
    for the full path or `.agentic/steps/4_build.md` for the quick path.

**Outputs:**

- `.agentic/tasks/TASK-<id>.md` - created with a complete header, durable
  Frame card, evidence classifications, one frame outcome line, and current
  checklist.

**Done when:**

- [ ] Frame card states the problem, outcome, actors, scenario, scope,
      examples, constraints, success signals, evidence, and unknowns
- [ ] material claims classified as stated, observed, inferred, or unknown
- [ ] contradictions and decision-blocking questions resolved or presented
- [ ] path chosen (`full` or `quick`) with its reason logged
- [ ] task branch established; `branch:` header matches the checkout
- [ ] task journal created with a complete header
- [ ] proposed behaviors map to the desired outcome and success signals
- [ ] scope confirmed by the user (checkpoint mode) or logged (autopilot)
- [ ] `stage:` advanced

**Skip when:** Never. Every task starts here, however small. If the prompt
names an existing task, do not frame it again — follow the resume
procedure in `.agentic/AGENTS.md` instead.
