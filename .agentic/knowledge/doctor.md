<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Doctor

## Purpose

`04_Software/adore/doctor.py` performs read-only, injectable readiness checks
used by assisted setup. It tells an operator whether host tools, a container
runtime, forge CLI authentication, executor availability, and the target's
AEGIS payload are suitable before delivery begins.

## AEGIS contract

`detect_aegis()` requires `.agentic/aegis.py`, accepts only `aegis 0.5.x`,
runs `status --all --json`, and requires schema `1`, a status envelope, task
list, and unreadable-task list. Missing Python/payload, nonzero exit, malformed
JSON, wrong shape/version/schema, or unreadable tasks returns a not-ready
`AegisStatus` with bounded diagnostic text rather than an exception that
pretends the target is compatible.

## Requirement coverage

- `REQ-FUNC-69bfe896` - AEGIS 0.5/schema-1 readiness acceptance only.
- `REQ-FUNC-8a2e5904` - injected host, forge, runtime, and executor readiness reporting.

## Boundaries and verification

All subprocess work flows through an injected `CommandRunner`, making tests
offline and preventing doctor from changing the workstation or repository.
GitLab/GitHub guidance reminds operators that the active/default CLI host is
the routing authority; Gitea routes through the selected `tea` login.
`04_Software/tests/test_doctor.py` covers readiness, absent payloads, invalid
responses, unsupported version/schema cases, and guidance.
