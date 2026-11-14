# Job lifecycle

A job is the work ADORE does for one ticket, from pickup to a merged change. This article shows its stages and where you take part. Labels and eligibility are in [Tickets for automatic pickup](/help/tickets).


Confirm **Cancel** before submitting it. Cleanup attempts to remove the runtime and worktree, including unpublished work; resources can remain if cleanup fails. Job state and evidence remain. Deleting a job is a separate action.

Open **Job actions**, beside the current stage, for **Retry**, **Cancel** or the confirmed fresh-run recovery when available. Only commands allowed for this job are shown.

Start is confirmed after the job is durably admitted and taken by the worker. The job then has its own progress and outcome. A queued or running command alone does not confirm admission. Cancel is confirmed only after the job has stopped with a saved cancellation result. Queueing the request or sending a stop signal does not confirm cancellation. If the result is uncertain, inspect the job before retrying.

Each project has one concurrent-job limit, shared by Start, Retry, fresh restarts and resumed work. Pausing monitoring stops automatic pickup and keeps explicit Start available. Lowering the limit leaves existing jobs running. Queued commands and settled clarification, approval or review waits use no executor; initialization and cleanup keep their place until safe release. Waiting before execution does not consume active work.

Concurrent jobs have separate working folders, execution resources, credentials and output. Cancelling one leaves the others running. Brief shared updates may wait; agents with ready resources continue.

Projects progress independently. With a limit of two, two jobs can execute together while the next Start waits for a place. Stopping the application stops its workers and jobs; uncertain interrupted work requires inspection before an explicit Retry.

After a lower job limit, admitted jobs that have not started wait for a place under the new limit. Jobs already executing continue, even above the lower limit, and cleanup keeps its place until safe release. Settings in another project and server administration remain available.

## Stages {#stages}

ADORE runs the AEGIS stages one at a time, each attempt in a fresh executor session. Executors never push, open an MR/PR or merge.

| Stage | What happens |
|---|---|
| Frame | Scope is agreed and the executor records whether the job takes the full or the quick path. |
| Specify | The requirement is written. |
| Design | A short design note is written for non-trivial work. |
| Build | The agent implements the ticket and selects suitable checks according to the repository instructions. |
| Validate | The agent reports checks according to the repository instructions, including CI-only checks not run locally, and closes the AEGIS task. ADORE observes completion without rerunning tests. |

The quick path runs Frame, Build and Validate. After Validate the job shows the stage **Done** while it waits for approval, is published and is in human review. AEGIS may return to any earlier stage on the selected path, including Design to Specify. ADORE saves the stage and continues in a fresh session within the existing limits. A done task returns to Validate when fresh verification is needed. A stage gets three failed attempts by default (**Failed attempts allowed per stage**).

## Direct jobs {#direct-evidence}

The list and job page show **Workflow**: **AEGIS** or **Direct**, as recorded for that job. A direct job uses **Implementation** (`build`), **Validation** (`validate`), then **Done**. It has no Framing, Specification, Design or AEGIS task. The timeline shows only saved events, not assumed completed steps.

**Latest recorded attempt** shows the last recorded agent launch. Without one, the page shows **Attempt unavailable**. Tests and checks are reported by the agent; ADORE does not execute them independently.

Direct **Implementation** uses the `build` override in `workflow.stage_timeout_overrides`, falling back to `budgets.per_gate_timeout_seconds`. **Validation** (`validate`) records the candidate for approval without running a separate test command.

## Clarification {#clarification}

When the executor needs information, ADORE posts a ticket comment, Clarification required for the stage, listing the questions, and sets `agent-clarify`. The job shows **Waiting for clarification**, and its detail offers **Answer on the ticket**. Choose **Read the question** to open **Agent question**, then **Answer on the ticket** when a saved location is available.

Reply with a normal comment on the ticket, then add `agent-answered`. Both are needed; ADORE's own comments do not count. ADORE removes both labels and resumes. Questions do not count as failed attempts. **Maximum question rounds** (3 by default) limits how often a job may ask, and **Time allowed for a human answer** (72 hours by default) fails the job when it expires.

## Approval {#approval}

Human approval before publication is enabled by default. Administrators can change **Require human approval before PR/MR** in Settings. When disabled, ADORE checks candidate and target freshness before publishing; repository tests remain the agent’s responsibility.

When the agent completes its workflow, ADORE records the candidate, removes the old approval label and asks for fresh human approval. Checks shown in the task journal are agent-reported.

Review it, then add `agent-approved` again; only a fresh addition counts. The approval is bound to that candidate and the target branch commit. If either changes, the approval is void and ADORE integrates, validates and asks again. This wait has no timer. The job detail offers **Review the candidate on the forge**.

When disabled, ADORE checks the validated candidate and target and publishes without waiting for a label. ADORE never merges.

## Publication and review {#review}

After validation and any required approval, ADORE pushes the branch and opens the MR/PR against the target branch, requests review from the accounts in **Request review from**, and sets `agent-mr`. **PR/MR state at publication** chooses Draft (default) or Ready for review. The job shows **Publishing** and then **Human review**. ADORE never merges. After a person merges, ADORE sets `agent-done`, the job shows **Completed**, and by default the remote branch is removed. An MR/PR closed without a merge fails the job.

To request changes, a reviewer adds `agent-revise` to the MR/PR. ADORE removes the label, starts new work on the same branch (a new task for AEGIS), and repeats validation and fresh approval before it pushes. **Maximum revision rounds** (5 by default) bounds this. A request beyond the limit fails the job.

