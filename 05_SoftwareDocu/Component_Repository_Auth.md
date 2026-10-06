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
GH_TOKEN/GH_ENTERPRISE_TOKEN and GH_HOST select GitHub; GITLAB_TOKEN/GITLAB_HOST
plus GLAB_CONFIG_DIR select GitLab; tea uses XDG_CONFIG_HOME with a temporary
JSON-as-YAML config and configured login. Token never enters argv or executor env.

## 8. Usage

Project Summary → Connect repository → server/token → Verify and connect →
Check host prerequisites. Reconnect to rotate or repair drifted credentials.
Revoke old tokens on the forge. No OAuth app setup or forge passwords.

## 9. Validation And Tests

`tests/test_repository_connection.py` verifies three-provider connection, trust
failures, role/CSRF/idle locks, secret storage, export/audit exclusion, engine/probe
bindings, redaction, corruption and scope drift. `web/e2e/jobs.spec.ts` proves
memory-only secret UI and honest scoped result. Real token permissions and Git
clone/push are human live acceptance, not offline proof.
