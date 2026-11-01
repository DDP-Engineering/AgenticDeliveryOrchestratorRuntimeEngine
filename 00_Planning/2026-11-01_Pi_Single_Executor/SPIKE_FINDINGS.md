<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# PI-01 spike findings: Pi 1.x headless contracts

Date: 2026-11-01. Ticket: [#51](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/51).
Reference for PI-02 to PI-07 together with `PLAN.md`. Everything below was
observed on this date unless marked **(code)** (read from Pi's shipped source
or docs) or **(not run)**.

Test bed: Windows 11 host (Node 24.18.0 and Node 22.23.4, Git Bash, Windows
PowerShell 5.1), WSL Ubuntu 24.04 with Docker Engine 29.6.1 (NAT networking),
image `node:22-bookworm-slim` + Pi, LM Studio 0.x on the Windows host
(`qwen/qwen3.5-9b`), the owner's ChatGPT subscription signed in fresh into an
isolated folder. No API key was available, so OpenAI/Anthropic API-key runs
were replaced by ChatGPT sign-in and a local fake endpoint; the owner's own
`~/.pi` was never read or written (a before/after listing is identical).

## Pinned versions

| Component | Version | Evidence |
|---|---|---|
| Pi (`@earendil-works/pi-coding-agent`) | **1.4.0** (npm `latest`, 2026-10-21) | `npm view`; `pi --version` -> `1.4.0` |
| Pi's own packages (`pi-ai`, `pi-agent-core`, `pi-tui`, `pi-mcp`, `pi-codemode`) | 1.4.0 (exact pins in Pi's `package.json`) | installed tree |
| `pi-web-access` | **0.46.0** (npm `latest`, 2026-10-29, MIT) | `npm view`; peer deps `*` on Pi packages |
| Node | **22.23.4** (22 LTS); Pi requires `>=22.19.0` | `engines`; image `node:22-bookworm-slim`; Windows: see Q9 |

## Fixtures

`fixtures/*.jsonl`, written by `rpc_probe.py`. One envelope per line:
`{"t_ms": <ms since start>, "dir": "stdin"|"stdout"|"stderr"|"exit"|"probe", "record": ...}`.
`stdout` records are Pi's protocol records as received; `stdin` records are the
commands sent. Secrets, home paths, user names, e-mails and host IDs are
redacted (`<REDACTED_...>`); a scan for JWTs, `sk-` keys, masked key hints,
e-mails, `urn:uuid` and the live credential's values found none.

| File | Scenario | Ends with |
|---|---|---|
| `run_tool_calls_chatgpt.jsonl` | Linux container, ChatGPT, `gpt-5.6-luna`: read, edit, `bash node test.js`; usage per message | `stop`, `agent_settled{aborted:false}`, exit 0 |
| `run_tool_calls_lmstudio_windows.jsonl` | Native Windows, LM Studio via `models.json`: read, edit, bash | `stop`, exit 0, cost 0 |
| `run_aborted_chatgpt.jsonl` | `abort` sent at the first tool call (`sleep 30`) | `agent_settled{aborted:true}`, exit 0 |
| `run_guard_blocks_forge.jsonl` | ADORE guard extension (`-e`) blocks `git push`, `gh`, `glab`, `tea`; `echo` allowed | `stop`, exit 0 |
| `run_web_access_lmstudio.jsonl` | `pi-web-access` loaded with `-e`, keyless Exa search + `fetch_content` | `stop`, exit 0 |
| `failed_invalid_api_key.jsonl` | OpenAI 401 (dummy key), native Windows Node 24 | `error`, exit `0xC0000409` (see Q9) |
| `failed_model_not_supported_chatgpt.jsonl` | ChatGPT sign-in with `gpt-5.4-mini` -> 400 `model_not_found` | `error`, exit 0 |
| `failed_refresh_chatgpt.jsonl` | expired access + invalid refresh token -> `invalid_grant` | `error`, exit 0 |
| `failed_rate_limit_retry.jsonl` | fake endpoint answering 429 (`retry-after: 1`) | 3 `auto_retry_*`, `error`, exit 0 |
| `failed_unreachable_endpoint.jsonl` | endpoint on a closed port | 3 retries, `Connection error.`, exit 0 |
| `failed_no_network_chatgpt.jsonl` | container with `--network none` | 3 retries, `Connection error.`, exit 0 |
| `failed_no_credentials.jsonl` | no key for the provider | `prompt` response `success:false` |

