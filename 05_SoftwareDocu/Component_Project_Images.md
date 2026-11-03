<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project images and external preparation

## 1. Purpose

Executor image definition and build are operator actions outside ADORE; backend,
container runtime and image selection are administrator choices at enrollment and in
reviewed Settings edits. Executor configuration explains both.

## 2. Responsibilities

ADORE owns no image definition or build. The retired image-build subsystem (the
Dockerfile draft store, the build runner and its web routes) is removed.
`ContainerBackend` owns actual run image identity and reviewed preparation recipe
authority. The executor environment lists the server's installed images and the
administrator chooses one.

## 3. Implementation Overview

`app.py` has no image-build routes: `GET/PUT /api/v1/projects/{name}/image-build`,
`/image-build/export`, `/image-build/operations`, `/image-build/operations/{id}`
and `/image-build/operations/{id}/cancel` answer 404. The worker does not handle
`image-build` operations or recover running builds. There are no migrations:
evidence left by earlier builds is not read.

## 4. Dependencies

Existing ProfileStore, WebStore and the executor environment image listing.
Actual image preparation uses the operator's runtime.

## 5. Inputs And Outputs

`execution.backend`, `container.runtime`, `container.image` and the local
account/home/path/cgroup keys are chosen through the reviewed pending flow.
Other environment configuration direct/stage/apply requests receive HTTP400
`environment_managed_externally`; other executor/model edits remain supported.
A pending candidate carrying an `image_build` binding, or a candidate for an
operator-owned environment key, could only be staged by an earlier build: it is
503 `pending_config_corrupt` on view and on apply, and an administrator can still
discard it through `DELETE /api/v1/projects/{name}/config/pending`.

## 6. Data Contracts

`ConfigEdit` has no `image_build_id` staging field, and the pending review shows
no image-build binding. Container images remain externally managed; the
configured `container.image` names an installed image.

## 7. Workflow Integration

External administrator → repository executor/Dockerfile → build/check on server →
existing profile config.toml → existing runtime/readiness. Admin GUI reads the real
profile path; Dev sees only operator contact guidance. Recipe plans determine the
effective image when configured. Local profiles omit container instructions.

## 8. Usage

See [Project executor images](../01_Documentation/Project_Executor_Images.md).

## 9. Validation And Tests

`test_executor_environment_choice.py`: installed image listing, chosen
environment keys through review, other environment keys staying external, and
`test_pending_image_build_binding_is_corrupt_but_discardable`.
`test_web_pending_config.py`:
`test_pending_candidate_for_an_external_key_is_corrupt_but_discardable`.
`web/e2e/images.spec.ts`: localized disclosure/local suppression/Admin
path/mobile presentation.
