<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE — Agentic Delivery Orchestrator & Runtime Engine

Current release: **ADORE 1.2.0**.

This is the standalone repository for **Agentic Delivery Orchestrator & Runtime Engine**:
a service that selects eligible tickets from GitLab or GitHub, guides an
executor agent (OpenCode, Pi, Codex, or Qwen) through the workflow gates, and—after
the required checks pass—opens a **draft** merge/pull request for human review.
A human still reviews and merges.

The repository keeps planning, operator documentation, tooling, implementation,
implementation notes, delivery material, and support files in separate
top-level folders.

The runnable Python package lives in `04_Software/`.

## Start Here

- New operators: [Getting Started](01_Documentation/Getting_Started.md).
- Credentials and the human merge boundary:
  [Security and Credentials](01_Documentation/Security_And_Credentials.md).
- Add a repository and its executor image:
  [Integrating a Runtime Project](01_Documentation/Integrating_A_Runtime_Project.md).
- Daily operation and recovery:
  [Operations Guide](01_Documentation/Operations_Guide.md) and
  [Recovery and Maintenance](01_Documentation/Recovery_And_Maintenance.md).
- Complete settings and command reference:
  [Configuration Reference](01_Documentation/Configuration_Reference.md) and
  [CLI Reference](01_Documentation/CLI_Reference.md).

For a deployment-ready runtime bundle, use the scripts in
[02_Tools](02_Tools/README.md); delivery artifacts are written to
[07_Delivery](07_Delivery/README.md).

## How ADORE Works

```text
forge ticket (eligible labels and readiness rules)
        -> orchestrator selects by configured priority and readiness
        -> isolates work (git worktree + container)
        -> guides executor gate-by-gate (thick conductor)
             intake -> alignment -> requirement -> check -> implementation -> validation
        -> parks and asks on ambiguity (posts a comment, resumes on reply)
        -> runs delivery-preflight (objective "done" signal)
        -> opens a DRAFT MR/PR, assigns a human reviewer
human reviewer -> approves and merges
```

## Design At A Glance

- **Forge-agnostic.** GitLab (`glab`) and GitHub (`gh`) sit behind one adapter
  interface, so the orchestrator logic never calls a platform CLI directly.
- **Executor-agnostic.** OpenCode, Pi, Codex, and Qwen are selectable through
  a configurable launcher.
- **Thick conductor.** The orchestrator drives one workflow gate at a time and
  checks invariants and exit codes between stages before advancing.
- **Human-gated delivery.** The orchestrator opens a draft MR/PR only; it never
  merges. Merge stays a human decision.
- **Portable.** Targets Ubuntu 22+ and Windows 11; the orchestrator is written
  in portable Python and runs the executor in a container.

## Repository Layout

- `00_Planning/` - architecture notes, design decisions, and roadmap.
- `01_Documentation/` - canonical operator, configuration, and CLI
  documentation.
- `02_Tools/` - repository-level helper scripts, release checks, and runtime
  packaging.
- `04_Software/` - the runnable orchestrator Python package.
- `05_SoftwareDocu/` - implementation notes and deeper technical contracts.
- `07_Delivery/` - generated runtime bundles, packaging, and release material.
- `09_Others/` - miscellaneous support material and local reference files.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license. See `LICENSE.txt` for
full license details.

SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
