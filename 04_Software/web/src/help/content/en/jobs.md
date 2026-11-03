# Job lifecycle

A job is the work ADORE does for one ticket, from pickup to a merged change. This article shows its stages and where you take part. Labels and eligibility are in [Tickets for automatic pickup](/help/tickets).

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

## Clarification {#clarification}

When the executor needs information, ADORE posts a ticket comment, Clarification required for the stage, listing the questions, and sets `agent-clarify`. The job shows **Waiting for clarification**, and its detail offers **Answer on the ticket**.

Reply with a normal comment on the ticket, then add `agent-answered`. Both are needed; ADORE's own comments do not count. ADORE removes both labels and resumes. Questions do not count as failed attempts. **Maximum question rounds** (3 by default) limits how often a job may ask, and **Time allowed for a human answer** (72 hours by default) fails the job when it expires.

## Approval {#approval}

When strict validation passes, ADORE removes `agent-approved`, posts the evidence on the ticket and waits. The job shows **Waiting for approval** and the ticket keeps `agent-working`. The evidence names the exact candidate and any deviations the executor recorded.

Review it, then add `agent-approved` again; only a fresh addition counts. The approval is bound to that candidate and the target branch commit. If either changes, the approval is void and ADORE integrates, validates and asks again. This wait has no timer. The job detail offers **Review the candidate on the forge**.

## Publication and review {#review}

After approval ADORE pushes the branch and opens the MR/PR against the target branch, requests review from the accounts in **Request review from**, and sets `agent-mr`. **PR/MR state at publication** chooses Draft (default) or Ready for review. The job shows **Publishing** and then **Human review**. ADORE never merges. After a person merges, ADORE sets `agent-done`, the job shows **Completed**, and by default the remote branch is removed. An MR/PR closed without a merge fails the job.

To request changes, a reviewer adds `agent-revise` to the MR/PR. ADORE removes the label, starts a new task on the same branch, and repeats validation and fresh approval before it pushes. **Maximum revision rounds** (5 by default) bounds this. A request beyond the limit fails the job.

If CI checks fail on the MR/PR, **Action when PR/MR CI checks fail** decides: Automatic repair (default) starts a revision, Notify only posts a comment, and Ignore skips CI status. Automatic repairs share the revision budget; once it is spent, ADORE posts a notice and the job stays in review.

## Failure and recovery {#failures}

When a stage fails, ADORE keeps one incident comment on the ticket up to date with the stage, attempt, error code, evidence and next action; when the agent exited without moving the stage on, the evidence also shows its last error-output lines. After the final attempt it posts a terminal comment, sets `agent-failed`, stops the container, keeps the worktree and frees the slot. Other causes are an expired answer time, a deleted source ticket and an exceeded limit such as cost or changed files. Closing the source ticket while a job waits cancels it.

In Jobs a failed job shows **Failed**, and its detail explains that recovery evidence is kept. **Retry** asks the worker to recover the job; it does not bypass validation or approval. In the Tickets view, Retry replaces Start. Removing `agent-failed` does not retry. **Cancel** appears for unfinished jobs and asks the worker to stop and clean up. Finished jobs cannot be cancelled. Administrators and assigned developers can use both. A queued command shows its progress, such as Command queued or Command completed. A failed or uncertain command also says why, when the engine names a reason, and shows the engine's last lines.

For local jobs, explicit **Retry** rechecks the installed executor and accepts an updated executable or inherited environment on the same computer and account. It keeps the task, worktree, branch, history and cumulative limits. Automatic monitoring does not do this. Changed execution settings or corrupt recovery evidence still need correction. If restarting fails, the command is marked failed and shows the saved cause, such as a missing executable, invalid version, command failure or timeout. No model request is sent by this version check; use **Test AI connection** for that.

When a container command exceeds its time limit, ADORE stops that container before another command can run. The next allowed attempt resumes the same container with its installed dependencies and files; network access stays unchanged. If safe stopping or restarting cannot be confirmed, the job fails and keeps its evidence for inspection before **Retry**. A failed preparation still needs its existing explicit recovery.

## Following jobs {#following-jobs}

Use **Jobs** in the sidebar or a project's **Jobs** tab, then the **Jobs** sub-tab. The table has these columns:

| Column | Content |
|---|---|
| Ticket | Number and title; opens the job detail. |
| Project | The owning project. |
| Status | The state, the current Stage, and a link to the ticket or MR/PR when a person must act. |
| Last activity | Time of the last saved event. |
| Consumption | Tokens used by the job. |

Click a column heading to sort. **Search jobs** matches titles, numbers, projects, job IDs, state, stage or outcome. The **Status** filter offers Active jobs, Waiting, Human review and Finished jobs. The page refreshes itself while visible.

The detail shows **What is happening now**, **Who acts**, **Where** and **What follows**, then Consumption, a Timeline (Date, Event, Stage), **Evidence and artifacts** links and **Technical details**. The timeline lists only saved events. Old activity alone does not show that work stopped.
