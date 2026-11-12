<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project profile

Web cancellation requires confirmation and explains attempted runtime/worktree cleanup; worker activity is distinct from its heartbeat. The configurable epic label excludes tickets from pickup and manual Start; eligible manual Start remains available when monitoring is paused.

Installation settings in Technical details are informational and configured in server project TOML. The generic web mutation rule rejects the workflow Python command as well as state/worktree paths; changing paths does not relocate existing data.

Shared CLI/web configuration defaults optional acceptance checking to false and additional revision rounds to five; the typed readiness and portable contracts contain supported fields only.

Implementation settings support reviewed edits for human-answer waiting time (positive integer plus seconds/minutes/hours/days), positive question-round count, a nonempty retry schedule (one nonnegative integer per line), and the complete stage-timeout map. The five stage rows (frame, specify, design, build, validate) choose either the general attempt limit or a positive custom limit in seconds; choosing general removes the override. Retry and timeout collections accept only safe integers and their declared keys; other lists/maps remain read-only except the existing reviewer list. Admins edit several settings, choose Save, confirm important effects and save at the existing idle boundary, with a reviewed budget-only exception for parked-clarification jobs; developers remain read-only. Names, help and controls share four locales. The answer deadline is independent of the reserved reminder; reminder format is still checked and no reminder is sent.

## Purpose and users

ADORE, the Agentic Delivery Orchestrator & Runtime Engine, conducts a team's
opt-in GitHub, GitLab or Gitea tickets. CLI/configured repositories without
`.agentic/aegis.py` use bounded fresh direct implementation attempts and optional
independent verification before human approval; an empty command keeps candidates
explicitly unverified. A present unsupported or
broken payload is refused without fallback. Web enrollment accepts repositories
with or without AEGIS. Guided enrollment and scalar/batch settings APIs accept an
exact optional single-line verification command under existing reviewed revision
and access boundaries; invalid nontext, CR/LF/NUL are refused with field feedback.
Enrollment Verification and Settings Implementation expose the optional command
through one-row textareas, exact domain validation and localized feedback. An
inspected AEGIS enrollment shows the repository-test-command note instead.
API and browser readiness report a separate
read-only workflow observation (AEGIS, Direct or not-inspected) outside prerequisite
checks and stores schema-3 evidence with strict deletion guidance on corruption.
Pending-clone evidence transfers unchanged at creation; the runtime pre-pick probe
remains authoritative. Jobs presentation is unchanged.
In an AEGIS-governed repository it runs one fresh executor session per AEGIS stage inside an
isolated branch/worktree with container or native local execution, verifies the candidate independently,
and publishes a draft or ready MR/PR according to `delivery.draft` after fresh human approval. It never merges. After a human merge, configured remote run-branch cleanup uses an exact commit lease on all three forges.
Administrator settings edit requested reviewers as a reviewed account list. Ready stays visible in Tickets; six status/answer-label names use an initially closed disclosure with reviewed edits, while the inactive scope-hint control is omitted.
Its users are the operator who runs the conductor on a host, the reviewers who
approve and merge on the forge, and the coding executor it launches: Pi,
ADORE's only coding agent.

## Product responsibilities

- `adore/aegis.py` speaks the AEGIS companion CLI over JSON schema 1 and fails
  closed on any contract violation.
- Native Python children use ADORE-owned UTF-8 standard-stream settings; localized
  evidence does not depend on the Windows code page, and corrupt bytes remain refused.
- `adore/orchestrator.py` claims tickets, provisions isolation, supervises
  stages or direct implementation, bounds failures, parks clarifications,
  replays notifications, verifies AEGIS strictly or runs optional direct
  verification with bounded fresh fixes, records explicit unverified evidence
  when no command is configured and publishes draft/ready reviews; `adore/state.py` persists schema-1
  run state, the single-conductor lock and an append-only JSONL journal.
