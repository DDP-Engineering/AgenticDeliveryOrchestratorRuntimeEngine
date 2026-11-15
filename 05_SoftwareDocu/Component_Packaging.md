<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Repository environment, build and packaging tools

## 1. Purpose

Separate development preparation, production web builds and complete user
distribution packaging under `02_Tools/setup/`, `02_Tools/build/` and
`02_Tools/package/`. Windows x64 ZIP and Linux x64 TAR.GZ, each in explicitly
named offline and online flavors, are the final
user delivery formats. See [Distribution](Component_Portable_Distribution.md)
for the included launcher and runtime contracts.

## 2. Responsibilities

- `setup/setup_development_environment.py` checks host tools, synchronizes frozen
  Python dependencies, runs `npm ci` and provisions Chromium. It installs no
  services and runs no tests. Optional source-checkout CLI service installers
  and their unit template live alongside it in `setup/`.
- `build/build_web_assets.py` invokes the frontend build with a thirty-minute
  limit. The build type-checks, compiles and stamps production assets. It
  installs no dependencies and produces no delivery archives.
- `build/generate_pi_model_catalog.py` refreshes the pinned Pi catalog offline.
  `build/executor_images/adore/` owns the project's explicit executor image recipe.
- `package/create_delivery_package.py` invokes the web build first, then the
  release checks, and assembles the application wheel, locked dependencies,
  CPython, curated user guides and launch templates in temporary staging.
  `--runtime-mode offline` (default) adds Node/Pi/search dependencies; `online`
  omits them and uses the managed native installation after host Node/npm setup.
- `package/bundle_native_tools.py` downloads checksum-pinned Node/fd/ripgrep
  archives, installs pinned Pi/web dependencies without lifecycle scripts,
  retains licenses and dereferences internal links for relocatable delivery.
- `package/create_executor_image_archives.py` explicitly builds or exports
  Linux amd64 images to separate compressed Docker archives. Builds require a
  clean committed checkout and use unique release/source tags. Existing local
  images can be selected explicitly; no push or running-container replacement occurs.
- `package/verify_delivery_package.py` checks a final archive and exercises its
  relocated application using isolated temporary user data.
- `package/release_checks/` owns release identity, four-locale release notes and
  static-asset licensing/fingerprints. `package/launcher_templates/` owns the
  shipped Start/Stop/CLI wrappers and launcher. Existing distribution-contract
  tests live in `package/tests/`.

## 3. Inputs and outputs

Build hosts require Python 3.11+, uv, Git and Node.js 22.18+ with npm.
Source inputs include `04_Software/`, Python/frontend lockfiles, the curated
user guides and launcher templates. Each command resolves the repository from
its current source location, independently of the caller's working directory.

Web builds update `04_Software/adore/web/static/`, which the application wheel
includes. Package creation writes only the native final archive and adjacent
SHA-256 file into repository-relative `07_Delivery/`. Temporary wheels, runtimes,
staging and verification data use automatically cleaned OS temporary directories.
Results print to the console without retained verification reports.

## 4. Usage

```text
python 02_Tools/setup/setup_development_environment.py
python 02_Tools/build/build_web_assets.py
python 02_Tools/package/create_delivery_package.py
python 02_Tools/package/verify_delivery_package.py
```

Package creation runs the web build automatically. Build and verify each archive
on its matching operating system. Explicit archive paths must be in `07_Delivery/`.

## 5. Validation and build integrity

Do not add or run automated tests for setup or service-installation scripts.
Application distribution acceptance is separate. Release consistency verifies
the committed frontend input/output fingerprint and independently rebuilds into
temporary storage with the installed Vite. It rejects stale or modified assets
without installing dependencies. Update the committed production bundle whenever
frontend build inputs change.

The wheel also includes the canonical executor base Dockerfile and Pi helpers
from `04_Software/docker/` as product assets for source-recipe export. The image-delivery tool builds
and exports them before delivery. Node license text is retained in the image at
/usr/local/LICENSE, alongside the Pi dependency and search-tool notices. End users load the compressed archives without
registry access or build tools; Docker/Podman itself remains a prerequisite.

## Source services

`02_Tools/setup/install_linux_service.sh`, `install_windows_service.ps1` and the
adjacent adore.service template configure a standalone CLI poller for a source
checkout. They do not install the complete web control plane. Linux uses systemd;
Windows uses Task Scheduler, with the default loop starting at logon and an
optional periodic once mode. Preparation-only and explicit uninstall are supported.
Uninstall retains run state, worktrees, containers and other operator data.

Installers validate the source layout/configuration and provision the web Python
extra. Linux can prepare missing shared runtime images; Windows verifies prepared
images. Explicit skip options retain operator responsibility. Unattended open
egress requires its explicit opt-in. Service identity and absolute config paths
belong to the operator; source startup uses the frozen Python environment.
Commands, flags and OS prerequisites live in the
[setup README](../02_Tools/setup/README.md), not a second deployment manual.

For the web application, the package launcher supervises one API and exactly one
adore-web-worker for the same absolute home/account. That supervisor owns project
workers and configuration work. Never run an additional standalone CLI poller for
a profile managed by the web supervisor. Custom service supervision follows the
same pair/ownership boundary. See [Web worker](Component_Web_Worker.md) and
[Portable distribution](Component_Portable_Distribution.md).

Setup/service scripts are maintained directly as repository tools. Do not add or
run automated deployment/environment setup tests for them.
