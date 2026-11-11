<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Docker build bundle component

## 1. Purpose

`adore/build_bundle.py` packages an administrator's reviewed executor image
definition for use with Docker Compose on another host.

## 3. Implementation overview

The reader validates the configured manifest reference and resolves it in the
project's local Git object database at a full commit ID. It compares the
manifest image with the saved image tag. Git tree metadata proves the paths
are regular blobs and establishes file and aggregate bounds before archive
reads. The reader checks bytes against the recorded blob IDs. It rejects
transformed files, links, unsafe paths and recognizable credential files.
The original TOML is included verbatim after the API checks for inline
credentials. Git runs with time limits and lazy fetching disabled.

## 5. Inputs and outputs

The registration is an optional `container.build_definition` setting.
The JSON manifest contains `schema` (1), `image`, `dockerfile`, and a bounded
`files` list including the Dockerfile. Paths are relative to the repository.
The ZIP contains `config.toml`, `compose.yaml`, `BUILD.txt` and the declared
blobs under `context/`. The exporter performs no Docker operations.

## 9. Validation and tests

`test_web_config_raw.py` covers authorization, exact bytes, declared binary
inputs and rejected definitions through the HTTP contract with a fake Git
runner. `e2e/portable.spec.ts` covers the optional ZIP selection and download.
