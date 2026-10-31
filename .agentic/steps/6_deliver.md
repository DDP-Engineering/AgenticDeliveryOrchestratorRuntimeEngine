<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage 6 - deliver

**Purpose:** Present, report, commit, and publish a validated candidate without
changing what was proved.

**Before the first delivery response:** decide candidate identity, save the
corresponding journal records, reread them, run summary, then present. Journal
records are allowed here; they are distinct from editing the validated source,
tests, requirements, specs or knowledge. Use the available record-edit tool
within its declared scope, even when the shell is read-only. Report an actual
permission refusal if encountered; do not infer one from another tool's mode.

**Read first:**

- The task journal `.agentic/tasks/TASK-<id>.md`, whole file, especially the
  latest validation evidence.
- The final diff and repository status.

**Reporting and resume:** Follow `.agentic/AGENTS.md` sections "Resume a task",
"Rulings and handoffs", and "Stage reporting". At transitions and pauses,
update the current checklist, minimal Handoff and Stage report, then show
`summary TASK-<id>`. Read required durable evidence; missing or shortened
context requires review. This adds no approval stop and never defers a material
deviation notice. Reuse unchanged instructions already read in this session -
**except this step file.** If you read it before `validate` began, read it again
now. Delivery is the one stage that publishes, and it is reached with the least
context left; its rules are not safe to work from memory.

**Steps:**

1. Inspect the current candidate and the recorded final proof. Use the same
   candidate-binding method and scope for both observations. Decide once:

   | Observation | Decision |
   |---|---|
   | Current binding equals the recorded validated binding | Candidate unchanged within that binding's scope; continue to step 2. |
   | Bindings differ, or an independently observed relevant edit occurred after proof | Return records to Validate below. |
   | No comparable binding or other sufficient identity evidence | Record exactly what identity evidence is unavailable; pause without asserting either equality or a post-proof edit. |

   A matching binding covers its included tracked and untracked files. A diff
   from the task base describes the proposed change set, not changes since
   validation; it cannot contradict the match by itself. If the binding excludes
   a relevant path, inspect that path separately and state the actual limit.
   Do not edit the candidate or rerun proof to resolve this delivery inspection.

   For a return to Validate, read
   `.agentic/steps/5_validate.md`, save `stage: validate`, replace the checklist
   with its complete "Done when" list and append the reason once. Refresh
   Handoff and Stage report with `current: validate` and the concrete next
   revalidation action. At a requested stop, save waiting/paused and
   `needs_user: yes`. Clear stale enabled-review verdicts while retaining the
   consumed round; disabled verdicts remain `disabled`. Reread the saved
   sections, run `summary TASK-<id>` and show its actual output. A response
   proposing this return does not save it. This is a journal-only update, not
   code repair or revalidation. Stop without publishing or running
   verification outside the user's requested scope.
2. When explicit review is enabled, confirm both current bound verdicts are
   `approved` for this unchanged candidate. Blank, malformed, stale,
   `disabled`, or `changes_required` evidence uses the same saved return. When
   explicit review is disabled, rely on the existing validation evidence and
   checkpoint; disabled review never skips them.
3. Keep the journal log append-only. Journal-only delivery records are
   expected here. Insert the new entry at the next section heading using the
   task template's append method; do not include old evidence lines in the
   replacement. Compare the saved historical Log prefix with the original,
   including whitespace, and restore any difference before summary. Updating
   Handoff or Stage report does not authorize normalizing earlier evidence.
4. **Save the approval pause before presenting**, in both interaction modes.
   Keep `stage: deliver` and its checklist; mark only observed completed items.
   Save Handoff `current: deliver`, `status: waiting`, and the concrete delivery
   decision in `next`. Save Stage report `stage: deliver`, `result: paused`,
   `current: deliver`, `needs_user: yes`, actual changed/evidence/issues and the
   same pending decision. Reread, run `summary TASK-<id>` and copy its actual
   output in a text fence as the first response block.

   Then present validation commands and
   results, accepted warnings and pre-existing failures, the exact diff
   summary, child status and integrated parent evidence when children are
   visible, what will be committed, exclusions, and the intended outcome.
   Present the `deliver` Stage-boundary choices from `.agentic/AGENTS.md` and
   wait for the human's choice. Keep approval unavailable if identity or proof
   is unresolved; a human approval cannot make missing proof current.
    Any deviation notices you gave along the
   way were notifications, not approvals: notices supplement this
   presentation and never shorten it, so repeat every deviation here even
   where you already said it, and state it as a deviation notice if this
   stage turns up a new one.
5. After approval, tick every checklist item except close-out, keep
   `stage: deliver`, log the decision, and run
   `python .agentic/aegis.py report TASK-<id>`. Read the appended report.
   Its check counts are a fresh report-time advisory snapshot, not a
   replacement for the validation evidence. Correct journal-only mistakes;
   any candidate correction returns to `validate` and requires new proof.
6. Deliver the approved outcome:
   - **Commit** on the task branch, with requirement IDs in the message.
   - **PR** by default. If CI runs `check --strict --run`, it decides merge.
   - Release or deployment beyond the PR requires the repository's separate
     process, explicit approval, and post-release verification.
   - With no remote, stop after the commit and report that no PR was opened.
     With no Git, stop after presentation and report that delivery is
     unavailable in this environment.
7. Close out only after the approved outcome succeeds - but let the outcome
   decide how many commits that takes:
   - **The outcome can still fail after the delivery commit** (a push, a PR, a
     release, a deployment): commit the delivery, wait for the outcome, then
     set `stage: done`, tick close-out, append one truthful log line, and make
     a small close-out commit pushed to the same PR. Only a later commit can
     report truthfully on something that had not happened yet.
   - **The outcome is the delivery commit itself** — a repository-local commit
     with no push, PR, release, or deployment — then nothing can fail after it,
     so close out *before* committing: set `stage: done`, tick close-out,
     append the log line, and let the same commit carry them. A second commit
     here records nothing that the first did not already prove.
   If delivery fails, record the failure and leave `stage: deliver` so `status`
   continues to show open work.

**Outputs:**

- Human-approved delivery decision in the journal.
- Report-time advisory snapshot appended to the journal.
- Delivery commit and the agreed outcome, normally a PR.
- A close-out commit once that outcome succeeds, or a single commit carrying
  the close-out where the commit is itself the whole outcome and so cannot
  fail after it.

**Done when:**

- [ ] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

**Skip when:** Never. Validation proves the candidate; delivery records and
publishes the approved result.
