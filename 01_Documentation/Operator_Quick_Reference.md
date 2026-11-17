# Operator quick reference

Applies to **ADORE 0.19.0**. This is a task reminder; the linked manuals define
the complete setup, configuration and recovery contracts.

## Setup and first pickup

1. Authenticate the host forge CLI (`gh`, `glab`, `tea` or Azure CLI with its
   azure-devops extension) and host Git
   separately. `git ls-remote origin` proves read access, not permission to push.
2. Choose a prepared project container image or managed local Pi. Install local
   project tools under the service account. See [Getting started](Getting_Started.md),
   [Local execution](Local_Execution.md) and [Project images](Project_Executor_Images.md).
3. Choose AEGIS or Direct. Automatic detection validates an installed AEGIS
   contract and selects Direct when absent. Explicit Direct bypasses AEGIS even
   when installed or unusable. Pi is the only executor in either workflow.
4. Review the project limits, publication approval and pipeline-repair policy.
   Publication approval defaults to enabled. Pipeline failure defaults to a
   bounded revision round; `notify` requests human intervention instead.
5. Create the configured labels before pickup. Web enrollment and project
   Settings offer **Create missing labels**. CLI init and polling do not create them.

For a standalone CLI profile, replace `<profile>` with its name:

```text
adore init <profile>
adore --profile <profile> config validate
adore --profile <profile> run --dry-run
adore --profile <profile> run --once
```

For web-managed projects, use setup checks and project monitoring. One web
supervisor coordinates project workers and their job pools. Do not start an
additional CLI polling loop over those profiles.

## Tickets and readiness

| Default label | Operator meaning |
|---|---|
| `agent-ready` | Allow pickup when readiness and capacity checks pass. |
| `P1`, `P2`, `P3` | Priority, highest first. A priority is required by default. |
| `agent-hold` | Prevent new pickup; active jobs continue. |
| `no-agent` | Exclude the ticket from pickup. |
| `agent-answered` | Resume clarification after adding a new answer comment. |
| `agent-revise` | Request a revision on the published MR/PR. |
| `agent-approved` | Approve the freshly presented candidate when approval is required. |

Names follow project settings. ADORE manages working, clarification, review,
failure and done lifecycle labels; editing a label does not transition saved
job state. Tickets cannot select another executor. Epics are excluded.
Acceptance-criteria checking is optional and off by default. A clear goal,
observable acceptance criteria and a bounded scope still help the agent.
See [Configuration](Configuration_Reference.md) and [Operations](Operations_Guide.md).

## Monitoring and steering

| Location or command | Use |
|---|---|
| **Jobs** | Select all projects or one project; search, filter and inspect jobs. |
| **Tickets** | Read automatically on opening; manually reread and sort columns. |
| Project **Summary** | Review project capacity and current state. |
| Job **Activity** | Browse paginated events; open the matched agent session when available. |
| Job **Agent sessions** | Read retained chat, select sessions and inspect live activity. |
| **Send now** / **Queue message** | Send an instruction to the current session now or after current work. |
| **Maximize** / **Restore** | Expand the conversation and return; Escape also restores. |
| Job **Job details** | Review saved outcome, branch, review information and diagnostics. |
| `adore --profile <profile> status` | Configuration health, state location and pause status. |
| `adore --profile <profile> runs` | Job identities, stages and lifecycle states. |
| `adore --profile <profile> logs <run-id>` | Recorded events for one job. |
| `adore --profile <profile> stats` | Outcomes, usage and reported or estimated costs. |

Pause stops automatic pickup while active jobs continue. Manual **Start** still
checks readiness and capacity. Cancel is a request until confirmed stopped.
Historical sessions are read-only. Message acknowledgement confirms receipt.
Treat retained conversation content as project data: it can include text printed
by tools. See [Web interface](Web_Interface.md) and [Security](Security_And_Credentials.md).

## Profiles, images and recovery

CLI configuration precedence is `-c FILE`, `--profile NAME`, active profile,
then `./config.toml`. Use an explicit profile in scripts.

Build images externally. ADORE retains reviewed image definitions and can execute
an optional [container preparation recipe](Container_Preparation.md). A failed
preparation requires explicit reprepare. Local Pi uses an owned Windows Job or
delegated Linux cgroup; the native service account still has its host credentials
and network access.

| Action | Effect and boundary |
|---|---|
| Answer clarification | Add a ticket comment and the answered label; monitoring resumes the workflow. |
| `retry <run-id>` | Reset the active stage counter; retain work, history and consumed budget. |
| **Restart job** for a cancelled job | Keep history and admit a fresh execution with the selected workflow. |
| `cancel <run-id>` | Request stopping the job; wait for confirmation before changing resources. |
| `reset <run-id> --to <stage> --force` | Correct ADORE's stage pointer after verifying evidence; never edit the AEGIS journal. |
| `delete <run-id> --force` | Explicit irreversible removal of the job and its owned resources. |
| `cleanup` | Remove eligible owned resources; protect active jobs, failed evidence and uncertain ownership. |

Prefix these commands with `adore --profile <profile>`. A changed image,
environment or resource identity requires a fresh job because execution plans
are pinned. Pending required forge notifications must be delivered before retry.
For unreadable or unsupported state, preserve evidence, confirm no active owner
and follow the error's named cleanup path. ADORE does not convert stored formats.
See [CLI reference](CLI_Reference.md), [Operations](Operations_Guide.md) and
[Troubleshooting](Troubleshooting.md).

ADORE publishes a draft or ready MR/PR according to settings. A human reviews
and merges. Cleanup removes only eligible resources with proven ownership.

## Presentations

The following editable presentations cover the same current operator tasks:

- [Setup and first run](Operator_Cheat_Sheets/Presentations/ADORE_01_Setup_And_First_Run.pptx)
- [Tickets, readiness and labels](Operator_Cheat_Sheets/Presentations/ADORE_02_Tickets_Readiness_And_Labels.pptx)
- [Monitoring and steering](Operator_Cheat_Sheets/Presentations/ADORE_03_Monitoring_And_Steering.pptx)
- [Profiles and container images](Operator_Cheat_Sheets/Presentations/ADORE_04_Profiles_And_Container_Images.pptx)
- [Failure recovery and cleanup](Operator_Cheat_Sheets/Presentations/ADORE_05_Failure_Recovery_And_Cleanup.pptx)

## Explicit job workflow

Start and fresh Restart require reviewing **With AEGIS** / **Without AEGIS**. CLI: `adore --profile NAME run --once --ticket IID --workflow direct` (or `aegis`). Automatic polling uses `workflow.mode = "auto"` or `"direct"`. Retry keeps the job’s saved workflow. Direct skips AEGIS even when installed; other repository rules and orchestrator limits remain in force.
