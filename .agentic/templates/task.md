<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!-- AEGIS:TEMPLATE
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

For an existing task, the latest user request defines the operation. The stage
header is state, not permission to start that stage. Honor explicit limits on
implementation and verification, including when reconciling stale records.
Record-only work still changes a file: name the journal and edited sections in
changed. "No product files changed" does not mean "No files changed". Before
summary, copy the observed review setting into both verdict fields: disabled
review requires `disabled`, never blank, even when no review was performed.
For an existing journal, use its bare TASK-<id> with brief or summary and its
path with file tools. The task command creates a new journal from a title;
it does not load an existing ID. After creation, retain its returned ID/path
and repair that same journal; never create another because fields or checklists
are incomplete or an edit failed. If creation's outcome is uncertain, inspect
status and the task directory before retrying. Preserve existing journals and
their history.

Confirm each record write succeeded before sending the next dependent edit.
Tool string values must contain actual line breaks and quotes from the read
text, not a JSON-serialized representation of that text. Do not double-escape
it. An exact-match rejection changes nothing: reread the section and replace a
small unique fragment using its actual text. If matching still fails, read the
whole current journal and write it back with only the authorized sections
changed, preserving the original legal prologue and every untouched section.
Use the current file, not a fresh template, for this fallback. Reread the saved
sections and verify their contents, including the complete checklist and report
fields, before summary. A repairable text mismatch does not require user approval
or justify abandoning authorized record updates at a stage stop.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  interaction   checkpoint | autopilot; copied from .agentic/aegis.toml
                when created and updated when an explicit user instruction
                overrides it
  requirements  comma-separated requirement IDs; empty until specify except
                an existing-contract quick fix, which records its existing IDs
                at frame; preserve IDs during record-only updates
  parent        optional top-level TASK-id; blank for an ordinary task
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
The first copyright/license comment block, before the title, is legal content,
not an `AEGIS:TEMPLATE` authoring note. Preserve that entire existing block
verbatim, including license references and SPDX text. Read it from the actual
journal, including a newly generated journal, before editing. Do not recreate
it from memory or copy another project's attribution. Prefer section edits;
if a full rewrite is necessary, carry the original prologue and untouched
sections forward. After writing, reread the beginning and compare it with the
original block. Restore any lost or changed lines before running summary.
The visible paragraph linking this authoring guide, immediately after the
header, stays in the generated journal. Preserve it on every edit or rewrite;
having read the guide does not remove its value for a later session. Prefer
section edits and preserve all untouched sections when recovering a failed edit.
The Log is a progress-and-evidence ledger, not an activity transcript. Append
only durable events that change the task's stage, scope, engineering outcome,
verification status, authority, or ability to proceed: stage transitions;
material scope or implementation decisions not already captured elsewhere;
consolidated automated or manual verification results; material discoveries;
blockers; approvals; deviations; and delivery outcomes.

Do not log routine searches, reads, edits, internal tool mechanics or corrected
command retries, and do not copy requirements, designs, specifications,
knowledge pages, Rulings, Handoff, or Stage report content into the Log. A
failed command belongs only when it exposes a candidate problem, changes the
implementation or tests, or remains an accepted verification limitation. Keep
each entry concise and self-contained; reference durable artifacts instead of
repeating them. Existing entries remain append-only under later contracts.
Record each consolidated outcome once. After a successful append, proceed to
Handoff, Stage report and summary; an already recorded outcome needs no duplicate.

Append a Log entry by inserting immediately before the following section
heading. Use that heading alone as the unique edit anchor, preserving it in the
replacement; keep every existing Log character outside the replacement. Do not
copy the last evidence line into the edit merely to locate the insertion point:
retyping can normalize spaces, punctuation or command output. If a full rewrite
is necessary, splice the original Log text unchanged and append the new entry.
Compare the saved old Log prefix character for character with the original;
restore any changed whitespace as well as content before summary. A new outcome
belongs after the old entries, never inside an earlier evidence line.