If CI checks fail on the MR/PR, **Action when PR/MR CI checks fail** decides: Automatic repair (default) starts a revision, Notify only posts a comment, and Ignore skips CI status. Automatic repairs share the revision budget; once it is spent, ADORE posts a notice and the job stays in review.

## Failure and recovery {#failures}

When a stage fails, ADORE keeps one incident comment on the ticket up to date with the stage, attempt, error code, evidence and next action; when the agent exited without moving the stage on, the evidence also shows its last error-output lines. After the final attempt it posts a terminal comment, sets `agent-failed`, stops the container, keeps the worktree and frees the slot. Other causes are an expired answer time, a deleted source ticket and an exceeded limit such as cost or changed files. Closing the source ticket while a job waits cancels it.

In Jobs a failed job shows **Failed**, and its detail explains that recovery evidence is kept. **Retry** asks the worker to recover the job; it does not bypass validation or any required approval. In the Tickets view, Retry replaces Start. Removing `agent-failed` does not retry. **Cancel** appears for unfinished jobs and asks the worker to stop and clean up. Finished jobs cannot be cancelled. Administrators and assigned developers can use both. A queued command shows its progress, such as Command queued or Command completed. A failed or uncertain command also says why, when the engine names a reason, and shows the engine's last lines.

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

The detail replaces the job list while open. Its compact heading combines the ticket number and title. **What is happening now** shows the state, who acts and **Next step**. Budgets and Consumption sit beside it on wide screens and below it on narrow screens. **Activity** lists saved events newest first. **Agent question** holds the active clarification; other states show **Evidence and artifacts**. **Technical details** holds identifiers, executor output and expandable **Original recorded events**. **Close** returns to the list with its filters. Old events do not become current action requests.

## Job budgets {#budgets}

Job details shows **Executor launches** (for example 9 / 20) and **Active work (seconds)** beside the current project limits, independently of token statistics. At 90% it warns that a limit is near; at the limit it asks you to raise it before resuming. The default launch limit is 20 in both enrollment and `adore init`.

Administrators can follow **Adjust budgets in project Settings**, open **Implementation**, edit only budgets, choose **Save** and confirm the exact values. A reviewed budget-only save is allowed while jobs wait for clarification, with no running conductor or unfinished operation. Other settings keep their usual idle and pause checks; developers have read-only settings.

Budgets are reread before each attempt, including resume and retry. A running attempt keeps its timeout. Active work is cumulative across retries, clarification answers and revisions; waiting time is excluded. Raising a limit preserves consumed work, the task and saved progress. A failed exhausted job still needs **Retry** after adjustment. Invalid or missing configuration stops further attempts until corrected.

If current limits cannot be read, the detail keeps saved consumption, evidence and recovery controls visible. Limits show — with an explicit unavailable notice; no default is guessed. Correct the project configuration before running again.

## Status and executor evidence {#operational-evidence}

**Working** means ADORE is conducting the saved stage; no human action is currently requested. **Waiting for clarification** needs an answer on the ticket. **Failed** stops autonomous work and keeps recovery evidence. The status card shows failed attempts in the current stage even while the job stays Working.

Questions appear in **Agent question** as Markdown with lists, tables and code. Leading HTML comments are omitted in the readable view; **Original question and evidence** retains the exact source. Other HTML remains literal, unsafe links are inactive and images do not load automatically. Wide tables and code scroll inside the question.

Timeline stages come from each event's recorded stage, stage context or transition destination; unrelated events remain unknown. Job times include seconds. An event is saved evidence, not a live progress signal.

Under **Technical details**, choose **View latest executor output**. This shows host-captured operational stdout/stderr for the latest recorded completed launch, including missing modules and test totals. Prompts, reasoning, scripts, configuration, paths, credentials and financial content are withheld. Unrecognized output is replaced by a notice or diagnostic category. Only the last 500 diagnostic records per stream, within 64 KiB, are kept.

The summary shows the attempt, recorded time, result and exit code. Expand **stdout** or **stderr** when records are present. If a launch is in progress, the panel identifies it and keeps the latest completed output. When the journal changes during a read, choose **Retry**. The last verified output is marked as possibly out of date.

A launch without proven capture, or a deleted snapshot, is explicitly unavailable; raw archives are never used as a fallback. Corrupt evidence is refused. Existing jobs can remain unavailable until a later executor launch records evidence; this view never starts one.

If **Consumption** cannot load, use **Refresh consumption** beside the error. Job evidence and recovery controls remain separate. A corrupt source still requires operator investigation.


## Project capacity {#project-capacity}

**Summary** shows only **Parallel job limit**, **Free** and **Queued jobs** as compact rectangles alongside the project’s operational facts. In the project or global **Jobs** page, choose **Capacity** beside **Tickets** and **Jobs**. Each project has one table row with its limit, free places, queue, monitoring and current job states. Finished jobs, operation history and logs are excluded. Choose 10, 25, 50 or All in **Rows per page** and use **Previous** and **Next**.

The queue counts submitted requests and admitted jobs waiting for dispatch, not unrequested forge tickets. A project at capacity does not block other projects. Settings still shows **Your latest operations** with saved Start, Retry, Cancel and settings results; Queued and In progress do not mean Confirmed.

A staged lower limit already stops new starts and resumptions until occupancy falls below it; already-running jobs continue; queued reservations wait for a current execution place. It never raises the active limit. Safe application still waits for unfinished work; the saved value and staged candidate remain visible until Save or Discard changes.
