<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Executor recipes

## 1. Purpose

Retain reviewed executor image definitions independently of projects and running
jobs, and close every declared local-image dependency for complete configuration
export. Actual image building stays external. The core uses standard-library
Python and no live runtime/forge/model commands.

## 2. Responsibilities

`recipe_sources.py` validates selected Dockerfile/ZIP bytes, source paths,
current recipe metadata and supported Dockerfile image/context references. It
serializes deterministic source archives and explicit Compose build graphs.
`executor_recipes.py` owns exact-image associations, immutable source objects,
built-in source lookup and bounded dependency resolution. `build_bundle.py`
retains its injectable immutable Git reader and integrates complete export.

The web API enforces administrator/CSRF/project/revision boundaries. The existing
RawConfiguration dialog owns attachment selection, automatic validation, Save,
replacement, missing-base recovery and the default complete-export choice.
No recipe operation modifies configuration, pending settings, credentials,
worktrees, images or job state, or requires pickup to be stopped.

## 3. Implementation Overview

The selected root comes from a managed image association, an optional pinned Git
source, or ADORE's bundled standard-base sources, in that order. Preparation uses
the same effective image selection as readiness; implicit tags normalize to
`:latest`. Named output tags are required; immutable image digests and image IDs
cannot promise an identical rebuild from source instructions alone.

Sources include FROM and image-backed COPY/RUN-mount dependencies. Stage aliases
and scratch remain internal; supported ARG defaults and explicit non-secret
build arguments resolve variable image names. Declared COPY/ADD context sources
must exist, including default-context RUN bind sources. Stage ARG/ENV scope,
ENV precedence and inherited stage values select context inputs; unknown values
used as paths fail closed. Unsupported syntax, cycles and conflicting sources
are typed errors.
Explicit registries, known standard public bases and declared external images
remain external prerequisites. Other bases resolve through embedded, retained
or bundled source definitions; missing images never produce a partial export.

Embedded sources remain pinned within their reviewed snapshot. New supplemental
bindings make previously unregistered embedded bases reusable independently;
existing bindings and the application-owned default are not implicitly replaced.
Reading such a binding selects only that image and its reachable embedded bases.
Source objects may be shared; a wrong association names its binding for recovery,
while a missing/corrupt source object or object collision names the whole
`executor-recipes` catalog. An object-only deletion would leave dangling bindings.
An explicit catalog reset removes retained recipes for all projects; configuration,
credentials and job state remain separate. The application performs no deletion.

## 4. Dependencies

Internal dependencies are Config, StateStore locking, ProfileStore home,
read-only preparation normalization, immutable Git input reading and shared web
authorization. The wheel includes the canonical executor base Dockerfile and Pi
guard/subscription helper and project license through hatch force-include; source checkouts read the
same files from the existing Docker context. No environment script source is
introduced inside the application package.

## 5. Inputs And Outputs

Inputs are a UTF-8 Dockerfile or ZIP, exact selected image, current config revision
and observed association digest. Outputs are availability metadata, validated
source snapshots and complete source ZIPs. Standalone raw TOML remains available.
Complete ZIPs contain exact saved TOML, current `recipe.json`, Compose, build
instructions and declared source contexts. Binaries, external credentials,
runtime mounts and agent-installed container contents are excluded.

## 6. Data Contracts

`ADORE_HOME/executor-recipes/objects/<sha256>.zip` holds immutable canonical
source bytes. `images/<image-sha256>.json` contains exactly schema 1, image and
object digest. File reads are bounded; schema, image, digest, source bytes and
controlled path/link types are validated before use. There are no migrations or
fallback readers. A corrupt or unsupported record is refused with the relative
path an operator deletes to start fresh; it is never rewritten automatically.

A catalog lock serializes writers. The selected image association changes by
atomic replacement only when the observed digest still matches. New source
objects are retained before association; unused objects after an interrupted
write do not change an existing definition. Supplemental bindings are created
only when absent, before the selected association is published; a write failure
attempts removal of only this operation's unchanged new supplemental links.

The current ZIP schema and limits are specified in
[Project executor images](../01_Documentation/Project_Executor_Images.md).
Paths, links, duplicate/case-colliding names, encrypted or corrupt archives,
recognizable credential paths, private keys and literal secret defaults are
refused. This is structural validation of declared sources, not execution or
proof that packages are reachable. It cannot identify every arbitrary secret;
operators select and review build inputs before attachment/building.

## 7. Workflow Integration

Admin GET `/api/v1/projects/{name}/executor-recipe` reads availability. Admin/CSRF
POST `.../preview` validates a bounded base64 source entirely in memory. PUT
retains it under config/image revision guards. The target must be the selected
image or a currently missing local base. Save records an image-source audit event.
GET raw configuration with `include_build=true` uses the same resolver.
401/403 precede source access; invalid sources return 400, stale associations or
config return 409, and corrupt retained data returns 503 with explicit recovery.
Every initial/final configuration read is bounded and refuses links/missing or
oversized files with config_corrupt; changed valid source bytes return stale_config_revision.
Catalog failures remain confined to recipe controls, not the Settings read or
Overview. Docker, Podman and WSL projects use the same source contract.

## 9. Validation And Tests

Offline `test_executor_recipes.py` proves input trust boundaries, deterministic
round trips, image graphs, current schemas, explicit source precedence and
bounded failure recovery. `test_web_executor_recipes.py` proves authorization,
CSRF, image/config concurrency and byte-preservation of a real parked run,
pending settings and credentials. Existing raw API tests prove exact Git bytes
and original TOML. Browser journeys cover attachment, complete/standalone choice,
mobile widths, focus and four locales. Product wheel assets are also inspected
using a temporary isolated wheel build; no deployment-script tests are added.
