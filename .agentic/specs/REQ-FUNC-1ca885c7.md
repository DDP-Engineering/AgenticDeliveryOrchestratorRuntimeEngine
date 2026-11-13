<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Complete project ZIP import

## Current source and API

ZIP is the existing export format, not a new stored schema. Require config.toml,
recipe.json schema 1, compose.yaml and BUILD.txt. Use the bounded existing recipe
parser; inspect in memory without extraction or execution. Require every local
image dependency in the ZIP; declared registry prerequisites remain external.
Parse the exported Compose JSON-subset YAML after comment lines are removed and
require it to equal the generated composition. Preserve exact TOML and file modes.

Admin+CSRF POST /api/v1/projects/import/bundle-preview accepts source (strict base64,
18 MiB decoded maximum), optional name/display_name/description. It reuses existing
TOML import identity, path, state and ownership inspection. Return its ordinary
preview fields plus bundle_revision; overall revision binds exact archive digest,
TOML inspection revision and observed image-binding revisions. No sources are saved.
POST /api/v1/projects/import/bundle requires explicit reviewed identity and revision
plus the exact source. Existing TOML routes stay unchanged. All fields are closed.

A container config must select the manifest's canonical root image. Preparation
selection uses the existing bounded read-only local Git resolver to obtain its
effective image; a normal import executes no commands. No Docker/Podman, network,
forge, model, archive-provided scripts, image build or automatic monitoring.

## Publication and source ownership

RecipeStore snapshots all embedded binding revisions and checks them again while
holding its catalog lock. Existing root definitions must equal the complete
imported snapshot; a conflicting root is refused, never implicitly replaced.
Identical roots are reused. Existing supplemental base associations are preserved,
as with current recipe attachment; the new root retains its own embedded sources.
The automatic canonical base is not replaced by a supplemental association.

Publish immutable sources and only previously unregistered bindings, then invoke
the existing paused project publisher under the catalog lock. The inner publisher
rechecks original TOML/state/ownership under its enrollment and conductor locks.
If it fails normally, it removes its profile and restores its previous pause state;
the source transaction removes only its exact new bindings. Existing associations
and source objects are never deleted. Unreferenced immutable objects may remain.
A rollback storage failure produces a typed service error requiring operator
inspection; process/power interruption retains the existing fail-closed incomplete
profile semantics, without recovery migrations or automatic data repair.
Lock order: recipe catalog -> enrollment -> candidate conductor. Current recipe
writes use profile-edit -> catalog; enrollment never takes existing profile-edit locks.

## Simple browser interaction

Keep the current Projects popup with a TOML/ZIP file selector and Import/Cancel.
ZIP file bytes are retained only in memory, sent as base64 and re-read before
confirmation, exactly as TOML is re-read now. Selecting another file invalidates
old responses. Invalid/stale/changed input keeps confirmation disabled. No recipe
upload/save or Docker build options appear. Project import is paused/unverified;
server locations and credentials still follow existing validation and host setup.
