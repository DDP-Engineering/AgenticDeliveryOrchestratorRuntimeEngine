<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to the Agentic Delivery Orchestrator & Runtime Engine are recorded here.
This project follows Keep a Changelog and Semantic Versioning.

## [Unreleased]

### Changed

- Show per-project capacity, queue causes and separate worker roles; retain Settings drafts and durable operation results across navigation/refresh. Staged lower job limits fence new admission while existing jobs continue.


- Execute scoped settings, checks and reviewed environment preparation in an independent
  bounded configuration worker; confirm durable outcomes, fence revisions/rights and
  preserve fast project saves, global administration and immediate admission controls.
- Run the web worker as one local supervisor with independent project workers and
  per-project run pools, fenced process trees and bounded application shutdown.

- Isolate concurrent job resources by project, serialize short shared mutations,
  preserve concurrent metrics exports and require proven ownership for cleanup.
- Guard project archive and deletion across every live execution and cleanup reservation.

- Separate short project admission from exclusive run execution and reconciliation;
  apply the project concurrency limit to manual starts, retries and resumed work.
- Add revision-bound single-run CLI dispatch, preserve live foreign owners and
  exclude initial queue waits from active execution budgets.
- Delete each project's `store_root/runs` before starting this build.
- Persist scoped execution/configuration claims, worker generations and process-bound ownership;
  recover only demonstrably dead owners and fence stale results and publication.
- Confirm Start at durable job admission and Cancel only from the actual saved cancellation result.
- Delete `ADORE_HOME/web.db` and `ADORE_HOME/web.db.initialized` before starting this build.

## [0.15.0] - 2026-11-12

### Added

- Configure whether each project requires human approval before PR/MR publication.

- Import complete project ZIPs in one automatically validated dialog, retaining
  exact configuration and executor image sources together with monitoring paused.

- Retain shared executor image recipes from Dockerfiles or source ZIPs and export
  project configuration with complete local-base definitions from one compact dialog.
- Include the standard executor base definition automatically in source exports.

### Fixed

- Compact Project Summary, remove its redundant executor tile, show Settings save controls only for pending work, and align Job scope with Tickets/Jobs tabs.
- Remove the verbose job-search hint while retaining the search limit and filters.

- Redesign Job details with a compact ticket heading, explicit next action, resources and evidence tabs.

- Save complete project exports directly, with recipe administration kept in Technical details.

- Align the ticket Actions header and buttons to the right, keeping desktop actions on one row.

- Keep raw configuration export options and feedback in dialogs with symmetric Settings actions.

- Keep Provider, Model and other single-line Settings controls at normal height.
- Retain verified executor output through live read conflicts and summarize completed launches.

### Added

- Web imports automatically prepare missing shared executor and network-proxy
  images, show progress, share concurrent preparation and support retry before
  saving a project. Existing images are reused, including through WSL.

- Jobs identifies AEGIS and Direct workflows and shows recorded agent attempts.
- Enroll repositories with or without AEGIS. ChatGPT subscriptions use server
  sign-in without an API-key selector; container choices include detected WSL runtimes.
- ADORE observes the agent's AEGIS journal and direct summaries, binds candidates
  to human approval and publishes approved changes. Repository checks belong to
  the agent; ADORE no longer runs strict AEGIS checks or standalone test commands.


### Fixed

- Restore enrollment and raw import actions after deleting the last project,
  and simplify the delete confirmation while keeping the exact-name instruction.

- Simplify enrollment helper text and credential spacing; automatically check setup
  and server access on entering Verification, with one manual recheck action.

- Check the configured container daemon, including WSL, during readiness and report
  unavailable services or executor images before starting ChatGPT sign-in.

- Read rewritten Direct summaries reliably on Windows, retaining file replacement
  and modification checks.
- Keep Direct Jobs readable across publication reset/retry history, while refusing
  invalid execution stages.
- Make tests independent of host shells, default encodings, newline
  conversion and symlink privileges; give large parameter cases bounded test IDs.

- Use the configured workflow Python for both AEGIS probes during `adore init`, and name it when unavailable.

- Keep healthy projects visible in Overview when another project's job state cannot be read.

- Narrow the ticket number column to leave more room for the other columns.

- Show the native Pi check and its Node error in enrollment for server execution.

- Use even spacing and keep the empty project card focused on enrollment or access.

- Stop checkpoints containing suspicious new system-cache or literal environment-variable paths.

- Open Add user and account password resets from the Users list with shared confirmation and eye buttons. Own-password changes also use confirmation and eye buttons.

- Announce the initial web account and remind its administrator to change the factory password.

- Clarify enrollment and project settings, preserve current readiness evidence, and support Pi reasoning effort.

- Complete localized setting help for Pi reasoning effort and native execution.

- Preserve reasoning effort when saving the agent connection and keep wide ticket source in its own scroll region.

- Retry brief Windows profile file locks while saving project settings.

- Keep typed folder paths when a directory listing finishes loading.

- Correct History targets and outcomes, and retain CLI job deletion evidence after removal.

- Confirm cancellation and clarify cleanup, worker activity, monitoring updates and project empty states; exclude configured epic tickets from pickup.

- Reconcile status labels during notification replay and identify the execution backend and web Retry in failure comments.

- Refresh the committed web bundle and detect stale frontend assets before packaging.

- Job details explains normal states in four languages, shows current-stage failures, event stages and seconds, safe Markdown questions, useful host-captured executor diagnostics and a real consumption refresh action. Concurrent usage snapshots retain verified prefixes without falsely reporting corruption.

- Budget defaults use 20 launches across CLI and web enrollment. Job details shows launches and cumulative active time with limit warnings; reviewed budget-only saves allow parked jobs and apply at the next attempt or resume without resetting consumption or progress. Unavailable current limits preserve valid job evidence and recovery controls.

- Confirmed web abandonment restarts failed tickets after owned resource/worktree and leased remote-branch cleanup. Stable drift has a useful Job details recovery path; CLI deletion reports clean ownership failures and web-worker lock guidance, with explicit saved-native-ownership cleanup.

- Concurrent job deletion no longer interrupts project/run listings; corrupt state remains visible and unrelated read errors still propagate.

- A late project-list response no longer replaces a newer explicit host-check result; subsequent background polls still refresh verification.

### Changed

- Delete the run-state directories under each configured `store_root/runs/` before starting this build.

- Delete each configured statistics database before starting this build; summaries now record workflow.

- Store agent prompts as shipped Markdown files in `adore/prompts/`, preserving the text sent to Pi.
- Use the executor's completed AEGIS validation for candidate approval, eliminating the duplicate strict run by ADORE.

- Offer detected Docker and Podman commands in project Settings, including Windows WSL, with manual entry and WSL image suggestions.

- Open raw TOML import in a Projects dialog with automatic file validation. Remove the browser project configuration clone workflow.

- Refresh project Settings, Access, History and global Change history automatically. Settings pauses while edits are unsaved. Project History uses automatic updates in place of its Refresh buttons.

- Delete each project profile’s `readiness.json` before starting this build; workflow observations are now separate from prerequisite checks.

- Ticket details place Body display and its selector together on the right of the description heading; action buttons wrap without splitting words when details open.

- Tickets render descriptions and comments as safe Markdown by default, with exact source mode saved per account, localized controls/help and keyboard-friendly themed layouts. HTML stays literal and images never load automatically.

- Web preference storage changed: delete `web.db` and `web.db.initialized` in the ADORE home before starting the new build.

- Project Settings saves all edited values with one Save action, confirms important effects, preserves failed drafts and uses the full row width for descriptions and controls.


### Added

- Export a reviewed Docker build bundle alongside the raw project configuration.

- Support ChatGPT subscription sign-in and scoped Pi execution natively on Windows and Linux/WSL2, with temporary stage tokens.

- Opt-in agent-controlled system-package installation in job containers, independent of network access, with reviewed settings and pinned recovery.

- ADORE installs and verifies the pinned Pi for native Windows and Linux jobs. Native stages use isolated RPC with the current service account and optional project tools PATH.
- Clone destinations offer automatic/custom locations and an administrator-only read-only host folder picker with Windows drives, Linux navigation and optional new subfolder names; selection never creates folders.

- Complete portable user distributions: native Windows x64 ZIP and Linux x64
  TAR.GZ include managed CPython, locked web dependencies, compiled UI and
  simple start/stop/CLI wrappers. The launcher opens a ready browser interface,
  reuses the existing instance, bounds restarts and logs, keeps user data outside
  the extracted application and verifies package checksums. Build and acceptance
  tooling live in `02_Tools/`; packages and receipts are generated in `07_Delivery/`.