- `adore/forge/` adapts GitLab (`glab`), GitHub (`gh`) and Gitea (`tea`);
  `adore/isolation.py` owns worktrees, checkpoint commits, candidate
  fingerprints and the Docker/Podman lifecycle; `adore/executor/` launches
  Pi in a container as one `pi --mode rpc` process per stage (`pi_rpc.py`)
  and ADORE-managed native Pi through the same RPC protocol.
- `adore/prompts.py` eagerly validates the fixed licensed Markdown catalog in
  `adore/prompts/`; the conductor and Pi launcher share it. Named values are
  inserted once as literal data, headers are excluded and body bytes preserved.
  File/encoding/header/template errors and missing values fail closed with
  file-named `PromptError`. Composition and notice selection remain caller-owned.
- `adore/config.py`, `doctor.py`, `wizard.py`, `profiles.py` and `cli.py`
  provide validated configuration, host readiness probes, assisted setup,
  profile homes and the `adore` command; `metrics.py`, `process_log.py`,
  `identity.py`, `branding.py` and `util.py` provide run statistics, mirrored
  logs, derived resource names, identity constants and shared helpers.
- The optional `adore/web/` API, SQLite identity/operation store and worker
  serve a bundled React dashboard from `04_Software/web/`. The worker uses
  existing CLI/conductor commands; browser roles are admin and project-scoped
  developer, with cost data reserved for admins. Its shared accessible shell
  keeps authorized project context explicit and distinguishes pending, empty
  and failed reads in the supported locales and themes. Overview presents compact
  authorized attention/active tables, one header Project selector and Details navigation;
  its primary link resets all-project scope and polling updates valid rows quietly.
  Unreadable job state produces a warning naming the affected project in Needs
  attention, while verified job rows from other projects remain visible;
  worker faults remain visible, with reporting/technical evidence in dedicated views.
  Settings, Access, global Change history and project History refresh while
  visible. Unsaved settings pause updates. Header Refresh is available on Users.
  Sidebar Jobs supplies scoped full-history navigation.
  Project Settings exports the saved TOML bytes. Projects imports exact TOML
  from a dialog that validates file selection automatically and publishes with stopped pickup.
  Settings → Agent and model has Internet access for the agent (`[executor] internet`, default Off: a container run reaches only the provider's hosts through its per-run proxy; On: open network with Pi's web search and page reading, Exa/Brave/Tavily/none, warned, shown not enforced for local projects).
  The container runtime editor suggests detected native and Windows WSL commands,
  supports manual entry, and uses the existing reviewed Save.
  Settings → Agent and model unifies the Pi provider, model and OpenAI-compatible endpoint (one coherent `executor.connection` member in the settings batch; models from the pinned Pi catalog), launch command, the provider's API key and RPC model testing
  (no agent choice; the native command is fixed); a ChatGPT-subscription project shows the server's one ChatGPT sign-in instead of the key (admin-only Pi OAuth through the selected container or managed native helper, a temporary access token per stage; container and native Windows/Linux runs with stage limits up to 3000 s), with the exact launch preset for container projects through reviewed apply, inline field editors retaining row columns and a names-only credential dropdown with removable selections.
  Settings uses six purpose
  categories and closed informational Technical details, with clarification/recovery/statistics-path topics and one Repository branch editor linked from PR/MR, visible catalog guidance and one Save for all edits with a concise important-effect confirmation with explicit base/candidate binding, idle/lock/pause safety and Dev
  financial/secret redaction. Admin portable export validates active configuration
  and transfers only complete polling/readiness/recovery/budget defaults with exact
  package-version compatibility and a change-detection checksum. Strict parsing
  writes no project state; transfer requires separate target-host setup. Admin raw
  TOML preview/download preserves original inline secrets through a separate
  administrator-only endpoint and memory-only dialog. Admin portable file/copy enrollment binds exact
  authorized source and target revisions, transfers the complete rule allowlist
  into independently owned stopped profiles, and shows localized source/default/
  effect mapping with explicit target reference/environment reconfirmation.
  Source/target corruption, collisions, replay and publication faults fail closed.
  Web enrollment publishes
  complete profiles with pickup stopped, keeps human labels separate from stable
  identity, validates setup offline and records explicit revision-bound readiness.
  Guided enrollment presents six localized steps, keeps corrections only in browser
  memory, returns canonical revision-bound review and runs explicit draft checks. Guarded creation publishes the exact reviewed configuration with pickup stopped and transfers current server-bound check evidence; activation remains separate.
  Exact server TOML enrollment reviews all declared locations and recognized
  agent/runtime settings, keeps corrected drafts in memory and verifies explicitly
  through ephemeral bounded probes. Publication binds unchanged file bytes,
  declared identity and inspected ownership/state with locked reinspection;
  existing terminal history comes from the declared server state location.
  Its additive global job API scans complete authorized current/archived history,
  uses composite project/run identities and optimistic content revisions, and
  exposes actual persisted waiting evidence with explicit usage unknowns.
  Strict read validation preserves the engine's schema-1 recovery contracts.

