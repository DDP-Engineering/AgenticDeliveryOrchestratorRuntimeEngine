# Operations guide

## System overview

ADORE coordinates eligible GitHub, GitLab, Gitea and Azure DevOps Services tickets through isolated
implementation, candidate publication and human review. Pi is the only coding
agent. Projects select container execution or managed Pi on the ADORE server.
Each job has its own Git branch, worktree, recorded workflow, execution plan and
resource identity. Project limits bound admission and consumed work.

| Owner | Responsibility |
|---|---|
| Pi and the repository instructions | Code changes, engineering decisions and selecting/reporting checks. |
| AEGIS, when selected for the job | Task journal, stage content and engineering transitions. |
| ADORE | Ticket selection, resource ownership, limits, recovery, host Git, candidate freshness and publication. |
| People | Clarification, configured approval, review and merge. |

ADORE does not run an independent repository test command and never merges.
The CLI and web interface share profiles and durable run state. The web API and
one supervisor use independent configuration, project and run processes;
projects progress independently up to their configured limits.

## Azure DevOps Services

Azure cloud operations use the common conductor. Work Item tags carry pickup,
status, clarification and candidate approval; a PR **label** carries revision.
Active/completed/abandoned PRs map to opened/merged/closed. Advisory CI uses the
current PR iteration's statuses and never infers success from missing information.
See [Azure DevOps Services](Azure_DevOps_Services.md) for exact area/process scope,
permission troubleshooting, missing-resource limitations and bounded live acceptance.

## Workflows

Before manual Start or Restart, choose **With AEGIS** or **Without AEGIS**.
Start uses the same selector in global Tickets and Projects > Tickets. Restart
creates a fresh job after confirmed owned cleanup; Retry, continuation and review
corrections retain the job’s saved workflow and Pi conversation.

For the latest cancelled job, **Restart job** retains its saved state, activity,
session archives and outcome. The new execution has a distinct `-rN` identity,
fresh working resources, conversation and budgets. Tickets follows the latest
execution; **Previous job** and **New job** navigate retained history. Failed-job
**Abandon and restart** remains destructive. Restart still requires an open,
eligible ticket, capacity, valid settings and verified cleanup; monitoring stays
paused if already paused. Web success confirms durable admission, not completion.
Retained history has no automatic expiry. Remove an explicitly selected old job
with `adore delete <run-id> --force`; audit retention does not remove job history.

`workflow.mode = "auto"` (default) detects AEGIS from the repository; absence
selects Direct and a present unusable payload is refused. `workflow.mode = "direct"`
skips AEGIS for new jobs. A manual `aegis` or `direct` choice overrides this default.
Explicit AEGIS requires a usable installed payload and never falls back. Direct
does not probe or invoke AEGIS, inspect its journals or create tasks/stages, even
when AEGIS is installed or unusable. The actual workflow is pinned in run state
before dispatch. ADORE leaves installed AEGIS files intact.

| Workflow | Stages | Completion evidence |
|---|---|---|
| AEGIS | Frame → Specify → Design → Build → Validate → Done; Specify and Design may be recorded as skipped | The agent's completed task journal and reported checks. |
| Direct | Implementation (`build`) → Validation (`validate`) → Done | Product changes and the retained implementation summary. |

One Pi implementation conversation belongs to each job. Each AEGIS stage runs
in a bounded RPC process; later stages, continuations and corrections restart
RPC with that same exact conversation. A permitted return to an earlier stage
continues from the journal and retained Pi context. Supported version/schema policy is defined in
`04_Software/adore/aegis.py`; retired stage names are refused.

The trusted Direct instruction overrides only repository obligations to use AEGIS
procedures. Coding, licensing and relevant verification rules remain in force.
The executor receives implementation work without deadline or budget instructions;
ADORE retains its existing limits. Direct implementation reads the repository instructions and writes
`ADORE_SUMMARY.md`. ADORE retains the summary and excludes the summary/questions
exchange files from the candidate. Summary-only work is not a product change.
Checks remain agent-reported; Direct does not claim independent verification.
Clarification and review revisions resume the same job conversation in either
workflow. Pi provides its own persistence and automatic compaction. The first
prompt supplies the ticket; later prompts supply the current stage and new
instructions, with changed ticket content supplied again when needed.
Independent reviewers use separate contexts only when the repository enables
them through its existing AEGIS review policy. Stage checkpoints, failed-attempt
limits, cancellation and per-attempt ChatGPT token renewal still apply.

Private history lives under `runs/<run-id>/io/pi-conversation/`, outside Git.
ADORE checks its exact identity before prompting. Missing or corrupt required
history stops the job; inspect it, or use the existing job deletion action and
start a new job. It is never silently replaced or selected from account history.
Agent sessions continues to show individual recorded attempts; prior history is
not replayed into each attempt, and previous token usage is not counted again.

## Runtime project contract

Prepare host Git and forge authentication, a clone of the intended repository,
the target branch, documented build/test instructions, and the selected runtime.
Generated caches and local tool state belong in the target's ignore rules.
AEGIS projects maintain their own payload, task journals and configuration.

