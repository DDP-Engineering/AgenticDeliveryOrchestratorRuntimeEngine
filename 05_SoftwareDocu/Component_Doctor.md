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

When `.agentic/aegis.py` is absent, `detect_aegis` runs no AEGIS command and
reports `No AEGIS found: tickets run in the direct workflow`. `AegisStatus.ok`
remains false: it means usable AEGIS, not general project readiness. The CLI
wizard renders absence as INFO; web enrollment readiness is unchanged.

For a present payload, `detect_aegis` runs `--version`, accepts only
a supported `aegis` version, then runs `status --all --json` and requires schema 1, command
`status`, a task list and an empty unreadable list. Missing Python, nonzero
exit, malformed JSON, wrong shape/version/schema, or unreadable tasks return a
not-ready `AegisStatus` with bounded detail.

The keyword-only `aegis_python` input defaults to `"python"`. Both probe
commands use that executable unchanged, with the target repository as their
working directory. A version-probe exit 127 names this interpreter in the
unavailable diagnostic and skips status. The wizard supplies the validated
profile's `workflow.aegis_python`; no interpreter discovery or shell parsing
is performed. An unusable present entry (including a directory or dangling
symlink) is not announced as absent/direct. Guidance describes optional AEGIS,
the supported installed-payload contract and refusal of broken payloads; it does
not require every repository to install AEGIS. ADORE never installs or edits it.

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

`discover_container_commands` runs bounded Docker and Podman version probes
on the host and up to eight Windows WSL distributions. It filters distro names
and returns command strings only for successful probes. `inventory_runtime_argv`
admits only fixed native and standard WSL prefixes for the web image inventory.
`test_executor_environment_choice.py` covers the resulting API contracts offline.

`tests/test_doctor.py` covers valid version/schema-1 detection, missing payload,
malformed/blocked status, wrong version/schema, and guidance. Parameterized
cases prove exact argv/cwd for python and python3, unavailable-interpreter
reporting, preserved bounded version/malformed-JSON diagnostics, exact
informational absence text, unusable present-entry refusal and optional-governance
guidance on Windows and Linux.

## 5. Portable Gitea authentication

`auth_status("gitea")` uses the shared portable tea runner and a bounded account
API request. Authentication requires HTTP success and a strict, bounded JSON
identity with a valid login; exit status alone is insufficient. Missing CLI is
reported separately. Failed/corrupt identities return value-free Connect
repository guidance. `external_auth=False` lets a caller-owned scoped runner
retain authority; web readiness uses this mode after binding project credentials.
Other forge probes retain their existing routing. Focused proof: doctor and
Gitea-auth tests, including missing/ambiguous metadata and protected scopes.

## Managed Pi readiness

The native executor probe verifies the server's Node and the pinned Pi CLI
through the managed installation verifier. A missing or invalid prerequisite
produces safe operator guidance. It never invokes a global Pi or calls a model.
