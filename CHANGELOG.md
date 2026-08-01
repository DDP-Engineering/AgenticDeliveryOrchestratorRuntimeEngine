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

- **ADORE 2.0 hard break to AEGIS 2.x - WP3: the conduction loop is
  `next`-driven.** `_conduct` no longer walks a hard-coded gate list. It
  starts the AEGIS run once (`run start <kind> [--quick]`, kind and profile
  resolved from ticket labels through the new `[workflow]` section), then
  loops: `aegis run status` for the authoritative stage, an allowlist check
  against the profile's declared sequence (`STANDARD_STAGES` eight,
  `QUICK_STAGES` four), one executor launch for that stage, then ADORE's own
  verification - `aegis stage show` readiness with no blockers, plus
  `aegis verify run` at validation and delivery, plus the committed-work
  check - and only then `aegis stage close`. ADORE is the delegated approver;
  the executor never closes a stage. When AEGIS reports `complete: true`,
  ADORE's publication phase (new stage name `publication`) integrates the
  target branch, runs one authoritative post-merge `aegis verify run` in
  place of the retired `gates run` + `delivery-preflight` pair, composes the
  MR body from `aegis delivery report` plus the rendered `report.md`, pushes,
  and opens the draft MR. Unresolved questions are now read from the stage
  form through `graph.json`, with the executor's questions file kept as a
  secondary channel. Everything AEGIS-facing fails loud: an unknown stage, a
  stage regression (what an approved `route_to` produces), a blocked
  `run start`/`run status`/`stage close`, and any contract or timeout error
  escalate with the exact AEGIS error and remediation - ADORE never waives,
  routes, or repairs AEGIS state. Journal event names follow the stage
  vocabulary (`stage-launch`, `stage-closed`, `stage-failed`,
  `stage-not-ready`, `verify-failed`, `aegis-run-started`,
  `aegis-run-complete`, `aegis-blocked`, `aegis-contract-failure`); metrics
  read the new names into the existing summary columns.
- **ADORE 2.0 hard break to AEGIS 2.x - WP4: failure evidence and block
  classification.** Retry prompts are now built from the AEGIS 2.x sources, in
  order and bounded: the blocked/failed response itself (`error`,
  `remediation`, stage `blockers[]`, the exact `next` command), then
  `validation-summary.json` (failing gate groups, invariants that do not hold,
  traceability/coverage/working-tree findings - disabled and waived gates are
  reported as such, never as passed), then the schema-3 `graph.json`
  `evidence[]` rows, then the `report.md` excerpts. Journal scraping is gone
  with the AEGIS 1.x `gate.output` event it depended on. A started run whose
  `graph.json` is missing escalates instead of yielding an empty evidence
  block. One helper, `classify_block`, decides what a blocked response means:
  a live `PERSISTENCE-LOCK-TIMEOUT` earns exactly one bounded retry (a
  `stage close` retries the close itself rather than relaunching the executor)
  and then escalates; the rest of the integrity floor and every run-resolution
  error escalate as state repair a human owns; unresolved questions, an
  alignment pause, a `repo-wide` access request, and a `route_to` request all
  park through the normal clarification flow; everything else escalates with
  the AEGIS error, its remediation, and the exact
  `aegis waive add <id> --reason "..."` command a human could run - never an
  automatic waiver. The waive hint is advisory and can never hide the original
  error.
- **ADORE 2.0 hard break to AEGIS 2.x - WP5: executor prompts speak AEGIS
  2.x.** `_GATE_GOALS` became `_STAGE_GOALS`, covering all eight stages plus
  `revise` in the form-first vocabulary: `stage prepare` / `show`, fill the
  generated form at the `artifact` path, `stage apply`, `check prepare` /
  `record` / `run`, `evidence prepare` / `apply`, red-before-green. Every
  prompt now forbids `aegis stage close` (ADORE is the delegated approver) and
  `aegis waive add` (a human decides), relays AEGIS's own exact `next`
  command and form path, and pins the run with `--run <aegis-run-id>` - the
  same pin the orchestrator uses - so a repository holding several runs cannot
  be worked on through the wrong one. Quick runs get implementation and
  validation variants that name the four bypassed stages, walk the manual
  evidence path, and explain that the `not-applicable - quick run` audits are
  the expected state. Questions may be recorded in the form's
  `control.unresolved_questions` or in the questions file; both are named and
  either parks the run.
