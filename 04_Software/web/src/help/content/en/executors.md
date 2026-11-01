# Executors and models

An executor is the pairing ADORE launches for every job: a coding agent and the AI model it uses. Administrators choose both in a project's Settings.

## What an executor is {#what}

For each job ADORE starts the project's coding agent in an isolated working copy, and the agent works through the repository's AEGIS stages with the configured model. The agents are OpenCode, Pi, Codex and Qwen Code. The agent never commits, pushes or sees forge credentials; ADORE does that. ADORE installs no agents and fetches no model lists, so the agent must already exist in the project image or on the server. Changes apply to new jobs only.

## Choose the agent and model {#agent-and-model}

Open **Settings → Agent and model**. The rows are **Default coding agent**, **Executor launch command** and **Executor model identifier**.

Administrators choose **Edit** on the Default coding agent row and select OpenCode, Pi, Codex or Qwen Code. Selecting an agent loads its saved command and model, or the documented command preset. Enter the model ID yourself for a new agent: the ID your agent and provider accept, usually `provider/model`. There is no universal default. The launch command must contain `{prompt}`. **Prepare candidate** reviews agent, command and model together, and **Apply change** writes them as one change. Expect to pause monitoring first; see [Project settings](/help/settings#editing).

## Authentication {#credentials}

Open **Authentication** in the same group. A project can authenticate in three ways.

- **Provider API keys.** Choose a **Credential variable** (for example OPENAI_API_KEY or ANTHROPIC_API_KEY), enter the **API key** and choose **Save API key**. ADORE stores it privately on the server and never shows it again; **Disconnect project API key** removes it. The variable must first be listed under **Allowed credential variables**, which holds names only (**Add credential variable**). Changing a key needs monitoring paused, an idle project and no pending change, and does not test the key.
- **Subscription or host sign-in.** The agent uses its own login on the ADORE server under the service account, set up outside the web interface (the **Subscription or browser sign-in** disclosure names the command). **Use host agent sign-in** is a pilot bridge that copies that login into the container, for OpenCode and Codex only. A ChatGPT subscription is not an OpenAI API key.
- **Environment-managed values.** A variable already set in the ADORE server environment is labelled **Set on the ADORE server; manage it externally**. The web interface cannot overwrite it.

Credential values never appear in reviews, audit records or exports. An empty variable list is valid with existing server sign-in, and also in api-key mode when the image or the installed executor signs in by itself.

## Test AI connection {#test-connection}

Administrators choose **Test AI connection** under **AI connection**. It sends one short request through the configured agent in a temporary container, which may incur provider charges. The project must be idle with valid saved settings and no pending change; the image needs Python and the agent.

The result is **AI model connected** or **AI connection could not be verified**, with guidance for a timeout, missing image or agent, bad credentials or unavailable model. It proves model access only, not tool support, and starts no job. The saved result is bound to the current model, settings and credentials and appears in the Summary host checks. Developers see it but cannot run the test.

## Where jobs run {#where-jobs-run}

| | Container | Native local execution |
|---|---|---|
| Runs in | A temporary Docker or Podman container on the ADORE server | The ADORE server itself, under the service's operating system account, in a dedicated worktree |
| Environment | A project image prepared by the administrator | Tools, versions and libraries you install yourself on that server |
| Sign-in | Listed API keys or host sign-in | The agent's existing login on that account, reused in place |
| Agent settings | The image's settings, plus the [local endpoint for OpenCode](#local-endpoint) when set | For OpenCode, a settings folder managed by ADORE: agents, providers, plugins and permissions from your personal OpenCode settings folder are not used, `git push` and the forge tools are blocked, and `.opencode` and `.agents/skills` folders in the account's home still apply |
| Isolation | Container with a network policy | Only the worktree; commands can reach whatever the account can, so use a dedicated least-privilege account |
| Chosen | **Runs in** → **Container**, the default, on enrollment step 2 or in Settings → Agent and model | **Runs in** → **Installed on the server**, or the server profile or TOML enrollment |

Edits in Settings go through **Prepare candidate**, review and **Apply change**. **Installed on the server** shows the native executor command and the local account fields (account `current`, home, PATH and, on Linux, the cgroup root) together with the local execution notice.

Host checks for a local project skip the container engine and check the native agent and its sign-in.

## Project image {#project-image}

For a container project, Settings → Agent and model shows **Executor runs in a container**, the **Image used** and an **Environment preparation instructions** disclosure. The web interface does not define or build the image, and adding a Dockerfile to the repository starts no build. The administrator prepares it on the server:

1. Create `executor/Dockerfile` in the repository, starting from the ADORE base image, with no credentials. The image needs Python, sh and the selected agent.
2. Build it with the server's Docker or Podman and verify the agent and tool versions.
3. Select the image in the web interface as described below or, with monitoring paused and no active jobs, set `execution.backend`, `container.image` and `container.required_tool_checks` in the project's `config.toml` (administrators see its path in the disclosure), then validate the profile.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

To use the image, choose the **Container runtime** (Docker or Podman) and the **Executor image** on step 2 of enrollment, or edit **Container runtime command** and **Agent container image** in Settings. The image is free text with suggestions read from the images on the ADORE server for that runtime (administrators only); a notice appears when the typed image is not on the server and another when the list cannot be read. Choosing an executor proposes an image whose tag starts with the executor name and a hyphen (for example `pi-`), preferring `adore-executor-base:`; it replaces only the old default or an earlier proposal, never a value you typed.

Then confirm with **Check host prerequisites** and **Test AI connection**.

## Local endpoint for OpenCode {#local-endpoint}

For a container project that uses OpenCode, administrators also see **OpenAI-compatible endpoint URL** in Agent and model, for a model served on your own network. Enter the URL, an optional **Credential environment reference**, the **Request timeout (seconds)** and, for HTTPS with a private CA, the **Custom CA file in executor image**. The protocol is fixed to OpenAI chat completions. **Prepare candidate** reviews the URL and model together.

The URL must be reachable from inside the executor container, where localhost is the container itself, and the image must already contain the provider package. Saving does not test reachability and adds no cloud fallback; **Check host prerequisites** tests a streamed tool call from a temporary container.
