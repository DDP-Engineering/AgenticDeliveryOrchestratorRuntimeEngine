<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Repository environment and packaging tools

## 1. Purpose

Expose three public cross-platform commands in `02_Tools/`:
`setup_environment.py`, `create_package.py` and `verify_package.py`.
Standard delivery is one complete Windows x64 ZIP and one Ubuntu/Linux x64
TAR.GZ, each with an optional adjacent SHA-256 file. See
[Portable user distribution](Component_Portable_Distribution.md) for launcher
and runtime contracts.

## 2. Responsibilities

- `setup_environment.py` checks build-host prerequisites, synchronizes the frozen
  Python environment including web/development dependencies, runs `npm ci` and
  provisions Chromium for repository UI development. It does not run tests,
  configure credentials, change an ADORE installation or install services.
- `create_package.py` automatically runs the internal release metadata/note checks,
  compiles/licenses the frontend and builds a native self-contained package using
  the version from `04_Software/pyproject.toml` and frozen dependency lock.
- `verify_package.py` defaults to this host's archive, validates release metadata
  and an optional adjacent hash, then checks relocated media, CLI, API/worker,
  ready browser startup and shutdown using isolated temporary user data.
- `internal/` owns the release checks and static-asset license stamping, called
  by the entry points or frontend build. They are implementation helpers.
- `portable/` holds shipped launch templates; `deploy/` remains specialized
  service administration, separate from repository environment setup.

## 3. Inputs and outputs

Build prerequisites: Python 3.11+, uv, Git and Node.js 22.18+ with npm on a
Windows/Linux x64 host. Source: `04_Software/`, `uv.lock`, frontend lockfile,
curated user guides and portable launcher templates.

Only final archives and optional adjacent `.sha256` files are retained in
`07_Delivery/`. Build staging and verification data use automatically cleaned OS
temporary directories. Results go to the console without saved reports/logs.
Every dependency/build command has a 30-minute timeout; prerequisite version
inspection has a 15-second timeout. Secrets and existing user data are not copied.

## 4. Usage

```text
python 02_Tools/setup_environment.py
python 02_Tools/create_package.py
python 02_Tools/verify_package.py
```

Use `python3` on Linux if necessary. To verify an explicit archive, pass its path
to `verify_package.py`. Build/verify each package on its matching operating system.
The separate source-runtime packagers, ZIP helper and wheelhouse installation
flow have been retired in favor of the portable distribution.

## 5. Validation

Application package acceptance remains separate from setup/deployment scripts.
Do not add or run automated tests for environment setup or deployment scripts.
Package/release verification prints results without retaining technical outputs.


## Web bundle verification

Release consistency checks the committed frontend input/output fingerprint and
rebuilds the frontend in a temporary directory using the locally installed Vite.
It rejects missing dependencies, stale inputs, modified output and output that
does not match the fresh build. Build and commit the production bundle whenever
frontend inputs change. No network installation is attempted by the checker.
