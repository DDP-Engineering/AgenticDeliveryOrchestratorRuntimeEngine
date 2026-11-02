<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Security And Credentials

This guide defines where ADORE obtains credentials, which boundary each
credential serves, and how to keep a target project under human control. Use it
with [Getting_Started.md](Getting_Started.md) and
[Configuration_Reference.md](Configuration_Reference.md).

## Credential Boundaries

| Need | Preferred location | Boundary |
| --- | --- | --- |
| Forge access | Authenticated `glab`, `gh` or `tea` session for the run-as account, or a real process environment variable | Host forge CLI |
| Model-provider key | The project's credential store (profile `.env`, saved from Settings → Agent and model) or the ADORE runtime environment | Only the configured provider's key variable plus configured `env_keys` |
| Profile settings | A profile `config.toml` | Non-secret configuration only |
| Project tools | A project-specific container image | No credentials |
| Service secrets | Operating-system secret store or service environment file | Process environment, with normal host controls |

Never place secrets in `config.toml`, a Dockerfile, a container image, ticket
body, commit, branch name, or MR/PR description.

## Forge Authentication

The ADORE host uses `glab` for GitLab, `gh` for GitHub, and `tea` (>= 0.15)
for Gitea. Authenticate the correct CLI as the same account that runs ADORE:

```bash
glab auth login
glab auth status
```

```bash
gh auth login
gh auth status
```

For GitLab and GitHub, ADORE does not carry a separate host setting. It uses
the active/default authenticated host selected by `glab` or `gh`; on a
corporate instance, verify that host is the intended company instance before
starting ADORE. Gitea remains explicitly selectable through its named login.

```bash
tea login add --name <login-name> --url http://<host>:<port> --token <token>
tea logins default <login-name>
tea whoami
```

For Gitea, create the token under Gitea -> Settings -> Applications with
read/write on repository and issue (no admin scopes; ADORE never merges). tea
stores host + token as a named login; when several logins exist or the wanted
one is not the default, set `[platform] login = "<login-name>"` in the profile
so ADORE pins the login explicitly on every call. The auth check is
`tea whoami` (tea has no `auth status` subcommand).

The token must permit the host account to read the target repository, read and
update tickets, create branches, push those branches, and create draft MR/PRs.
Use the narrowest token scope and repository access that meet those needs.

Note on git push: ADORE pushes run branches with plain `git` from the local
clone, not through the forge CLI. The clone's `origin` remote must therefore
be pushable non-interactively by the run-as account - an SSH remote with a
loaded key, or an HTTP(S) remote with a credential helper (tea ships one:
`git config credential.helper '!tea login helper'`).

ADORE never merges. Keep branch-protection rules and required human review in
the forge; they are the final delivery boundary.

### Important: ADORE `.env` Is Not Forge-CLI Login

For CLI engine commands, ADORE reads `.env` beside the resolved profile/config
first and falls back to cwd `.env` when no adjacent file exists. Direct library
callers default to cwd `.env`. The real process environment overrides file
values. ADORE passes only the configured provider's key variable and the
names in `[executor] env_keys` to executor containers.

Therefore a `GITLAB_TOKEN` or `GITHUB_TOKEN` stored only in that `.env` file is
not used by `glab` or `gh` on the host. Use an authenticated CLI session or put
the token in the actual process environment. A systemd `EnvironmentFile` is an
example of the latter because systemd exports it before ADORE and the forge CLI
start. `tea` reads its logins only from its own config file
(`tea login add`); it does not consume token environment variables at all.

## Executor Credentials

Pi, ADORE's only coding agent, runs inside an ADORE-managed container. It
receives exactly one model credential: the key of the configured
`[executor] provider`, under the environment variable Pi reads for that
provider. The key never appears in `config.toml`; an inline key field is
refused as an unknown key.

```toml
[executor]
provider = "openai"
model = "gpt-5.5"
```

Save the key in **Settings → Agent and model → Provider API key**, which writes
it to the project's credential store (the profile `.env`, mode 0600), or provide
it through the ADORE process environment or that `.env` (cwd is the fallback):

```dotenv
OPENAI_API_KEY=<provider-key>
```

The variable follows the provider (`ANTHROPIC_API_KEY` for `anthropic`,
`GEMINI_API_KEY` for `google`, and so on). An OpenAI-compatible endpoint
(`provider = "custom"`) takes an optional `ADORE_ENDPOINT_API_KEY`; the
generated Pi `models.json` names that variable (`$ADORE_ENDPOINT_API_KEY`) or a
literal placeholder, never the key. A ChatGPT subscription has no key variable;
its sign-in is not available yet. The web interface shows only the variable
name and whether it is set for the project or on the server, and its value
never appears in API responses, audit records, logs or Test AI connection
results.

`[executor] env_keys` lists additional secrets Pi receives besides the
provider's key; most projects need none. Only those names and the provider's
variable reach the executor container. ADORE rejects known forge credential
names (`GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GLAB_TOKEN`, `GITEA_TOKEN`,
and `TEA_TOKEN`) in `env_keys`. The executor prompt also forbids commit, push,
MR/PR creation, merge, and creating AEGIS child task journals (`task --parent`)
outside the single pinned task. ADORE alone creates local checkpoint commits and
performs remote publication after a fingerprint-bound human approval.

Every required problem/approval comment is written to a local outbox before
transport. Evidence is bounded and common credential forms are redacted. A
notification failure stops active code work instead of silently losing the
operator signal.

