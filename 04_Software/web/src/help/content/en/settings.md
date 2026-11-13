# Project settings

A project's Settings tab lists the working rules ADORE applies to it: which tickets it picks up, its limits, how it publishes and which agent it uses. Administrators edit several settings and save them together; developers read them.

## Where to find Settings {#where}

Open [Projects](/projects), choose a project and select the **Settings** tab. The tabs are Summary, Settings, Jobs, Statistics, History and, for administrators, Access.

Saved settings refresh every 15 seconds while the browser tab is visible. Updates pause while you have unsaved settings or while a save or discard is in progress. The refresh also pauses while you enter a price or API key, or complete ChatGPT sign-in. An observed monitoring result revalidates clean saved settings without closing groups; dirty drafts and valid confirmations keep their existing guards. Your own successful Save validates the saved values before editing resumes, without closing the open groups.

Administrators can edit. Developers with access to the project see **Read-only settings**, without Edit buttons and without secrets or financial settings. Each project has its own settings; global capacity and audit retention belong to Administration.

## Setting groups {#groups}

Every group is closed when you open Settings, and the number beside its name counts its rows.

| Group | What it controls |
|---|---|
| Repository | Forge and repository, Gitea login, **Target branch** (base of new jobs and destination of PR/MRs), the job branch name template with an optional naming rule and a live example, and the agent's display name, resource name and commit author email. |
| Tickets | **Ready for pickup label**, **Exclude from pickup label**, the folded **Status labels**, how often ADORE checks the forge, whether tickets need acceptance criteria or a priority label, and the default task type. See [Tickets for automatic pickup](/help/tickets#labels). |
| Implementation | Per-job limits: **Active job limit**, **Maximum executor launches per job**, **Active work time limit (seconds)**, **Job cost cap (USD)**, **Maximum changed files per job** and **Stage attempt time limit (seconds)**. It also holds **Verification command**, **Clarifications**, **Recovery after errors**, **Advanced stage time limits**, **Publish progress commits** and the quick-path label. |
| PR/MR and review | **Request review from**, **PR/MR state at publication** (Draft or Ready for review), the approval label, **Remove branch after human merge**, revision rounds and **Action when PR/MR CI checks fail** (Automatic repair, Notify only or Ignore). |
| Statistics | **Record completed job measurements** and **Record agent-reported tokens**. **Statistics database file** is shown for information only. |
| Agent and model | Provider, model, authentication and **Test AI connection** [Executors and models](/help/executors). |
| Technical details | Read-only installation values such as the job state folder, the local repository path and the job working folders. They are changed in the project's `config.toml` on the server, and changing a path does not move existing data. |

## Values and help {#values}

Each row has a label, a description that is always visible, an **Active value** and an **ADORE default**. The description says what the setting controls, its unit or allowed values, and what changing it does, or that it is reserved and unused. There is no separate Help button.

A **Default** badge means the project's `config.toml` does not set the value, so ADORE's default applies. Editing it writes a value for this project only. A row marked **Not editable here** is changed in `config.toml` on the server. A row marked **Apply only with pickup paused and no active jobs** needs the extra condition described below.

Choose **Installed on the server** to use ADORE-managed Pi under the current OS account. The optional **Project tools PATH** selects the tool directories. See [Install Pi on the server](/help/executors#installed-executors).

## Editing {#editing}

1. Choose **Edit** beside each value you want to change. You can edit several settings across groups.
2. Use the single **Save** button above the groups. It is enabled only when values change and all open edits are valid.
3. For important changes, **Confirm important changes** shows the project, changed values and effects. Choose **Save changes**, or **Keep editing** to return without saving.

Rules that apply:

- **Discard changes** clears all unsaved edits. Cancelling the confirmation keeps them without creating a saved candidate.
- Saving is bound to the configuration you edited. A stale revision stops saving and retains your inputs. Discard your changes to reload the saved settings before editing again. Concurrent administrators get a conflict.
- The server checks the complete configuration and saves all edits together. A budget-only reviewed save also allows jobs waiting for clarification, with no active conductor or unfinished operation. Other settings require finished jobs. A failed save retains your inputs and any prepared candidate for retry.
- Identity and runtime changes also need monitoring paused. Choose **Pause monitoring** on Summary and let active work finish; pausing does not interrupt a running job.
- Budget limits apply before the next attempt or resume, preserving consumed work and progress. See [Job budgets](#budgets).

Navigation and browser reload ask before discarding unsaved settings edits. Brief Windows file locks are retried automatically; if saving still fails, check file access and retry **Save**.

## Verification command {#verification-command}

In **Implementation**, **Verification command** is optional single-line shell text saved as `[workflow] verify_command`. Administrators use the same **Edit** and **Save** flow as other settings; developers can read it but cannot edit. It is also available during enrollment; see [Repository workflows](/help/projects#workflows).

For the direct workflow, ADORE runs it independently from the job worktree root in the selected execution environment under the validation time limit. Keep the exact spaces, quotes and shell operators you need. An empty value leaves the candidate explicitly unverified. Line breaks and NUL are refused with field feedback and prevent Save; correct the text rather than expecting it to be flattened. The web interface never runs the command on enrollment or save.

AEGIS jobs ignore this setting and use the repository’s AEGIS test commands. The field remains visible in Settings for either workflow. No command is suggested or selected automatically.

Direct implementation uses the **Implementation** `build` limit in `workflow.stage_timeout_overrides`; independent verification uses the **Validation** `validate` limit. Each falls back to the general `budgets.per_gate_timeout_seconds` when its override is unset. The other AEGIS stage limits do not apply to direct jobs.

## Original TOML {#toml}

Beside the Project settings heading, administrators have **Preview raw configuration** and **Export raw configuration**. Preview opens a closable dialog and keeps the text only in memory. Download gives the saved `config.toml` exactly as stored, with comments, formatting and any inline secrets, so handle it as a secret. Neither includes a pending candidate, resolved defaults, separate `.env` files or external credentials. Developers cannot use them. Select the exported file in [Import raw configuration](/help/projects#import-project) and ADORE automatically checks server paths, state-folder ownership and inline secrets before enrollment.

## Agent system packages {#system-packages}

**Allow agent system package installation**

In Settings → Agent and model, administrators enable this permission with **Save** and confirm its effect. It is off by default and available for container projects. Rebuild or select a compatible image with sudo first, then start a fresh job. The agent runs package commands directly, reads failures and adapts within job limits.

Network access remains separate: open permits reachable sources, allowlist-proxy permits allowed HTTP/HTTPS domains, and none permits only available local sources. Package scripts have administrative rights inside the container; mounted project folders remain shared with the server. Installed system packages remain when the same container resumes; a fresh container requires reassessment and installation.

## Job budgets {#budgets}

Job details shows **Executor launches** (for example 9 / 20) and **Active work (seconds)** beside the current project limits, independently of token statistics. At 90% it warns that a limit is near; at the limit it asks you to raise it before resuming. The default launch limit is 20 in both enrollment and `adore init`.

Administrators can follow **Adjust budgets in project Settings**, open **Implementation**, edit only budgets, choose **Save** and confirm the exact values. A reviewed budget-only save is allowed while jobs wait for clarification, with no running conductor or unfinished operation. Other settings keep their usual idle and pause checks; developers have read-only settings.

Budgets are reread before each attempt, including resume and retry. A running attempt keeps its timeout. Active work is cumulative across retries, clarification answers and revisions; waiting time is excluded. Raising a limit preserves consumed work, the task and saved progress. A failed exhausted job still needs **Retry** after adjustment. Invalid or missing configuration stops further attempts until corrected.

If current limits cannot be read, the detail keeps saved consumption, evidence and recovery controls visible. Limits show — with an explicit unavailable notice; no default is guessed. Correct the project configuration before running again.
