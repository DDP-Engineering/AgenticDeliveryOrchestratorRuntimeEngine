<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to the Agentic Delivery Orchestrator are recorded here.
This project follows Keep a Changelog and Semantic Versioning.

## [Unreleased]

### Changed

- Split executor images into a generic `ador-executor-base:0.2.0` and a
  Cockpit-GCP runtime-project image with Terraform/gate tooling; live-verified
  the Cockpit image on rootless Podman through `docker/verify-runtime.sh`.

### Added

- `[container] required_tool_checks` for fail-fast validation that a selected
  runtime-project image contains required build/test tools.

## [0.2.0] - 2026-07-06

### Added

- Runtime bundle packaging scripts in `02_Tools/` for PowerShell, cmd.exe, and
  Bash; bundles include the existing Task Scheduler/systemd deployment scripts.
- Release versioning and changelog rules aligned with the workflow-template
  convention: root changelog plus synchronized `pyproject.toml` and
  `ador.__version__` release metadata.
- Initial repository scaffold: top-level folder structure
  (`00_Planning`, `01_Documentation`, `02_Tools`, `04_Software`,
  `05_SoftwareDocu`, `07_Delivery`, `09_Others`) mirroring the Agentic
  Development Workflow Template.
- Per-folder README files describing each folder's intended content.
- Root `README.md` and `AGENTS.md` describing the project scope and rules.
