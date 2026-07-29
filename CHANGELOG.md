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

### Added

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
