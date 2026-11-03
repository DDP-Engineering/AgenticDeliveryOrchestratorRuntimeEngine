# Adding a repository

Add a repository as a project so ADORE can pick up its ready tickets, run a coding agent on them and publish draft merge or pull requests for people to review. Only administrators add projects, and ADORE never merges.

## Before you start {#before-you-start}

Have these ready:

- The repository address (https or ssh) that the ADORE server account can read. ADORE clones it into its own folder when you create the project.
- AEGIS installed in the repository (`.agentic/aegis.py` and `.agentic/aegis.toml`). ADORE uses it as installed and never edits it. Its test commands run inside the Linux container, so write them for the container.
- A GitLab, GitHub or Gitea account that can read and update issues and create draft reviews.
- The ready and approval label names. A person adds the ready label to make a ticket eligible; see [Tickets for automatic pickup](/help/tickets#labels).
- The model ID for the Pi coding agent and, for a container project, an image on the server built from the ADORE base image, which contains Pi. See [Executors and models](/help/executors).

## Enroll new project {#add-project}

Choose **Enroll new project** on [Projects](/projects). The guided wizard starts at Repository and identity and takes five steps, and changing any answer makes earlier validation and checks stale.

| Step | What it asks |
|---|---|
| Repository and identity | **Repository URL** and **Read repository**: ADORE fills in **Forge**, **Repository**, **Gitea tea login**, **Target branch** and the project ID for you to confirm, and proposes a **Local clone path** you can change. **Continue** stays disabled until the repository has been read. **Display name** starts as the repository name; **Description** is optional. |
| Agent and model | Choose **Provider**, **Model** and endpoint details, when needed. Select **Runs in**, the runtime and image for a container. Save the provider key in Settings after creation. For **Installed on the server**, only the current OS account and optional **Project tools PATH** are shown. |
| Eligibility, reviewers and limits | **Ready label**, **Approval label**, optional **Reviewers (comma-separated)** and four job limits: executor launches, active seconds, reported cost in USD and changed files. A cost cap of 0 switches that cap off; it does not mean free. |
| Verification | **Validate setup** checks structure and server folders. **Check environment** then tests Git, the forge tool and sign-in, the container engine, Pi in the image and the AEGIS files. Nothing is published. Each result appears beside its button; **Continue** opens the review once the setup is valid. |
| Review and create | Shows the exact candidate and server locations, and a closed **Settings left at their defaults** list of every other setting with its default value (read-only; change them in Settings after creation). **Change** returns to a step. **Create project with pickup stopped** first clones the repository (from a URL), checks AEGIS and the target branch, then saves the project and, unless you untick **Create the ADORE labels in the repository**, creates the missing ADORE labels and lists the result; **Open project** follows. |

For native local execution choose **Runs in → Installed on the server**. Specialized container setups use the advanced server TOML method below.

Choose **Installed on the server** to use ADORE-managed Pi under the current OS account. The optional **Project tools PATH** selects the tool directories. See [Install Pi on the server](/help/executors#installed-executors).

**Automatic location** keeps the proposed clone path. Choose **Custom location** and **Choose folder…** to browse folders on the ADORE host. Click a row to select it; double-click or press Enter to open it. Use Back or Parent folder to navigate, then **Select folder** to confirm the exact existing folder. Enter a new destination directly in the main clone-path field. The selector creates nothing; links and network paths are refused. **Cancel** preserves the draft.

**Target branch** lists the remote branches for GitHub, GitLab and Gitea, including self-hosted repositories. The repository’s default branch is selected and marked **default**. Choose another branch if needed. **Read repository** refreshes the list and keeps an explicit selection while that branch still exists. Changing the URL clears the previous choices. If no default is reported, choose a branch yourself; if the repository has no branches, add one there and read it again. This uses the ADORE account’s Git access; unknown forge types still need manual selection.

## Import project config {#import-project}

Choose **Import project config** on [Projects](/projects) to enroll an existing ADORE `config.toml` exactly as it is, for example one created with the command line or saved earlier with **Download raw configuration** in a project's Settings. The file (UTF-8, up to 512 KiB) needs absolute server paths and no inline secrets: the review lists any it finds, so replace them with environment references first. Its project ID and state folder must not belong to an enrolled project. ADORE copies the file byte for byte and ends with **Enroll with pickup stopped**. History appears only if its data already exists at the declared state folder.

## Clone project config {#clone-project}

Choose **Clone project config** on [Projects](/projects) to start a new project with the working rules of another. **From a project on this server** reads a project you can access; **From a portable settings file** reads a portable JSON file (up to 64 KiB) from the same ADORE version. Only 15 working rules (polling, readiness, recovery, job budgets) are carried; identity, repository, labels, credentials, endpoints, images and history are never copied. Choose **Review source rules**, then **Set up new target** and answer the guided steps. Review unknown files: the checksum detects edits but does not prove authorship.

## After creation {#after-creation}

A new project starts with monitoring stopped. Developers see it once an administrator grants access on its **Access** tab. On the **Summary** tab:

1. Choose **Connect repository**. Enter the forge server address and an access token created on the forge, then **Verify and connect**. This confirms the account and read access to the repository. The token stays on the server, never in the browser. Alternatively, sign in the forge tool under the ADORE service account.
2. Choose **Check host prerequisites**. The details cover Git, the repository command tool, repository sign-in, the container engine, Pi in the image and the AEGIS files, plus the server's ChatGPT sign-in for a ChatGPT subscription, the network proxy image while [internet access](/help/executors#internet) is Off and the web search key when Brave or Tavily needs one. For a project that runs on the server itself, **Local execution** replaces the container engine and image rows: it checks compatible Node, ADORE-managed Pi and the selected provider credential. This is not a full job and does not prove push permission.
3. Run **Test AI connection** in Settings, as described in [Executors and models](/help/executors#test-connection).
4. Choose **Activate monitoring**. The Monitoring tile changes from Paused to Active and ADORE starts picking up tickets that carry the ready label. **Pause monitoring** stops new pickups but does not interrupt a running job.

## Archive, restore and delete {#lifecycle}

Administrators find these buttons on the Summary tab.

- **Archive project** works after jobs finish and queued requests clear. It keeps settings, history, metrics and audit records and stops new work. **Restore project** brings it back.
- **Delete project** appears only for archived projects and asks you to type the project name. It removes the project's ADORE settings, job history, metrics, containers and worktrees. It keeps the repository and its branches, worktrees of jobs handed to a person, a job-state folder outside ADORE home and the audit trail. Deletion is refused while work is queued or unfinished. **Also remove the local clone** (unticked) also deletes the clone ADORE made under its `repos` folder; it is offered only for a clean clone of this project's repository that no other project uses and no worktree kept by the deletion still needs, otherwise the dialog says why the clone stays.

> Deletion cannot be undone. To adjust a project afterwards, see [Project settings](/help/settings).

## Gitea sign-in on this computer {#gitea-sign-in}

ADORE uses the saved project connection first. Otherwise it reuses the current account’s tea configuration. If tea reports a missing login, ADORE checks standard Windows or Linux configuration locations and selects the configured login, a single default, or the only available login. Multiple accounts without a clear selection require an explicit connection.

Discovery respects `XDG_CONFIG_HOME`. On Windows it also checks the account’s Local AppData, Roaming AppData and home `.config` directories; on Linux it checks the home `.config` directory. It does not search private application caches or copy credentials between computers.

1. Open the project’s **Summary** tab and choose **Connect repository**.
2. Enter the Gitea origin, including its port when needed, in **Repository server**.
3. Create a token on that Gitea server for the account allowed to read/update issues and create draft reviews, and enter it in **Access token**.
4. Choose **Verify and connect**. An HTTP server requires the displayed acknowledgement. A failed check preserves the saved connection.
5. Choose **Check host prerequisites** again. Git clone/push credentials are configured separately.

On another computer, prepare that computer’s own CLI sign-in or use this connection form. The delivery archive contains no user tokens.