`python .agentic/aegis.py components` lists the knowledge page that routes
each component to its source and tests.

## Supported operation

One conductor per state root polls in a loop or in externally scheduled single
passes, on Windows 11 through Task Scheduler or on Ubuntu 22+ through systemd.
Run lifecycle states (`working`, parked, awaiting approval, publishing, in
review, terminal) are separate from workflow stage. Workflow is selected from
the pinned worktree before the first claim save and retained on continuation.
The executor's validate session closes an AEGIS task; ADORE verifies that advance
itself. Direct uses build/validate/done with no task bindings: settled changed
work without questions saves completion/validate atomically, then checkpoints
and integrates the target. Configured workflow.verify_command runs independently
through the owned environment under the validate timeout; pass precedes the final
checkpoint/fingerprint. Failures/timeouts count once under max_stage_failures and
route to fresh build sessions with retained sanitized command/exit/output context;
successful fix builds preserve the count. Exhaustion stops VERIFICATION_FAILED;
explicit Retry re-arms it while retaining history/work and cumulative budgets.
Empty configuration records not-configured evidence. Retry can finish completed
validation without another launch; missing completion needs build authority.
AEGIS ignores verify_command and keeps its strict commands and counter resets. Both runs
stay at stage done while awaiting approval, publishing and in review.
A stage receives a bounded
number of failed attempts, questions park the run without consuming that
budget, and required forge notifications pass through a persisted outbox. Parked cleanup is durably settled before polling resumes; status replay reconciles the current lifecycle labels.
Publication requires a fresh `agent-approved` label bound to the exact
candidate fingerprint and target commit; every review round repeats
workflow-appropriate evidence and approval. Direct approval and MR/PR bodies
show the retained agent summary, file count and configured command/result or
explicit unverified notice; adopted and
revised reviews refresh that description without changing review settings.
Summary/questions are excluded from direct progress/checkpoints/publication;
unsafe present artifacts fail closed. Direct summaries never count as a strict
verification pass. Metrics and authorized job reads serialize recorded workflow.
The shared CLI/web default publishes guarded work-in-progress checkpoints to
the owned ticket branch before approval, without opening an MR/PR; an explicit
false keeps intermediate checkpoints local. An operator
can hand a run to a human at a safe boundary; the resulting terminal state
protects the worktree from routine cleanup and further autonomous execution.

## Established constraints

- The CLI runtime is standard-library Python 3.11+ with no runtime dependencies.
  The optional `web` extra adds FastAPI, Uvicorn and Argon2id support.
- ADORE companion version/schema policy is declared in `adore/aegis.py`.
  It never edits the AEGIS payload. ADORE releases use independent Semantic
  Versioning; companion compatibility is verified separately.
- Run state is schema 1 with required aegis/direct workflow and no migration
  from earlier builds; direct task bindings or AEGIS-only stages, state with
  unknown or missing keys, an unknown stage (the removed `deliver` included) or
  corrupt values fails closed with the run directory to delete.
