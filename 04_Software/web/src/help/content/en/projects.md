# Adding a repository

Add a repository as a project so ADORE can pick up its ready tickets, run a coding agent on them and publish draft merge or pull requests for people to review. Only administrators add projects, and ADORE never merges.

## Before you start {#before-you-start}

Have these ready:

- The repository address (https or ssh) that the ADORE server account can read. ADORE clones it into its own folder when you create the project.
- AEGIS installed in the repository (`.agentic/aegis.py` and `.agentic/aegis.toml`). ADORE uses it as installed and never edits it. Its test commands run inside the Linux container, so write them for the container.
- A GitLab, GitHub or Gitea account that can read and update issues and create draft reviews.
- The ready and approval label names. A person adds the ready label to make a ticket eligible; see [Tickets for automatic pickup](/help/tickets#labels).
- The coding agent, its model ID and a container image on the server that contains the agent. See [Executors and models](/help/executors).

## Enroll new project {#add-project}

Choose **Enroll new project** on [Projects](/projects). The guided wizard starts at Repository and identity and takes five steps, and changing any answer makes earlier validation and checks stale.

| Step | What it asks |
|---|---|
| Repository and identity | **Repository URL** and **Read repository**: ADORE fills in **Forge**, **Repository**, **Gitea tea login**, **Target branch** and the project ID for you to confirm, and proposes a **Local clone path** you can change. **Continue** stays disabled until the repository has been read. **Display name** starts as the repository name; **Description** is optional. |
| Agent and model | **Executor** (opencode, codex, pi or qwen), **Model**, **Model authentication** (api-key, or host-auth for OpenCode and Codex only) and **Credential environment references**: variable names such as LOCAL_API_KEY, never values. |
| Eligibility, reviewers and limits | **Ready label**, **Approval label**, optional **Reviewers (comma-separated)** and four job limits: executor launches, active seconds, reported cost in USD and changed files. A cost cap of 0 switches that cap off; it does not mean free. |
| Verification | **Validate setup** checks structure and server folders. **Check environment** then tests Git, the forge tool and sign-in, the container engine, the agent in the image, the AEGIS files and, where possible, the model endpoint. Nothing is published. |
| Review and create | Shows the exact candidate and server locations. **Change** returns to a step. **Create project with pickup stopped** first clones the repository (from a URL), checks AEGIS and the target branch, then saves the project; **Open project** follows. |

The wizard uses the standard container profile. Native local execution and specialized container setups use the advanced server TOML method below.

## Import project config {#import-project}

Choose **Import project config** on [Projects](/projects) to enroll an existing ADORE `config.toml` exactly as it is, for example one created with the command line or saved earlier with **Download raw configuration** in a project's Settings. The file (UTF-8, up to 512 KiB) needs absolute server paths and no inline secrets: the review lists any it finds, so replace them with environment references first. Its project ID and state folder must not belong to an enrolled project. ADORE copies the file byte for byte and ends with **Enroll with pickup stopped**. History appears only if its data already exists at the declared state folder.

## Clone project config {#clone-project}

Choose **Clone project config** on [Projects](/projects) to start a new project with the working rules of another. **From a project on this server** reads a project you can access; **From a portable settings file** reads a portable JSON file (up to 64 KiB) from the same ADORE version. Only 15 working rules (polling, readiness, recovery, job budgets) are carried; identity, repository, labels, credentials, endpoints, images and history are never copied. Choose **Review source rules**, then **Set up new target** and answer the guided steps. Review unknown files: the checksum detects edits but does not prove authorship.

## After creation {#after-creation}

A new project starts with monitoring stopped. Developers see it once an administrator grants access on its **Access** tab. On the **Summary** tab:

1. Choose **Connect repository**. Enter the forge server address and an access token created on the forge, then **Verify and connect**. This confirms the account and read access to the repository. The token stays on the server, never in the browser. Alternatively, sign in the forge tool under the ADORE service account.
2. Choose **Check host prerequisites**. The details cover Git, the repository command tool, repository sign-in, the container engine, the agent in the image, the AEGIS files and the AI model connection. This is not a full job and does not prove push permission.
3. Run **Test AI connection** in Settings, as described in [Executors and models](/help/executors#test-connection).
4. Choose **Activate monitoring**. The Monitoring tile changes from Paused to Active and ADORE starts picking up tickets that carry the ready label. **Pause monitoring** stops new pickups but does not interrupt a running job.

## Archive, restore and delete {#lifecycle}

Administrators find these buttons on the Summary tab.

- **Archive project** works after jobs finish and queued requests clear. It keeps settings, history, metrics and audit records and stops new work. **Restore project** brings it back.
- **Delete project** appears only for archived projects and asks you to type the project name. It removes the project's ADORE settings, job history, metrics, containers and worktrees. It keeps the repository and its branches, worktrees of jobs handed to a person, a job-state folder outside ADORE home and the audit trail. Deletion is refused while work is queued or unfinished. **Also remove the local clone** (unticked) also deletes the clone ADORE made under its `repos` folder; it is offered only for a clean clone of this project's repository that no other project uses and no worktree kept by the deletion still needs, otherwise the dialog says why the clone stays.

> Deletion cannot be undone. To adjust a project afterwards, see [Project settings](/help/settings).
