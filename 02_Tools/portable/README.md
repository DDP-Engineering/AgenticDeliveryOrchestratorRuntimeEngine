<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Start ADORE

Extract the complete archive into a folder where you can run programs.
Python, the ADORE application, the compiled web interface and its dependencies
are included. Installation, administrator privileges, system Python, uv,
Node.js and Internet access are not needed to start the interface.

## Windows 11 x64

Double-click **Start-ADORE.cmd**. Keep its window open while using ADORE.
The browser opens when both the web server and command worker are ready.
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
(`tea`, `gh` or `glab`), executor tools and Docker/Podman when selected are
project prerequisites. They are checked when configuring a project and are
not required merely to open the interface. Do not start an additional
`adore run --loop` scheduler for projects managed by the web worker.

## Data, logs and updates

Data stays outside this application folder: `%APPDATA%\adore` on Windows,
or `$XDG_CONFIG_HOME/adore` (normally `~/.config/adore`) on Linux.
`ADORE_HOME` overrides the location. Existing ADORE data is reused; back it up
before upgrading. Do not delete the database's initialization marker.

Logs are in `logs/launcher.log` under the data folder. Four rotating log files
use at most approximately 8 MiB. Startup failures show an error and the log
location. Starting again opens the existing instance for that data folder.
An unrelated program occupying the port produces an error.

To update, stop ADORE, back up its data, extract the new version into a new
folder and start it. Your accounts, projects and history remain in the data
folder. Preserve a backup for rollback; older versions cannot reverse newer
database migrations. You can move or rename the extracted application folder
while ADORE is stopped.

## Optional arguments

The start scripts accept `--no-browser`, `--port 8766`, `--home <data-folder>`,
`--verify`, `--startup-timeout 45` (1..120 seconds) and `--restart-limit 3`
(0..10). Use the same `--home` for the stop script if you override it.
The launcher supervises both services, stops the surviving service after a
crash, and retries the pair up to three times. Shutdown waits up to fifteen
seconds before forcing termination. Interrupted jobs retain recovery state.

CLI access uses `ADORE.cmd --help` on Windows or `./adore.sh --help` on Linux.
See [Documentation](Documentation/README.md) for project configuration and
operating instructions.

## Included software

The CPython distribution is supplied by
[Astral Python Standalone Builds](https://github.com/astral-sh/python-build-standalone).
Its license is retained inside `python/`, together with third-party license
files distributed by the runtime. Python dependency licenses are retained in
their installed package metadata. ADORE's license is in `LICENSE.txt`.
`manifest.json` records versions, the dependency-lock checksum and SHA-256
checksums for the installation. It detects damaged media; it is not a signed
publisher identity certificate.
