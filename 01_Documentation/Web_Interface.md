<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE web interface

The optional web installation serves the React interface and a same-origin
FastAPI API. It uses the same project profiles and run state as the CLI. The
Overview opens **Needs attention** across all projects your account can access,
including archived history. Use **Job scope** for one project. Clarification,
publication approval, draft review, failed/stale jobs and pending handoffs appear
before the current-state counts. Those counts describe the selected scope.
Open a ticket to read what is happening, who acts, where and what follows.

Administrators open Add project from Projects to enroll an existing server clone
through six steps: method, repository/identity, working environment,
eligibility/reviewers/limits, verification, review/create. AEGIS is the repository's
workflow for framing, building, testing and reviewing changes; ADORE conducts that
workflow for eligible issues and publishes only draft MR/PRs for human review.
The clone must already exist at an absolute path on the ADORE server with Git
metadata and its installed AEGIS workflow. Enter the forge's owner/repository
identifier and existing target branch; Gitea can select an existing tea login.
Choose the actual executor, provider/model, installed runtime and local image.
Image/provider choices are explicit values, not an installed-software inventory.
In API-key mode, enter uppercase credential environment names separated by commas;
put their values in the protected server environment or profile .env. Host-auth is
available for OpenCode/Codex only and uses an existing server session.

Choose a human display name separately from the stable profile ID. Ready and
approval labels, forge reviewer usernames and four run limits are reviewed before
creation. Cost limit zero disables that cap and does not imply free execution.
Visible guidance explains units, eligibility and approval. Existing hold/exclude
rules remain applicable.

Validate setup performs local structural validation without external probes.
Check environment is a separate explicit action after its effects are explained:
bounded host tool/auth checks, a disposable container using the existing local image,
and a supported configured local-model probe under the project's egress policy.
AEGIS files are inspected without execution. Failed, partial and unverified
evidence stays explicit with correction and recheck controls. Stopped enrollment
can be created with incomplete verification; check prerequisites before activation.
The review includes exact setup, server configuration/state/worktree paths and
verification status. Confirm submits only the reviewed candidate revision.
Completion states that pickup is stopped; Open project leads to its details.
Activation is a separate administrator action and guarantees no particular issue starts.

Back and review Change retain values. Edits invalidate validation, verification
and review. The draft lives only in browser memory. Leaving via shell, history,
Cancel or sign-out warns about loss; refresh/close uses the browser's own warning.
After refresh the draft is empty. No durable draft endpoint or browser-storage
draft exists. A failed creation is not automatically retried; check Projects for
the chosen ID if its response could not be confirmed, then deliberately review again.

The web worker is the scheduler and executes queued operations through the existing
ADORE CLI. Run one web worker per ADORE home, and do not run a separate
`adore run --loop` scheduler for those projects. The web worker runs one engine
command at a time. During any blocking worker command or project poll it
watches queued cancellations across projects, rechecks the actor's access, and signals the matching conductor
gate.

Secondary text uses contrasting light/dark theme colours. Project metadata,
configuration values, type/domain hints and field help use 0.875rem text with
1.5 line height; long identifiers and guidance wrap within their panels.
On narrow screens, setting labels, values and help stack vertically.

## Start from source

On a development machine, install the optional web dependencies and build the
frontend before starting the two processes:

```text
cd 04_Software
uv sync --extra web --group dev
cd web
npm ci
npm run build
cd ..
uv run --extra web adore-web --home <ADORE_HOME>
uv run --extra web adore-web-worker --home <ADORE_HOME>
```

### Development verification

After `uv sync --extra web --group dev` in `04_Software` and `npm ci` in
`04_Software/web`, provision the test browser once from the web directory:

```text
npx playwright install chromium
npm run validate
```

`npm run validate` runs the Node helper tests, type-checks the UI and browser
tests, builds into `.e2e-dist`, and runs the Chromium E2E suite. The isolated
build carries the project license and bundled notices; it leaves the deployed
`adore/web/static` build intact. `npm run test:e2e` runs the build and browser
portion, and `npm run typecheck` checks TypeScript alone. Run
`npm --prefix 04_Software/web run validate` from the repository root for the
same frontend validation. The configured implementation verification command
uses this route too; running it directly requires no AEGIS task or stages.

The browser suite starts its own API on `127.0.0.1:18765`, refuses to reuse an
existing listener, and creates a temporary `ADORE_HOME`, projects and accounts.
It exercises the real HTTP API and queue worker with injected command runners.
Ticket 42 simulates success and ticket 43 simulates an engine failure; these
requests do not run executors, Git, forge CLIs or containers. Browser requests
outside the test origin are blocked. Dependency and browser downloads are
setup operations; verification then runs offline.

The suite covers sign-in/out, incorrect credentials, admin/developer and
project access, CSRF, configuration staging/applying and stale revisions,
route reload/Back, a 390px viewport and worker success/failure/idempotency.
It uses one worker, no retries, a 30-second per-test timeout and a four-minute
browser-suite limit. The test server has a fixture-only shutdown route so
normal teardown also removes its temporary home on Windows. Forced termination
can leave an `adore-e2e-*` directory in the system temporary directory.

Failures retain screenshots and traces under `web/test-results/`. The HTML
report is under `web/playwright-report/`; from the web directory, inspect it
with `npx playwright show-report`. These outputs, `.e2e-dist`, dependency
directories and TypeScript build metadata are ignored by Git. Chromium is the
initial automated browser target; live forge/container acceptance and
accessibility audits are separate checks.

The API binds to `127.0.0.1:8765` by default. Access it at
`http://127.0.0.1:8765`. A new identity store creates `admin` / `admin` once.
Change that password immediately in Settings. Passwords are stored as Argon2id
hashes, not recoverable ciphertext. An initialized database that is deleted or
corrupt stops startup instead of recreating the default account. Back up both
`web.db` and `web.db.initialized` with the ADORE home and project state.

For remote access, terminate HTTPS at a reverse proxy, keep the API on loopback,
and forward the original scheme securely. Do not expose a plain-HTTP login
listener on a network interface. Browser sessions use HttpOnly, SameSite cookies
and a CSRF token. Five failed login attempts per username and client are blocked
for ten minutes. Administrators create users and assign projects. Developers see
only assigned projects, can start a ready ticket and retry/cancel their runs,
and never receive financial fields. Administrators can pause or resume new
ticket pickup for a project; in-flight work continues. A cancel request is
queued. While the worker runs a blocking command or project poll, it
rechecks access and signals the conductor to stop an active executor gate; the
conductor then performs normal cancellation cleanup. A cancel received while
the conductor is outside an executor gate can still wait for that bounded
operation to finish. If the run completes first,
the worker rejects the late cancel and preserves its completed state.
An operator may use `adore handoff <run-id>` to transfer a run to a human.
Jobs shows pending and completed handoffs. A completed handoff preserves its
worktree, remains in history and cannot be cancelled from the web interface.
Optional `delivery.publish_checkpoints = true` makes owned ticket-branch
progress commits fetchable before approval; draft MR/PR creation still waits
for a fresh candidate-bound human approval. The default is false.
Disabling a user revokes sessions; the last
active administrator cannot be disabled. Administrators can reset an account's
password in Administration; this revokes all of that account's sessions, and
at its next sign-in the account sees only a change-password screen until it
chooses a new password of at least 8 characters. Until then the API answers
other routes with 403 `password_change_required`. There is no email password
recovery.
Administration has separate System status, Users and Change history submenus.
Administrators create and manage accounts in Users and inspect account, project
and operation events in Audit, one page at a time. Developers cannot open these
submenus. Every user's language, theme and password are under My account, a
top-level sidebar entry.


### Change evidence and retention

**Change history** shows who changed what, the recording time and the result.
Filter by the actor ID displayed with the account name, a stable project, exact
change-type action code and UTC period. Blank bounds search all retained time;
**From** includes its instant and **Until** excludes it. Apply filters resets the
page. Counts and 10/25/50/All choices cover the complete matched server history.
**Evidence** expands known before/after values, operation correlation and revisions.
A preparation shows a candidate, with **Prepared** rather than an applied result.
Discard records removal of a durable pending configuration. **Uncertain** means
the host could not confirm completion; inspect/reconcile the actual resource
before attempting recovery. Legacy **Before value not recorded** is unknown,
not an empty value or an inferred difference. Strings or sensitive settings can
be explicitly redacted. Passwords/environment values and raw error text are omitted.

Project **History** combines jobs with change evidence for that immutable project.
Dev receives assigned-project operational changes; administrative account/access,
price and policy events remain Admin-only. Legacy name-only events do not establish
Dev visibility. Revoked or replaced grants cannot expose another project's events.
An empty filter result explains that no changes match; failed reads hide data and
can be retried with **Refresh**. There is no audit download/export action.

In **System status**, administrators set **Audit retention**. Zero/blank means
unlimited; age and stored-text MiB bounds apply independently and remove oldest
visible events. Saving reports actual deletions. The text bound includes structured
evidence and correlations and does not cap the database file on disk. Removing
audit events preserves jobs, run journals, identities, queued operations and replay
receipts. Completed filesystem receipts retain deduplication metadata rather than
before/after values; unresolved attempts retain redacted evidence for host
reconciliation. Retention policy editing requires Admin and CSRF authorization.
Browser-local account/enrollment corrections and abandoned memory drafts do not
change host state. Successful server previews are prepared evidence; publication,
access changes and pickup completion have their own actual results.

### Create a user with reviewed access

In **Users**, enter the username and password, then continue to role and project
access. **Admin** explicitly grants all current and future projects, system
administration and costs. **Dev** grants only the selected projects; labels help
recognition while the displayed stable IDs identify grants. To create Dev with
no project access, deliberately select **Create Dev without project access**.

Review identity and exact access before **Create reviewed account**. The review
omits the password. **Correct identity** and **Correct access** return to your
choices. The draft lives only in this page's memory; navigating away or reloading
clears it. Creation commits account and grants together; a duplicate username,
invalid selection or changed/archived/deleted project rejects the operation
without a partial account. Correct the choice and review again after a rejection.
The result states the account and actual access. Existing password sign-in,
administrator reset, required own-password replacement and disabled-session
behavior continue to apply.

Assigned-project editing under Users and the project's Access tab both show
**Before** and **After** before **Apply reviewed access**, then the actual result.
**Correct access** cancels that review without applying. These remain Admin-only;
Dev direct routes and API calls retain project, administration and cost restrictions.

Every view has its own address, so links can be bookmarked or shared and the
browser's reload, Back and Forward keep your place. Examples:
`/projects/<project-id>/configuration`, `/jobs?project=<project-id>&run=<run-id>`,
`/metrics?project=<project-id>&tab=usage`, `/admin/users` and `/account`. Opening
an address while signed out shows sign-in and then that view. An unknown address
opens Overview; an administrator address opened by a developer opens Overview;
a project you cannot access opens Projects with a "not found" message.
Pages stop refreshing in the background while the browser tab is hidden and
refresh immediately when you return.

For a single-host Ubuntu installation with a preinstalled Nginx, this example
keeps the API private and replaces any client-supplied forwarding headers. Put
the certificate and key on the host before enabling it, and replace the host
name and paths with your internal deployment values:

```nginx
server {
    listen 443 ssl;
    server_name adore.internal.example;
    ssl_certificate /etc/adore/tls/fullchain.pem;
    ssl_certificate_key /etc/adore/tls/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 60s;
    }
}
```

Only the proxy should accept remote connections. Check that a login through
HTTPS returns a `Secure` session cookie and that the API listener remains bound
to loopback. The certificate, DNS entry and Nginx installation are host
prerequisites supplied before offline deployment; the ADORE installer never
fetches them.
A host-specific launcher can instead serve `create_app(ADORE_HOME)` directly
with Uvicorn's SSL certificate and key arguments and `proxy_headers=False`.
Bind only a trusted LAN/VPN address, restrict its firewall port to those
networks, and verify the HTTPS login cookie is `Secure`. The host supplies and
rotates its certificate and key; the offline bundle does not fetch them.
On Jobs, search complete authorized retained history by saved ticket title or
number, project, job ID, lifecycle, stage or outcome. **Job scope** selects one
project; status groups remain visible, while **Advanced filters** offers exact
lifecycle/stage/executor, outcome text and inclusive UTC last-update dates.
Executor matches a case-sensitive saved identity; missing identities do not match.
A changed page revision hides previous results and offers **Reload first page**.

To start an existing ticket, first select its current project. Enter a positive
integer such as `42` for `/issues/42`, without `#` or a URL. The worker applies
existing readiness, ready/hold/exclude and approval gates. Switching scope clears
the ticket draft; archived projects retain history with start hidden.
Retry and Cancel explain their effects and appear only for supported current
states. A queued command is waiting for the worker. Its actual operation result
then shows completed, failed or uncertain; unreadable status leaves completion
unknown. A completed command alone does not establish a successful job or merge.

Statistics places its scope selector with the common reporting period controls.
Changing projects retains the reporting period and category tab. Administrators
start with **All projects**, showing overall Summary totals and a project table.
Selecting one project applies to every category and export, including project
and repository comparison tables. Opening Statistics from project details selects
that project. Developers choose only their assigned projects.
The top bar names the current page and provides common actions. Project details
retains the project opened from Projects. Its Summary, Settings, History and, for
administrators, Prices and Access tabs switch content within the page; Jobs
and Statistics are links to those pages for the project. Access lists every
developer account with whether it can access the project, and an
administrator grants or removes one developer's access with a button; the
change applies at once, leaves the developer's other projects alone and is
audited. Administrators always have access.
Metadata rows have breathing room, with a clear gap before the links. System
status, Users and Audit operate at platform scope and My account at account
scope; a developer's projects can also be managed together on Users. On a phone, wide tables show
an edge shadow where more columns can be scrolled into view. Jobs keeps search
and status visible, with additional controls under Advanced filters;
use Menu to switch pages.

Project names and job ticket numbers are links, so a job opens in Jobs from
any table. When the selected Statistics scope has no jobs yet, Summary, Quality
and Trends show a short message instead of empty cards. Estimated prices start
with the project's own executor selected.

Forms mark required fields with `*` and a legend, example placeholders start
with "e.g." (or the selected language's equivalent), and every field that sets
a password states and enforces the 8-character minimum.
Jobs and tables with more than ten rows offer 10, 25, 50 and All row choices.
Opening a ticket's details shows its timeline as a Date, Event and Stage table.
It starts with ten events per page and offers the same row choices and
Previous/Next navigation for longer histories. The latest recorded events appear
first, and Next moves toward older events. Saved journals retain append order;
opening another ticket starts at the first page. Empty histories show the
explicit unknown-evidence message.
Previous/Next moves between pages when a finite size is selected. All returns
every matching run after project authorization and filtering.
Overview and Jobs start at ten rows and support complete server-side pagination;
continuations use the returned source revision.
Signing out clears cached project, job, account and financial views before a
different user signs in on the same browser tab. The new session starts at
Overview, including when the previous user was on an administrator page.
Language and theme can be chosen on the login page before authentication.
After login, Settings saves each choice to the current account; it follows the
user across browsers. Until an account has a saved value, the browser's saved
choice (or system default) applies. A failed save restores the prior choice.
After upgrading a web identity database from schema 1-3, administrators must
reassign developer project access. Older grants were tied only to profile names;
schema 4 clears them so a replacement profile cannot inherit access.
Schema 6 adds account presentation preferences without changing passwords,
sessions, memberships or prices. Schema 13 adds the reset marker; upgraded
accounts, including `admin`, keep signing in normally.

Error banners show a sentence in the selected language for the API's error
code, followed by any server detail. API error bodies always have the form
`{"detail": {"code": "...", "message": "..."}}`, with `message` optional; see
`05_SoftwareDocu/Component_Web_API.md` for the code contract.

`GET /api/v1/health` reports API process liveness. `GET /api/v1/ready` returns
200 only while the separate control worker has refreshed its heartbeat within
ten seconds; a missing or stale worker returns 503. These endpoints do not
require a browser session and reveal no account or project data. A graceful
worker stop clears readiness immediately; after an abrupt stop it expires within
ten seconds. Schema 5 adds the worker heartbeat without resetting accounts.
Administration shows this control-worker status and refreshes it every five
seconds. Ready means the command worker has a recent heartbeat; it does not
confirm forge, executor, or model connectivity.

## Offline delivery

On a build machine with network access and a Python matching the target OS,
architecture, and Python minor version, build the frontend and run:

```text
python 02_Tools/package_web_offline.py --output 07_Delivery
```

Use `--forge gitea --executor pi --runtime docker` when preparing media for a
host with that combination. The defaults accept any installed supported forge
and executor CLI. The media records these tool requirements alongside Git and
the container runtime.

The resulting `adore-web-<version>-<os>-<arch>-py<version>` directory contains
the application wheel, dependency wheels pinned by `uv.lock`, license,
checksums, installer, and
launcher. `--image <tag>` can include a previously built Docker or Podman image
archive. Copy the directory to the target, where installation uses only local
wheels and `pip --no-index`:

```text
python install.py --target <runtime-directory>
python launch.py --target <runtime-directory> --home <ADORE_HOME>
```

Run `python install.py --check-only` before installation to verify media
checksums and matching host/tool prerequisites without creating a runtime.
When image archives are present, pass `--load-images` to install them before
the Python runtime is created; otherwise their exact tags must already exist
in the selected container runtime.
When building media, `--image TAG` embeds a prepared image archive and
`--require-image TAG` records a preinstalled image prerequisite without copying
its bytes. Both forms make the installer verify the exact tag before it writes
the Python runtime. The latter is suitable for large project images already
supplied offline on the host. With one listed image and a selected `--executor`,
the installer also checks that binary inside the image without network access;
use `--executor-image TAG` to select it when media lists several images.

The combined launcher restarts the API and worker together after an unexpected
exit, up to three times with short increasing delays. Use `--restart-limit 0`
to disable restarts or a value through 10 for a different finite limit. It
exits nonzero after the limit, so a host service manager can alert an operator.
Stop the launcher with Ctrl-C for a graceful shutdown of both children.

The target needs the matching Python with `venv` and `ensurepip` (on Ubuntu,
install `python3-venv` from local installation media first, or supply a Python
distribution that includes it), a suitable
Docker/Podman/WSL runtime, a host forge CLI, repository-local AEGIS,
credentials, and prepared project images. The generic web bundle does not
contain arbitrary project toolchains or model weights. Supply those separately
or preinstall them offline; missing prerequisites are operator setup errors.
The executor CLI belongs inside the selected project image, not on the API
host. Project readiness checks it there without pulling the image.
The installer verifies every bundled file, rejects unlisted files in the media,
and checks `ensurepip`, the recorded host tool groups and any required image
tags before creating the target. When invoked through a
symlinked Python executable, it restarts through that executable's real path
before creating the virtual environment. It performs no Internet
download.
Cloud forges and AI services may still need network access at runtime.

## Manual backup and restore

History is retained indefinitely by default. An administrator can set audit
retention by days, stored audit-text MiB, or both under Administration > Audit;
the boxes show saved limits, with **0** for unlimited. Enter zero or clear a box
to remove that limit. Days must be whole numbers up to 36500; the size supports
fractional MiB up to 1024, rounded to whole bytes. A positive size must represent
at least one byte after rounding. Saving or reopening displays the current policy.
The oldest events are removed first when either bound is exceeded. Unlimited
limits retain audit events indefinitely. The size bound counts UTF-8 audit
payloads, not SQLite file allocation, which may remain larger after pruning.
Accounts, prices, journals and usage are not pruned by these limits. Stop both
the API and web worker before copying or
restoring data so SQLite and run journals form one consistent snapshot. Back up
the entire `ADORE_HOME` directory, including `web.db`,
`web.db.initialized`, profiles, and default project state roots. Also back up
every external `store_root` named in a profile's `profile.json`; retain the
same paths, or update those profile paths as part of a controlled restore.
Protect the copy like a credential backup because it contains password hashes,
sessions, profile configuration, and possibly operational secrets.

To restore, use the same ADORE version, keep both processes stopped, restore
the complete directory into an empty target home plus any external state
roots, and start the API and worker. Verify that the changed administrator
password still works, `admin` / `admin` does not return, profiles and runs are
present, and metrics/prices match the backup. Never restore only `web.db` or
delete the `.initialized` marker to trigger bootstrap. After an upgrade,
restore the matching package alongside its backup; reverse database migrations
are not supported.

## Portable working rules

Administrators can open a project's Settings, read **Export portable settings**,
preview validated active working rules and download a versioned JSON package.
Pending changes and host/identity/access/secrets are excluded; all credential and
endpoint references are omitted. Exact installed source-version compatibility
is required. The checksum detects changes without establishing authenticity.
The parser supplies rules for new projects; this panel provides export.
**Add project** offers portable import/copy, with recognized rules,
independent target setup and mandatory reference reconfirmation. See
[Portable project settings](Portable_Project_Settings.md) for the enumerated
allowlist, source/parser rejection rules, target-host limitations and API.
Exact server TOML enrollment and statistics CSV remain separate formats.

## Project and model setup

An administrator can create a profile in Projects, edit validated scalar
configuration keys in Project details, and use the CLI for other complex settings.
Every project setting lives in that project's own `config.toml`; Project details
> Configuration lists the effective value of each setting and marks it **Set
for this project** (written in the file) or **Default** (ADORE's built-in
value, used because the file does not set it). **Only settings set for this
project** hides the defaults. Each row's visible guidance explains, in the selected
language, what the setting controls, its unit or allowed values and the effect
of changing it (or that it is reserved and not used yet), and shows **ADORE
default** - the value used when the project's file does not set it. Assigned
developers see read-only purpose categories with financial settings and secrets
omitted, plus field types and help. My account contains account preferences and password.
Web-created profiles place worktrees under an absolute, project-specific path
inside ADORE home. For Pi authenticated through an existing ChatGPT
subscription, mount the Pi agent credential directory into the container at
`/home/adore/.pi/agent` using `[container] run_args`, and leave
`[executor] stage_host_auth = false`. Protect the host directory as a secret.
`run_args` is a list, so Project details shows it as **Not editable here**; set
the mount in the project's `config.toml`. An administrator can edit the
profile TOML while pickup is paused or import an existing profile with
absolute paths, then validate and resume it.
Pi's completed JSON turns supply token counts, including cached input tokens.
Its CLI cost number is an estimate and is not presented as billed cost;
administrator price rules can provide a separate estimate. A subscription
therefore still needs iteration and wall-clock limits because a monetary
budget cannot be enforced from a provider charge that is not reported.
To enroll an existing configuration, open **Enroll an existing configuration for
this ADORE server** from Projects. This advanced exact mode uses `config.toml`
from an existing ADORE profile or an operator-prepared `config.example.toml`.
Prepare it for this server before selecting the UTF-8 file (maximum 512 KiB).

1. Select the file. The browser keeps it in memory and preserves its exact bytes,
   including line endings, comments and unknown keys.
2. Declare a stable lowercase project ID and separate display name/description.
   Read declared locations to inspect the server paths; correct paths in the source
   file and select it again. Repository clones already exist on this server.
3. Validate structure and local ownership/state. Every repository, worktree,
   state and metrics path must be absolute, below a volume root; state roots are
   unowned, with no active/corrupt runs or conductor lock.
4. Optionally select Check environment after reading its effects. The server runs
   bounded Git/forge/authentication and disposable local-image container checks;
   a configured model probe may contact its endpoint under the egress policy.
   Repository AEGIS files are inspected. Nothing is published or activated.
   Failed, partial and unverified evidence stays visible; Recheck is explicit.
5. Review identity, config destination, repository/worktree/state/metrics paths,
   resolved physical paths, agent and executor/model/runtime/image/egress plus credential reference names.
   Enroll with pickup stopped confirms that exact candidate. Stale file/identity,
   state/ownership or concurrent lock changes reject confirmation.
6. Completion confirms stopped pickup and offers Open project. Activation is a
   separate administrator action after credentials and environment are ready.

The file alone transfers no historical jobs: completed history is visible only
where underlying data already exists at the declared state location on this
server. Secret values in TOML are rejected; provide values through protected
server environment/profile stores. Corrections show configuration keys and
server locations. Internal Back/Change keeps the draft and invalidates old
checks; changing the disk file requires reselection/revalidation/review.
Cancel, leaving or refresh warns before losing the memory-only draft. Failure
keeps correction available and never displays a successful enrollment.

Config edits include a SHA-256 revision so stale browser pages receive a
conflict. CLI `config set` and web edits also share a local process lock;
concurrent ADORE edits receive a conflict instead of overwriting each other.
Direct host file edits do not use this lock. A start request still applies
ADORE's ready-ticket and hold/exclude rules. The current publication policy
remains: automatic draft MR/PR creation
after the existing `agent-approved` publication gate, with a human deciding
whether to merge.

In Projects, an administrator can archive a project after its jobs have
finished and its queued requests have cleared. Archive preserves the profile,
job history, metrics, estimated prices and audit history. Archived projects
remain readable to assigned users, but the web worker and named/active-profile
CLI pickup stop new work; job controls return after an administrator restores
the project. Archive rejects active or corrupt run state. A standalone CLI
invocation with an explicit `-c` file is outside profile archive control.
An administrator can then delete an archived project from its Projects row:
the confirmation states what is removed and kept and requires typing the
project name. The web worker runs `adore profile delete <name> --force
--remove-resources`, which removes the project's ADORE settings, job history,
metrics, containers and worktrees. The repository and its branches, worktrees
of jobs handed to a person, a state folder outside ADORE home and the audit
trail are kept. Deletion is refused while work is queued or unfinished.
The Projects page lists authorized projects in a sortable table with
10, 25, 50 and All row choices when needed. Administrators can pause or resume
pickup and archive or restore a project directly from its row; all authorized
users can open project details. The table shows configured executor and last
run activity. "Config
valid" means the TOML passed static validation; it does not establish that
forge credentials, containers or the model endpoint are reachable.
Select a project's Details action to see its status and recent jobs, then open that
project's Jobs or Statistics view. Administrators can also jump to Settings and
membership management from the project details.
Administrators can use **Check now** on project details to test the API host's
Git, forge CLI/sign-in, executor CLI inside the project image, AEGIS file
presence and direct
Docker/Podman runtime. For a configured local OpenCode endpoint, the same
action also launches a disposable container using the project image and egress
policy, then checks a streamed tool call against the selected model. The
result names the executor-container context and a redacted failure reason.
The probe requires the image to be present locally and does not execute AEGIS.
Administration > System status also shows free disk space for ADORE's account database and
each project's run-state root. It warns when any measured volume has less than
1 GiB free. A failed measurement is shown as a failed check, not as available
space. This check does not remove data; with indefinite non-audit retention, operators
must size storage and back it up.
Jobs can be filtered by an exact observed executor. Older jobs whose journals
did not record executor identity will not match this filter.
The wider **Observed executor** and **Outcome contains** fields share one row
and stack on narrow screens. Each has Help with examples and matching rules.
Observed executor takes the case-sensitive name recorded in ADORE's job
journal, such as `pi`, `codex`, `opencode` or `qwen` (up to 200 characters).
Outcome contains searches a fragment of ADORE's saved result or error text,
ignoring case (up to 80 characters): examples include `EXECUTOR_TIMEOUT`,
`ticket closed` and `merged by human`. Saved outcomes can include AEGIS error
details; the filter does not search the full AEGIS or executor log. Leave
either field empty to remove that filter.

In Project details > Settings, administrators prepare **one setting at a time**.
The seven collapsible categories are Repository and tickets; Agent and model;
Isolated environment; Rules and approvals; Limits and recovery; Measurement and
notifications; Advanced. Frequent settings appear first within their category.
Each row gives an understandable label, visible purpose/units/consequence guidance,
its **Active value**, **ADORE default**, and **Set for this project** or **Default**
source. **Help** retains the technical key, type, numeric bounds and choices from
server catalog metadata. Lists, tables, launch commands and unsupported sections
are read-only here and are edited in the host's project TOML.

Choose **Edit**, correct the value and choose **Prepare candidate**. This writes
only the pending candidate. Review the affected project, **Active value** and
**Proposed value**, effect, actual preparation time and full base/candidate
revisions under Technical details. The actor is shown as not recorded because
saved candidate records contain no actor. The supported OpenCode endpoint form
prepares its URL/model/connection options together as the existing single edit.
**Copy safe review** copies only the displayed safe values and revision identifiers.
Credential values, inline provider JSON and credential-bearing URLs are redacted.

Choose **Apply change** explicitly to submit both reviewed revisions. The server
checks the exact candidate and stored base, configuration/conductor locks,
nonterminal or corrupt job state and unfinished web operations. Identity/runtime
changes also require pickup stopped. Stop pickup, wait for active work to finish,
then apply; stopping pickup does not interrupt an existing job. A blocked apply
keeps the candidate and explains recovery. Invalid types/ranges or endpoint
credentials/protocol fail closed; correct the edit and prepare again. If active
TOML changed, discard the candidate, refresh and prepare against the new revision.
A failed candidate read disables edits and Apply; refresh or explicitly discard it.
**Discard change** removes only the candidate and preserves the active configuration.
The workflow supports one pending setting per project and keeps existing jobs on
their original configuration. The existing direct API retains its safety checks.

The existing Codex host-auth executor remains suitable for the owner's
ChatGPT-subscription testing where that CLI supports it. A ChatGPT subscription
is not an OpenAI API key or metered API billing source. For OpenCode and an
OpenAI-compatible local server, save the exact `provider/model` ID and its URL
together in Project details. ADORE validates and writes both settings atomically. It
sets `OPENAI_BASE_URL` and OpenCode's `OPENCODE_CONFIG_CONTENT` provider override,
using `@ai-sdk/openai-compatible` and the selected model ID.
An optional `OPENAI_API_KEY` environment reference lets OpenCode resolve an
API key already supplied to the executor; the UI accepts only the variable
name and stores no key value. Existing credential references remain in place
when this field is left at “Keep current.”
The endpoint form fixes the protocol to OpenAI chat completions and sets a
bounded request timeout in OpenCode. For HTTPS with a private CA, enter an
absolute CA-file path **inside the executor image**; ADORE passes it to
OpenCode through `NODE_EXTRA_CA_CERTS` and to the container probe through
`SSL_CERT_FILE`. The file must already be present in that image. The staged
form also accepts an empty CA field to clear a previously configured custom
CA when the endpoint changes.
The staged
review shows the URL, model, protocol, timeout, credential reference and CA
path before Apply. The explicit readiness check tests a streamed tool call
from a disposable executor container; saving syntax alone is not a live test.
The URL must be
reachable **from the executor container**, and its image must already contain
that provider package for offline operation. This follows the
[OpenCode provider](https://opencode.ai/docs/providers/) and
[inline configuration](https://dev.opencode.ai/docs/config/) contracts.
The web editor validates an HTTP(S) URL and the full ADORE config; it does not
test reachability or add cloud fallback. An acceptance probe using OpenCode
1.18.31 in the executor base image completed a streamed request to a local
OpenAI-compatible server on an internal Docker network with no Internet route.
Your deployment still needs a URL reachable from its own executor container.
Other executors and protocols require their own configuration and image preparation.
On Statistics, an administrator can select **Rebuild usage history** to reconcile
retained journal usage and launch coverage into the local SQLite projection.
The per-run cursor records the ingested journal length and digest. Repeating
the action does not add duplicate events or alter jobs; changed or missing journal
evidence returns an error for operator review. Archived projects are included.
When creating a project, ADORE-managed host-auth staging is available only for
OpenCode and Codex. Select the non-staged option for Pi or Qwen. Pi can use the
protected credential mount described above with `stage_host_auth = false`;
ADORE does not copy Pi credentials from the host automatically.

## Navigation and project scope

The primary menu contains **Overview**, **Projects**, **Jobs** and
**Statistics**. **My account** holds language, theme and password preferences.
Administrators also see **System status**, **Users** and **Change history**.
Dev users see only projects granted by an administrator. A Dev with no grants
can use My account and receives guidance to request project access.

The dark navigation panel displays the transparent DDP Engineering company
mark; ADORE is the product name. Use the keyboard **Skip to content** link to
reach page content. On compact screens, **Menu** opens navigation and choosing
a destination closes it.

The project context shows the scoped project's display name and repository.
Its links open that project's hub, Jobs or Statistics. Overview and Jobs default
to **All authorized projects**; Statistics keeps its independent scope and
`/metrics` URLs. A selected job URL includes both immutable project and run IDs,
so colliding run IDs remain distinct after reload. Closing detail clears its ID.

Projects and hub Summary display **Pickup** separately from **Environment
verification**. Stopped pickup prevents new work and allows active jobs to
continue. Verification is explicit and tied to saved configuration revision and
check time: unverified, stale, failed, partial or verified. Invalid configuration
is separate. Summary includes Jobs/Statistics links; Settings remains redacted
read-only for Dev and editable through existing Admin controls. Prices/Access
are Admin-only; History shows terminal project jobs. Existing `/configuration`
and `/prices` addresses remain valid.

Detail leads with exact lifecycle and saved stage, the observed reason and action
location. Saved question/candidate/draft references open the forge. Publication
approval stays candidate-bound and conditional; people decide merge. Completed
means the job completed, even if its saved outcome is arbitrary text. Named
actors, per-job duration and consumption stay unknown in this evidence contract.
The timeline shows only saved events, including stages actually visited on a
quick path. Old recorded activity does not prove executor failure; the separately
shown heartbeat describes the control worker only.

Use **How ADORE works** for delivery vocabulary:

- A **job** is work and verification for one repository issue.
- An **enrolled project** is an existing repository configured on the ADORE host.
- **Pickup stopped** prevents new issues from starting; active jobs continue.
- **Waiting for clarification** needs an answer in the repository issue.
- **Waiting for approval** requires candidate-bound publication approval on the forge.
- **Draft review** makes a draft MR/PR available for people to review; people decide merge.

Guided fields display essential instructions beside the control.
Loading, an empty result and a failed request have distinct presentations.
Failed requests withhold totals; use **Refresh** to retry. Missing measurements
remain unavailable. A successful empty Projects result provides enrollment or
access guidance according to your role.

## Status and metrics

Authenticated API clients can read global jobs through `GET /api/v1/jobs-page`.
Administrators receive all current and archived project history; developers
receive only assigned projects. Add `project_id=<immutable project ID>` to read
one authorized project. Search `q` matches actual project labels, run/ticket IDs,
saved ticket titles, lifecycle, exact stage and outcome. `status_group` accepts
`active`, `waiting`, `review` or `terminal`; exact lifecycle/stage filters are
also available. Attention, exact observed executor, outcome fragment and inclusive
UTC stored-update date filters are supported. `limit` is 1–100 or `all` (default 25); `offset` starts at zero.

The server validates all selected history before reporting complete results.
Counts/groups cover searched jobs before secondary filters;
`total` covers the final filtered set. Order uses the latest persisted state or
journal activity in UTC, missing activity last, then immutable project/run IDs.
Rows retain both IDs, so identical run IDs in different projects remain distinct.
Pass the returned `snapshot` on each subsequent page. A 409
`job_snapshot_changed` means sources or access changed; restart at offset zero.
This revision detects changes optimistically, rather than retaining a frozen
server snapshot. Host writes after final reinspection appear on the next read.

`GET /api/v1/jobs/{project_id}/{run_id}` returns the same safe evidence model.
Saved ticket titles, ticket/MR links, questions and approval references appear
only when available. Stage and lifecycle remain separate. Missing legacy
metadata, timestamps, named responsibility and consumption remain explicitly
unknown. Actual comment/candidate/MR evidence supports the reported next action;
the API never invents a reviewer, question or completed outcome. Corrupt retained
state/ticket/journal evidence returns a typed 503, with no partial totals.
Job reads use local retained snapshots and execute no forge/container/executor
commands. Composite detail additionally carries only saved redacted event/date/stage
fields for the observed timeline. Existing project run API routes remain compatible. See
[the job component contract](../05_SoftwareDocu/Component_Web_Jobs.md) for field
coverage, strict URL validation and source-change semantics.

Statistics keeps shared project, date, timezone and grouping controls above
Summary, Usage, Quality, Trends and Projects. Use **All time** to clear both date bounds; blank dates select All-time;
selected dates apply to every statistic and export. Usage additionally supports
exact executor/model filters; job counts remain independent of those identities.
Unknown values show a dash, measured zero shows 0, source errors show failed
load, and unallocated usage is explicitly counted. Open reviews are current
state. These controls preserve four-language guidance.

Summary starts with jobs started, completed and failed, known input/output/total
tokens, coverage and measured duration samples. Completed includes all terminal
outcomes, and each lifecycle count uses its actual event time. **Current state ·
active now** is separate from interval events. **Not available**, **Measured zero**
and **Partial · known subtotal** distinguish unavailable, observed zero and known
amounts with incomplete coverage. A total requires both known token directions;
known subtotals and observation counts do not assert a complete bill. Reported
cost is observed evidence; estimated cost uses saved executor/model prices and
remains separate. All financial evidence and exports remain Admin-only.

Job consumption shows immutable Project ID and Run ID, lifetime, selected period,
unallocated observations and source. Jobs list/details reuse the reporting dates,
timezone and grouping, with a link back to Statistics. A separate all-time read
retains lifetime evidence outside a selected period; absent period projections
show Not available. The export menu includes **Job consumption** CSV for the
same project/date/timezone/grouping selection. Scope controls are encoded in
Statistics and Jobs URLs for direct links, reload and browser Back.

Trends displays readable lifecycle bars and a captioned accessible table of the
same server rows. Empty periods have explicit empty feedback. Loading, failed,
malformed or incompatible responses withhold numerical presentations and exports;
old responses cannot overwrite a newer selection or removed project access.
**Messages** explicitly says **Not available** while real message collection is
unavailable; executor launches do not supply message counts.

Reporting scope is the authorized immutable project set, a half-open UTC
instant interval `[from,to)`, the selected IANA timezone and day/week/month
granularity. Inclusive date controls resolve each local midnight independently;
the upper bound is midnight after `day_to`, including 23/25-hour DST days.
Omitted bounds are unbounded; both omitted explicitly select `all_time`.
All scoped totals, cards, tables, daily rows, cohorts and exports use this scope.

Started uses the first `picked` event; completed/failed uses the latest event
matching the final lifecycle. Checkpoints and state update times do not supply
these dates. Recorded summary start/end is fallback only without lifecycle
journal evidence. `current_stock` separately names jobs/active/waiting/review/
terminal now, including only actual retained runtime state.

Unique usage is attributed at its own consumption instant. `jobs` uses
`(project_id,run_id)` with separate `lifetime`, `in_period`, `unallocated`,
source and coverage. Historical summaries survive runtime-state removal;
positive summary-only measurements belong to lifetime/unallocated, never a
fabricated period. Missing individual token fields stay null; explicit measured
zero stays zero. Neutral legacy summary defaults are unknown. Legacy missing,
invalid, naive or date-only timestamps contribute unallocated coverage and
amounts. Financial fields and financial coverage are Admin-only in every nested
projection and export. Reported and estimated costs remain separate; matching
immutable prices use the consumption UTC day, and never price reported money
again. Coverage identifies partial evidence rather than asserting a full bill.

Review cohorts use first MR opening/adoption in scope; validation cohorts use
first strict verdict in scope. Human merge uses reviewed jobs with actual done
in scope and `merged by human`. Rework requires reviewer-requested revision;
pipeline repair is separate. Each rate exposes numerator/denominator; empty is
null. Open reviews are labeled current state. Monetary efficiency uses only
period consumption for the completed/human-merged cohort and separate known
reported/estimated samples.

Duration is terminal-summary elapsed wall time including waits, selected by
recorded end instant in scope. Count, sum and sorted exact `samples_seconds`
support pooled mean/median without browser date approximation. Recorded zero
is valid; absent pairs are excluded and inconsistent pairs fail.

Raw state/JSONL and read-only summary rows are validated before filters.
Malformed JSON, duplicate keys, unsupported schema, invalid fields, conflicting
versioned identity/timestamp, numeric overflow and invalid versioned timestamps
fail typed 503 without source rewriting. Invalid scope/identity filters return
422. Analytical summary reads neither initialize nor migrate runtime data.
CSV includes scope/project provenance, empty unavailable cells and spreadsheet
escaping; `X-ADORE-Scope`/`X-ADORE-Coverage` describe empty exports too.
Project `/api/v1/projects/{name}/jobs-usage.csv` and Admin global
`/api/v1/jobs-usage.csv` share usage date/timezone/group/executor/model filters.

Offline proof: `test_web_scoped_metrics.py`, `test_web_metrics.py`,
`test_web_pricing.py`, `web/tests/metrics.test.mjs`, `web/tests/statistics.test.mjs` and
`web/e2e/statistics.spec.ts`, followed by native
Python/Ruff and frontend validation. CLI summary/export semantics are preserved.

Administrators configure immutable exact executor/model input/output USD rates
per million tokens in Settings. Backdated rates may recalculate estimates;
retain an export when a point-in-time estimate is needed. Prices are estimates,
not invoices or spending caps, and follow immutable project identity.

The UI ships English, French, German, and Romanian translations with light,
dark, and system themes. The About dialog displays the runtime version and
bundled license plus notices for locked third-party web dependencies, keeps keyboard focus inside until closed, and restores focus
to About. On narrow screens, the Menu button expands the primary navigation
and a page choice closes it; Sign out remains in the top bar. The worker queue
is durable and idempotent per actor/key;
operations interrupted during a worker stop become `uncertain` for operator
reconciliation rather than being blindly replayed.

## Backend project enrollment and verification

**Add project** offers **Import portable settings** and **Copy project settings**.
Sources supply only the strict 16-rule allowlist. The localized wizard requires
fresh target identity/repository/environment/references, shows source/default/effect
mapping and independently allocated locations, and confirms pickup-stopped
creation. Exact source/candidate revisions, Admin/CSRF, current source authority,
ownership collision checks and rollback/replay guards remain server-enforced.
**Advanced: unchanged server TOML copy** retains host-specific exact-copy behavior.
See [Portable project settings](Portable_Project_Settings.md) for the workflow,
format, exclusions, error recovery and target endpoint setup.


The project API separates the portable profile ID (`name`), immutable identity
(`id`) and human label (`display_name`). Administrators may change only the human
label through `/api/v1/projects/{name}/identity`; paths, access grants, queued
operations and running jobs keep their identity. Existing profiles display their
profile name until a label is saved.

`id-availability` and `setup-preview` are administrator/CSRF-protected POST routes.
They validate locally without probing forge, runtime or models. Availability is
advisory. Preview findings expose `code`, `field` and `remediation`, with no secret
values. Guided creation and exact TOML import publish only after pickup is stopped;
review setup and explicitly verify readiness before the separate start/resume action.
The guided wizard consumes the canonical preview and its additive guarded routes.

The preview exposes a SHA-256 draft revision binding exact generated configuration,
profile ID, display label and description, plus the config-byte revision and canonical
review. Its generated header is deterministic across previews. Supported setup fields
include ready/approval labels, four run budgets and credential environment names.
`POST /api/v1/projects/setup-check` requires the reviewed draft/revision and returns
response-only verification with UTC time, exact config and draft revisions, typed
checks and a redacted model reason. No profile or draft is stored. A changed revision
returns 409 before probing. Gitea authentication uses the selected tea login.
`POST /api/v1/projects/setup-create` rebuilds and compares the reviewed revision,
then uses the existing atomic stopped-publication boundary. Duplicate IDs fail closed.
Both routes require administrator mutation CSRF. Existing guided and TOML API callers
retain their contracts. Draft verification is ephemeral: newly published profiles
still have unverified persisted readiness until their explicit project check.

Project reads report structural `validation`, `pickup_state` and `verification`
independently. Explicit `readiness-check` stores revision/time-bound evidence:
`unverified` means no evidence, `stale` means config bytes changed, `failed` means a
check failed, `partial` includes undetected WSL runtime, and `verified` means the
recorded checks succeeded for that revision. Age alone does not stale evidence;
repeat verification when operational circumstances change. It does not grant approval
or restart jobs. Corrupt readiness evidence fails closed: inspect the host sidecar,
repair/remove invalid evidence and explicitly rerun verification. Keep credentials
in supported environment references or protected mounts; inline secret values,
provider JSON secrets and URL credentials are rejected without echoing them.