Only eligible open tickets can start: configured readiness/priority requirements
apply to automatic pickup and manual Start. Epic, hold and exclusion labels block
admission.
Create the configured lifecycle, approval and revision labels before running.
See [Getting started](Getting_Started.md) and [Configuration](Configuration_Reference.md).

Every admitted job records a complete execution plan before its first save.
Containers without preparation still pin the effective image and provisioned
container/image IDs. Local jobs pin their host/account/resource identity.
Preparation remains optional. Replaced resources or stable policy drift require
explicit recovery or a fresh job; a stored job never receives a guessed plan.

Reusing a repository container requires its current
`io.ddp.adore.git-binding=pointer-v2` label and intact saved Git pointer. A missing,
empty or unknown label is refused with the exact container name; that includes a
container created by an earlier build, which still mounts the whole clone. After confirming
that the container is no longer running active work, remove that named container
manually and start a fresh job. ADORE does not relabel, convert or delete it
automatically. Preserve worktrees and evidence while diagnosing the refusal.

## Runtime states

Stage records engineering progress; lifecycle records the operator-visible state.
A stage of Done can coexist with approval or review still pending.

| Lifecycle | Meaning |
|---|---|
| `working` | Admitted work or a bounded executor attempt; queued work is distinguished by its dispatch evidence. |
| `parked-clarification` | Waiting for an answer on the source ticket. |
| `awaiting-approval` | The candidate is presented for configured human approval. |
| `publishing` | Candidate publication is in progress. |
| `in-review` | The published MR/PR awaits human review or merge. |
| `failed` | Work stopped; retained evidence supports explicit recovery. |
| `done` | A human merge was observed. |
| `cancelled` | Cancellation and resource release were recorded. |
| `handoff-pending` / `handed-off` | Human ownership was requested / confirmed. |

## Normal operator loop

1. Enroll and verify the project. Check repository access, runtime prerequisites
   and the model connection separately; a version check does not prove AI access.
2. Review readiness, labels, target branch, approval policy and budgets.
3. Read Tickets and inspect eligibility. Start one explicitly or enable monitoring.
4. Follow Jobs, Activity and Agent sessions. Use the recorded attempt, not an old
   event timestamp alone, to diagnose execution.
5. Answer clarification on the ticket. Apply the configured answered label.
6. Review the candidate presentation and approve it when approval is required.
7. Review the MR/PR; request changes or merge through the forge.

Use one web supervisor per ADORE home. Do not run an additional `adore run --loop`
scheduler over the same web-managed profiles. The standalone CLI remains usable
for deliberate project operations; locks and ownership checks still apply.

## Admission, capacity and budgets

Monitoring pause stops new automatic pickup and preserves in-flight work.
Explicit Start is available while monitoring is paused, subject to readiness,
unique ticket ownership and project capacity. Successful Start confirms a durable
admission, not that Pi has already started.

Jobs from different projects run independently. A project admits up to its
`polling.max_concurrent_runs`; a reviewed reduction below current usage can remain
staged while existing jobs finish. It does not cancel those jobs.

Executor-launch and cumulative active-work limits are separate from token/cost
statistics. Waiting time is excluded. Retry, clarification and revisions retain
consumed work. Limits are reread before attempts; a running attempt keeps its
existing timeout. A failed exhausted job needs explicit Retry after adjustment.

See [Configuration](Configuration_Reference.md) for limits and scoped save rules.

## Clarification and instructions

A blocking question parks the job and appears on the source ticket. Read it from
Job details or the forge, answer on that ticket and use the configured answered
label. An unanswered clarification can exhaust its configured deadline.
Questions do not count as failed engineering attempts.

Agent sessions also supports messages during working jobs. Send now submits at
the next safe agent boundary; Queue message waits for current work to finish.
Receipt confirms delivery, not completed work. Unacknowledged instructions can
remain queued for a later session. Historical conversations are read-only.

## Approval and publication

Human approval is enabled by default through `delivery.require_human_approval`.
ADORE presents the retained result, changes and exact candidate/target binding,
removes an existing approval label and waits for fresh approval. Candidate or
target drift invalidates that approval.

When approval is disabled, candidate and target freshness checks still apply.
Guarded progress commits can be pushed when `delivery.publish_checkpoints` is
on; these are separate from final MR/PR publication and do not authorize merge.
The agent never commits, pushes, creates reviews or merges on ADORE's behalf.

ADORE supplies the configured agent name/email to its checkpoint and target merge
commands, so no global Git identity is needed. Actual file conflicts return to
the implementation conversation. Other Git integration failures preserve the job
and report an integration error for operator correction instead of relaunching Pi.

ADORE adopts an existing matching open MR/PR where appropriate, or creates a
Draft/Ready review according to `delivery.draft`. It refreshes the publication
description and records its pushed checkpoint. A publication failure retains
state for inspection; an uncertain outcome is not permission to publish blindly.

## Review and revisions

Use the configured revise label on the MR/PR to request changes. A revision keeps
the job branch and recorded workflow. AEGIS creates a new task; Direct returns to
implementation. Fresh candidate evidence and the configured approval policy apply.

