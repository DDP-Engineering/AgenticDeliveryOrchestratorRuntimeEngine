<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project executor images and retained recipes

## Routing

Start at `adore/web/app.py` recipe/raw-config routes for project export;
`adore/executor_recipes.py` owns source retention/resolution and
`adore/recipe_sources.py` validates input and creates the portable ZIP.
Focused proof: `tests/test_executor_recipes.py`, `test_web_executor_recipes.py`,
`test_web_config_raw.py` and `web/e2e/portable.spec.ts`. Actual runtime behavior
belongs to execution.md; preparation profiles to preparation.md; native runs
to local-execution.md.

## Purpose and boundaries

ADORE retains reviewed image-source snapshots shared by exact image tag and
exports saved configuration with the complete declared local image graph.
The administrator owns actual image builds and deployment; preparation/readiness
own effective runtime selection. Source registration preserves configuration,
pending edits, credentials, job state and execution policy.

## Public interface

Admin GET `/api/v1/projects/{name}/executor-recipe` returns availability, source,
missing local images and binding/config revisions. Admin+CSRF POST `.../preview`
validates Dockerfile/ZIP bytes without writes; PUT retains them with config
revision and observed binding digest. GET `config/raw?download=true&include_build=true`
exports complete sources; standalone TOML remains available.
The compact RawConfiguration export dialog handles automatic validation, explicit
Save recipe, missing bases and replacement. Normal Settings hides the advanced
Git build-definition field. The old image-build routes answer 404.
Runtime/image/account choices retain reviewed configuration saves, with detected
native/WSL runtime suggestions and manual entry.

## Invariants

- Current-schema image bindings and immutable SHA-256 source objects live only in
  `ADORE_HOME/executor-recipes`; corruption names data for operator deletion and
  never silently falls back. Bad bindings name their own file; missing/corrupt
  shared objects name the whole catalog, since object-only deletion leaves dangling
  bindings. The operator explicitly resets recipes for all projects; other stores
  are preserved. No migration or automatic repair.
- Source files are bounded and validated without extraction/execution. Links,
  traversal, duplicate paths, private keys and unsupported Dockerfile semantics
  are refused before retention. COPY/ADD and context-backed RUN bind sources must
  exist under actual stage ARG/ENV scope; unknown source variables are refused.
  Local cycles/missing definitions reject export.
- Embedded sources are pinned. Supplemental image bindings never implicitly
  overwrite existing reviewed associations or the standard builtin base.
- Root binding is published last under the catalog lock with digest CAS.
  Project revision/identity and existing Admin/CSRF checks precede source writes.
- Public registry/package access is a separate build prerequisite. Managed source
  lookup does not execute Docker, forge commands or agents; optional Git sources
  use the existing injected immutable blob reader.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Source syntax/ZIP/Compose | recipe_sources.py | test_executor_recipes.py |
| Shared sources/effective image/closure | executor_recipes.py | test_executor_recipes.py |
| Authorization/CAS/config preservation | web/app.py | test_web_executor_recipes.py |
| Existing Git source export | build_bundle.py | test_web_config_raw.py |
| Compact export/attachment dialog | RawConfiguration.tsx | portable.spec.ts |
| Runtime selection/external build ownership | app.py/ContainerRuntimePicker | test_executor_environment_choice.py/images.spec.ts |

## Key behaviors

- REQ-FUNC-e5c8a96f: shared immutable recipes with explicit replacement.
- REQ-FUNC-c2cbfa1b / REQ-REL-aa0c1685: complete source ZIP or named missing bases.
- REQ-FUNC-4404d38b: canonical standard base sources ship in the wheel automatically.
- REQ-SEC-409d6c82 / REQ-DATA-65ebe5f6: bounded input and refused corrupt storage.
- REQ-REL-0f5a1e11 / REQ-SEC-c3a134af: CAS and administrator/CSRF authority.
- REQ-UX-3534628b / REQ-NFR-5e0f55d9: compact dialog, preserved project/job stores.
- Existing environment mutation guards and pending_config_corrupt refusal remain;
  an invalid image_build candidate may be discarded through the pending endpoint.

## Files

- `04_Software/adore/{executor_recipes,recipe_sources,build_bundle}.py`: source contracts.
- `04_Software/adore/web/app.py`: authorization, revision-bound recipe/export routes.
- `04_Software/web/src/{RawConfiguration,App,ContainerRuntimePicker}.tsx`: user controls.
- `04_Software/tests/test_executor_recipes.py`, `test_web_executor_recipes.py`,
  `test_web_config_raw.py`, `test_executor_environment_choice.py`: offline contracts.
- `04_Software/web/e2e/{portable,images}.spec.ts`: browser contracts.
- `01_Documentation/Project_Executor_Images.md` and
  `05_SoftwareDocu/Component_Executor_Recipes.md`: user/component guidance.
