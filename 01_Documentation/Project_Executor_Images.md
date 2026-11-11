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

## Retain an image definition in ADORE

Use **Project → Settings → Technical details → Image definition** to register
sources when preparing an external executor image. Export is a separate one-click
save of the complete configuration and image-source ZIP. ADORE includes the standard executor
base definition automatically. For an externally prepared image, choose its
Dockerfile or source ZIP under **Definition file**; selection validates it, and
**Save recipe** retains the source. A Dockerfile alone is sufficient only when
all its local build inputs are already contained in that file. Otherwise supply
a ZIP with a root `Dockerfile` and the files it copies. This workflow works with
Docker, Podman and WSL runtime commands and does not execute a build.

If a local base is missing, the same dialog identifies that image and accepts
its definition. **Change definition** replaces the selected image's retained
source. The definition is shared by projects choosing the same image tag.
Use distinct tags for images with different definitions, including across
different runtime contexts. Named tags are required for rebuilding; an image ID
or immutable image digest cannot be recreated exactly from source instructions.

Image recipes live independently under `ADORE_HOME/executor-recipes/`. Saving
them changes no project TOML, pending settings, authentication or job state and
requires no job restart. Retained sources take priority over the optional Git
source described below. A prepared project uses its preparation plan's effective
image. Plain names follow Docker's implicit `:latest` tag.

### Complete source ZIPs and local bases

A complete export supplies `recipe.json`, exact saved `config.toml`, Compose,
build instructions and all declared contexts. The same ZIP can attach a recipe
on another server. A source ZIP can declare several related image definitions:

```json
{
  "schema": 1,
  "image": "project-executor:1",
  "definitions": [
    {
      "image": "project-executor:1",
      "context": "project",
      "dockerfile": "Dockerfile",
      "files": ["Dockerfile", "setup.sh"],
      "build_args": {},
      "external_images": []
    },
    {
      "image": "project-base:1",
      "context": "base",
      "dockerfile": "Dockerfile",
      "files": ["Dockerfile"]
    }
  ]
}
```

Here `project/Dockerfile` starts from `project-base:1`; `base/Dockerfile` supplies
that local base. All listed files are relative to their context; context paths
are relative to the ZIP root. Optional `build_args` contains non-secret strings,
and `target` selects a named Dockerfile stage. An `external_images` list explicitly
declares other registry-provided bases, for example `company/base:1`. Standard
Docker Hub base names and explicit registry references are external build
prerequisites. Use a fully qualified registry name for other external images,
or declare them in `external_images`, rather than inventing a local base recipe.

Embedded base definitions remain pinned to that reviewed source snapshot. ADORE
makes previously unregistered embedded bases reusable by other projects, while
preserving existing image associations and its bundled default. A standalone
image update does not rewrite another image's explicitly embedded snapshot.

Validation bounds the ZIP to 18 MiB, source files to 128 entries and 16 MiB
combined (4 MiB per file), and the image graph to 32 definitions. It refuses
traversal, links, duplicate/case-colliding paths, recognizable credential paths,
private-key material, secret argument defaults, missing COPY/ADD sources,
unresolved arguments, unsupported syntax and image cycles. Heredoc COPY/ADD,
alternate Dockerfile escape directives and ONBUILD instructions are unsupported.
These checks establish the declared build inputs; they do not execute package
installation or prove that remote packages are available. Review sources before
building, and keep credentials outside the ZIP. Agent-installed packages and
running container/job contents are not retained by this definition export.

An unavailable local base prevents a partial complete export; the dialog names
the missing image. Clearing **Include Docker build files** explicitly exports
the standalone TOML. Corrupt saved data is refused with the relative object or
binding path an operator deletes to start fresh; it is never repaired silently.

## Optional immutable Git build source

Commit the Dockerfile and a manifest in the project repository. The image must
match the exact tag saved in ADORE. The Dockerfile and every input are paths
relative to the repository root, which becomes the exported build context.
For example, commit `executor/build.json` with this content.

```json
{
  "schema": 1,
  "image": "my-project-executor:1.0.0",
  "dockerfile": "executor/Dockerfile",
  "files": ["executor/Dockerfile", "executor/setup.sh"]
}
```

Review the commit and ensure it exists in the project clone on the ADORE
server. Set `container.build_definition` in the server's project TOML to
`executor/build.json@<full-commit-id>`. The normal interface uses file attachment
instead of asking for this Git reference. Choose **Export raw configuration**
and keep **Include Docker build files** selected. The ZIP contains the same
saved TOML, recipe metadata, Compose, build instructions and all resolved local
base definitions. The Git manifest can declare up to 128
regular files, 4 MiB per file and 16 MiB combined. List each file explicitly
using portable paths with letters, digits, dots, underscores and hyphens.
Include any required ignore files. Keep credentials out of the listed files
and configure registry or package authentication separately.

Extract the ZIP on a Docker host, arrange access to the Dockerfile's base
images and package sources, then run `docker compose build` in the extracted
directory. Docker Engine with BuildKit and Compose v2.17 or later builds local
bases in dependency order using named service contexts. It tags the image
selected by the project's effective configuration. Import `config.toml`
separately after reviewing its server paths, then attach this same ZIP to retain
the definitions. Registry access and build credentials are configured separately.

## Build and verify on the execution server

For the ADORE project itself, a synthetic recipe and export manifest are available
under `02_Tools/containers/adore-executor/`. This reconstructs the DCP executor's
observed Pi, Node, Python and Playwright tooling from Ubuntu, without requiring
the original local image. See its `README.md` for versions, build context,
registration and verification. It reconstructs the toolchain; it is not an image
backup and does not include agent-installed packages, credentials or job state.

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

ADORE retains reviewed source definitions but does not build images. The routes
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

Default-context `RUN --mount=type=bind` sources (`source` or `src`) must be
included in the selected build files. Stage-backed mounts use their declared
stage/image dependency. Context variables follow stage ARG/ENV scope and ENV
precedence; an unknown base-image variable used as a source path is refused
rather than guessed.

If retained recipe data is corrupt, ADORE names what to delete to start fresh.
A bad image association names its record. A missing or corrupt shared source
object names `ADORE_HOME/executor-recipes`: deleting that catalog removes saved
image definitions for all projects, while configurations, credentials and jobs
stay intact. Nothing is deleted automatically; attach the original source again
after the explicit reset.
