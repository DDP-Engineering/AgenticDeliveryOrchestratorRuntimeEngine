# Synthetic ADORE project executor

This recipe supports development of ADORE itself. It is outside standard
delivery; the image-archive tool exports only executor-base.


This optional development image extends the common `adore-executor-base:1.0.0` image and adds Playwright 1.63.0, Chromium 153.0.8010.12 (revision 1243), FFmpeg revision 1011 and browser system dependencies. Build the common base first, or pass `--build-arg BASE_IMAGE=<prepared-base-tag>`. Normal jobs can use the common base directly and let Pi install project dependencies with environment administration enabled. The specialized image is not required for Electron or browser jobs and is not included in standard delivery archives.

This is a functional reconstruction, not a byte-identical image backup. Ubuntu
packages and transitive npm dependencies are resolved when building. Packages
installed later by an agent, project worktrees, Python environments, credentials,
and job state are not copied. Build access to Ubuntu, Node, npm, uv/Python,
Playwright package sources is required. Runtime network access
remains an independent ADORE setting.

The build context is the repository root. From that directory:

```sh
docker build --file 02_Tools/build/executor_images/adore/Dockerfile \
  --tag adore-executor-adore:synthetic-check .
docker run --rm --network none adore-executor-adore:synthetic-check python --version
docker run --rm --network none adore-executor-adore:synthetic-check pi --version
```

The default non-root account is `adore`, UID/GID 1000. Supply `USER_UID` and
`USER_GID` build arguments when the execution server uses another account.
Repository dependencies remain the agent's responsibility in its job container.
The recipe does not embed a shared machine identity: if tests need a machine-id,
prepare a unique identity in that job's container, never copy the server's ID.

`build.json` declares every exported input and the new
`adore-executor-adore:pi1.5.2-pw1.63.0` tag. Build and select this image explicitly;
existing image tags and active job containers remain untouched. Register it as
`02_Tools/build/executor_images/adore/build.json@<full-source-commit>` in
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
