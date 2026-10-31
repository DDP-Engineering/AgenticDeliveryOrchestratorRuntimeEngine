<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Repository Authentication Component

## 1. Purpose

Connect and verify a project repository account without changing shared host logins.

## 2. Responsibilities

Validates server/token input, verifies account and exact repository read access,
publishes protected scoped records, binds CLI execution and redacts token output.
The web API owns authorization/locks/audit; Git transport credentials remain external.

## 3. Implementation Overview

`verify_connection` runs fixed user and repository API GET commands with eight
second limits. Gitea additionally requires the final HTTP status to be 2xx.
`save_connection` invalidates readiness and atomically publishes a 0600 record.
`project_runner` fails closed on schema, identity or provider/repo/login drift.
`credential_runner` uses per-command temporary config/environment without global
process mutation. Missing scoped record preserves external CLI auth.

## 4. Dependencies

Standard library, Config platform fields, existing ForgeError/CommandRunner;
tea >= 0.15, gh or glab. No additional package dependency.

## 5. Inputs And Outputs

Admin supplies server origin, token and optional HTTP acknowledgement. The
internal verified record includes the token; `connection_view` is the sole
secret-free response projection. New credentials apply to subsequent engine
construction and explicit host checks.

## 6. Data Contracts

Secret record schema 1 has exactly schema, project_id, provider, repository, login,
server, token, account. Identity matches profile.json, provider/repo/login match
Config. Strict duplicate-free JSON, bounded size, 0600 POSIX permissions; symlinks
and malformed/mismatched records reject with RepositoryAuthError. HTTP requires
acknowledgement; GitHub HTTPS only. Server subpaths are excluded. Files and backups
require service-account access restrictions; Windows requires profile ACLs.

## 7. Workflow Integration

GUI → web API authorization/idle lock → verification → uncertain audit → secret
publication → confirmed audit. Readiness serializes with credential replacement.
Worker from_config and explicit web host checks use the same scoped runner.
Failed Gitea readiness probes write a value-free `forge_auth_failure` warning:
CLI exit code, timeout flag, final HTTP status, identity validity, output lengths
and whether a named login was selected. Exact known missing-login errors map to
closed reason codes (`no-logins`, `login-missing`, `other`). Config-file presence
under the runner's XDG, local/roaming application-data and legacy home locations
is recorded as present/absent/unset/unavailable without reading credential files.
These host locations do not inspect an internally scoped runner's temporary config.
Response bodies, headers, filesystem paths, account/login
values and credentials are excluded; the portable launcher retains the warning
in its existing bounded log. The boolean readiness contract is unchanged.
GH_TOKEN/GH_ENTERPRISE_TOKEN and GH_HOST select GitHub; GITLAB_TOKEN/GITLAB_HOST
plus GLAB_CONFIG_DIR select GitLab; tea uses XDG_CONFIG_HOME with a temporary
JSON-as-YAML config and configured login. Token never enters argv or executor env.

## 8. Usage

Project Summary → Connect repository → server/token → Verify and connect →
Check host prerequisites. Reconnect to rotate or repair drifted credentials.
Revoke old tokens on the forge. No OAuth app setup or forge passwords.
The connection dialog has one dismissal button, **Cancel**, beside **Verify and
connect**. Cancel and Escape clear the draft token without submitting credentials.

## 9. Validation And Tests

`tests/test_repository_connection.py` verifies three-provider connection, trust
failures, role/CSRF/idle locks, secret storage, export/audit exclusion, engine/probe
bindings, redaction, corruption and scope drift. `web/e2e/jobs.spec.ts` proves
memory-only secret UI and honest scoped result. Real token permissions and Git
clone/push are human live acceptance, not offline proof.

## Private read for image redaction

load_connection returns the existing strictly validated protected record or
None only when absent. project_runner reuses this public read before creating
the same scoped forge runner. ImageBuildService reads its token in memory only
to reject/redact source/output; build clients never receive it. Corrupt records
fail closed. Existing scoped auth tests and image secret boundaries cover the seam.

## Portable external Gitea discovery

`adore/gitea_auth.py` owns `discover_tea_logins`, safe `TeaLogin` metadata,
`portable_tea_runner` and value-free `GiteaAuthError` codes. Discovery uses
injected CLI calls within eight seconds, bounded strict duplicate-free JSON,
and presence checks in standard Windows/Linux account roots. Explicit XDG and
the first populated CLI configuration retain authority. Token/unknown metadata
fields are discarded; no secret files are read or copied.

`project_runner` prioritizes strict protected records. Only missing Gitea records
use portable external discovery. The wrapper keeps successful calls unchanged
and recovers only exact pre-HTTP missing-login errors, choosing an explicit name,
one default or the sole login and retrying once with a copied child environment.
Ambiguous/malformed metadata or an absent explicit name fails closed; HTTP and
scoped-credential failures preserve the original authority. Other commands and
providers pass through. Existing engine construction already uses project_runner.

Web new/transfer probes wrap external auth. Saved-project probes use the project
runner directly; missing auth becomes an ordinary failed forge_auth check. Ticket
reads return the closed auth code for localized Connect repository instructions.
Enrollment uses the same metadata, omitting ambiguous host suggestions. Four-locale
UI/help names the connection fields and verification actions. Focused proof:
`test_gitea_auth.py`, `test_repository_connection.py`, `test_repository_source.py`,
and frontend error/help tests.