## 1. Install

Commands: `npm view @earendil-works/pi-coding-agent version engines dist-tags`;
`npm install --prefix <scratch>/pi-prefix @earendil-works/pi-coding-agent@1.4.0`;
the image `Dockerfile` (`npm install -g --prefix /opt/pi ...@1.4.0 pi-web-access@0.46.0`).

Observed:
- Package `@earendil-works/pi-coding-agent`, `latest` = 1.4.0 (a
  `legacy-node20` tag points at 0.74.2). `engines.node` = `>=22.19.0`.
- Isolated prefix install works on Windows in 12 s: `node_modules` 139 MB, 215 MB
  with `pi-web-access`. Linux image: `/opt/pi` 250 MB, image 960 MB on
  `node:22-bookworm-slim` (+git, curl, ca-certificates).
- npm 11 (`allowScripts`) skipped two install scripts (`protobufjs` postinstall,
  `@google/genai` no-op preinstall); Pi and the web extension worked without them.
- Entry point: `<prefix>/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js`
  (`bin` `pi`; on Windows also `pi.cmd`/`pi.ps1` shims). The OAuth helper CLI is
  `.../node_modules/@earendil-works/pi-ai/dist/cli.js` (nested under Pi when
  installed globally).
- Pi ships its docs in the package (`docs/*.md`); they match 1.4.0 and were
  the reference for the **(code)** items.

Consequences:
- PI-02: the image installs exact versions with `npm install -g --prefix /opt/pi`
  on Node 22; start Pi as `node <cli.js>` (no shell shim). Image size is
  dominated by the Node base; Pi adds about 250 MB.
- PI-07: `npm install --prefix <adore-dir>` with exact versions works on both
  OSes; call `node <cli.js>` directly on Windows to avoid `.cmd` quoting.

## 2. RPC protocol

Command: `python rpc_probe.py --out ... --cwd <worktree> --prompt ... -- pi --mode rpc --no-session --no-approve --model <provider/id>`
(see the fixtures). Reference: Pi `docs/rpc.md`, `rpc-commands.md`, `json.md`.

Observed:
- Framing: one JSON object per LF-terminated line on stdin/stdout. Pi's docs
  require splitting on LF only (not U+2028/2029); the probe reads bytes.
- Prompt: `{"id":"x","type":"prompt","message":"..."}` -> response
  `{"id":"x","type":"response","command":"prompt","success":true,"data":{"disposition":"started"}}`
  within 0.3-0.8 s. `success:false` (with `error`) when the prompt cannot start,
  for example with no credential for the provider.
- Event sequence of one run (`run_tool_calls_chatgpt.jsonl`): `agent_start`,
  `turn_start`, `message_start/end` **role `system`** (new in 1.x: the full
  system prompt in `sections` `preamble`, `tools`, `rules`, `docs`, `cwd`, plus
  context files), `message_start/end` user, then per turn: assistant
  `message_start`, `message_update` deltas (`thinking_*`, `text_*`,
  `toolcall_start/delta/end`), assistant `message_end` (`stopReason`
  `toolUse`/`stop`/`error`, `usage`), `tool_execution_start/update/end`,
  `message_start/end` role `toolResult`, `turn_end`; finally `agent_end`
  (all messages of the run) and `agent_settled{"aborted":false}`.
- Completion: `agent_settled` is the only reliable end; `agent_end` can be
  followed by retries or compaction. Assistant `message_end` carries
  `stopReason`, `errorMessage`, `model`, `provider`, `responseId`, `durationMs`.
- Abort (`run_aborted_chatgpt.jsonl`): `{"type":"abort"}` while `bash sleep 30`
  ran -> the tool ended at once with `isError:true` "Command aborted", Pi
  emitted one more turn whose assistant message has `stopReason:"error"` and
  `errorMessage:"This operation was aborted"`, then `agent_settled{"aborted":true}`
  **before** the `abort` response; 12 ms from command to both.
