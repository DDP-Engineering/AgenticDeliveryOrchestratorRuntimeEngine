# Executors and models

An executor is what ADORE launches for every job: the Pi coding agent and the AI model it uses. Administrators choose the model in a project's Settings.

## What an executor is {#what}

For each job ADORE starts Pi, its only coding agent, in an isolated working copy, and Pi works through the repository's AEGIS stages with the configured provider and model. Pi never commits, pushes or sees forge credentials; ADORE does that. In a container ADORE uses the Pi built into the executor image; for a project installed on the server, Pi must already be installed for the server account. Changes apply to new jobs only.

## Choose the provider and model {#agent-and-model}

Open **Settings → Agent and model**. The rows are **Provider**, **Model**, **Executor launch command** and, for an endpoint, **Endpoint base URL** and **Endpoint API type**. **Edit** on any of the provider, model or endpoint rows opens one editor for all of them, and they are reviewed and applied as one change.

- **Provider**: one of Pi's API-key providers (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral and others), **ChatGPT subscription** or **OpenAI-compatible endpoint**.
- **Model**: choose from Pi's list for that provider or type any model ID the provider accepts, for example `gpt-5.4`. The list comes with the Pi version ADORE ships and is read without internet access. There is no universal default.
- **ChatGPT subscription**: Pi uses the ChatGPT Plus or Pro account this ADORE server is signed in to, see [Sign in with ChatGPT](#chatgpt). The model list holds the models a ChatGPT subscription serves, for example `gpt-5.6-luna`.

**Prepare candidate** shows each field's active and proposed value and **Apply change** writes them; expect to pause monitoring first, see [Project settings](/help/settings#editing). In a container ADORE starts the Pi built into the image itself, through its RPC mode with fixed settings, and stops it at the stage time limit or when you cancel; the launch command is not used there, so only the Pi preset is offered. For a project installed on the server the launch command starts the installed Pi, defaults to `pi -p --mode json --model {model} {prompt}` (`{model}` becomes provider/model), must contain `{prompt}` and must not use `--auto`.

## OpenAI-compatible endpoint {#endpoint}

For a model served on your own network, such as LM Studio, Ollama or vLLM, choose **OpenAI-compatible endpoint** and fill in:

- **Endpoint base URL**: the address as seen from the container, for example `http://192.168.1.20:1234/v1`. `localhost` is the container itself. `host.docker.internal` reaches the host only on Docker Desktop; with Docker Engine on Linux or inside WSL use the host's network address, and for a server on Windows reached from Docker in WSL use the WSL default gateway.
- **Endpoint API type**: `openai-completions` for LM Studio, Ollama and vLLM; `openai-responses`, `anthropic-messages` and `google-generative-ai` are also accepted.
- **Model**: the model ID the endpoint serves.

An endpoint key is optional: save it under Authentication as ADORE_ENDPOINT_API_KEY. ADORE describes the endpoint to Pi for every job; the address never carries a user name, password or query. With [internet access](#internet) Off, ADORE allows the endpoint's address itself. An endpoint is available for container projects only.

## Authentication {#credentials}

Open **Authentication** in the same group.

- **Provider API key.** The panel names the variable the configured provider needs, for example OPENAI_API_KEY for OpenAI or ANTHROPIC_API_KEY for Anthropic. Enter the **API key** and choose **Save API key**. ADORE stores it privately in the project's credential store on the server, never in the configuration file, passes it to Pi only as that variable and never shows it again; **Disconnect project API key** removes it. Changing a key needs monitoring paused, an idle project and no pending change, and does not test the key.
- **Existing account sign-in.** Only for a project installed on the server: Pi uses its own sign-in for the server account, set up outside the web interface. A container project uses the provider's API key, or for a ChatGPT subscription a short-lived access token from the server's [ChatGPT sign-in](#chatgpt); no sign-in is copied into the container.
- **Environment-managed values.** A variable already set in the ADORE server environment is labelled **Set on the ADORE server; manage it externally**. The web interface cannot overwrite it.
- **Web search key.** With internet access On and web search Brave or Tavily, the panel also lists BRAVE_API_KEY or TAVILY_API_KEY, saved the same way, also for a ChatGPT subscription.
- **Additional credential variables.** Names only (**Add credential variable**) of extra secrets Pi receives besides the provider's key; most projects need none.

Credential values never appear in the configuration file, reviews, audit records, logs or exports.

## Sign in with ChatGPT {#chatgpt}

One ChatGPT Plus or Pro account serves every project on this ADORE server whose provider is **ChatGPT subscription**. Administrators sign in under **Authentication** of such a project; ADORE runs Pi's own OpenAI sign-in, so the server needs no browser.

1. Choose **Sign in with ChatGPT**.
2. Open **Open the ChatGPT sign-in page** on your own computer and sign in with the ChatGPT account. The link is valid for 15 minutes.
3. The browser then shows an error page at `127.0.0.1:1455`. That is expected: copy the full address from its address bar.
4. Paste it into **Redirect address** and choose **Complete sign-in**.

The status is **Signed in**, **Not signed in** or **Sign in again**. **Sign in again** means OpenAI no longer accepts the stored sign-in; jobs fail until an administrator signs in again. An address from an older link is refused and the sign-in keeps waiting; **Cancel** ends it. When OpenAI refuses the account, for example because its plan cannot share the subscription, the sign-in ends with that reason. **Disconnect ChatGPT** deletes the stored sign-in.

The sign-in stays in a private folder on the ADORE server. Before each stage ADORE takes a fresh access token from it, valid for about an hour, and passes only that token to Pi; the sign-in itself never enters the job's container. A ChatGPT project therefore runs in a container, its stage time limits are at most 3000 seconds, and its image must be built from the current ADORE executor image. Only administrators see or change the sign-in; audit records name the action, never a token or address.

> ADORE is free today. Offering it as a hosted or paid service with ChatGPT sign-in would first need OpenAI's interest form.

## Test AI connection {#test-connection}

Administrators choose **Test AI connection** under **AI connection**. It starts Pi once in a temporary container, or in a temporary folder for Pi installed on the server, asks it to run one shell command and then to reply with a fixed text, and may incur provider charges. The project must be idle with valid saved settings and no pending change; for a container project the configured image must exist on the server.

The result is **AI model connected** only when the shell command ran and the reply arrived. Otherwise **AI connection could not be verified** comes with its own guidance for: no credential saved, no ChatGPT sign-in, a ChatGPT plan that cannot share its subscription, a reached ChatGPT usage limit, a key the provider rejected, a provider or endpoint Pi could not reach, a model the provider or endpoint does not know, a rate limit, another provider error, a timeout, a missing image or Pi, or a shell command Pi could not run. It starts no job. The saved result is bound to the current provider, model, settings and credentials and appears in the Summary host checks. Developers see it but cannot run the test.

## Internet access for the agent {#internet}

**Internet access for the agent** in Settings → Agent and model decides what a job's container can reach. It is **Off** by default.

- **Off**: the container reaches only the model provider. ADORE allows the provider's own addresses itself, for an OpenAI-compatible endpoint its address, through a separate network proxy for each job. Web search, page reading and downloads such as `curl`, `npm install` or `pip install` fail, and Pi is told so.
- **On**: the container has an open network. Pi can search the web and read pages, and download libraries with `curl`, `npm` or `pip`.

**Web search** chooses the search service while it is On: **Exa (no key)**, the default, **Brave (key needed)**, **Tavily (key needed)** or **None** (no web search or page reading). For Brave or Tavily, save BRAVE_API_KEY or TAVILY_API_KEY under **Authentication**.

> With internet access On, a malicious web page could try to make the agent send its API key or ChatGPT token out. Prefer limited, short-lived keys.

Both settings change through **Prepare candidate** and **Apply change** like other settings. With internet access Off the proxy image must exist on the ADORE server; **Check host prerequisites** reports it, and the search key when one is needed. For a project installed on the server the switch is shown as **Not enforced**: Pi reaches whatever the server reaches.

## Where jobs run {#where-jobs-run}

| | Container | Native local execution |
|---|---|---|
| Runs in | A temporary Docker or Podman container on the ADORE server | The ADORE server itself, under the service's operating system account, in a dedicated worktree |
| Environment | A project image prepared by the administrator | Tools, versions and libraries you install yourself on that server |
| Sign-in | The provider's API key, or for a ChatGPT subscription a short-lived access token from the server's ChatGPT sign-in | The provider's API key or Pi's existing sign-in on that account, reused in place |
| Agent settings | The Pi built into the image, with settings fixed by ADORE; personal Pi settings and skills are not read | The Pi installed for that account, started with the launch command and that account's Pi settings |
| Isolation | Container; with internet access Off it reaches only the model provider | Only the worktree; commands can reach whatever the account can, so use a dedicated least-privilege account |
| Chosen | **Runs in** → **Container**, the default, on enrollment step 2 or in Settings → Agent and model | **Runs in** → **Installed on the server**, or the server profile or TOML enrollment |

Edits in Settings go through **Prepare candidate**, review and **Apply change**. **Installed on the server** shows the native executor command and the local account fields (account `current`, home, PATH and, on Linux, the cgroup root) together with the local execution notice.

Host checks for a local project skip the container engine and check the installed Pi and its sign-in or API key.

## Detect installed executors {#installed-executors}

When you choose **Installed on the server**, ADORE detects OpenCode, Pi, Codex and Qwen Code on the execution host. **Runs as** identifies the machine and account; in a portable desktop installation, this is the computer running ADORE. The first detected installation prefills an empty or standard command during enrollment. **Detected installations** lets you choose another installation. Existing saved commands and manual edits stay unchanged.

ADORE automatically uses the account running its process, that account’s home folder and tool PATH, and the executor’s saved sign-in. This is a new executor process, not a connection to an open terminal session. A service uses its service account.

Detection starts automatically when local execution is selected; switching agents uses the detected list. Open **Advanced** for **Detect installed executors** if you need to refresh it. Open **Advanced** to enter **Executable path on the ADORE host** and choose **Use executable**, or edit **Executor launch command**. Windows uses a real `.exe`; Node agents need the installed Node/JavaScript command. Detection reads installation locations only: it does not install tools, sign in or test model access.

Open **Advanced** for the full command, a manual executable path, home/PATH overrides and Linux cgroup delegation. Leave home and PATH empty for automatic values. PATH means tool directories, not the executable file. Account names in Settings verify the current identity; they do not switch users.

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

For a custom WSL runtime command, place `--` or `--exec` before the container command. Standard Docker and Podman entries are handled automatically.

Then confirm with **Check host prerequisites** and **Test AI connection**.

## System packages {#system-packages}

An administrator can review **Allow agent system package installation** in **Settings → Agent and model**. It is off by default and available only for containers. Pi can then install packages directly with `sudo -n`, inspect the results and adapt within the job limits. **Internet access for the agent** remains a separate choice; when it is off, external package sources need an allowed host. Use a compatible image with sudo, pause monitoring and wait for idle jobs before applying, then start a fresh job. Installed packages stay in that container; they do not update the image.
