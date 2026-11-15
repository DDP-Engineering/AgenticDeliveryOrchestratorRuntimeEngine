<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Start ADORE

Extract the complete archive into a folder where you can run programs.
Both **offline** and **online** archives include Python, ADORE, the compiled web
interface and application dependencies. Neither needs system Python, uv,
administrator privileges or Internet access to open the interface.

Choose **offline** for included Node, Pi, its web extension, fd and ripgrep.
Choose **online** for a smaller archive; native execution then needs separately
prepared Node.js 22.23.4 or later in the 22.x line with npm and Internet access
for `ADORE.cmd pi install` (Windows) or `./adore.sh pi install` (Linux).
The online package does not download Node automatically.

## Windows 11 x64

Double-click **Start-ADORE.cmd**. Keep its window open while using ADORE.
The browser opens when the web server and local supervisor are ready. The
supervisor owns independent project workers, run pools and a configuration worker.
Double-click **Stop-ADORE.cmd**, or press Ctrl+C in the start window, to stop.
Use Stop-ADORE before closing the console window or updating the application.

## Linux x64 (glibc)

Extract the TAR.GZ, enter its folder and run:

```sh
./start-adore.sh
```

On a desktop, ADORE opens the browser. On a server, open the displayed address
in a browser on that machine. Press Ctrl+C or run `./stop-adore.sh` to stop.
The server listens only on loopback; use the documented TLS reverse-proxy
configuration for access from other machines.

## First use

The default address is <http://127.0.0.1:8765/>. A new installation creates the
account **admin**, password **admin**; change it when signing in.
Add and check your projects in the interface. Git, an authenticated forge CLI
(`tea`, `gh` or `glab`), project-specific build tools and Docker/Podman when selected are
project prerequisites. They are checked when configuring a project and are
not required merely to open the interface. Do not start an additional
`adore run --loop` scheduler for projects managed by the web worker.

## Executor setup

In the offline archive, native execution uses the included Node and Pi directly. Run `ADORE.cmd pi verify`
on Windows or `./adore.sh pi verify` on Linux. `pi install` only verifies the
bundled runtime; it makes no downloads. Keep the application directory intact.
In the online archive, prepare Node/npm first, then run `pi install` and `pi verify`
as the account running ADORE. Git and project-specific tools are separate prerequisites.

Container images are separate compressed archives. On a host with Docker/Podman
already installed, import the required executor and egress-proxy archives:

```sh
docker load --input adore-0.16.0-executor-base-linux-x64.tar.gz
docker load --input adore-0.16.0-egress-proxy-linux-x64.tar.gz
```

Use `podman load --input` with Podman. The command reports the imported image tag;
select that exact tag in project Settings. The optional executor-adore archive
adds the ADORE project toolchain and Chromium. Importing requires no registry or
image build. Project-specific images must likewise be prepared before delivery.
AI/model and remote repository access still require their configured network.

## Data, logs and updates

Data stays outside this application folder: `%APPDATA%\adore` on Windows,
or `$XDG_CONFIG_HOME/adore` (normally `~/.config/adore`) on Linux.
`ADORE_HOME` overrides the location. Existing ADORE data is reused; back it up
before upgrading. Do not delete the database's initialization marker.

Logs are in `logs/launcher.log` under the data folder. Four rotating log files
use at most approximately 8 MiB. Startup failures show an error and the log
location. Starting again opens the existing instance for that data folder.
An unrelated program occupying the port produces an error.

To replace the application, stop ADORE, back up its data and extract into a
new folder. Each build accepts only its current stored formats; a refused store
names the database/marker or run directory to delete for a fresh start. Never
delete live ownership evidence. You can move the application folder while stopped.

## Optional arguments

The start scripts accept `--no-browser`, `--port 8766`, `--home <data-folder>`,
`--verify`, `--startup-timeout 45` (1..120 seconds) and `--restart-limit 3`
(0..10). Use the same `--home` for the stop script if you override it.
The launcher supervises both services, stops the surviving service after a
crash, and retries the pair up to three times. Shutdown waits up to fifteen
seconds before forcing termination. The supervisor stops all project/run
children with bounded tree shutdown. Parent creation identities fence children
if the launcher disappears. Interrupted jobs and uncertain operations retain
recovery evidence and require inspection; they are not automatically restarted.

CLI access uses `ADORE.cmd --help` on Windows or `./adore.sh --help` on Linux.
See [Documentation](Documentation/README.md) for project configuration and
operating instructions.

## Included software

The CPython distribution is supplied by
[Astral Python Standalone Builds](https://github.com/astral-sh/python-build-standalone).
Node is supplied by nodejs.org. The installed Pi/web packages retain their
upstream licenses; fd and ripgrep notices are retained beside the bundled tools.
The delivery manifest records their exact versions and checksums. CPython
licenses are retained inside `python/`, together with third-party license
files distributed by the runtime. Python dependency licenses are retained in
their installed package metadata. ADORE's license is in `LICENSE.txt`.
`manifest.json` records versions, the dependency-lock checksum and SHA-256
checksums for the installation. It detects damaged media; it is not a signed
publisher identity certificate.
