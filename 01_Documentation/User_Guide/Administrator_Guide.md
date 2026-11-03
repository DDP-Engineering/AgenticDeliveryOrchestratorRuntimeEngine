<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Administration

The portable package runs the web application and its worker together. It
includes Python and their dependencies. Repository access and implementation
tools are prepared separately under the OS account running ADORE.

## Prepare the host

Install Git and the CLI for the project's forge: tea for Gitea, gh for GitHub or
glab for GitLab. Authenticate that CLI on the ADORE host using its own login
workflow. For Gitea, keep the saved login name available for project setup.

Reading/cloning a repository uses Git. An SSH repository URL therefore needs
working Git SSH access; the forge CLI login is used separately for tickets,
comments and PR/MR operations. Successful repository reading alone does not prove
forge API authentication.

A desktop launch normally uses the desktop user's account. A service uses its
configured service account. Prepare Git, forge access and the selected execution
environment for that account on the ADORE host.

## Pi installed on the server

As the ADORE service account, install Node.js 22.23.4 or later in the 22.x line
with npm, then run `adore pi install` and `adore pi verify` using the service's
ADORE home. Choose **Installed on the server**, confirm the current account,
and configure the provider and model. Save the project key in **Provider API
key** if required. Set **Project tools PATH** only when the job needs different
tool directories. ADORE starts the pinned Pi installation through its managed
Node executable and ignores the account's personal Pi settings and sign-in.

Windows uses an owned Job Object. On Linux, set `ADORE_LOCAL_CGROUP_ROOT` in
the service environment to a writable delegated cgroup v2 root that supports
`cgroup.kill`. See [Local execution](../Local_Execution.md) for setup and checks.

Project code can access what that OS account permits. Prepare tools, versions,
SDKs and libraries on the execution machine and use an appropriately restricted
account. A Git worktree is not a host sandbox.

## Container executors

Prepare Docker or Podman and an image containing Python, sh, the pinned Pi runtime
and the project tools. ADORE uses a locally available image; missing images are
not pulled automatically. Build and verify project images outside the interface.
The in-app **Executors and models** help contains the image preparation guidance.

Choose the container runtime and image during setup or through the reviewed
**Settings → Agent and model** flow. Check the host prerequisites and use
**Test AI connection** separately when you want to check real model access.
That test contacts the configured provider and may incur usage charges.

## Credentials and accounts

Enter references, not passwords or token values, in ordinary setup fields.
Forge authentication belongs to the forge CLI or the dedicated repository
connection controls. Provider API keys belong in the dedicated provider-key
controls or the documented protected environment configuration. Keep secrets out
of repository files, container images, tickets and copied diagnostic messages.

Change the initial administrator password and create individual web accounts.
Assign developers access only to their intended projects. Web accounts control
interface access; they do not select the OS account used by the executor.

## Data and backups

The default data directory is `%APPDATA%\adore` on Windows and
`$XDG_CONFIG_HOME/adore` (normally `~/.config/adore`) on Linux. `ADORE_HOME` or an
explicit launch `--home` can select another location. Use the same home when
stopping the application.

Before backup or restore, stop both services using the stop wrapper. Copy the
whole data directory, including `web.db`, its initialization marker, profiles
and run state. Include any external project state directories selected in the
configuration. Protect backups as credentials: they can contain sessions,
password hashes and operational secrets.

Restore the whole consistent backup with the matching application version, then
verify accounts, projects and history. Restore the matching package with a
rollback backup; reverse database migrations are not supported. Do not restore
only the database or remove the initialization marker to recreate an admin user.

## Access and advanced commands

The portable launcher listens on loopback. Remote access requires administrator-
managed TLS reverse-proxy deployment; a browser on another computer does not
change where jobs execute. Keep remote deployment and service configuration under
host administration.

For command help, use **ADORE.cmd --help** on Windows or **./adore.sh --help** on
Linux. The package-root README documents launcher arguments. The in-app help
covers normal project operations; the source repository retains the exhaustive
configuration, deployment and CLI references for specialized administration.

[Back to the user guide](README.md) · [Troubleshooting](Troubleshooting.md)
