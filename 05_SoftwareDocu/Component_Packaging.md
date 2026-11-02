<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Packaging (`02_Tools/package_runtime.*`)

> Sources: `02_Tools/check_release_consistency.py`,
> `02_Tools/create_portable_zip.py`,
> `02_Tools/package_runtime.ps1`, `02_Tools/package_runtime.cmd`, and
> `02_Tools/package_runtime.sh`.

## 1. Purpose

Create a small operator-facing ADORE runtime bundle without copying the whole
development repository. The bundle is intentionally a transparent Python
package directory, not a PyInstaller executable or OS-native package.

## 2. Responsibilities

- Stage the runtime files needed from `04_Software/` and the canonical
  operator documentation from `01_Documentation/`.
- Include `deploy/` so the unpacked bundle can install Windows Task Scheduler
  or Ubuntu systemd setup with the existing deployment scripts.
- Exclude local development and runtime state: `.venv/`, `.adore/`, worktrees,
  tests, caches, and `.env`.
- Name packages from the release version in `04_Software/pyproject.toml`.
- Copy `config.toml` only when explicitly requested; never copy `.env`.
- Fail closed when release metadata, runtime branding, deployment resources,
  embedded archive metadata/documentation, delivery artifacts, or forbidden
  pre-1.0 identity tokens drift.

Native Windows single-file executables, Ubuntu `.deb` packages, and image
publishing are not owned by this component.

## 3. Implementation Overview

`02_Tools/stamp_web_assets.py` adds the project legal banner to each built
JS/CSS file once and copies `LICENSE.txt` and web `THIRD_PARTY_NOTICES.md`.
The default output is `04_Software/adore/web/static`; `--output <directory>`
selects an isolated build such as `web/.e2e-dist`. An absent built `index.html`
is rejected before writing, and repeated stamping is idempotent. Offline CLI
tests in `04_Software/tests/test_web_asset_stamp.py` cover these contracts.

The PowerShell and Bash scripts stage the same bundle shape:

```text
adore-runtime-<version>/
  adore/
  deploy/
  docker/
  Documentation/
  pyproject.toml
  uv.lock
  README.md
  README_PACKAGED.md
  CHANGELOG.md
  config.example.toml
  .env.example
```

`package_runtime.cmd` is a thin wrapper that delegates to the PowerShell script.
Both real packagers stage into `<output>/.packaging_tmp`, archive or move the
bundle, and then remove the temporary staging directory. Both ZIP paths call
`create_portable_zip.py`, which writes member names with `/` regardless of the
host OS, rejects links and special entries, refuses an output inside the source
bundle, and atomically replaces the destination only after a complete archive.

## 4. Dependencies

- Internal: `04_Software/` runtime files, root `CHANGELOG.md`.
- External: PowerShell or Bash plus Python 3 for version parsing and portable
  `.zip` creation; `tar` for `.tar.gz`.

## 5. Inputs And Outputs

Inputs:

- Output directory (`-OutputDir` / `--output-dir`), default `07_Delivery/`.
- Package format (`zip`, `tar.gz`, or `directory`, depending on host script).
- Optional package name override.
- Optional explicit inclusion of `04_Software/config.toml`.

Outputs:

- `07_Delivery/adore-runtime-<version>.zip` from PowerShell by default.
- `07_Delivery/adore-runtime-<version>.tar.gz` from Bash by default.
- A directory bundle when requested.

## 6. Data Contracts

The runtime bundle root is the directory shape that `04_Software/deploy`
expects as its working directory. It also contains `Documentation/README.md`
as the entry point for prerequisites, credentials, configuration, operation,
and recovery. The packagers rewrite the copied runtime README's documentation
links to remain valid within that bundle. After unpacking, operators run `uv
sync --frozen`, create or provide `config.toml`, and then run the deployment
script for their host.

## 7. Workflow Integration

Packaging happens after implementation validation and before host deployment.
Deployment itself remains the responsibility of the included `deploy/` scripts.
The release workflow runs `check_release_consistency.py` before packaging and
runs it again with `--require-artifacts` after both delivery archives exist;
the packagers do not invoke the checker themselves.
The legacy-identity source scan skips generated `07_Delivery/web-candidate-*`
trees, including installed Linux test runtimes whose symlinks Windows cannot
stat. It still scans source documentation and checks canonical runtime archives.

## 8. Usage

```powershell
python .\02_Tools\check_release_consistency.py
.\02_Tools\package_runtime.ps1
.\02_Tools\package_runtime.ps1 -Format directory
.\02_Tools\package_runtime.cmd -OutputDir D:\packages
```

```bash
python3 02_Tools/check_release_consistency.py
bash 02_Tools/package_runtime.sh
bash 02_Tools/package_runtime.sh --format zip
bash 02_Tools/package_runtime.sh --include-config
```

## 9. Validation And Tests

Minimum validation after changes:

- PowerShell packager creates a bundle in a temporary output directory.
- cmd wrapper `-h` path delegates successfully.
- Bash syntax check (`bash -n`) and one temporary bundle creation.
- Inspect the bundle to confirm excluded paths are absent and `deploy/` plus
  `Documentation/` are present.
- Run `check_release_consistency.py --require-artifacts`; it validates both
  artifact names and their layout, exclusions, embedded package/lock metadata,
  documentation entry points, credential guidance, and legacy identity scan.
  The current release lock is ADORE 0.13.0 with changelog date 2026-09-12.
- `tests/test_release_consistency.py` invokes the public portable-ZIP command
  on a nested bundle, verifies forward-slash names and Linux extraction, and
  verifies a missing source fails closed without creating an artifact.

## 10. Limitations And Future Work

- The optional web bundle is built by `02_Tools/package_web_offline.py` for
  one OS, architecture and Python minor version. It includes the compiled UI,
  application/dependency wheels pinned by `uv.lock` (including IANA `tzdata`
  for Windows reporting), license, SHA-256 manifest and a `pip --no-index`
  installer. Installation rejects missing, changed or unlisted media before
  creating a runtime. The manifest also records required host tool groups:
  Git, one selected forge CLI, and a container runtime. With `--executor pi`
  Pi is recorded as an image prerequisite and checked by project readiness
  inside the already prepared image.
  `install.py --check-only` verifies these and checksummed media without
  changing the target; embedded images load or are inspected before virtual
  environment creation. A symlinked host Python is resolved before virtual
  environment creation. `02_Tools/launch_web.py` supervises the installed API
  and worker as one pair: if either exits, it stops the sibling and restarts
  both at most three times with 1/2/4-second backoff. `--restart-limit 0..10`
  changes that finite limit; exhausted or failed startup returns nonzero.
  Child console signals are isolated so a supervisor Ctrl-C stops both
  processes. A service manager may instead run the two
  installed entrypoints independently with its own restart policy.
  Container images can be embedded with `--image` or required as preinstalled
  tags with `--require-image`; both are verified before runtime creation.
  With `--executor pi`, Pi is checked with a no-network, no-pull Python probe inside
  `--executor-image TAG`, or the sole listed image.
  Forge CLIs remain host
  prerequisites, while Pi and project toolchains belong in prepared
  project images. See
  `01_Documentation/Web_Interface.md`.

- The bundle still requires the matching Python with `venv` and `ensurepip`
  (Ubuntu's `python3-venv` package or an equivalent offline Python distribution), `git`,
  the selected forge CLI and a container runtime on the deployment
  host. `uv` is needed only on the build host.
- Native Windows executable and Ubuntu package creation remain future work.
