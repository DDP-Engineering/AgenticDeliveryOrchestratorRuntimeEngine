<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project executor images

In a stopped container project, open **Settings → Isolated environment →
Project executor image**. The administrator owns the executable Dockerfile.
The ADORE server builds with its configured runtime and account; the browser
does not run Docker, download packages or supply host files.

1. **Existing image** retains the existing image setting and its normal review.
2. **Define image** opens the legal ADORE base template. Edit or paste UTF-8
   Dockerfile text, or load a text file. Keep the canonical FROM and finish with
   USER adore. Use RUN for explicit system-tool installation.
3. Review tool checks beside the source, one shell-free command per line.
   Initial checks come from the profile; the saved definition is the explicit
   authority for the checks proposed by Use image.
4. Save the definition, then explicitly choose **Build and verify**.
   Saving does not launch a build. Unsaved edits disable building/selection.
5. Follow queued, runtime inspection, building and verification phases and the
   bounded output. **Use image** prepares the existing configuration review.
   Review the immutable image ID and active/proposed tool checks, then apply.
   Pickup must stay stopped and work must be idle. Failed, stale, interrupted
   or uncertain results cannot be selected.

System tools belong in the image. Per-worktree libraries belong in the reviewed
project preparation recipe; see [Container preparation](Container_Preparation.md).
Image verification checks the installed selected executor and declared tool
commands. Model access and full run readiness require their separate explicit
checks. Local profiles show the server-account tooling responsibility notice
and have no build or automatic host-preparation actions. Developers can read
saved source/evidence but cannot save, build, cancel or apply.

## Context, network and bounds

Advanced details show policy, runtime/account, managed tag, immutable base/result
IDs and execution-context checksum. The initial context contains only Dockerfile;
COPY/ADD, repository snapshots, extra stages, ARG, ONBUILD, syntax-front-end
downloads and RUN mount/network overrides are unsupported. Syntax checks describe
the supported input format; they do not sandbox administrator commands.
No checkout, home directory, .env, provider/forge credentials, sockets, build
secrets, SSH forwarding or privileged options enter the context/build container.

The base must already be installed in the selected runtime. The execution
Dockerfile pins its actual image ID, while the original source remains exportable.
Downloads default to no network. Selecting the default build network explicitly
allows Dockerfile package downloads; it does not change executor/preparation
egress. No base pull, package inference or builder installation is automatic.

Definitions accept 64 KiB UTF-8/1024 lines, up to 32 checks of 512 bytes each,
30–1800 seconds (default 600), and 512–4096 MiB per build step (default 1024).
Build flags enforce one CPU, the selected memory/swap limit and intermediate
container removal. All build/verification commands share the operation deadline;
individual inspection/check commands are capped at 30 seconds. Exact owned
cleanup gets a separate bounded 30-second window, with native process drain
also bounded by the shared controller. Retained output is a redacted 64 KiB tail,
plus at most 64 KiB each for the active native stdout/stderr.

Linux-container Docker uses the explicit legacy builder with memory/CPU capability
checks. Unsupported/removed legacy builders fail with evidence. Podman requires
Linux cgroup v2 CPU/memory controllers. Plain docker/podman executables and
WSL -- docker/podman or WSL -d DISTRIBUTION -- docker/podman are accepted.
Remote/TLS credentialed Docker contexts and arbitrary runtime wrappers/options
are unsupported. Runtime clients use isolated authentication/configuration homes;
Podman retains the service account's rootless data/runtime locations without
copying authentication. WSL runs through a cleared Linux environment and
translated owned paths.

Native Windows build clients use owned Jobs. Linux requires a service-account
delegated cgroup v2 root with cgroup.kill in ADORE_BUILD_CGROUP_ROOT. This is a
worker environment setting, independent of native local executor profile settings.
Missing ownership/capability support fails closed.

## Evidence and recovery

Each profile owns image-build/draft.json and UUID operation directories outside
the checkout. Strict schema-1 records bind source/configuration revisions,
project/runtime/account, context, base/result IDs and verified checks.
Managed tags are unique adore-built-PROJECT_ID:OPERATION_ID values; existing
tags are not overwritten. Export Dockerfile retains the saved original source.
Advanced Export build evidence downloads only the saved definition, public
operation evidence and current redacted output.

At most ten operations and 160 owned native command launch records per operation
are retained. JSON records are capped at 512 KiB; source/context and output are
independently bounded. Repeated review requests also consume this finite native
evidence allowance. New work rejects exhausted retention. Images are retained;
ADORE never pushes, prunes or deletes them. The operator owns image disk capacity
and offline archival/reconciliation of terminal profile evidence before another
build. Do not remove evidence for an active or uncertain operation.

Cancel before start performs no runtime commands. Active cancellation signals
only the owned native process scope. A stopped client alone cannot prove the
daemon's build cleanup: active cancel/timeout or failed process/resource control
is uncertain, retains evidence, and cannot become a usable image. Restart
reconciles verified native leases and exact verification-container identities,
marks interrupted requests terminally, and never repeats a build. An identity
mismatch forbids cleanup; the operator must inspect the original runtime and
owned resources. No PID-only kill or inventory-wide cleanup is used.

Selection stages one immutable image ID and the definition's tool checks through
the existing candidate workflow. Stage and apply recheck current source/config,
runtime/base/result identities and labels. Recipe image conflicts are rejected by
the shared preparation plan. Review a consistent profile/recipe selection
separately; ADORE does not edit target-repository YAML.

## Deferred acceptance checklist

Offline proof uses injected runtime output and an isolated browser API/worker.
The following remain explicitly deferred from issue #22:

- Full offline Python suite, full frontend helper/browser suites and aggregate
  AEGIS strict --run, with the final #23 integrated candidate.
- #23: existing image, GUI-built image with preparation, and native local mode
  through one complete isolated AEGIS job, bounded recovery and candidate-bound
  approval/draft publication, preserving the human merge boundary.
- Windows native Jobs, Linux delegated cgroups, Docker legacy, rootless Podman
  and supported WSL wrappers: actual CPU/memory/network limits, installed base
  identity, tool verification, cancellation/timeout/worker crash and daemon
  reconciliation. Confirm unrelated images/containers remain intact.
- Platform link/junction ownership rejection and service-account/private-home
  permissions, registry/proxy credential absence and log redaction.
- Explicit model access and real forge account/issue/Git/draft-only permissions,
  using operator-authorized credentials and cost/network limits.

No live runtime, package download, provider request or forge publication is part
of the offline implementation verification.