- Errors after acceptance never produce a second response: they are an
  assistant `message_end` with `stopReason:"error"` and `errorMessage`
  (see Q10). Malformed JSON gets `{"type":"response","command":"parse","success":false}` **(docs)**.
- Exit: closing stdin requests shutdown; Pi exited 0 within about 0.3 s on
  Linux and on Windows with Node 22. Closing stdin **right after** writing
  commands made Pi exit without processing them (trust test): stdin must stay
  open until `agent_settled`.
- Stderr: free text, never protocol (`Warning: Model "x" not found for
  provider "y". Using custom model id.`; the Windows libuv assertion).
- Record sizes: `agent_end` up to 24 KB, `message_start/end` up to 11 KB,
  `tool_execution_end` up to 8 KB in these short runs; they grow with context
  and tool output.

Consequences for PI-02:
- Use one process per stage: `node cli.js --mode rpc --no-session --no-approve
  --no-skills --no-extensions -e <adore-guard> --model <provider>/<id>`, stdin
  held open, stdout read as bytes split on LF, stderr captured as diagnostics.
- Done = `agent_settled`; cancelled = `agent_settled.aborted == true` (not a
  stop reason); failed = last assistant `stopReason == "error"` (keep
  `errorMessage`). Do not use the exit code as the result (see Q9).
- Stage timeout or cancel: send `abort`, wait for `agent_settled` with a short
  grace, close stdin, then kill after a grace period.
- Bounded memory: keep only usage, tool names/status and the last assistant
  text; do not retain `agent_end.messages` or the system message.
- The fixtures are the replay source for a fake Pi: replay the `stdout`
  envelopes after the matching `stdin` command.

## 3. Usage and cost

Observed (`run_tool_calls_chatgpt.jsonl`, `failed_*`):
- Every assistant `message_end.message.usage` has `input`, `output`,
  `cacheRead`, `cacheWrite`, `reasoning`, `totalTokens` and
  `cost{input,output,cacheRead,cacheWrite,total}` (USD). `message_update` also
  carries the cumulative `usage` of the streaming message.
- `get_session_stats` -> `tokens{input,output,cacheRead,cacheWrite,total}`,
  `cost` (number), `toolCalls`, `assistantMessages`, `contextUsage{tokens,
  contextWindow,percent}`, `sessionId`; works with `--no-session`
  (`sessionFile` absent).
- Cost is Pi's **estimate** from its model catalog prices (Model object `cost`
  in USD per million tokens): ChatGPT-subscription runs report a non-zero cost
  (0.0006 USD) although nothing is billed per token; LM Studio reports 0
  unless `models.json` sets `cost`. Failed requests report zero usage.

Consequences: PI-02 records usage per assistant `message_end` into the usage
journal (one entry per turn) and cross-checks the total with
`get_session_stats` before closing stdin. The interface labels cost as
"estimated" and shows none (or "included in subscription") for ChatGPT.

## 4. Isolation

Commands: runs with `PI_CODING_AGENT_DIR=<scratch>`; `ls -la` of the agent
directory after each run; `find ~/.pi` before and after (identical); a
container test with `HOME` holding `~/.agents/skills/homeskill` (`home_test.sh`).

Observed:
- `PI_CODING_AGENT_DIR` relocates the whole agent directory (flag: none; SDK:
  `agentDir`). `PI_CODING_AGENT_SESSION_DIR`/`--session-dir` move sessions;
  `--no-session` writes none.
- `auth.json` is always `<agent-dir>/auth.json` **(code)**: no separate path in
  the CLI (`agent-session-services.js`, `auth-storage.js`). `models.json`,
  `settings.json`, `mcp.json`, `web-search.json` (pi-web-access),
  `AGENTS.md`/`SYSTEM.md`, `extensions/`, `skills/`, `prompts/` live there too.
- Pi writes into the agent directory on its own: `auth.json` (`{}` when absent,
  mode 0600) and `models-store.json` at every start; `settings.json` with a
  generated `deviceId` when the interactive login runs **(code)**.
- Read from outside the agent directory: `~/.agents/skills/` from `HOME`
  (observed: listed by `get_commands`; gone with `--no-skills`); context files
  `AGENTS.md`/`CLAUDE.md`/`AGENTS.override.md` from the working folder and its
  parents (observed in the system message for every trust setting; disabled
  with `--no-context-files`); project `.pi/` and `.agents/skills` only when
  trusted (Q5).
