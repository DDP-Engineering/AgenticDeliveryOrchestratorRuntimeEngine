<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Setup and Credentials

> **Status**: Planning. Everything that must be installed, configured, or
> credentialed to run the Agentic Delivery Orchestrator (ADOR), on Windows 11
> (first tests) and Ubuntu 22 (production). Token scopes verified against the
> official GitLab and GitHub docs (July 2026); see References.

## 0. Setup Checklist (summary)

| # | Item | Where | Notes |
|---|---|---|---|
| 1 | `git` | host | Any recent version. |
| 2 | Container runtime | host | Docker Desktop (Win) / Docker Engine or Podman (Ubuntu). |
| 3 | Python 3.11+ | host | For ADOR itself (stdlib only). |
| 4 | Git-platform CLI | host | `glab` (GitLab) and/or `gh` (GitHub), authenticated. |
| 5 | Executor CLI | container image | opencode / pi / codex. |
| 6 | Git-platform token | `.env` / CLI auth | GitLab `api` scope, or GitHub fine-grained (see below). |
| 7 | Model provider key | `.env` -> container | e.g. `ANTHROPIC_API_KEY`. |
| 8 | Git identity for the bot | config | `agent.name` -> commit author. |
| 9 | Branch protection | Git platform repo | Protect target branch; require approval so the bot cannot merge. |
| 10 | `config.toml` | ADOR repo | Non-secret settings (see Configuration_Reference.md). |

## 1. Host Prerequisites

Same on both OSes (ADOR is portable Python; the heavy tooling lives in the
container image):

- **git** on `PATH`.
- **Container runtime:** Docker Desktop (Windows 11) or Docker Engine / Podman
  (Ubuntu 22). ADOR runs the executor in a container.
- **Python 3.11+** for ADOR (no third-party runtime dependencies).
- **Git-platform CLI**, authenticated (section 2): `glab` and/or `gh`.
- **Network access** to the Git platform host (for this project, the self-managed
  GitLab at `gitlab.examplexdigital.fr`) and to the model provider API.

## 2. Git Platform Credentials

ADOR needs to: read issues and their comments, post/edit issue comments (status +
questions), read/apply labels, push a branch, create and update a (draft) merge
or pull request, and read MR/PR review threads. It must **not** be able to merge.

### 2.1 GitLab (this project's Git platform)

**Recommended token:** a **Project Access Token** on the `cockpit-gcp` project, or
a **Personal Access Token** on a dedicated service/bot account if one exists. In a
corporate instance where new users are hard to create, a PAT on an existing
service account (or an approved human account) is acceptable - identity is
marker-based, not account-based (see design doc 5c).

**Scope:** `api`.

- The `api` scope grants **complete read and write API access** for the token's
  scope, which covers everything ADOR does through the API: create/update merge
  requests, create and edit issue/MR **notes** (comments), read issues and
  discussions, and read/manage **labels**.
- For a **personal access token**, `api` **also** grants read/write to the
  repository over **Git-over-HTTP** (push/pull) - so a single `api` PAT covers
  both the API actions and the `git push` of the run branch.
- Do **not** add `sudo` or `admin_mode`.

**Alternative (more granular):** use a **fine-grained personal access token** to
restrict the token to the single `cockpit-gcp` project. Classic PATs have no
per-endpoint scope for "merge requests only" - writing MRs/notes requires `api`.

**Role / membership (this is what blocks merging):**

- The token's account must be a **project member with the Developer role**.
  Developer can push to non-protected branches, create merge requests, and add
  notes/labels.
- Do **not** grant **Maintainer/Owner**. With the target branch protected and
  merges requiring approval, a Developer-level token **cannot merge** - which
  enforces the "human merges" boundary at the permission level.

**Wire it up (CLI auth):**

```bash
# self-managed host
glab auth login --hostname gitlab.examplexdigital.fr
# or non-interactive with a token:
export GITLAB_TOKEN=<token>        # ADOR / glab read this
```

If `glab` is already authenticated on the host (as in the current setup), ADOR
can ride that auth and no token is needed in `.env`. Provide `GITLAB_TOKEN` only
for direct API calls or to run `glab` inside the container.

### 2.2 GitHub (portability path)

**Recommended token:** a **fine-grained personal access token** scoped to the
single target repository, with these repository permissions:

| Permission | Level | Why |
|---|---|---|
| Metadata | Read | Mandatory baseline for fine-grained tokens. |
| Contents | Read and write | Clone/fetch and **push** the run branch. |
| Pull requests | Read and write | Create/update the draft PR; read review threads. |
| Issues | Read and write | Read issues, post/edit comments, manage labels. |
| Commit statuses | Read (optional) | Read CI status on the PR. |

