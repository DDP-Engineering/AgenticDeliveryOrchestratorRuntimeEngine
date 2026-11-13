# Job lifecycle

A job is the work ADORE does for one ticket, from pickup to a merged change. This article shows its stages and where you take part. Labels and eligibility are in [Tickets for automatic pickup](/help/tickets).


Confirm **Cancel** before submitting it. Cleanup attempts to remove the runtime and worktree, including unpublished work; resources can remain if cleanup fails. Job state and evidence remain. Deleting a job is a separate action.

## Stages {#stages}

ADORE runs the AEGIS stages one at a time, each attempt in a fresh executor session. Executors never push, open an MR/PR or merge.

| Stage | What happens |
|---|---|
| Frame | Scope is agreed and the executor records whether the job takes the full or the quick path. |
| Specify | The requirement is written. |
| Design | A short design note is written for non-trivial work. |
| Build | A failing test comes first, then the implementation, until the tests pass. |
| Validate | Review, the full test suite, a strict check and the AEGIS report; the AEGIS task closes. ADORE then repeats the strict check itself before it asks for approval. |

The quick path runs Frame, Build and Validate. After Validate the job shows the stage **Done** while it waits for approval, is published and is in human review. AEGIS may return to any earlier stage on the selected path, including Design to Specify. ADORE saves the stage and continues in a fresh session within the existing limits. A done task returns to Validate when fresh verification is needed. A stage gets three failed attempts by default (**Failed attempts allowed per stage**).

## Direct jobs {#direct-evidence}

The list and job page show **Workflow**: **AEGIS** or **Direct**, as recorded for that job. A direct job uses **Implementation** (`build`), **Validation** (`validate`), then **Done**. It has no Framing, Specification, Design or AEGIS task. The timeline shows only saved events, not assumed completed steps.

**Latest recorded attempt** is the last executor stage-launch attempt, not cumulative launches or failed attempts. Without a saved launch, the page shows **Attempt unavailable**. Independent verification shows the saved command before its result, **Duration (seconds)** and **Output tail** as literal redacted text. Empty output is explicit. Changing Settings does not replace the saved command or result.

| Result | Meaning |
|---|---|
| Passed | The command exited zero without timing out. |
| Failed | The command exited nonzero without timing out; the latest failure stays visible during a new implementation attempt. |
| Timed out | The command exceeded its time limit, regardless of exit code. |
| Not configured: unverified | No verification command was configured; this is not a pass. |
| Verification evidence unavailable | No verification outcome is recorded yet; this does not mean not configured. |

Direct implementation uses the **Implementation** `build` limit in `workflow.stage_timeout_overrides`; independent verification uses the **Validation** `validate` limit. Each falls back to the general `budgets.per_gate_timeout_seconds` when its override is unset. The other AEGIS stage limits do not apply to direct jobs.

## Clarification {#clarification}

When the executor needs information, ADORE posts a ticket comment, Clarification required for the stage, listing the questions, and sets `agent-clarify`. The job shows **Waiting for clarification**, and its detail offers **Answer on the ticket**.

Reply with a normal comment on the ticket, then add `agent-answered`. Both are needed; ADORE's own comments do not count. ADORE removes both labels and resumes. Questions do not count as failed attempts. **Maximum question rounds** (3 by default) limits how often a job may ask, and **Time allowed for a human answer** (72 hours by default) fails the job when it expires.

## Approval {#approval}

When AEGIS strict validation or configured direct verification passes (or direct verification is explicitly unconfigured), ADORE removes `agent-approved`, posts the evidence on the ticket and waits. The job shows **Waiting for approval** and the ticket keeps `agent-working`. The evidence names the exact candidate and any deviations the executor recorded.

Review it, then add `agent-approved` again; only a fresh addition counts. The approval is bound to that candidate and the target branch commit. If either changes, the approval is void and ADORE integrates, validates and asks again. This wait has no timer. The job detail offers **Review the candidate on the forge**.

## Publication and review {#review}

