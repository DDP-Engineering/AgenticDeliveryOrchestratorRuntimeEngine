# Tickets for automatic pickup

ADORE picks up tickets from your forge repository (GitHub, GitLab or Gitea) when they carry the right labels, and you can also start one by hand. This article covers labels, eligibility and the Tickets view.

## How pickup works {#how-pickup-works}

Each project has a **Monitoring** state, shown as **Active** or **Paused** in the Projects table and on the project's Summary tab. While monitoring is Active, ADORE checks the repository for ready tickets at a regular interval (60 seconds by default; see **Ticket check interval (seconds)** in [Project settings](/help/settings)). It takes the eligible ticket with the highest priority first (P1, then P2, then P3), then the lowest number, and advances one job at a time.

An administrator can use **Pause monitoring** and **Activate monitoring** on the project's Summary tab. Paused monitoring stops new pickups; running jobs continue.

## Create the labels first {#labels}

GitHub and Gitea reject an unknown label name, so a missing label makes status updates fail. All labels below must exist in the forge repository before the first run. ADORE creates the missing ones when you add a project (**Create the ADORE labels in the repository**, ticked by default in Review and create) or when you press **Create missing labels** in Settings → Repository; it never changes or deletes existing labels, and lists what it created, what already existed and what failed (for example when the server's forge account may not create labels). The names are defaults; rename one only together with its project setting.

| Label | Purpose |
|---|---|
| `agent-ready` | You add it to offer a ticket for pickup. ADORE replaces it with the working label when the job starts. |
| `agent-working` | ADORE sets it while it works, publishes and waits for your approval. |
| `agent-clarify` | ADORE sets it when it has asked a question and waits for an answer. |
| `agent-answered` | You add it after replying to a question. |
| `agent-mr` | ADORE sets it after publishing the MR/PR, while it waits for human review. |
| `agent-failed` | ADORE sets it when a job fails. |
| `agent-done` | ADORE sets it after a person has merged the MR/PR. |
| `agent-approved` | You add it on the ticket to approve publishing the presented candidate. |
| `agent-revise` | A reviewer adds it on the MR/PR to request a revision round. |

ADORE removes the lifecycle labels it is not applying on every status update, so all must exist. Adding a status label by hand does not change the job.

## What makes a ticket eligible {#eligible-tickets}

A ticket is picked up only when every rule holds. They are checked in this order:

1. The ticket is open.
2. It has the ready label (`agent-ready`).
3. It does not have the hold label (`agent-hold`). Removing the hold label makes the ticket eligible again.
4. It does not have the exclusion label (`no-agent`, setting **Exclude from pickup label**). It wins over the ready label. Removing it restores eligibility; adding it does not stop a job already started.
5. ADORE has no job for the ticket yet.
6. It has a priority label: `P1`, `P2` or `P3`. **Require ticket priority label** is on by default.
7. If **Require ticket acceptance criteria** is on, the description contains the words acceptance criteria (any case) or an unchecked task item, `- [ ]`. This check is off by default.

Optional labels shape the job: `bug` or `fix` makes a fix task, `change` a change task, and any other ticket a feature task. `agent-quick` is only a hint; the executor decides between the full and quick path and records why.

## Reviewing and starting tickets {#tickets-view}

Open a project from Projects, choose its **Jobs** tab and stay on the **Tickets** sub-tab. The global **Jobs** page in the sidebar has the same two sub-tabs and a **Job scope** selector. With **All projects**, the table gains a Project column and each row acts on its own project.

Nothing is read until you press **Read tickets**. It loads up to 500 open tickets. More than 10 tickets are shown a page at a time: choose 10, 25, 50 or All in **Rows per page**, and move with **Previous** and **Next**; the pager shows the page number of the page count. Each row shows number, title, labels, Status and actions. Status names what blocks a ticket:

| Status | Meaning |
|---|---|
| Ready to start | Every rule holds. |
| Missing label ... | The ready label is absent. |
| On hold or Excluded from ADORE | The hold or exclusion label is present. |
| Missing priority label | No priority label. |
| Missing acceptance criteria | Required text not found. |
| Has a job or Job: ... | ADORE already has a job; the job state is shown. |
| Not open | The ticket is closed. |
| Monitoring paused | Monitoring is paused for the project; an administrator activates it in the project Summary. Start stays unavailable until then. |

**Start** queues a job; the worker still applies the usual gates. If the ticket lacks the ready or a priority label, ADORE asks you to confirm, lets you choose a priority, and **Add labels and start** adds them in the repository first. Start is unavailable for closed, held or excluded tickets, tickets missing required acceptance criteria, and tickets with a job. **Retry** replaces Start when the job failed. **Stop** asks for confirmation, cancels an unfinished job and removes the ready label so monitoring does not pick the ticket up again. **Details** shows description and comments.

**Start** is also unavailable while the project's monitoring is paused. A confirmation opens directly under its ticket and names the labels it adds, including the priority you choose. If the worker cannot start a queued ticket, the notice says why in your language (monitoring paused, all execution slots busy, AEGIS check failed, ticket no longer eligible, or another ADORE process busy) and shows the last lines of the engine output. Labels that Start added stay on the ticket: ADORE picks it up when its rules allow, and **Stop** removes them.

## Checklist for a first ticket {#checklist}

1. Create all nine labels in the forge repository.
2. Check that Monitoring is Active.
3. Write a clear title and a description with acceptance criteria.
4. Add a priority label, and optionally `bug`, `fix`, `change` or `agent-quick`.
5. Add `agent-ready` last.
6. Wait for the next check, or press **Read tickets** and **Start**.
7. Follow the job in [Job lifecycle](/help/jobs). Terms are in the [Glossary](/help/glossary).
