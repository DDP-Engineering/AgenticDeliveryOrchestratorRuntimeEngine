<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Deployment and packaging

## Purpose

`04_Software/deploy/` provides host-specific unattended operation, while
`02_Tools/package_runtime.*` creates a compact, transparent runtime bundle.
They keep OS-specific behavior outside ADORE's portable Python conductor.

## Deployment contract

`deploy/install-ubuntu.sh` prepares an Ubuntu 22+ checkout and can install a
systemd service. `deploy/install-windows.ps1` prepares Windows 11 and can
register the ADORE Task Scheduler task in loop or repeating-once mode.
Both scripts are fail-fast, idempotent, validate the chosen config, leave state
on uninstall, and never put secret values in argv or logs. They refuse
unattended open container egress unless the operator explicitly overrides it.
The OS scheduler and ADORE's durable lock together prevent a second poller.

## Packaging contract

The PowerShell/Bash packagers derive the bundle name from the release version,
stage the runtime, deployment files and selected operator documentation, and
exclude virtual environments, state, worktrees, tests, caches, and `.env`.
Portable ZIP creation rejects links/special entries and replaces output only
after a complete archive. `check_release_consistency.py` verifies version,
metadata, documentation, artifact layout, exclusions, and legacy identity
drift before release handoff.

## Requirement coverage

- `REQ-FUNC-e3daac09` - version-derived, state-free portable runtime bundle.
- `REQ-FUNC-78969e20` - fail-fast installer/uninstaller and explicit unattended egress policy.

## Boundaries and verification

These tools do not install prerequisites silently, create native EXE/deb
packages, publish images, or contain credentials. Validate installer edits
with host-appropriate syntax/smoke checks and package edits with a temporary
bundle plus `04_Software/tests/test_release_consistency.py` and the release
consistency checker.
