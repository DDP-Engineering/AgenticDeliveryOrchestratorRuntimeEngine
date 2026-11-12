<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Doctor

## Routing

For read-only host readiness and CLI authentication, start at
`04_Software/adore/doctor.py` and `04_Software/tests/test_doctor.py`.
Portable tea metadata and protected project credentials belong to
repository-auth.md; web permission and persisted evidence belong to web-interface.md.

## Purpose and boundaries

Provides injectable host-tool, container, executor, forge authentication and
AEGIS-payload probes. Callers own UI, configuration persistence and authorization.
All command execution uses CommandRunner; tests fake external CLIs.

## Public interface

`detect_aegis()` returns an `AegisStatus`, `aegis_version_supported()` answers
for one `aegis --version` text, and `guidance_for()` returns the per-platform
remedy text, which names the supported range (`AEGIS_SUPPORTED_TEXT`) and
schema 1. `detect_executor()` probes Pi (`doctor.PI`) with `pi --version`.
`discover_container_commands()` returns successful native and Windows WSL
Docker and Podman version probes. `inventory_runtime_argv()` resolves the
standard read-only inventory command form into a fixed argument list.

## Invariants

No workstation mutation. Gitea authentication requires successful HTTP and
strict bounded duplicate-free JSON with a valid account login; invalid output
never authenticates or echoes raw diagnostics. Caller-owned credential authority
is retained with external_auth=False. GitHub/GitLab use active/default CLI auth.
Present-payload AEGIS readiness requires the supported client range, schema 1
and readable journals. Absent payload runs no command and reports
`No AEGIS found: tickets run in the direct workflow`. AegisStatus.ok remains
false for absence (usable AEGIS, not overall readiness); unusable present
entries, including dangling links/directories, are probed rather than bypassed.
`detect_aegis`, `aegis_version_supported` and `guidance_for` share the client
version floor; malformed version/schema/status and nonzero commands fail readiness.
Both AEGIS probes use the keyword-only `aegis_python` executable, default `python`,
in the target cwd. Version exit 127 names that executable and skips status.

## Change map

| Request | Entry | Focused proof |
| --- | --- | --- |
| Authentication | auth_status | test_doctor.py and test_gitea_auth.py |
| AEGIS compatibility | detect_aegis | test_doctor.py |
| Tool guidance | detect_all and guidance_for | test_doctor.py |
| Web runtime discovery | discover_container_commands and inventory_runtime_argv | test_executor_environment_choice.py |

## Key behaviors

- REQ-FUNC-69bfe896: supported present AEGIS/schema-1 payload readiness.
- REQ-FUNC-6e20aea3 / REQ-FUNC-e08ce8af: absence is direct-workflow
  information; remediation explains optional AEGIS and the client-declared
  installed contract, never mandatory installation or automatic payload edits.
  Web enrollment's AEGIS gate remains separate.
- REQ-FUNC-f47c612e / REQ-FUNC-a1603c88: configured interpreter for version/status.
- REQ-FUNC-7081a87e: unavailable-interpreter diagnostic.
- REQ-FUNC-fe08018c / REQ-FUNC-d04bc2e0: preserved version/JSON failure diagnostics.
- REQ-FUNC-8a2e5904: injected host/forge/runtime/executor reporting.
- REQ-FUNC-cacfa8b2: portable current-account Gitea discovery and verified identity.
- REQ-UX-163a1c99: safe Connect repository recovery steps.
- REQ-FUNC-72081f3b and REQ-SEC-548f27ce: fixed, bounded runtime probes with validated distro names.

## Files

- 04_Software/adore/doctor.py — typed probes and guidance.
- 04_Software/adore/gitea_auth.py — portable tea metadata policy.
- 04_Software/tests/test_doctor.py — offline readiness contracts.
- 04_Software/tests/test_gitea_auth.py — portable discovery integration.
- 05_SoftwareDocu/Component_Doctor.md — component documentation.

Native executor detection calls the managed verifier and reports Node/Pi prerequisites.