- Personal resources off: `--no-skills`, `--no-extensions` (also removes the
  built-in `llama` extension; explicit `-e` still loads), `--no-prompt-templates`,
  `--no-themes`, `--no-mcp`, `--no-context-files`.

Consequences: PI-02/PI-07 set `PI_CODING_AGENT_DIR` to an ADORE-owned folder,
`PI_OFFLINE=1`, `PI_TELEMETRY=0`, `PI_SKIP_VERSION_CHECK=1`, and pass
`--no-skills --no-extensions --no-prompt-templates --no-themes --no-mcp`. Keep
context files on (the project's `AGENTS.md` is the AEGIS contract). On the
server, also set `HOME` to an ADORE folder or rely on `--no-skills`.

## 5. Trust and extensions

Command: `trust_test.sh` (a project `.pi/extensions/project-ext.ts` that writes
a marker when loaded, a project skill and `AGENTS.md`, under four flag sets),
then a live run with `-e adore-guard.ts`.

Observed:

| Flags | Project extension | Project skill | `AGENTS.md` |
|---|---|---|---|
| none (default `defaultProjectTrust: "ask"`) | not loaded | not listed | loaded |
| `--no-approve` | not loaded | not listed | loaded |
| `--approve` | **loaded** | listed | loaded |
| `-e adore-guard.ts` (returns `project_trust: no`) | not loaded | not listed | loaded |

- RPC never prompts: with no flag the default `"ask"` means "skip".
  `--approve`/`--no-approve` are one-run overrides; a user-level or `-e`
  extension can decide through the `project_trust` event **(code, observed for "no")**.
- An explicit `-e <file.ts>` loads without trust and without compilation
  (Pi uses `jiti`), also together with `--no-extensions`.
- Guard (`run_guard_blocks_forge.jsonl`): a `tool_call` handler returning
  `{block:true, reason}` stopped `git push origin HEAD`, `gh pr list`,
  `glab mr list` and `tea issues` before execution; each still produced
  `tool_execution_start` and `tool_execution_end` with `isError:true` and the
  reason as result text; `echo allowed` ran. The handler sees `bash` and
  `powershell` tool calls.

Consequences: PI-02 always passes `--no-approve` and `-e <adore-guard.ts>`
(shipped in the image and the managed installation); the guard also answers
`project_trust` with "no". Blocked attempts can be counted from
`tool_execution_end` with the guard's reason. As planned, the guard is defence
in depth; the boundary stays "no forge credential in the agent environment".

## 6. Providers and `models.json`

Commands: `pi --help`; `docs/providers.md`; `pi --list-models <provider>`;
`models.json` runs against LM Studio natively and from a container
(`lm_container.sh`, `lmnet.sh`).

Observed:
- API-key providers and variables (Pi 1.4.0 `--help` and docs): Anthropic
  `ANTHROPIC_API_KEY`, OpenAI `OPENAI_API_KEY`, Google Gemini `GEMINI_API_KEY`,
  Mistral `MISTRAL_API_KEY`, Groq `GROQ_API_KEY`, Cerebras `CEREBRAS_API_KEY`,
  xAI `XAI_API_KEY`, OpenRouter `OPENROUTER_API_KEY`, DeepSeek
  `DEEPSEEK_API_KEY`, NVIDIA `NVIDIA_API_KEY`, Fireworks `FIREWORKS_API_KEY`,
  Together `TOGETHER_API_KEY`, Baseten `BASETEN_API_KEY`, Hugging Face
  `HF_TOKEN`, Vercel AI Gateway `AI_GATEWAY_API_KEY`, MiniMax
  `MINIMAX_API_KEY`/`MINIMAX_CN_API_KEY`, Moonshot `MOONSHOT_API_KEY`, Kimi
  `KIMI_API_KEY`, ZAI `ZAI_API_KEY`/`ZAI_CODING_CN_API_KEY`, OpenCode
  `OPENCODE_API_KEY`, Qwen `QWEN_TOKEN_PLAN_API_KEY`/`..._CN_...`, Xiaomi
  `XIAOMI_API_KEY` (+ token-plan variants), Meta `META_API_KEY`, Ant Ling
  `ANT_LING_API_KEY`, Radius `RADIUS_API_KEY`, GitHub Copilot
  `COPILOT_GITHUB_TOKEN`; multi-variable: Azure (`AZURE_OPENAI_API_KEY` +
  `AZURE_OPENAI_BASE_URL` or `..._RESOURCE_NAME`), Bedrock (AWS variables),
  Cloudflare (`CLOUDFLARE_API_KEY` + account/gateway ids), Vertex
  (`GOOGLE_CLOUD_API_KEY` or ADC).
- Key without a file: the provider's environment variable (observed:
  `OPENAI_API_KEY` reached OpenAI and was rejected as invalid) or
  `--api-key` (visible in the process list; not recommended). Precedence:
  `--api-key`, `auth.json`, `models.json` `apiKey`, environment **(code/docs)**.
  `pi auth check --provider openai` reports an env key as `ready` without a
  network call.
