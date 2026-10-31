<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage 5 - validate

**Purpose:** Reconcile everything that may still change the candidate, then
prove the final tree before it is presented for publication.

**Execution order for full authorized validation:** finish source, requirement,
knowledge and context corrections; obtain enabled reviews; run final full proof;
then update only journal records and show the actual summary. Any later edit to
the proved candidate requires fresh relevant review and proof. If verification
fails, save its actual command, exit and scope in the journal, refresh the
pause/blocker and run summary before responding. A failed test is not a failed
journal write. A narrower user request still limits which actions may run.

**Read first:**

- The task journal `.agentic/tasks/TASK-<id>.md`, whole file.
- `.agentic/AGENTS.md` and `.agentic/templates/task.md` before editing records,
  unless their current authoring guidance is already in this intact session.
- Every requirement on its `requirements:` line.
- `python .agentic/aegis.py components` if diff review exposes an additional
  touched component whose knowledge page the task did not already name.
- The knowledge page of each component you touched.
- `.agentic/templates/component.md` when creating a missing page or migrating
  a touched legacy page.

**Reporting and resume:** Follow `.agentic/AGENTS.md` sections "Resume a task",
"Rulings and handoffs", and "Stage reporting". At transitions and pauses,
update the current checklist, minimal Handoff and Stage report, then show
`summary TASK-<id>` before detail, using `.agentic/templates/task.md` for
plain-field syntax. Read required durable evidence; missing or shortened
context requires review. This adds no approval stop and never defers a material
deviation notice. Reuse unchanged instructions already read in this session -
**except this step file.** If you read it before `build` began, read it again
now. Honor the requested stopping point: inspection or record updates do not
authorize repairs or verification excluded by the user. A prohibition on
changing source, tests or verification configuration still permits running the
existing configured validation commands; distinguish modification limits from
explicit execution limits.

## Optional explicit review and bounded re-review

Read `[review]` in `.agentic/aegis.toml` before applying this protocol.
When review is disabled, record both verdicts as `disabled`, leave
`review_round` blank, and skip only explicit verdicts and their fix loop.
Existing semantic review, full suite, strict check, evidence, and the delivery
checkpoint remain mandatory.

Apply this protocol after the semantic review, corrections, and documentation
updates in steps 1-8 below, and before the final proof in step 9.
Provide both reviewers the available focused proof and exact test assertions.
Final full strict proof is due after both approvals, not a prerequisite for
issuing those approvals. Reviewers still report missing evidence already due,
untested behavior and unsupported claims. An existing executed regression test
can cover a restoration without any test-file change. Candidate binding is
checked before and after each independent inspection; report both observations.
Identify each linked requirement, spec and journal by its current checkout path
in the review brief. Reviewers read those files even when untracked: an absent
HEAD version is not missing current scope. Include this evidence order in each
brief: inspect current files and focused proof, issue verdicts, then the
coordinator runs final full proof after approvals. Incomplete final-proof
checklist items at this point describe work still due, not failed execution.
For a request limited to processing supplied independent results for the
unchanged candidate, apply the decision below and report it; do not restart
reviews or run final proof while their outcome blocks further work.

When review is enabled:

1. Set a new review's initial `review_round` to 1; retain a consumed round on
   resume. The total bound is
   `1 + max_fix_cycles`; two fix cycles means three total review rounds.
2. Ask two questions and record independent verdicts. **Specification
   compliance** checks scope, exclusions, requirements, specs, and design.
   **Implementation quality** checks correctness, errors, tests, security,
   maintainability, portability, and unrequested work.
3. Both verdicts apply to the same current candidate. Any candidate change
   invalidates both verdicts: write blank `spec_compliance:` and
   `implementation_quality:` fields, retain the consumed `review_round`, and
   record why in issues and the Log. Re-review both roles when authorized and
   within the remaining budget. Saying "stale" does not clear saved approvals.
4. If either verdict is `changes_required` and a cycle remains, append the
   findings to the log and route to the appropriate existing stage.
5. Fix only the recorded findings, rerun relevant proof, increment the round,
   and return here. Do not expand scope or reset the counter to continue.
6. A specification ambiguity or scope change uses the existing human
   checkpoint; do not guess inside the loop.
7. If both current verdicts are `approved`, continue with the final proof and
   delivery transition below.