- **ADORE 2.0 hard break to AEGIS 2.x - WP6: config, wizard, doctor, image.**
  A new validated `[workflow]` section decides how a ticket becomes an AEGIS
  run: `default_kind`, a `kind_labels` map (first configured match wins),
  `quick_label`, and optional `stage_timeout_overrides` that raise or lower
  `[budgets] per_gate_timeout_seconds` per stage. Validation refuses kinds
  AEGIS does not conduct (including the interactive `adoption`), stage-timeout
  keys that are not AEGIS stages or values that are not positive whole
  seconds, and a quick label that neither `default_kind` nor any `kind_labels`
  entry could ever pair with `fix`/`change` - a silently ignored quick label
  would let an operator believe a run was proportional when it was not. The
  `adore init` wizard now asks for the ready/fix/change/quick labels (writing
  neither table when every default is accepted) and probes the target clone
  with the new `doctor.detect_aegis`: the POSIX wrapper must exist,
  `aegis config validate --json` must answer `status: ok`, and the policy must
  report schema 3. Anything else - a missing wrapper, a blocked response,
  unparseable output, a different schema - reads as not-ready with the AEGIS
  detail preserved, and the guidance points at WAEGIS while stating that AEGIS
  1.x is unsupported with no migration path. The executor base image and its
  README now name the AEGIS 2.x CLI and its actual prerequisites.
- **ADORE 2.0 hard break to AEGIS 2.x - WP7: documentation.**
  `01_Documentation/Integrating_A_Runtime_Project.md` is now the AEGIS 2.x
  contract page: the grouped invocation, the four-key envelope and exit-code
  discrimination, run-id pinning, the per-profile stage cycle with ADORE as
  the delegated approver, and a table of the escalation semantics.
  `Operations_Guide.md` gains a "Read an AEGIS escalation" table mapping each
  outcome - park, blocked with remediation, waivable blocker with the exact
  `aegis waive add` command, a held persistence lock, the integrity floor, and
  a contract failure - to what an operator should do.
  `Configuration_Reference.md`, `CLI_Reference.md`, both READMEs, and the
  `AGENTS.md` status paragraph follow the same vocabulary.
- `adore reset --to` now accepts the eight AEGIS stages or `publication`. It
  moves ADORE's own pointer only - AEGIS still owns the governed run's stage,
  which conduction re-reads from `run status` - and it never touches AEGIS
  state.

### Fixed

- **A persistence lock still held at `run start` now escalates instead of
  stranding the run** (review finding ADORE-PY-001 / ADORE-ARCH-004).
  `_ensure_aegis_run` hand-rolled a single retry and then routed the second
  failure through `_handle_block`, which only *logs* a `BLOCK_RETRY`
  classification; a second consecutive `PERSISTENCE-LOCK-TIMEOUT` therefore
  left the run in `working` forever - never parked, never escalated, and
  invisible to the poll loop. It now uses the same iterative `_retryable`
  loop as the stage loop, so the second lock block takes the existing
  exhausted-lock path and the run ends `failed` with the documented "the
  persistence lock is still held" reason.
- **The stage-regression guard no longer crashes at the end of the sequence**
  (review finding ADORE-PY-003). Once ADORE closed the last stage
  (`delivery`), `_checked_stage` indexed `expected[closed_index + 1]` while
  composing the regression message - out of range - so AEGIS re-reporting
  `delivery` without setting `complete` raised an `IndexError`. `IndexError`
  is not an `AegisError`, so it escaped `_conduct`'s escalation handler and
  crashed the poll loop with a raw traceback instead of failing the run. The
  boundary case now states the regression generically and raises the intended
  `AegisProtocolError`, which escalates the run deterministically.
- **The container exec seam can no longer run unbounded** (review finding
  ADORE-PY-002). `ContainerManager.exec` defaulted `timeout` to `None` and
  forwarded it explicitly, so `run_command`'s own 600 s default never applied
  and `subprocess.run(timeout=None)` was reached by every caller that did not
  name a budget - `verify_required_tools` (operator-configured
  `required_tool_checks`, run at every provision) and `_stage_host_auth`'s
  mkdir/cp among them. A hung check or a wedged container runtime blocked
  `_provision` and with it the whole single-threaded poll pass, with no other
  layer of protection. `exec` now defaults to `util.DEFAULT_COMMAND_TIMEOUT`
  and resolves an explicit `None` to it: at that seam `None` means "use the
  default bound", never "no bound".

### Removed

- **`adore/gates.py` and its AEGIS 1.x verbs** (`invariants`, `status`,
  `resume`, `gates run`, `delivery-preflight`, `report`), together with
  `tests/test_gates.py` and `05_SoftwareDocu/Component_Gates.md`. They are
  replaced by `adore/aegis.py`; there is no compatibility path.