After approval ADORE pushes the branch and opens the MR/PR against the target branch, requests review from the accounts in **Request review from**, and sets `agent-mr`. **PR/MR state at publication** chooses Draft (default) or Ready for review. The job shows **Publishing** and then **Human review**. ADORE never merges. After a person merges, ADORE sets `agent-done`, the job shows **Completed**, and by default the remote branch is removed. An MR/PR closed without a merge fails the job.

To request changes, a reviewer adds `agent-revise` to the MR/PR. ADORE removes the label, starts new work on the same branch (a new task for AEGIS), and repeats validation and fresh approval before it pushes. **Maximum revision rounds** (5 by default) bounds this. A request beyond the limit fails the job.

If CI checks fail on the MR/PR, **Action when PR/MR CI checks fail** decides: Automatic repair (default) starts a revision, Notify only posts a comment, and Ignore skips CI status. Automatic repairs share the revision budget; once it is spent, ADORE posts a notice and the job stays in review.

## Failure and recovery {#failures}

When a stage fails, ADORE keeps one incident comment on the ticket up to date with the stage, attempt, error code, evidence and next action; when the agent exited without moving the stage on, the evidence also shows its last error-output lines. After the final attempt it posts a terminal comment, sets `agent-failed`, stops the container, keeps the worktree and frees the slot. Other causes are an expired answer time, a deleted source ticket and an exceeded limit such as cost or changed files. Closing the source ticket while a job waits cancels it.

In Jobs a failed job shows **Failed**, and its detail explains that recovery evidence is kept. **Retry** asks the worker to recover the job; it does not bypass validation or approval. In the Tickets view, Retry replaces Start. Removing `agent-failed` does not retry. **Cancel** appears for unfinished jobs and asks the worker to stop and clean up. Finished jobs cannot be cancelled. Administrators and assigned developers can use both. A queued command shows its progress, such as Command queued or Command completed. A failed or uncertain command also says why, when the engine names a reason, and shows the engine's last lines.

For local jobs, explicit **Retry** rechecks the installed executor and accepts an updated executable or inherited environment on the same computer and account. It keeps the task, worktree, branch, history and cumulative limits. Automatic monitoring does not do this. Changed execution settings or corrupt recovery evidence still need correction. If restarting fails, the command is marked failed and shows the saved cause, such as a missing executable, invalid version, command failure or timeout. No model request is sent by this version check; use **Test AI connection** for that.

When a container command exceeds its time limit, ADORE stops that container before another command can run. The next allowed attempt resumes the same container with its installed dependencies and files; network access stays unchanged. If safe stopping or restarting cannot be confirmed, the job fails and keeps its evidence for inspection before **Retry**. A failed preparation still needs its existing explicit recovery.

## Abandon and start again {#restart}

For a failed job, **Abandon and start again** discards its saved state, worktree including unpublished work, and unchanged owned remote branch. Review the warning and confirm. ADORE verifies ownership before cleanup and starts the same open ticket with current settings only after cleanup succeeds. Monitoring stays paused if already paused. Administrators and assigned developers can use this action.

Stable execution settings or backend drift cannot be fixed by Retry; Job details explains this and offers the confirmed action. Restore the saved settings to keep existing work. Native Retry can still revalidate volatile environment changes, including processor variables after resizing a VM.

Foreign resources, another computer/account, corrupt ownership evidence or a changed remote branch block recovery. Partial cleanup keeps remaining evidence and starts no new job. If the job changes after confirmation, refresh its details and review again. A CLI lock may belong to the web worker: pause monitoring in Project Summary and wait for the current bounded job. Do not remove a live lock file.

If an older deleted job left a branch without a recorded checkpoint, ADORE keeps that branch and uses a fresh generation. A known checkpoint that changed still blocks recovery. At most three alternative names are tried and repository naming rules must allow a free name; otherwise recovery stops before cleanup. The result explains when an older branch was kept.

## Following jobs {#following-jobs}

