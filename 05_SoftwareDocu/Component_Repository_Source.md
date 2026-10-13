<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Repository Source (`adore/web/repository_source.py`)

## 1. Purpose

Let an administrator enroll a project from its repository URL: validate the address,
detect forge details and clone the repository into ADORE's own folder at creation.

## 2. Responsibilities

- `parse_repository_url`: accept https, http and ssh (including `user@host:path`)
  addresses without passwords, queries, fragments or option-like values; return host,
  repository path (owner/name, GitLab subgroups allowed) and name.
- `detect_kind` / `tea_login_hosts`: github.com and gitlab.com directly, other hosts by a
  matching server `tea logins list --output json` entry (Gitea, with its login name);
  otherwise unknown and the administrator chooses.
- `default_branch`: parse `git ls-remote --symref -- <url> HEAD`.
- `suggest_id`: lowercase slug of the repository name (at most 60 characters), first free
  `-2`..`-99` suffix.
- `read_origin` / `origin_matches`: compare an existing clone's origin with the URL.
- `ls_remote`, `tea_logins`, `clone`, `branch_exists`: commands through the injected
  runner with `GIT_TERMINAL_PROMPT=0` and SSH batch mode, bounded by timeouts.

## 3. Workflow Integration

`/api/v1/projects/repository-source` reads an address (no writes). Preview, checks and
creation in `adore/web/app.py` treat `clone_url` as described in
`Component_Web_API.md`: the clone location is proposed as `<ADORE home>/repos/<project
ID>` and may be changed to another absolute folder outside ADORE home or under its
`repos` folder (outside home its parent must exist; `~` is not expanded); it is made only
at creation (reserved with an exclusive mkdir and a sibling in-progress marker; a marker
older than 15 minutes without a folder is replaced, with a folder it marks an interrupted
clone that must be removed by hand), reused
when its origin matches, never overwritten otherwise, and removed again only by the
request that created it when verification or publication fails. The parser also rejects
SSH users or hosts starting with `-` and control characters, and git runs with
`GIT_ALLOW_PROTOCOL=ssh:https:http`.

## 4. Validation And Tests

`tests/test_repository_source.py` covers parsing and rejection, detection helpers, the
endpoint, preview without writes, checks, clone at creation, reuse, the occupied location
and cleanup after missing AEGIS or target branch. The e2e `enrollment.spec.ts` drives the
URL flow through the browser with a simulated forge.

## 5. Limitations

Forge kind for self-hosted GitLab or GitHub Enterprise is not detected; the administrator
chooses it. Cloning needs the service account's existing git credentials.
