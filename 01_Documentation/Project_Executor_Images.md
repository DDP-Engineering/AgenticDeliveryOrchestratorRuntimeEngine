<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project executor images

The server administrator prepares the executor image outside ADORE: the Dockerfile
and the build stay on the server. Choosing the image is done in ADORE: enrollment
step 2 and **Project → Settings → Agent and model** offer **Runs in**, **Container
runtime** and **Executor image**, with suggestions read from the images present on
the server. For a container project, Settings also displays the effective
image and expandable **Environment preparation instructions**. The administrator
also sees the resolved server profile `config.toml` path; authorized developers
see guidance to contact the administrator. Local projects omit this notice.

## Create the definition in the project repository

Use a standard Dockerfile. The recommended layout is:

```text
executor/
  Dockerfile
  README.md
```

Record build commands, required versions, verification and profile selection in
`executor/README.md`. Start from a compatible base already installed on the ADORE
server. The canonical base tag already contains Python, sh and the pinned Pi,
ADORE's only coding agent; a different base must provide them itself.

```dockerfile
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Replace the comment with installation commands for your project. Keep credentials
outside the Dockerfile. Project library preparation remains the optional reviewed
per-worktree recipe described in [Container preparation](Container_Preparation.md).

## Build and verify on the execution server

Use the runtime installed on that server, Docker or Podman. From the repository
root, for Docker:

```sh
docker build --file executor/Dockerfile --tag adore-executor-project:1.0 .
docker run --rm --network none --entrypoint python3 adore-executor-project:1.0 --version
```

Verify Pi and every project tool as the image's non-root user.
Use controlled versioned tags or immutable image IDs for reproducible deployment.
Adding `executor/Dockerfile` to the repository does not trigger a build in ADORE.
The suggested location is an operator convention, not a watched file contract.

## Select the prepared image

In the web interface, choose the image in **Executor image** on enrollment step 2, or
edit **Agent container image** in Settings → Agent and model. The field is free text
and suggests the images present on the ADORE server (`<runtime> images`, for the
selected **Container runtime**); a notice appears when the typed image is not on the
server or the list cannot be read. Settings edits go through the reviewed
configuration flow: prepare candidate, review, apply.

To select the image in the server profile instead, pause pickup and ensure there are
no active jobs. Update the existing server profile at the path displayed to the
administrator in Settings → Agent and model:

```toml
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
[execution]
backend = "container"
[container]
image = "adore-executor-project:1.0"
required_tool_checks = ["python3 --version"]
```

These are sections of the existing profile, not a complete replacement profile.
Add the Pi and project checks and keep any configured recipe's image
consistent: its validated plan owns the effective image when preparation is set.
Run `adore --profile <name> config validate`, then the explicit host/model checks
as appropriate before resuming pickup. Image/tool availability, preparation,
model access and full job readiness retain their separate evidence.

For native execution, choose **Installed on the server** in **Runs in** (or set
`execution.backend = "local"` in the server profile) and follow
[Local execution](Local_Execution.md). Specialized profiles use existing server
TOML enrollment.

## Environment changes and recovery

ADORE has no image definition or build feature. The routes
`/api/v1/projects/{name}/image-build`, `/image-build/export`,
`/image-build/operations`, `/image-build/operations/{id}` and
`/image-build/operations/{id}/cancel` answer HTTP 404, and the web worker runs
no image builds. Environment setting edits and staging return HTTP 400
`environment_managed_externally`, except `execution.backend`, `container.runtime`,
`container.image` and the `local.*` account keys, which use the reviewed
configuration flow.

A pending candidate with an image-build binding, or for an operator-owned
environment key, could only be staged by an earlier build. Viewing or applying it
returns HTTP 503 `pending_config_corrupt`. An administrator removes it with
**Discard change** in Settings, or through
`DELETE /api/v1/projects/{name}/config/pending`.

## Images for adaptive agent installation

Rebuild the current base image to include sudo before enabling `container.system_packages`. No existing image is rebuilt automatically. Compatible images supply root-owned OS Python, id, sudo/visudo and a supported package manager; the default user remains non-root. Agents may then install missing system packages directly, with egress configured separately. See [Agent dependency installation](Agent_Dependency_Installation.md).
