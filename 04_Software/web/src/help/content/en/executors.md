# Executors and models

An executor is what ADORE launches for every job: the Pi coding agent and the AI model it uses. Administrators choose the model in a project's Settings.

## What an executor is {#what}

For each job ADORE starts Pi, its only coding agent, in an isolated working copy, and Pi works through the repository's AEGIS stages with the configured model. Pi never commits, pushes or sees forge credentials; ADORE does that. ADORE fetches no model lists. In a container ADORE uses the Pi built into the executor image; for a project installed on the server, Pi must already be installed for the server account. Changes apply to new jobs only.

## Choose the model {#agent-and-model}

Open **Settings → Agent and model**. The rows are **Executor model identifier** and **Executor launch command**.

Enter the model ID yourself: the Pi model in `provider/model` form, for example `openai/gpt-5.4`. There is no universal default. In a container ADORE starts the Pi built into the image itself, through its RPC mode with fixed settings, and stops it at the stage time limit or when you cancel; the launch command is not used there, so only the Pi preset is offered. For a project installed on the server the launch command starts the installed Pi, defaults to `pi -p --mode json --model {model} {prompt}`, must contain `{prompt}` and must not use `--auto`. Each row is an ordinary setting: **Prepare candidate** reviews it and **Apply change** writes it. Expect to pause monitoring first; see [Project settings](/help/settings#editing).

A model served on your own network through an OpenAI-compatible endpoint, such as LM Studio, cannot be configured in this version.

## Authentication {#credentials}

Open **Authentication** in the same group. A project can authenticate in three ways.

- **Provider API keys.** Choose a **Credential variable** (for example OPENAI_API_KEY or ANTHROPIC_API_KEY), enter the **API key** and choose **Save API key**. ADORE stores it privately on the server and never shows it again; **Disconnect project API key** removes it. The variable must first be listed under **Allowed credential variables**, which holds names only (**Add credential variable**). Changing a key needs monitoring paused, an idle project and no pending change, and does not test the key.
- **Existing account sign-in.** Only for a project installed on the server: Pi uses its own sign-in for the server account, set up outside the web interface. A container project always uses provider API keys; no sign-in is copied into the container.
- **Environment-managed values.** A variable already set in the ADORE server environment is labelled **Set on the ADORE server; manage it externally**. The web interface cannot overwrite it.

Credential values never appear in reviews, audit records or exports. An empty variable list is valid for a project installed on the server that uses the existing account sign-in.

## Test AI connection {#test-connection}

Administrators choose **Test AI connection** under **AI connection**. It sends one short request through Pi in a temporary container, or in a temporary folder for Pi installed on the server, which may incur provider charges. The project must be idle with valid saved settings and no pending change; for a container project the configured image must exist on the server.

The result is **AI model connected** or **AI connection could not be verified**, with guidance for a timeout, missing image or Pi, bad credentials, unavailable model or a shell command Pi could not run. In a container Pi answers without using tools, so the test proves model access only. For Pi installed on the server the request also asks Pi to run one shell command, and the result is connected only when that command ran. It starts no job. The saved result is bound to the current model, settings and credentials and appears in the Summary host checks. Developers see it but cannot run the test.

## Where jobs run {#where-jobs-run}

| | Container | Native local execution |
|---|---|---|
| Runs in | A temporary Docker or Podman container on the ADORE server | The ADORE server itself, under the service's operating system account, in a dedicated worktree |
| Environment | A project image prepared by the administrator | Tools, versions and libraries you install yourself on that server |
| Sign-in | Listed provider API keys | Listed provider API keys or Pi's existing sign-in on that account, reused in place |
| Agent settings | The Pi built into the image, with settings fixed by ADORE; personal Pi settings and skills are not read | The Pi installed for that account, started with the launch command and that account's Pi settings |
| Isolation | Container with a network policy | Only the worktree; commands can reach whatever the account can, so use a dedicated least-privilege account |
| Chosen | **Runs in** → **Container**, the default, on enrollment step 2 or in Settings → Agent and model | **Runs in** → **Installed on the server**, or the server profile or TOML enrollment |

Edits in Settings go through **Prepare candidate**, review and **Apply change**. **Installed on the server** shows the native executor command and the local account fields (account `current`, home, PATH and, on Linux, the cgroup root) together with the local execution notice.

Host checks for a local project skip the container engine and check the installed Pi and its sign-in or API key.

## Project image {#project-image}

For a container project, Settings → Agent and model shows **Executor runs in a container**, the **Image used** and an **Environment preparation instructions** disclosure. The web interface does not define or build the image, and adding a Dockerfile to the repository starts no build. The administrator prepares it on the server:

1. Create `executor/Dockerfile` in the repository, starting from the ADORE base image, with no credentials. The base image already contains Python, sh and the pinned Pi.
2. Build it with the server's Docker or Podman and verify the tool versions.
3. Select the image in the web interface as described below or, with monitoring paused and no active jobs, set `execution.backend`, `container.image` and `container.required_tool_checks` in the project's `config.toml` (administrators see its path in the disclosure), then validate the profile.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

To use the image, choose the **Container runtime** (Docker or Podman) and the **Executor image** on step 2 of enrollment, or edit **Container runtime command** and **Agent container image** in Settings. The image is free text with suggestions read from the images on the ADORE server for that runtime (administrators only); a notice appears when the typed image is not on the server and another when the list cannot be read.

Then confirm with **Check host prerequisites** and **Test AI connection**.