Use **Jobs** in the sidebar or a project's **Jobs** tab, then the **Jobs** sub-tab. The table has these columns:

| Column | Content |
|---|---|
| Ticket | Number and title; opens the job detail. |
| Project | The owning project. |
| Status | The state, recorded Workflow, current Stage, and a link to the ticket or MR/PR when a person must act. |
| Last activity | Time of the last saved event. |
| Consumption | Tokens used by the job. |

Click a column heading to sort. **Search jobs** matches titles, numbers, projects, job IDs, state, stage or outcome. The **Status** filter offers Active jobs, Waiting, Human review and Finished jobs. The page refreshes itself while visible.

Lists and open details update every 15 seconds while visible; Consumption updates every 30 seconds. Background reads keep rows, sort, filters, page size, page, open sections and your reading position. Use the separate **Refresh** controls for jobs, detail and Consumption. **Last refreshed** records a validated completion, not the start of a request.

After a connection failure or a 30-second read deadline, older validated information can remain with a stale notice and **Retry**. Stale job list or detail evidence cannot enable commands; a consumption failure alone does not block independently valid job actions. Invalid or denied evidence is hidden. A changed paging snapshot requires **Reload first page**, not a silent page reset. Open executor output is not fetched again by parent updates; a changed job evidence revision still clears its binding.

The detail shows **What is happening now**, **Who acts**, **Where** and **What follows**, then Consumption, a Timeline (Date, Event, Stage), **Evidence and artifacts** links and **Technical details**. The timeline lists only saved events. Old activity alone does not show that work stopped.

## Job budgets {#budgets}

Job details shows **Executor launches** (for example 9 / 20) and **Active work (seconds)** beside the current project limits, independently of token statistics. At 90% it warns that a limit is near; at the limit it asks you to raise it before resuming. The default launch limit is 20 in both enrollment and `adore init`.

Administrators can follow **Adjust budgets in project Settings**, open **Implementation**, edit only budgets, choose **Save** and confirm the exact values. A reviewed budget-only save is allowed while jobs wait for clarification, with no running conductor or unfinished operation. Other settings keep their usual idle and pause checks; developers have read-only settings.

Budgets are reread before each attempt, including resume and retry. A running attempt keeps its timeout. Active work is cumulative across retries, clarification answers and revisions; waiting time is excluded. Raising a limit preserves consumed work, the task and saved progress. A failed exhausted job still needs **Retry** after adjustment. Invalid or missing configuration stops further attempts until corrected.

If current limits cannot be read, the detail keeps saved consumption, evidence and recovery controls visible. Limits show — with an explicit unavailable notice; no default is guessed. Correct the project configuration before running again.

## Status and executor evidence {#operational-evidence}

**Working** means ADORE is conducting the saved stage; no human action is currently requested. **Waiting for clarification** needs an answer on the ticket. **Failed** stops autonomous work and keeps recovery evidence. The status card shows failed attempts in the current stage even while the job stays Working.

Questions render as Markdown with lists, tables and code. HTML remains literal, unsafe links are inactive and images do not load automatically. Wide tables and code scroll inside the question.

Timeline stages come from each event's recorded stage, stage context or transition destination; unrelated events remain unknown. Job times include seconds. An event is saved evidence, not a live progress signal.

Under **Evidence and artifacts**, choose **View latest executor output**. This shows host-captured operational stdout/stderr for the latest recorded completed launch, including missing modules and test totals. Prompts, reasoning, scripts, configuration, paths, credentials and financial content are withheld. Unrecognized output is replaced by a notice or diagnostic category. Only the last 500 diagnostic records per stream, within 64 KiB, are kept.

A launch without proven capture, or a deleted snapshot, is explicitly unavailable; raw archives are never used as a fallback. Corrupt evidence is refused. Existing jobs can remain unavailable until a later executor launch records evidence; this view never starts one.

If **Consumption** cannot load, use **Refresh consumption** beside the error. Job evidence and recovery controls remain separate. A corrupt source still requires operator investigation.
