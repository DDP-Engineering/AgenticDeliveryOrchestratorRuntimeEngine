<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE web interface

The optional web installation serves the React interface and a same-origin
FastAPI API. It uses the same project profiles and run state as the CLI. The
Overview cards expand to show authorized projects or the selected project's
active, awaiting-review and failed jobs. Select a project from the expanded
Projects table; closing a card returns to Recent jobs. Open another project
from Projects to view its details.

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
It uses one worker, no retries, a 30-second per-test timeout and a three-minute
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
On Jobs, select a project beside the ticket field within the page, then filter
by lifecycle, AEGIS stage, inclusive last-update dates in UTC, or text contained
in the job outcome (ignoring case). Ticket Help explains the existing issue
number from that project's repository: enter a positive integer such as `42`
for `/issues/42`, without `#` or the URL. Switching projects clears the ticket
draft. Archived projects remain selectable for history; Start job is available
on unarchived projects and still applies ready, hold and exclude rules.
Statistics places its scope selector with the common reporting period controls.
Changing projects retains the reporting period and category tab. Administrators
start with **All projects**, showing overall Summary totals and a project table.
Selecting one project applies to every category and export, including project
and repository comparison tables. Opening Statistics from project details selects
that project. Developers choose only their assigned projects.
The top bar names the current page and provides common actions. Project details
retains the project opened from Projects. Its Overview, Configuration and, for
administrators, Prices and Access tabs switch content within the page; Jobs
and Statistics are links to those pages for the project. Access lists every
developer account with whether it can access the project, and an
administrator grants or removes one developer's access with a button; the
change applies at once, leaves the developer's other projects alone and is
audited. Administrators always have access.
Metadata rows have breathing room, with a clear gap before the links. System
status, Users and Audit operate at platform scope and My account at account
scope; a developer's projects can also be managed together on Users. On a phone, wide tables show
an edge shadow where more columns can be scrolled into view, and Jobs collapses
its history filters behind a Filters button that shows how many are active;
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
empty-state message.
Previous/Next moves between pages when a finite size is selected. All returns
every matching run after project authorization and filtering.
The overview shows its seven
most recently updated runs and counts all lifecycle states for that project.
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

## Project and model setup

An administrator can create a profile in Projects, edit validated scalar
configuration keys in Project details, and use the CLI for other complex settings.
Every project setting lives in that project's own `config.toml`; Project details
> Configuration lists the effective value of each setting and marks it **Set
for this project** (written in the file) or **Default** (ADORE's built-in
value, used because the file does not set it). **Only settings set for this
project** hides the defaults. Each row's **Help** explains, in the selected
language, what the setting controls, its unit or allowed values and the effect
of changing it (or that it is reserved and not used yet), and shows **ADORE
default** - the value used when the project's file does not set it. Assigned
developers see the same list, with redacted secrets, field types and help, but
cannot stage or apply changes. My account contains account preferences and password.
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

In Project details, administrator configuration changes are staged for review before
they are applied. Staging leaves the live TOML unchanged. Review the displayed
key, value and revision, then choose Apply or Discard. Apply rejects a stale
revision, active job, conductor lock or unfinished web operation. For project
identity and runtime settings, pause project pickup first, wait for active work
to finish, then apply and resume pickup. A host-side TOML edit made after
staging invalidates the candidate; discard it and stage a new edit. The
existing direct API edit follows the same safety rules. This workflow does not
interrupt a running job or update its effective configuration mid-run.
Administrators edit a setting on its own row: **Edit** opens the current value
(a drop-down for choices and true/false), **Stage change** stages it, and the
Configuration panel below applies or discards it. Common settings - repository,
forge, runtime, image, executor, polling and run limits - come first. A row
notes when applying needs paused pickup and no active jobs. Lists, tables,
executor commands, state and clarification settings show **Not editable here**:
change them in the project's `config.toml` on the ADORE host.

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

The project context shows the selected project's name and repository. Its
links open that project's details, Jobs or Statistics. Overview's enrolled
project count covers all accessible projects, while its job counts cover the
selected project. Jobs always shows the selected project's existing history.
Administrators can select **All projects** within Statistics; the page explains
that scope. Statistics retains its `/metrics` URL and existing deep links,
including its project and category parameters. Jobs retains selected-job deep links.

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

