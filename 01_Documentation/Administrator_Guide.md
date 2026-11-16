# Administration

The portable package runs the web application and its worker together. It
includes Python and their dependencies. Repository access and implementation
tools are prepared separately under the OS account running ADORE.

## Projects and workers

One local supervisor owns independent project workers, a configuration worker
and each project's job pool. The **Active job limit** belongs to the selected
project; two projects set to one can both work at the same time. Project settings
and monitoring stay scoped to that project. Accounts, access, audit retention,
shared ChatGPT sign-in and service administration remain server-wide.

A lower limit holds new starts. Jobs already executing continue; admitted jobs
that have not started wait for the lower limit. Monitoring pause stops automatic
pickup and leaves explicit eligible Start available. Cancel signalling remains
available with a full job pool. Confirm the durable result before repeating an
operation; an uncertain result needs inspection. Use the portable Stop command
to drain the application's owned worker trees. Never remove live ownership files.

## Prepare the host

Install Git and the CLI for the project's forge: tea for Gitea, gh for GitHub or
glab for GitLab, or Azure CLI with the azure-devops extension for Azure DevOps
Services. Authenticate that CLI on the ADORE host using its own login
workflow. For Gitea, keep the saved login name available for project setup.
Azure also needs an explicit organization, project, repository and repository-owned
Boards Area Path. See the Azure DevOps Services guide beside the source manuals
or at the root of the delivery package.

Reading/cloning a repository uses Git. An SSH repository URL therefore needs
working Git SSH access; the forge CLI login is used separately for tickets,
comments and PR/MR operations. Successful repository reading alone does not prove
forge API authentication.

A desktop launch normally uses the desktop user's account. A service uses its
configured service account. Prepare Git, forge access and the selected execution
environment for that account on the ADORE host.

## Pi installed on the server

The Windows/Linux **offline** delivery includes Node 22.23.4, Pi 1.5.2, pi-web-access 0.46.0,
fd and ripgrep. Extract the complete archive; `adore pi verify` checks these
files offline. `adore pi install` verifies the bundled runtime without downloading
or copying it into user data. The smaller **online** delivery and source-checkout installations need
Node.js 22.23.4 or later in the 22.x line with npm, then `adore pi install`
(registry access required) and `adore pi verify` as the service account. Choose **Installed on the server**, confirm the current account,
and configure the provider and model. Save the project key in **Provider API
key** if required. Set **Project tools PATH** only when the job needs different
tool directories. ADORE starts the pinned Pi installation through its managed
Node executable and ignores the account's personal Pi settings and sign-in.

Windows uses an owned Job Object. On Linux, set `ADORE_LOCAL_CGROUP_ROOT` in
the service environment to the absolute path of a writable, delegated cgroup v2
root. Run the service inside that subtree with permission to create child cgroups
and use `cgroup.kill`. Setting the path alone does not grant those permissions.

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

A build accepts only its current stored formats. A refused store names the
database/marker or run directory the operator can delete to start fresh.
Do not reinterpret older data or delete it automatically. Do not restore
only the database or remove the initialization marker to recreate an admin user.

## Fresh web database during pre-release

The web schema identifier remains 1; its table definitions describe only the
current build. There are no migrations, compatibility readers or automatic
resets. A matching identifier does not make an incomplete structure acceptable.

For an explicitly chosen reset, stop both the web and worker services, then
remove `ADORE_HOME/web.db` and `ADORE_HOME/web.db.initialized`. Remove any
`web.db-wal`, `web.db-shm` or `web.db-journal` sidecars only after both services
have stopped. Restart with the same home; the new database uses the current
structure and initial admin/admin sign-in. Web accounts, sessions, permissions,
preferences and command/change history reset. Project profiles, credentials
stored outside the web database, job state and Pi conversations are separate
and remain on disk. Recreate any required web accounts and project grants.

## Storage and retained job history

**Administration → System status** groups storage availability and free capacity
below Workers. Audit retention limits administrative events only; it does not
expire job records or Pi conversations. Cancelling a job releases verified working
resources and keeps recorded evidence. Restarting a cancelled job retains that
history and allocates a fresh execution, so retained data can continue to grow.

Use `adore --profile NAME delete RUN_ID --force` for an explicitly selected old
execution after inspection. It verifies owned-resource cleanup before removing
state. `cleanup` reclaims eligible resources rather than deleting retained job
history. There is no automatic job-history expiry or individual GUI Delete action.

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

## New-job workflow default

In project Settings > Implementation, **Default workflow** selects automatic AEGIS
detection (`auto`) or Direct (`direct`) for new jobs. Manual Start and Restart
allow a per-job choice; Retry keeps the saved workflow. The fixed pre-release
schema and explicit reset procedure are described above.