- **Internet access for the agent.** Settings → Agent and model has **Internet access for the agent** (`[executor] internet`, default Off) and **Web search** (`[executor.web] search`: `exa`, the keyless default, `brave`, `tavily` or `none`). Off: a container run sits behind its per-run egress proxy, which admits only the model provider's hosts (from the pinned Pi's own provider data, now `hosts` in `adore/pi_catalog.json`; `api.openai.com` for a ChatGPT subscription; the endpoint's host or IP address for an OpenAI-compatible endpoint) plus `[container.egress] allowlist`; Pi loads no web tools and its system prompt says that only the model provider is reachable, so `curl`, `npm install` and `pip install` fail. On: open network, Pi loads the pinned pi-web-access extension with an ADORE-written `web-search.json`, and downloads go through bash. A Brave or Tavily key (`BRAVE_API_KEY`, `TAVILY_API_KEY`) is saved under Authentication, also for a ChatGPT subscription, and reaches only internet-on runs. Settings warns while On that a malicious page could try to make the agent send its API key or ChatGPT token out, and shows the switch as not enforced for a project installed on the server. **Check host prerequisites** adds the egress proxy image (Off) and the search key (Brave or Tavily). The egress proxy admits IP addresses as well as host names and gets the `--add-host` options of `[container] run_args`; the unattended install scripts refuse `[executor] internet = true` unless `--allow-open-egress` / `-AllowOpenEgress` is passed.
- **Sign in with ChatGPT from the web interface.** An administrator signs the ADORE server into one ChatGPT Plus or Pro account under Settings → Agent and model → **ChatGPT sign-in** of a project whose provider is ChatGPT subscription: ADORE runs Pi's own OpenAI sign-in in a one-off helper container from the project's image, shows the OpenAI link, and the administrator pastes the browser's `127.0.0.1:1455` redirect address back (no browser on the server; the state is checked first; 15 minutes at most; Cancel and **Disconnect ChatGPT**). The sign-in lives in `<ADORE home>/chatgpt/` (Pi's `auth.json` 0600 and lock, a stable installation id) and is shared by every ChatGPT project. Before each stage ADORE gets an access token valid for the stage limit plus five minutes, refreshed under Pi's lock in the helper container (the only container that mounts the directory), and gives Pi only `OPENAI_API_KEY=<access token>` in that stage's exec environment, masked in evidence; the refresh token never enters a run container, and a stage without a token fails naming the cause. Status is **Signed in**, **Not signed in** or **Sign in again** (unreadable sign-in or a refused refresh such as `invalid_grant`). Refusals (`subscription_sharing_user_not_eligible`, declined, rejected code, OpenAI unreachable) have their own messages in four languages; Test AI connection adds `sign-in-required`, `subscription-refused` and `usage-limit`; the readiness check of a ChatGPT project adds `executor_sign_in`; the model list offers the models of Pi's ChatGPT catalog (`chatgpt_models` in `pi_catalog.json`, for example `gpt-5.6-luna`). ChatGPT projects need container execution and stage time limits of at most 3000 seconds. The routes are admin-only with CSRF and audited by cause code without any token, code or address: `GET`/`PUT`/`DELETE /api/v1/chatgpt-sign-in`, `DELETE /api/v1/chatgpt-sign-in/pending`, `POST /api/v1/projects/{name}/chatgpt-sign-in`. ADORE is free today; offering it hosted or paid with ChatGPT sign-in would first need OpenAI's interest form. Rebuild the executor image (it now ships `/opt/adore/pi/adore-chatgpt.mjs`, checked by `docker/verify-runtime.sh`).
- **Choose Pi's provider, model and credential, or an OpenAI-compatible endpoint.** Settings → Agent and model and enrollment step 2 offer **Provider** (Pi's API-key providers, read offline from the pinned Pi 1.4.0 into `adore/pi_catalog.json` by `02_Tools/generate_pi_catalog.py`; **ChatGPT subscription**; and **OpenAI-compatible endpoint** for LM Studio, Ollama or vLLM), **Model** (Pi's list for the provider, or any typed ID) and, for an endpoint, **Endpoint base URL** (the address as seen from the selected execution environment) and **Endpoint API type**. Provider, model and endpoint are reviewed and applied as one change (`executor.connection`). The API key is saved in the project's credential store under the variable Pi reads for the provider (OPENAI_API_KEY, ANTHROPIC_API_KEY and so on; ADORE_ENDPOINT_API_KEY, optional, for an endpoint) and reaches Pi only as that variable; for an endpoint ADORE writes Pi's `models.json` into the ADORE-owned agent directory before every stage. Enrollment takes no key and names the variable to save after creation. New `GET /api/v1/pi-providers`.
- Enroll a project from its repository URL: **Read repository** detects the forge (github.com, gitlab.com or a matching server tea login), repository, Gitea login and default branch, derives the project ID from the repository name (no Stable project ID field; route names new, clone and repository-source are now reserved IDs) and proposes an editable clone path `<ADORE home>/repos/<ID>`; Continue stays disabled until the repository has been read; creation clones the repository there with the server account's git credentials (or reuses a clone with the same origin), requires AEGIS and the target branch, and removes a fresh clone on failure. There is no separate existing-clone mode (a matching clone at the chosen path is reused), every field shows an example, and Clone project config uses the same step. New `POST /api/v1/projects/repository-source` and optional `clone_url` on setup/transfer requests.
- Review and create (Enroll new project and Clone project config) lists the settings left at ADORE's defaults, closed and read-only, grouped and named as in Settings, with a note that they can be changed in Settings after creation; for a clone the copied rules are not listed as defaults. The setup and transfer previews return `defaults`.
- Create the project's ADORE labels in the repository: Review and create offers **Create the ADORE labels in the repository (missing ones only)**, ticked by default, and Settings → Repository offers **Create missing labels**. ADORE reads the repository's labels once and creates only the missing ones named by the project's settings (lifecycle, hold/exclude, priorities, bug type, approval, revise, quick-path and task-type labels) with a colour and description, never changing existing labels, and reports created, existing and failed labels. New `POST /api/v1/projects/{name}/labels/ensure` and label list/create in the GitHub, GitLab and Gitea adapters.
- Choose where the executor runs again from the web: Enroll new project and Clone project config offer **Runs in** (Container or Installed on the server), the container runtime and an image with suggestions from the server's own images (new `GET /api/v1/executor-images`), the current account and optional project tool PATH for local projects, and optional credential variable names; Settings → Agent and model shows and reviews `execution.backend`, `container.runtime`, `container.image` and the local account fields. Other environment keys and image builds stay outside the web.
- The Tickets table is paged: more than 10 tickets show 10 per page by default, with **Rows per page** (10, 25, 50, All), the visible range, the page number of the page count and **Previous**/**Next**; a new read returns to the first page.
- Delete project can also remove the local clone ADORE made: an unticked **Also remove the local clone** option appears only when the clone lies under `<ADORE home>/repos`, is a clean clone of the project's repository, is not used by another project and has no linked worktree that deletion keeps (ADORE's own job worktrees are removed first); otherwise the dialog says why it stays. New `GET /api/v1/projects/{name}/delete-preview`, `remove_clone` on the delete request and `adore profile delete --remove-clone`.
- Reviewers are optional: `[delivery] reviewers = []` is valid and opens the MR/PR without a review request; the enrollment wizard, `adore init` and the Settings reviewer editor accept an empty list.

- How ADORE works now opens an in-app help center at `/help`: ten topics (what ADORE does, interface tour, adding a repository, project settings, executors and models, tickets for automatic pickup, job lifecycle, statistics and costs, administration, glossary) in English, French, German and Romanian, with search, an outline, `/help/<topic>` addresses and contextual **?** links on the Tickets view, the Add project wizard and project Settings. Content is bundled Markdown checked by `tests/help.test.mjs` for locale parity, a safe Markdown subset and valid links; AGENTS.md "Help content rules" keeps it current. The dropdown glossary became the Glossary topic.

- About > What's new lists each release's user-facing notes in the user's language, newest first and grouped New/Improved/Fixed by topic. Notes live in `04_Software/adore/release_notes.toml` with all four locales per entry, are maintained by agents under the new AGENTS.md "Release notes rules" (journal line `release-notes: ...`) and are checked by `02_Tools/check_release_notes.py` (contract, changelog dates, current version; `--since` warns on changelog-only changes); `/api/v1/about` returns them as `release_notes`.

- Browse a project's open forge tickets from its Jobs tab: a Tickets sub-tab reads them on request with ADORE pickup eligibility and job state, starts a ticket (adding its missing ready and chosen priority labels after confirmation), retries a failed job, stops a ticket (cancels its unfinished job and removes the ready label) and shows its description and comments as plain text; the job table moves to a Jobs sub-tab.


- Native projects use managed Pi with project credentials with pinned machine/environment identity, verified Windows Job/Linux cgroup ownership, native AEGIS/gate evidence, backend-aware setup/settings/readiness and user-owned tooling guidance.

### Changed

- Before starting this build, delete obsolete native run directories under `[state].store_root/runs/` that contain the old local execution plan; remove `[executor] command` and `[local]` home, environment and cgroup_root from local project TOML.

- Update the repository's managed AEGIS payload to the rebuilt 0.14.0 delivery,
  preserving project configuration and journal/history files. Enable structure,
  sequence and state diagrams for applicable Design stages. Retain optional
  CodeGraph files/configuration; upstream no longer exposes its CLI commands.


- Connect repository keeps a single Cancel button beside Verify and connect;
  remove the redundant Close button from the dialog heading.

- Enrollment and Clone project config offer remote target branches in a dropdown
  with the repository's default selected and marked. GitHub, GitLab and Gitea,
  including self-hosted remotes, share one bounded Git read. Rereading retains an
  explicitly chosen still-existing branch; empty or malformed listings cannot
  silently select a fabricated default.

- Simplify the host folder chooser to compact directory rows, single selection,
  double-click/keyboard navigation and exact folder confirmation. Agent and model
  uses independent field columns; automatic executor discovery keeps optional
  re-detection under Advanced.

- Reserve delivery for the complete Windows/Linux portable archives and optional
  adjacent hashes only. Build/verification work uses automatically cleaned OS
  temporary directories; results are printed without retained logs or reports.
  Three public cross-platform commands cover repository setup, package creation
  and package verification; release/license helpers are internal and older
  source-runtime/wheelhouse packaging flows are retired.

- Portable user distributions include three concise usage, administration and
  troubleshooting guides instead of the entire documentation tree. An explicit
  packaging allowlist excludes engineering, UX handoff and source reference files;
  packaged link and inventory checks guard this boundary. Full in-app help remains
  included in four languages.

- Move host deployment scripts and the systemd template to `02_Tools/deploy/`.
  Windows and Linux installers resolve `04_Software/` in a checkout and the
  runtime root in a delivery bundle; both packagers copy deployment resources
  from the tools directory and keep bundled `deploy/` commands working.
- **BREAKING: `[container.egress] mode` is removed; `[executor] internet` decides the agent's network access and is off by default.** Delete `mode` from `[container.egress]` in `config.toml`; a configuration that still sets it is refused. A container project now needs the egress proxy image (`docker/Dockerfile.egress-proxy`) unless internet access is on. `[container.egress] allowlist` now lists extra hosts an internet-off run may reach and may be empty; a local profile refuses a non-empty one.
- **BREAKING: `[executor]` takes `provider` (required: a Pi API-key provider id, `chatgpt` or `custom`) and `model` is the model ID within that provider (`gpt-5.5`, not `openai/gpt-5.5`).** `[executor.endpoint]` with `base_url` and `api` is required for `custom` and refused otherwise; `custom` supports both execution environments. `env_keys` now lists only additional secrets, the provider's key variable is always passed, and it defaults to empty. Unknown keys, such as an inline `api_key`, are refused by name. Add `provider` to each `config.toml`, remove the provider prefix from `model`, and delete each profile's `model-connection.json` and `pending_config.json` before starting this build.
- **Test AI connection in a container runs over Pi's RPC mode** with the same challenge as Pi installed on the server (one shell command that prints a nonce, then an exact reply) and reports `credential-missing` (no key saved or set; no container starts), `credential-invalid`, `connection-failed` (provider or endpoint unreachable), `model-unavailable`, `rate-limited` and `provider-error` separately, with guidance in four languages.
- **BREAKING: Pi is ADORE's only coding agent; OpenCode, Codex and Qwen Code support is removed.** `[executor]` takes `provider` and `model`. Container runs use the image's pinned Pi. Server runs use managed Pi and require removing any explicit `[executor] command`. `default`, `stage_host_auth`, every `[executor.<name>]` table (`[executor.pi]` included) and `[labels.executor]` are refused as unknown keys, and `[container] runtime_env` or `[local] environment` names starting `OPENCODE_`, `CODEX_` or `QWEN_` are refused; move the model to `[executor] model` and delete the rest. Removed with them: the agent choice in Settings → Agent and model, enrollment and `adore init`; host sign-in staging (`stage_host_auth`, auth mode `host-auth`; container projects use provider API keys); the OpenCode-compatible endpoint form, model catalogue, endpoint probe and the host check's model-endpoint row (the Test AI connection result still shows there); local OpenCode configuration isolation and `CODEX_HOME`; and OpenCode, Codex and Qwen Code in the executor image, which now installs only Pi and pi-web-access as the coding agent. Before starting this build, finish or cancel active jobs and delete each profile's `readiness.json`, `model-connection.json` and `pending_config.json`; Statistics keeps the executor names stored with earlier usage.
- **Pi in containers runs through its RPC mode.** The executor image pins Node 22.23.4, Pi 1.4.0 and pi-web-access 0.46.0 (checked by `docker/verify-runtime.sh`) and ships ADORE's Pi guard extension. Each stage starts one `pi --mode rpc --no-session` process with an ADORE-owned agent directory (`/home/adore/.adore-pi-agent`) and none of the personal skills, extensions, templates, themes or MCP servers; the guard, loaded with `-e` without project trust, blocks `git push` and `gh`/`glab`/`tea`. ADORE sends `abort` at the stage timeout or on cancel and ends the process after a grace period; failures name their class (credential, sign-in, rate-limit, model, network, provider); token usage is summed over the turns and Pi's estimated cost is not reported. Both execution environments use a fixed RPC launcher. A Pi agent directory mounted at `/home/adore/.pi/agent` is no longer read, so a ChatGPT subscription uses the server's ChatGPT sign-in instead (see Added). Rebuild `adore-executor-base:1.0.0` before starting this build.
- ADORE no longer reads data written by earlier builds: there are no migrations or compatibility while it is in development. Run state at the removed `deliver` stage or missing a current key, `profile.json` with unknown or missing keys, `config.toml` keys this build does not read (such as `[state] channel` or the Codex `{resume}` placeholder), a `metrics.db` with other columns, journal events without a timestamp or with one lacking its UTC offset, usage events without an event ID, pending configuration candidates staged by an earlier build, and audit rows without evidence are refused with a message that names what to delete or fix. The retired image-build subsystem and its `/image-build` routes are removed, and `adore cleanup` no longer recognises container and network names cut by earlier builds; remove such leftovers with the runtime CLI (Recovery_And_Maintenance.md). Statistics Trends no longer shows **Usage without a consumption date**, which every current usage event has. `POST /config/apply` requires `base_revision`, which the browser already sends. Before starting this build, delete the run directories, `metrics.db` and `pending_config.json` that the refusals name, and remove stale keys from `config.toml`.
- **Test AI connection** for Pi installed on the server now asks the agent to run `echo <nonce>` with its shell tool and then reply with a second nonce. It reports connected only when the shell call completed and printed the nonce and the reply is exact; a missing, rejected or failed shell call reports the new reason `tool-call-failed`, with guidance in four languages to check the agent's permissions. The local test is bounded at 90 seconds instead of 45 and keeps up to 1 MiB of agent output instead of 64 KiB, so a local Pi test, whose events repeat the whole conversation, can pass at all. Container profiles run the same challenge over RPC. The help text, the host-check row and the docs no longer say tools are never checked.
- **BREAKING: ADORE conducts AEGIS 0.15.0, where validate closes the task, and
  requires AEGIS 0.15.0 or newer.** The conducted paths are frame, specify,
  design, build, validate and done, and the quick path frame, build, validate
  and done; the deliver stage and `6_deliver.md` are gone. The executor's
  validate session ends with AEGIS's final `check --strict --run`, `report` and
  `advance` to done, and that validate -> done advance triggers ADORE's own
  strict check and the candidate-bound approval. After approval ADORE only
  pushes the branch and opens or adopts the draft or ready MR/PR: no executor
  session and no AEGIS command runs, and the branch is pushed once. A done task
  ADORE holds no verification evidence for (an invalidated approval, a run-ahead
  session) gets one fresh session that returns it with `advance --to
  validate`; a failed independent check counts one validate failure and a
  remediation session returns the task from done to validate, build, design or
  specify.
  A run keeps the stage done while it waits for approval, publishes and is in
  review; ADORE records the fingerprint it published, so `retry` returns a run
  that failed after publication to review, resumes publication of an approved
  unpublished candidate (also after `reset --to publishing`) and conducts any
  other run from done; publication refuses a run outside stage done or the
  publishing pointer with `PUBLICATION_STAGE`. The probe and the readiness check refuse an older AEGIS with a
  message naming 0.15.0, so runs begun under the deliver flow, including runs
  already in review, are not carried over; run records and run-journal events that name deliver
  are refused. Stage prompts name `advance`, `log` and `pause` (`pause --blocked`
  for questions), the continuation context names `brief` and the journal State,
  and the human handoff note names `brief` and the full task journal instead of
  the retired Handoff and Stage report sections. Re-verified against the installed 0.15.0 CLI: the version line,
  schema 1, the `status` list and task documents (a legacy deliver journal is
  listed with the validate step file; the State block is not part of the JSON),
  the `check` document and `--run` records, the single-path `task` output and
  the `report appended to` confirmation.
- `[workflow] stage_timeout_overrides` and the Settings stage-limit editor cover
  the five stages frame, specify, design, build and validate; a deliver key now
  fails configuration validation as not an AEGIS stage.
- Refreshed this repository's own `.agentic/` companion to AEGIS 0.15.0, removed
  its CodeGraph plugin and enabled structure, sequence and state design
  diagrams. The companion governs how ADORE is developed and does not ship in
  the runtime bundle.

- Projects offers three separate actions, each on its own page: **Enroll new project** (guided wizard starting directly at Repository and identity, five steps), **Import project config** (upload an existing `config.toml`, such as one saved with Download raw configuration once its inline secrets are replaced) and **Clone project config** (`/projects/clone`, rules from a project on this server or a portable settings file). The duplicate Enroll an existing configuration button and the in-wizard method buttons are gone; help topics follow in four locales, and a refused browser Back keeps the current page address.

- Redesign About: the DDP Engineering logo on a dark band, ADORE and its version as the largest text, and What's new, License and Third-party notices buttons with both license texts folded until pressed; Tab cycles inside the dialog.

- Show the header Refresh and last-refresh time only on pages that do not update themselves (Users, Change history and a project's Settings, Access and History); Overview, Projects, Jobs, Statistics and System status refresh automatically.

- Steady change history evidence: Evidence opens on a full-width row below the event so the table columns no longer resize, operation correlations and configuration revisions show their first 12 characters (full value on hover), and base/candidate revisions appear only when recorded.

- Tidy user project access: Assigned projects opens full width below the account, each project is one checkbox row with its name and its forge and repository path in columns (the unique name is added when display names repeat), and creation choices use the same rows; reviews and results keep the stable project IDs.

- Compact System status: audit retention shows the current limits (Unlimited when none) above the prefilled form with one short impact sentence, the control worker and storage are compact indicators in one row, and storage is grouped by physical volume (`volume_id` in `/api/v1/system/storage`) - one line for a shared disk, a table only for several.

- Show each Statistics per-project family once: the All projects scope line, the Projects tab and the Repository table are removed; Summary lists job counts and average elapsed per project, Usage consumption, costs and unpriced events per project, and Quality rework, revisions, repairs and review rounds per project, each with the repository under the project name.

- Simplify the Jobs table: Ticket, Project, Status, Last activity and lifetime token Consumption, sortable on the server by Ticket, Project, Status or Last activity (`/api/v1/jobs-page` `sort`/`order`); the Selected period line, selected-period consumption, project/run identifiers, outcome text and activity-age hints leave the rows (identifiers and outcome stay in job details).

- Align the global Jobs page with the project hub: a compact project selector and the same Tickets/Jobs sub-tabs (`view=jobs`), with All projects Tickets reading every authorized active project into one table with a Project column; the ticket-number start form and the scope/worker explanations are removed (start a ticket from Tickets), and worker status appears only when it needs attention.

- Compact the Statistics Trends tab: one table with a row per period bucket and inline bars replaces the chart plus its duplicate table, time zone labels and measurement labels are gone, coverage shows as compact values, and the separate Estimated cost section is removed (administrators find unpriced usage events among the Usage totals and estimated cost per project in Projects).

- Compact the Statistics Quality tab: delivery quality, administrator cost per job and MR/PR revision/pipeline repair totals use the compact Usage-style values without explanatory paragraphs, and the daily revision table lists only days with activity.

- Compact Statistics: the reporting period is one row (project, From, Through, Group by, All time, Export CSV) without the time zone selector or explanatory text, and Summary shows only the measure cards (no current-state count, heading, scope line, explanations or Messages); job elapsed time joins the Usage totals as compact values and the per-job consumption table is removed because Jobs already shows it; the Usage table sorts by column instead of executor/model filters, and the redundant Rebuild usage history button is removed (reads already reconcile usage); periods use UTC unless the link supplies a time zone.

- Order project hub tabs Summary, Settings, Jobs, Statistics, History, Access.

- Show a project's Jobs and Statistics as tabs inside its project hub, with job detail opening in the Jobs tab and no repeated project selector or scope panel; Overview, Jobs and Statistics pages identify their scope only through their own Project selector.

- Move Admin estimated prices from their own project tab into Settings → Agent and model; prices are recorded for Pi and its configured model, so the form asks only for effective date and input/output rates; older `/prices` links open Settings.

- Show pending settings above category groups with changed values and adjacent Apply/Discard; fold complete review/technical evidence and clearly block unchanged simple candidates.

- Consolidate executor configuration in Settings → Agent and model, with reviewed launch-command and model settings and names-only provider authentication controls.

- Clarify externally configured installation values in Technical details and align Workflow Python command API authority with its read-only GUI.

- Enable reviewed Implementation edits for human-answer duration, question rounds, retry-delay lists and all six stage timeout overrides, with localized typed controls; validate the active answer deadline independently of the reserved reminder.

- Clarify implementation settings in four GUI locales with executor-launch and active-work names, consistent candidate review and accurate capacity, telemetry, timing, file-count, checkpoint and quick-path guidance.

- Enable reviewed Repository editing of job branch templates and optional naming rules, with four-locale names/help and a revision-bound Python-checked example; retain external runtime paths and reject malformed or unevaluable branch naming in CLI and GUI.

- Group Project Settings by Git delivery flow: Repository, Tickets, Implementation, PR/MR and review, Statistics and informational Technical details; add topic disclosures and a single integration-branch editor referenced from PR/MR, retain separate Executor configuration, and omit inactive GUI controls.

- Default acceptance-criteria pickup checking to false and maximum additional revision rounds to five; move the revision limit to Limits and recovery with accurate exhaustion guidance.
- Remove the inactive known-component requirement from CLI/web configuration and portable rules; portable working rules now contain fifteen fields.

- Separate ready/answered ticket actions from five initially collapsed status-label settings, localize their names and lifecycle help, and hide inactive executor-prefix and scope-hint controls while preserving technical configuration.

- Clarify the Target branch setting in all four GUI locales, including its new-job base and PR/MR destination, with consistent row/editor/review naming.

- Rename reviewer settings to Request review from and support a localized multiline account editor through typed reviewed configuration apply, with strict list validation.

- Enable guarded progress commit publication by default in CLI and GUI; preserve explicit project overrides and final human publication approval.

- Allow `delivery.draft = false` to create review-ready PR/MRs after fresh human publication approval; settings show localized Draft/Ready for review choices. Existing review records retain their state, and ADORE never merges.

- Move execution environment preparation outside ADORE: Executor configuration now shows conditional container Dockerfile/server-profile instructions and effective image; Settings and guided enrollment omit environment editors.

- Unify executor settings and Provider credentials in one panel with heading Test AI connection; offer server-validated launch command presets through reviewed dropdown edits.

- Balanced Settings description/value columns and collapsed project categories on entry.

- Moved setting Edit actions beside Active value and removed the separate action column.

- Simplified project Settings and added administrator preview/download of original TOML, including inline secrets, in place of the portable export panel.

### Fixed

- Native Python commands use managed UTF-8 standard-stream encoding so Windows AEGIS validation retains non-ASCII evidence without relaxing corrupt-output refusal.

- Native ChatGPT configuration errors now explain that ChatGPT sign-in requires a container project.
- Pi execution plans pin provider, endpoint, internet and search settings; package-enabled RPC stages retain redacted, bounded evidence and settle timed-out processes before reuse.
- Delete affected job run directories in the configured state store before starting this build; saved execution plans require the current Pi policy.

- Integrate the current AEGIS workflow with native retry, backward stage routing,
  independent container package permission, Git context and timeout recovery.

- Quiesce timed-out container commands before retry, preserve the same installed environment, and fail closed when safe recovery is unconfirmed.

- Preserve native Git discovery in new job containers with a read-only linked-worktree pointer, clear inherited repository selectors, validate binding evidence and retain warm resources. Use direct WSL argument transport so shell expressions and paths reach the container literally.


- Executor output archives preserve the 64 KiB package-log byte limit on Windows without newline expansion.

- Preserve inherited PATHEXT in native executor environments so Windows shell
  commands resolve installed tools such as Git and Python.

- Align executor journal editing with rebuilt AEGIS 0.14.0 guidance: preserve
  task identity, original legal content, authoring links and append-only history.
  Capture and replay its unchanged companion CLI/schema contract with malformed
  evidence regressions; ADORE and companion releases retain independent versions.


- Explicit Retry refreshes the installed native executor and inherited environment
  on the same host/account for every job and executor, preserving task/worktree,
  history and cumulative budgets. Failed rearming returns a nonzero CLI result;
  web operations show the saved failure cause instead of generic rejection.


- Accept AEGIS backward stage routing within the selected workflow, including
  Design to Specify. Save the actual stage before checkpoints and report typed
  checkpoint failures without leaving an orphaned working job.

- Preserve stdout/stderr through the Windows background supervisor so successful
  native version and model checks no longer appear to return empty responses.

- Local readiness shows one concise explanation and retains safe failure causes/exit codes;
  native version checks accept stderr, and Pi connection checks identify provider/model failures.

- Recover missing external Gitea logins through bounded current-account discovery
  in standard Windows/Linux configuration roots, preserving scoped credentials
  and explicit overrides. Missing or ambiguous sign-in now explains the localized
  Connect repository flow without application-specific paths or credential copies.

- Automatic command launches disable Git/generic pagers per child environment and
  suppress Windows console allocation, including worker/native executor launches,
  while retaining captured output, timeouts and process ownership.

- Manual ticket Start now runs the selected ticket while monitoring stays paused,
  preserving all other admission checks and displaying specific, localized failure reasons.

- Reviewed web settings tolerate brief Windows file-read locks and retain the candidate with an explicit error if saving remains unavailable.


- **Check details** for a project that runs on the server no longer repeats the local-execution notice in the *Local execution* row. The notice appears once at the top; the row says what it checks (the selected agent's tools for the server account and its existing sign-in or a provider API key) and, when the check fails, how to fix it: sign the agent in on the ADORE server under that account, or save a provider API key in Settings → Agent and model, and check the installed tool PATH.
- Manual Start remains available while automatic monitoring is paused. When the worker cannot start a queued ticket, `adore run --once --ticket N` prints `error: ticket #N not started: <code>` (`pickup_paused`, `at_capacity`, `aegis_probe_failed`, `not_eligible`, `conductor_busy`) and the operation keeps that `reason` plus a `detail` with the engine's last 20 lines (at most 2000 characters, ANSI removed, credentials redacted), shown as a sentence in the user's language and a bounded block in Tickets, Jobs and the project status and returned by `GET /api/v1/operations/{id}`; every failed engine operation keeps its `detail`. Labels a refused Start added stay on the ticket, and the notice names them. Start and Stop confirmations open under their ticket, and the Start message names the chosen priority label instead of the word Priority. The web database schema changed (operations gain `reason` and `detail`) and is not migrated: delete `web.db` and `web.db.initialized` in the ADORE home before starting this build. ADORE now refuses a web database from any other schema with a message naming both files, and no longer upgrades older ones.
- A `NO_STAGE_PROGRESS` stage failure (the executor exited 0 but AEGIS stayed at the same stage) now carries the executor's last stderr lines in its evidence: up to 20 lines and 2000 characters, ANSI colour codes removed and credentials redacted on the whole stderr before it is cut, so a cut never separates a key from its secret. The incident and terminal comments on the ticket, the run journal and Job details show it, so a cause such as auto-rejected tool permissions is visible without reading `io/stderr.log` on the server. When a failed job's evidence exceeds 2000 characters, for any error code, Job details now keeps its first line, such as `stage build failed on attempt 3/3: …`, then `...` and the end, instead of only the end.
- Native local execution on Windows passes the standard Windows machine/system variables (`PATHEXT`, `PROCESSOR_ARCHITECTURE` and the other `PROCESSOR_*` names, `NUMBER_OF_PROCESSORS`, `OS`, `SystemDrive`, `ProgramData`, `ProgramFiles`, `ProgramFiles(x86)`, `ProgramW6432`, the `CommonProgramFiles*` names, `ALLUSERSPROFILE`, `PUBLIC`) to executor gates, readiness probes and strict verification. Project tooling detects the platform again (`platform.machine()` was empty) and `%SystemDrive%` no longer turns into a literal folder inside the worktree. Account names (`HOMEDRIVE`, `HOMEPATH`, `USERDOMAIN`) and forge credentials stay excluded. The pinned local environment changes with this fix: finish or cancel local runs before upgrading, because a local run started on the earlier build is treated as drifted.
- Disabled buttons now look unavailable everywhere (dimmed, not-allowed cursor); on Enroll new project, **Read repository** is the primary action and **Continue** stays visibly disabled until the repository has been read.
- Restore the accented letters in the German, French and Romanian handoff status labels (Übergabe läuft / Übergeben, Transféré, Predare în curs), which showed "?" instead.


- Keep model and launch-command editing within the existing setting rows and select allowed credential variables through a compact dropdown with removable names.

- Web statistics and exports respect the configured summary database; statistics storage paths are managed externally with only an informational database file in Settings.

- Clarify PR/MR CI failure actions in all four dashboard languages and align the Integration branch reference with standard setting values.

- Clarify the pickup exclusion label in all four GUI locales: exclusion lasts while the label is present and does not stop already-started jobs.

- Apply configured human-merged run-branch removal to GitHub, GitLab and Gitea with exact commit protection, bounded failure reporting and consistent settings help.

- Web automatic ticket checks share CLI loop interval, capped error backoff,
  nonnegative jitter and quiet hours, with independent per-project waits after
  completion. Polling settings remain available with localized scope guidance.

- Remove the ineffective State reporting channel (`[state] channel`); the read-only durable job state folder stays.

- Complete localized corrective messages for environment, preparation, model and executor credential failures.

- Project image clients resolve native runtime executables and return captured
  bounded output, preserving real exit/timeout and fail-closed stream validation.
  Environment setup starts with backend/image controls and uses inline image
  editing, aligned fields, visible downloads and spaced actionable build results.

- Project image choices show the current image and open its reviewed editor;
  larger Dockerfile/tool-check fields, numbered instructions and a compiler
  example clarify installation, verification, downloads and paused-project prerequisites.

- Host prerequisite checks open their results immediately with checking/error feedback and an internal Close details action.

- Show one dismissible application notification, updating operation status and hiding final/ordinary feedback after five seconds while preserving worker polling.

- Host-check AI access presentation uses a current successful explicit executor test instead of reporting it as untested.

- Hide host-check time/configuration version and its explanation from project Summary.

- Gitea host sign-in checks use the supported named-login API after GUI connection. Repository connection opens a closable modal beside host checks, with an aligned HTTP consent checkbox.

- Make host-check details collapsible with a persistent verdict, clarify the checked
  configuration version and explain external repository sign-in under the service account.

- Explain project host-prerequisite checks with clear verdicts, purposes and corrective
  actions, one checked-at/revision line, honest unavailable model checks, and
  validated project-bound browser evidence.

### Added

- Shared container execution backend and immutable reviewed recipe plans with a closed version-1 Actions-style preparation grammar, same-container dependency setup before AI gates, bounded redacted evidence, identity-bound recovery and explicit capped `retry --reprepare`.
- CLI plan review and revision-bound GUI preparation selection/apply, effective-image readiness and persisted preparation outcomes.

- Project Executor configuration tab with single-owned model settings and protected scoped provider API key save/remove.
- Durable explicit model connectivity evidence bound to immutable project, configuration and credential inputs, reused by Summary and host-check access display.

- Explicit GUI model connection tests through Pi, with bounded disposable containers and redacted project/configuration-bound results.

- Project-scoped repository connection from the GUI for Gitea, GitHub and GitLab,
  with bounded account/repository verification, protected token storage, isolated
  worker/readiness CLI use and secret-free results.

- Structured redacted web change evidence with known before/after and revisions,
  distinct preparation/application/discard results, atomic identity/access/queue
  evidence, durable filesystem uncertainty and idempotent completion. Corrupt
  or unknown audit storage is rejected.
  Authorized server-filtered/paged history and project evidence accompany
  separate administrative retention settings and deletion impact (#19).

- Reviewed web account creation with explicit Admin/global or Dev/stable-project
  access, deliberate empty grants, one atomic account/grant/audit transaction,
  lifecycle-race rollback and secret-free corrective review. Account/project
  grant edits show before/after and applied results; offline negative, browser,
  localization and responsive regression proof accompanies the contracts (#18).

- Explanatory scoped Statistics with explicit all-time, separate active-now stock,
  honest zero/unavailable/partial coverage and cost provenance, server-sample
  durations, composite job lifetime/period consumption, and labeled trends with
  accessible tables. Scope URLs/CSV, stale-response and grant-revocation guards,
  four-locale narrow layouts and honest message placeholders complete #15.

- Consistent scoped web metrics with DST-aware instant boundaries, nullable
  consumption, composite per-job lifetime/period/unallocated projections and
  CSV, strict read-only analytical sources and server-selected duration samples
  and quality cohorts; current-state counts and Admin-only money remain distinct (#14).

- Portable file import and authorized source-project settings copy for new projects,
  with complete rule/default/effect mapping, explicit target reference/environment
  reconfirmation, independent stopped ownership, exact source/candidate binding,
  collision/replay/rollback guards and localized responsive guidance (#10).


- Administrator-only portable project working-rule preview/download with strict
  `adore-project-settings` schema-1 allowlist, deterministic checksum, exact package
  source-version compatibility and public roundtrip parser. Excludes credentials,
  endpoints, identity, host paths, access and history; localized export explains
  target-host setup and separate TOML/CSV formats (#9).


- Purpose-based project settings with visible catalog guidance, distinct active/
  default/proposed values and exact single-candidate review, safe copy and explicit
  apply/discard. Server metadata supplies domains; stale/idle/pause protections and
  four-locale responsive guidance remain enforced (#13).

- Action-oriented Overview and complete authorized global Jobs with safe observed
  detail timelines, project History, scoped search/advanced filters and explicit
  asynchronous command results; EN/FR/DE/RO and offline boundary/browser checks (#12).


- Authorized global/project job read API with composite identities, complete
  paging/search/status groups and optimistic source revisions. Persisted titles,
  activity and waiting evidence keep honest unknowns; strict local
  source/URL validation fails closed without external refresh commands (#11).

- Guided exact server TOML enrollment with localized source/effect explanations,
  complete safe location/runtime review, explicit bounded import checks and
  pickup-stopped completion (#8).

- Six-step guided enrollment with memory-only corrections, navigation-loss warnings,
  accessible findings/focus, explicit environment checks and exact candidate review
  before creating a project with pickup stopped (#7).
- Compatible secret-reference-only setup preview, draft verification and guarded
  revision-bound creation with complete server paths, eligibility labels and run limits.

- Stable project display labels, portable ID availability and offline structured
  setup preview contracts for web enrollment (#6).
- Atomic pickup-stopped web creation/import and persisted revision-bound explicit
  readiness evidence, with rollback, secret guards and offline boundary tests (#6).

- Accessible shared dashboard shell with the approved transparent DDP Engineering logo, real primary/account navigation links, explicit project context, content skip link and a localized delivery glossary.

- Published the Web UX implementation reference bundle, English brief, approved branding, preserved design history and integrity manifests for the existing web baseline.
- Offline Chromium browser regression tooling for the web interface: `npm run validate` runs Node tests, TypeScript checks, an isolated Vite build and Playwright journeys against a temporary API/worker home with simulated external commands. Failed browser checks retain screenshots and traces.
- Project details has an administrator-only Access tab listing the project's developers; Grant access and Remove access change one developer's access to that project at once, leaving their other projects alone. It replaces the Manage access link to the Users page.
- Administrators can delete an archived, idle project from the Projects page after typing its name; the web worker runs the new `adore profile delete <name> --force --remove-resources`, which also removes the project's containers and worktrees while keeping human-owned worktrees, external state and the audit trail.

### Changed

- Project Summary keeps host-check results collapsed behind an adjacent accessible chevron, with model evidence inside details and compact presentation above jobs.

- Project Settings keeps all project values/defaults with one permanent description, without duplicate Help or override-only filtering; global policies remain in Administration.

- Consolidated project Summary into information/action tiles and compact job lists; integrated explicit host checks and accessible modal project deletion.

- Simplified Projects to a read-only directory with a Repo forge column; consolidated project identity and navigation, with lifecycle actions on dedicated Summary.

- Projects describes new-ticket pickup as Monitoring (Active/Paused) with
  consistent pause/activate actions and concise project rows and summary.

- Compact Overview attention and active tables with one project selector and Details;
  worker faults remain visible, while reporting dates, timezone, consumption and
  repeated scope explanations stay out of the overview.

- Project hubs separate pickup from revision/time-bound verification and expose
  Summary, Settings and History alongside existing Admin Prices/Access and
  Jobs/Statistics links. Unsafe or corrupt
  job evidence hides data, and changed page sources require explicit restart (#12).


- Exact enrollment binds reviewed bytes, identity, server ownership and terminal
  state; locked reinspection rejects concurrent mutations. Memory-only corrections
  invalidate prior checks/review and changed disk files require reselection (#8).
- Long dashboard page titles wrap within narrow viewports.

- Dashboard navigation uses Statistics and Change history while preserving established URLs and supported actions. Guided fields show essential instructions visibly; status badges combine symbols and text.
- Loading, empty access and failed requests have separate presentations; failed dashboard reads withhold totals and delayed job-detail responses cannot refill another project's view.

- Every project setting's Help now explains, in English, French, German or Romanian, what the setting controls, its unit or allowed values and the effect of changing it (or that it is reserved), and shows ADORE's default value; a test keeps the texts in step with the configuration keys.
- Project details > Configuration marks every setting as set for this project or default, can show only the project's own settings, and lets administrators edit a setting on its row; common settings come first, rows say when applying needs paused pickup and which settings must be changed in config.toml. The separate common-setting and advanced key/value forms are gone.
- Project names and job ticket numbers are links; a job's View or ticket opens it in Jobs from every table, including Project details Recent jobs.
- Overview card hints say what each number covers, chevrons and sign-out use drawn icons, headings no longer touch the first field, and the Prices form preselects the project's executor.
- Metrics shows one message instead of zero-valued cards when the selected scope has no jobs.
- French, German and Romanian job-related error messages use the same job terms as the rest of the interface.
- Every web view now has its own address (for example `/projects/<id>/configuration`, `/jobs?project=<id>`, `/admin/users`, `/account`), so reload, browser Back/Forward and shared links keep the view.
- Project details now uses Overview, Configuration and Prices (administrators) tabs, with Jobs, Metrics and Manage access as links.
- My account is a top-level sidebar entry for every user; Administration lists System status, Users and Audit.
- Audit and Overview job tables load one page at a time from the server (new `/api/v1/audit-page`; job pages accept several lifecycles), and background refresh pauses while the browser tab is hidden.
- Forms mark required fields, example placeholders are styled and prefixed as examples, and password fields state the 8-character minimum.
- On phones, wide tables show a scroll shadow and Jobs filters collapse behind a counted Filters button.
- An administrator password reset now requires the account to choose a new password at its next sign-in; until then the web interface shows only a change-password screen and the API returns `password_change_required`. The bootstrap `admin` account is not affected.
- Web API errors now always carry a stable snake_case `detail.code` with optional `detail.message` diagnostics, including request validation (`invalid_request`), account and price failures, and unknown API paths (404 `not_found`).
- Ticket timelines show the latest recorded events first; subsequent pages move toward older history.
- Selected-ticket timelines on Jobs now use a table with 10/25/50/All row choices and page navigation.
- Project details uses the opened project context with a common-controls-only header and clearer spacing between metadata and actions.

- Audit retention displays saved limits and explicit zero values for unlimited retention, with localized guidance and validated input conversion.
- Platform System status, Users, Audit and account Settings show their own controls without an unrelated header project selector.
- Metrics uses one project scope across all tabs and CSV exports. Administrator
  All projects scope shows pooled totals and a project breakdown; selecting a
  project focuses every view, with assigned-project privacy for developers.
- Metrics now places project selection within its common reporting controls, with full-width project selection on phones.
- Jobs now aligns wider executor/outcome filters with localized Help explaining recorded data sources and matching rules.
- Jobs now places project selection beside its ticket/start controls and provides localized ticket-number help.
- Import project now opens a standalone page with localized field help and clears the browser-held file and preview when leaving.
- Add project now opens a standalone page with localized field help, server-side clone-path guidance and editable executor-image suggestions.
- Project details now shows redacted project settings and field guidance to assigned developers; administrators edit project configuration, endpoint and estimated prices there.
- Projects now uses sortable, paged rows with pickup, archive and details actions per project.
- Overview summary cards now expand into project or scoped job tables, with project selection in the Projects expansion.

### Fixed

- How ADORE works is now a header help button beside Refresh/About; Overview
  uses sidebar Jobs navigation without a duplicated View all jobs footer link.

- Overview project selection now precedes the selected-project context in the header;
  the primary Overview link defaults to all authorized projects. Periodic job reads
  update quietly without replacing valid tables with loading feedback; failed reads
  still withhold stale evidence, and Overview omits the refresh timestamp.

- Pending web edits reject incompatible scalar types and bind the browser's
  reviewed base; corrupted restored endpoint metadata fails closed. Dev settings
  omit financial caps and credential-bearing URLs remain redacted (#13).

- `metrics.capture_tokens` now appears in a project's Configuration and can be changed there and with `adore config set`; it was hidden and refused as a secret because its name contains "tokens". It must be true or false; any other value is refused and never shown, and other secret-looking names stay hidden and refused.
- The configuration reference and the example configuration now say that a closed source ticket cancels a waiting run (a deleted ticket or a closed-unmerged MR/PR fails it, and a run in review follows its MR/PR first), and that `remove_source_branch` takes effect only on GitLab.
- Configuration edits from the web interface and `adore config set` keep the file's CR LF or LF line endings on every OS; staging a new table in a CR LF file on Windows no longer fails as invalid configuration, and `config set` no longer rewrites every line ending.
- In `allowlist-proxy` egress mode every run gets its own proxy container and egress network: long names end in a short digest of the executor name instead of being cut to a shared value, so a run no longer starts behind another run's proxy or loses it when that run ends. Proxies and networks named by an earlier build are not recognised; remove them by hand (see Recovery and Maintenance).
- `adore cleanup` works only on the selected project's runs: on a host where projects share the agent slug, egress network prefix or worktree root it no longer removes another project's containers, proxies, networks or worktrees, nor a proxy or network another existing executor still uses, and runs with corrupt state keep their worktree and containers.
- Required-field markers now sit on the same line as their label instead of below it.
- Web error banners now show a sentence in the selected language instead of raw error codes, and clear after a later successful action or a view change.
- Add project and Import project now reject invalid project names in the browser; the name pattern had been ignored by browsers that compile patterns with the `v` flag.
- Primary buttons keep readable dark text on the accent colour when the theme follows a dark system setting.
- Improved faint project details text with stronger theme contrast, larger metadata/settings guidance and wrapping for long values.

- The web runtime now reads DCP checkpoint-bearing run state, preserves guarded
  checkpoint publication and human handoff, and shows handoffs as protected
  project history. Pending or completed handoffs cannot be cancelled by a
  queued web command.

- Creating a user and staging configuration no longer show a false form-reset
  error after success. Switching accounts returns to Overview instead of
  leaving an inaccessible administrator page selected.

- Removed repeated page headings so dashboard content starts higher. The
  project selector now sits in the top bar, and narrow metric hints, usage
  actions and account rows wrap without clipped or overlapping text. The About
  dialog stays within the viewport and scrolls internally on small screens.

### Added

- Administration now groups System status, Users, Audit and Settings in a
  sidebar submenu. Administrators can set audit retention by days and stored
  text size; the default remains unlimited. Audit, Jobs and data tables show
  10/25/50/All paging when they exceed ten rows.

- Metrics now has a shared reporting filter and CSV export area with Summary,
  Usage, Quality, Trends and administrator-only Projects tabs.

- Pi usage now retains cache-read and cache-write categories separately from
  total input tokens; the web usage view and CSV expose known categories.

- Offline media can name large, preinstalled executor images as checked
  prerequisites without embedding an additional image archive and verifies
  the Pi binary inside the image without network access.
- Append-only SQLite usage projection with immutable project/source identities,
  conflict-checked replay, and an administrator history rebuild action.
- SQLite schema 11 projects launch coverage and retains per-run journal cursors;
  replay is idempotent and detects changed or truncated earlier evidence.
- Offline installer prerequisites now match actual execution ownership:
  host Git/forge/runtime, with executor CLI readiness checked inside the
  prepared project image without an image pull.
- Immutable web project IDs for browser selection, developer grants, queued
  commands and administrator prices, preserving ownership across profile
  renames and preventing replacement-name inheritance.
- Evidence-denominated reported and estimated USD per completed and
  human-merged job, with stage failures and operator retries shown separately.
- Offline media records forge, executor and runtime host prerequisites; its
  installer offers a read-only preflight and checks image availability before
  creating the target runtime.
- Loopback-only web listener explicitly restricts trusted proxy headers to
  local peers; HTTPS login cookie and raw forwarded-header boundaries are tested.
- Compact collapsible navigation and narrow-width wrapping for small displays
  and high zoom, exercised across phone, tablet and desktop viewport sizes.
- IANA-timezone reporting with daily, Monday-weekly and monthly metrics and
  attributed-usage trends, backed by bundled offline timezone data.
- Explicit executor token-coverage signals so complete zero-token reports
  remain known zero while absent or partial reports remain unavailable.
- Administrator storage status for ADORE home and project run-state volumes,
  with a low-space warning below 1 GiB and explicit measurement errors.
- Versioned per-launch usage observations and dashboard coverage that separate
  reported, unavailable and disabled telemetry without double-counting usage;
  monetary coverage remains administrator-only.
- Stable run/attempt IDs on numeric usage events, with identical journal replay
  counted once and conflicting versioned evidence rejected in summaries and
  web metrics.
- Bounded whole-pair API/worker restart with increasing backoff in the offline
  launcher and an operator-configurable restart limit.
- Administrator staged configuration review and safe apply/discard, with
  conductor and active-work checks and paused pickup for runtime changes.
- Administrator editing of single-value project settings, with the common
  settings first.
- Project detail view linking scoped status and recent jobs to jobs, metrics,
  settings and membership management.
- Exact observed-executor filter for project job pages, with corrupt journal
  identity rejected instead of inferred from today's project configuration.
- Staged configuration apply can reconcile an interrupted metadata update and
  preserves candidate bytes across Windows and Linux.
- About now includes notices for the locked React and Python web dependencies.
- Explicit administrator host-prerequisite diagnostics on project details,
  with bounded command probes and no CLI output in browser responses.
- Searchable, status-filterable project directory with static configuration
  status, executor and UTC last activity.
- Administrator preview and byte-preserving import of an existing ADORE TOML
  configuration, with path/secret validation and paused pickup.
- Administrator project archive and restore retain job, metrics and price history while stopping web and profile-based CLI pickup.
- Optional same-origin React/FastAPI dashboard with local Argon2id accounts,
  admin/developer project RBAC, four languages, light/dark/system themes,
  project and job views, reported metrics and administrator-only costs.
- Durable web operation queue and single-host worker for selected-ticket
  start, retry, cancel and profile polling. Selected-ticket starts retain the
  existing ticket eligibility and draft-publication gates.
- OS/Python-specific offline web bundle with bundled UI and dependency wheels,
  SHA-256 verification and a `pip --no-index` installer.
- The offline installer resolves symlinked host Python executables before
  creating a virtual environment.
- Administrator password reset with session revocation; web config and journal
  views filter credential-bearing fields before sending them to browsers.
- Administrator audit-history view of account, project and operation actions.
- Per-project daily CSV export with monetary values reserved for administrators,
  plus an administrator-only global daily CSV with project/repository identity.
- Immutable administrator-managed USD-per-million-token prices and dated cost
  estimates, shown separately from provider-reported cost.
- Repository-grouped token/job/cost totals in the administrator dashboard and
  live-run usage in project headline totals.
- Separate reviewer-requested MR/PR revision and automatic pipeline-repair
  counts in daily/project metrics and CSV exports.
- Administrator-only per-revision token and cost attribution from journal usage,
  keeping reported, estimated, and unavailable amounts distinct.
- UTC-normalized daily metrics for journal events with timezone offsets.
- Project and administrator-global attributed usage views and CSV exports with
  UTC date, executor and model filters; financial values remain administrator-only.
- A queued web cancellation rechecks run lifecycle and cannot rewrite a run
  that finished before the worker reached the command.
- A worker-side cancellation watcher now rechecks grants across projects
  during any blocking command or poll, signals the conductor, and interrupts the matching executor
  container before normal cancellation cleanup.
- CLI `config set` and web configuration edits now share a local process lock,
  rejecting concurrent ADORE edits without changing the configuration file.
- Public API liveness and worker readiness endpoints, backed by a durable
  heartbeat that stays current during blocking engine commands.
- The About dialog keeps keyboard focus inside and restores it on close;
  compact layouts keep Sign out available in the top bar.
- Project-scoped, bounded Jobs pages with lifecycle and stage filters, plus
  localized status/stage labels and full overview lifecycle counts.
- Clear cached account/project data on browser sign-out and discard responses
  started under the previous session.
- Administrator control-worker readiness status with automatic refresh and
  localized ready, unavailable and check-failed states.
- Inclusive UTC last-update dates and case-insensitive outcome text filters for
  scoped, paged Jobs queries.
- Inclusive UTC daily reporting periods for project/global metrics and CSV,
  with dated-event period totals separate from all-time totals.
- Terminal job elapsed-time sample count, average and median in Metrics, with
  a separate UTC completion-period view.
- Evidence-based reviewer-rework, first-validation and human-merge quality
  rates with eligible-job denominators and open-review counts.
- Account-scoped language and theme preferences with browser fallback before
  login.

### Changed

- Developer grants are bound to the profile creation time, so a profile
  replaced under the same name does not inherit them.
- The web store records the control worker's heartbeat.

- **ADORE now watches the forge pipeline on a published draft and can repair
  it.** Each poll of an `in-review` run reads the verdict through the new
  `Forge.pipeline_status`, normalized to `success`, `failed`, `running`, `none`
  or `unknown`. GitLab reads it inline from the MR document; GitHub requests
  `statusCheckRollup` in a separate `gh pr view` call, so a gh that does not
  know the field cannot break the MR read the poll depends on; Gitea reads the
  pull for `head.sha` and then that commit's combined status. The method is
  contracted never to raise, because the poll is watching a run doing no code
  work: anything unreadable is `unknown`, which is silent.
- New `[review] on_pipeline_failure`, defaulting to `revise`, decides what a
  newly failed verdict does. `revise` starts a governed repair round on the
  same bounded path the revise label uses: a new AEGIS task on the same branch,
  earlier journals preserved, and the executor told that a green pipeline is
  part of this round's acceptance criteria. The round therefore still ends at
  strict validation and a **fresh human approval** before anything is pushed,
  so automatic repair never weakens the delivery gate and ADORE still never
  merges. `notify` posts one comment and waits for a human; `ignore` skips the
  read entirely for a repository with no CI.
- A repair round announces itself on the draft, so a reviewer watching the
  MR/PR learns why commits are about to arrive instead of seeing an unexplained
  push. The notice names the round number and how to opt out.
- Only a CHANGED verdict is a signal, and `pipeline_reported` is cleared when a
  revision starts, so a run waiting days is neither nagged on every poll nor
  repaired twice for one failure, and the pipeline a repair produces is judged
  on its own. Repairs and human-requested revisions share `max_review_rounds`,
  so a permanently red pipeline cannot loop; when the budget is spent the run
  keeps waiting in review with a comment saying so rather than being failed.

### Fixed

- Web-created projects now use an absolute per-project worktree directory,
  preventing retries from targeting a different path when the worker starts
  from another working directory.
- ADORE's host-side checkpoint commits now use the configured agent name and
  email, so a fresh clone does not depend on global Git identity settings.
- Pi JSONL completed-turn usage now records prompt, cached-input and output
  tokens once per turn. Pi's estimated cost remains distinct from a billed
  provider cost, so administrator price rules can supply an estimate.

- **GitHub and GitLab could never open a draft MR/PR.** Before creating one,
  `_publish` probes for an adoptable MR/PR by branch. `gh pr view <branch>`
  reports a branch miss as `no pull requests found for branch`, and
  `glab mr view <branch>` as `no open merge request available for`; neither
  matched the adapters' not-found markers, so the probe raised instead of
  reporting "none yet". The run then failed as `MR_CREATE_FAILED` after the
  push and after a human had approved the candidate, and `adore retry` hit the
  same wall. Both adapters now recognise their CLI's branch-miss wording; a
  genuine transport or auth failure still raises, so ADORE never opens a
  duplicate on a bad read. Gitea was unaffected.
- **A parked run on a busy ticket never resumed.** GitHub and GitLab comment
  reads fetched a single page, which is the OLDEST 100 entries, so a human
  answer past that point was invisible and the run died on
  `CLARIFICATION_TIMEOUT`. GitLab hit the cap fastest because every ADORE label
  change adds a system note. Both adapters now walk pages to the end, as the
  Gitea adapter already did.
- **The revise loop read an empty review thread on GitHub and Gitea.** Both
  routed MR/PR comments through the issue surface only, so a reviewer who
  requested changes through "Review changes" left the revision executor nothing
  to act on and the round was spent on a blind revision. Both adapters now also
  read submitted review bodies and inline diff comments and merge all surfaces
  onto one timeline. GitLab already returned diff notes.
- **An unexpected error killed the poll loop instead of one run.** `run_loop`
  caught only `ForgeError`, so an `IsolationError` from a checkpoint commit, or
  a `KeyError` from an executor template carrying an unsupported brace, ended
  the process and stranded every waiting run; the next start then failed the
  in-flight run as `STALE_WORKING`. The loop now logs any unexpected error and
  continues with the configured backoff, while `KeyboardInterrupt` still stops
  it cleanly.
- **`run_command` let some OS errors escape.** Only `FileNotFoundError` and
  `TimeoutExpired` became a `CommandResult`; a `PermissionError` or a command
  line past the Windows 32767-character limit propagated raw, past every
  handler. Any `OSError` is now reported as exit code 126.
- **The stage prompt contradicted itself about stopping.** The autopilot
  override added for AEGIS 0.13's checkpoint default said "never stop at a
  stage-boundary checkpoint", while the closing paragraph said "stop after the
  current stage". Both are reconcilable, but only via a trailing qualifier, and
  a model resolving the conflict in favour of the louder, earlier instruction
  runs the whole task in one session. Autopilot now speaks only about who
  decides and never about how far to go, and the one-stage rule is its own
  paragraph giving the reason: the session boundary is what gives ADORE a
  checkpoint, a per-stage error budget, and the chance to hand back the last
  failure. Measured on the same model, repository and ticket shape: two
  run-aheads in three launches before, none in six after.
- **A launch that produced nothing inherited the previous stage's transcript.**
  The gate protocol cleared the questions file before each launch so its
  presence afterwards could only mean this launch wrote it, but never applied
  the same rule to the output and stderr streams. An executor exiting zero
  without writing therefore had the previous stage's transcript archived as its
  own evidence and its tokens re-counted against the cost budget. Observed live:
  a build attempt archived byte-identical design output under the same session
  id. The streams are now cleared with the questions file.
- **An executor that ran the whole task in one session lost all its work.** The
  stage guard is a pure function of two stage names, so a skipped stage and a
  task completed in a single launch produce the identical hop and were refused
  alike. The run failed terminally, `adore retry` replayed the same refusal, and
  the completed work sat uncommitted. A forward jump is now accepted when the
  durable journal carries a Log entry for every stage it crossed, recorded as
  `stages-run-ahead` rather than tolerated silently; a genuine skip leaves gaps
  and stays refused. Found in the GitHub pilot, where the same model ran ahead
  in two of three launches and never once in seven on Gitea.
- **A failed publication attempt made the next one fail differently.** Every
  fingerprint refuses a dirty worktree, which is right for the first entry into
  publication, where validation guarantees a clean tree. On the paths that
  re-enter afterwards - the `_publish` retry and the approval-freshness check in
  `retry` - a part-finished bookkeeping attempt leaves files touched, so both
  died terminally on a condition they could have cleared, and a failure budgeted
  for three attempts got one. Leftover work is now settled first. The baseline
  for the candidate-mutation guard is captured once when publication begins and
  reused, so settling cannot launder an unapproved product change into the
  baseline; the guard is stricter across retries, not weaker.
- **A transient push failure ended a fully validated run.** Found in the Gitea
  pilot: a one-off `remote: Failed to authenticate user` from a credential
  refresh hit `PUSH_FAILED`, which is terminal, discarding both the run's work
  and the human approval bound to that exact candidate. The identical command
  succeeded seconds later. Every fetch around the push already retried through
  `_transient`; the push did not, because it returns its outcome as data rather
  than raising. All three push sites now retry on the same bounded schedule. A
  genuine refusal, such as a protected branch or a non-fast-forward, still fails
  every attempt and ends the run loudly.
- **Strict verification ran twice on every successful run.** The
  validate-to-deliver transition verifies, then the next pass of the conduct
  loop reads the task back at deliver and verified again, re-running the whole
  check catalogue and every configured command. Six seconds on the pilot's toy
  suite, a doubled test suite on a real repository. Re-verification is now
  skipped only when the candidate hashes identically to the one the stored
  evidence describes. Recorded deviations are re-harvested from the task the
  loop already read, which the second verification pass had been providing by
  accident.
- **Tool-regenerated files counted as product mutation.** A target repository
  without matching `.gitignore` rules carries its own bytecode and tool caches
  in the candidate, and the delivery gate reruns the configured commands, which
  rewrites them. That could invalidate an approval a human had already given,
  for a file nobody edited. Bytecode and the common tool caches are now excluded
  from the product fingerprint only; they stay in the diff and in
  `changed_files`, because the candidate really does contain them. `adore init`
  additionally flags a target repository that has no `.gitignore`, since that is
  the root cause and only the repository's own rules can separate generated
  files from new source the executor wrote.
- **Gitea reported a pipeline as `running` for a repository with no CI.** Gitea
  answers `state: "pending"` with `total_count: 0` when nothing has reported on
  the commit, so a repository without CI read as a pipeline forever in progress.
  The status count now decides before the state does.
- **A mistyped clone path during `adore init` was misdiagnosed.** git run with
  a missing working directory fails as "no such file" on POSIX and WinError 267
  on Windows, so the new push-access probe reported a missing git binary or a
  raw OS code. It now names the directory that does not exist.
- **An executor command template could carry a placeholder nothing fills.** The
  launcher renders the template with `str.format`, so an unsupported placeholder
  such as `{resume}`, or a shell `${HOME}`, raised `KeyError` at gate time once per
  attempt until the stage budget was spent, with nothing pointing at the cause.
  Configuration validation now rejects unsupported and malformed placeholders
  at setup.
- **`run --once` tracebacked where `run --loop` recovered.** After the poll loop
  was taught to survive an unexpected fault, a single pass still exited with a
  raw traceback for the same cause. That is the mode cron and Task Scheduler
  call, so it now reports the error and exits nonzero like every other CLI
  failure.
- **A missing lifecycle label failed the first run in silence.** The forge
  write that fails at claim time is the same one that would carry the
  explanation, so nothing appeared on the ticket. The reason is now logged to
  the console and `adore.log`, and `Getting_Started.md` lists the nine labels
  that must exist in the repository before the first run.

### Changed

- The executor launcher no longer carries session-continuation machinery. The
  orchestrator always launched with an empty session and never stored one back,
  so the `--session` append, Codex's `resume --last` rewrite, the dead-session
  self-heal relaunch and the per-executor `_extract_session_id` hooks could
  never run; `GateRun.session_id` and the `session` argument are gone with
  them. Every gate was, and remains, a fresh executor session with the durable
  AEGIS journal as the resume authority.
- `adore init` now probes host git push access with `git ls-remote` in the
  target clone. That credential is separate from the platform CLI login and was
  previously unverified until `_publish` reached the push, where a failure
  discarded an approval a human had already given.
- The AEGIS setup guidance pointed at `adore doctor`, a command the CLI does not
  implement; it now names `adore init <profile>`, which repeats the same probe.
- Documented that ADORE reads no forge pipeline, check-run or commit-status
  result, so a failing pipeline on a draft is a human decision point, and that
  `allowlist-proxy` egress needs Podman 4.0 or newer with netavark, since
  Podman 3.x with CNI cannot resolve the proxy alias on an internal network.

### Added

- The approval presentation now leads with the deviations the AEGIS task
  journal recorded: a count and the full text of every `DEVIATION <stage>`
  entry, harvested with the same marker rule AEGIS applies to its own delivery
  report and copied into the persisted validation evidence. Deviations inform
  the approver and never block; a run with none says so explicitly.
- A root `LICENSE.txt` carrying the PolyForm Noncommercial 1.0.0 text that
  every file header already references.
- `[container] selinux_relabel` makes ADORE usable on a host with SELinux
  enforcing, the default on Fedora, RHEL, CentOS Stream, Rocky and Alma.
  `docker/README.md` already named the requirement, but the four bind mounts
  were composed as bare `source:target` and no configuration could add a
  relabel suffix, so those hosts denied the container every read and each stage
  failed on permission denied. `shared` now appends `z` to the host bind mounts
  only - clone, worktree, run io directory, and the generated egress-proxy
  config, which becomes `ro,z` - while the named cache volumes stay untouched
  because the runtime already labels them. The default stays `off`, so Windows,
  WSL and Ubuntu profiles are unchanged. The private `Z` label is refused by
  both configuration validation and the `ContainerManager` constructor: it
  labels content with a per-container category, and the repository clone is
  shared by every run and by host git, so `Z` would bind the clone to whichever
  container mounted it first and break the next run.

### Removed

- `AegisClient.report()`, `AegisClient.evolution()` and
  `WorktreeManager.product_diff_fingerprint()`: publication no longer runs the
  delivery bookkeeping and close-out sessions they served, so the
  `PREMATURE_DONE`, `PUBLICATION_SETUP`, `DELIVERY_EXECUTOR_EXIT`,
  `CANDIDATE_MUTATION`, `DIRTY_DELIVERY`, `CLOSE_OUT_FAILED`,
  `CLOSE_OUT_NOT_DONE` and `CLOSE_OUT_PUSH_FAILED` failures are gone with them,
  and `deliver` is no longer a reset target or a stage-timeout key.
  `RunState.approved_product` is gone.

- Remove the Jobs Advanced filters (exact status, stage, observed executor, outcome text and update dates) and their `/api/v1/jobs-page` parameters; Jobs keeps search and the status group.

- Omit standalone CLI ticket checking mode from GUI settings while preserving its TOML/CLI behavior and web cadence controls.

## [0.13.0] - 2026-09-12

### Changed

- **ADORE's release number tracks the AEGIS line it was verified against**:
  this release jumps from 0.9.0 to 0.13.0, skipping 0.10.0, 0.11.0 and
  0.12.0, so the ADORE version names the newest AEGIS release the companion
  contract was re-proven on. The runtime still conducts the whole supported
  range (AEGIS major 0 at 0.5 or later); the number is a statement about
  verification, not a narrowing of compatibility.
- **ADORE conducts AEGIS 0.9.1 through 0.13.0 without a version-gate or
  parser change**, checked surface by surface against the AEGIS 0.13.0
  template. Re-verified unchanged: the `aegis <major>.<minor>.<patch>`
  version line (0.13.0 passes the major-0, floor-0.5 gate in
  `04_Software/adore/aegis.py`), JSON schema `1` on every payload, the
  `status` list and task documents (the new `interaction:` header key is an
  additive string the decoder already tolerates), the `check` document
  (`findings`/`summary`/`run`, `strict` only under `--strict`; an invalid
  `[interaction]` table arrives as an ordinary `config` finding), the
  single-path `task` creation output, the `report appended to `
  confirmation, and the `evolution` envelope, which changes only under the
  `--compact` flag ADORE never passes.
- One behavioral change closes the only supervision gap the new releases
  open: the executor stage prompt now declares every conducted task
  autopilot-to-deliver by explicit conductor instruction and has the
  executor record `interaction: autopilot` in the journal header. AEGIS
  0.13.0 makes checkpoint mode the default and stops before every stage
  transition, which ADORE would otherwise read as `NO_STAGE_PROGRESS` and
  fail after three attempts. The instruction is the per-task override AEGIS
  itself defines, so no target `aegis.toml` changes; frame keeps its
  path-selection sentence.
- What AEGIS 0.9.1 through 0.13.0 otherwise added falls outside ADORE's
  parsing boundary and is deliberately not modelled: the `trace` and
  `components` commands, `test --no-fallback` and `--dry-run`, the
  project-owned context scaffolds, the Routing-based component page
  template, the compact journal-ledger rules, and the optional host
  integrations for OpenCode, Pi, Codex, Qwen Code and Claude Code. Executors
  reach all of them through `AGENTS.md` like any other AEGIS feature, and
  ADORE's executors read `AGENTS.md` natively inside their container.
  Surfacing summaries, deviations and review verdicts at the approval gate
  remains open work, tracked in `.agentic/tasks/TASK-9aebe1f3.md`.
- Refreshed this repository's own `.agentic/` companion to AEGIS 0.13.0,
  preserving repository configuration and engineering history. The
  companion governs how ADORE is developed and does not ship in the runtime
  bundle.

### Removed

- `AegisClient.anchor()` and `AegisClient.test()`. No orchestrator path
  called them: the executor runs `anchor` and `test` itself during build and
  validate, and ADORE's own verification goes through `check --strict --run`.
  The client now carries only the operations the conductor issues, which is
  the surface re-verified on every AEGIS release.

## [0.9.0] - 2026-08-31

### Changed

- **ADORE's release number now tracks the AEGIS line it was verified
  against**: this release jumps from 0.7.0 directly to 0.9.0, deliberately
  skipping 0.8.0, so the ADORE version names the newest AEGIS release the
  companion contract was re-proven on. The runtime still conducts the whole
  supported range (AEGIS major 0 at 0.5 or later); the aligned number is a
  statement about verification, not a narrowing of compatibility.
- **ADORE conducts the AEGIS 0.8/0.9 releases without a version-gate or parser
  change**, and as with 0.7 the claim was checked surface by surface against
  the AEGIS 0.9.0 template rather than asserted. Re-verified unchanged: the
  `aegis <major>.<minor>.<patch>` version line (0.9.0 passes the major-0,
  floor-0.5 gate in `04_Software/adore/aegis.py`), JSON schema `1` on every
  payload, the `status` list and task documents (the new `parent:` header key
  is additive and the decoder tolerates extra string header keys), the `check`
  document (`findings`/`summary`/`run`, `strict` only under `--strict`; new
  check ids such as `review-state` flow through as ordinary findings), the
  single-path `task` creation output, the `report appended to ` confirmation,
  and the untouched `anchor`/`evolution` envelopes.
- One behavioral change closes the only supervision gap the new features open:
  the executor stage prompt now forbids creating child task journals
  (`task --parent`) in conducted runs. ADORE pins exactly one active task and
  reads only it, so executor work in a child journal would be invisible to
  stage supervision and end in a misleading `NO_STAGE_PROGRESS` failure;
  coordination is the conductor's job, not the executor's.
- What AEGIS 0.8.0 and 0.9.0 otherwise added falls outside ADORE's parsing
  boundary and is deliberately not modelled: the `summary` and `brief`
  commands are not called by the orchestrator (executors reach them through
  `AGENTS.md` like any other AEGIS command); the stage-report, rulings, and
  handoff journal sections are not decoded and do not appear in the status
  JSON; and `[review]` verdict policy belongs to the target repository, whose
  problems reach ADORE generically as check findings. Surfacing summaries,
  deviations, and review verdicts at the approval gate remains open work,
  tracked in `.agentic/tasks/TASK-9aebe1f3.md`.

## [0.7.0] - 2026-08-22

### Changed

- **ADORE conducts the whole AEGIS 0.7 line without a code change**, and that
  claim is now checked rather than asserted. Every contract surface the client
  depends on was re-verified against AEGIS 0.7.2: the `aegis <major>.<minor>.<patch>`
  version line, JSON schema `1` on every payload, the `status` list and task
  document (`header`, `stage`, `step_file`, `done`, `checklist`, `log`), the
  `check` document (`findings`/`summary`/`run`, and `strict` present only under
  `--strict`), and the `report appended to ` confirmation. All unchanged, so
  the version gate in `04_Software/adore/aegis.py` — major 0, floor 0.5 — needed
  no edit. This is the payoff of the 0.6.0 change that replaced the exact-minor
  pin with a major-plus-floor range.
- What AEGIS 0.7.1 and 0.7.2 did add falls outside ADORE's parsing boundary and
  is deliberately not modelled: the new `diagram` and `explain` commands are not
  called by the orchestrator (executors reach them through `AGENTS.md` like any
  other AEGIS command); the reworked `coverage_class` precedence changes which
  findings `check` emits, not the shape ADORE decodes; and the tightened
  `DEVIATION <stage>:` marker is read by AEGIS alone — `04_Software/` has no
  notion of deviations yet. Surfacing them at the approval gate remains open
  work, tracked in `.agentic/tasks/TASK-9aebe1f3.md`.
- Documentation now states the real AEGIS compatibility contract — major 0 at
  0.5 or later, JSON schema 1 — where it previously implied a hard 0.5.x pin
  (`04_Software/README.md`, `config.example.toml`, and the aegis-client
  knowledge page). No documentation names an AEGIS version, so a companion
  release no longer dates the prose.
- Refreshed this repository's own `.agentic/` companion to AEGIS 0.7.2, which
  also narrows AEGIS's scope to software development operations: version
  assignment and release-package construction — this release included — now
  follow the repository's own procedures rather than opening a task journal.
  The companion governs how ADORE is developed and does not ship in the runtime
  bundle.

## [0.6.0] - 2026-08-18

### Changed

- **ADORE no longer pins an AEGIS minor.** The old `SUPPORTED_SERIES = (0, 5)`
  demanded an exact minor, so every AEGIS release broke conduction until ADORE
  was edited in dozens of files. The gate is now a major plus a floor:
  `SUPPORTED_MAJOR = 0` and `MINIMUM_SERIES = (0, 5)`. Any AEGIS `0.y.z` at
  `0.5.0` or newer is conducted, so an AEGIS minor release needs no ADORE
  change at all.
- The floor is not cosmetic: `anchor` and `evolution` arrived in AEGIS 0.5.0
  and this client calls both, so a bare major check would accept a 0.4.x
  payload and then fail partway through a task. The floor turns that into an
  honest refusal at probe. A different major is still refused outright,
  because a major bump is the signal that the companion contract changed.
- `doctor` no longer keeps its own version pattern. It had a second, private
  regex that silently went stale whenever the client's range moved; it now
  derives the answer from the client's constants, so the setup probe and the
  orchestrator can never disagree about what is supported.
- Documentation, doctor guidance, the wizard report, and the executor stage
  prompt no longer name an AEGIS version at all. The supported range is
  declared once, in `adore/aegis.py`, and rendered from those constants where
  an operator needs to read it.
- **BREAKING: the ADORE run-state schema is renumbered from `4` to `1`,** so it
  reads alongside the AEGIS JSON schema instead of carrying the count forward
  from superseded ADORE lines. The number describes the shape of `state.json`
  only and is independent of any ADORE release. Existing schema-4 state is not
  migrated and is refused on load; delete the state root and start fresh. The
  diagnostics now render the number from the constant rather than repeating it
  in prose, so it cannot drift again.
- The superseded-implementation narrative is gone. Documentation, docstrings,
  operator guidance and tests no longer disclaim an earlier ADORE or AEGIS
  line, describe themselves as a "hard break", or promise not to migrate a
  contract nobody runs. The prose states what is supported; anything else is
  refused, and that is the whole rule.
- ADORE's own `.agentic/` payload is upgraded to AEGIS 0.6.0, so the repository
  is governed by the same series it conducts. That payload adds deviation
  notices: an agent states an anomaly in the conversation as a
  `DEVIATION <stage>:` line the moment it records one. ADORE reads the
  schema-1 JSON contract only and is unaffected by it - the notice adds no
  command, no schema field, and no journal change.

### Fixed

- AEGIS invocation timeouts now become retry-budgeted `AEGIS_TIMEOUT` stage
  failures, and clarification expiry uses the validated shared duration parser.
- Clarification resume, review revision, and approval invalidation now restart
  the active wall-clock phase without resetting cumulative budgets; approval
  invalidation also clears stale per-stage failures before re-conduction.
- Container-bound AEGIS calls now use a bounded, shell-quoted file exchange so
  spaced or shell-sensitive ticket text never crosses WSL-wrapped runtime argv,
  while pre-script failures preserve bounded runtime exit diagnostics.
- Executor timeout classification now follows the command runner's typed
  `timed_out` signal instead of guessing from stderr text.
- Human merges now count in aggregate, profile, and dashboard success metrics.
- Cleanup preserves live/unknown locks, operator mutations share the
  single-conductor lock, and `run --once` gives lock advice only for typed lock
  contention.
- Repository probing accepts AEGIS 0.5 adoption stages while active ADORE task
  decoding remains restricted to the seven conduction stages.
- Clarification handoffs are consumed once and removed after durable posting;
  closed source tickets cancel waiting/open-review runs without overriding an
  authoritative terminal MR/PR, while ticket text drift refreshes the persisted
  snapshot with a visible journal/resume note.
- Publication retry rechecks approval, adopts existing open branch MRs/PRs, and
  preserves close-out checkpoint/push recovery for already-done tasks.
- Review intent is consumed only after new-task creation, and terminal status
  replay no longer overwrites a cancelled, done, or failed lifecycle/outcome.
- Cleanup now protects failed-run worktrees, containers and evidence for retry,
  while sweeping exact-prefix orphan executor/proxy containers and egress
  networks with separate report fields even after allowlist mode changes.
- Ticket task-kind selection honors configured feature mappings before
  `workflow.default_kind`, and each budget check reads durable cost only once.
- CLI engine construction now prefers `.env` beside the resolved config,
  falls back to cwd, preserves process-environment precedence, and continues
  to inject only configured executor keys.

### Changed

- Metrics terminal classification now contains only runtime-emitted `done`,
  `failed`, and `cancelled`; the unused worktree commit-count API was removed.
- GitLab/GitHub wizard hosting/URL/visibility prompts were removed. Guidance now
  states that the platform CLI's active/default authenticated host controls
  corporate routing; Gitea retains explicit tea login selection.
- Operator guidance now states that conduction is serial, approval/review have
  no timers by design, failed resources require explicit cancel/delete to
  release, and the repository status describes the current ADORE/AEGIS 0.6
  companion-CLI contract.
- Container lifecycle documentation now states that parked containers are
  stopped and retained for resume or explicit cleanup boundaries.

## [0.5.0] - 2026-08-14

### Added

- Durable schema-4 run state for active and historical AEGIS task journals,
  stage-scoped failure history, validation evidence, candidate fingerprints,
  approval transitions, marker-owned incidents, and a required-notification
  outbox with idempotent ticket/MR replay and deleted-MR fallback.
- Configurable stage and transient recovery limits with defaults of three
  total failed attempts per stage and backoff `[5, 30, 120]`, plus the fresh
  delivery approval label protocol (`agent-approved`).
- Forge-agnostic MR/PR comment create/edit operations for GitHub, GitLab and
  Gitea, and product-diff/candidate fingerprint support in isolation.

### Changed

- The ADORE release identity is intentionally synchronized with its supported
  AEGIS line: ADORE `0.5.0` conducts AEGIS `0.5.x` only.
- **BREAKING: ADORE now supports only AEGIS 0.5.x JSON schema 1.** The grouped
  AEGIS 3.x client, run graph, waiver, schema-3 evidence and delegated
  stage-close behavior are removed. There is no compatibility or migration
  layer for unfinished ADORE 3.x state.
- One ticket now owns a task branch/worktree/container and one or more AEGIS
  `TASK-<id>` journals. Executors own journal stages; ADORE independently
  checks transitions, integrates the target, runs strict verification,
  checkpoints every successful stage locally, and owns all Git/forge writes.
- Publication requires a fresh post-presentation approval label bound to the
  exact candidate and target. Revisions create new AEGIS tasks on the same
  branch and require revalidation plus fresh approval. Publication remains
  draft-only and ADORE still never merges.

### Fixed

- Autonomous work can no longer remain silently stuck. Recoverable failures
  update a durable incident and the third failed attempt aborts; protocol,
  state, containment, policy and global-budget failures abort immediately.
  Notification failure itself stops work and remains queued for poll replay.

- Operator documentation now describes the AEGIS 0.5 hard-break contract,
  Gitea support, journal-stage ownership, fail-loud recovery, approval
  freshness, current defaults, and the released 0.5.0 identity consistently.

