# Adding a repository

Add a repository as a project so ADORE can pick up its ready tickets, run a coding agent on them and publish draft merge or pull requests for people to review. Only administrators add projects, and ADORE never merges.

## Before you start {#before-you-start}

Have these ready:

- A Git clone of the repository on the ADORE server, with an `origin` and an existing target branch. Adding a project never clones; the path is on the server, not your computer.
- AEGIS installed in that clone (`.agentic/aegis.py` and `.agentic/aegis.toml`). ADORE uses it as installed and never edits it. Its test commands run inside the Linux container, so write them for the container.
- A GitLab, GitHub or Gitea account that can read and update issues and create draft reviews.
- The ready and approval label names. A person adds the ready label to make a ticket eligible; see [Tickets for automatic pickup](/help/tickets#labels).
- The coding agent, its model ID and a container image on the server that contains the agent. See [Executors and models](/help/executors).

## Add a project {#add-project}

Choose **Add project** on [Projects](/projects). **Guided new project** takes six steps, and changing any answer makes earlier validation and checks stale.

| Step | What it asks |
|---|---|
| Enrollment method | Nothing to enter. It confirms the clone already exists on the server. |
| Repository and identity | **Display name**, **Stable project ID** (lowercase letters, digits, dot, underscore or hyphen, up to 64 characters), optional **Description**, **Forge**, **Repository** as owner/repository (not a URL), **Gitea tea login** (Gitea only), **Local clone path** and **Target branch**. |
| Agent and model | **Executor** (opencode, codex, pi or qwen), **Model**, **Model authentication** (api-key, or host-auth for OpenCode and Codex only) and **Credential environment references**: variable names such as LOCAL_API_KEY, never values. |
| Eligibility, reviewers and limits | **Ready label**, **Approval label**, **Reviewers (comma-separated)** (at least one) and four job limits: executor launches, active seconds, reported cost in USD and changed files. A cost cap of 0 switches that cap off; it does not mean free. |
| Verification | **Validate setup** checks structure and server folders. **Check environment** then tests Git, the forge tool and sign-in, the container engine, the agent in the image, the AEGIS files and, where possible, the model endpoint. Nothing is published. |
| Review and create | Shows the exact candidate and server locations. **Change** returns to a step. **Create project with pickup stopped** saves it; **Open project** follows. |

The wizard uses the standard container profile. Native local execution and specialized container setups use the advanced server TOML method below.

## Import project {#import-project}

The same page offers three more methods.

- **Import portable settings** reads a portable JSON file (up to 64 KiB) from the same ADORE version. **Copy project settings** reads another project you can access. Both carry only 15 working rules (polling, readiness, recovery, job budgets); identity, repository, labels, credentials, endpoints, images and history are never copied. Choose **Review source rules**, then **Set up new target** and answer the guided steps. Review unknown files: the checksum detects edits but does not prove authorship.
- **Advanced: unchanged server TOML copy** opens [Enroll an existing configuration for this ADORE server](/projects/import). It takes an existing ADORE `config.toml` (UTF-8, up to 512 KiB) with absolute server paths and no secrets, copies it byte for byte and ends with **Enroll with pickup stopped**. History appears only if its data already exists at the declared state folder.

## After creation {#after-creation}

A new project starts with monitoring stopped. Developers see it once an administrator grants access on its **Access** tab. On the **Summary** tab:

1. Choose **Connect repository**. Enter the forge server address and an access token created on the forge, then **Verify and connect**. This confirms the account and read access to the repository. The token stays on the server, never in the browser. Alternatively, sign in the forge tool under the ADORE service account.
2. Choose **Check host prerequisites**. The details cover Git, the repository command tool, repository sign-in, the container engine, the agent in the image, the AEGIS files and the AI model connection. This is not a full job and does not prove push permission.
3. Run **Test AI connection** in Settings, as described in [Executors and models](/help/executors#test-connection).
4. Choose **Activate monitoring**. The Monitoring tile changes from Paused to Active and ADORE starts picking up tickets that carry the ready label. **Pause monitoring** stops new pickups but does not interrupt a running job.

## Archive, restore and delete {#lifecycle}

Administrators find these buttons on the Summary tab.

- **Archive project** works after jobs finish and queued requests clear. It keeps settings, history, metrics and audit records and stops new work. **Restore project** brings it back.
- **Delete project** appears only for archived projects and asks you to type the project name. It removes the project's ADORE settings, job history, metrics, containers and worktrees. It keeps the repository and its branches, worktrees of jobs handed to a person, a job-state folder outside ADORE home and the audit trail. Deletion is refused while work is queued or unfinished.

> Deletion cannot be undone. To adjust a project afterwards, see [Project settings](/help/settings).
