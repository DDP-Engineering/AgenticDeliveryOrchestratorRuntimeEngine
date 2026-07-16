<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Branding Contract (`adore/branding.py`)

## 1. Purpose

Provide one authoritative Python contract for the ADORE product name, acronym,
package, configuration home, state/log defaults, container paths, image and
cache names, deployment identities, and runtime-package prefix.

## 2. Responsibilities

- Export immutable constants used by configuration, identity, profiles,
  isolation, process logging, CLI presentation, deployment, and packaging.
- Keep the hard-cut ADORE namespace explicit: no pre-1.0 aliases or fallbacks.
- Give the release-consistency check a compact set of canonical values to
  compare with shell scripts, package metadata, and delivery artifacts.

## 3. Dependencies And Behavior

The component is standard-library only and has no runtime dependencies or
side effects. Configurable per-project agent names and slugs remain owned by
the identity/config components; branding constants define only built-in
defaults and fixed product-controlled resources.

## 4. Validation

`tests/test_branding.py` asserts every public constant and the absence of
legacy aliases. Release validation additionally compares these values with
package, deployment, Docker, and delivery surfaces.
