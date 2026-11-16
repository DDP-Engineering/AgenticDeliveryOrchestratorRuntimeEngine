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

## Files

- `04_Software/adore/branding.py` - shared constants for product, paths,
  container, deployment, and package identity.
- `05_SoftwareDocu/Component_Branding.md` - component-level reference.

## Current contract

Built-in identity defaults come from `adore/branding.py`. Current UI/API and resource-operation tests exercise their public effects; there is no standalone test duplicating the constant table.
