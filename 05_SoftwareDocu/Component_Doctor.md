<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Doctor Component

## 1. Purpose

`adore/doctor.py` provides offline-testable environment and target-payload
probes for assisted setup.

## 2. AEGIS Probe

`detect_aegis` requires `.agentic/aegis.py`, runs `--version`, accepts only
a supported `aegis` version, then runs `status --all --json` and requires schema 1, command
`status`, a task list and an empty unreadable list. Missing Python, nonzero
exit, malformed JSON, wrong shape/version/schema, or unreadable tasks return a
not-ready `AegisStatus` with bounded detail.

## 3. Dependencies and Integration

All probes use injected `CommandRunner`; unit tests never contact external
systems. The wizard prints the same guidance. Other probes cover Git,
Docker/Podman/WSL, forge CLI/auth and Pi availability (`detect_executor` runs
`pi --version`; Pi is needed on the host only for a local run, since the
executor image pins its own). GitLab/GitHub
guidance states the runtime routing contract explicitly: ADORE uses the
platform CLI's active/default authenticated host, which must be the intended
corporate instance. Gitea continues to route through its selected tea login.

## 4. Validation and Tests

`tests/test_doctor.py` covers valid version/schema-1 detection, missing payload,
malformed/blocked status, wrong version/schema, and guidance.

## 5. Portable Gitea authentication

`auth_status("gitea")` uses the shared portable tea runner and a bounded account
API request. Authentication requires HTTP success and a strict, bounded JSON
identity with a valid login; exit status alone is insufficient. Missing CLI is
reported separately. Failed/corrupt identities return value-free Connect
repository guidance. `external_auth=False` lets a caller-owned scoped runner
retain authority; web readiness uses this mode after binding project credentials.
Other forge probes retain their existing routing. Focused proof: doctor and
Gitea-auth tests, including missing/ambiguous metadata and protected scopes.
