# Using ADORE

Applies to **ADORE 0.21.0**.

ADORE takes eligible repository tickets through implementation, checks and human
review, then publishes a PR/MR. Merging remains a human decision.

## Start and sign in

Extract the complete Windows ZIP or Linux TAR.GZ into a folder where programs can
run. Both variants include Python and the web application. The offline archive
also includes Node, Pi, its web extension and search tools without setup downloads.
The online archive needs separately prepared Node/npm and `pi install` for native
execution. Container images are separate archives that an administrator imports
with Docker/Podman before selecting them.

- Windows: double-click **Start-ADORE.cmd**.
- Linux: run **./start-adore.sh** from the extracted folder.

Normal start and stop do not scan all installation files. For a complete integrity
check after extraction or when diagnosing corruption, run **Start-ADORE.cmd --verify**
or **./start-adore.sh --verify** separately; this can take several minutes on Windows.

The browser opens when the application and its worker are ready. The default
address is `http://127.0.0.1:8765/`. A fresh installation starts with **admin** /
**admin**; change the password from **My account**. This pre-release accepts only
its current stored formats. If a store is refused, follow the named manual cleanup
instructions in [Administration](Administrator_Guide.md#fresh-web-database-during-pre-release).

Use **How ADORE works** in the header for the full interface help. It is included
offline in English, French, German and Romanian. These three files provide a
short starting point; the in-app help describes each screen and setting.

## Add a repository

1. Open **Projects → Enroll new project** and enter the repository URL.
2. Choose **Read repository**, then confirm the forge, repository and branch.
   **Target branch** lists remote branches and initially selects the repository's
   default, marked **default**. Choose another branch if needed. Reading again
   refreshes the list and keeps your selection if it still exists. This works with
   GitHub, GitLab, Gitea and Azure DevOps Services, using Git access
   configured for the account running ADORE. If no default is reported, choose a
   branch; if the repository is empty, add a branch there and read it again.
   For Gitea, the tea login is the name of an existing CLI login on the ADORE host.
   Azure cloud projects also require their repository-owned Boards Area Path;
   an administrator prepares Azure CLI and its azure-devops extension.
3. Keep **Automatic location** for the clone. For another destination, choose
   **Custom location** and enter a path or use **Choose folder…**. The selector
   shows folders on the ADORE computer. Click to select, double-click to open,
   then **Select folder** to use the exact existing folder. For a new destination,
   edit the path in the main form; folders are created only when creating the project.
4. In **Agent and model**, choose where Pi runs, its provider, model and
   authentication. Pi is the only executor. **Installed on the server** uses
   ADORE's managed Pi runtime under the service account; offline packages include
   it, while online/source installations require `adore pi install` first.
   Personal Pi settings and sign-in are not used. Container execution needs an
   image prepared on the host. Project tools and networking follow the selected
   execution environment.
5. Set pickup rules, reviewers and limits. Validate the setup, check the
   environment and review the exact project before creating it.
6. Creation leaves monitoring stopped. Review the saved project and its
   prerequisites, then activate monitoring when ready.

Git, a signed-in forge CLI, the managed Pi runtime and project tools belong on the
computer running ADORE. A native local executor uses a new process under the
ADORE account; it does not attach to a terminal session. Linux native execution
also requires administrator-prepared cgroup delegation.

## Work with projects and jobs

- **Summary** shows readiness and project actions.
- **Settings** contains repository, pickup, budget, review and agent settings.
- **Tickets** is a separate page, globally and inside a project. It reads open
  tickets automatically and keeps **Read tickets** for manual refresh.
- **Jobs** shows progress, questions, failures and review requests.
- **Statistics** and **History** provide usage and activity information.

Answer clarification requests and approve the exact candidate when asked.
Pausing monitoring stops new automatic pickup; inspect existing jobs separately.
Use the interface's cancel/retry/cleanup actions when a job needs intervention.
For the latest cancelled job, **Restart job** starts a fresh execution with the
chosen workflow and retains the old activity and conversation. **Previous job**
and **New job** connect the executions. A failed job's **Retry** keeps its work;
**Abandon and restart** discards that failed execution's work after confirmation.

## Stop and update

Stop with **Stop-ADORE.cmd**, **./stop-adore.sh** or Ctrl+C in the launch window.
Before updating, stop ADORE, back up its data and extract the new package into a
new folder. Accounts, projects and history live outside the application folder.
The package-root README lists the data locations and startup options.

- [Administration](Administrator_Guide.md): host prerequisites, credentials and backups.
- [Troubleshooting](Troubleshooting.md): failed checks, startup and recovery.

## Choose how a job works

Before Start or a fresh Restart, choose **With AEGIS** or **Without AEGIS**. Direct implementation works even in a repository with AEGIS installed and preserves its other coding and verification rules. Retry and continuation retain the original job workflow. The Jobs list and details show the saved workflow. An administrator can set **Default workflow** in project Implementation settings; automatic detection is the default.
