<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Repository tools

Source tools are grouped by their purpose. Run them from any directory: each
command resolves the repository from its own file location. Use `python3` on
Linux if `python` is unavailable.

| Folder | Responsibility | Entry points and assets |
|---|---|---|
| `setup/` | Prepare the development machine or an optional source-checkout CLI service. | `setup_development_environment.py`, `install_linux_service.sh`, `install_windows_service.ps1`, `adore.service`. |
| `build/` | Build production web assets and maintain inputs used by the application and executor images. | `build_web_assets.py`, `generate_pi_model_catalog.py`, `executor_images/adore/`. |
| `package/` | Assemble and verify the complete user distribution. | `create_delivery_package.py`, `verify_delivery_package.py`, `launcher_templates/`, `release_checks/`, `tests/`. |

## Development setup

```text
python 02_Tools/setup/setup_development_environment.py
```

Requires Python 3.11+, uv, Git and Node.js 22.18+ with npm. Synchronizes frozen
Python dependencies, frontend dependencies and Chromium for UI development.
It does not run tests, install services or configure credentials.

The optional Linux/Windows service installers operate on a source checkout and
manage the standalone CLI poller. See [setup and service instructions](setup/README.md).
Packaged users start ADORE with the included Start/Stop commands instead.

## Build

```text
python 02_Tools/build/build_web_assets.py
```

Uses the prepared frontend environment to type-check and compile the application,
then applies legal notices and the build fingerprint. Production assets are
written into `04_Software/adore/web/static/`, where the Python wheel includes them.
This command installs nothing and runs no tests.

`build/generate_pi_model_catalog.py` refreshes the provider/model catalog from
the pinned Pi 1.5.2 offline, including regional provider variants, model IDs,
thinking levels and endpoint hosts. Run it when changing the pinned Pi, using its `--help`
for the required local Node and Pi paths. It is not a routine package step.

`build/executor_images/adore/` contains the ADORE project's executor Dockerfile,
build context rules and export manifest. It builds an agent environment, not the
user application archive. See its [image instructions](build/executor_images/adore/README.md).
Build images explicitly with a scratch tag when active jobs use the existing tag.

`build/verify_container_runtime.sh` is an explicit live check for Docker/Podman.
Run it on the Linux execution host or inside WSL. It uses the recipe assets in
`04_Software/docker/`, creates scratch resources and can build an absent image.
It is separate from setup, packaging and automated product tests. Usage is in
the [container guide](../04_Software/docker/README.md#verify-a-container-runtime).

## Package

```text
python 02_Tools/package/create_delivery_package.py --runtime-mode offline
python 02_Tools/package/create_delivery_package.py --runtime-mode online
python 02_Tools/package/verify_delivery_package.py --runtime-mode offline
```

Creation builds web assets, checks release consistency and notes, builds the
Python wheel and bundles CPython with locked dependencies. It writes the native
final ZIP or TAR.GZ plus its SHA-256 file into repository-relative `07_Delivery/`.
Windows archives are built on Windows x64; Linux archives on Linux x64, including
WSL Ubuntu. Building requires network access. End users need no installed Python,
Node.js or uv to open the interface; offline archives also include native Pi. The builder
also downloads checksum-pinned Node, fd and ripgrep archives and installs the
exact Pi/web packages into application-owned media. The `offline` flavor includes these native tools. The smaller `online` flavor
omits them: prepare host Node.js 22.23.4+ in the 22.x line with npm, then run
`pi install` with registry access for native execution. Both flavors include
Python and application dependencies and open the interface offline. Archive
names include the flavor; building both modes on each OS creates four archives. `--use-existing-web-assets` checks the existing source/output fingerprint
and release metadata without rebuilding an already prepared frontend.

`package/create_executor_image_archives.py --build` builds only the generic
base executor from a clean committed checkout and publishes its compressed image
archive plus SHA-256 file. Each image has
a unique release/source tag; existing tags and containers are untouched. Use
`--only executor-base` (repeatable) to select roles, `--runtime podman` for Podman,
or `--image executor-base=LOCAL_TAG` without `--build` to export prepared local
images. Use `--build-network host` when the build host requires host networking
for its download endpoints; the default uses the runtime build network.
Standard image delivery contains only **executor-base**, with Pi and its execution
dependencies. This Linux image serves Linux hosts and Docker/WSL on Windows.
Project-specific development images and the Squid proxy image for allowlisted
container access are prepared separately; neither is generated by delivery tooling.

The image archives load directly with `docker load --input` or
`podman load --input`; the target needs no registry access or build tools.

Verification accepts an optional archive path under `07_Delivery/`. It checks
identity and hashes, extracts the archive into temporary storage, and exercises
the included application with isolated user data and bounded startup/shutdown.
It prints results and removes temporary work on exit.

Normal packaged startup checks metadata without scanning installed files, and
stop uses the running instance ownership record. Users can run
`Start-ADORE.cmd --verify` or `./start-adore.sh --verify` separately for the full
checksum and dependency check; the builder always performs it before publication.

`package/launcher_templates/` holds the files copied into the user archive:
Start, Stop, CLI wrappers, the Python launcher, startup configuration and the
package README. These are launch templates, not shared container scripts.
`package/release_checks/` contains automatically invoked release and asset checks.
`package/tests/` retains existing offline distribution-contract tests. Do not add
or run automated tests for setup or service-installation scripts.

Only final delivery archives and optional adjacent `.sha256` files remain in
`07_Delivery/`. Intermediate Python runtimes, wheels, extracted archives and
verification data use automatically cleaned OS temporary directories. Reports
and logs are not saved in the delivery directory.