- Executors use the selected container/native backend, never receive forge credentials, and never
  commit, push, open or merge. ADORE owns checkpoints, push and draft creation
  and never merges; `delivery.draft` selects draft (`true`, default) or ready (`false`) creation.
- Secrets live only in the process environment or a gitignored `.env`.
- Version assignment, packaging and delivery are repository operations outside
  AEGIS scope, checked by `02_Tools/internal/check_release_consistency.py`. This
  repository's own `.agentic/` companion does not ship in the runtime bundle.
- Code follows `01_Documentation/Code_Style.md`. Each component keeps a
  contract in `05_SoftwareDocu/` and a page in `.agentic/knowledge/`, updated
  in the same change as the component.

## Implementation orientation

- `04_Software/adore/` is the package; `04_Software/tests/` is the fully
  offline pytest suite, one file per component.
- The web action workspace presents complete authorized attention/history and
  observed next actions; project hubs distinguish pickup from revision-bound
  environment verification. The durable queue owns actual command outcomes.
- `04_Software/web/` is the build-time React source; the packaged static build
  lives in `04_Software/adore/web/static/`.
- `02_Tools/deploy/` holds the host installers and systemd unit;
  `04_Software/docker/` holds the executor base and egress-proxy images.
- `01_Documentation/` is operator documentation, `05_SoftwareDocu/` holds
  component contracts, `02_Tools/` holds release tooling, `07_Delivery/` holds
  final portable archives and optional hashes; `00_Planning/` holds design history.
- `.agentic/requirements/functional/` is the behavior register;
  `.agentic/tasks/` holds task journals.

## Authoritative references

- `README.md` - product summary, current release and repository layout.
- `01_Documentation/README.md` - operator guide index; start with
  `Getting_Started.md` and `Integrating_A_Runtime_Project.md`.
- `01_Documentation/Configuration_Reference.md` and `CLI_Reference.md` - every
  setting and command.
- `01_Documentation/Security_And_Credentials.md` - credential placement and
  the human merge boundary.
- `01_Documentation/Web_Interface.md` - web deployment, roles and metrics.
- `05_SoftwareDocu/README.md` - component contract index.
- `CHANGELOG.md` - release history, including each AEGIS re-verification.

## Ticket body presentation

Tickets descriptions and comments default to React-rendered GFM with literal HTML,
protected absolute HTTP/HTTPS/mailto links, inert image placeholders and read-only
task checkboxes. The Description-side selector applies exact Markdown source or
Rendered mode to every open body. The account preference is read on sign-in/reload;
one optimistic save per session rolls back visibly on failure and ignores stale
account responses. Four-locale controls/help and themed local overflow support
keyboard and narrow-screen reading. Web storage uses only schema 16; another
version is refused with the store files to delete, never migrated. See
knowledge/web-interface.md and Component_Web_Frontend.md.

## Web account access

Admin user creation guides identity/credentials, explicit role/stable project
IDs and secret-free corrective review. One SQLite transaction commits account,
grants and the existing success audit after selected profile reinspection.
Dev zero grants require deliberate acknowledgement; Admin role grants global
project/system/cost access. Compatible account/reset/assignment APIs remain
supported. Account and project grant editors show before/after and actual result;
credential drafts remain transient and clear on success or leaving the page.

## Web reporting scope

Web analytical summaries use the profile-configured statistics database with CLI path semantics; the database file is informational in Settings and JSONL/HTML destinations are server TOML/CLI configuration.

Web analytics resolves inclusive local calendar controls to canonical half-open
UTC instants with explicit all-time. Scoped lifecycle/consumption/quality and
server-selected duration samples share that contract. Current-state stock,
per-job lifetime and unallocated summary-only measurements are separately named;
unknown amounts are null and all financial evidence is Admin-only. Analytical
source reads fail closed and preserve operational persistence/CLI contracts.

