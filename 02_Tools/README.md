<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Tools

This folder holds repository-level scripts used outside the runtime package.
Use it for development-environment setup, release/delivery preparation,
packaging, verification helpers, and other repository automation scripts.
The current implemented tool is the runtime-bundle packager:

- `check_release_consistency.py` - fails closed when the ADORE package,
  lockfile, images, deployment names, documentation, delivery-artifact
  contents, or forbidden pre-1.0 identifiers drift from the 1.0.0 release
  contract.
- `package_runtime.ps1` - Windows PowerShell packager; writes a trimmed
  `adore-runtime-<version>.zip` or directory under `07_Delivery/`.
- `package_runtime.cmd` - cmd.exe wrapper around the PowerShell packager.
- `package_runtime.sh` - POSIX/Bash packager; writes a trimmed
  `adore-runtime-<version>.tar.gz`, `.zip`, or directory under `07_Delivery/`.
- `create_portable_zip.py` - shared standard-library ZIP writer used by both
  packagers; rejects links/unsafe placement and always writes POSIX member
  names so Windows-built ZIPs extract to the documented tree on Linux.

The runtime bundle contains the runnable contents of `04_Software/` needed on a
deployment host: `adore/`, `deploy/`, `docker/`, package metadata, lockfile,
examples, changelog, and the canonical operator documentation under
`Documentation/`. It excludes development/test/runtime state such as `tests/`,
`.venv/`, `.adore/`, `worktrees/`, caches, and `.env`.

The package includes the existing setup scripts in `deploy/`; it does not
replace them. After unpacking, use `deploy/install-windows.ps1` for Windows Task
Scheduler setup or `deploy/install-ubuntu.sh` for Ubuntu systemd setup.

Examples:

```powershell
python .\02_Tools\check_release_consistency.py
python .\02_Tools\check_release_consistency.py --require-artifacts
```

```powershell
.\02_Tools\package_runtime.ps1
.\02_Tools\package_runtime.ps1 -Format directory
.\02_Tools\package_runtime.cmd -OutputDir D:\packages
```

```bash
bash 02_Tools/package_runtime.sh
bash 02_Tools/package_runtime.sh --format zip
bash 02_Tools/package_runtime.sh --include-config
```

By default, `config.toml` is not copied because it is target-specific, and
`.env` is never copied. Use the explicit config option only for a controlled
operator handoff where that target config is meant to travel with the bundle.

## Conventions

- Scripts are provided as **Bash (`.sh`)**, **PowerShell (`.ps1`)**, and
  **cmd (`.bat`/`.cmd`)** as appropriate, so packaging and deployment can be
  driven from both Ubuntu 22+ and Windows 11.
- Every script is **commented for each stage** - a short comment before each
  meaningful step explains what that stage does - so the scripts double as
  readable, step-by-step runbooks.
