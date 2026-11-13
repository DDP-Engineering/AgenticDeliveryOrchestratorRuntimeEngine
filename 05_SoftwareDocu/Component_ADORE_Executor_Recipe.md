<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE project executor recipe

## 1. Purpose

Provide reviewed, exportable build inputs for the ADORE project's executor.
The synthetic recipe reconstructs tooling observed on DCP rather than requiring
its previously built local image. It is an operator-owned environment asset;
the orchestrator's generic build-export implementation is unchanged.

## 2. Responsibilities

The Dockerfile installs the agent toolchain and Chromium dependencies in the
same image used for execution and testing. Runtime credentials, network policy,
per-worktree dependency installation and job state remain owned by ADORE and
the agent. Registering this recipe does not build an image or resume a job.

## 3. Implementation Overview

Source files live under `02_Tools/containers/adore-executor/`. The Dockerfile
reconstructs the executor base from Ubuntu 22.04, then installs Playwright and
Chromium. Its adjacent `Dockerfile.dockerignore` admits only reviewed build
inputs, including ADORE's existing Pi guard and subscription helper. No host
credentials, worktrees, node_modules or caches enter the build context.

The default non-root user has UID/GID 1000; build arguments allow changing
them. Node's archive checksum and the agent, uv, Python and Playwright versions
are explicit. Distribution packages and transitive npm dependencies remain
resolved at build time, so the result is not a byte-identical image backup.
The Chromium, headless-shell and FFmpeg archives use the revisions reported by
the pinned Playwright release. Curl retrieves them over HTTPS with bounded
timeouts and retries, avoiding the Node HTTPS timeout observed on DCP.

## 4. Dependencies

Docker Engine with amd64 Linux image support, Docker Compose for an exported
bundle, and build-time access to upstream image and package sources are required.
The source inputs include `04_Software/docker/pi/adore-guard.ts`,
`04_Software/docker/pi/adore-chatgpt.mjs` and `LICENSE.txt`.

## 5. Inputs And Outputs

`build.json` follows the existing build-bundle schema 1 contract: an exact image
tag, a repository-relative Dockerfile and explicit regular-file inputs. The
repository root is the build context. The manifest and inputs must exist at
the immutable Git commit named by `container.build_definition` in the enrolled
project clone. A source-only Git snapshot is valid if retained by a local ref.

The existing export endpoint supplies saved TOML, Compose, build instructions
and the declared context. A Docker build produces the configured image tag;
validation uses a separate scratch tag to protect existing execution images.

## 9. Validation And Tests

This is environment setup; no automated product tests are added or run for it.
Manually build the declared context, verify the non-root agent and Python/Node
versions, and launch Chromium against an in-memory page without network access.
Check that export returns the exact registered files and that source registration
preserves the project's image, unfinished job state and pending configuration
edits. The recipe's README describes operator commands and reconstruction limits.
