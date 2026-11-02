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
The implemented tools are the release checker and the runtime-bundle packager:

- `check_release_consistency.py` - fails closed when the ADORE package,
  lockfile, image tags, deployment names, documentation, delivery-artifact
  contents, or forbidden pre-rename identifiers drift from the release
  identity declared by its `EXPECTED_VERSION` constant.
- `package_runtime.ps1` - Windows PowerShell packager; writes a trimmed
  `adore-runtime-<version>.zip` or directory under `07_Delivery/`.
- `package_runtime.cmd` - cmd.exe wrapper around the PowerShell packager.
- `package_runtime.sh` - POSIX/Bash packager; writes a trimmed
  `adore-runtime-<version>.tar.gz`, `.zip`, or directory under `07_Delivery/`.
- `create_portable_zip.py` - shared standard-library ZIP writer used by both
  packagers; rejects links/unsafe placement and always writes POSIX member
  names so Windows-built ZIPs extract to the documented tree on Linux.
- `check_release_notes.py` - checks the four-locale user-facing release notes
  in `04_Software/adore/release_notes.toml` (contract, changelog dates, current
  version); `--since <rev>` warns when `CHANGELOG.md` changed without them.
- `generate_pi_catalog.py` - writes `04_Software/adore/pi_catalog.json`, the
  Pi providers, key variables and models offered in Settings and enrollment,
  by running the pinned Pi's `--list-models` offline (`PI_OFFLINE=1`, one
  placeholder provider variable at a time, variables from Pi's
  `docs/providers.md`). Rerun it whenever the pinned Pi version changes;
  pass `--node <Node 22>` and `--cli <prefix>/.../pi-coding-agent/dist/bundle/cli.js`.
- `stamp_web_assets.py` - stamps built JS/CSS with the project license and
  copies license/third-party notices. Its default is `adore/web/static`;
  `--output <directory>` selects an existing isolated build containing
  `index.html`, as used by the offline Playwright verification route.

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
python .\02_Tools\check_release_notes.py --since master
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
