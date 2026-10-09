<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project executor images

Executor environments are prepared by the server administrator outside ADORE.
For a container project, **Project → Settings → Agent and model** displays the effective
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
server. The canonical base tag must contain Python, sh and the selected executor;
a base for another executor must be adapted or replaced externally.

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

Verify the selected executor and every project tool as the image's non-root user.
Use controlled versioned tags or immutable image IDs for reproducible deployment.
Adding `executor/Dockerfile` to the repository does not trigger a build in ADORE.
The suggested location is an operator convention, not a watched file contract.

## Select the prepared image

Pause pickup and ensure there are no active jobs. Update the existing server
profile at the path displayed to the administrator in Settings → Agent and model:

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
Add the selected executor/project checks and keep any configured recipe's image
consistent: its validated plan owns the effective image when preparation is set.
Run `adore --profile <name> config validate`, then the explicit host/model checks
as appropriate before resuming pickup. Image/tool availability, preparation,
model access and full job readiness retain their separate evidence.

For native execution, externally select `execution.backend = "local"` and follow
[Local execution](Local_Execution.md). Guided creation uses the standard container
profile; specialized profiles use existing server TOML enrollment.

## Historical evidence and recovery

Existing image-build records remain in each profile. Authorized scoped read,
export, status and cancel routes retain evidence and owned interrupted cleanup.
Definition saves and build submissions return HTTP 410
`environment_managed_externally`. Environment setting edits/staging/application
return HTTP 400 with the same code; existing dedicated AI endpoint edits remain
available. Retained queued image-build requests fail without launching a runtime.
Old pending environment candidates remain readable and discardable; they cannot
be applied. Existing profiles, installed images and database schema are retained.
