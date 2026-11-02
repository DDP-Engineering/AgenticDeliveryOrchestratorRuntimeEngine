<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Doctor

## Routing

Use this page for read-only readiness checks during assisted setup: host tools,
container runtime, forge CLI authentication, executor availability and the
target repository's AEGIS payload. Start at `04_Software/adore/doctor.py`;
focused proof is `04_Software/tests/test_doctor.py`. The AEGIS version range
itself is declared in `aegis-client.md`; guided setup flows belong to
`wizard.md`.

## Purpose and boundaries

`04_Software/adore/doctor.py` tells an operator whether the host and the target
repository are suitable before delivery begins. It changes nothing on the
workstation or in the repository; all subprocess work flows through an injected
`CommandRunner`.

## Public interface

`detect_aegis()` returns an `AegisStatus`, `aegis_version_supported()` answers
for one `aegis --version` text, and `guidance_for()` returns the per-platform
remedy text, which names the supported range (`AEGIS_SUPPORTED_TEXT`) and
schema 1. `detect_executor()` probes Pi (`doctor.PI`) with `pi --version`.

## Invariants

- `detect_aegis()` requires `.agentic/aegis.py`, accepts only an `aegis`
  release at 0.15.0 or later within major 0, read from the client's
  `SUPPORTED_MAJOR` and `MINIMUM_SERIES`, then runs `status --all --json` and
  requires schema `1`, a status envelope, a task list and an empty
  unreadable-task list.
- A missing Python or payload, a nonzero exit, malformed JSON, or a wrong
  shape, version or schema returns a not-ready `AegisStatus` with bounded
  diagnostic text instead of an exception that pretends the target is
  compatible.
- GitLab and GitHub guidance names the active/default CLI host as the routing
  authority; Gitea routes through the selected `tea` login.

## Key behaviors

- `REQ-FUNC-69bfe896` - only an AEGIS 0.15.0-or-later, major-0, schema-1
  payload is ready.
- `REQ-FUNC-8a2e5904` - injected host, forge, runtime and executor readiness
  reporting.

## Files

- `04_Software/adore/doctor.py` - readiness probes and guidance.
- `04_Software/tests/test_doctor.py` - readiness, absent payloads, invalid
  responses, unsupported version or schema, and guidance.
