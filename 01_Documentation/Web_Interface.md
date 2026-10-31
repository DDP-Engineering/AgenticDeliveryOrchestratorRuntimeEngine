<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE web interface

Technical details displays Durable job state folder (`state.store_root`), Workflow Python command (`workflow.aegis_python`), Existing local repository path (`worktree.repo_path`) and Job working folders (`worktree.root`) as informational installation values. Operators configure them in the project TOML on the ADORE server; generic web mutations are refused. The localized guidance explains that changing a path does not relocate existing job state, repositories or working folders.

Project Settings follows **Repository → Tickets → Implementation → PR/MR and review → Statistics → Agent and model**, followed by closed **Technical details**. Repository owns platform/author identity and the single integration-branch editor; PR/MR shows its value and a link that opens/focuses that row. Tickets owns eligibility, polling, priority/type and pickup/status labels; hold/exclude affect pickup, not already-started jobs. Implementation owns capacity, budgets and progress commits, with closed Clarifications, Recovery after errors and Advanced stage time limits. Statistics owns recording/token switches and the informational database file inside closed Advanced statistics paths. Technical details and worktree paths are read-only; Repository branch naming uses reviewed edits and a server-checked example; runtime installation and image builds stay external and Agent and model groups executor settings, including where it runs, the container runtime and the image, in Settings. Inactive reserved controls are omitted without changing CLI configuration. All categories start closed, retain reviewed Admin edits and Dev redaction, and have four-locale names.

**Maximum revision rounds** belongs to **PR/MR and review**. Its shared CLI/web default is five; explicit project limits remain effective. **Require ticket acceptance criteria** defaults to false, while priority remains required by default. Supported readiness settings contain no component requirement.

In **Tickets**, **Ready for pickup label** stays in the main list. Six names (answered, clarify, done, failed, review, working) are grouped in **Status labels**, initially closed. A person adds the answered label after a new reply; ADORE manages the other state labels. Expand it for the existing administrator prepare/review/apply workflow; developers see values without edit controls. Names and help are localized in all four languages. Executor-label prefix and ticket-scope hint stay in technical configuration and are omitted from the GUI because they have no runtime effect.

**Exclude from pickup label** in Tickets edits the label name, shown as **Eticheta de excludere de la preluare** in Romanian. Its help explains that label presence blocks pickup, removal restores possible eligibility, and started jobs continue.

**Target branch** in Repository identifies both the starting branch for new jobs and the destination of their PR/MR. The row, editor and candidate review share its localized name (**Ramura de integrare** in Romanian). Use a short remote branch name such as `main`, without `origin/`; existing PR/MR targets remain unchanged.

The optional web installation serves the React interface and a same-origin
FastAPI API. It uses the same project profiles and run state as the CLI. The
Overview opens **Needs attention** across all projects your account can access,
including archived history. One **Project** selector scopes both **Needs attention**
and **Active jobs** from the ADORE/Overview header, followed by the job tables. Activating the primary
**Overview** link resets to all authorized projects; a scoped URL/reload retains
its explicit selection. Automatic job reads run every 15 seconds while visible,
retaining validated current-scope rows while the background response is pending.
A failed or malformed update hides the rows until the next automatic update;
Overview displays no Refresh or refresh timestamp. Compact rows show the job title, project/ticket, observed
status and **Details**. Details opens Jobs with the owning project and run.
The sidebar **Jobs** link retains the selected scope. Worker faults are visible; a healthy
worker needs no banner. Overview reads no consumption and displays no reporting
period, dates or timezone. Jobs holds technical evidence and Statistics owns
reporting filters; displayed timestamps use the browser/device local timezone.

Projects offers administrators three separate actions: **Enroll new project**
(`/projects/new`, the guided wizard), **Import project config** (`/projects/import`,
an existing `config.toml`) and **Clone project config** (`/projects/clone`, the
working rules of a project on this server or of a portable settings file).
Enroll new project starts from the repository URL (https or ssh): **Read repository**
detects the forge (github.com, gitlab.com or a matching server `tea` login), the
repository, the Gitea login and the default branch, derives the project ID from the
repository name and proposes the clone location `<ADORE home>/repos/<project ID>`,
which you can change to another absolute folder (outside ADORE home, where its parent
must already exist, or under its `repos` folder; `~` is not expanded). If the server
stops during a clone, the location reports a running or interrupted clone: remove the
partial folder and its `.<folder>.adore-cloning` marker, then create again. **Continue** stays disabled until the repository has been read.
Nothing is written until creation, which clones the repository there (or reuses a clone
with the same origin), requires the installed AEGIS files and the target branch, and
removes a fresh clone if creation fails. The clone uses the ADORE service account's git
credentials, the same ones publication uses. There is no separate existing-clone mode:
an existing clone is reused when its path is the clone location and its origin matches. The wizard has five steps: repository/identity, agent/model,
eligibility/reviewers/limits, verification, review/create. Review and create lists the
settings left at ADORE's defaults (closed, read-only, grouped like Settings; change them in
Settings after creation) and offers
**Create the ADORE labels in the repository (missing ones only)**, ticked by default:
after creation ADORE reads the repository's labels and creates the missing labels the
project's settings name (lifecycle, hold/exclude, priorities, bug type, approval, revise,
quick-path and task-type labels) with a colour and description, never changing existing
ones, and lists created, existing and failed labels; a failure leaves the project created.
Settings → Repository offers the same as **Create missing labels**. AEGIS is the repository's
workflow for framing, building, testing and reviewing changes; ADORE conducts that
workflow for eligible issues and publishes draft or ready MR/PRs according to `delivery.draft` for human review.
Reviewers are optional: an empty list opens the MR/PR without requesting a review.
Choose the actual executor and provider/model, then **Runs in**: **Container** or
**Installed on the server** (`execution.backend` = `container` or `local`).
For Container, choose the **Container runtime** (Docker or Podman) and the
**Executor image**. The image is free text with suggestions read from the images
present on the ADORE server (administrators only; read-only; `GET /api/v1/executor-images`);
a notice appears when the typed image is not on the server and another when the list
cannot be read. Choosing an executor proposes an image whose tag starts with
`<executor>-` (preferring `adore-executor-base:`), replacing only the old default or
an earlier proposal, never a typed value. For Installed on the server, the step shows
the native executor command and the local account fields (account `current`, home,
PATH, Linux cgroup root) with the local execution notice.
Image/provider choices are explicit values; the image itself is still prepared on the
server by the administrator.
In API-key mode, enter uppercase credential environment names separated by commas,
or leave them empty when the image or the installed executor signs in by itself;
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


