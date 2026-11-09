<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Repository tools

Three public commands, the same on Windows and Ubuntu/Linux:

```text
python 02_Tools/setup_environment.py
python 02_Tools/create_package.py
python 02_Tools/verify_package.py
```

Use `python3` on Linux when `python` is not available. Run from the repository
root; the scripts resolve their working files from their own locations.

| Command | What it does |
| --- | --- |
| `setup_environment.py` | Prepares the repository Python environment, frontend dependencies and Chromium. Requires Python 3.11+, uv, Git and Node.js 22.18+ with npm. Does not run tests or install services. |
| `create_package.py` | Checks release metadata/notes, compiles and licenses the frontend, bundles Python and locked dependencies, then writes the native final archive and adjacent SHA-256 file. Requires the prepared environment and build-time network access. |
| `verify_package.py [archive]` | Checks the archive identity/hash, extracts into temporary storage, verifies all package files and starts/stops the actual application with isolated data. Defaults to the current release for this host. Prints results and removes temporary data on exit. |

Build/verify the Windows ZIP on Windows and the Linux TAR.GZ on Ubuntu/Linux x64.
WSL Ubuntu can build and verify the Linux package. The target user needs no Python,
Node.js or uv installation to open the packaged application.

`07_Delivery/` holds only these final archives and optional adjacent `.sha256`
files. No README, report, log, extracted test package or technical directory is
retained there. `sha256sum -c *.sha256` checks hashes from that directory on Linux.

`internal/` contains automatically called release checks and asset licensing.
`portable/` holds the start/stop/CLI templates copied into each package.
`deploy/` contains specialized Windows/Ubuntu service administration sources;
they are independent of repository setup and ordinary portable startup.
`tests/` contains existing portable-media contract checks, not setup/deploy tests.
Do not add or run automated tests for environment setup or deployment scripts.

Older source-runtime packagers and the separate wheelhouse installer/launcher
have been retired. There is one standard portable delivery flow.

`generate_pi_catalog.py` refreshes the pinned Pi provider/model catalog offline; use it when changing the pinned Pi version.