- The `.agentic/.workspace/state/current_run` pointer read. Run-local AEGIS
  files are addressed by the run id ADORE persisted, so the seam that broke
  once in 1.x is gone.

### Added

- **ADORE 2.0 hard break to AEGIS 2.x - WP1: the AEGIS client
  (`adore/aegis.py`).** One component owns the whole AEGIS-facing contract:
  it invokes the grouped CLI as `bash .agentic/tools/run.sh <group> <action>
  [--run <id>] --json` inside the run's container, pins the AEGIS run id
  captured at `run start` on every later call (the worktree `current_run`
  pointer is never read again), and parses the stable four-key envelope into
  a frozen `AegisResponse` with `ok`/`blocked`/`failed`/`complete`/`error`/
  `code`/`remediation` helpers. Exit 0 and exit 1 are workflow signals
  returned as data; everything else fails loud - exit 2 (usage error, or the
  wrapper finding no Python runtime), a timeout, unparseable or non-object
  output, a missing or mistyped envelope key, a status contradicting the exit
  code, and a `run start` without a well-formed run id all raise
  `AegisProtocolError`/`AegisTimeoutError` so the conductor escalates instead
  of degrading. `--quick` is rejected client-side for any kind but `fix` and
  `change`, and `waive add` is deliberately not wrapped: waiving stays a
  human decision. Wrappers: `run_start`, `run_status`, `run_resume`,
  `stage_show`, `stage_close`, `verify_run`, `delivery_report`, `waive_list`,
  `config_validate`. Covered by 16 offline tests over a fake exec seam.
- **ADORE 2.0 hard break to AEGIS 2.x - WP2: the AEGIS run id is persisted.**
  `RunState` gains `aegis_run_id`, written into `state.json` at
  `aegis run start` and never cleared, so a restart or a resume pins the same
  governed run with `--run` instead of starting a second one or consulting the
  worktree-local `current_run` pointer. A state file written before the field
  existed loads as `None` - "no AEGIS run started yet" - purely through the
  dataclass default; no migration code exists. Covered by round-trip tests
  with and without the field.
- Gitea forge support behind the same adapter interface (`[platform]
  kind = "gitea"`), implemented over the `tea` CLI (>= 0.15 required for
  `tea api`; verified against tea 0.15.0 / Gitea 1.25.4). Reads and
  comment/PR writes go through `tea api` with the adapter enforcing the HTTP
  status line itself (tea exits 0 even on HTTP errors), endpoints are built
  without a leading slash (a tea prefixing quirk), selection paginates at the
  Gitea 50-item page cap guided by `X-Total-Count`, drafts use the `WIP: `
  title prefix, and label operations go through `tea issues/pulls edit`
  (name-to-id resolution). New optional `[platform] login` pins the tea login
  name; the `adore init` wizard, `doctor` probes (`tea whoami` - tea has no
  `auth status` and exits 0 for unknown subcommands), guidance texts, and
  config validation (gitea repos are strictly `OWNER/REPO`; `login` rejected
  for other kinds) cover the new platform end to end, with offline
  happy/negative tests for every tea quirk. Selection post-filters on the
  ready label because Gitea silently ignores a `labels=` filter naming a
  label the repository does not have (returning every open issue) - found
  and pinned during the live pilot against Gitea 1.25.4, which verified the
  full mutating round-trip (labels, comment post/edit, WIP draft PR by
  number and branch, PR label clearing, shared issue/PR index space).

### Changed

- The deployment installers (`install-ubuntu.sh`, `install-windows.ps1`)
  accept `tea` as the platform CLI in their prerequisite check, so a
  Gitea-only host no longer fails the install with "neither glab nor gh
  found".

### Fixed

- MR/PR number parsing from web URLs now recognizes Gitea's plural
  `/pulls/<n>` shape (previously only GitLab `merge_requests` and GitHub
  `pull`), so the post-MR poll can track terminal states on Gitea.

## [1.2.0] - 2026-07-25

### Added

- `adore config set <section.key> <value>` is now implemented (it was a stub).
  It edits one scalar in the resolved config file (same precedence as every
  other command), infers the value type, preserves comments and other keys,
  refuses secret-looking keys (they belong in `.env`), and writes only when the
  whole resulting config still loads and validates (atomic tmp + replace).
- The orchestrator now prepends the target workflow's read-only `resume`
  bootstrap brief to an executor relaunch prompt (`gates.workflow_resume` +
  `Orchestrator._workflow_orientation`), so a fresh executor session - a gate
  retry, a delivery fix, a revise round, or a run resumed mid-workflow after a
  restart - orients from the authoritative run state (current and next stage,
  intent, alignment, specs, checks, recent evidence, cited requirements)
  instead of re-deriving it. It is best-effort and payload-agnostic: a
  target-repo workflow CLI that predates the `resume` verb exits non-zero and
  the brief is simply omitted, and a fresh run starting at intake gets none on
  its first launch. Secret values are redacted like the failure context.

