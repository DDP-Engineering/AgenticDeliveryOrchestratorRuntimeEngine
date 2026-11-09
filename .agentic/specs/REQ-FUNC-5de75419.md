<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Scoped repository connection

POST /api/v1/projects/{immutable-id}/repository-connection: {server: origin URL, token: 1..4096 visible ASCII characters, allow_http: boolean}. Admin+CSRF, valid nonarchived idle project and config lock. Return {project_id, provider, server, repository, account}; no credentials. Invalid input 422; active work or changed snapshot 409; verification failure 400; corrupt stored credentials/storage failure 503. No endpoint exposes tokens.

Origin URL accepts HTTPS; HTTP only with explicit allow_http=true; GitHub HTTPS only. URL credentials, paths other than root, queries/fragments, malformed ports reject. Fixed CLI commands verify account and exact repository JSON identity. Nonzero/timeout, missing/non-2xx tea HTTP status, malformed JSON or repository mismatch reject. No write/clone/push/full-job permission claim.

repository-auth.json schema1: schema, project_id, provider, repository, login, server, token, account. Strict closed schema, bounded bytes, atomic 0600 file. profile.json immutable identity and current provider/repo/login must match; corrupt/stale record rejects without fallback. GH_TOKEN/GH_ENTERPRISE_TOKEN + GH_HOST; GITLAB_TOKEN + GITLAB_HOST; tea temporary isolated XDG_CONFIG_HOME with fixed JSON-as-YAML config. Other commands receive no injected credential; returned forge streams redact token. No shared config/process-global mutation. Engine and readiness share runner binding. Replacement requires idle conductor lock and invalidates old readiness.

Browser secret is memory-only, cleared immediately on submit/cancel/unmount. Pending results cannot appear on another project. Existing four locales. User creates a token on the forge. Form explains read verification, required issue/draft permissions and separate Git transport access. Server backups contain credentials and require service-account access restrictions.
