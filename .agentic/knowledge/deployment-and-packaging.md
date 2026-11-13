<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Deployment and packaging

The public repository tools are `02_Tools/setup_environment.py`,
`create_package.py` and `verify_package.py`.
Setup synchronizes frozen Python/web development dependencies, frontend packages
and Chromium without running tests, configuring credentials or installing services.
Create checks release metadata/notes, compiles and licenses the frontend, then
bundles managed CPython, frozen dependencies, ADORE, three curated user guides
and the `02_Tools/portable/` launch templates for the matching native OS.
Verify checks archive release identity and optional hash, relocates/exercises the
actual media with isolated data, then removes all temporary files on exit.

`07_Delivery/` retains only complete Windows ZIP/Linux TAR.GZ user archives and
optional adjacent hashes. No technical directory, README, report, build workspace
or extracted verification media is retained. Build and verification use managed
OS temporary storage and console output.

`02_Tools/internal/` contains release metadata/note checks and asset licensing. The release consistency check verifies the committed frontend fingerprints and compares an isolated local Vite rebuild before packaging; rebuild and commit the bundle when inputs change.
`02_Tools/deploy/` remains specialized service administration. No automated tests
are added or run for environment setup or deployment scripts. The old advanced
source bundle and separate wheelhouse installer flow have been retired.

`02_Tools/deploy/` provides host-specific unattended operation, while
`02_Tools/package_runtime.*` creates a compact, transparent runtime bundle.
They keep OS-specific behavior outside ADORE's portable Python conductor.
`02_Tools/package_web_offline.py` additionally creates an OS/Python-specific
web bundle from the locked dependencies and bundled React assets.

## Public interface

`deploy/install-ubuntu.sh` prepares an Ubuntu 22+ checkout and can install a
systemd service. `deploy/install-windows.ps1` prepares Windows 11 and can
register the ADORE Task Scheduler task in loop or repeating-once mode.
Both scripts are fail-fast, idempotent, validate the chosen config, leave state
on uninstall, and never put secret values in argv or logs. They refuse
an unattended install with `[executor] internet = true` (open container egress)
unless the operator passes `--allow-open-egress` / `-AllowOpenEgress`; with it
false they build (Ubuntu) or verify (Windows) the egress proxy image.
The OS scheduler and ADORE's durable lock together prevent a second poller.

## Invariants

The PowerShell/Bash packagers derive the bundle name from the release version,
stage the runtime, deployment files and selected operator documentation, and
exclude virtual environments, state, worktrees, tests, caches, and `.env`.
Portable ZIP creation rejects links/special entries and replaces output only
after a complete archive. `check_release_consistency.py` verifies version,
metadata, documentation, artifact layout, exclusions, and legacy identity
drift before release handoff.
The web bundle carries local dependency wheels, a checksum manifest, installer
and launcher. Installation verifies the media and invokes `pip --no-index`;
the manifest checks Git, forge, executor and runtime tool groups before target
creation. A check-only invocation verifies host readiness without installation;
required images load or are inspected before creating the Python environment.
the API and worker are separate foreground processes. See `web-interface.md`.
The combined web launcher supervises both processes as one pair, stopping the
survivor after either exits and applying a finite restart limit with 1/2/4-second
backoff by default. An external service manager can instead supervise the
installed entrypoints separately.

## Key behaviors

- `REQ-FUNC-e3daac09` - version-derived, state-free portable runtime bundle.
- `REQ-FUNC-78969e20` - fail-fast installer/uninstaller and explicit unattended egress policy.
- `REQ-PLAT-a1b60ff9` - offline web installation from host-matched media.

## Routing

For shipped executor source definitions, inspect `04_Software/pyproject.toml`
force-include mappings and `adore/executor_recipes.py` builtin loading.
For actual delivery/setup operations use the `02_Tools/` entrypoints above;
source export behavior belongs to project-images.md.

## Purpose and boundaries

Delivery tooling packages native user media. The product wheel also retains
canonical executor-base sources: Dockerfile, Pi guard, ChatGPT helper and license.
These product resources support source-only export from installed ADORE without
a checkout; they do not build an executor image during installation or export.
OS-specific setup stays outside the portable conductor. Setup/deployment tooling
has no automated product-test workflow under the repository applicability rule.

## Files

- `02_Tools/package_runtime.*`, `package_web_offline.py` - delivery media.
- `02_Tools/install_web_offline.py`, `launch_web.py` - offline install and launch.
- `02_Tools/internal/check_release_consistency.py` - release contract checker.
- `02_Tools/deploy/` - OS service installation.
- `04_Software/tests/test_web_package.py`, `test_release_consistency.py` - checks.

Canonical resource verification uses an isolated wheel build in automatically
cleaned OS temporary storage, confirming the four resources and builtin resolution
with only the extracted wheel on the Python import path. REQ-FUNC-4404d38b owns
this packaging seam; source-level contracts are in test_executor_recipes.py.
