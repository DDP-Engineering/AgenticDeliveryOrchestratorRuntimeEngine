<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Troubleshooting

## The interface does not open

Keep the start window visible and read its error. Check `logs/launcher.log` in
the ADORE data directory. The package-root README gives the default data paths.

- An occupied port can be changed with `--port 8766` on the start script.
- Starting the same data home again reuses its existing instance.
- Damaged or incomplete media should be replaced by a fresh complete extraction.
- The data directory must remain writable. The application folder and user data
  are separate; do not copy a live database into a different package folder.

If the browser did not open automatically, open the displayed local address.
Use the stop wrapper before updating or replacing the application.

## Project checks fail

Read each failed check during enrollment or use **Summary → Check host
prerequisites** for a saved project. Correct the prerequisite on the ADORE host
and rerun the check. Unverified means there is no current evidence of success.

| Check | What to verify |
|---|---|
| Git or repository access | Git is installed; the remote URL, SSH key or HTTPS access works under the ADORE OS account. |
| Forge CLI or authentication | The selected tea/gh/glab is available and signed in to the intended server. The Gitea tea login field is a saved login name. |
| Container runtime | The selected Docker/Podman runtime is available to that account and the chosen image already exists locally. |
| Executor | The selected native installation or image contains the agent and required project tools. |
| Local Linux process control | A writable delegated cgroup-v2 root with `cgroup.kill` is configured in Advanced. |
| AEGIS or target branch | The target repository contains its required AEGIS installation and the selected branch exists. |
| Model connection | The model ID, existing executor sign-in or configured provider credentials and endpoint are correct. Use the separate connection test when required. |

## An executor is not detected

Confirm that it is installed for the account shown in **Runs as**, on the ADORE
computer. Choose **Detect installed executors** after correcting installation or
PATH. A process inherits its environment when started; restart ADORE after
changing the host's PATH.

You can open **Advanced** and enter the native executable or full command
manually. On Windows, use the real `.exe` or the installed Node/JavaScript pair.
Detection does not install tools, sign in or test model access. Leave home and
PATH overrides empty unless you intentionally use a prepared custom environment.

## A clone folder cannot be selected

The dialog browses the ADORE host, not the browser computer. Choose an existing
readable directory, or enter a more specific location when the list is limited.
Links, UNC/device paths and mapped Windows network drives are not browsed.

Use one new subfolder name, without path separators, or clear it to use the
selected directory itself. Selection creates nothing. Project creation verifies
the destination and can reuse only a clone of the same repository. Manual path
entry remains available; **Automatic location** restores the proposed destination.

## A job stops or needs help

Open its details and read the recorded failure or requested clarification. Check
the host and saved configuration before using Retry. Approval applies to the
exact displayed candidate; changed work can require fresh review.

Pausing monitoring stops new automatic pickup. Use job actions explicitly to
cancel or release existing work. Keep evidence and worktrees while diagnosing a
failure; avoid editing run-state files or deleting process records by hand.
The in-app job lifecycle help explains each state and its available actions.

## Settings cannot be saved

Brief Windows file locks are retried automatically. If saving still fails, check
file access and choose **Apply change** again. The reviewed change is retained;
avoid editing the active configuration while applying it.

## Before sharing diagnostics

Retain the error, time, project/job identifier and relevant log excerpt. Remove
passwords, tokens and provider credentials. Keep the complete original evidence
and a backup before making recovery changes.

[Back to the user guide](README.md) · [Administration](Administrator_Guide.md)
