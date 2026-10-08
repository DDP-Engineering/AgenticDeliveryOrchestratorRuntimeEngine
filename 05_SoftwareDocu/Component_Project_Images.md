<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project image evidence and external preparation

## 1. Purpose

Preserve historical project image evidence and owned interruption recovery while
executor environment definition, build and selection are operator actions outside
ADORE. Executor configuration explains that external workflow.

## 2. Responsibilities

`ImageBuildStore` retains bounded strict project-owned source/operation records.
`ImageBuildService` retains readers, verification contracts and interrupted owned
cleanup. Its internal pipeline remains available to existing artifact tests; web
routes and the worker do not expose build execution. `ContainerBackend` continues
to own actual run image identity and reviewed preparation recipe authority.

## 3. Implementation Overview

`app.py` authenticates and scopes historical reads/exports/status/cancellation.
Definition PUT and operation POST return 410 `environment_managed_externally`
before artifact or runtime changes. The worker fails retained queued builds and
marks their evidence rejected; it never starts a build. Previously running owned
scopes retain existing recovery/cleanup checks. No history/image/schema migration
or resource deletion accompanies this change.

## 4. Dependencies

Existing ProfileStore, WebStore, ImageBuildStore, ImageBuildService and native
owned process controllers. Existing Docker/Podman clients are used only by owned
interruption recovery here. Actual image preparation uses the operator's runtime.

## 5. Inputs And Outputs

Scoped historical image-build GET/export/operation-status and cancellation
contracts remain. Authorized definition save/build creation receive HTTP410.
Environment configuration direct/stage/apply requests receive HTTP400
`environment_managed_externally`; other executor/model edits remain supported.
Old pending candidates can be read and discarded but not applied.

## 6. Data Contracts

Existing strict artifact schemas, UUID ownership, bounded source/output,
secret redaction and uncertain cleanup fail-closed semantics remain. Configuration
schema, database action enum and installed images retain compatibility.

## 7. Workflow Integration

External administrator → repository executor/Dockerfile → build/check on server →
existing profile config.toml → existing runtime/readiness. Admin GUI reads the real
profile path; Dev sees only operator contact guidance. Recipe plans determine the
effective image when configured. Local profiles omit container instructions.

## 8. Usage

See [Project executor images](../01_Documentation/Project_Executor_Images.md).

## 9. Validation And Tests

`tests/test_web_image_build.py`: guidance metadata, membership/role/CSRF scoping,
mutation refusal with unchanged bytes/artifacts/runtime, queued rejection and
non-environment edits. `test_web_pending_config.py`: strict legacy read/discard
and apply refusal. `test_image_build.py` retains artifact/native identity/recovery
trust-boundary coverage. `web/e2e/images.spec.ts`: localized disclosure/local
suppression/Admin path/mobile presentation.
