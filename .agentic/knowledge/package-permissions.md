<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Package permissions

## Routing

Use for direct agent system-package sudo authority inside a container. Start with adore/package_permissions.py and ContainerManager.authorize_system_packages; verify tests/test_system_packages.py. Egress/lifecycle belongs to isolation.md, policy drift to preparation.md and orchestrator.md, GUI authorization to web-interface.md.

## Purpose and boundaries

Supply fixed container-only permission code. The agent chooses, installs and adapts dependencies; ADORE configures authority and never executes package installations on the host.

## Public interface

PACKAGE_AUTHORIZATION_SCRIPT runs with the exact numeric UID through root-owned OS Python inside the owned container. PACKAGE_AUTHORIZATION_ACK is the only accepted confirmation. staged_auth_redactions reads only the bounded approved auth snapshot and returns in-memory redaction values, rejecting duplicates, excessive depth/size and malformed JSON. Manager errors are typed IsolationError.

## Invariants

Opt-in defaults false. Non-root agent identity, root-owned sudoers and bounded subprocess checks are required. Package scripts have effective container-root authority. Network policy, forge credentials and host lifecycle remain separately governed.

## Key behaviors

- REQ-FUNC-c405688e: direct noninteractive package-manager sudo, with explicit incompatible-image failure.
- REQ-SEC-c5d56d9f: proxy preservation and independent egress; host exposure overrides are refused in the managed mode.

## Files

- 04_Software/adore/package_permissions.py: fixed runtime authorization code.
- 04_Software/adore/isolation.py: measured UID and bounded runtime transport.
- 04_Software/tests/test_system_packages.py: positive and trust-boundary tests.
- 05_SoftwareDocu/Component_Package_Permissions.md: implementation documentation.
