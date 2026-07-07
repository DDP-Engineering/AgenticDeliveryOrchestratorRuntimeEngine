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
change as the component (see the Documentation Rules in the repository
`AGENTS.md`).

## Component documentation (phase 1 - base services)

- `Component_Util.md` - shared helpers: injectable command runner, duration
  parsing, UTC timestamps (`ador/util.py`).
- `Component_Config.md` - typed `config.toml` loading, slug-derived defaults,
  and validation (`ador/config.py`).
- `Component_Identity.md` - marker-based comment identity and slug-derived
  naming (`ador/identity.py`).
- `Component_State_Store.md` - the authoritative local run state, run-id,
  content hash, lock, pause flag, fail-closed corrupt-state handling
  (`ador/state.py`).
- `Component_Forge_Adapters.md` - the Git-platform boundary: `Forge`
  interface plus the GitLab (`glab`) and GitHub (`gh`) adapters
  (`ador/forge/`).
- `Component_CLI.md` - the `ador` command surface and exit-code contract
  (`ador/cli.py`).

## Component documentation (phase 2 - isolation and executor)

- `Component_Isolation.md` - per-run git worktree + executor container
  lifecycle, the GIT_DIR/GIT_WORK_TREE mounting model, and executor
  base/runtime-project images (`ador/isolation.py`, `docker/`).
- `Component_Executor_Launcher.md` - headless gate launches through the
  file-based gate protocol (WSL-safe, output captured to files), session
  continuation, questions detection (`ador/executor/`).

## Component documentation (phase 3 - the conductor engine)

- `Component_Orchestrator.md` - the thick-conductor state machine: polling,
  selection, the per-gate loop, clarification park/resume, budgets,
  signaling, cancel/retry (`ador/orchestrator.py`).
- `Component_Gates.md` - the .agentic workflow CLI wrappers (the conductor's
  objective verification between gates) (`ador/gates.py`).

## Component documentation (phase 4 - delivery and observability)

- `Component_Metrics.md` - statistics capture and query: journal -> SQLite
  run summaries, stats/report/export CLI, static HTML dashboard
  (`ador/metrics.py`).
- `Component_Deployment.md` - Task Scheduler/systemd deployment scripts and
  service setup (`04_Software/deploy/`).
- `Component_Packaging.md` - runtime-bundle packaging scripts
  (`02_Tools/package_runtime.*`).

## Planned contents (later phases)

- `State_Machine.md` - the run states and transitions (pick, isolate, gate loop,
  park/resume on clarification, deliver, retry, escalate) and the run budgets
  that bound them.
- `Idempotency_And_Recovery.md` - how the orchestrator recovers after a restart
  without double-posting comments or re-opening MRs.
