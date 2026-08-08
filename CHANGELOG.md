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

- **Graph-backed clarification answers now reach the executor.** A resumed
  AEGIS stage whose applied form still held its original unresolved question
  used to park again before launching, so the executor could never reconcile
  the human answer or clear the form. An answered clarification thread now
  bypasses only that pre-launch park, is delivered with explicit reconciliation
  instructions, and remains guarded by the existing post-launch graph check:
  any question the executor does not clear parks the run again.

### Changed

- **Retarget the unreleased hard break to ADORE 3.0 / AEGIS 3.x.** The
  adaptation plan now pins AEGIS 3.0.0 and WAEGIS 3.0.0 from the authoritative
  source checkout, documents the unchanged runtime contract and the WAEGIS 3
  pilot-provisioning boundary, and renames current-facing ADORE/AEGIS product
  labels accordingly. The installed ADORE version remains 1.2.0 until CR1-CR6
  and the live pilot are complete. The user-selected 3.0.0 version will be cut
  only as the final action after that acceptance evidence is green.
- **WSL2 bind-mount teardown-race retry moved from the core loop to the
  isolation layer** (review finding ADORE-ARCH-009). `_TEARDOWN_RACE_MARKERS`,
  `_is_teardown_race`, and the retry-with-backoff lived in `orchestrator.py`,
  against `AGENTS.md`'s "no OS-specific glue in the core loop" rule.
  `WorktreeManager.remove` (`isolation.py`) now retries the whole removal
  past the transient mount-release signatures itself, with an injectable
  `sleep`; the orchestrator's `_teardown` shrinks to one call plus a husk-log
  line on failure. `orchestrator.py` now contains no WSL error-signature
  strings. Behavior is unchanged (same markers, same backoff, same husk
  fallback); the two orchestrator-level teardown-race tests moved to
  `test_isolation.py` against the real `WorktreeManager`, and a single
  orchestrator-level test now covers the simplified pass-through.
- **Config/doc surface corrected to match runtime enforcement** (review
  findings ADORE-ARCH-005, 006, 007, 011). Nine settings were documented or
  exampled as live behavior the runtime does not have: the entire
  `[reconcile]` section (`on_ticket_deleted`/`on_ticket_closed` values are
  never consulted - reconciliation hardcodes their default behavior and only
  for parked runs; `on_trigger_removed` has no implementation at all -
  adding the hold label mid-run does not stop an active run, use
  `adore cancel <run-id>`); `[readiness] require_known_component` and
  `max_scope_hint` (only `require_acceptance_criteria` and
  `require_priority_label` actually filter pickup); and four more dead
  settings (`container.parked_state`, a redundant twin of `keep_parked`;
  `review.review_reminder_after`, no MR-reminder nudge exists;
  `metrics.capture_resource`, no resource probing exists; `executor.mode`,
  the conductor is unconditionally thick). `Configuration_Reference.md` and
  `config.example.toml` now carry an explicit STATUS/"not yet
  consulted"/"not implemented" caveat on every one of these rows instead of
  presenting them as working knobs. Also fixed `config.example.toml`'s
  `[platform] kind` comment, which named only `"gitlab"`/`"github"` despite
  the Gitea adapter (`forge/gitea.py`) being fully supported - it now lists
  all three adapters and the commented gitea-only `login` key. No behavior
  changed; `[budgets] max_cost_usd` and the escalation-reason-on-ticket claim
  were already accurate after the ADORE-ARCH-003/002 fixes and needed no
  further edits.
- **Forge adapters share their CLI-invocation plumbing** (review finding
  ADORE-PY-004). `_parse_json`, `_run`, and the marker-based `_is_not_found`
  were byte-for-byte duplicated across `forge/gitlab.py`, `forge/github.py`,
  and `forge/gitea.py` (already drifting once: Gitea's not-found handling
  lives in its `_api` HTTP-status logic instead). All three now come from the
  shared `Forge` base in `forge/base.py`; `GitHubForge` keeps its own
  `_NOT_FOUND_MARKERS` override for the "could not resolve" text `gh`
  reports that `glab`/`tea` do not. Every error message format is unchanged;
  the existing forge adapter tests pass without modification.
- **ADORE 3.0 hard break to AEGIS 3.x - WP3: the conduction loop is
  context-driven.** `_conduct` no longer walks a hard-coded gate list. It
  starts the AEGIS run once (`run start <kind> [--quick]`, kind and profile
  resolved from ticket labels through the new `[workflow]` section), then
  loops: `aegis run status` for the authoritative stage, an allowlist check
  against the profile's declared sequence (`STANDARD_STAGES` eight,
  `QUICK_STAGES` four), validates the bounded schema-1 `run context` before
  every fresh executor session, and launches at most one executor for that
  stage. A genuinely unprepared stage is safely prepared first; an applied,
  ready stage found after restart skips the executor. ADORE then performs its
  own
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
  `aegis-run-complete`, `aegis-blocked`, `aegis-contract-failure`); a terminal
  AEGIS `abandoned` outcome never enters publication. Metrics
  read the new names into the existing summary columns.
- **ADORE 3.0 hard break to AEGIS 3.x - WP4: failure evidence and block
  classification.** Retry prompts are now built from the AEGIS 3.x sources, in
  order and bounded: the blocked/failed response itself (`error`,
  `remediation`, stage `blockers[]`, the exact `next` command), then
  `validation-summary.json` (failing gate groups, invariants that do not hold,
  traceability/coverage/working-tree findings - not-enforced, not-applicable,
  and waived checks are reported as such, never as passed), then the schema-3 `graph.json`
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
  error. Artifact ingestion is a single strict trust boundary: the pinned path
  must be contained, POSIX-relative, regular, no larger than 4 MiB, and strict
  UTF-8. Graph schema/profile/run identity, validation status and gate
  vocabulary, evidence links/results, waiver truth, quick RED/GREEN proof,
  working-tree/audit truth, and delivery-report path/heading are validated and
  cross-checked. Missing, escaped, special, oversized, corrupt, cross-run, or
  contradictory evidence raises typed `AegisArtifactError` and blocks
  publication. Run summaries persist a separate `governance_outcome` so an
  accepted waiver cannot become a clean pass in reports.
- **ADORE 3.0 hard break to AEGIS 3.x - WP5: executor prompts are policy-thin
  and context-led.** `_STAGE_GOALS` names the objective, while the validated
  AEGIS `run context` owns `required_reads`, checklist, artifact availability,
  and exact procedure. Prompts pin the run and forbid stage close, waiver,
  run/profile changes, routing, and remote Git/forge operations. They do not
  replay AEGIS mechanics. For a new quick run, the executor must create and
  register a real focused check before changing code, record its RED result,
  then record the GREEN result from the same check after the change. Exit zero,
  manual assertions, and a nothing-ran path cannot satisfy INV-3. The
  `QUICK-SCOPE-ADVISORY` reason and exact full-run restart command are surfaced
  without blocking the proportional run.
- **ADORE 3.0 hard break to AEGIS 3.x - WP6: config, wizard, doctor, image.**
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
  `bash .agentic/tools/run.sh --json config validate` must answer `status: ok`, and the policy must
  report schema 3. Anything else - a missing wrapper, a blocked response,
  unparseable output, a different schema - reads as not-ready with the AEGIS
  detail preserved, and the guidance points at WAEGIS while stating that AEGIS
  1.x is unsupported with no migration path. The executor base image and its
  README now name the AEGIS 3.x CLI and its actual prerequisites.
- **ADORE 3.0 hard break to AEGIS 3.x - WP7: documentation.**
  `01_Documentation/Integrating_A_Runtime_Project.md` is now the AEGIS 3.x
  contract page: the grouped invocation, the four-key envelope and exit-code
  discrimination, run-id pinning, the per-profile stage cycle with ADORE as
  the delegated approver, and a table of the escalation semantics.
  `Operations_Guide.md` gains a "Read an AEGIS escalation" table mapping each
  outcome - park, blocked with remediation, waivable blocker with the exact
  `aegis waive add` command, a held persistence lock, the integrity floor, and
  a contract failure - to what an operator should do.
  `Configuration_Reference.md`, `CLI_Reference.md`, setup/recovery/operator
  cheat sheets, both READMEs, and the `AGENTS.md` status paragraph follow the
  same vocabulary. They record the canonical global-option command order,
  approved WAEGIS 3 provisioning boundary, context-led stage procedure, quick
  real RED/GREEN contract, strict artifact trust boundary, truthful waiver /
  not-enforced / N/A reporting, and ADORE-cancel versus human AEGIS-abandon
  ownership boundary.
- `adore reset --to` now accepts the eight AEGIS stages or `publication`. It
  moves ADORE's own pointer only - AEGIS still owns the governed run's stage,
  which conduction re-reads from `run status` - and it never touches AEGIS
  state.
- The deployment installers (`install-ubuntu.sh`, `install-windows.ps1`)
  accept `tea` as the platform CLI in their prerequisite check, so a
  Gitea-only host no longer fails the install with "neither glab nor gh
  found".

### Fixed

- **CR6 real delivery-context routing.** The schema-1 parser inferred every
  full-stage reference as `agentic-development/reference/<stage>.md`, but the
  authoritative AEGIS 3 payload routes standard/quick delivery through
  `agentic-delivery/SKILL.md` and reports that one path as both `reference`
  and `skill`. ADORE now locks that exact exceptional mapping and de-duplicates
  it in the expected `required_reads` sequence. Happy and stale-reference
  negative tests cover the direct-context trust boundary.
- **CR6 applied-ready validation restart loop.** ADORE used to run
  `aegis verify run` and only then check that validation work was committed.
  AEGIS verification necessarily persists graph, evidence, and summary
  artifacts, so a successful verification made its own worktree dirty and
  caused another validation executor launch; the loop repeated until a
  budget failed. The committed-work check now runs before verification.
  Applied-ready restart state can skip the executor, verify, and close while
  preserving AEGIS's fresh artifacts for the next governed commit. A
  regression test makes verification dirty the fake worktree and proves no
  relaunch occurs.
- **CR6 full-run file-budget sizing.** The AEGIS 3 pilot reached 45 changed
  paths at the end of the check stage, before implementation, because durable
  forms, requirement/check snapshots, evidence, graph, and journal correctly
  count against the same scope bound as product files. The legacy 40-file
  default therefore made a healthy full run impossible. Config, wizard,
  example, and operator-reference defaults are now 120: still explicit and
  bounded, with headroom for the governed artifacts plus the product diff.
  Tests lock the new happy-path default and the fail-closed zero boundary.
- **CR6 cross-platform acceptance findings.** WSL mount conversion now
  normalizes Windows separators explicitly instead of delegating to the host
  OS's `Path` flavour, so Windows drive paths produce the same `/mnt/<drive>`
  mount on Windows and Linux. The Windows and POSIX runtime packagers now share
  a fail-closed standard-library ZIP writer that emits canonical `/` member
  names; Windows `Compress-Archive` had written backslash members that did not
  extract to the documented tree on Linux. Happy and negative regression tests
  cover portable ZIP creation and invalid bundle input.
- **A genuine inner exit 124 is no longer misreported as ADORE's own
  timeout** (review finding ADORE-ARCH-010). `docker exec` propagates
  whatever exit code the INNER command used, so a payload legitimately
  exiting 124 for its own reasons (its own `timeout(1)` wrapper, for
  example) was indistinguishable from ADORE's wrapper bound expiring -
  `AegisClient.invoke` keyed `AegisTimeoutError` on the raw exit code alone.
  `CommandResult` now carries a `timed_out` flag, set ONLY by `run_command`
  when its own `subprocess.TimeoutExpired` fires - never inferred from
  `exit_code == 124` - and `invoke` keys `AegisTimeoutError` on that flag
  instead. A genuine inner exit 124 now falls into the ordinary
  exit-code-outside-0/1 `AegisProtocolError`, naming the exit code, so
  escalation messages blame the right component. The now-dead
  `TIMEOUT_EXIT_CODE` constant was removed.
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
- **A forge failure while parking no longer strands the run** (review finding
  ADORE-ARCH-008). `_park` posted the clarification comment unguarded, so a
  transient platform error there raised past `_conduct_stages` (which catches
  only `AegisError`) into `run_loop`'s backoff, leaving the run `working`
  with its questions lost. The post is now wrapped: a `ForgeError` journals
  the questions as `park-post-failed` (truncated to 2000 chars - the only
  copy left) and escalates. Escalation is the fail-closed disposition here;
  a parked run would be waiting for an answer to a question nobody was
  asked.
- MR/PR number parsing from web URLs now recognizes Gitea's plural
  `/pulls/<n>` shape (previously only GitLab `merge_requests` and GitHub
  `pull`), so the post-MR poll can track terminal states on Gitea.

### Removed

- **`[container] parked_state`** (review finding ADORE-ARCH-007). Validated
  but never consulted at runtime - `keep_parked` is the field parking
  actually reads - so it was a redundant, misleading dead twin: setting
  `parked_state = "removed"` changed nothing. An existing `config.toml`
  carrying the key is unaffected (`load_config` silently ignores unknown
  keys, same as any typo); it simply has no effect from here on.
