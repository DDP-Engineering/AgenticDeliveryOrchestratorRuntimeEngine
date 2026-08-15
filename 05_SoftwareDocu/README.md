<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software Documentation

Implementation notes, internal contracts, and deeper technical documentation for
the orchestrator package belong here. Component documents follow
`component_documentation_template.md` and are created or updated in the same
change as the component.

This folder is the home for component implementation documentation. AI agents
must keep it current when they create or change component behavior, contracts,
responsibilities, dependencies, or workflow integration. These documents are
implementation companions to the code and tests; user manuals and operator
guides belong in `01_Documentation/`.

## Component documentation (phase 1 - base services)

- `Component_Branding.md` - canonical ADORE product, package, filesystem,
  container, deployment, and delivery identity constants
  (`adore/branding.py`).
- `Component_Util.md` - shared helpers: injectable command runner, duration
  parsing, UTC timestamps (`adore/util.py`).
- `Component_Config.md` - typed `config.toml` loading, slug-derived defaults,
  and validation (`adore/config.py`).
- `Component_Identity.md` - marker-based comment identity and slug-derived
  naming (`adore/identity.py`).
- `Component_State_Store.md` - the authoritative local run state, run-id,
  content hash, lock, pause flag, fail-closed corrupt-state handling
  (`adore/state.py`).
- `Component_Forge_Adapters.md` - the Git-platform boundary: `Forge`
  interface plus the GitLab (`glab`), GitHub (`gh`) and Gitea (`tea`) adapters
  (`adore/forge/`).
- `Component_CLI.md` - the `adore` command surface and exit-code contract
  (`adore/cli.py`).

## Component documentation (phase 2 - isolation and executor)

- `Component_Isolation.md` - per-run git worktree + executor container
  lifecycle, the GIT_DIR/GIT_WORK_TREE mounting model, and executor
  base/runtime-project images (`adore/isolation.py`, `docker/`).
- `Component_Executor_Launcher.md` - headless gate launches through the
  file-based gate protocol (WSL-safe, output captured to files), session
  continuation, questions detection (`adore/executor/`).

## Component documentation (phase 3 - the conductor engine)

- `Component_Orchestrator.md` - the thick-conductor state machine: polling,
  selection, the AEGIS stage loop, clarification park/resume, budgets,
  signaling, cancel/retry (`adore/orchestrator.py`).
- `Component_Aegis_Client.md` - the AEGIS 0.5.x companion-CLI client: schema-1
  task/check validation, contained journal paths, command wrappers, transition
  allowlist, and typed fail-loud errors (`adore/aegis.py`).

## Component documentation (phase 4 - delivery and observability)

- `Component_Metrics.md` - statistics capture and query: journal -> SQLite
  run summaries, stats/report/export CLI, static HTML dashboard
  (`adore/metrics.py`).
- `Component_Process_Log.md` - ADORE-owned rotating `run` command log at
  `<store_root>/adore.log` (`adore/process_log.py`).
- `Component_Deployment.md` - Task Scheduler/systemd deployment scripts and
  service setup (`04_Software/deploy/`).
- `Component_Packaging.md` - runtime-bundle packaging scripts
  (`02_Tools/package_runtime.*`).

## Cross-cutting contracts

The implemented run-state, recovery, and idempotency contracts are currently
documented in `Component_State_Store.md`, `Component_Orchestrator.md`, and
`Component_Isolation.md`. Operator-facing recovery procedures belong in
`01_Documentation/Recovery_And_Maintenance.md`.