The header button **How ADORE works**, beside About (and Refresh where shown), opens
the in-app help center at `/help`: ten topics (what ADORE does, interface tour,
adding a repository, project settings, executors and models, tickets for
automatic pickup, job lifecycle, statistics and costs, administration, glossary)
in your language, each with its own `/help/<topic>` address, a search field and
an On this page outline. A project's Tickets view, the Enroll new project wizard and
project Settings show a **?** link that opens the matching topic in a new tab.
Full job history is reached through the sidebar Jobs link; Overview
keeps job-specific Details links.


Projects labels new-ticket pickup as **Monitoring**, with Active/Paused states.
The directory shows project, repository path, Repo (Gitea/GitHub/GitLab),
Monitoring, jobs and last activity. Open the project to use Summary actions
for pause/activate monitoring and archive/restore;
delete is available for an archived idle project after exact-name confirmation.
Environment verification records explicit checks against the saved configuration
revision; Unverified means no current evidence, not an observed failure. Use
Project details → Summary → Check host prerequisites for the administrator check.
Pause semantics are available in header help instead of repeated row guidance.

### Editing clarification, recovery and stage limits

In Project settings, open **Implementation**, then **Clarifications**, **Recovery after errors** or **Advanced stage time limits**. Choose Edit, enter the typed value and select Prepare candidate. Inspect the active/proposed comparison, then Apply change. Discard change leaves active settings unchanged.

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The six stage rows choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins prepare, inspect active/proposed values and apply only at the existing idle boundary; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

## Branch naming

Repository settings provides **Job branch name template** and **Optional branch name rule**. Administrators edit one field at a time, prepare the validated candidate, review active/proposed values, stop project pickup and apply while no jobs are active. Existing jobs retain their configuration. Developers see the same effective settings and example without edit actions. Worktree paths and runtime setup remain externally managed.

The template generates a name; the optional Python regular expression checks it. For example `feature/{slug}-{iid}` produces `feature/adore-1`, compatible with `^feature/.*$`. Empty rule means no extra naming rule. The repository convention is entered explicitly; ADORE does not fetch it automatically.

The server preview uses the effective agent slug, ticket number `1` and run identifier `sample-run-1`. It refreshes while editing and when reviewing a branch candidate, shows the generated name and rule result, and writes neither configuration nor Git branches. This is one example, not a guarantee for every future identifier. Missing/unsupported variables, invalid Git names or Python regex, mismatch and unavailable/slow checking block preparation; refresh after a stale revision. Allowed fields are `{slug}`, `{iid}` and `{run_id}` without format modifiers; include `{iid}` or `{run_id}`. Template and rule are bounded to 512 characters each; generated examples to 255 characters; regex matching to one second.


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
only assigned projects, can start tickets (including adding the ready and
priority labels), stop tickets and retry/cancel their runs,
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
`delivery.publish_checkpoints` defaults to true in both CLI and web. Owned
ticket-branch progress commits are fetchable before approval; MR/PR creation
still waits for fresh candidate-bound human approval. An explicit false keeps
intermediate checkpoints local. The GUI shows the shared model default and
retains saved project overrides.
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
**Evidence** opens a row below the event with known before/after values and the
operation correlation, plus the base and candidate configuration revisions when a
configuration change recorded them; identifiers show their first 12 characters
(hover for the full value) and the table columns do not move.
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

In **System status**, administrators set **Audit retention**; the current limits
are shown above the prefilled form (Unlimited when no limit is set). Zero/blank means
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
administration and costs. **Dev** grants only the selected projects, listed by name with their forge and
repository path (one checkbox row each, with the unique project name added when
display names repeat); reviews and results add the stable IDs that identify grants. **Assigned projects** on an account opens
the same list below it. To create Dev with
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
The global **Jobs** page starts with one compact **Job scope** selector and the
same **Tickets** (default) and **Jobs** (`view=jobs`) sub-tabs as the project hub;
a job link opens the Jobs sub-tab. With **All projects**, Read tickets reads the
open tickets of every authorized active project into one table with a Project
column; each row's actions act on its project, and a project whose forge read
fails shows its own error. Worker status appears
only when the worker is unavailable or failing. In the job list, search complete
authorized retained history by saved ticket title or number, project, job ID,
lifecycle, stage or outcome; **Status** narrows the list to active, waiting,
in-review or finished jobs; there are no further filters.
A changed page revision hides previous results and offers **Reload first page**.

To start an existing ticket, use **Start** in the Tickets sub-tab, for one
project or for All projects. The worker applies existing readiness, ready/hold/exclude and
approval gates; archived projects retain history with start hidden.
Retry and Cancel explain their effects and appear only for supported current
states. A queued command is waiting for the worker. Its actual operation result
then shows completed, failed or uncertain; unreadable status leaves completion
unknown. A completed command alone does not establish a successful job or merge.

Statistics shows its reporting period in one row: the project selector (on the
global page), From, Through, Group by, **All time** and **Export CSV**. Periods
use UTC; a statistics link may carry another IANA time zone.
Changing projects retains the reporting period and category tab. Administrators
start with **All projects**, showing overall Summary totals and a project table.
Selecting one project applies to every category and export, including project
and repository comparison tables. A project's own Statistics tab in Project
details shows that project without a selector. Developers choose only their
assigned projects.
The top bar names the current page and provides common actions. Project details
retains the project opened from Projects. Its Summary, Settings, Jobs, Statistics,
History and, for administrators, Access tabs switch content within the page. Access lists every
developer account with whether it can access the project, and an
administrator grants or removes one developer's access with a button; the
change applies at once, leaves the developer's other projects alone and is
audited. Administrators always have access.
Metadata rows have breathing room, with a clear gap before the links. System
status, Users and Audit operate at platform scope and My account at account
scope; a developer's projects can also be managed together on Users. On a phone, wide tables show
an edge shadow where more columns can be scrolled into view. Jobs shows search
and status; use Menu to switch pages.

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

Use the complete Windows ZIP or Ubuntu/Linux TAR.GZ from `07_Delivery/`.
Extract it and start `Start-ADORE.cmd` or `./start-adore.sh`. Python, ADORE,
its web dependencies, compiled interface, worker and user guides are included.
No host Python/uv/Node.js or installation step is needed to open the application.
Git, forge authentication, executors, project tooling/images and any model
services remain the configured project's prerequisites.

From a checkout, the build host uses the three repository commands:

```text
python 02_Tools/setup_environment.py
python 02_Tools/create_package.py
python 02_Tools/verify_package.py
```

Use `python3` on Linux if necessary. Build and verify on each matching native
Windows or Ubuntu/Linux x64 host. Setup prepares the source environment;
packaging builds/licenses the frontend automatically and includes a managed
Python with locked dependencies. Verification uses automatically cleaned
temporary data and prints results without retaining logs or reports.
Only the final archives and optional adjacent hashes remain in `07_Delivery/`.
The former separate wheelhouse installation flow is retired.

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

Administrators use **Preview raw configuration** or **Download raw configuration** beside Project settings. Preview opens a closable dialog; download preserves original saved `config.toml` bytes including comments, formatting and inline secrets. Pending changes, resolved defaults, separate `.env` files and external credentials are excluded. Preview is memory-only and cleared on dismissal or project/session change. Developers retain redacted read-only settings and cannot access raw configuration. Candidate review/apply/discard remains inside Settings.

Portable working rules remain available through the transfer API.
**Clone project config** offers both portable sources, with recognized rules,
independent target setup and mandatory reference reconfirmation. See
[Portable project settings](Portable_Project_Settings.md) for the enumerated
allowlist, source/parser rejection rules, target-host limitations and API.
Exact server TOML enrollment and statistics CSV remain separate formats.

## Project and model setup

An administrator can create a profile in Projects, edit validated scalar
configuration keys and the requested reviewer list in Project details, and use the CLI for other complex settings.
**Request review from** is an administrator-editable list with one forge account
per line; leave it empty to request no review. Prepare the change, compare active/proposed
reviewers, then apply it. Requests affect subsequent PR/MR creation and confer
no publication approval or merge permission. Other list settings keep their
individual supported-editing rules.

Every project setting lives in that project's own `config.toml`; Project details
Settings lists effective project values including defaults. Each row's visible guidance explains, in the selected
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
To enroll an existing configuration, open **Import project config** from
Projects. This exact mode uses `config.toml` from an existing ADORE profile, a
file saved earlier with **Download raw configuration** (once no enrolled project
owns its ID or state folder and its inline secrets are replaced with environment
references) or an operator-prepared `config.example.toml`.
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
The local clone is kept too unless you tick **Also remove the local clone** (unticked
by default). The dialog offers it only when it lies under `<ADORE home>/repos` (not through a symlink), is a git clone of the project's repository, is not another project's clone and has no linked worktree that deletion keeps (ADORE's own job worktrees are removed first) and no uncommitted changes;
otherwise it says why the clone stays. Deletion then adds `--remove-clone` and
removes the clone after the profile.
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
Administration > System status shows the control worker and storage as compact
indicators. Storage measures free disk space for ADORE's account database and each
project's run-state root, grouped by physical volume: one line when they share a disk,
a table only when project state roots (`state.store_root`) live on different disks.
It warns when any measured volume has less than 1 GiB free. A failed measurement is shown as a failed check, not as available
space. This check does not remove data; with indefinite non-audit retention, operators
must size storage and back it up.
In Project details > Settings, administrators prepare **one setting at a time**.
The categories are Repository, Tickets, Implementation, PR/MR and review, Statistics, and Agent and model, followed by closed informational Technical details. Frequent settings appear first within their category.
Each row gives an understandable label, visible purpose/units/consequence guidance,
its **Active value** and **ADORE default**; inherited values carry a **Default** badge. Permanent guidance below the label explains each setting; server catalog metadata still constrains edit types, choices and numeric bounds. Supported reviewer/provider-name lists and retry/stage-limit collections use typed reviewed editors; other unsupported sections remain externally configured. Agent and model offers complete reviewed agent selections and launch presets.

The **Durable job state folder** remains visible read-only. The reserved
`state.channel` compatibility value stays in TOML/API metadata and has no web
Settings row; runtime reporting always uses its status comment and lifecycle labels.

Choose **Edit**, correct the value and choose **Prepare candidate**. This writes
only the pending candidate. Pending configuration appears above the settings categories. The main comparison shows changed values only, with adjacent Apply/Discard actions. A candidate with unchanged simple values displays a clear notice and disables Apply; image/plan binding candidates retain their review. Closed Technical details contains the complete safe comparison, effect, preparation time, revisions and Copy safe review. Blocking pause/stale notices remain visible. Object property order is ignored when comparing values; list order is significant. The comparison wraps into labeled value cells on narrow screens. The supported OpenCode endpoint form
prepares its URL/model/connection options together as the existing single edit.
Copy contains all safe compared values and revision identifiers.
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
Every Statistics read reconciles retained journal usage and launch coverage into
the local SQLite projection; administrators can also call
`POST /api/v1/usage/rebuild` to reconcile every project at once.
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

Overview, Jobs and Statistics name their scope through their own **Project**
selector. Overview and Jobs default to **All authorized projects**; Statistics
keeps its independent scope and `/metrics` URLs. A selected job URL includes both immutable project and run IDs,
so colliding run IDs remain distinct after reload. Closing detail clears its ID.

The dedicated project header displays its name and repository path beside
Summary, Settings, Jobs, Statistics, History and Access tabs; Access is
Admin-only. **Jobs** has two sub-tabs. **Tickets** (the default) reads the
project's open tickets from its repository only when you press **Read tickets**,
then lists number, title, labels and whether ADORE can start the ticket (or
which rule blocks it, or its job's state). More than 10 tickets are paged: 10 per
page by default, **Rows per page** 10, 25, 50 or All, the visible range, the page
number of the page count and **Previous**/**Next**; a new read returns to page 1.
**Start** queues a job; when the
ticket lacks the ready label or a priority label, it first asks you to confirm
and to pick a priority, then adds those labels in the repository. A closed, held
or excluded ticket, one without required acceptance criteria, or one that
already has a job cannot be started; **Retry** re-runs a failed job; **Stop** asks for confirmation, cancels the ticket's unfinished
job and removes its ready label so monitoring does not pick it up again;
**Details** shows the description and loads the comments. Ticket text is shown
as plain text. The **Jobs** sub-tab (`?view=jobs`) searches and lists the project's jobs and opens a
job's detail in the same tab (`/projects/<id>/jobs?run=<run_id>`), including jobs
chosen from Summary or History. **Statistics** shows that project's reporting
period, statistics tabs and CSV exports (`/projects/<id>/statistics`). Neither
tab repeats a project selector; worker status appears only when the worker is
unavailable or failing.
Summary holds monitoring actions and revision-bound environment verification.
Paused monitoring prevents new work and allows active jobs to continue.
Verification is explicit and tied to saved configuration revision and check time:
unverified, stale, failed, partial or verified. Invalid configuration is separate.
Settings remains redacted
read-only for Dev and editable through existing Admin controls. Administrators
record estimated token prices under Settings > Agent and model: enter the
effective date and input/output rates, and ADORE records them for the selected
coding agent and its configured model (set the model first when none is
configured). The table below lists the project's prices. Access is Admin-only; History shows terminal project jobs.
`/configuration` is the Settings address; older `/executor` and `/prices`
addresses open Settings.

Detail leads with exact lifecycle and saved stage, the observed reason and action
location. Saved question/candidate/draft references open the forge. Publication
approval stays candidate-bound and conditional; people decide merge. Completed
means the job completed, even if its saved outcome is arbitrary text. Named
actors, per-job duration and consumption stay unknown in this evidence contract.
The timeline shows only saved events, including stages actually visited on a
quick path. Old recorded activity does not prove executor failure; the separately
shown heartbeat describes the control worker only.

The help center's **Glossary** topic (How ADORE works) defines the delivery vocabulary:

- A **job** is work and verification for one repository issue.
- An **enrolled project** is an existing repository configured on the ADORE host.
- **Pickup stopped** prevents new issues from starting; active jobs continue.
- **Waiting for clarification** needs an answer in the repository issue.
- **Waiting for approval** requires candidate-bound publication approval on the forge.
- **Draft review** makes a draft MR/PR available for people to review; people decide merge.

Guided fields display essential instructions beside the control.
Loading, an empty result and a failed request have distinct presentations.
Failed requests withhold totals until the next automatic update. The header
**Refresh** (with the last refresh time) appears only on pages that do not update
themselves: Users, Change history and a project's Settings, Access and History. Missing measurements
remain unavailable. A successful empty Projects result provides enrollment or
access guidance according to your role.

## Status and metrics

Authenticated API clients can read global jobs through `GET /api/v1/jobs-page`.
Administrators receive all current and archived project history; developers
receive only assigned projects. Add `project_id=<immutable project ID>` to read
one authorized project. Search `q` matches actual project labels, run/ticket IDs,
saved ticket titles, lifecycle, exact stage and outcome. `status_group` accepts
`active`, `waiting`, `review` or `terminal`, and `attention=true` selects jobs
awaiting intervention or recovery. `limit` is 1–100 or `all` (default 25); `offset` starts at zero.

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

Statistics keeps shared project, date and grouping controls above
Summary, Usage, Quality and Trends. With **All projects**, each tab ends with one
per-project table for its own data (Summary: job counts and average elapsed;
Usage: consumption and costs; Quality: rework, revisions, repairs and review rounds),
with each repository shown under its project name. Use **All time** to clear both date bounds; blank dates select All-time;
selected dates apply to every statistic and export. Usage shows its totals and
job elapsed time (measured jobs, average, median) as one row of compact values;
click any usage table column heading to sort it, again to reverse; unknown values
stay last. Quality shows delivery quality, administrator cost per job and MR/PR
revision and pipeline repair totals in the same compact form; rates keep their
numerator/denominator, and the daily revision table lists only active days.
Unknown values show a dash, measured zero shows 0, source errors show failed
load, and unallocated usage is explicitly counted. Open reviews are current
state. These controls preserve four-language guidance.

Summary shows only the measure cards: jobs started, completed and failed and
known input/output/total tokens. Completed includes all terminal
outcomes, and each lifecycle count uses its actual event time; jobs active right
now are shown on the project Summary and Overview. **Not available**, **Measured zero**
and **Partial · known subtotal** distinguish unavailable, observed zero and known
amounts with incomplete coverage. A total requires both known token directions;
known subtotals and observation counts do not assert a complete bill. Reported
cost is observed evidence; estimated cost uses saved executor/model prices and
remains separate. All financial evidence and exports remain Admin-only.

Usage adds job elapsed time (measured jobs, average and median elapsed).
Per-job consumption appears in Jobs as lifetime input/output tokens (details add
the total, administrator costs and observation count); Jobs has no reporting
period. The Jobs table shows Ticket, Project, Status, Last activity and
Consumption; click Ticket, Project, Status or Last activity to sort the whole
list on the server (again to reverse). Project and run identifiers appear in job
details. The Statistics export menu includes **Job consumption** CSV for the
same project/date/timezone/grouping selection. Scope controls are encoded in
Statistics and Jobs URLs for direct links, reload and browser Back.

Trends shows usage coverage and undated usage as compact values and one table
with a row per period bucket: started, completed and failed counts carry
proportional bars, and tokens and administrator money show plain values or a
dash. Administrators find unpriced usage events among the Usage totals and
estimated cost per project in Projects. Empty periods have explicit empty feedback. Loading, failed,
malformed or incompatible responses withhold numerical presentations and exports;
old responses cannot overwrite a newer selection or removed project access.

Reporting scope is the authorized immutable project set, a half-open UTC
instant interval `[from,to)`, the reporting IANA timezone (UTC unless the link
supplies one) and day/week/month
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
null. Review still open counts reviews open now, independent of the period. Monetary efficiency uses only
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
dark, and system themes. The About dialog shows the DDP Engineering logo and
the runtime version; License and Third-party notices (for locked web
dependencies) expand only when pressed. What's new lists each release's notes in
your language, newest first, grouped New, Improved and Fixed; the release still
in development appears as In development. The dialog keeps keyboard focus
inside until closed and restores focus to About. On narrow screens, the Menu button expands the primary navigation
and a page choice closes it; Sign out remains in the top bar. The worker queue
is durable and idempotent per actor/key;
operations interrupted during a worker stop become `uncertain` for operator
reconciliation rather than being blindly replayed.

## Backend project enrollment and verification

**Clone project config** offers **From a project on this server** and **From a portable settings file**.
Sources supply only the strict 15-rule allowlist. The localized wizard requires
fresh target identity/repository/environment/references, shows source/default/effect
mapping and independently allocated locations, and confirms pickup-stopped
creation. Exact source/candidate revisions, Admin/CSRF, current source authority,
ownership collision checks and rollback/replay guards remain server-enforced.
**Import project config** retains host-specific exact-copy behavior.
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


Project Summary uses two panels beneath the shared project header. The first
shows separated label/value tiles for Container type, Executor, Monitoring,
environment verification and actual scoped Active jobs, Waiting, Draft review
and Failed jobs counts. Unavailable/corrupt job evidence shows unknown counts
and withholds job rows. The second groups compact Needs attention and Active
jobs tables; Details opens the full scoped job view. Usage/reporting belongs
to Jobs/Statistics. Worker faults stay visible.
Administrator monitoring/archive/restore/delete and Check host prerequisites
buttons live in the information panel. Explicit host-check results appear there.
Explicit host checks retain internally validated check time and configuration revision.
Check host prerequisites opens the details panel immediately and shows Checking while the request runs. Duplicate checks are blocked. Results or localized failure guidance appear inside the panel; Close details hides it without cancelling a running check, and completion respects the closed state. The check button exposes the disclosure state and regains focus on close. Project/account/page changes discard stale responses; project-tab navigation retains current evidence. Model/executor
access evidence appears only inside these details on Summary. There is no separate
connected-model output or overall performed-check banner, keeping the following jobs panel visible. Configuration/time metadata remains internal; configuration changes require fresh evidence. An Admin can configure repository sign-in through Connect repository in Summary,
or externally under the ADORE service account. Browser sign-in is separate.
Git supplies isolated working copies; the repository command tool reads issues and
publishes draft reviews; repository sign-in tests configured host authentication.
The container engine starts isolation; agent availability proves executable presence
in the local image; workflow availability checks the two configured AEGIS files.
A compatible configured OpenCode endpoint receives a temporary-container streamed
model/tool-call check. Current saved explicit model-access evidence is shown for every executor. When no current result exists, model access remains untested. OpenCode endpoint/tool compatibility is identified separately when it was performed. Unknown container detection is incomplete;
any failed check requires intervention with a targeted corrective instruction.
These checks do not prove a complete job, Git push permission or AEGIS execution.
Fresh browser evidence validates the API status contract, selected project identity, revision, UTC
check time, exact check keys/types and consistent model-probe results before display;
invalid results produce a localized error and withhold the new check rows.

Deletion uses a native modal with exact-name confirmation, Escape/cancel,
focus containment and trigger focus restoration; navigation clears intent.
Deletion remains subject to archived/idle project preconditions.


## Project repository connection

Summary → **Connect repository** opens an Admin-only modal token form beside Check host prerequisites for the saved
provider/repository. Enter a server origin and an access token created on that
forge. HTTP requires explicit acknowledgement; GitHub requires HTTPS. Embedded
credentials, paths, queries and fragments reject. The project must be idle,
nonarchived and free of pending configuration/operations. **Verify and connect**
checks account identity and exact repository read access with two eight-second
CLI limits. This does not prove issue-write, draft-review, Git clone/push or
complete-job permissions. Run **Check host prerequisites** for fresh results.

The browser clears its memory-only token on submission, Close, Cancel or Escape and discards it
on project/session/navigation changes. Results contain account/server/repository,
never token. Failed authentication preserves previous credentials; an unconfirmed
request may have reached the server, so inspect readiness before retrying.

The worker and GUI host check use the same isolated CLI binding. Protected
repository-auth.json beside config binds immutable project identity and current
provider/repository/login. Other projects/shared logins remain unchanged. Missing
records preserve external auth; corrupt/stale records fail closed. Reconnect after
provider/repository/login changes. Structured config/portable exports and audit exclude tokens; raw TOML is an explicit Admin-only exception.
executors receive none. POSIX files use 0600; Windows profile ACLs and server-home
backups require service-account restrictions. See Component_Repository_Auth.md.

Proof: tests/test_repository_connection.py, existing readiness tests and
web/e2e/jobs.spec.ts repository-connection journeys with keyboard, four locales,
narrow/dark layout, token clearing and wrong-scope rejection.


## Explicit AI connection test

Administrators use **Settings → Agent and model → Test AI connection** for the configured OpenCode, Pi, Codex or Qwen model. Each explicit click sends one short request in a temporary container and may incur provider charges. The project must be idle with valid saved settings and no pending configuration/operations; its installed image must contain Python and the agent.

Only a valid completed challenge response reports connected. Failures provide redacted guidance for credentials, model availability, image, CLI version or network. The action reuses executor credentials and egress; it starts no job and proves no tool capability. Evidence is durably saved, bound to current project/model/configuration and credential inputs. Summary and host-check details reuse the current access result; endpoint/tool compatibility remains separate. Host-check time/version are internally validated and hidden from Summary/check details. See Component_Model_Connection.md.


## Project setting scope and guidance

Statistics displays **Statistics database file** as an informational row with
four-locale guidance. Server `config.toml` owns `metrics.db_path`,
`metrics.export_jsonl` and `metrics.html_out`; web candidate preparation rejects
all three. JSONL and static HTML paths remain available through TOML/CLI and
are omitted from Project Settings controls. Project/global statistics, usage
and their CSV exports read summaries from the configured database with the
same relative-path semantics as CLI. Missing databases contribute no summaries
and remain absent; malformed configuration or database evidence returns the
existing typed 503 response. Metadata-only profiles retain their state-root
summary history until a configuration file exists. Analytical reads preserve
SQLite bytes, authorization, scope and financial redaction.

PR/MR settings names the CI response **Action when PR/MR CI checks fail**.
Active/default values, option labels and candidate review use **Automatic repair**,
**Notify only** and **Ignore**, localized in English, French, German and Romanian.
The configured values remain `revise`, `notify` and `ignore`. Help explains the
shared revision-round limit and fresh human approval before repair publication.
The read-only Integration branch reference uses the standard responsive setting
row: description and Repository link in the label column, Active value and the
branch in the value column, with the same value typography as other settings.
Its link opens Repository and focuses the single target-branch setting.

Project Settings displays the selected project's operational settings, including inherited defaults. Executor/model/authentication settings and the applicable OpenCode endpoint form belong to Settings → Agent and model. Descriptions remain permanently below each label and provide the editor's accessible description. There is no per-row Help disclosure or override-only filter. The default/source marker describes value origin, not ADORE-wide scope. Polling intervals, per-project concurrency, executor and recovery settings remain per-project within Settings; the backend, container runtime and image are reviewed edits there, while other environment setup is externally managed. Global capacity and audit retention belong to Administration. No project setting is promoted into a global policy by this presentation.

Proof: web/e2e/settings.spec.ts project settings keep defaults and single guidance (administrator/developer), plus existing candidate edit/discard journey.

## Project executor configuration

**Project → Settings → Agent and model** owns the default coding agent, the selected agent's launch command/model, AI connection testing, where the project runs (`execution.backend`), the container runtime and image (plus the local account, home, PATH and cgroup root for local projects) and external container guidance. Its **Authentication** disclosure groups allowed credential variable names, host sign-in reuse and **Provider API keys**. The agent editor offers OpenCode, Pi, Codex and Qwen Code even when their command tables are absent. Selecting an agent loads its saved command/model or the documented command preset; a new model ID must be supplied explicitly. Prepare reviews agent, command and model together, then Apply writes one complete paused/idle candidate. The generic launch-command/model labels follow the selected agent. Edit keeps agent, command and model controls inside their existing description/value rows; the default-agent row owns Prepare/Cancel for the complete draft, beside its dropdown using the shared editor layout and normal responsive wrapping. Grouped-edit guidance stays in the description column. Validation occupies its own line after the controls, keeping selector/actions aligned when the selected agent needs a model; Prepare remains disabled until the complete draft is valid. Credential names are added through a dropdown and remain visible as individually removable selections. Backend, runtime and image edits go only through the reviewed flow (prepare candidate, review, apply); a direct PUT returns 409 `pending_config_required`. While the image row is edited it offers the same server image suggestions. Installed agents and runtime preparation remain external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only credential selector offers known provider names and retained custom names, independently of coding agent. Empty lists support existing server sign-in, including in API-key mode when the image or the installed executor signs in by itself (`env_keys = []`). Applying names does not delete saved `.env` values. Provider API keys offers private Save/Disconnect for known allowed variables and shows sources only; key changes require paused pickup and idle/pending-free state. Explicit Test AI connection remains the evidence of model access and may incur provider charges. Subscription login retains the installed CLI's external service-account workflow. See [Executor configuration](../05_SoftwareDocu/Component_Executor_Configuration.md) for the exact API/storage contracts.

### Transient application notifications

The application shows one dismissible notification for ordinary feedback or the current operation. Operation status replaces the queued confirmation. Pending/running operations stay visible until completion or dismissal; terminal results and ordinary notices disappear after five seconds. Closing the banner keeps worker polling and final project refresh active. Replacement/unmount cancels earlier dismissal timers; persisted outcomes remain available in History. Error alerts retain their existing presentation.

Editable settings place **Edit** beside **Active value** in the value column, including narrow screens. Administrators retain candidate review/apply/discard and disabled-state safeguards; developers have read-only rows.

Project Settings purpose categories are collapsed on entry. Opening a category shows equal-width description and active-value columns separated by24px; below640px they stack at full width. Native disclosures retain keyboard operation. Agent and model groups AI connection, selected-agent settings, closed Authentication and external environment guidance. Its inline field editors retain the existing row columns and stack using the normal mobile layout; the credential-name dropdown and removable selections wrap within the value column.

## Container preparation

Preparation recipes and the other environment settings (`execution.preparation`, `container.uv_cache_volume`, `container.run_args`, egress, SELinux, `worktree.*` roots) are configured externally through the server TOML/CLI; the web refuses them with 400 `environment_managed_externally`. Backend, container runtime, image and the local account keys are reviewed Settings edits. Settings → Agent and model displays the effective container image and external preparation instructions. Host/model checks never execute setup. Job details retain durable preparation outcomes and explicit replay guidance. See [Container preparation](Container_Preparation.md).

## Native local execution

Native execution is selected with **Runs in → Installed on the server** at enrollment or in the reviewed Settings flow, in the server profile, or through server TOML enrollment. Existing native executor/model and explicit host checks use that prepared environment. The container notice is omitted for local projects. See [Local execution](Local_Execution.md) for machine/account, authentication and process ownership.

## Project executor images

Settings → Agent and model shows a compact container notice with the effective image and one expandable instruction disclosure. It identifies standard `executor/Dockerfile`, optional `executor/README.md`, a non-root example, external Docker/Podman build and verification, and the existing profile fields. Only administrators see the actual resolved server `config.toml` path. No controls define or build an image; **Executor image** (enrollment step 2 and Settings) selects one that the administrator prepared on the server. Specialized profiles use server TOML enrollment. Historical records remain readable/exportable/cancellable; old pending candidates can be discarded, and queued image-build requests fail without runtime execution. See [Project executor images](Project_Executor_Images.md).

## Automatic polling cadence

Automatic web polling and CLI `run --loop` use `PollCadence`: after a round
finishes, wait `poll_interval_seconds * multiplier + uniform(0, poll_jitter_seconds)`.
With `poll_backoff = true`, failures double the multiplier from 1 to 2/4/8,
cap at 8, and success resets it to 1. Disabled backoff uses 1. Quiet rounds retain
the multiplier and defer automatic work using the same wait. Quiet windows use
server-local time; explicit web commands remain available.
The web worker keeps independent in-memory cadence/deadlines per immutable
project identity and treats nonzero, timed-out, malformed or exceptional CLI
outcomes as failed checks. Invalid configuration gets a 60-second recheck with
no engine invocation. Restart resets cadence; serial work on another project
may delay a due round. `polling.mode` governs standalone CLI startup; the web
service schedules repeated `run --once` rounds independently of that value.
Project Settings exposes interval, jitter and error backoff controls. Standalone
CLI startup mode is configured in the server TOML; its saved value remains
available in raw configuration and the effective API catalog.

## Installed local executor discovery

Local enrollment and launch-command editing in Agent and model Settings offer
automatic native executor suggestions, manual executable paths and an editable
command. See [Local execution](Local_Execution.md#installed-executor-selection).
The administrator-only `GET /api/v1/local-executors` reads bounded host paths
without launching tools and returns no-store host/account and launch references.

## Simple local setup and clone folders

Native enrollment shows detected installations and **Runs as** automatically.
The current ADORE process account, its home/PATH and existing executor sign-in
are used by default. **Advanced**, initially closed, contains the full command,
manual executable path, home/PATH overrides and Linux delegated cgroup root.
Settings groups local account assertions and environment overrides in Advanced.

After Read repository, **Automatic location** retains the proposed clone path.
**Custom location** enables manual input and **Choose folder…**. This administrator
dialog browses directories on the ADORE host (Windows drives or Linux root), not
the browser computer. Choose an existing directory, or give a new subfolder name;
selection writes nothing. Clear the name to reuse an existing clone. Cancel keeps
the draft, and Automatic location restores the proposed path. Invalid, linked,
UNC/device or unreadable paths fail explicitly; limited lists suggest a typed
location. Clone validation and creation remain at the final reviewed action.

Reviewed configuration apply retries only Windows replace errors 5/32/33, at most six attempts with 50ms between attempts (250ms maximum scheduled delay). Persistent or other OS write failures return `config_write_failed` (HTTP 503), keep the active configuration and pending review, and clean the temporary candidate. Existing state/config locks and revision checks remain in force.

### Compact host folder and executor selection

Custom clone location opens a compact web folder chooser on the ADORE host.
One click selects a row; double-click or Enter opens it. Back, Parent and the
address bar navigate; Select folder confirms the exact existing folder. New
destinations are typed in the main clone-path field. Cancel preserves the draft.
The chooser performs no writes.

Agent and model groups controls in independent columns, stacked on narrow
screens. Native executor discovery starts automatically; changing the agent uses
the detected list. Optional re-detection, manual paths/commands and environment
overrides live under Advanced. Existing manually entered commands remain intact.


During enrollment and Clone project config, **Read repository** reads remote
branches through Git for GitHub, GitLab and Gitea, including self-hosted instances,
using the ADORE account’s existing Git credentials. **Target branch** offers a
dropdown with the repository’s default branch selected and marked. Rereading
refreshes choices and preserves a manually selected branch if it still exists.
Changing the URL or a failed reread clears previous discovery. A remote without
a reported default needs an explicit selection; an empty repository needs a
branch before enrollment can continue. This read does not clone or change the
repository. Forge kind for an unknown self-hosted host still requires selection.


The **Connect repository** dialog closes with **Cancel** beside **Verify and
connect**, or with Escape. Dismissing clears the draft token without submitting.

## Manual Start and monitoring

Jobs > Tickets > Start manually admits only that ticket, including when
Monitoring is Paused. It leaves automatic monitoring paused. Shared eligibility,
capacity, repository workflow, conductor locking and approval checks remain in
effect. Operation feedback names the concrete failed check in the selected
interface language. Invalid or uncertain engine results require host-log
inspection before retrying.

## Agent system package permission

For container projects, Settings > Agent and model includes a reviewed boolean **Allow agent system package installation** (false by default). Admins prepare and apply the change through existing revision/pause/idle guards; developers have read-only access. The setting changes no network option and requires a compatible image and a fresh job. See [Agent dependency installation](Agent_Dependency_Installation.md).