Keep the list small and remove keys Pi does not need.

## Pi Sign-In

ADORE copies no host sign-in into a container: the former `stage_host_auth`
bridge is removed, and the key is refused with `[executor] unknown key
'stage_host_auth': remove it from config.toml`. Pi in a container runs with
ADORE's own agent directory (`/home/adore/.adore-pi-agent`) and reads nothing
from `~/.pi`, so a container project always uses a provider API key in the
provider's environment variable. ADORE's guard extension, loaded for every
container Pi run, refuses `git push` and the `gh`, `glab` and `tea` commands in
the agent's shell; the boundary stays that no forge credential is in the
container.

A project installed on the server (local execution) may instead reuse the
account's own Pi sign-in in place (`PI_CODING_AGENT_DIR`, default
`~/.pi/agent`); see [Local execution](Local_Execution.md). That does not remove
the need to protect the account's own credential store. For unattended
operation, prefer an explicit model-provider key.

## Git Identity

Set a bot name and email in `[agent]`. They are used for the commits ADORE
creates. The identity is not an access-control mechanism; forge permissions
remain bound to the authenticated host account or token.

```toml
[agent]
name = "ADORE"
slug = "adore"
email = "adore-bot@local"
```

Use an organization-approved email address when the forge requires a verified
or attributable commit identity.

## Container and Network Boundaries

- Build project tools into a project image; never bake credentials into it.
- Keep the run-as account non-privileged where practical.
- Use rootless Podman with `--userns=keep-id` when that matches the host model.
- Keep `[container.egress] mode = "open"` only when unrestricted executor
  network access is acceptable. Use `none` or `allowlist-proxy` where the
  target project's policy requires it.
- Use `[container] required_tool_checks` to prove project tools are present
  before an executor starts a gate.

## Pre-Run Security Checklist

Before the first real poll, confirm:

1. The run-as account can authenticate the selected forge CLI.
2. The profile contains no secret values.
3. Pi has only the provider's key and the keys listed in `env_keys`.
4. The target project's branch protections require human review and merge.
5. The chosen image contains no secret files.
6. The configured egress mode meets the target project's policy.
7. `adore --profile <profile-name> config validate` completes successfully.


## Project-scoped repository tokens from the GUI

Admin Project → Summary → Connect repository verifies the configured forge
account and exact repository read access before saving a token for this project.
Create a token on the forge, then submit over the ADORE HTTPS interface. Use an
account restricted to the required repositories and these operational permissions:

- Gitea: read user identity plus repository/issue read-write scopes. See
  [Gitea token scopes](https://docs.gitea.com/1.26/development/api-usage).
- GitHub: selected repository Contents, Issues and Pull requests permissions
  appropriate to ADORE operations. See
  [GitHub fine-grained permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens).
- GitLab: api scope and appropriate project membership. See
  [GitLab token scopes](https://docs.gitlab.com/security/tokens/access_token_scopes/).

Successful connection proves read access, not all operational permissions. Git
clone/push credentials remain separately configured on the host. GUI web login
and forge account login are separate. Reconnect to rotate; revoke old tokens on
the forge. OAuth applications and forge passwords are not supported by this form.

repository-auth.json is a strict scope-bound secret beside config, with POSIX0600
permissions; Windows installations require restricted profile-home ACLs. Backups
contain the file and require equal protection. Tokens do not enter argv, API
responses, browser storage, config/portable export, audit or executor environments.
The matching forge CLI gets isolated temporary config/environment; shared login
files are untouched and temporary config is removed after each command. Returned
CLI token text is redacted. Missing scoped files retain external CLI login;
corrupt, insecurely permissioned or mismatched records fail closed.

Forge HTTPS verifies certificates. Explicit HTTP acknowledgement is available for
local Gitea/GitLab; tokens are unencrypted on that path. Origin subpaths are excluded.
CLI mechanisms: [gh environment](https://cli.github.com/manual/gh_help_environment),
[glab configuration](https://docs.gitlab.com/cli/config/) and
[tea config schema](https://gitea.com/gitea/tea/src/branch/main/modules/config).

## Project provider keys in the web interface

Admin Project → Executor configuration → Provider credentials edits approved provider variables in the private profile .env. Saving/removing requires paused monitoring, idle valid state and no pending changes. Other .env variables are retained. POSIX files use 0600; Windows deployment must protect the profile directory with the service-account ACL. Browser drafts clear after a mutation and leaving the page; response, audit and portable export omit credential values. Ambient environment overrides remain externally managed. A saved key is not proof of provider sign-in; Test AI connection is explicit and may use API billing separately from a subscription. GUI disconnect removes only the chosen project API key, leaving external subscription login and provider revocation to their actual owners. See Component_Executor_Configuration.md for strict input/evidence contracts.

## Container preparation

Preparation recipes are explicitly acknowledged executable project input and immutable review evidence. Keep secret values in existing allowlisted credential variables, not source text. Setup uses existing egress and executor credentials; no forge credentials are injected. Known secret values are redacted from bounded retained streams. Read-only host/model checks never execute recipes. See [Container preparation](Container_Preparation.md).

## Native local execution

Local worktrees are not host sandboxes. Use a dedicated least-privilege account. Installed auth is reused in place; provider values stay in protected .env/memory. Account filesystem/credential-helper access remains available to project commands.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.
