<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE - Agentic Delivery Orchestrator & Runtime Engine

Runnable implementation of the orchestrator described in
`00_Planning/Orchestrator_Design_And_Decisions.md`.

## Package layout

- `adore/` - the Python package (standard library only at runtime).
  - `cli.py` - the `adore` command surface (argparse).
  - `config.py` - typed `config.toml` loading and validation.
  - `identity.py` - marker-based comment identity + slug-derived names (5c/5d).
  - `state.py` - authoritative local run state: `.adore/runs/<run-id>/`
    (ticket.json, state.json, journal.jsonl), run-id, content hash,
    single-instance lock, pause flag (8a).
  - `util.py` - injectable command runner, duration parsing, timestamps.
  - `forge/` - Git-platform adapters: `gitlab.py` (glab) and `github.py` (gh)
    behind one `Forge` interface. Merging is absent from the interface.
  - `isolation.py` - per-run git worktree + executor container lifecycle
    (mounting model: repo at `/adore/repo`, worktree at `/adore/work`,
    git driven by GIT_DIR/GIT_WORK_TREE inside the container).
  - `executor/` - executor launcher: headless per-stage launches via the
    file-based gate protocol (gate.sh + captured event stream in the run's
    io dir), session continuation, questions detection.
  - `orchestrator.py` - the thick-conductor engine: polling, selection, the
    AEGIS stage loop, clarification park/resume, budgets, ticket signaling.
  - `aegis.py` - the AEGIS 2.x client: grouped CLI invocation, `--run`
    pinning, envelope parsing, and the typed fail-loud errors.
  - `metrics.py` - statistics: journal -> SQLite run summaries + JSONL
    mirror, aggregation, CSV export, static HTML dashboard, per-profile stats.
  - `process_log.py` - fixed rotating process log for `adore run`
    (`<store_root>/adore.log`) so scheduled runs keep ADORE-owned stdout history.
  - `profiles.py` - runtime-project profiles: cross-platform config home,
    CRUD, active pointer, config-path resolution (one install, many projects).
  - `doctor.py` - environment detection + OS-specific prerequisite guidance.
  - `wizard.py` - the `adore init` assisted-config wizard.
- `docker/` - `Dockerfile.executor-base` for the generic
  `adore-executor-base:1.0.0` executor environment, plus the pattern for
  project-owned runtime images. See `docker/README.md`.
- `deploy/` - deployment scripts (design 12a): `install-ubuntu.sh` +
  `adore.service` (systemd), `install-windows.ps1` (Task Scheduler), and the
  deployment procedure in `deploy/README.md`.
- `config.example.toml` - example configuration (copy to `config.toml`).
- `.env.example` - the canonical list of required secrets.
- `tests/` - offline unit tests (adapters run against a fake command runner).

## Implementation phases

1. **Base services (done):** util, config, identity, state store, forge
   adapters, CLI wiring for `config` / `status` / `runs` / `pause` / `resume`.
2. **Isolation + executor launcher (done, live-verified):** worktree +
   container lifecycle, the executor image, and the opencode gate launcher.
3. **The thick-conductor engine (done, live-piloted on ticket #45; reworked
   for AEGIS 2.x in ADORE 2.0):** polling, selection, the `next`-driven AEGIS
   stage loop with verification and budgets, clarification park/resume,
   TTL/timeouts, cancel/retry. Wired to
   `adore run --loop|--once|--dry-run`, `cancel`, `retry`, `logs`, `delete`.
4. **Publication (done, live-piloted to draft MR !29):** the 11a sequence -
   merge target branch (executor resolves conflicts), one authoritative
   post-merge `aegis verify run`, push, DRAFT MR with reviewers, environment
   retained;
   post-MR merge/close detection completes or ends the run; the 11b revise
   cycle (agent-revise label -> executor rework with the review thread ->
   delivery tail -> same MR updated, bounded by max_review_rounds).
5. **Metrics + execution logs (done):** per-launch token usage journaled,
   immutable executor-launch archives under each run's `io/archive/`, run
   summaries in SQLite at terminal states, rotating `<store_root>/adore.log`,
   `adore stats|report|export` + static HTML.
6. **Operator commands (done):** `adore reset <run-id> --to <stage> --force`
   (state surgery; follow with `adore retry`) and `adore cleanup` (stale lock,
   orphaned containers, orphaned/husk worktrees; corrupt state reported,
   never auto-deleted).
7. **Deployment (done):** `deploy/` scripts for both hosts - systemd unit on
   Ubuntu 22+, Task Scheduler (loop at logon or repeating `--once`) on
   Windows 11; fail-fast prerequisite checks, locked env sync, config
   validation, image build/verify.
8. **Assisted config + profiles (done, cross-platform verified):** `adore init`
   guided wizard, `adore profile list|show|use|rename|delete|path`, global
   `--profile`, per-project profiles under a cross-platform config home, run
   statistics. One install serves many projects. See
  `../01_Documentation/Integrating_A_Runtime_Project.md`. Still pending: the
  security decisions in `00_Planning/TODO.md` (container egress allowlist
  before unattended runs).

## Development

```bash
uv run --group dev pytest        # tests
uv run --group dev ruff check .  # lint
uv run adore -c config.example.toml config validate
```

Testing convention (see the Testing Rules in the repository `AGENTS.md`):
every public behavior gets a happy-path test plus negative tests at its trust
boundaries (CLI output, config files, human comments, persisted state), and
corrupt input must fail closed with a typed error (`StateError`, `ForgeError`).

Runtime target: Python 3.11+; runs on Ubuntu 22 (production) and Windows 11
(first tests).
