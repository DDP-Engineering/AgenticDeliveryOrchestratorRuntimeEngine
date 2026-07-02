<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Tools

This folder holds **all scripts needed to work with the project across its whole
lifecycle** - from setting up a development environment, through building and
packaging, to delivery. In short: every script required to set the project up for
development and take it all the way to packaging and release belongs here.

Planned contents:

- **Development environment setup** scripts (Windows PowerShell and Bash) that
  install the orchestrator's Python environment (via `uv`) and verify that
  `glab`/`gh`, `git`, the chosen executor CLI, and the container runtime are
  available.
- **Build / container** helpers for the executor image (bundling the target
  repo's `.agentic` CLI, an executor, and the Git-platform CLI) and its cache
  volumes.
- **Packaging** scripts that build the distributable ADOR package (wheel/sdist)
  and the executor image.
- **Delivery / release** scripts for publishing the package/image and handling
  any release bookkeeping.
- Local lint/test convenience wrappers.

## Conventions

- Scripts are provided as **Bash (`.sh`)**, **PowerShell (`.ps1`)**, and
  **cmd (`.bat`/`.cmd`)** as appropriate, so the project can be set up and
  delivered on both Ubuntu 22 (production) and Windows 11 (first tests).
- Every script is **commented for each stage** - a short comment before each
  meaningful step explains what that stage does - so the scripts double as
  readable, step-by-step runbooks.
