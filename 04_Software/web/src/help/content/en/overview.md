# What ADORE does

ADORE turns a prepared ticket on your code forge into a draft merge request or pull request that people review. This page explains the flow and the two roles; the other topics cover each screen.

## What ADORE does {#what-adore-does}

ADORE watches the projects an administrator has enrolled. When a ticket on the forge (GitHub, GitLab or Gitea) is prepared for pickup, ADORE starts a **job** for it:

- It runs a coding agent (the executor) in an isolated environment: a dedicated branch, working folder and container.
- The agent follows the repository's AEGIS workflow one stage at a time: Frame, Specify, Design, Build and Validate. A small change may take a quick path without Specify and Design.
- The executor validates the result. ADORE asks a person to approve that exact candidate.
- After approval, ADORE publishes a draft MR/PR for people to review. A project can be set to publish a ready MR/PR instead.

> ADORE never merges. It has no merge operation; a person decides whether to merge on the forge.

The web interface shows what is running and what needs attention. It also lets you start tickets, retry or cancel jobs, and, as an administrator, set up projects and accounts.

If a project's job state cannot be read, **Needs attention** names that project. Job data from the other selected projects remains visible.

## From ticket to merge {#flow}

| Step | Status shown | Who acts | What happens |
|---|---|---|---|
| 1. Prepare | No job yet | A person | The ticket gets the ready label and a priority label, or you press **Start** in Jobs → Tickets, which adds missing labels after you confirm. |
| 2. Work | Working | ADORE and the coding agent | ADORE creates the job and the agent works through the AEGIS stages. |
| 3. Clarify | Waiting for clarification | A person | Only if the agent has a question. Answer in the repository issue and add the answered label. |
| 4. Validate | Working | Coding agent | The executor runs the project's strict verification. |
| 5. Approve | Waiting for approval | A person | ADORE presents the candidate on the forge. A person adds the approval label. Approval is bound to that exact candidate. |
| 6. Publish | Publishing | ADORE | ADORE pushes the branch and opens the draft MR/PR. |
| 7. Review | Human review | A person | People review. Requesting a revision starts another revision round, which needs a fresh approval. |
| 8. Merge | Completed | A person | A person merges on the forge. ADORE does not. |

If the candidate or its target branch changes after approval, the approval no longer applies and the job validates again. Terms are explained in the [glossary](/help/glossary).

## Roles {#roles}

| Role | Sees | Can do |
|---|---|---|
| Administrator (Admin) | All current and future projects, plus Administration and costs | Everything a Dev can do, and enroll projects, edit project settings through reviewed changes, pause or resume Monitoring, archive or restore projects, manage users and project access, set audit retention, read change history, and see and set costs |
| Dev | Only the projects an administrator assigned | Start and stop tickets, retry or cancel jobs, read statistics for assigned projects, and read project settings (read-only, with secrets and financial settings omitted) |

A Dev never sees monetary values and cannot open the Administration pages. When no project is assigned, Overview asks the Dev to request access from an administrator. If there are no projects, an Admin can select **Enroll new project** on Overview.

## Getting started {#getting-started}

1. Administrators enroll the repository: [Adding a repository](/help/projects).
2. Choose the model the Pi coding agent uses: [Executors and models](/help/executors).
3. Prepare tickets so ADORE can pick them up: [Tickets for automatic pickup](/help/tickets).
4. Follow each job to its draft MR/PR: [Job lifecycle](/help/jobs).

Developers start at step 3 once an administrator has given them access to a project.

## Where to find more {#topics}

- [What ADORE does](/help/overview): this page.
- [Interface tour](/help/interface): sidebar, header, project hub and status labels.
- [Adding a repository](/help/projects): enroll a project.
- [Project settings](/help/settings): what each setting group controls.
- [Executors and models](/help/executors): the Pi coding agent, models and authentication.
- [Tickets for automatic pickup](/help/tickets): labels and starting tickets.
- [Job lifecycle](/help/jobs): statuses, waiting states, retry and cancel.
- [Statistics and costs](/help/statistics): usage, quality, trends and estimated costs.
- [Administration](/help/administration): users, access, system status and change history.
- [Glossary](/help/glossary): the terms used throughout the interface.
