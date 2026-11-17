# Component: Portable user distribution

Sources: `02_Tools/package/create_delivery_package.py`, `02_Tools/package/launcher_templates/`,
`02_Tools/package/verify_delivery_package.py`, `02_Tools/package/tests/test_delivery_package.py`.

## 1. Purpose

Deliver a complete native Windows x64 ZIP or Linux x64 TAR.GZ that starts the
web API and command worker without system Python or uv. Offline archives also
supply native Pi without Node.js/npm setup or installation downloads. Online
archives leave native executor provisioning to the operator.
Packaging and launcher sources belong to `02_Tools/`; only final archives and
optional adjacent SHA-256 files belong to `07_Delivery/`. Build/verification
work uses automatically cleaned OS temporary storage; results go to the console.
Application code remains in `04_Software/`.

## 2. Responsibilities

- Include managed CPython from Astral Python Standalone Builds and dependency
  wheels selected by the frozen lock's `web` extra, with third-party licenses.
  Each wheel must match the hash recorded in the lock; a mismatch stops the build.
- Include the application wheel, precompiled web assets, curated user documentation,
  legal notices, native start/stop/CLI wrappers and checksum inventory.
- Start a bounded API/worker pair, open a ready browser interface, reopen the
  existing instance for the same data home, and provide explicit stop controls.
- Keep runtime user data and rotating logs outside extracted installation files.

Offline native delivery includes Node 22.23.4, Pi 1.5.2, pi-web-access 0.46.0, fd 10.5.1
and ripgrep 15.2.0. Git, forge authentication, project toolchain provisioning, model credentials,
containers and service-manager installation remain project/operator setup.
`--runtime-mode online` omits the native payload. It still includes Python and
application dependencies, so the interface opens offline; native execution needs
host Node 22.23.4+ in the 22.x line with npm and registry access for `pi install`.
`--runtime-mode offline` is the default. There is no automatic Node download
on an online installation.

## 3. Implementation Overview

The builder runs on each matching OS. --use-existing-web-assets keeps the
verified frontend fingerprint and release checks while avoiding another frontend
build; default packaging builds and independently checks it. CPython's pin is declared once as
`PYTHON_VERSION` in the builder. `uv python install` provisions a fresh managed
runtime inside an owned native OS temporary workspace; a dereferenced copy becomes
the package's `python/`. The builder installs a freshly built ADORE wheel and
the frozen web dependency set into that copy, using uv's explicit system-write
override only for this isolated copy. It does not modify host Python.

Build-specific console scripts and local-wheel URL metadata are removed.
Wrappers resolve their interpreter and launcher relative to their own location.
Unused standard-library test/development/Tk material is excluded. No user
profiles, credentials, virtual environment or repository working state is copied.
The package's verifier checks every file before publication to the final archive.
Normal startup reads only the bounded manifest and checks host/application version
metadata. It performs no recursive inventory scan or file hashing. Stop bypasses
the package manifest entirely and uses the existing validated ownership record,
so damaged media does not delay a stop request. This common launcher behavior
applies to Windows/Linux and offline/online packages without a verification cache.
Full integrity and dependency verification is explicit: `Start-ADORE.cmd --verify`
or `./start-adore.sh --verify`. At most eight readers hash regular files in
batches of 256; the entire inventory, including native dependencies, is checked.
Normal startup no longer detects arbitrary payload damage before services start;
operators use the explicit full check after extraction or to diagnose corruption.
The native payload lives inside the installed application at adore/_native_tools.
Node/fd/ripgrep archives have fixed published SHA-256 pins; Pi/web dependencies
are installed only on the build host. npm metadata and upstream dependency
licenses remain present. Unix executable links are dereferenced; npm/npx entry
wrappers retain their correct relative module resolution after relocation.
The runtime marker in adore_portable.pth selects this exact payload and refuses
incomplete media instead of choosing host tools. Bundled pi install is a
verification operation with no network or copying to user data.
An installed `adore_portable.pth` disables bytecode writes for engine child
invocations as well as the top-level launcher. Bytecode is rebuilt with
hash-based invalidation and relative code filenames. This covers Python
bootstrap imports that precede `.pth` processing and avoids timestamp changes
during archive extraction invalidating those caches.
Native temporary staging avoids slow small-file operations on WSL-mounted
Windows volumes. Publication copies a complete archive to a temporary file in
`07_Delivery/` and replaces the final name atomically on that volume.

The launcher uses a cross-platform OS file lock in the existing ADORE home.
Only the lock owner publishes instance metadata or starts services. A second
launcher validates the owner's loopback port and waits for worker readiness.
It opens that instance without replacing its ownership. An unrelated occupied
port fails before service startup. Corrupt ownership records and invalid package
metadata produce explicit `DeliveryError` results; full verification additionally
rejects corrupt, missing, linked or unlisted payload files. A stale record alone
cannot confer ownership.

