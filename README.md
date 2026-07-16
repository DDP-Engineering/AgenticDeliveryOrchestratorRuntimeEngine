<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Delivery Orchestrator & Runtime Engine

Current release: **ADORE 1.0.0**.

This repository is the standalone home for the **Agentic Delivery Orchestrator & Runtime Engine**:
a service that pulls a high-priority ticket from a forge (GitLab or GitHub),
guides an executor agent (opencode, pi.dev, or codex) through the agentic
development workflow gates, and — once every gate is green — opens a **draft**
merge/pull request for human review. A human still reviews and merges.

It keeps planning, documentation, tooling, implementation code, implementation
notes, delivery material, and support files in separate top-level folders, in
the same layout convention as the Agentic Development Workflow Template.

The runnable Python package lives in:

`04_Software/`

## What It Does

```text
forge ticket (label: agent-ready)
        -> orchestrator picks highest priority, applies readiness filter
        -> isolates work (git worktree + container)
        -> guides executor gate-by-gate (thick conductor)
             intake -> requirement -> check -> implementation -> validation
        -> parks and asks on ambiguity (posts a comment, resumes on reply)
        -> runs delivery-preflight (objective "done" signal)
        -> opens a DRAFT MR/PR, assigns a human reviewer
human reviewer -> approves and merges
```

## Design At A Glance

- **Forge-agnostic.** GitLab (`glab`) and GitHub (`gh`) sit behind one adapter
  interface, so the orchestrator logic never calls a CLI directly.
- **Executor-agnostic.** opencode, pi.dev, and codex are swappable through a
  configurable launcher.
- **Thick conductor.** The orchestrator drives one workflow gate at a time and
  checks invariants and exit codes between stages before advancing.
- **Human-gated delivery.** The orchestrator opens a draft MR/PR only; it never
  merges. Merge stays a human decision.
- **Portable.** Targets Ubuntu 22 for production and Windows 11 for first tests;
  the orchestrator is written in portable Python and runs the executor in a
  container.

## Repository Layout

- `00_Planning/` - architecture notes, design decisions, and roadmap for the
  orchestrator.
- `01_Documentation/` - operator and configuration documentation for running
  the orchestrator.
- `02_Tools/` - repository-level helper scripts, including runtime packaging.
- `04_Software/` - the runnable orchestrator Python package (implementation).
- `05_SoftwareDocu/` - implementation notes and deeper technical contracts.
- `07_Delivery/` - generated runtime bundles, packaging, and release material.
- `09_Others/` - miscellaneous support material and local reference files.

## Status

ADORE has an implemented CLI under `04_Software/` with config/profile setup,
state tracking, forge adapters, isolated executor runs, delivery to draft
MR/PR, metrics, cleanup/reset operations, and deployment scripts for Windows
Task Scheduler and Ubuntu systemd. `02_Tools/package_runtime.*` creates trimmed
runtime bundles under `07_Delivery/` for operator handoff without copying the
whole repository.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See `LICENSE.txt` for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
