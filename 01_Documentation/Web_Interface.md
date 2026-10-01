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
Projects table; closing a card returns to Recent jobs. The project selector in
the top bar remains available on other pages.

Administrators open Add project from the Projects directory as a separate
page. Every field has a Help disclosure. Local clone path means an absolute
path to an existing Git clone on the ADORE server, not on the browser computer.
Executor image accepts a suggested tag or a custom local tag. Suggestions are
examples, not a live inventory; build or load the image on the server before
running jobs. Save opens the new project's details; Back to projects and Cancel
return to the directory without creating a project.

The web worker is the scheduler and executes queued operations through the existing
ADORE CLI. Run one web worker per ADORE home, and do not run a separate
`adore run --loop` scheduler for those projects. The web worker runs one engine
command at a time. During any blocking worker command or project poll it
watches queued cancellations across projects, rechecks the actor's access, and signals the matching conductor
gate.

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
password in Administration; this revokes all of that account's sessions. There
is no email password recovery.
Administration has separate System status, Users, Audit and Settings submenus.
Administrators create and manage accounts in Users and inspect account, project
and operation events in Audit. Developers cannot open these submenus; their
personal preferences and password remain under My account.

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
Metrics places its project selector with the common reporting period controls;
it scopes the selected-project statistics, usage and project CSV exports.
Changing projects retains the reporting period and category tab. Administrator
global totals and all-project exports retain their global scope.
The top bar names the current page and provides common actions. Project details
and account/administration views also show a project selector there. On a
phone, these controls wrap above the page content; use Menu to switch pages.
Jobs and tables with more than ten rows offer 10, 25, 50 and All row choices.
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
sessions, memberships or prices.

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
the oldest events are removed first when either bound is exceeded. Blank
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
Assigned developers can inspect that project's effective settings in the same
view, with redacted secrets, field types and help. They cannot stage or apply
changes. Administration/Settings contains account preferences and password.
Web-created profiles place worktrees under an absolute, project-specific path
inside ADORE home. For Pi authenticated through an existing ChatGPT
subscription, mount the Pi agent credential directory into the container at
`/home/adore/.pi/agent` using `[container] run_args`, and leave
`[executor] stage_host_auth = false`. Protect the host directory as a secret;
the guided form does not configure this mount. An administrator can edit the
profile TOML while pickup is paused or import an existing profile with
absolute paths, then validate and resume it.
Pi's completed JSON turns supply token counts, including cached input tokens.
Its CLI cost number is an estimate and is not presented as billed cost;
administrator price rules can provide a separate estimate. A subscription
therefore still needs iteration and wall-clock limits because a monetary
budget cannot be enforced from a provider charge that is not reported.
To bring an existing ADORE `config.toml` into the dashboard, open **Import
project** from Projects. It opens a dedicated page with Help for each field.
Choose the file, provide a new project name, review the
forge/repository, runtime, state directory and validation issues, then import.
The copied TOML is byte-for-byte unchanged, including comments and unknown
keys. State, repository, worktree and metrics paths must be absolute, and no
other profile may own the state directory. Existing completed jobs at that
state path remain visible. Import rejects active or corrupt jobs and an active
conductor lock. Pickup starts paused; an administrator resumes it after checking
the imported configuration and supplying credentials. Secret values in TOML
are rejected; `.env` is not imported. Back and Cancel discard the browser's
selected file and preview. After a successful import, Project details opens.
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
The Projects page lists authorized projects in a sortable table with
10, 25, 50 and All row choices when needed. Administrators can pause or resume
pickup and archive or restore a project directly from its row; all authorized
users can open project details. The table shows configured executor and last
run activity. "Config
valid" means the TOML passed static validation; it does not establish that
forge credentials, containers or the model endpoint are reachable.
Select a project's Details action to see its status and recent jobs, then open that
project's Jobs or Metrics view. Administrators can also jump to Settings and
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
The common-setting selector shows current values for repository, forge,
runtime, executor, polling and run limits. Expand **Advanced setting key** for
other scalar settings from the configuration reference.

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
On Metrics, an administrator can select **Rebuild usage history** to reconcile
retained journal usage and launch coverage into the local SQLite projection.
The per-run cursor records the ingested journal length and digest. Repeating
the action does not add duplicate events or alter jobs; changed or missing journal
evidence returns an error for operator review. Archived projects are included.
When creating a project, ADORE-managed host-auth staging is available only for
OpenCode and Codex. Select the non-staged option for Pi or Qwen. Pi can use the
protected credential mount described above with `stage_host_auth = false`;
ADORE does not copy Pi credentials from the host automatically.

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
On Metrics, the reporting period, timezone and day/week/month grouping sit above
the Summary, Usage, Quality, Trends and Projects tabs. The Projects tab is
administrator-only. The **Export CSV** menu in the same area offers selected-project
metrics and usage files, plus administrator-only all-project files. All four
exports use the shared period, timezone and grouping; the usage files also use
the executor and model filters in the Usage tab. The default is UTC and daily
grouping. The date fields limit period tables, trend tables, usage events and CSV
exports to an inclusive period in the selected timezone; week buckets begin on
Monday and month buckets begin on the first. The selected-project period row and administrator global
period row sum only dated journal events. Headline, project/repository, coverage,
and revision-history totals remain all-time. Legacy usage known only from a run
summary may appear in the all-time total without appearing in a period row.
The **Usage by executor and model** tab applies the selected local-date range plus
exact executor/model text filters to dated usage events. It shows event and
token totals by the selected grouping, with unknown identity marked when old journal entries
lack it. The selected-project CSV uses the same filters. Administrators also
see filtered totals for all projects and can export a global CSV with project
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
Metrics use existing terminal run summaries and journal usage events. Executor output may omit
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
