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

The quick path runs Frame, Build and Validate. After Validate the job shows the stage **Done** while it waits for approval, is published and is in human review. AEGIS may return to any earlier stage on the selected path, including Design to Specify. ADORE saves the stage and continues in the same job conversation within the existing limits. A done task returns to Validate when fresh verification is needed. A stage gets three failed attempts by default (**Failed attempts allowed per stage**).

## Direct jobs {#direct-evidence}

The list and job page show **Workflow**: **AEGIS** or **Direct**, as recorded for that job. A direct job uses **Implementation** (`build`), **Validation** (`validate`), then **Done**. It has no Framing, Specification, Design or AEGIS task. The timeline shows only saved events, not assumed completed steps.

**Latest recorded attempt** shows the last recorded agent launch. Without one, the page shows **Attempt unavailable**. Tests and checks are reported by the agent; ADORE does not execute them independently.

Direct **Implementation** uses the `build` override in `workflow.stage_timeout_overrides`, falling back to `budgets.per_gate_timeout_seconds`. **Validation** (`validate`) records the candidate for approval without running a separate test command.

## Clarification {#clarification}

When the executor needs information, ADORE posts a ticket comment, Clarification required for the stage, listing the questions, and sets `agent-clarify`. The job shows **Waiting for clarification**. **Read the question** opens the question in **Job details**; **Answer on the ticket** uses its saved location.

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

Container jobs keep the image and resource selected when they start, even without preparation. If that resource is replaced, start a fresh job. Preparation remains optional.

## Abandon and start again {#restart}

For a failed job, **Abandon and restart with AEGIS** or **Abandon and restart without AEGIS** discards its saved state, worktree including unpublished work, and unchanged owned remote branch. Review the warning and confirm. ADORE verifies ownership before cleanup and starts the same open ticket with current settings only after cleanup succeeds. Monitoring stays paused if already paused. Administrators and assigned developers can use this action.

Stable execution settings or backend drift cannot be fixed by Retry; Job details explains this and offers the confirmed action. Restore the saved settings to keep existing work. Native Retry can still revalidate volatile environment changes, including processor variables after resizing a VM.

Foreign resources, another computer/account, corrupt ownership evidence or a changed remote branch block recovery. Partial cleanup keeps remaining evidence and starts no new job. If the job changes after confirmation, refresh its details and review again. A CLI lock may belong to the web worker: pause monitoring in Project Summary and wait for the current bounded job. Do not remove a live lock file.

If an older deleted job left a branch without a recorded checkpoint, ADORE keeps that branch and uses a fresh generation. A known checkpoint that changed still blocks recovery. At most three alternative names are tried and repository naming rules must allow a free name; otherwise recovery stops before cleanup. The result explains when an older branch was kept.

## Following jobs {#following-jobs}

Use **Jobs** in the sidebar or the project’s separate **Jobs** tab. The table has these columns:

| Column | Content |
|---|---|
| Ticket | Number and title; opens the job detail. |
| Project | The owning project. |
| Status | The state, recorded Workflow, current Stage, and a link to the ticket or MR/PR when a person must act. |
| Last activity | Time of the last saved event. |
| Consumption | Tokens used by the job. |

Click a column heading to sort. **Search jobs** matches titles, numbers, projects, job IDs, state, stage or outcome. The **Status** filter offers Active jobs, Waiting, Human review and Finished jobs. The page refreshes itself while visible.

The detail replaces its originating list while open. Above the title are **Activity**, **Agent sessions** and **Job details**, with **Show ticket** and **Close** on the right. Saved status, stage and workflow appear below the title. Budgets and consumption occupy the right-hand column. Required question, approval and review actions stay visible. **Close** restores the originating view, scope, search, filters and pagination.

**Activity** is a paginated table with time, activity, stage and session. Choose 10, 25, 50 or All rows and use Previous/Next. **Open conversation** opens the exact session when the stage and attempt identify one recorded launch; unrelated or ambiguous events have no link. Returning to Activity keeps its page. Job budgets and Consumption occupy the right-hand column, below the content on narrow screens.

## Agent session history {#agent-sessions}

**Agent sessions** opens the current session, or the latest completed session. The conversation shows the initial prompt, agent replies, user messages and expandable tool calls/results. Agent replies use readable Markdown. Messages appear inline with a single author label; reasoning and tools can be expanded. Usage remains in the right-hand Consumption panel.

Pi keeps one implementation conversation for the job across stages, continuations and corrections. Processes can restart at checkpoints; the conversation resumes with its context and Pi's automatic compaction. The selector still shows recorded attempts, with only each attempt's new activity and usage. Independent reviews use separate contexts when the repository's review policy requires them.

Session, its selector and the live activity indicator share a row directly above the conversation, aligned with its width. The conversation fits the available screen height and scrolls internally as messages arrive. Send now and Queue message sit beside the message box on wide screens, below it on narrow screens.