8. If either verdict still requires changes on the final allowed round, set
   `result: blocked`, `needs_user: yes`, and Handoff `status: blocked`.
   Retain the current verdicts/round, name the user decision and show summary.
   Do not repair, run final proof, or advance to deliver from this state.
   In both next fields and the response, ask for the specific scope or policy
   decision needed to unblock work. Accepting a finding as a limitation does
   not itself resolve a required behavior or permit delivery. Do not offer
   "accept the finding and advance" as an alternative to that decision.
   Read the accepted Frame and requirement prose before proposing a scope
   change: a draft requirement may already describe accepted scope. Changing
   its status alone neither adds that scope nor fixes the missing behavior.
   Compare the finding with the actual In scope and Out of scope text and
   subsequent user decisions. Name the accepted behavior and its source before
   describing the decision. Do not claim a behavior is excluded merely because
   its requirement is draft or its implementation is missing. If the sources
   conflict, preserve and name that conflict instead of inventing agreement.
   If the behavior is already accepted, do not offer adding or activating it
   as a scope change. Ask whether to authorize another review cycle under a
   changed policy, or to change the existing accepted contract. Keep both
   next fields concise and name that actual decision, not a generic reference.
9. Only an explicit human Ruling that changes scope or policy can reset the
   counter.
   Record the actual human decision as a Ruling; authoring a Ruling yourself
   does not create authority. After an authorized change, reconcile scope and
   requirements, complete any authorized corrections, and obtain current
   verdicts and proof before delivery. The proposed decision is still pending
   until the user makes it.
   Without a new human decision, leave Rulings unchanged or empty. Do not add
   a pseudo-Ruling to say that none exists or that authorization is pending.

**Steps:**

Parent validation owns the integrated candidate. Review all children visible
in this checkout, confirm each child was independently validated, and verify
their combined behavior against the parent's scope and requirements. A child
verdict or green suite does not replace integration proof in the parent.

1. Review the diff semantically, hunk by hunk, against the frame scope and
   exclusions, each requirement and its verification, the design note, error
   paths, Windows/Linux portability, secrets, security, and unrequested work.
   If a comparison tool is unavailable, record that limitation and inspect the
   current source, tests and requirements with available read tools. Do not loop
   over unavailable command variants or claim a comparison you did not observe.
   `source-no-test-changes` describes the diff, not test coverage. Read the
   existing tests before deciding a test is missing. If they already assert
   the required behavior and boundaries, retain them and explain that coverage;
   do not return to build merely because no test file changed. A return for
   missing coverage must name the specific untested behavior.
2. Send wrong assumptions backwards instead of patching around them here. Set
   `stage:` to `specify` or `design`, replace the checklist with that stage's
   "Done when" list, log why, and stop. An implementation flaw returns to
   `build` by the same protocol. Clear stale approvals as above and synchronize
   both current fields with the new header. Save `result: paused`,
   `needs_user: yes`, Handoff `status: waiting`, and the next authorized action.
   Stop at that return; a record-only request does not authorize repairs.
   Read the destination step file now and copy its entire "Done when" list
   verbatim, retaining its requirements and ordering. Do not substitute a
   shorter checklist from memory or run that stage's work to populate it.
   Use one comma-separated `must_read:` line with the journal, destination
   step and files needed for the next action; semicolons are not separators.
   On resuming, read
   `.agentic/steps/2_specify.md` for specify, `.agentic/steps/3_design.md`
   for design, or `.agentic/steps/4_build.md` for build.
3. Update component knowledge after implementation corrections. For every
   materially changed component, update or create
   `.agentic/knowledge/<component>.md` against the reviewed code and tests.
   Locate and read the existing owning page before choosing a new filename.
   Use the task's known page or the component index; a failed guessed-path read
   does not establish that the component has no knowledge page.
   If a touched legacy page lacks Routing or another standard section, or
   still carries a retired `## Architecture` section, migrate it to the
   current template at `.agentic/templates/component.md`: remove a retired
   `## Architecture` section and keep any still-true constraint from it in
   Purpose and boundaries or Invariants. Reconcile Routing,
   Purpose and boundaries, Public interface, Invariants, Key behaviors, and
   Files. Reconcile Change map when the
   component has multiple independent edit-and-test seams. Include any page
   updated earlier for a handoff. Finish these updates before the final
   independent reviews, when enabled, and final proof.