- Do **not** grant Administration. If the agent must edit files under
  `.github/workflows`, also add **Workflows: Read and write** (not needed for the
  current GitLab-hosted repo).
- **Classic PAT alternative:** the `repo` scope covers all of the above but is
  broader; prefer fine-grained.

**Role:** repository **collaborator with Write**. Branch protection with a
required review prevents the token from merging (same boundary as GitLab).

**Wire it up:**

```bash
gh auth login                      # interactive
export GITHUB_TOKEN=<token>        # or non-interactive
```

## 3. Executor and Model Provider Credentials

The executor (opencode / pi / codex) runs **inside the container** and needs a
model-provider API key. This is the credential you almost certainly must supply.

- **Which key** depends on the executor's configured provider, e.g.
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or a gateway key. Put it in `.env`; ADOR
  injects only this subset into the container at `docker run` time.
- **opencode:** configured by `opencode.json` in the target repo (model, skills,
  permissions) plus the provider key in the environment. The repo's
  `opencode.json` already sets tool permissions and marks `git push` /
  `gh pr create` as `ask` (which safely blocks the executor from pushing).
- **pi / codex:** same pattern - a provider key in the environment; the launcher
  command template in `config.toml` selects the tool.
- **Never bake keys into the container image.** Pass them at launch only.

## 4. Git Identity for the Bot

Not a secret, but required so commits are attributed consistently:

- `git config user.name` / `user.email` inside the container derive from
  `agent.name` (default `ADOR`). Use a recognizable identity, e.g.
  `ADOR <ador-bot@examplexdigital.fr>`.
- This is separate from the marker used to distinguish comments (design doc 5c);
  it only affects commit authorship.

## 5. Branch Protection (repo-side configuration)

This is what makes "the agent never merges" a hard rule rather than a convention:

- **Protect the target branch** (`develop` and/or `main`).
- **Require at least one approval** on the MR/PR before merge.
- Allow **Developer/Write** to push feature branches and open MRs, but restrict
  **merge** of the protected branch to Maintainer/approved reviewers.
- ADOR opens the MR/PR as a **draft**, which additionally cannot be merged until a
  human marks it ready.

## 6. Container Runtime and Image

- Install Docker/Podman (section 1).
- Build the **executor image** once (`ador-executor:latest`) with the base
  tooling baked in: Python 3.11 + `uv`, Node 20 + `npm`, `git`, the executor CLI,
  `glab`/`gh`, and the target repo's build/test tools (matching `.gitlab-ci.yml`).
- Create the persistent cache volumes referenced in `config.toml`
  (`ador-uv-cache`, `ador-npm-cache`) so `uv sync` / `npm ci` are fast.

## 7. Where Each Value Goes

| Value | Location | Secret? |
|---|---|---|
| `GITLAB_TOKEN` / `GITHUB_TOKEN` | `.env` (or CLI auth store) | Yes |
| Model provider key (e.g. `ANTHROPIC_API_KEY`) | `.env` -> container | Yes |
| Git platform kind, repo path, labels, polling, budgets, etc. | `config.toml` | No |
| Bot name/slug, git identity | `config.toml` | No |
| Branch protection, approvals | Git platform project settings | n/a |

- Secrets: `.env` (gitignored; template in `.env.example`), or on a server prefer
  systemd `EnvironmentFile=`, an OS keyring, or CI/CD variables.
- Non-secrets: `config.toml` (see `Configuration_Reference.md`).

## 8. Minimal vs Least-Privilege

- **Fastest to start:** rely on the already-authenticated `glab`/`gh` on the host
  for the Git platform, and supply only the model provider key in `.env`.
- **Least privilege (recommended for production):** a fine-grained,
  project-scoped Git-platform token on a dedicated service account with exactly the
  permissions in section 2, Developer/Write role only, and enforced branch
  protection.

## References

- GitLab - Access token scopes (the `api`, `read_api`, `write_repository` table
  and the Git-over-HTTP footnote for personal access tokens):
  https://docs.gitlab.com/security/tokens/access_token_scopes/
- GitLab - Personal access tokens:
  https://docs.gitlab.com/user/profile/personal_access_tokens/
- GitLab - Fine-grained personal access tokens:
  https://docs.gitlab.com/auth/tokens/fine_grained_access_tokens/
- GitHub - Permissions required for fine-grained personal access tokens:
  https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens
