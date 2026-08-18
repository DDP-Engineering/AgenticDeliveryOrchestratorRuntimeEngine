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

