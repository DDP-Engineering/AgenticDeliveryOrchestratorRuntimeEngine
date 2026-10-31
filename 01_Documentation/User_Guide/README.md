<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Using ADORE

ADORE takes eligible repository tickets through implementation, checks and human
review, then publishes a PR/MR. Merging remains a human decision.

## Start and sign in

Extract the complete Windows ZIP or Linux TAR.GZ into a folder where programs can
run. Python and the web application are included.

- Windows: double-click **Start-ADORE.cmd**.
- Linux: run **./start-adore.sh** from the extracted folder.

The browser opens when the application and its worker are ready. The default
address is `http://127.0.0.1:8765/`. A fresh installation starts with **admin** /
**admin**; change the password from **My account**. Existing accounts and projects
are reused when you update the package.

Use **How ADORE works** in the header for the full interface help. It is included
offline in English, French, German and Romanian. These three files provide a
short starting point; the in-app help describes each screen and setting.

## Add a repository

1. Open **Projects → Enroll new project** and enter the repository URL.
2. Choose **Read repository**, then confirm the forge, repository and branch.
   **Target branch** lists remote branches and initially selects the repository's
   default, marked **default**. Choose another branch if needed. Reading again
   refreshes the list and keeps your selection if it still exists. This works with
   GitHub, GitLab and Gitea, including self-hosted repositories, using Git access
   configured for the account running ADORE. If no default is reported, choose a
   branch; if the repository is empty, add a branch there and read it again.
   For Gitea, the tea login is the name of an existing CLI login on the ADORE host.
3. Keep **Automatic location** for the clone. For another destination, choose
   **Custom location** and enter a path or use **Choose folder…**. The selector
   shows folders on the ADORE computer. Click to select, double-click to open,
   then **Select folder** to use the exact existing folder. For a new destination,
   edit the path in the main form; folders are created only when creating the project.
4. In **Agent and model**, choose where the executor runs, the agent and model.
   **Installed on the server** detects existing supported installations and shows
   **Runs as**. The current OS account, its home/PATH and saved executor sign-in
   are the defaults. Detection starts automatically; switching agents uses the
   detected list. **Advanced** contains optional re-detection, manual command/path
   and environment settings. Container execution needs an image prepared on the host.
5. Set pickup rules, reviewers and limits. Validate the setup, check the
   environment and review the exact project before creating it.
6. Creation leaves monitoring stopped. Review the saved project and its
   prerequisites, then activate monitoring when ready.

Git, a signed-in forge CLI, the selected executor and project tools belong on the
computer running ADORE. A native local executor uses a new process under the
ADORE account; it does not attach to a terminal session. Linux native execution
also requires administrator-prepared cgroup delegation.

## Work with projects and jobs

- **Summary** shows readiness and project actions.
- **Settings** contains repository, pickup, budget, review and agent settings.
- **Jobs → Tickets** reads open tickets and offers explicit start/retry actions.
- **Jobs** shows progress, questions, failures and review requests.
- **Statistics** and **History** provide usage and activity information.

Answer clarification requests and approve the exact candidate when asked.
Pausing monitoring stops new automatic pickup; inspect existing jobs separately.
Use the interface's cancel/retry/cleanup actions when a job needs intervention.

## Stop and update

Stop with **Stop-ADORE.cmd**, **./stop-adore.sh** or Ctrl+C in the launch window.
Before updating, stop ADORE, back up its data and extract the new package into a
new folder. Accounts, projects and history live outside the application folder.
The package-root README lists the data locations and startup options.

- [Administration](Administrator_Guide.md): host prerequisites, credentials and backups.
- [Troubleshooting](Troubleshooting.md): failed checks, startup and recovery.