- `models.json` for an OpenAI-compatible endpoint (proven against LM Studio):

  ```json
  {"providers": {"lmstudio": {"baseUrl": "http://<host>:1234/v1",
    "api": "openai-completions", "apiKey": "lm-studio",
    "models": [{"id": "qwen/qwen3.5-9b", "contextWindow": 32768, "maxTokens": 4096}]}}}
  ```

  API types: `openai-completions`, `openai-responses`, `anthropic-messages`,
  `google-generative-ai` and others listed in `docs/models-configuration.md`.
  `apiKey`/headers accept a literal, `$VAR`/`${VAR}` or `!command`.
- `apiKey: "$LMSTUDIO_API_KEY"` with the variable unset makes the model
  **disappear** ("No models available"); a keyless endpoint needs a literal
  placeholder key.
- Native Windows run: 3 tool calls, `stop`, exit 0
  (`run_tool_calls_lmstudio_windows.jsonl`).
- From a container (WSL Docker Engine, NAT): `host.docker.internal` with
  `--add-host=host.docker.internal:host-gateway` reaches the **WSL VM**, not
  Windows (HTTP 000); the Windows host is reachable at the WSL default gateway
  (`172.27.80.1`, HTTP 200). Run through it: 6 tool executions, `stop`, exit 0.
- An unknown model id is not rejected by Pi (Q10).

Consequences for PI-04: the Pi provider ids above are the `provider` values;
keys reach Pi only as their environment variable; ADORE writes `models.json`
with a literal placeholder when the endpoint has no key, or `$VAR` plus the
variable when it has one. The base URL is the address **as seen from where
Pi runs**; the interface must say so (`host.docker.internal` is valid only on
Docker Desktop). ADORE validates the model id itself (Q10).

## 7. ChatGPT sign-in

Commands: `login.sh` (the bundled `pi-ai` CLI `login openai`, in a container
with no published port, stdin from a FIFO, the redirect URL read from a file
the owner wrote); `pi auth check|print-bearer-token`; `refresh_test.sh`
(two containers at once); `break_cred.sh`; `bearer_test.sh`.

Observed:
- "Sign in with ChatGPT" is Pi provider **`openai`** with OAuth
  (`openai-codex` is the legacy Codex-client flow). There is **no RPC command
  and no `pi` flag** for login (`pi auth` has only `print-api-key`,
  `print-bearer-token`, `check`). The TUI `/login` uses the same module as the
  bundled `pi-ai` CLI, which is scriptable over stdin/stdout:
  `node .../pi-ai/dist/cli.js login openai` prints the authorize URL and reads
  the pasted callback URL. Headless works: the browser's redirect to
  `http://127.0.0.1:1455/auth/callback?...` fails, the owner pastes it, the
  CLI exchanges the code (third attempt succeeded; the first two failed on a
  wrong paste and on an OAuth `state` from an earlier attempt, each a clear
  error with exit 1).
- The callback server binds `127.0.0.1:1455` (`PI_OAUTH_CALLBACK_HOST` changes
  the bind host only); a second concurrent login fails with "Port 1455 is in
  use" **(code)**. The login must be completed within the same process (PKCE
  verifier and `state` are in memory).