`review.on_pipeline_failure` chooses automatic revision, notification or ignore.
Automatic repairs and human-requested revisions share the review-round limit.
Only a revision requested with the label is given the MR/PR comments; add the
label when the agent should act on review feedback.
ADORE reads pipeline verdicts; it does not host CI or fetch pipeline job logs.
After a human merge it records completion and honors the configured source-branch
removal policy. An unmerged closed review fails the job.

## Recovery

Read the failure reason, Activity, session and diagnostic evidence first. Correct
the actual cause before Retry: authentication, runtime ownership, missing tools,
source conflict, limits, unavailable payload or notification transport.

```text
adore --profile <name> logs <run-id>
adore --profile <name> retry <run-id>
```

Retry resets the current stage counter and preserves work, task history,
cumulative active work and audit evidence. A pending required notification blocks
new code work until delivery succeeds. A normal poll replays due notifications
without starting another implementation session.

A completed attempt can report an earlier supported AEGIS stage. That is different
from `STALE_WORKING`, where the conductor was interrupted. Forward jumps without
required stage evidence fail closed. An explicit reset changes only ADORE's stage
pointer; it does not edit the AEGIS journal. Use the CLI reference before resetting.

### Environment and preparation recovery

Retry retains the pinned environment. A changed backend, stable execution policy,
resource ownership or image can require a fresh job. The web action **Abandon and
start again** shows the destructive effects and requires confirmation. It verifies
owned resources and starts the still-open ticket with current settings only after
cleanup succeeds. Monitoring remains paused when already paused.

A local Retry can explicitly revalidate volatile installed-executor/PATH evidence
on the same host/account while retaining stable policy and cumulative limits.
It does not switch a job to another backend. See [Local execution](Local_Execution.md).

Incomplete preparation is not replayed by ordinary Retry. Inspect its retained
steps, then use the explicit reprepare operation when appropriate. See
[Container preparation](Container_Preparation.md).

### Publication and Git recovery

Candidate or target changes require fresh validation/presentation. Before retrying
uncertain publication, inspect the saved checkpoint, remote branch and MR/PR.
`STALE_PUBLISHING` requires explicit recovery rather than automatic replay.
Checkpoint failures preserve the worktree and identify the failing path or Git
operation. Correct that cause before retrying; do not bypass resource ownership.

### Cancel, handoff and cleanup

Pause is not cancellation. Cancel queues a durable request when the run is owned;
confirmation means the actual stop/cleanup was recorded, not merely accepted.
Handoff waits for a safe boundary and preserves human-owned work. Wait for
`handed-off` before editing that worktree.

Failed jobs retain their recovery evidence. Explicit Cancel/Delete are resource
release boundaries; routine cleanup protects active, failed, human-owned and
corrupt jobs. Foreign resources and unknown live owners are never guessed away.
Never remove a live lock file. See [CLI reference](CLI_Reference.md) for exact flags.

## Worker supervision and service maintenance

The API serves authenticated requests and durable command results. The supervisor
owns independent configuration and project workers; project workers dispatch fresh
single-run processes. Each process checks durable ownership and ancestor identity.
A blocked project does not consume another project's configuration/execution lane.

The API and worker must use the same account and absolute ADORE home. Stop the
whole supervisor only when its owned jobs can safely stop. For deployment, preserve
active workers until a validated rollout can retain their running processes.
The portable Start/Stop controls own the complete application tree.

Interrupted effects retain uncertain ownership until process death is proved.
They are not silently replayed. Inspect durable operation outcomes and job evidence
before resubmitting a command. Service setup is in
[deployment tools](../02_Tools/setup/README.md).

## Data, backup and maintenance

Back up the ADORE home, profile configuration and protected credentials, web
identity database, state, image definitions and any externally configured state
roots. Keep backups private. A stopped copy avoids races; a live SQLite backup
must use SQLite's backup mechanism, not a lone copy of a changing database file.
An active filesystem/log snapshot is not an atomic application-wide backup.

Each stored format has one current schema. Unsupported data is refused with
explicit operator cleanup guidance. The application does not convert or recreate
an incompatible store. Do not fabricate missing plans or job history.

Statistics distinguish observed tokens, reported cost, estimated cost and missing
coverage. Missing evidence is not zero. Runtime evidence and summaries remain
separate from session text. Use explicit export/report commands for retained data;
`stats --rebuild` changes metrics, not job state or journals.

## Repository content and progress

ADORE observes Git progress using exact content bytes. Replacement characters,
non-UTF-8 source data, binary files and large generated diffs do not invalidate
that observation. Content correctness belongs to the repository checks performed
by the executor. Git command failures, unsafe paths or unreadable files still
produce explicit errors. This behavior applies to both AEGIS and Direct jobs,
independently of the model, executor, programming language or framework.

## References

- [Web interface](Web_Interface.md): navigation, job details and account workflows.
- [CLI reference](CLI_Reference.md): exact commands and flags.
- [Configuration reference](Configuration_Reference.md): settings and defaults.
- [Security and credentials](Security_And_Credentials.md): account and secret boundaries.
- [Getting started](Getting_Started.md): installation and first project.
