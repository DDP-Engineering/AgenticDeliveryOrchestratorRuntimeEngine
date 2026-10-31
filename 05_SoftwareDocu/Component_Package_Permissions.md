<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Package permissions

## 1. Purpose

Authorize adaptive system-package installation by the job agent inside an opted-in container. Package choice, execution and interpretation stay with the coding executor.

## 2. Responsibilities

`adore/package_permissions.py` contains fixed authorization code and its exact success acknowledgement. `ContainerManager.authorize_system_packages` measures a non-root numeric UID and issues a bounded root exec using the image’s OS Python. `ContainerBackend` first checks the pinned identity and addresses the immutable container ID. The code configures root-owned sudoers and tests noninteractive elevation with a version-only package-manager invocation; it performs no installation.

## 3. Dependencies and contracts

Trusted Linux image with root-owned `/usr/bin/python3` and `/usr/bin/id`, sudo, visudo, safe `/etc/sudoers.d` and an installed supported package manager. Supported paths are documented in Agent_Dependency_Installation.md. Package scripts have effective container-root authority; sudo is not an isolation boundary. Current normal user ownership is retained for ordinary code/library writes. The root bootstrap clears its subprocess environment and accepts only a measured numeric UID. Administrative process errors, timeouts, unsafe directories or missing exact acknowledgement raise IsolationError.

## 4. Workflow integration

Strict boolean `container.system_packages` defaults false. Enabled jobs bind policy/container/image in the existing execution plan and resource record before granting authority. Egress is independent; proxy variables survive agent sudo. Host-oriented runtime overrides and native backend elevation are rejected. Stopped same-container jobs preserve the filesystem; drift/resource loss fails closed. Model/host checks never install packages or grant this permission.

## 5. Evidence and verification

Gate output is available to the agent. Enabled launches retain API-key and staged-subscription-credential-redacted stdout/stderr at 64 KiB per stream after completion, including immutable archives; complete original usage is streamed before truncation so cost/token accounting remains intact. This is a retention bound, not a live filesystem quota. Offline public tests in test_system_packages.py cover config, root authorization transport, negative process output, independent modes, same-resource retry/drift, reviewed web settings and gate retention. Live Docker/Podman package installation is separate acceptance.