- Stored credential (`auth.json`, shape only): `openai: {type:"oauth",
  access:<JWT 2106 chars>, refresh:<196 chars>, expires:<ms, 1 h minus a 3-min
  margin>, clientId:<32 chars, issued per login>, scopes:[openid, profile,
  email, offline_access, resource.invoke, chatgpt.tokens.use.direct]}`. No
  e-mail and no host ID field; the access token's claims are `sub`, `aud`,
  `client_id`, `scope`, an encrypted metadata blob and standard JWT claims
  (no e-mail claim).
- Host ID: the authorize URL carries `ext_agent_host_id=urn:uuid:<deviceId>`.
  Interactive Pi persists `deviceId` in `<agent-dir>/settings.json`; the
  `pi-ai` dev CLI uses a random one per login and does not store it **(code)**.
- The `pi-ai` CLI wrote `auth.json` with mode **644** into its working folder
  (Pi's own store creates it 0600).
- Refresh: tokens **rotate** (new access and refresh token). Two containers
  started together on one mounted credential **directory**, token expired:
  both `ready`, one rotation; Pi re-reads `auth.json` under a
  `proper-lockfile` lock (`auth.json.lock` directory, 30 s stale) and skips
  the refresh when another process already refreshed **(code + observed)**.
- The lock is created next to the path **as given** (`realpath:false`): a
  single-file bind mount or a symlinked `auth.json` in a per-run agent
  directory does **not** share the lock **(code)**; concurrent refreshes would
  then race and the losing refresh token would be invalid.
- Failed refresh (`failed_refresh_chatgpt.jsonl`): the run ends with
  `stopReason:"error"`, `"OAuth refresh failed for openai: OpenAI OAuth token
  request failed (400): {"error":"invalid_grant"}"`; Pi keeps the dead
  credential on disk; no fallback to an environment key **(code)**.
- `pi auth check --provider openai --json`: exit 0 `ready`, exit 1
  `not_ready/credentials_not_configured`, exit 2 `invalid/invalid_state`
  (refreshes unless `--no-refresh`).
- Models: with ChatGPT sign-in `gpt-5.4-mini` and `gpt-5.5` are refused (400
  `model_not_found`, "not supported when using Codex with a ChatGPT account");
  `gpt-5.6-luna` works. `--list-models openai` lists the full API catalog
  regardless; the legacy `openai-codex` catalog lists only `gpt-5.6-*` and
  `gpt-6*` models.
- Access token as API key (`bearer_test.sh`): `pi auth print-bearer-token
  --provider openai --min-expiry 30m` (refreshes under the lock) returned the
  access token; a container with only `OPENAI_API_KEY=<access token>` and an
  empty agent directory completed a run (`stop`). The refresh token never
  entered that container.

Consequences for PI-05: drive the bundled `pi-ai` login (or call
`builtinProviders()` `openai` `auth.oauth.login` from a small ADORE-owned
Node script) from the web interface, keep the process alive until the owner
pastes the callback, validate `state` before submitting, persist a stable
`deviceId`, write `auth.json` 0600. Offer only models that work with ChatGPT.
Map "sign in again" to `pi auth check` exit 2 or `OAuth refresh failed` /
`invalid_grant`. See "Plan changes needed" 1 for how runs get the credential.

## 8. Web access (`pi-web-access`)

Commands: `npm view pi-web-access`; install into the prefix/image; README;
`web_test.sh` (LM Studio model in a container, `-e /opt/pi/lib/node_modules/pi-web-access`,
`web-search.json` = `{"provider":"exa","toolActivation":"eager","workflow":"none"}`;
once normal, once with `--dns 127.0.0.1`).

Observed:
- Pinned 0.46.0 (MIT, peer deps `*` on Pi packages, so it must be installed
  in the same prefix as the pinned Pi).
- Loading for headless runs: `-e <prefix>/node_modules/pi-web-access` (the
  package declares `pi.extensions: ["./dist"]`) loaded it in RPC with
  `--no-approve`; `pi install npm:pi-web-access` would instead write
  `settings.json` and install at runtime (not wanted).
- Config: `<PI_CODING_AGENT_DIR>/web-search.json` (else `XDG_CONFIG_HOME/pi/`
  or `~/.pi/agent/`). Keys `braveApiKey`, `tavilyApiKey`, `exaApiKey`, ... or
  environment variables `BRAVE_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`
  (environment wins); values may be `$VAR`. `provider`/`searchProvider` picks
  the default; `workflow` `none` (default, no curator browser);
  `toolActivation` `auto|dynamic|eager|none`.
- Keyless Exa (MCP) search worked (`web_search` -> results, "Provider: exa").
  With ChatGPT signed in, `auto` mode tries subscription-backed OpenAI search
  first **(docs)**.
- `fetch_content`: modes `readable` (default), `raw`, `answer`, `extract`
  (opt-in); `maxInlineContentChars` default 30 000 (1 000-200 000, the rest
  stored for `get_search_content`); `fetch.timeout` default 30 s; an SSRF
  guard blocks private and reserved IP ranges by default; GitHub URLs may use
  `gh` and clones (350 MB cap). Observed: readable mode refused a script-heavy
  page ("content may load dynamically") and suggested remote fallbacks; raw
  mode returned the HTML.
- Without network (DNS blocked, model reachable): tools fail fast and clearly
  (`getaddrinfo EAI_AGAIN`, `fetch failed`), but the model kept trying for 25
  tool calls before answering.
- Brave and Tavily with a key: **(not run)**, no key available; names from the
  README.

Consequences for PI-06: install `pi-web-access@0.46.0` next to Pi; load it
with `-e` only when internet is On; write `web-search.json` into the
ADORE-owned agent directory with `workflow: "none"`, `toolActivation:
"eager"`, `provider` from `[executor.web] search`, keys as `$VAR` with the
variable injected. With internet Off, do not load it at all (no tools to
thrash on).

## 9. Windows

Commands: native Windows runs with `node <cli.js>` (Node 24.18.0 and Node
22.23.4 from the scratch prefix), Git Bash, `--tools read,powershell,edit,write`.

Observed:
- Pi 1.4.0 runs natively: tool calls through Git Bash (`bash node test.js`
  -> `ok`) and the `powershell` tool (fell back to Windows PowerShell 5.1,
  `-NoProfile -NonInteractive -ExecutionPolicy Bypass`, no `pwsh` installed).
  Bash resolution: `shellPath` setting, `%ProgramFiles%\Git\bin\bash.exe`,
  `(x86)`, then `PATH` **(docs)**.
- **Node 24.18.0 crash on exit**: after a run that ended with a provider error,
  closing stdin ended Pi with `Assertion failed: !(handle->flags &
  UV_HANDLE_CLOSING), file src\win\async.c, line 94` and exit code
  3221226505 (`0xC0000409`) in 7 of 7 runs; after successful runs it exited 0.
  The same scenario on **Node 22.23.4 exited 0 in 3 of 3 runs**.
- Shell tools receive `PI_SESSION_ID`, `PI_PROVIDER`, `PI_MODEL`, ... and the
  markers `AI_AGENT=pi`, `PI_CODING_AGENT=true` **(docs)**.

Consequences for PI-07: pin Node 22 LTS (22.23.4) in the managed installation
on Windows (and Linux); launch `node.exe <cli.js>`; require Git for Windows
(or set `shellPath`); offer the `powershell` tool as an option. Never treat a
non-zero exit as the run result (Q2).

## 10. Failure modes

Commands: `rpc_probe.py` against a dummy OpenAI key, a fake endpoint
(`fake_provider.py`, 429 with `retry-after: 1`, or 500), a closed port, an
unknown model id, no credential, and `--network none`.

| Case | What ADORE sees | Exit |
|---|---|---|
| Invalid API key | `prompt` ok; assistant `stopReason:"error"`, `errorMessage` "OpenAI API error (401): ... Incorrect API key provided: sk-inval****0000 ..."; no retry | 0 (Node 24 Windows: `0xC0000409`) |
| No credential for provider | `prompt` response `success:false`, `error` "No API key found for openai. Use /login ..." | 0 |
| Unknown model id | stderr warning "Model ... not found ... Using custom model id."; the provider decides: OpenAI with the dummy key answered 401 before checking the model, ChatGPT 400 `model_not_found`, **LM Studio answers with the loaded model** (`stop`) | 0 |
| Rate limit (429) | `auto_retry_start{attempt,maxAttempts:3,delayMs,errorMessage}` x3, `auto_retry_end{success:false,finalError}`, `entry_appended`, then `stopReason:"error"` "429: ..." | 0 |
| Server error (500) | same retry pattern, "500: ..." | 0 |
| Unreachable endpoint / no network | same retry pattern, `errorMessage` "Connection error." | 0 |
| ChatGPT refresh fails | `stopReason:"error"`, "OAuth refresh failed for openai: ... invalid_grant" | 0 |
| Model not allowed for ChatGPT | `stopReason:"error"`, 400 `model_not_found` | 0 |
| Abort | `agent_settled{aborted:true}`; last assistant `stopReason:"error"` "This operation was aborted" | 0 |

Retry defaults: `retry.maxRetries` 3, `baseDelayMs` 2000 (exponential),
`maxAgentDelayMs` 60 000; provider-level retries 0 **(docs)**. Provider error
texts can contain a masked key (`sk-inval****0000`).

Consequences for PI-02: classify from the last assistant `errorMessage`
(401/403 -> credential, `invalid_grant`/"OAuth refresh failed" -> sign in
again, 429 -> rate limit, `model_not_found`/404 -> model, "Connection error."
-> endpoint/network) and from a `prompt` response with `success:false`;
redact `sk-...****...` hints and key values before persisting messages; bound
the wall clock (retries add up to about 14 s by default). PI-04 validates the
model id against `get_available_models` or its own list.

## Plan changes needed

1. **ChatGPT credential reaches runs as a short-lived access token, not a
   mount (PLAN 4.3) - contradicts a plan decision, owner to decide.** The plan
   says the credential "is used in place (mounted into containers), never
   copied, so Pi's own lock serializes token refreshes". Pi only reads
   `<agent-dir>/auth.json`, and its lock is created next to that path. The
   lock is therefore shared only if the ChatGPT credential directory itself
   is the agent directory of every run. That directory would then also hold
   `models.json`, `web-search.json` and `models-store.json`, which ADORE
   writes per project. A single-file or symlink mount would break the lock,
   and refresh tokens rotate. The spike proved an alternative: ADORE keeps
   the credential in one host directory, refreshes it there with
   `pi auth print-bearer-token --provider openai --min-expiry <stage timeout>`
   (Pi's lock still serializes this), and gives each run only
   `OPENAI_API_KEY=<access token>` (valid up to about 1 h). The refresh token
   never enters a container. A stage longer than the token's lifetime would
   fail with 401.
2. **ChatGPT models (PLAN 4.2 example):** with a ChatGPT subscription only
   some models work (`gpt-5.6-luna` yes; `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`
   no). The example `model = "gpt-5.4"` is valid for an API key but not for
   `provider = "chatgpt"`. PI-04/PI-05 need a ChatGPT model list. `chatgpt` is
   an ADORE-level choice: in Pi it is provider `openai` with OAuth.
3. **Endpoint address from containers (PLAN 4.2 example):**
   `http://host.docker.internal:1234/v1` works only on Docker Desktop. On a
   WSL or Linux Docker Engine it reaches the Docker host, not Windows, so the
   example and the help must say "the address as seen from the container".
4. **Node pin (PLAN 4.5):** pin Node 22 LTS (22.23.4) for the managed
   installation; Node 24.18 crashes on exit on Windows after failed runs.
5. **Internet Off (PLAN 4.4):** do not load `pi-web-access` when internet is
   Off. The plan says what the switch maps to for egress but not for the
   extension.
6. **Isolation flags (PLAN 4.1/4.5):** besides the ADORE agent directory, runs
   need `--no-skills` (Pi reads `~/.agents/skills` from `HOME`),
   `--no-extensions` (built-in `llama` extension), `--no-prompt-templates`,
   `--no-themes`, `--no-mcp`, `--no-approve`, and `PI_OFFLINE=1`.

Items 2-6 refine the plan without changing a decision. Item 1 changes a
decision; asked on 2026-11-01, the owner chose to **decide it in PI-05**:
PI-05 brings both options (mount the credential directory as each run's agent
directory, or a per-run access token) back to the owner before implementing.
PLAN.md is unchanged.
