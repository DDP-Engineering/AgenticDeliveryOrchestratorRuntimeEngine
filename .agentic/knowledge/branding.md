<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Branding

## Purpose

Defines the product identity, package paths, deterministic resource names, and
the host/container mount names that form ADORE's cross-platform vocabulary.
All other components import these constants instead of rebuilding names.

## Public contract

`adore/branding.py` provides the ADORE identifier/version, path constants,
resource naming helpers, and the canonical `/adore/io` and `/adore/worktree`
mounts. It is intentionally dependency-light: mount constants originate here
so executor and AEGIS transport do not create an import cycle through isolation.

## Key behaviors

- Names derived resources predictably from a bounded run identity, making
  recovery and cleanup able to prove ownership.
- Keeps host/container paths consistent across Docker, Podman, and WSL.
- Separates product/version constants from persisted ADORE state schema and
  the independent AEGIS schema-1 protocol.

## Requirement coverage

- `REQ-FUNC-308299d1` - shared product, resource, and mount identity contract.

## Files

- `04_Software/adore/branding.py` - shared constants for product, paths,
  container, deployment, and package identity.
- `05_SoftwareDocu/Component_Branding.md` - component-level reference.
- `04_Software/tests/test_branding.py` - naming and mount regression tests.