4. Reconcile project and environment context. Bring affected sections of
   `.agentic/context/project.md` and `.agentic/context/environment.md` into
   agreement with the same candidate and the canonical configuration and setup
   references. Populate missing files only with known in-scope facts; preserve
   unrelated sections. Project and component documents state current positive
   responsibilities and behavior. Replace stale claims; keep proposals,
   removed-feature inventories, before/after narratives, and investigation
   history in the journal. Leave unchanged sections untouched.
5. Re-read each requirement. Confirm its status and prose describe the built
   behavior, its verification matches the observation, and all affected paths
   and linked tests are current. Correct documentation drift now; a mismatch
   with an established contract returns to build or an authorized scope
   decision, rather than weakening the requirement to match the code. Active
   prose states the current positive outcome and meaningful failure responses.
   Resolve draft-spec open decisions before activation and retain their decision
   history in the journal, not the active spec.
6. Complete and record every `Manual:` or `Inspection:` verification. Name the
   method, action, and observed result; never substitute a manual label for an
   automatable test that is merely missing. Where a manual method stands in for
   a test that could have been written, state it as a deviation notice in the
   conversation, per `.agentic/AGENTS.md`.
7. If steps 1-6 changed executable behavior, tests, or verification configuration,
   run relevant focused proof as needed to resolve the change. Prose-only updates
   require semantic and traceability review; they do not alone require another
   runtime test run. Do not run an impacted set that expands to the full suite
   immediately before the final full proof.
8. If validation changed any repository file outside `.agentic/`, rerun
   `python .agentic/aegis.py evolution --task TASK-<id>` so the saved,
   timestamped report describes the final candidate. Review every added,
   modified, and removed path. The report is descriptive evidence, not a
   tamper-proof guarantee. If evolution reports no anchor, keep it missing and
   record the historical limitation; do not run `anchor` during validate to
   repair it. Creating one now does not recover build-start evidence.
   Do not tick an unperformed evolution report as completed. If no refresh is
   applicable because validation changed only `.agentic/`, state that condition
   explicitly; an absent historical anchor remains an independent limitation.
   Leave the evolution checklist item unchecked when no report was run. Record
   `not applicable: validation changed only .agentic/` in the Log when true;
   this explains the unchecked item without inventing completion. A strict-check
   note about a missing anchor is not an evolution report. If a required report
   cannot be obtained, keep that verification limitation unresolved or record
   an explicitly authorized disposition; do not tick the item to clear it.
   Missing historical anchor evidence does not itself show a current source or
   test flaw. Keep that limitation separate from the current proof and from a
   decision that an explicit policy actually requires; do not invent a repair
   task solely to remove the historical note.
9. **Prove the final candidate only after every candidate-changing step:**
    `python .agentic/aegis.py check --task TASK-<id> --strict --run`.
    This executes the configured full verification commands plus the advisory
    catalog. Schedule this once after edits and review, rather than once per
    stage. A failure or subsequent candidate change requires relevant review and
    fresh proof; the last proof must describe the tree handed to `deliver`.
    Do not run a separate full `test` immediately before this command. An earlier
    full run, a dry-run preview, or an unchanged fingerprint on a cancelled job
    cannot substitute for the required successful final verification.
    Reading source or test definitions is inspection, not a test pass. Report
    tests as passed only when an observed execution of those tests exited zero.
    `python .agentic/aegis.py check --task TASK-<id> --dry-run` lists what
    `--run` would execute and each command's limit without running any of it.
    Use it to find out what this proof costs *before* committing to it, not to
    replace it.
    **When you cannot run it, say so rather than skipping it.** A standing
    instruction that forbids the full suite, an environment that cannot execute
    it, or a limit you would exceed are all real constraints, and none of them
    lets you omit the proof silently or record one that did not happen.
    Substitute the narrowest proof that still covers the candidate, name what it
    does not cover, and state the substitution as a deviation notice under
    step 10. Steps 9 and 10 read together: this step says what the required
    proof is, and step 10 says what you owe when you advance without it.
