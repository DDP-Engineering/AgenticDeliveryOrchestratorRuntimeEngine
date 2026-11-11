<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Docker build bundle component

## 1. Purpose

`adore/build_bundle.py` reads immutable Git build inputs and exports saved
configuration with complete executor image sources for Docker Compose on another
host. Generic retained-source and graph ownership is documented in
[Executor recipes](Component_Executor_Recipes.md).

## 3. Implementation overview

The optional Git reader validates the configured manifest reference and resolves it in the
project's local Git object database at a full commit ID. It compares the
manifest image with the saved image tag. Git tree metadata proves the paths
are regular blobs and establishes file and aggregate bounds before archive
reads. The reader checks bytes against the recorded blob IDs. It rejects
transformed files, links, unsafe paths and recognizable credential files.
`read_git_recipe` returns a validated in-memory definition with the immutable
source revision. `export_build_bundle` resolves managed, Git and bundled sources,
then packages the closed local-image dependency graph. The original TOML is
included verbatim after the API checks for inline credentials. Git runs with
time limits and lazy fetching disabled. No container runtime is executed.

## 5. Inputs and outputs

The Git registration is an optional `container.build_definition` setting.
The JSON manifest contains `schema` (1), `image`, `dockerfile`, and a bounded
`files` list including the Dockerfile. Paths are relative to the repository.
The ZIP contains `config.toml`, `recipe.json`, `compose.yaml`, `BUILD.txt`, root
sources under `context/` and declared local bases under separate contexts.
Compose service contexts establish build ordering while Dockerfile bytes and
executable permissions stay intact. Unavailable local bases fail closed.

## 9. Validation and tests

`test_web_config_raw.py` covers authorization, exact bytes, declared binary
inputs and rejected definitions through the HTTP contract with a fake Git
runner. `test_executor_recipes.py` covers retained inputs, complete image chains,
ARG/stage references, unsafe archives and corrupt records.
`test_web_executor_recipes.py` covers scoped retention, CSRF, concurrency and
job/config preservation. `e2e/portable.spec.ts` covers the compact attachment,
default complete export, standalone choice, responsive controls and localization.
