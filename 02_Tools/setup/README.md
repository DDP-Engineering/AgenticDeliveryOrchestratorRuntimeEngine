<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Environment and service setup

## Development checkout

Run `python 02_Tools/setup/setup_development_environment.py`. It requires
Python 3.11+, uv, Git and Node.js 22.18+ with npm, installs locked development
dependencies and Chromium, and runs no tests or services. See the
[tools index](../README.md) for build and packaging commands.

## Optional standalone CLI service

`install_linux_service.sh` and `install_windows_service.ps1` prepare the sibling
`04_Software/` source checkout, validate its configuration and optionally register
the standalone CLI poller. They are separate from ordinary packaged Start/Stop.
They do not install the web application's API and worker pair.

Before installation, prepare `04_Software/config.toml`, authenticate the host
forge CLI and Git, and supply the required provider credentials outside source
control. Prepare the project's selected execution environment. See
[Configuration](../../01_Documentation/Configuration_Reference.md),
[Security](../../01_Documentation/Security_And_Credentials.md) and
[executor images](../../04_Software/docker/README.md).

From the repository root on Linux:

```sh
bash 02_Tools/setup/install_linux_service.sh
bash 02_Tools/setup/install_linux_service.sh --service
bash 02_Tools/setup/install_linux_service.sh --uninstall
```

The first command prepares only. `--service` installs and starts `adore.service`
using the adjacent template. `ADORE_USER` selects the service account. Logs use
`journalctl -u adore -f` and the configured run store. `--skip-image` skips image
preparation; `--allow-open-egress` explicitly allows unattended open egress.

On Windows:

```powershell
.\02_Tools\setup\install_windows_service.ps1 -NoTask
.\02_Tools\setup\install_windows_service.ps1
.\02_Tools\setup\install_windows_service.ps1 -Mode once -IntervalMinutes 10
.\02_Tools\setup\install_windows_service.ps1 -Uninstall
```

The default registers the CLI loop at logon. `-NoTask` prepares only.
`-Runtime` selects Docker, Podman or a WSL wrapper; `-ImageTag` selects the prepared
image. Windows verifies images instead of building them. `-SkipImageCheck` skips
that verification. `-AllowOpenEgress` explicitly allows unattended open egress.

Both installers fail on incomplete source layouts or invalid settings. Re-running
refreshes the source environment and service/task registration. Uninstall removes
the service/task and retains application state, worktrees and containers.

## Web operation

Use the package Start/Stop commands for the complete web application. A custom
service installation must supervise the API and exactly one `adore-web-worker`
under the same account and absolute home. The supervisor owns project workers,
configuration work and bounded job pools. Do not register standalone CLI polling
for profiles already managed by that supervisor. See
[Web interface](../../01_Documentation/Web_Interface.md) and
[source-service boundaries](../../05_SoftwareDocu/Component_Packaging.md#source-services).