10. Record one consolidated final validation result in the log: command, exit
    code, commands/tests run, and remaining warnings with their accepted
    reasons. Write that outcome once; if already recorded, continue to step 11.
    An accepted reason explains why the candidate remains adequately covered,
    with observed evidence; repeating a warning's trigger is not that reason.
    For unchanged tests, identify the existing cases that cover the restored
    behavior and boundaries. If the reason is not established, leave it unresolved.
    Repair Handoff or Stage report directly instead of appending the outcome
    again. Record an earlier failed gate only when it exposed a candidate
    problem, caused an implementation or test change, or remains an accepted
    limitation; omit corrected operational retries. Never write "green" over a
    non-zero exit. A failure introduced by this task returns to the
    appropriate earlier stage. A pre-existing base-branch failure is named and
    kept out of scope, with its effect on CI stated honestly. State it as a
    deviation notice when the candidate advances while accepting a relevant
    failure or warning, omitting or weakening required verification, or
    substituting materially weaker evidence. A tool-use error or failed command that is
    corrected and rerun successfully without affecting the candidate or proof
    is operational detail, not a deviation. Apply the material-impact rule in
   `.agentic/AGENTS.md` rather than turning every non-zero exit into a notice.
    Keep present execution separate from missing historical evidence. Do not
    create or offer to reconstruct a past red run or build-start anchor.
    A newly authorized run proves only the candidate actually executed now.
    List missing history as a limitation and any decision needed about it.
11. If step 2 returned the task to an earlier stage, keep that return header
    and synchronized current fields; do not apply this validate checkpoint.
    Otherwise, at a checkpoint or explicit stop, retain validate as header and
    current stage. Save Handoff `status: waiting`, Stage report `result: paused`,
    `needs_user: yes`; use blocked for an unresolved blocking decision.
    Name the pending decision in both next fields and only actual changes in
    changed. Use the task template's exact field values. If summary reports
    missing or malformed records, repair the snapshots and rerun it; do not
    author a replacement summary. Run summary after these edits and copy its
    output first in one
    code block, then explain the result and the `validate` Stage-boundary
    choices. Stop before transition, including in explicitly bounded autopilot.
    Report only edits made during this operation in `changed`; identify
    pre-existing candidate changes as inspected evidence instead. Present
    continuation only when its prerequisites hold. If proof failed or is
    missing, or a review decision blocks work, state that delivery is
    unavailable now and name the actual next action or pending decision.
    A proposed exception is not an accepted limitation; a deviation notice
    alone does not authorize weaker verification or clear a failed verdict.
    Choose one persisted next action or scoped question before presenting the
    checkpoint choices. When validation permits delivery and confirmation is
    pending, ask whether to start deliver for this validated candidate. Do not
    save a menu such as choosing delivery, corrections or pause in either next
    field. When a prerequisite is unresolved, next must address it first and
    Handoff blockers must name it; do not route around it to a later stage.
    A limited inspection or record update is not stage completion and does
    not call for a generic completion menu. Copy summary output without
    rewriting fields; only an immediate deviation notice may precede it.
    Include every output line, including Details and any truncation marker or
    instruction to read the full journal. If the snapshot is too long, read the
    full journal, shorten the saved fields without losing unresolved facts, then
    rerun summary. Never expand or replace truncated tool output from memory.
    After the user chooses to continue, or immediately in unrestricted
    autopilot, tick the checklist, set `stage: deliver`, and replace it with
    the delivery stage's "Done when" list. Before delivery work, read
    `.agentic/steps/6_deliver.md`.
    The task now means "validated, not yet published." If the user instead
    returns to Frame at this checkpoint, read `.agentic/steps/1_frame.md`
    before Frame work; other correction returns use the paths in step 2.

**Outputs:**

- Reviewed candidate with current requirements and component knowledge.
- Manual observations where required.
- Final suite and strict-check evidence in the journal log.
- Journal advanced to `stage: deliver` only after proof.

**Done when:**

- [ ] diff reviewed against scope, requirements, design, error paths,
      portability, security, and unrequested work
- [ ] affected component knowledge updated or created against the reviewed code
      and tests; touched legacy pages migrated before final review and proof
- [ ] `.agentic/context/project.md` and `.agentic/context/environment.md` reconciled with the
      candidate
- [ ] requirements re-read: status, prose, verification, paths, and links true
- [ ] manual or inspection verification completed and recorded where applicable
- [ ] final evolution report refreshed after the last candidate edit
- [ ] final `check --strict --run` result recorded truthfully after all edits
- [ ] remaining warnings and pre-existing failures explained
- [ ] `stage: deliver`

**Skip when:** Never, on either path. Quick path skips specification and design
when proportionate; it does not skip repository-wide proof.