The Statistics browser presents canonical scope-bound measures and CSV actions,
explicit all-time versus current stock, honest zero/unknown/partial evidence,
reported versus estimated Admin money, server samples, and labeled trends with
accessible tables. Job list/detail consumption uses immutable project/run
identity and selected-period/lifetime/unallocated measurements. Reporting routes
preserve calendar/timezone/group selections; stale, revoked and malformed reads
hide evidence. Four locales and both themes share these responsibilities.

## Web change evidence

Web mutations record closed redacted actor/time, known stable identity and
before/after/revision evidence. SQLite account/access/queue/policy mutations own
atomic evidence; filesystem attempts retain uncertainty through crashes and use
separate replay receipts for single confirmation. Every audit write carries
structured evidence; a row without it, or corrupt audit storage, fails closed.
Authorized actor/project/action/UTC filters precede server counts/paging; Dev
project history excludes administrative rows. Change history presents
who/what/when/result; System status owns independent audit retention and deletion
impact. Credentials, environment values and raw errors remain excluded.

Admin Project Summary Connect repository provides scoped Gitea/GitHub/GitLab
authentication. See repository-auth.md knowledge and Security_And_Credentials.md.
Protected per-profile tokens are used only by forge CLI commands and explicit
web host checks, with external CLI auth as the missing-record default. Corrupt
or mismatched scoped records fail closed.

Explicit administrator model connectivity uses Pi through a bounded disposable container, or an installed Pi in a disposable native workspace; see knowledge/model-connection.md. Real provider acceptance is operator-triggered and may incur cost.

Project Settings → Agent and model owns the Pi model and launch command settings and approved provider key save/remove; strict durable credential-bound model access evidence is reused inside Summary’s collapsed host-check details. See knowledge/executor-configuration.md. Subscription login of an installed Pi remains the local service account's own flow.

## Reviewed container preparation

`adore/preparation.py` resolves closed exact-Git recipe plans and effective image authority; `adore/execution.py` supplies backend paths/environment, bound commands and owned container lifecycle. Preparation runs in the normal pinned worktree/container before AEGIS/AI, with bounded redacted immutable evidence and explicit capped replay. Optional recipe execution state in schema 1 verifies resource/image/policy identity on reuse. Profiles without recipes or enabled package permission retain existing profile-update/recovery behavior and empty execution records. CLI reviews external preparation plans; GUI shows the effective image and saved run evidence. Host/model probes never execute setup.

## Native local execution

LocalBackend and owned Windows Job/Linux delegated cgroup scopes share the existing
conductor. Actual machine/account, non-secret environment and installed executable
identity are pinned. Tools and auth remain operator-owned; worktrees are not host
sandboxes. Configured direct verification alone permits an exact owned platform
shell operation (Windows cmd from bound SystemRoot, Linux /bin/sh), with the
service account's permissions and no container isolation. Ordinary native argv
shell refusal remains. Verification keeps bounded sanitized true trailing output
and confirms owned cleanup on success, failure and timeout. The installed Pi uses the account's existing sign-in at
`$PI_CODING_AGENT_DIR/auth.json` (default `~/.pi/agent/auth.json`) or approved
provider keys. See knowledge/local-execution.md and 01_Documentation/Local_Execution.md.

## Project executor images

Settings → Agent and model shows a compact container notice with the effective image and one expandable instruction disclosure. It identifies standard `executor/Dockerfile`, optional `executor/README.md`, a non-root example, external Docker/Podman build and verification, and the existing profile fields. Only administrators see the actual resolved server `config.toml` path. No controls define or build an image. Enrollment step 2 and Settings → Agent and model let administrators choose Runs in (Container or Installed on the server), Container runtime and Executor image (suggestions from the images on the server, `GET /api/v1/executor-images`) and the local account fields, through the reviewed configuration flow in Settings; the administrator still prepares the image on the server. Other environment keys stay external; specialized profiles use server TOML enrollment. ADORE has no image-build subsystem; its former routes answer 404. A pending candidate with an `image_build` binding or for an operator-owned key, which only an earlier build could stage, is 503 `pending_config_corrupt` on view and apply and can only be discarded. See [Project executor images](../../01_Documentation/Project_Executor_Images.md).