- **`adore/gates.py` and its AEGIS 1.x verbs** (`invariants`, `status`,
  `resume`, `gates run`, `delivery-preflight`, `report`), together with
  `tests/test_gates.py` and `05_SoftwareDocu/Component_Gates.md`. They are
  replaced by `adore/aegis.py`; there is no compatibility path.
- The `.agentic/.workspace/state/current_run` pointer read. Run-local AEGIS
  files are addressed by the run id ADORE persisted, so the seam that broke
  once in 1.x is gone.
- **The `@author`, `@date`, and `@version` Doxygen tags** from every Python
  docstring under `04_Software/` and `02_Tools/`, and the corresponding
  style-guide rules in `01_Documentation/Code_Style.md` and `AGENTS.md`
  (including the callable-level and file-level `@version` bump-on-change
  obligation). Zero behavior change; all other Doxygen tags are unaffected.

### Added

- **`[budgets] max_cost_usd` is now enforced** (review finding
  ADORE-ARCH-003). It was validated, wizard-prompted, and documented as a
  live limit while `_budget_exceeded` never read it, so an unattended run
  with a misbehaving executor could spend unboundedly in dollars while
  staying inside the iteration and wall-clock budgets - against
  `AGENTS.md`'s mandate to bound every run by cost. The check now sums
  `cost_usd` across the run's journaled `usage` events and fails the run with
  `budget exceeded: cost $X.XX`. It is deliberately only as good as what the
  executor reports: zero-cost reporting (or
  `[metrics] capture_tokens = false`) leaves the cap inert, which
  `Configuration_Reference.md` now states outright instead of implying a
  guarantee.
- **Stale-`working`-run detection** (review finding ADORE-ARCH-001). A run
  whose conductor died mid-conduct stayed `lifecycle = "working"` forever;
  because `working` runs count against `[polling] max_concurrent_runs`, one
  crash silently stopped all future pickup at the default of 1, with no
  ticket comment and no signal beyond `"at_capacity": true` in the poll
  summary. Reconciliation now escalates any `working` run this process is not
  conducting whose last state write is older than
  `[budgets] max_wall_clock_seconds + per_gate_timeout_seconds`, journaling
  `stale-working-detected` and counting it in the new poll-summary `stale`
  key. Reconciliation runs before the capacity check, so the freed slot is
  used in the same poll pass. The threshold derives from the operator's own
  budgets, in-flight runs are tracked on the instance by a nesting
  `_conducting` context manager, and a run with an unparseable `updated_at`
  is never reaped.
- **Escalations now post their reason on the ticket** (review finding
  ADORE-ARCH-002). `_escalate` wrote the reason to `run.outcome`, the
  journal, and the log, while the ticket received only the generic edited
  status line (`[ADORE] status: failed - stage X - run Y`). The AEGIS error,
  its remediation, and the carefully composed `aegis waive add` hint were
  invisible to anyone without host access - and `Operations_Guide.md` claimed
  otherwise. `_escalate` now posts one dedicated comment carrying the full
  reason plus the `adore logs` / `adore retry` commands for that run, under a
  `kind=escalation` marker. The post is best-effort
  (`contextlib.suppress(ForgeError)`): local state stays authoritative, so a
  forge outage still leaves the run `failed` with its reason. Secret
  redaction is unchanged - callers redact before passing the reason in.
- **ADORE 3.0 hard break to AEGIS 3.x - WP1: the AEGIS client
  (`adore/aegis.py`).** One component owns the whole AEGIS-facing contract:
  it invokes the grouped CLI as `bash .agentic/tools/run.sh [--run <id>]
  --json <group> <action>` inside the run's container, pins the AEGIS run id
  captured at `run start` on every later call (the worktree `current_run`
  pointer is never read again), and parses the stable four-key envelope into
  a frozen `AegisResponse`. Successful `run context` is a deliberately
  separate, closed schema-1 `AegisContext` response family. Helpers expose
  `ok`/`blocked`/`failed`/`complete`/`error`/
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
  `config_validate` and `run_context`. Warnings and quick-scope advisories are
  bounded, validated, and preserved. Covered through the offline fake-exec
  contract suite, including malformed/oversized context and envelope cases.
- **ADORE 3.0 hard break to AEGIS 3.x - WP2: the AEGIS run id is persisted.**
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
