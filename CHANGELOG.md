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

### Fixed

- Gitea host sign-in checks use the supported named-login API after GUI connection. Repository connection opens a closable modal beside host checks, with an aligned HTTP consent checkbox.

- Make host-check details collapsible with a persistent verdict, clarify the checked
  configuration version and explain external repository sign-in under the service account.

- Explain project host-prerequisite checks with clear verdicts, purposes and corrective
  actions, one checked-at/revision line, honest unavailable model checks, and
  validated project-bound browser evidence.

### Added

- Project-scoped repository connection from the GUI for Gitea, GitHub and GitLab,
  with bounded account/repository verification, protected token storage, isolated
  worker/readiness CLI use and secret-free results.

- Structured redacted web change evidence with known before/after and revisions,
  distinct preparation/application/discard results, atomic identity/access/queue
  evidence, durable filesystem uncertainty and idempotent completion. Explicit
  web schema-14 upgrade preserves legacy unknowns and rejects corruption.
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
  activity and waiting evidence retain honest legacy/usage unknowns; strict local
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

- Consolidated project Summary into information/action tiles and compact job lists; integrated explicit host checks and accessible modal project deletion.

- Simplified Projects to a read-only directory with a Repo forge column; consolidated project identity and navigation, with lifecycle actions on dedicated Summary.

- Projects describes new-ticket pickup as Monitoring (Active/Paused) with
  consistent pause/activate actions and concise project rows and summary.

- Compact Overview attention and active tables with one project selector and Details;
  worker faults remain visible, while reporting dates, timezone, consumption and
  repeated scope explanations stay out of the overview.

- Project hubs separate pickup from revision/time-bound verification and expose
  Summary, Settings and History alongside existing Admin Prices/Access and
  Jobs/Statistics links. Missing legacy activity remains unknown; unsafe or corrupt
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
- An administrator password reset now requires the account to choose a new password at its next sign-in; until then the web interface shows only a change-password screen and the API returns `password_change_required`. The identity database moves to schema 13; existing accounts, including `admin`, are not affected.
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
- In `allowlist-proxy` egress mode every run gets its own proxy container and egress network: long names end in a short digest of the executor name instead of being cut to a shared value, so a run no longer starts behind another run's proxy or loses it when that run ends. Upgrade note: finish, cancel or re-provision parked long-named `allowlist-proxy` runs from an earlier release first (see Recovery and Maintenance).
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
  the selected executor binary inside the image without network access.
- Append-only SQLite usage projection with immutable project/source identities,
  conflict-checked replay, and an administrator history rebuild action.
- SQLite schema 11 projects launch coverage and retains per-run journal cursors;
  replay is idempotent and detects changed or truncated earlier evidence.
- Offline installer prerequisites now match actual execution ownership:
  host Git/forge/runtime, with executor CLI readiness checked inside the
  prepared project image without an image pull.
- OpenCode endpoint staging now records the supported protocol, bounded
  request timeout and optional HTTPS custom-CA path, and shows the resulting
  non-secret settings in the pending review.
- Clearing the endpoint CA field removes an earlier custom-CA reference when
  switching back to an HTTP or default-trust endpoint.
- Immutable web project IDs for browser selection, developer grants, queued
  commands and administrator prices, preserving ownership across profile
  renames and preventing replacement-name inheritance.
- Evidence-denominated reported and estimated USD per completed and
  human-merged job, with stage failures and operator retries shown separately.
- OpenCode local endpoints can use an allowlisted executor environment-key
  reference; inline provider configuration is omitted from API config reads.
- Administrator local-model readiness checks from a disposable executor
  container with project egress policy, bounded tool-stream probe and no image
  pull or host-connectivity fallback.
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
- OpenCode local endpoint configuration now writes an OpenAI-compatible provider
  override for the selected model, rather than relying on a base URL variable.
- The OpenCode web form now saves the model ID and local endpoint URL together
  in one validated configuration revision.
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
  a separate UTC completion-period view and explicit undated-history coverage.
- Evidence-based reviewer-rework, first-validation and human-merge quality
  rates with eligible-job denominators and open-review counts.
- Account-scoped language and theme preferences with browser fallback before
  login and a schema-6 migration preserving existing identity data.

### Changed

- Web identity schema 4 binds developer grants to the profile creation time.
  Upgrading from schemas 1-3 clears older name-only grants; administrators must
  reassign access to the current profiles.
- Web identity schema 5 adds worker heartbeat storage while preserving existing
  users, sessions, grants and prices.

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

- Assisted and web project setup now reject host-auth for Pi and Qwen before
  creating a profile; configuration validation enforces the same executor
  boundary instead of failing during job provisioning.
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
  launcher renders the template with `str.format`, so `{resume}` on a non-Codex
  executor, or a shell `${HOME}`, raised `KeyError` at gate time once per
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
  AEGIS journal as the resume authority. Codex's `{resume}` template slot is
  still accepted and always resolves to empty, so existing profiles keep
  working.
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

