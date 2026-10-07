<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project profile

## Purpose and users

ADORE, the Agentic Delivery Orchestrator & Runtime Engine, conducts
AEGIS-governed repositories for a team. It selects opt-in GitHub, GitLab or
Gitea tickets, runs one fresh executor session per AEGIS stage inside an
isolated branch, worktree and container, verifies the candidate independently,
and publishes only a draft MR/PR after fresh human approval. It never merges.
Its users are the operator who runs the conductor on a host, the reviewers who
approve and merge on the forge, and the coding executors it launches:
OpenCode, Pi, Codex and Qwen Code.

## Product responsibilities

- `adore/aegis.py` speaks the AEGIS companion CLI over JSON schema 1 and fails
  closed on any contract violation.
- `adore/orchestrator.py` claims tickets, provisions isolation, supervises
  stages, bounds failures, parks clarifications, replays notifications,
  verifies strictly and publishes drafts; `adore/state.py` persists schema-1
  run state, the single-conductor lock and an append-only JSONL journal.
- `adore/forge/` adapts GitLab (`glab`), GitHub (`gh`) and Gitea (`tea`);
  `adore/isolation.py` owns worktrees, checkpoint commits, candidate
  fingerprints and the Docker/Podman lifecycle; `adore/executor/` launches
  the supported executors through a file-based gate protocol.
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
  its primary link resets all-project scope and polling updates valid rows quietly;
  worker faults remain visible, with reporting/technical evidence in dedicated views.
  Header help discloses localized delivery meanings beside Refresh/About; sidebar
  Jobs supplies scoped full-history navigation.
  Executor configuration unifies settings/provider credentials and heading model testing,
  with server-authoritative agent and exact launch-preset choices through reviewed apply.
  Settings uses seven purpose
  categories, visible catalog guidance and exact single-candidate active/proposed
  review with explicit base/candidate binding, idle/lock/pause safety and Dev
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
  memory, returns canonical revision-bound review and runs explicit ephemeral draft
  checks. Guarded creation publishes the exact reviewed configuration with pickup
  stopped; activation and persisted project verification are separate actions.
  Exact server TOML enrollment reviews all declared locations and recognized
  agent/runtime settings, keeps corrected drafts in memory and verifies explicitly
  through ephemeral bounded probes. Publication binds unchanged file bytes,
  declared identity and inspected ownership/state with locked reinspection;
  existing terminal history comes from the declared server state location.
  Its additive global job API scans complete authorized current/archived history,
  uses composite project/run identities and optimistic content revisions, and
  exposes actual persisted waiting evidence with explicit legacy/usage unknowns.
  Strict read validation preserves the engine's schema-1 recovery contracts.

`python .agentic/aegis.py components` lists the knowledge page that routes
each component to its source and tests.

## Supported operation

One conductor per state root polls in a loop or in externally scheduled single
passes, on Windows 11 through Task Scheduler or on Ubuntu 22+ through systemd.
Run lifecycle states (`working`, parked, awaiting approval, publishing, in
review, terminal) are separate from the AEGIS stage. A stage receives a bounded
number of failed attempts, questions park the run without consuming that
budget, and required forge notifications pass through a persisted outbox.
Publication requires a fresh `agent-approved` label bound to the exact
candidate fingerprint and target commit; every review round repeats validation
and approval.
An explicit profile opt-in may publish guarded work-in-progress checkpoints to
the owned ticket branch before approval, without opening an MR/PR. An operator
can hand a run to a human at a safe boundary; the resulting terminal state
protects the worktree from routine cleanup and further autonomous execution.

## Established constraints

- The CLI runtime is standard-library Python 3.11+ with no runtime dependencies.
  The optional `web` extra adds FastAPI, Uvicorn and Argon2id support.
- ADORE conducts AEGIS major 0 at 0.5 or later over JSON schema 1, declared
  once in `adore/aegis.py`. It never edits the AEGIS payload, and the ADORE
  release number names the AEGIS release the contract was last re-verified
  against.
- Run state is schema 1 with no migration from earlier lines; unknown or
  corrupt state fails closed.
- Executors run inside a container, never receive forge credentials, and never
  commit, push, open or merge. ADORE owns checkpoints, push and draft creation
  and never merges; `draft = false` is rejected by configuration validation.
- Secrets live only in the process environment or a gitignored `.env`.
- Version assignment, packaging and delivery are repository operations outside
  AEGIS scope, checked by `02_Tools/check_release_consistency.py`. This
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
- `04_Software/deploy/` holds the host installers and systemd unit;
  `04_Software/docker/` holds the executor base and egress-proxy images.
- `01_Documentation/` is operator documentation, `05_SoftwareDocu/` holds
  component contracts, `02_Tools/` holds release tooling, `07_Delivery/` holds
  generated runtime bundles and `00_Planning/` holds design history.
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

## Web account access

Admin user creation guides identity/credentials, explicit role/stable project
IDs and secret-free corrective review. One SQLite transaction commits account,
grants and the existing success audit after selected profile reinspection.
Dev zero grants require deliberate acknowledgement; Admin role grants global
project/system/cost access. Compatible account/reset/assignment APIs remain
supported. Account and project grant editors show before/after and actual result;
credential drafts remain transient and clear on success or leaving the page.

## Web reporting scope

Web analytics resolves inclusive local calendar controls to canonical half-open
UTC instants with explicit all-time. Scoped lifecycle/consumption/quality and
server-selected duration samples share that contract. Current-state stock,
per-job lifetime and undated unallocated measurements are separately named;
unknown amounts are null and all financial evidence is Admin-only. Analytical
source reads fail closed and preserve operational persistence/CLI contracts.

The Statistics browser presents canonical scope-bound measures and CSV actions,
explicit all-time versus current stock, honest zero/unknown/partial evidence,
reported versus estimated Admin money, server samples, and labeled trends with
accessible tables. Job list/detail consumption uses immutable project/run
identity and selected-period/lifetime/undated measurements. Reporting routes
preserve calendar/timezone/group selections; stale, revoked and malformed reads
hide evidence. Four locales and both themes share these responsibilities.

## Web change evidence

Web mutations record closed redacted actor/time, known stable identity and
before/after/revision evidence. SQLite account/access/queue/policy mutations own
atomic evidence; filesystem attempts retain uncertainty through crashes and use
separate replay receipts for single confirmation. Schema-14 audit upgrade preserves
historic unknown values and identity and rejects corrupt storage. Authorized
actor/project/action/UTC filters precede server counts/paging; Dev project history
excludes administrative and name-only legacy rows. Change history presents
who/what/when/result; System status owns independent audit retention and deletion
impact. Credentials, environment values and raw errors remain excluded.

Admin Project Summary Connect repository provides scoped Gitea/GitHub/GitLab
authentication. See repository-auth.md knowledge and Security_And_Credentials.md.
Protected per-profile tokens are used only by forge CLI commands and explicit
web host checks, with external CLI auth as the missing-record default. Corrupt
or mismatched scoped records fail closed.

Explicit administrator model connectivity uses the selected OpenCode/Pi/Codex/Qwen CLI through a bounded disposable container; see knowledge/model-connection.md. Real provider acceptance is operator-triggered and may incur cost.

Project Executor configuration owns agent/model settings and approved provider key save/remove; strict durable credential-bound model access evidence is reused inside Summary’s collapsed host-check details. See knowledge/executor-configuration.md. Subscription login remains the installed CLI service-account flow.