AEGIS owns backward stage routing within the selected full/quick path. The
conductor saves accepted stages before checkpoints, continues with fresh bounded
sessions and preserves typed checkpoint failures at the observed stage. Jobs
uses this durable state; see knowledge/orchestrator.md and aegis-client.md.

## Job branch naming

Repository settings uses administrator-reviewed branch template/rule edits with a revision-bound fixed example. Shared CLI/web Python validation rejects malformed formatting, invalid Git samples and incompatible or unevaluable rules; scoped developers can preview without write authority. Runtime paths remain external. See Configuration_Reference.md and knowledge/config.md.

Local enrollment and Agent and model command editing detect installed native
executors and known npm entrypoints on the actual Windows/Linux ADORE host,
with explicit manual executable paths. Discovery reads files without executing
CLIs; existing auth/model checks and native isolation remain separate. See
`01_Documentation/Local_Execution.md` and knowledge/executor-discovery.md.

Native enrollment uses a read-only detected account with automatic home/PATH.
Full commands and environment overrides stay under Advanced. Clone destinations
have automatic/custom selection and an administrator host folder navigator;
selection is read-only and actual clone publication retains its existing checks.
See knowledge/host-folders.md and 01_Documentation/Web_Interface.md.

Reviewed web configuration saves preserve the active file and pending review on write errors; brief Windows replacement contention uses six attempts with at most 250ms total scheduled delay and explicit localized failure.

The clone folder chooser uses compact selectable directory rows, address/Back/Parent
navigation and exact existing-folder confirmation. A listing preserves edits to
the address made while it loads. New destinations remain editable in the main
form. Agent and model uses independent field columns. Local executor
discovery is automatic, with optional re-detection under closed Advanced controls.


Repository enrollment reads remote branches and symbolic HEAD through Git for
all supported forge types, including self-hosted addresses. Target branch uses
a remote dropdown with the default marked and initially selected; explicit
selection survives rereads while it exists. Empty or unknown defaults require
clear user action. See Component_Repository_Source.md.

Manual ticket Start admits only the selected eligible ticket while retaining
paused automatic monitoring. Existing capacity, workflow, lock and approval
gates remain active. CLI terminal evidence binds the requested IID, exit code
and closed reason; the worker persists safe outcomes and the interface renders
localized explanations. See Component_Orchestrator.md, Component_CLI.md and
Component_Web_Worker.md.

Automated host/native commands use child-only pager defaults and Windows
CREATE_NO_WINDOW. Container exec forwards the same pager defaults to executor
children. Output/status/timeout and native Job/cgroup ownership stay authoritative;
see util.md, local-execution.md and isolation.md knowledge.

Gitea external authentication recovers exact pre-HTTP missing-login errors through
bounded metadata discovery in standard Windows/Linux account configuration roots.
Protected project connections and explicit XDG retain priority. Closed failures
lead to four-locale Connect repository guidance; see repository-auth.md.

Native host checks measure Pi prerequisites for the service account. Current readiness stores only closed prerequisite booleans; the separate bound model-connection evidence provides the concrete Pi provider/tool failure in Summary. Container Pi runs through RPC; native Pi uses the nonce-based shell challenge and file protocol.

Windows native supervisors explicitly forward both captured streams when using
CREATE_NO_WINDOW. Version and model checks consume the same bounded parent-owned
pipes; successful exit alone does not fabricate version or model evidence.


Explicit native Retry revalidates inherited environment and installed executable
identity on the same host/account for every supported executor/job, retaining
progress and cumulative budgets. CLI returns failure for immediate failed rearming;
web operations display the saved terminal cause with bound run/exit evidence.


