# Project settings

A project's Settings tab lists the working rules ADORE applies to it: which tickets it picks up, its limits, how it publishes and which agent it uses. Administrators change them through a reviewed, one-setting-at-a-time flow; developers read them.

## Where to find Settings {#where}

Open [Projects](/projects), choose a project and select the **Settings** tab. The tabs are Summary, Settings, Jobs, Statistics, History and, for administrators, Access.

Administrators can edit. Developers with access to the project see **Read-only settings**, without Edit buttons and without secrets or financial settings. Each project has its own settings; global capacity and audit retention belong to Administration. Settings does not refresh itself, so use the header Refresh to reread it.

## Setting groups {#groups}

Every group is closed when you open Settings, and the number beside its name counts its rows.

| Group | What it controls |
|---|---|
| Repository | Forge and repository, Gitea login, **Target branch** (base of new jobs and destination of PR/MRs), the job branch name template with an optional naming rule and a live example, and the agent's display name, resource name and commit author email. |
| Tickets | **Ready for pickup label**, **Exclude from pickup label**, the folded **Status labels**, how often ADORE checks the forge, whether tickets need acceptance criteria or a priority label, and the default task type. See [Tickets for automatic pickup](/help/tickets#labels). |
| Implementation | Per-job limits: **Active job limit**, **Maximum executor launches per job**, **Active work time limit (seconds)**, **Job cost cap (USD)**, **Maximum changed files per job** and **Stage attempt time limit (seconds)**. It also holds **Clarifications**, **Recovery after errors**, **Advanced stage time limits**, **Publish progress commits** and the quick-path label. |
| PR/MR and review | **Request review from**, **PR/MR state at publication** (Draft or Ready for review), the approval label, **Remove branch after human merge**, revision rounds and **Action when PR/MR CI checks fail** (Automatic repair, Notify only or Ignore). |
| Statistics | **Record completed job measurements** and **Record agent-reported tokens**. **Statistics database file** is shown for information only. |
| Agent and model | The model, launch command, authentication and **Test AI connection**. See [Executors and models](/help/executors). |
| Technical details | Read-only installation values such as the job state folder, the local repository path and the job working folders. They are changed in the project's `config.toml` on the server, and changing a path does not move existing data. |

## Values and help {#values}

Each row has a label, a description that is always visible, an **Active value** and an **ADORE default**. The description says what the setting controls, its unit or allowed values, and what changing it does, or that it is reserved and unused. There is no separate Help button.

A **Default** badge means the project's `config.toml` does not set the value, so ADORE's default applies. Editing it writes a value for this project only. A row marked **Not editable here** is changed in `config.toml` on the server. A row marked **Apply only with pickup paused and no active jobs** needs the extra condition described below.

Detection starts automatically when local execution is selected; switching agents uses the detected list. Open **Advanced** for **Detect installed executors** if you need to refresh it. For local execution, choose a detected installation or enter an executable path; see [Detect installed executors](/help/executors#installed-executors). Open **Advanced** for the full command, a manual executable path, home/PATH overrides and Linux cgroup delegation. Leave home and PATH empty for automatic values. PATH means tool directories, not the executable file. Account names in Settings verify the current identity; they do not switch users.

## Editing {#editing}

1. Choose **Edit** beside the Active value, enter the new value and choose **Prepare candidate**. This writes only a pending candidate; the live configuration is unchanged.
2. The **Pending configuration** panel appears above the groups and lists only the changed values. A candidate that changes nothing cannot be applied. Open **Technical details** for the full comparison, the effect, the preparation time, both revisions and **Copy safe review**. Credential values are redacted.
3. Choose **Apply change** to submit it, or **Discard change** to remove only the candidate.

Rules that apply:

- One setting at a time: other Edit buttons stay disabled until the candidate is applied or discarded.
- Review is bound to revisions. Apply sends the reviewed base and candidate revisions, so if the active file changed meanwhile you must discard, refresh and prepare again. Two administrators editing at once get a conflict instead of overwriting each other. Edits made directly to the file on the server bypass this protection.
- The server rechecks at Apply that no job is active and no operation is unfinished. A blocked Apply keeps the candidate and explains how to recover.
- Settings that change identity or runtime also need monitoring paused. Choose **Pause monitoring** on Summary and let active work finish; pausing does not interrupt a running job.
- New values apply to later jobs. Existing jobs keep their configuration.

Brief Windows file locks are retried automatically. If settings still cannot be saved, the reviewed candidate stays available: check file access and retry **Apply change**.

## Original TOML {#toml}

Beside the Project settings heading, administrators have **Preview raw configuration** and **Download raw configuration**. Preview opens a closable dialog and keeps the text only in memory. Download gives the saved `config.toml` exactly as stored, with comments, formatting and any inline secrets, so handle it as a secret. Neither includes a pending candidate, resolved defaults, separate `.env` files or external credentials. Developers cannot use them. A downloaded file can be enrolled again with [Import project config](/help/projects#import-project) once its secrets are replaced with environment references.

## Agent system packages {#system-packages}

**Allow agent system package installation**

In Settings → Agent and model, administrators can enable this separate permission through Prepare candidate and Apply change. It is off by default and available for container projects. Rebuild or select a compatible image with sudo first, then start a fresh job. The agent runs package commands directly, reads failures and adapts within job limits.

Network access remains separate: open permits reachable sources, allowlist-proxy permits allowed HTTP/HTTPS domains, and none permits only available local sources. Package scripts have administrative rights inside the container; mounted project folders remain shared with the server. Installed system packages remain when the same container resumes; a fresh container requires reassessment and installation.