Both service processes use the bundled interpreter and a sanitized Python
environment. A private per-run stop file bridges shutdown requests even when
Windows has no attached console. Native signals and bounded kill fallbacks
handle services that do not exit. A crashed sibling is stopped before a whole
pair restart; the default allows three restarts. API/worker application code
and durable state contracts are unchanged.

## 4. Dependencies

- Build host: Python 3.11+, uv, matching Windows/Linux x64, build/dependency
  network access, and compiled frontend assets. Node.js/npm build the frontend.
- Runtime host: Windows 11 x64 or glibc Linux x64. Ubuntu/WSL is the native
  Linux acceptance environment. The included interpreter is not an Alpine/musl build.
- Redistributed runtime: [Python Standalone Builds](https://docs.astral.sh/python-build-standalone/).
  Retain upstream licenses and installed dependency license metadata.

## 5. Inputs And Outputs

- Build input: `04_Software/pyproject.toml`, `uv.lock`, application/frontend source,
  frontend lockfile and the `02_Tools/package/launcher_templates/` templates. Release checks and
  frontend compilation/licensing run automatically before archive construction.
- Build output: `07_Delivery/adore-<version>-<offline|online>-windows-x64.zip` or
  `07_Delivery/adore-<version>-<offline|online>-linux-x64.tar.gz`. Each archive has an adjacent
  `.sha256` file naming that archive without directory prefixes. There are no
  retained technical directories, README files, test reports or logs in delivery.
  Output is fixed to repository-relative `07_Delivery/`; no output option is needed.
- Manifest: schema 1, required `runtime_delivery` (`offline` or `online`),
  application/Python/OS/architecture and native tool versions (empty for online), dependency-lock hash,
  interpreter provenance and SHA-256 inventory. This detects damage, not signer identity.
- Limits: each external build command 1800 seconds; 60000 files / 1 GiB before
  archiving; startup 1..120 seconds; restart limit 0..10; shutdown 15 seconds
  before forced termination; log rotation 2 MiB with three backups.
- Data: normal `adore_home()` semantics, overridden by `ADORE_HOME` or `--home`.
  A data home inside the extracted installation is rejected.

## 8. Usage

Prepare the checkout once, then create/verify on each native host:

```text
python 02_Tools/setup/setup_development_environment.py
python 02_Tools/package/create_delivery_package.py --runtime-mode offline
python 02_Tools/package/create_delivery_package.py --runtime-mode online
python 02_Tools/package/verify_delivery_package.py --runtime-mode offline
```

Linux can use `python3` for these tooling commands. User startup is
`Start-ADORE.cmd` on Windows or `./start-adore.sh` on Linux. See the copied
`02_Tools/package/launcher_templates/README.md` for data, logs, updates, shutdown and optional flags.

## 9. Validation And Tests

`python -m unittest discover -s 02_Tools/package/tests -p test_delivery_package.py -v` covers
complete manifests, tampering, missing/unlisted files, invalid external paths,
host/schema mismatches, malformed launch limits and unsupported output overrides.

`python 02_Tools/package/verify_delivery_package.py <archive-in-07_Delivery>` extracts and moves
the actual archive into a path with spaces, removes all host tools from PATH,
verifies native dependency imports and CLI startup, checks corruption/port
rejection, starts the actual API/worker, verifies the fake browser sees ready
services, serves the compiled UI, reopens the existing instance and stops it.
Persistent user data and unchanged media are checked. Extracted packages,
isolated user data and temporary logs are owned by a context-managed OS temporary
directory on both platforms and removed on success or failure. Results go to
the console; no receipt or report is saved. Unit fixtures likewise use OS
temporary directories. No existing home, forge, executor or model is accessed.
Each command and wait has an explicit timeout. Deployment/environment setup
script tests are not added or run.

Distribution-only changes require no application release-note or in-app help
entry. User-facing operating instructions are maintained with the distribution.

## 10. Limitations

Native Windows and glibc Linux builds are separate artifacts. macOS, ARM64,
automatic updates, signing and OS installers are not part of this distribution.
Close the application through Stop-ADORE/Ctrl+C before closing its console or
replacing files. Each build accepts only the current stored schemas. Unsupported
stores are refused with a message naming the files/directories to delete; the
application never migrates or recreates them automatically. Project jobs still require their configured host tools
and connectivity; only application startup is self-contained and offline.

Native acceptance also proves authenticated read-only host folder navigation,
malformed path refusal and unchanged filesystem selection. The compiled interface
includes automatic/custom clone destinations and closed advanced native options.

## User documentation selection

Self-contained Windows ZIP/Linux TAR.GZ user media contains only
Documentation/README.md, Administrator_Guide.md and Troubleshooting.md, sourced
from the three flat source guides in `01_Documentation/`, with User_Guide.md
renamed README.md in the archive. `create_delivery_package.copy_user_documentation` uses
a fixed three-file allowlist and refuses missing/linked required sources before
staging. Internal code style, implementation references and the operator quick
reference remain repository material. The full four-locale interface
help remains in the compiled app. `verify_delivery_package.py` checks exact inventory and all
relative guide links in each actual archive; Tools unit tests cover extra and
missing/linked inputs.