The installed AEGIS companion contract is covered by captured CLI replay in
test_aegis_compatibility.py, including refusal of the older captured release.
Every stage prompt names the installed journal authoring guide and preserves
task identity, legal content and history through the companion CLI writers.
Companion updates do not renumber ADORE or replace project payloads.

## Agent-controlled container packages

Explicit container.system_packages enables direct noninteractive package-manager sudo by the normal agent, independent of egress. The conductor pins authority and resource IDs even without recipes and preserves existing stage limits and forge boundaries. Settings reviews the separate boolean; false preserves legacy authority. See knowledge/package-permissions.md and 01_Documentation/Agent_Dependency_Installation.md.


## Container Git context

Fresh repository containers use a read-only container-native Git pointer while
the host keeps its own pointer. Git selects independent and nested repositories
normally; managed repository-selection environment fields are provisioning
metadata. Warm containers preserve their creation-time binding and installed
contents. WSL container commands use direct argument execution; custom wrappers
identify their command boundary explicitly. See knowledge/isolation.md and
01_Documentation/Operations_Guide.md for ownership and recovery contracts.

## Container timeout recovery

Shared container commands address observed immutable IDs. Actual timeouts require
verified same-resource interruption before output retention, with deferred verified
restart at the next command/provision. Dependencies/files/user/egress are retained.
Unconfirmed recovery blocks active admission and becomes terminal infrastructure
failure; cancellation and explicit owned release keep authority. No new runtime
package or state schema is required. See knowledge/execution.md and Operations_Guide.

## Confirmed recovery after drift

Failed-job abandonment uses confirmed state revisions, verified owned native/container/worktree cleanup and leased remote-branch deletion before normal manual admission with monitoring pause preserved. Explicit native cleanup uses saved ownership without resolving current tools; ordinary execution/Retry identity checks remain strict. Proof: tests/test_drift_recovery.py and web/e2e/driftRecovery.spec.ts. No stored schema changes or live resource acceptance are required.

Previously orphaned unproven refs are preserved through bounded fresh branch generations, with actual naming-rule checks and atomic initial local ref creation. Verified own branches remain reusable; known changed checkpoints refuse before cleanup.


## Budget boundaries and accumulated work

CLI/web enrollment default to 20 launches. The conductor rereads budgets before
provision and each executor attempt, pinning parsed/resolved non-budget settings
without rerunning startup probes; missing/corrupt/unknown/drifted source fails
BUDGET_CONFIG_INVALID. A current launch retains its timeout. The effective active
clock anchor shifts over inactive intervals, retaining all consumed work on retry,
clarification resume and revisions. No new stored fields or schema are required.
Admin reviewed budget-only saves permit parked jobs under existing lock, revision,
state-root and operation guards. Job details shows current limits with launches,
active seconds and 90%/exhaustion guidance independently of token statistics.

Missing/corrupt budget limits retain valid job evidence and recovery with explicit unavailable limits; consumed work remains visible. Non-budget binding includes scalar types.

## Operational job details

Job details explains normal lifecycle states, exposes current-stage failed attempts and event-recorded stage/context/transition destinations with second-precision times. Clarification Markdown uses the existing safe renderer and local scrolling. On-demand executor output uses host-normalized, journal/digest-bound operational snapshots outside executor IO; missing provenance is explicit and raw archives are never a fallback. Canonical missing-module exceptions and test counts remain useful while private content and costs are withheld for both roles. Concurrent consumption snapshots preserve verified prefixes/cursors, and read failures have a real refresh control. Scoped offline API/RPC/helper/browser tests cover the seam; historical live 503 causes remain unproven.


History identifies ticket/job targets and actual operation outcomes; CLI delete records a local receipt before cleanup even without web identity. History imports it with project-scoped authorization and conservative interruption handling.

A new web identity store announces its factory administrator credentials at creation. The unchanged factory administrator sees a persistent localized reminder linking to My account; password change and reset revoke sessions, and no stored format changes.

Own-password changes, including after reset, offer independent password visibility and require matching confirmation; the existing server minimum is eight characters.
