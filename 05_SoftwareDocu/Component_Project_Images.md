<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project executor image definition and build

## 1. Purpose

image_build.py owns explicit profile Dockerfile artifacts and durable bounded
image evidence; image_build_runner.py controls the owned runtime client.
ProjectImage.tsx embeds the administrator flow inside Settings Environment.
Its existing-image panel shows the active image and embeds SettingsList's normal
single-setting editor/review with focus. Backend and image controls lead the
environment group; other settings use a collapsed advanced disclosure. Three
four-locale steps explain system-tool RUN lines, successful checks and explicit
save/build/use. Source/check columns align on wide screens and stack on narrow
screens; downloads sits beside checks, bounds in a disclosure and build evidence
in a separate panel with actionable failures and automatically loaded output.
Textareas show 16/six resizable lines and preserve unsaved text across choices.
The compiler example is read-only guidance with no configuration side effects.

## 2. Responsibilities

ImageBuildStore owns strict bounded source/check/policy and operation records,
revisions, cancellation and redacted output. ImageBuildService owns unique
queued snapshots, runtime capability/base identity, minimal context, build,
non-root/image/label/tool verification, identity-safe cleanup and review.
The existing WebStore/CommandWorker owns queue serialization, actor rechecks,
conductor lock, audit completion and startup reconciliation. Existing config
pending/apply owns reviewed application; preparation owns recipe image conflicts.

## 3. Implementation Overview

prepare captures source/config and project/runtime/account identity without
commands. run consumes only queued records, inspects capabilities/base, pins
FROM in a Dockerfile-only context, builds a unique labeled tag and verifies
the immutable image in an unmounted credential-free temporary container.
Creation receipts persist before checks; ContainerBackend bound commands and
expected resource IDs protect execution/removal. Current identity is rechecked
before verified completion and again by review. recover never repeats work.

## 4. Dependencies

Existing config/profile/state/web queue, ContainerBackend/ContainerManager,
LocalProcessController/NativeScopes, protected credential readers for redaction,
and standard-library JSON/hash/argv/path/thread/time operations. Docker legacy
or Podman with checked Linux resource capabilities; optional strict WSL prefix.
No new core dependency.

ImageBuildRunner resolves only the first native executable against the supplied
controlled PATH before entering the controller's ownership barrier. The controller
returns authoritative exit/timeout plus captured files; the adapter rechecks owned
stdout/stderr files, 64 KiB bounds and strict UTF-8, redacts them and returns the
actual streams. Missing executables and missing/linked/oversized/invalid output
fail closed. Native execution and process-control contracts remain shared.

## 5. Inputs And Outputs

ImageDefinition accepts dockerfile, checks, current revision, network, timeout
and memory only. ImageRequest binds saved source/config plus idempotency key.
Reads expose source/template/profile tool-check defaults and closed operation
summaries. Status adds bounded live output. HTTP never runs a build.

## 6. Data Contracts

Schema 1 closed records live under the profile image-build directory.
Draft revision is canonical content SHA-256. Operation UUID/project bind the
managed tag, config/source, runtime/account, pinned base/result IDs, context SHA,
create receipt, verified checks and phase. queued/inspecting/building/verifying
are active; verified/failed/cancelled/uncertain/interrupted are terminal.
Only complete current verified evidence can stage container.image with the
definition checks. Pending image_build binds exact evidence and candidate checks;
corrupt/missing/stale/foreign evidence fails closed through ImageBuildError.

## 7. Workflow Integration

GET/PUT project image-build, GET export, POST operations, GET operation UUID and
POST operation/cancel use existing project scope/CSRF/admin rules. Save/enqueue
require stopped idle managed state and no pending config/operations. Worker
rechecks authorization/state and holds the conductor lock. Use image passes
optional image_build_id through existing config/pending; apply reinspects
identities and the shared exact-Git preparation plan before replacement.
Existing images and native local ownership remain compatible.

## 8. Usage

See Project_Executor_Images.md for GUI steps, policy, supported runtime grammar,
ADORE_BUILD_CGROUP_ROOT and operator retention/recovery. Network defaults none;
the installed base never pulls. Checks and time/resource limits are explicit.
Linux rootless data/runtime locations remain bound while client auth homes are
isolated. Native scope control reuses Windows Jobs/Linux delegated cgroups.

## 9. Validation And Tests

tests/test_image_build.py proves source/policy/retention/corruption, runtime
prefixes/resources/environment, pinned verification, failure/cancel/restart
and replacement cleanup refusal using injected commands. test_web_image_build.py
proves authorization/worker/idempotency, exact pending/apply, stale evidence
and recipe conflict. Frontend imageBuild.test.mjs proves closed response binding;
images.spec.ts proves the real offline API/worker GUI and role/local boundaries.

## 10. Limitations And Future Work

Administrator Dockerfiles are executable input, with supported-format checks.
COPY/ADD/context snapshots and credentialed remote/build contexts are unsupported.
Active daemon cancellation cannot be inferred from native client termination;
uncertain evidence requires operator reconciliation. Native metadata is capped
at 160 launches/operation, ten retained operations; source/records/output are
bounded. Images persist under operator disk ownership. Live platform/runtime
and #23/full-suite acceptance remain deferred as listed in the operator guide.

Podman identity pins checked hostname and graphRoot/runRoot/graph driver, excluding
mutable inventory counts. Strict raw OCI and sha256-prefixed IDs normalize for
image evidence; exact backend-inspected resource representation owns controls.
