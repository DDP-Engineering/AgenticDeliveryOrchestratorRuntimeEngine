# ADORE environment map

Read only the setup or verification section needed for this task.
Commands and pinned dependencies live in their source files; do not duplicate machine-specific paths.

## Toolchain and setup

- Python 3.11+, uv and Git. Product core is standard-library Python; web uses the locked optional extra.
- From `04_Software`: `uv sync --frozen --extra web` installs development/web dependencies.
- From `04_Software/web`: `npm ci`; browser work additionally needs `npx playwright install chromium`.
- `.agentic/aegis.toml` contains canonical verification commands and `04_Software` workdir.
- `02_Tools/setup/setup_development_environment.py` prepares development tooling, not services or tests.
- Current commands and host prerequisites: `01_Documentation/Getting_Started.md` and `02_Tools/README.md`.

## Focused verification

```text
# From 04_Software
uv run --frozen --no-sync python -m pytest -n 0 tests/test_COMPONENT.py
uv run --frozen --no-sync ruff check adore/CHANGED.py tests/test_CHANGED.py

# From 04_Software/web
node --test tests/CHANGED.test.mjs
npm run typecheck
npm run build:e2e
npx playwright test e2e/CHANGED.spec.ts --grep SCENARIO
```

Select actual changed contracts/consumers rather than literal placeholder names.
Pytest defaults to two xdist workers grouped by file; use `-n 0` for small selections.
Non-authentication fixtures use low-cost real Argon2; production hashing remains available
through `real_password_hashing` or `--real-password-hashing`. Mutable homes/databases stay isolated.
Details: `05_SoftwareDocu/Component_Test_Infrastructure.md`.

Browser tests use a disposable API/worker home, fake external command boundaries, loopback port
18765 and the dedicated `.e2e-dist` build. The current suite is serial because its fixture server
is shared. Do not simply increase workers without isolation. Authentication/polling/cleanup
contracts and bounded process waits remain real unless the existing fixture explicitly controls time.
Reuse a valid build/proof when its inputs are unchanged. Full suites, native acceptance and archives
follow the user's gate; never rerun them just for handover or journal edits.

## Execution prerequisites

- Pi is pinned by the native installer/container recipe. Offline delivery includes Node/Pi/tools;
  online/source installs require host Node/npm and `adore pi install`, then `adore pi verify`.
- Native jobs run as the service account. Windows uses owned Job Objects; Linux requires a writable
  delegated cgroup-v2 subtree with `cgroup.kill`. Host credentials/network are not a sandbox.
- Containers use an installed Docker/Podman image; no implicit image pull. Egress can be open,
  none or allowlisted according to the reviewed configuration. Images are built outside the conductor.
- Forge CLI authentication is host-only (`gh`, `glab`, `tea`, or Azure CLI with azure-devops).
  Git clone/push credentials are separate. Providers use their explicit protected credentials;
  ChatGPT refresh tokens remain server-side. Never load operator secrets into test fixtures.
- References: `01_Documentation/Local_Execution.md`, `Security_And_Credentials.md`,
  `Azure_DevOps_Services.md`, `Container_Preparation.md`, and `04_Software/docker/README.md`.

## Build, release and delivery

`npm run build` in `04_Software/web` writes deployable assets and their fingerprint.
An already valid frontend needs no rebuild for Python-only, documentation or release-note changes.
`01_Documentation/Releases.md` owns version changes, release notes and explicit release checks.
`02_Tools/README.md` owns setup/build/package commands; delivery outputs go only in `07_Delivery`.
Do not conflate source verification, package verification and live deployment.

## Platform and storage

Use portable Python for the core. `.gitattributes` owns LF/CRLF rules; preserve them in scripted edits.
Windows and WSL/Linux have independent environments and native runtime requirements.
All tests use temporary ADORE_HOME values. Stored-format failures require operator-chosen cleanup;
never repair them by introducing migrations or compatibility readers.
