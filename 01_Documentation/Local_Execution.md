<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local execution

Select `[execution] backend = "local"` to run the installed executor under ADORE's
current machine/service account in a dedicated ticket worktree. Omitted backend
keeps container execution. Choose **Runs in → Installed on the server** on enrollment
step 2 or in Settings → Agent and model (reviewed configuration flow), or use assisted
CLI setup or external server TOML enrollment; the web shows the native executor command
and the local account fields (`account`, `home`, `path`, Linux `cgroup_root`).
Readiness evidence identifies the actual server machine/account. Tools installed on the browser
laptop do not prepare the execution server.

## Account and user-owned tools

You decide and independently install/prep project tools, versions, SDKs and libraries
on that machine under the effective account. ADORE checks basic selected-executor
availability and auth state. It supplies no catalogue, discovery, installer,
bootstrap or required project-tool manifest. Authenticate the installed CLI
interactively under the service account before unattended operation. ADORE never
switches account or starts login. A named `local.account` asserts the actual account
(qualified name on Windows); `current` uses it directly. Empty home/PATH settings
use native defaults; explicit values select an already prepared environment.

A worktree is not a host sandbox. Project commands can access files, credentials
and helpers permitted to the OS account. Use a dedicated least-privilege account
and keep forge publication credentials outside it when possible. Environment
filtering does not remove filesystem access. Container egress restrictions are
refused locally; `container.egress.mode` must be `open`.

## Platform controls

Native Windows uses a unique non-breakaway Job Object with kill-on-close. The CLI
must be an executable `.exe`. npm `.cmd`, `.bat`, PowerShell and shell wrappers
are refused. For npm CLIs configure absolute installed `node.exe` plus the absolute
installed `.js`, `.mjs` or `.cjs` entrypoint outside the project clone. Quote paths
with spaces. Both installed identities are pinned.

Native Linux requires an absolute writable operator-delegated cgroup-v2 root with
`cgroup.controllers`, new child cgroups and `cgroup.kill`. Set `local.cgroup_root`
to that root. Configure delegation through your service manager; ADORE creates
and removes only its random child scopes. The trusted child joins before project
code, and `cgroup.kill` controls descendants. ADORE inside WSL2 works only with
the same Linux controls. Windows-to-WSL local wrapping, macOS, cgroup v1 and
PID/process-group fallbacks fail before project commands. Delegation is process
control setup; project dependency provisioning remains user-owned.

## Configuration and authentication

Keep your forge, worktree, reviewers and executor/model declarations. Example:

```toml
[execution]
backend = "local"
preparation = ""

[local]
account = "current"
home = ""
path = ""
cgroup_root = "" # Linux: absolute delegated root; Windows: unused
environment = { LANG = "en_US.UTF-8" } # Non-secret settings only

[executor]
default = "opencode"
env_keys = [] # Existing account login; approved keys may instead use protected .env
stage_host_auth = false

[executor.opencode]
command = "opencode run --dir {worktree} -m {model} --format json {prompt}"
model = "openai/your-model"
```

For a Windows npm CLI use its actual installed entrypoint, preserving normal flags:

```toml
command = '"C:\Tools\node.exe" "C:\Tools\agent\cli.js" -p --mode json --model {model} {prompt}'
```

Templates are tokenized before replacement: prompt/model/path spaces stay in their
argument. Each gate starts a fresh session; the only placeholders are `{prompt}`,
`{model}` and `{worktree}`. Shell compounds,
redirection and shell executables are unsupported. Set `workflow.aegis_python`
to installed native Python when `python3` is unavailable; its path may contain spaces.

Local mode rejects preparation recipes, host-auth staging, container run arguments,
tool-check manifests, SELinux relabel and custom `container.runtime_env`. Remove
these when changing backend. Use `local.environment` for non-secret endpoint and
config-location settings. Unknown local fields, managed HOME/PATH/account overrides
and forge credential variables reject. Approved provider secrets belong in the
protected profile `.env` or process environment through `executor.env_keys`.
Inline `OPENCODE_CONFIG_CONTENT` must be bounded strict JSON with `{env:NAME}` auth
references; literal API keys/tokens/passwords are refused.

For OpenCode profiles every local command (gates, probes, strict verification)
uses an ADORE-managed OpenCode configuration home instead of the account's
personal one: `XDG_CONFIG_HOME` points at the folder `executor-config` in the
profile's state root, `OPENCODE_DISABLE_CLAUDE_CODE=1` turns off OpenCode's Claude
Code compatibility, and `OPENCODE_PERMISSION` allows edits and shell commands while
denying `git push`, `tea`, `gh` and `glab`. ADORE creates the folder when the local
backend starts; a path that cannot be created or is not a folder stops the job
with a local execution error before any command runs.

What still applies: the repository's own `opencode.json`, `.opencode/` folder and
AGENTS.md, and the sign-in under `XDG_DATA_HOME`, reused unchanged.

What no longer applies:

- everything in the personal configuration home (`~/.config/opencode`): agents,
  prompts, MCP servers, plugins, providers, model overrides and the small model.
  A model from a personal provider (for example a local LM Studio provider) then
  fails; declare the provider in `[local].environment` `OPENCODE_CONFIG_CONTENT`,
  or point `XDG_CONFIG_HOME` at a prepared configuration;
- Claude Code compatibility: `~/.claude/skills`, `~/.claude/CLAUDE.md` and also the
  repository's `.claude/skills` and its `CLAUDE.md` fallback (AGENTS.md is read as
  usual).