### Changed

- Parametrized the executor image group id: `Dockerfile.executor-base` now takes
  `ARG USER_GID` (alongside `USER_UID`) and the Ubuntu installer builds with
  `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)`, so the
  container user/group match the host account that runs ADORE without manual
  ACL/`chmod` remediation on hosts where the UID/GID is not 1000.
- Operator documentation refresh: `Integrating_A_Runtime_Project.md` now states
  the agentic workflow (`.agentic/tools/run.sh`) as an explicit target-project
  prerequisite - ADORE verifies every gate through it, so a repository without
  it cannot be conducted - including the project-image runtime implications;
  `Operations_Guide.md` documents `adore config set` for safe single-key edits;
  and the product-version references across `01_Documentation` were rolled from
  1.0.0 to 1.2.0 (container image tags are versioned separately and unchanged).

### Fixed

- Widen the staged executor `auth.json` (host-auth pilot) to mode 0644 in the
  run's io dir so the container user can read it even when its UID does not
  match the host on a hand-built image; the copy is transient and deleted
  immediately after staging.

## [1.1.0] - 2026-07-24

### Added

- `[budgets] per_gate_timeout_seconds` (default 1800): an independent bound on a
  single executor launch, separated from `max_wall_clock_seconds` (the total
  run ceiling). The two were previously one knob, so a generous per-gate limit
  forced an equally generous total and vice versa. Existing configs keep
  working; the new key is optional.

### Changed

- The single-instance lock now reclaims a lock left by a **crashed** poller on
  the same host (its recorded pid is provably dead), instead of wedging every
  future start until a manual `adore cleanup`. This closes a boot-loop under
  `systemd Restart=on-failure` / Task Scheduler after a hard crash. A live
  owner, an unreadable lock record, or a lock written on a different host are
  still never stolen (fail closed). The lock record now also carries the
  owner's `host`.
- An in-review run whose merge request/PR is **deleted** on the platform now
  ends the run after a short grace (a few polls, to ride out a transient 404)
  instead of staying in-review and re-logging "not found" on every poll
  forever. State is kept for audit.
- Resume detection no longer mistakes a **quoted** reply for the agent's own
  comment: when a human replies by quoting ADORE's clarification comment, the
  carried-over hidden marker sits on blockquote lines and is ignored, so the
  answer is seen and the run resumes.
- Executor gate scripts wrap the command in a `{ ...; }` group so the
  output/stderr redirection covers a whole compound command template, not just
  its last stage.
- A new run fetches the remote before creating its worktree, so it branches
  from an up-to-date base instead of a possibly stale local ref (best-effort;
  an offline fetch never blocks provisioning).
- Selection no longer truncates the ready-ticket pool at 100: the GitLab
  adapter paginates (its API caps per-page at 100) and the GitHub adapter reads
  up to 500, so a high-priority ticket beyond the first page is not missed.
- Hardened the executor forbidden-flag guard (shlex tokenizing, `--flag=value`
  form) and made `force_rmtree` use `onexc` on Python 3.12+.
- Reorganized the operator documentation into a complete, project-agnostic
  path covering installation, credentials, runtime-project integration,
  operations, recovery, configuration, and the CLI.
- Made the root README the primary repository entry point and refreshed the
  internal component documentation to match current implementation contracts.
- Extended runtime bundles with the canonical operator documentation and made
  their embedded documentation links valid after unpacking.
- Strengthened release consistency validation to inspect archive layout,
  exclusions, embedded package metadata, documentation entry points, and
  credential guidance.
- Replaced the tracked pilot configuration, deployment guidance, and test
  fixtures with generic runtime-project terminology.

### Fixed

- **GitHub revise cycle could never trigger.** `get_merge_request` requested
  `--json number,state,url,isDraft` but read `data["labels"]`; because `gh`
  returns only the requested fields, the label list was always empty, so the
  revise-label trigger in the post-MR poll never fired on GitHub (GitLab was
  unaffected). `labels` is now in the requested field set, with a regression
  test that pins the selection so it cannot silently regress.
- Configuration validation now rejects `reminder_after >= answer_timeout`
  (a reminder that could never fire before the run is released) and a
  non-positive `per_gate_timeout_seconds`.
- The files-touched budget now counts a rename as one file (its destination)
  and strips git's quoting, instead of counting the `"old -> new"` string as an
  odd path.
- Removed dead code (`_TERMINAL_EVENTS` in the metrics module).
- Realigned the workflow active-run pointer ADORE reads for retry-prompt
  failure evidence. AEGIS moved the pointer from `.agentic/current_run` to the
  worktree-local `.agentic/.workspace/state/current_run` and retired the old
  path (AEGIS payload 1.1.0/1.2.0). ADORE still read the retired path, so after
  a failed gate the pointer resolved to nothing and `graph.json`/`journal.jsonl`/
  `report.md` failure evidence was silently dropped from retry prompts, leaving
  only the raw exit-code/stderr tail. The orchestrator now reads the current
  pointer location; the `.agentic` CLI verbs, run artifacts, and journal schema
  ADORE consumes are otherwise unchanged, so no other contract adjustment was
  required.

### Removed

- Removed project-specific executor image material and project-specific
  references from source, documentation, generated bundles, and release notes.

## [1.0.0] - 2026-07-16

### Changed

- Renamed and rebranded the project as **ADORE 1.0.0** through a breaking,
  compatibility-free hard cut.
- Renamed the Python distribution, package, and command to `adore`; changed
  the environment, global home, project state, logs, questions file, forge
  marker, branch, container, image, cache, service, task, and runtime bundle
  identities to their ADORE forms.
- Centralized runtime branding constants and added a release-consistency check
  for package metadata, lockfile, images, deployment names, documentation,
  delivery artifacts, and forbidden pre-1.0 identity tokens.

### Removed

- Removed all compatibility, fallback, migration, import, and alias behavior
  for the pre-1.0 project identity. Existing run behavior is otherwise
  unchanged.

### Fixed

- Fixed the allowlist-proxy Squid configuration to use proxy-owned log paths;
  the live Docker probe now permits configured hosts while denying others.

## [0.6.0] - 2026-07-15

### Added

- Added visual operator cheat sheets for the pre-1.0 implementation covering setup, ticket
  readiness and labels, profiles and container images, monitoring and
  steering, and failure recovery.

### Changed

- Refreshed operator documentation against the pre-1.0 implementation,
  including current package names, executor support, credential guidance, and
  runtime-project image examples.
- Docker executor base image now accepts `--build-arg USER_UID=$(id -u)` so
  the container user matches the host user, preventing bind-mount ownership
  mismatches. Podman deployments continue to use `run_args = ["--userns=keep-id"]`.
  Updated Dockerfile, deploy scripts, config example, and documentation.

## [0.5.1] - 2026-07-08

### Changed

- Fed existing `.agentic` failure evidence into gate retry and delivery-fix
  prompts, with bounded excerpts and configured executor-secret redaction.

## [0.5.0] - 2026-07-08

### Added

- Persisted immutable executor-launch archives under each run's io directory
  and added a project-owned rotating process log for scheduled run commands,
  improving auditability for Task Scheduler and `--once` runs.

## [0.4.0] - 2026-07-07

### Added

- Added `[container.egress]` with `open`, `none`, and `allowlist-proxy` modes,
  including the generic Squid proxy image, per-run proxy/network lifecycle,
  cleanup sweep support, deployment guardrails, and live runtime verification
  coverage.

### Changed

- Clarified repository folder ownership and AI-agent documentation update
  responsibilities across planning, documentation, tools, software
  documentation, and delivery folders.

## [0.3.1] - 2026-07-07

### Changed

- Improved assisted-init fixed-choice prompts to show numbered options while
  still accepting literal choice text, and anonymized setup/example references.

## [0.3.0] - 2026-07-07

### Changed

- Split executor images into a generic base and a runtime-project-specific
  image with the required project tooling; live-verified a project image on
  rootless Podman through `docker/verify-runtime.sh`.

### Added

- `[container] required_tool_checks` for fail-fast validation that a selected
  runtime-project image contains required build/test tools.

## [0.2.0] - 2026-07-06

### Added

- Runtime bundle packaging scripts in `02_Tools/` for PowerShell, cmd.exe, and
  Bash; bundles include the existing Task Scheduler/systemd deployment scripts.
- Release versioning and changelog rules aligned with the workflow-template
  convention: root changelog plus synchronized `pyproject.toml` and
  package release metadata.
- Initial repository scaffold: top-level folder structure
  (`00_Planning`, `01_Documentation`, `02_Tools`, `04_Software`,
  `05_SoftwareDocu`, `07_Delivery`, `09_Others`) mirroring the Agentic
  Development Workflow Template.
- Per-folder README files describing each folder's intended content.
- Root `README.md` and `AGENTS.md` describing the project scope and rules.
