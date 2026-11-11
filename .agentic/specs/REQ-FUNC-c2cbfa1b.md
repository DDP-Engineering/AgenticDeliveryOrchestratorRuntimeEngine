<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable executor recipes

## Scope and ownership

The accepted task is generic source retention and complete project export. It
does not build images in the application, inspect arbitrary host directories,
reverse-engineer images, modify execution policy, restore jobs or migrate stores.
Existing TOML project import remains unchanged: an exported bundle supplies
`config.toml` for that flow and the same ZIP can attach its executor definition.

## Source contract

An attachment is a UTF-8 Dockerfile (context name `Dockerfile`) or a ZIP.
A context-only ZIP has a root `Dockerfile`; every regular source file is part
of its explicitly selected context. A portable ZIP has root `recipe.json`:

```json
{
  "schema": 1,
  "image": "sample-executor:1",
  "definitions": [
    {
      "image": "sample-executor:1",
      "context": "context",
      "dockerfile": "Dockerfile",
      "files": ["Dockerfile", "setup.sh"],
      "build_args": {},
      "external_images": []
    }
  ]
}
```

`context` is a portable relative directory, or `.` for a context-only input.
Dockerfile and file names are relative to that context. Optional `target`
selects a named stage; build arguments are non-secret scalars. Definitions
name unique tagged images. Source files are read as bounded regular bytes,
never extracted to caller-selected paths. Limits reuse the existing export
contract: 128 unique files, 4 MiB each, 16 MiB combined, 18 MiB ZIP, plus
bounded metadata (64 KiB) and 32 image definitions/dependency nodes.
Traversal, links, encrypted archives, duplicate/case-colliding paths, unknown
schema/fields, recognizable credentials and private keys are refused.

Dockerfile FROM and image-backed COPY/RUN mount references establish the image
dependency graph. Stage aliases and scratch are internal. Global ARG defaults
and supplied non-secret build arguments resolve image variables; unsupported
or unresolved syntax fails closed. Declared source files cover local COPY/ADD
inputs, including context-backed RUN bind mounts. Stage-local ARG/ENV scope and
ENV precedence select source paths; an unknown base-image variable used there
fails closed. Public official base names and explicit registry references are
external prerequisites; other external images must be declared explicitly.
Unresolved local image references require an attached, embedded or built-in
recipe; they are not guessed from image history. Cycles are refused.

Git-manifest sources remain available through the existing immutable-reference
contract; they become a validated in-memory definition. Additional managed base
definitions can complete that image's graph. No Git lookup occurs when a managed
attachment supplies the selected image's sources. The standard executor base
definition and guard/helper inputs ship with the application wheel.

## Persistence and concurrency

Managed sources live under `ADORE_HOME/executor-recipes/`: immutable canonical
ZIP objects named by SHA-256 and one current-schema JSON binding per exact image
tag. A binding contains only schema 1, image and object digest. A catalog lock
and atomic file replacement protect writes. Replacement requires the previously
observed binding digest (null for no binding). Invalid/corrupt stored data raises
a typed error naming what to delete; it is never repaired silently. Invalid bindings
name their binding; missing/corrupt source objects and object collisions name the
entire `executor-recipes` catalog so removal clears both objects and associations.
The dialog explains that this explicit reset removes retained recipes for all
projects, preserving their configurations, credentials and jobs.
Embedded bases receive reusable bindings only when no association exists; existing
bindings and the bundled base default are never replaced implicitly. A retained
root keeps its embedded sources pinned when another image binding changes.
Source resolution uses preparation's effective image and Docker's implicit latest
tag; digest-only selected images require an explicit tag for this build contract.
Recipe writes do not modify any project configuration, pending change or job.

## API and compact UI

Admin-only GET `/api/v1/projects/{name}/executor-recipe` returns the selected
image, source kind, available/missing status, missing local images and current
binding digest. POST `.../preview` checks a bounded base64 attachment without
writes. PUT attaches the exact previewed bytes with project config revision and
observed binding digest. Mutation authorization/CSRF precede source reads/writes.
The target is the selected image or a currently missing dependency of it.
Responses expose metadata/errors, never source text or credentials.

The existing export dialog loads this status, defaults container exports to
include the complete definition and offers an explicit TOML-only choice.
Attachment/replacement and adding a missing local base stay in this dialog;
file selection validates automatically, Save retains the definition, and
Export downloads. No recipe hashes, Git manifests or paths must be typed in
the normal interface. Native projects keep standalone TOML export.

## Complete export

The ZIP contains exact saved `config.toml`, canonical `recipe.json`, declared
contexts, `compose.yaml` and concise build instructions. Compose maps local
image dependencies through named `additional_contexts: service:<name>` so
BuildKit orders dependent builds. No runtime containers, volumes, credentials,
worktrees or image binaries are included. Public image/package registries and
separately supplied registry authentication remain build prerequisites.
An unavailable local base rejects complete export and names missing images;
it never produces a partial bundle. Raw TOML remains explicitly available.

## Failure contracts

401/403 and CSRF follow existing API policy. Invalid uploads or unsupported
Dockerfile constructs use 400; missing local bases/cycles use typed 400 errors
for complete export. Concurrent binding/config changes use 409. Corrupt retained
recipe data uses 503 with a deletion recovery path. Missing definitions are an
ordinary GET status, not proof of a corrupt project or invalid execution setup.