History loads progressively without shortening retained message text. New messages follow automatically only while you are at the bottom; use **New messages** to return after reading earlier messages. The session selector keeps other attempts available, and **Current session** returns to live work.

New launches explicitly retain their outgoing prompts and message times. Earlier sessions show only what was recorded. Administrators and assigned developers retain the same access; structured costs remain administrator-only.

Use **Maximize** to fill the page with Agent sessions. **Restore** or Escape returns to the normal view. The selected session, messages and unsent draft are preserved.

### Sending instructions {#instructions}

Enter a **Message to the agent** at the bottom of the current conversation. **Send now** submits it at the next safe agent boundary; **Queue message** waits until current work finishes. Between sessions, Queue message remains available while the job is working. Historical conversations are read-only.

Your message appears in the conversation with **Queued**, **Received by agent** or a failure status. Received confirms receipt, not completed work. Invalid input is explained only when sending: 1–4000 characters without NUL, with at most 256 retained instructions per job.

Unacknowledged instructions remain queued for a later session. Acknowledged delivery is saved in the job and posted to the ticket; temporary comment failures retry independently.

## Job budgets {#budgets}

Job details shows **Executor launches** (for example 9 / 20) and **Active work (seconds)** beside the current project limits, independently of token statistics. At 90% it warns that a limit is near; at the limit it asks you to raise it before resuming. The default launch limit is 20 in both enrollment and `adore init`.

Administrators can follow **Adjust budgets in project Settings**, open **Implementation**, edit only budgets, choose **Save** and confirm the exact values. A reviewed budget-only save is allowed while jobs wait for clarification, with no running conductor or unfinished operation. Other settings keep their usual idle and pause checks; developers have read-only settings.

Budgets are reread before each attempt, including resume and retry. A running attempt keeps its timeout. Active work is cumulative across retries, clarification answers and revisions; waiting time is excluded. Raising a limit preserves consumed work, the task and saved progress. A failed exhausted job still needs **Retry** after adjustment. Invalid or missing configuration stops further attempts until corrected.

If current limits cannot be read, the detail keeps saved consumption, evidence and recovery controls visible. Limits show — with an explicit unavailable notice; no default is guessed. Correct the project configuration before running again.

## Job details and diagnostic {#operational-evidence}

**Job details** shows the saved result once, the recorded **Branch**, the **Last published commit** when available, the MR/PR link and **Review rounds** separately. A missing branch is shown as **Not recorded**. A published commit identifies the last verified pushed checkpoint, not a candidate fingerprint.

When clarification is required, **Read the question** opens this tab. The question uses readable Markdown, with unsafe links inactive and images not loaded automatically. **Answer on the ticket**, approval and review actions remain visible near the status when needed. The original question is available inside **Diagnostic**.

**Diagnostic** starts collapsed. Open it for internal project/job IDs, **Failed attempts in current stage**, direct-attempt or preparation evidence, and **View latest executor output**. Review rounds are separate from current-stage failures.

**Unavailable data** names missing ticket, activity history, title or last activity time only when relevant sources are absent. This describes available evidence, not token usage. Consumption remains in the right-hand panel.

**View latest executor output** reads normalized operational stdout/stderr for the latest recorded launch, with its time, attempt, stage and exit code. Private content is withheld; at most 500 diagnostic records within 64 KiB per stream are retained. Missing or corrupt evidence is reported explicitly, and changing evidence offers Retry.

**Activity** is the single event table. Published code is accessible through the MR/PR link. Job details uses saved evidence and does not create files or start an executor.

## Project capacity {#project-capacity}

**Summary** shows **Parallel job limit**, **Free** and **Queued jobs** beside the project’s operational facts. Project Jobs and Tickets are separate top-level tabs and have no Capacity sub-tab. The global Jobs page retains its Capacity table with per-project limits, free places, queue and monitoring; use its existing pagination.

The queue counts submitted requests and admitted jobs waiting for dispatch, not unrequested forge tickets. A project at capacity does not block other projects. Settings still shows **Your latest operations** with saved Start, Retry, Cancel and settings results; Queued and In progress do not mean Confirmed.

A staged lower limit already stops new starts and resumptions until occupancy falls below it; already-running jobs continue; queued reservations wait for a current execution place. It never raises the active limit. Safe application still waits for unfinished work; the saved value and staged candidate remain visible until Save or Discard changes.

## Choose the workflow {#workflow-choice}

In **Job actions**, choose **Abandon and restart with AEGIS** or **Abandon and restart without AEGIS** for a fresh job, then accept the short browser confirmation that discards existing work. Missing AEGIS disables its action. Tickets keeps its **Workflow** selector before **Start**. **Retry**, continuation and review corrections retain the saved workflow and the same Pi conversation.