The dashboard shows projects, run status and timeline, token counts, time-zone-aware
activity, and review rounds. Administrators additionally see per-project and
global reported and estimated USD costs and period totals, plus repository-grouped token,
job, reported-cost, and estimated-cost totals. Profiles sharing a non-empty
repository label appear under one repository row; the selected project's
repository also has a combined trend table. Each project's trend table can be
downloaded as CSV; developer exports omit monetary columns. Administrators can
also export global trend rows with project and repository identity.
The Job elapsed time panel shows the number of terminal jobs with valid start
and end timestamps, plus their average and median elapsed seconds. This is
wall-clock time, including waits for human input, and does not claim executor
runtime. Older undated summaries are omitted from the duration sample instead
of being counted as zero. With a date range selected, a second duration
panel includes jobs by their completion day in the selected timezone; its sample may differ from
the daily completion count when timestamps are unavailable.
Daily completed-job trends use the run's terminal journal event. Later recovery
checkpoints do not make an older failed job appear newly completed.
The administrator project table also shows each project's measured-job count
and average elapsed time; its total row sums counts but leaves average blank.
On Statistics, the reporting period, timezone and day/week/month grouping sit above
the Summary, Usage, Quality, Trends and Projects tabs. The Projects tab is
administrator-only. The **Export CSV** menu in the same area offers metrics and
usage files for the selected scope: one project or administrator **All projects**. These
exports use the shared period, timezone and grouping; the usage files also use
the executor and model filters in the Usage tab. The default is UTC and daily
grouping. The date fields limit period tables, trend tables, usage events and CSV
exports to an inclusive period in the selected timezone; week buckets begin on
Monday and month buckets begin on the first. The period row for the selected
scope sums only dated journal events. Headline, project/repository, coverage,
and revision-history totals remain all-time. Legacy usage known only from a run
summary may appear in the all-time total without appearing in a period row.
The **Usage by executor and model** tab applies the selected local-date range plus
exact executor/model text filters to dated usage events. It shows event and
token totals by the selected grouping, with unknown identity marked when old journal entries
lack it. The selected-project CSV uses the same filters. Administrators also
see filtered totals for all projects when All projects is selected, and export a global CSV with project
and repository labels. Developers can inspect their assigned project's usage
and export tokens, but receive no monetary fields. Job counts and headline
totals in Summary are not filtered by executor/model because a run may
have used more than one model, and older run summaries lack that identity.
An unknown reported or estimated cost remains unavailable, rather than zero.
The dashboard and CSV show reviewer-requested MR/PR revisions separately from
automatic repairs after a failed pipeline, both by selected reporting period. The administrator
project view also attributes subsequent token usage, reported cost, and
configured estimates to each revision until the next revision starts. Work
before the first revision stays in the run total; a revision without monetary
evidence shows unavailable cost. Unknown revision triggers appear in an
unclassified coverage count. Journal timestamps with offsets are converted to
the selected timezone before grouping. Review rounds remain a
separate overall run counter; these counts do not imply a human merged the MR/PR.
The **Delivery quality** panel uses all-time journal evidence and displays each
rate with its numerator and eligible-job denominator. Reviewer rework is the
number of jobs with a reviewer-requested revision divided by jobs with a
recorded opened or adopted MR/PR. First validation pass is the number whose
first strict-verification event passed divided by jobs with such an event.
Merged without reviewer revision is the number of human-merged, reviewed jobs
with no reviewer-requested revision divided by human-merged, reviewed jobs.
Pipeline repairs do not count as reviewer requests. Jobs still open after
reaching review have a separate count. An empty denominator displays no rate;
older jobs without the necessary journal evidence are excluded.
Stage failures and operator retries are separate event counts. Administrators
also see reported and estimated USD per completed and human-merged job; each
figure uses only jobs with that kind of monetary evidence and shows its
denominator. The two cost sources are never added together.
In All projects scope, quality rates use the combined eligible-job counts,
and cost-per-job figures use the combined jobs with monetary evidence.
Duration averages and medians are calculated from individual measured jobs.
Choosing one project limits these figures and all breakdown rows to that project.
Administrators can add immutable, effective-dated USD prices per project, executor and exact model
in Settings. Each rate is input/output USD per one million tokens. For a
token-only usage event, the dashboard uses the rate effective on that event's
UTC day; a provider-reported cost for that event is never estimated again.
Reported and estimated costs are separate, and unpriced events remain visible
as a coverage gap. Existing price versions cannot be edited. Adding a backdated
rate can recalculate earlier estimates, so export any estimate you need to
retain as a point-in-time record. Prices are estimates, not billed invoices or
spending caps. Prices follow the project's immutable ID across a profile
rename. Rates whose ownership cannot be proven during a database upgrade remain
stored but do not contribute estimates until the administrator re-enters them.

Missing cost telemetry is shown as unavailable, not zero. Project headline
token and reported-cost totals include live journal events; legacy terminal
summaries supply token totals when their journal has no usable usage event.
Statistics use existing terminal run summaries and journal usage events. Executor output may omit
tokens or cost, and historical runs may lack model identity. Daily charts use
journal event dates; terminal summaries cover completed runs. The current
release has no billing reconciliation.
The Usage coverage panel distinguishes launches with reported token usage,
launches whose token usage is unavailable, and launches with capture disabled.
Administrators also see reported/unavailable cost launch counts. These counts
begin with versioned launch observations; older jobs without them are not
classified. A missing observation is never treated as a zero-token or free job.
New numeric usage records identify their launch so a replayed journal record
does not inflate project, daily, model or terminal-job totals. Conflicting
records stop the affected metrics query with an explicit data error.

The UI ships English, French, German, and Romanian translations with light,
dark, and system themes. The About dialog displays the runtime version and
bundled license plus notices for locked third-party web dependencies, keeps keyboard focus inside until closed, and restores focus
to About. On narrow screens, the Menu button expands the primary navigation
and a page choice closes it; Sign out remains in the top bar. The worker queue
is durable and idempotent per actor/key;
operations interrupted during a worker stop become `uncertain` for operator
reconciliation rather than being blindly replayed.

## Backend project enrollment and verification

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
