# ADORE project map

Current facts and routing only. Read the relevant component, not every linked manual.
Root AGENTS.md owns repository policy; task journals are history, not current instructions.

## Product and boundaries

ADORE conducts opted-in forge tickets through isolated implementation and human review.
GitLab, GitHub, Gitea and Azure DevOps Services share a forge interface. Pi is the only executor.
Pi implements and reports repository checks. ADORE owns admission, worktrees/resources,
recovery, candidate freshness, approval and publication; only humans merge.

New jobs use automatic detection or explicit AEGIS/Direct selection. Direct bypasses installed
AEGIS entirely; Retry retains workflow and the private job conversation. AEGIS stages,
continuations and corrections resume that conversation through bounded RPC processes.
The supported AEGIS range is declared in `04_Software/adore/aegis.py`.

Each job has a pinned execution plan. Failures retain retry evidence. Cancel releases verified
working resources and retains recorded history. Only the latest cancelled execution can Restart;
a fresh `-rN` generation has independent resources/budgets and links to its predecessor.
Failed abandonment remains destructive. Stale confirmation or uncertain ownership refuses effects.

Each stored format has one current structure, with no migration or compatibility path.
Web schema stays 1 and validates its complete structure. Unsupported stores require explicit
operator cleanup; no automatic reset. Release version comes from `04_Software/pyproject.toml`.

## Read by concern

| Concern | Current implementation contract |
|---|---|
| Admission, AEGIS/Direct, approval, recovery | `05_SoftwareDocu/Component_Orchestrator.md` |
| State, generations, dispatch, journals and locks | `05_SoftwareDocu/Component_State_Store.md` |
| Git checkpoints, fingerprints and isolated resources | `05_SoftwareDocu/Component_Isolation.md` |
| Pi RPC, private conversation and session recording | `05_SoftwareDocu/Component_Executor_Launcher.md` |
| Queued/live instructions and acknowledgement | `05_SoftwareDocu/Component_Instructions.md` |
| Native ownership, managed Node/Pi, Windows Jobs/Linux cgroups | `05_SoftwareDocu/Component_Local_Execution.md` |
| Plans, recipes and explicit preparation | `05_SoftwareDocu/Component_Preparation.md` |
| Forge output, scope and Azure tag/PR-label semantics | `05_SoftwareDocu/Component_Forge_Adapters.md`, `Component_Azure_DevOps.md` |
| Typed settings and per-job workflow selection | `05_SoftwareDocu/Component_Config.md` |
| Accounts, grants, CSRF, durable operations and owners | `05_SoftwareDocu/Component_Web_Identity.md` |
| Supervisor, project/run/configuration workers | `05_SoftwareDocu/Component_Web_Worker.md` |
| Jobs, sessions, budgets, literal records and role-limited usage | `05_SoftwareDocu/Component_Web_Jobs.md` |
| Navigation, scoped Jobs/Tickets, three tabs and drafts | `05_SoftwareDocu/Component_Web_Frontend.md` |
| Usage, unknown costs, projection ownership | `05_SoftwareDocu/Component_Metrics.md` |

The complete component index is `05_SoftwareDocu/README.md`. AEGIS knowledge pages route to
component sources/tests; do not duplicate full contracts here. User workflows and commands are
in `01_Documentation/Operations_Guide.md`, `Web_Interface.md` and `CLI_Reference.md`.

## Interface essentials

Global Jobs and Tickets have all-project/single-project scope. Project Jobs/Tickets are separate
tabs; capacity stays in Summary. Tickets reads on entry and keeps manual Read tickets.
Job details has Activity, Agent sessions and Job details tabs, with a right-side budget panel.
Session history is read-only; live instructions support Send now/Queue message and chat maximization.
Restart success confirms durable admission and opens the new job, not completed implementation.

## Change discipline

Follow root AGENTS.md, Code_Style.md and Releases.md. Update only affected source, tests,
component documentation, four-locale help and user notes. Requirements cover implemented product
behavior and its tests. Preserve history without importing it into the active context.