At a checkpoint, explicit stop or session end, including a record-only update:
save Handoff status: waiting, Stage report result: paused and needs_user: yes.
Both current fields must equal the header; report stage names the reported
stage. A blocking decision uses blocked instead. Set both next fields to the
specific pending action or decision. Update the saved fields even if the stage
did not change; saying "stopped" only in the response is insufficient.
When explicit review is disabled, both verdicts are disabled and review_round
is blank. Derive that setting from the current configuration or observed brief;
do this on limited record refreshes too. Blank verdicts mean no recorded verdict,
not disabled review. Use only the typed values listed below; unavailable evidence
does not
permit unavailable, success, failed or zero in status, result or review fields.
Leave unknown evidence blank. If no verification ran, keep evidence blank and
put that absence and any user report in issues or the Log. This does not erase
actual inspection evidence when the operation included inspection. Cite actual
command results; inspection of code
or test definitions is not an executed test. Preserve history and report any
action that exceeded the request honestly.
Missing historical proof remains missing; a new run cannot establish that a
test ran before an existing implementation change.
Do not offer to reconstruct past red/green execution or create a retroactive
build-start anchor. Preserve the missing history as a limitation. If the next
authorized operation is current verification, name its command and present
scope only; if a decision about the historical gap is required, ask that
specific decision without promising to recover the past.
Before selecting a build action, inspect the current changed source and relevant
test or name that inspection as next if it has not been done. A modified path
does not reveal whether the candidate currently fails. If the fix is already
present and focused verification is next, name the configured command on the
current tree. Do not promise a red result or undo code to manufacture missing
history. Missing historical evidence belongs in issues, not blockers, unless
an identified policy requires a specific decision before the next operation.
Choose exactly one next operation before writing either next field:
- The next executable operation: name the action and actual target. For
  verification, name the command and current candidate.
- A required user decision: ask the concrete question that resolves the blocker,
  such as accepting the framed scope or authorizing delivery of a validated tree.
Do not save the stage-boundary menu in either next field. "Await direction" or
"choose how to proceed" is not a scoped question. The requested stop applies
now; describe what a later resume should do without adding an approval gate
that no instruction requires. Missing historical evidence alone does not name
such a decision: keep it as a limitation and identify the actual current action
or the specific policy disposition needed, without promising to recreate history.
Keep unavailable historical red/anchor records in issues. Never combine
current verification with a promise to "record the missing red/anchor/green
evidence"; the new result covers only the execution performed now. Audit the
saved next fields themselves, even when the surrounding explanation is correct.
An explicit scope decision updates the Rulings even when older scope text
conflicts. Preserve that history and identify any unresolved inconsistency;
do not silently treat unrelated old Frame text as acceptance of the new scope.
Supersede only by appending a new Ruling with `supersedes=RULING-<old-id>`.
Do not edit or annotate the earlier line, including its reason or decision.
The new link marks the earlier decision superseded; no backward annotation is
needed when the user asks to mark it superseded.
Interpret each Frame field by its role: Problem records an undesirable condition,
while Desired outcome and accepted scope state the target behavior. A problem
description can describe the original bug even after the current tree fixes it.
Compare normative outcomes with the requirement and Rulings; quote the actual
incompatible commitments before claiming a scope conflict. The difference between
a defect and its accepted correction does not require a new scope decision.
When source and tests already match the accepted outcome, choose current focused
verification as next rather than asking which of the bug and outcome governs.
Compare the decision with the saved Frame/path. If they conflict, name that
unreconciled scope in issues and the required next decision; do not rewrite
Frame or implement it under a record-only request.
Keep the sources separate: quote the actual conflicting Frame clause and name
the Ruling that contains each decision. Never transfer a value from an old
Ruling into a claim about what Frame says. When the saved Frame concerns a
different behavior, say which behavior it covers and reconcile that scope first.
An unresolved prerequisite takes precedence over the destination stage: next
must resolve it first, and Handoff blockers must name it. Do not record a scope
conflict in issues while directing next straight to specification or build.
Describe missing records as observed absence. Do not infer who changed the
candidate, when, or in which session unless durable evidence establishes it.
At a return or transition, read the destination step and copy its complete
"Done when" checklist verbatim. Do not invent a shorter generic checklist.
In changed, name only edits made during this operation; put inspected
pre-existing candidate changes in evidence or issues.
Before summary, reread the saved header, Handoff and Stage report. Check that
the existing IDs required by this task and path are in the header, both next fields describe the same
operation, blockers and next agree, and disabled-review fields are explicitly
disabled. Use the accepted Frame and actual rulings when describing scope;
requirement status or missing implementation cannot erase an accepted behavior.
After these edits, run summary TASK-<id>; fix malformed fields if it fails.
Use separate physical lines for the saved snapshot. For example, a bounded
autopilot transition from Design to Build with no missing human decision uses
the following Stage report values (substitute actual paths and evidence):

stage: design
result: completed
current: build
changed: .agentic/tasks/TASK-<id>.md
evidence: <observed Design inspection or command result>
issues:
next: Run <focused-test-command> before the implementation change
needs_user: no
spec_compliance: disabled
implementation_quality: disabled
review_round:

Its header and Handoff current are build; Handoff status is ready, with the
same next action. This records the completed transition, not completed Build.
For a checkpoint, requested stop or session end, use waiting/paused/yes as
specified above instead. A bounded transition request can end before Build
without requiring a new human decision. Review fields follow the actual config.
The example is plain saved fields, not a literal backslash-n string, bullet,
table, or code fence. If summary reports malformed fields, reread the current
section, repair those fields, reread it and rerun summary before responding.
If summary says the Stage report is not recorded, complete the saved snapshot
and rerun even when the command exits zero. Do not author a replacement summary.
Copy its output unchanged as the first response block, before introductory
prose or details; only an immediate deviation notice may precede it. Do not
reformat its fields or duplicate the raw Handoff and Stage report.
Copy every line, including Details, truncation markers and instructions to read
the full journal. After reading shortened content, repair overly long saved
fields and rerun summary if needed; do not silently expand the printed output
or replace its Needs user warning. Keep explanations after the exact block.
Response shape after any immediate deviation notice:
```text
<entire actual summary stdout, unchanged>
```
Then explain the operation. The fence is required; Markdown line breaks are
not a substitute for it.
A pause or record-only update is not completion of the stage. State the one
pending action or decision, not a generic completion menu. Offer a transition
only when the stage's requirements, review and proof permit it; otherwise
describe the unmet prerequisite. Proposed exceptions remain pending and never
grant authority to advance.
-->

# TASK-0000 — <one-line title>

stage: frame
type: feature
path: full
interaction: checkpoint
requirements:
parent:
branch: <branch>
base:
opened: 2026-01-01

Before editing this journal, read `.agentic/templates/task.md` for record syntax
and pause/report rules. Reuse its guidance if already read in this intact session.

## Done checklist (current stage)

- [ ] copy the "Done when" list from the current step file here

## Frame

Problem:
Desired outcome:
Actors:
Primary scenario:
Examples:
Counterexamples:
In scope:
Out of scope:
Constraints:
Success signals:
Evidence:
Assumptions:
Unknowns:
Decision-blocking questions:
Proposed behaviors:
Path and reason:

## Requirement coverage

<!-- AEGIS:TEMPLATE
A broad Frame outcome may produce several atomic behavior rows. Each
atomic behavior maps to exactly one requirement. Keep this table current
through design.
| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
-->

## Design

<!-- AEGIS:TEMPLATE
Filled at design when the task is non-trivial; otherwise record why skipped.
-->

## Log

- 2026-01-01 frame: <scope accepted or pending, exclusions, chosen path and why>

## Rulings

<!-- AEGIS:TEMPLATE
Append decisions here; never edit history. Supersede with a new ruling.
Use the single-line record format below, including every named field.
Do not replace it with a prose bullet or split it across lines.
If there is no new decision, leave this section unchanged or empty. Never
append a placeholder Ruling saying None, pending, or no decision authorized.
- RULING-001 | date=YYYY-MM-DD | decision=<decision> | reason=<reason> | source=user | supersedes=none
source: user | repository | requirement | technical
-->

## Handoff

<!-- AEGIS:TEMPLATE
Replace these fields with the latest minimal resume snapshot.
One plain key: value per line, no bullets or continuation lines.
must_read holds comma-separated repository-relative paths on ONE line.
Replace placeholders with a concrete question/action and actual paths. Do not
copy generic text such as "the recorded next action" into either next field.
Keep next concise; put the supporting explanation in issues or the Log.
Example of a paused build (substitute the actual stage, action and paths):
current: build
status: waiting
next: Run <focused-test-command> on the current candidate after this requested pause
must_read: .agentic/tasks/TASK-<id>.md, .agentic/steps/4_build.md
blockers:
-->

current:
status:
next:
must_read:
blockers:

## Stage report

<!-- AEGIS:TEMPLATE
One replaceable snapshot. Plain `key: value`, one per line, no fences, no
bullets - `summary` and `check` both reject anything else.
result: in_progress | completed | paused | blocked | skipped
spec_compliance: approved | changes_required | disabled
implementation_quality: approved | changes_required | disabled
review_round: 1 through 1 + configured max_fix_cycles, or blank when disabled
stage is the reported stage; current must match the journal header after any
transition. At a stop: result: paused, needs_user: yes, Handoff status: waiting.
If the reviewed candidate changed, clear both verdicts, retain the consumed
review_round and name the invalidation in issues; preserve historical Log entries.
Leave unknown fields blank; summary prints not recorded.
-->

stage:
result:
current:
changed:
evidence:
issues:
next:
needs_user:
spec_compliance:
implementation_quality:
review_round:
