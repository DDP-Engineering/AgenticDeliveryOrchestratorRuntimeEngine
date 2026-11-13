# Interface tour

The interface has a dark sidebar for moving between pages and a top bar that names the current page and offers common actions. This page lists the pages, the header buttons, the project hub and the status labels.

## Navigation {#navigation}

| Page | What you do there |
|---|---|
| Overview | See **Needs attention** and **Active jobs** for the projects you can access. **Details** opens a job in Jobs. |
| [Projects](/projects) | Browse enrolled projects with their repository, forge, Monitoring state, job count and last activity. Open a project to reach its hub. Administrators also see **Enroll new project** or **Import raw configuration**. |
| [Jobs](/jobs) | Pick a **Job scope**, then use the **Tickets** sub-tab to read forge tickets and start them, or the **Jobs** sub-tab to search jobs and open their details. |
| [Statistics](/metrics) | Read usage, quality and trends for a reporting period. See [Statistics and costs](/help/statistics). |
| Administration | Administrators only. It opens three pages: [System status](/admin/status), [Users](/admin/users) and [Change history](/admin/audit). See [Administration](/help/administration). |
| [My account](/account) | Choose your language and theme and change your password. |

The sidebar also shows your name and role, and **Sign out**. On a narrow screen, **Menu** opens the navigation and choosing a page closes it.

A Dev sees only the projects an administrator assigned and has no Administration entry. Every page has its own address, so bookmarks, Back, Forward and reload keep your place.

## Header {#header}

The top bar shows the page title and these controls.

- **Project**: a selector on Overview only. It narrows **Needs attention** and **Active jobs** to one project; the default is all projects you can access. Jobs has its own **Job scope** selector and Statistics has a **Project** selector in its reporting period row.
- **Refresh** and the **Last refreshed** time appear in the header on Users.
- **About**: the ADORE version, with **What's new** (release notes by release, newest first, grouped New, Improved and Fixed), **License** and **Third-party notices**.
- **How ADORE works**: opens this help center.

## Project hub {#project-hub}

Opening a project from Projects shows its name and repository path above these tabs.

| Tab | What it holds |
|---|---|
| Summary | Container type, executor, Monitoring, environment verification, job counts, and compact Needs attention and Active jobs tables. Administrators also get **Pause monitoring** or **Activate monitoring**, **Archive project** or **Restore project**, **Check host prerequisites** and **Repository access**. |
| Settings | The project's effective settings in groups. Administrators change one setting at a time through a reviewed change; Devs read them without secrets. See [Project settings](/help/settings). |
| Jobs | The Tickets and Jobs sub-tabs for this project, without a project selector. |
| Statistics | The same reporting period, tabs and exports as the Statistics page, for this project only. |
| History | Recorded changes to the project and its finished jobs. |
| Access | Administrators only: grant or remove a developer's access. |

Paused Monitoring stops new tickets from being picked up; jobs that already started continue.

## Status labels and badges {#statuses}

Badges carry a symbol as well as colour, and job lists show the current stage beside the status.

| Job status | Meaning |
|---|---|
| Working | ADORE is conducting a stage. |
| Publishing | ADORE is publishing an approved candidate. |
| Waiting for clarification | The agent needs an answer in the repository issue. |
| Waiting for approval | A person must approve the candidate on the forge. |
| Human review | A draft MR/PR is open; people decide whether to merge. |
| Handoff pending | A transfer to a person is waiting for a safe point. |
| Handed off | A person took over; automatic work has ended. |
| Completed | The job finished. This alone does not show that anyone merged. Compact lists call it Done. |
| Failed | The job stopped with evidence kept; an authorized user can **Retry** it. |
| Cancelled | The job was cancelled. |
| Stale | The job is marked stale; inspect its saved outcome. |

On Jobs, **Status** narrows the list to **Active jobs**, **Waiting**, **Human review** or **Finished jobs**. A project's Monitoring badge reads **Active** or **Paused**, and an archived project reads **Archived**. Environment verification reads **Verified**, **Partially verified**, **Verification failed**, **Stale verification** or **Unverified**; Unverified means there is no current evidence, not that a check failed.

After **Start**, **Retry** or **Cancel**, a notice reports the command as queued, running, completed, failed or uncertain. Inspect an uncertain command before submitting it again. A failed or uncertain command also says why, when the engine names a reason, and shows the engine's last lines.

## Automatic updates, language and theme {#preferences}

Overview, Projects, Jobs, project Settings, project Access, project History and Change history reload their data every 15 seconds while the browser tab is visible. Settings pauses while you have unsaved changes or a save or discard is in progress. Statistics and System status also refresh automatically. Background updates pause while the browser tab is hidden and resume when you return. Failed reads normally hide the affected data until a successful update. Statistics keeps its report and controls during background reads, with an in-view **Refresh** and source update times. After a connection failure or read deadline it can retain a clearly marked older report with **Retry**; invalid or unauthorized evidence stays hidden. See [Statistics and costs](/help/statistics). Both change-evidence panels also keep the same page during reads and offer **Refresh**, successful update time and marked older evidence with **Retry** after connection or deadline failures; see [Administration](/help/administration#change-history).

In [My account](/account), **Appearance** holds **Language** (English, Français, Deutsch, Română) and **Theme** (**System**, **Light**, **Dark**). Each choice is saved to your account and follows you across browsers; before you sign in, the sign-in page remembers the choice in the browser. **Change password** needs your current password and a new one of at least 8 characters.

The initial administrator sees a reminder until the factory password is changed. Follow **Change password** in the reminder to open My account.

When changing your password, enter the new password twice. Use the buttons to show or hide each entry. The new password needs at least 8 characters.
