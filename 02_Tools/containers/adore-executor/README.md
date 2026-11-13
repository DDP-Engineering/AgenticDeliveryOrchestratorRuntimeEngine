<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Synthetic ADORE project executor

This recipe reconstructs the tools observed in the DCP project's
`adore-executor-adore:pw1.63.0-b73dae3` image on 2026-11-11. It starts from
Ubuntu 22.04 and includes the executor base tooling, Pi 1.4.0, Node 22.23.4,
uv 0.13.7, CPython 3.11.18, and Playwright 1.63.0 with Chromium and its system
dependencies. It does not require the original local executor image.
The browser archives use the exact versions reported by Playwright 1.63.0:
Chromium 153.0.8010.12 (revision 1243) and FFmpeg revision 1011. They are fetched
over HTTPS with curl, bounded timeouts and retries; this avoids the Node HTTPS
download timeout observed on DCP. When changing Playwright, update the browser
versions and cache directory revisions together from `playwright install --dry-run
chromium`.

This is a functional reconstruction, not a byte-identical image backup. Ubuntu
packages and transitive npm dependencies are resolved when building. Packages
installed later by an agent, project worktrees, Python environments, credentials,
and job state are not copied. Build access to Ubuntu, Node, npm, uv/Python,
GitLab, GitHub and Playwright package sources is required. Runtime network access
remains an independent ADORE setting.

The build context is the repository root. From that directory:

```sh
docker build --file 02_Tools/containers/adore-executor/Dockerfile \
  --tag adore-executor-adore:synthetic-check .
docker run --rm --network none adore-executor-adore:synthetic-check python --version
docker run --rm --network none adore-executor-adore:synthetic-check pi --version
```

The default non-root account is `adore`, UID/GID 1000. Supply `USER_UID` and
`USER_GID` build arguments when the execution server uses another account.
Repository dependencies remain the agent's responsibility in its job container.
The recipe does not embed a shared machine identity: if tests need a machine-id,
prepare a unique identity in that job's container, never copy the server's ID.

`build.json` declares every exported input and the exact tag currently saved for
the DCP project. Register it as
`02_Tools/containers/adore-executor/build.json@<full-source-commit>` in
`container.build_definition`, after that commit is available in the enrolled
project clone. A reviewed Git snapshot containing just these inputs also works;
keep its commit reachable with a local reference on the server.

Then use **Settings → Export raw configuration → Include Docker build files**.
The archive contains `config.toml`, `compose.yaml`, `BUILD.txt` and this build
context. After extraction, `docker compose build` rebuilds and tags the image
named in the configuration. On a server with existing jobs, verify with a scratch
tag first; do not replace the existing image tag or change a job container during
verification. Exporting and registering a definition do not rebuild the image
or restart jobs.