Known gaps: OpenCode still reads the account's home-level `~/.opencode/` folder
(configuration, agents, plugins) and `~/.agents/skills`, whatever
`XDG_CONFIG_HOME` says. Keep them empty on the ADORE account; a `~/.opencode`
configuration that sets `ask` permissions makes local jobs fail as before.

The deny rules are a safety belt, not a boundary: the account keeps whatever
credentials it holds. Project tools that read `$XDG_CONFIG_HOME` see the managed
folder too. To use your own settings instead, set `XDG_CONFIG_HOME`,
`OPENCODE_DISABLE_CLAUDE_CODE` (for example `0`) or `OPENCODE_PERMISSION` in
`local.environment`; explicit values win, and on Windows these three names match
regardless of case. These values are part of the pinned environment, so finish or
cancel local runs before upgrading to a build that changes them.

Existing auth is reused in place: OpenCode at `XDG_DATA_HOME/opencode/auth.json`
(default `~/.local/share/opencode/auth.json`), Codex at `CODEX_HOME/auth.json`,
Pi at `PI_CODING_AGENT_DIR/auth.json` (default `~/.pi/agent/auth.json`), Qwen at
`~/.qwen/oauth_creds.json`. Bounded valid JSON is read only for auth/redaction;
credential stores are never copied to worktrees, IO or archives. Known account/
provider values are redacted from retained output, questions and launch descriptions.
Commands receive the small system/config-location allowlist, explicit local
settings, managed account/home/PATH and approved provider variables. On Windows
the allowlist also passes the machine/system names that platform detection and
system-folder lookups need: `PATHEXT`, `PROCESSOR_ARCHITECTURE`,
`PROCESSOR_ARCHITEW6432`, `PROCESSOR_IDENTIFIER`, `PROCESSOR_LEVEL`,
`PROCESSOR_REVISION`, `NUMBER_OF_PROCESSORS`, `OS`, `SystemDrive`, `ProgramData`,
`ProgramFiles`, `ProgramFiles(x86)`, `ProgramW6432`, `CommonProgramFiles`,
`CommonProgramFiles(x86)`, `CommonProgramW6432`, `ALLUSERSPROFILE` and `PUBLIC`.
Account names such as `HOMEDRIVE`, `HOMEPATH` and `USERDOMAIN` are not passed.
A run pins the resulting environment, so finish or cancel local runs before
upgrading to a build that changes this allowlist; a run started earlier is
otherwise treated as drifted.

## Review, readiness and limits

Use `adore --profile NAME config validate`, then `config plan` to review the pinned
non-secret local fingerprint without project commands. Web settings stage one
candidate and recheck fingerprint/revision under idle/pause/lock rules. Local
settings hide container-only controls. Portable working rules exclude backend,
machine/account, local paths/environment/cgroup and runtime identity.

Explicit host readiness checks Git/forge/AEGIS files and selected native CLI/auth
without Docker/Podman, images or recipes. Container rows are hidden locally.
Readiness does not prove project dependencies or an entire job. **Test AI connection**
sends a bounded nonce challenge through the same configured CLI/account/environment
and may incur cost. For OpenCode, Pi and Codex the challenge asks the agent to run
`echo <nonce>` with its shell tool and then reply with a second nonce; only a completed
shell call that printed the nonce plus the exact reply reports ready, and a missing,
rejected or failed shell call reports `tool-call-failed`. Qwen keeps the no-tool
challenge: only a completed matching response without observed tool calls reports
ready. It initiates no login. Compatible endpoint checks use owned native
Python with an 8-second command bound. Executor version checks are bounded at
10 seconds; the model challenge at 90 seconds. Gates retain configured budgets.

## Durable recovery and cleanup

Schema-1 execution state pins backend, machine/account, non-secret environment,
installed executable/Node entrypoint metadata and worktree/IO identity. Authoritative
runtime and immutable launch ownership live outside worktree/IO. ADORE assigns
the native scope, persists the active lease and then releases the trusted child.
The lease binds run UUID, host, supervisor PID birth and exact random Job/cgroup.
Control never kills a recovered PID alone. Reused PIDs, replaced scopes, corrupt
records or unconfirmed drain fail closed and preserve resources/evidence.

Timeout/cancellation terminate the verified scope including descendants; normal
exit also drains descendants. Parking retains worktree/archives without a live gate.
Retry/restart reconciles the same pinned resource. Explicit cancel/delete release
only verified run controls/worktrees; shared tools/home/auth and archives remain.
Routine cleanup protects active, failed, human-owned and corrupt runs. Container
profiles protect persisted native worktrees. Restore the pinned backend/account/
environment after drift or start a fresh run; never edit identity records to force
recovery. Windows parent death closes its Job; Linux recovery uses durable cgroup
identity. Old binaries reject local records.

The existing conductor retains AEGIS journals, questions, immutable gate archives,
usage coverage, authoritative exit/timeout and candidate-bound approval. Publication
opens draft MR/PRs only. ADORE never merges.

## Verification coverage

Offline proof injects native processes, Win32 accounting, Linux cgroup filesystem
and external CLIs. Focused contract/regression, TypeScript, helper, build and browser
checks cover the implemented boundaries. Full Python/frontend suites, aggregate
AEGIS `--run`, integrated epic #23 and live OS/executor/provider/forge acceptance
are explicitly deferred for this change.

Native AEGIS stdout preserves the established 4 MiB JSON exchange bound; gate
stdout, stderr and questions remain bounded at 64 KiB; Test AI connection keeps up to 1 MiB
of executor stdout, as the container test does, because Pi repeats the whole
conversation in its events. Native stream decoding
rejects invalid UTF-8; truncated JSON cannot become successful AEGIS evidence.
The shared drain retains container defaults. Saved local readiness checks reuse
approved profile .env values in memory through the same native environment.
