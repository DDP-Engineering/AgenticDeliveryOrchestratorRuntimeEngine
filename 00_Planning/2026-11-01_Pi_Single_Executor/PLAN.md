<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Pi as ADORE's single coding agent

Date: 2026-11-01. Status: approved by the owner for ticketing on 2026-11-01;
owner decisions recorded in section 11.
Baseline: branch `task/adore-web-interface` at `946757e` (11 commits ahead of
`origin` when this plan was written). Line numbers below refer to that commit
and will drift.

## 1. Decision

ADORE keeps exactly one coding agent: **Pi** (`@earendil-works/pi-coding-agent`,
MIT, repository `earendil-works/pi`). OpenCode, Codex and Qwen Code support is
removed.

- ADORE drives Pi through its **RPC mode** (`pi --mode rpc --no-session`, JSON
  lines over stdin/stdout), one fresh process per stage. The TypeScript SDK is
  not used; it stays an option for later (own tools, in-memory credentials).
- Pi and its web extension are **pinned and shipped by ADORE**: in the executor
  image, and in an ADORE-managed installation when Pi runs on the server.
- The user configures only: **provider and model**, an **API key** or a
  **ChatGPT sign-in** (or an OpenAI-compatible endpoint such as LM Studio,
  Ollama or vLLM), **internet access on/off**, and **where it runs**.
- Internally ADORE keeps its executor interface with this one implementation,
  so a vendor agent can be added later without exposing a choice to users.

## 2. Why Pi

Requirements: implement code headlessly; API keys for many providers including
local OpenAI-compatible servers; OpenAI (ChatGPT) subscription sign-in; web
search, page reading and downloads; simple and stable to integrate from Python.

| Criterion | Pi | OpenCode (runner-up) |
|---|---|---|
| API keys and local servers | 33 key providers; `models.json` for OpenAI-compatible endpoints | 75+ providers; `baseURL` |
| ChatGPT subscription | Official "Sign in with ChatGPT" since 0.99.0, works on a headless server (paste the redirect URL) | Official flow only in v2; v1 has only the legacy Codex-client flow |
| Web search and reading | Through the `pi-web-access` extension (Exa needs no key) or MCP | Built-in `webfetch`/`websearch` |
| Downloads | `bash` (`curl`, package managers) | `bash` |
| Integration from Python | RPC documented, with a Python client example; JSON output versioned (session v3) with usage and cost | `run --format json` documented only by third parties; HTTP API changed in v2; no Python SDK |
| Stability (2026-11) | 1.x since 2026-10-01; SDK changed after 1.0, CLI/RPC protocols documented | v1 and v2 lines in parallel; v2.2.0-2.2.5 broke APIs within days |
| Permissions | None; the container is the boundary | Present, but its own SECURITY.md says they are not isolation |

Quality: Terminal-Bench results show that the model matters more than the
harness; with Claude and Gemini models generic harnesses land within a few
points of the vendor CLIs, while Codex CLI leads on GPT-5.x models (5-29 points
against Terminus 2; no published OpenCode or Pi runs with GPT-5.x). Choosing Pi
over OpenCode is not expected to change implementation quality.

Not possible with any single third-party agent: Claude Pro/Max subscriptions
(Anthropic allows them only in its unmodified Claude Code binary) and Google
consumer plans (prohibited and enforced). Claude models remain usable with an
API key.

## 3. Target user experience

Settings -> Agent and model (and step 2 of enrollment) shows:

1. **Provider**: a Pi provider with an API key, "ChatGPT subscription", or
   "OpenAI-compatible endpoint".
2. **Model**: chosen from the provider's models, free text allowed.
3. **Credential**: the API key (stored in the project's credential store), the
   ChatGPT sign-in status, or for an endpoint its base URL, API type and
   optional key.
4. **Internet access for the agent**: Off (only the model provider is
   reachable) or On (web search, page reading, package downloads).
5. **Where it runs**: container (default) or installed on the server.

Launch command, flags, image contents and Pi version are not user-editable.

## 4. Target design

### 4.1 Runtime

Per stage ADORE starts `pi --mode rpc --no-session` in the worktree with an
ADORE-owned Pi agent directory and the provider credential in its environment,
sends the stage prompt, streams events with bounded memory, records usage per
turn into the versioned usage journal, and sends `abort` on stage timeout or a
cancellation marker, then terminates the process after a grace period. Stage
results are still read from AEGIS, as today. The push/forge guard is an
ADORE-owned Pi extension loaded explicitly, so it does not depend on project
trust; the real protection stays that no forge credential enters the agent's
environment.

### 4.2 Configuration schema (target; PI-01 confirms Pi's names)

```toml
[executor]
provider = "openai"        # a Pi API-key provider id, "chatgpt" or "custom"
model = "gpt-5.4"
internet = false           # false: model provider only; true: open network

[executor.endpoint]        # only when provider = "custom"
base_url = "http://host.docker.internal:1234/v1"
api = "openai-completions" # Pi API type for the endpoint

[executor.web]
search = "exa"             # exa (no key) | brave | tavily | none
```

API keys never appear in `config.toml`: they live in the project's credential
store and reach Pi as the environment variable Pi defines for the provider.
For `custom`, ADORE writes Pi's `models.json` into the ADORE-owned agent
directory. Keys of the removed executors are refused (no migration).

### 4.3 Credentials

- API keys: per project, existing credential store, injected per process.
- ChatGPT: one credential per ADORE host, in an ADORE-owned directory, signed in
  from the web interface (Pi's official OpenAI flow, redirect URL pasted back).
  It is used in place (mounted into containers), never copied, so Pi's own lock
  serializes token refreshes. Disconnect deletes it. The legacy Codex-client
  flow is not offered. Today's host sign-in copying is removed.
- Forge credentials never reach the agent (unchanged).

### 4.4 Internet access and web tools

`internet = false` maps to the container egress allowlist with the provider's
host (or the custom endpoint's host) derived by ADORE; `true` maps to open
egress. Web search and page reading come from the pinned `pi-web-access`
extension, configured by ADORE (Exa without a key by default, optional Brave or
Tavily key). Downloads use `bash` (`curl`, `npm`, `pip`). On a server-installed
run the switch cannot be enforced and the interface says so.

### 4.5 Pi installed on the server

ADORE installs the pinned Pi into its own prefix with a Node version that meets
Pi's minimum, never uses a global Pi or the account's `~/.pi`, and isolates the
agent directory. Linux and Windows are supported. Because Pi has no permission
prompts, the interface recommends a dedicated OS account.

### 4.6 Security model

The container is the isolation boundary. No forge credentials in the agent
environment; draft-only publication after human approval. With internet On, a
malicious page can try to make the agent send the API key or the mounted
ChatGPT credential out; the interface warns, and limited or short-lived keys
are recommended.

## 5. What is removed (inventory at 946757e)

About 900 lines exist only because of multiple executors and about 580 only
for OpenCode (custom endpoint, model catalogue, local configuration isolation).

- `04_Software/adore/executor/launcher.py`: OpenCode (367-430), Codex (515-599),
  Qwen (602-625) classes and the selector (628-654); Pi (433-512) is rewritten.
- Presets written three times: `adore/web/executor_configuration.py:16-27`,
  `adore/wizard.py:57-65` and `745-762`, `config.example.toml:156-192`.
- `adore/config.py`: per-executor validation (1002-1058), OpenCode endpoint
  (1186-1210), default executor (279).
- `adore/web/model_connection.py`: per-executor probes and parsers.
- Host sign-in staging: `adore/orchestrator.py:111-112, 235-237, 2870-2873,
  3019-3044`; `adore/execution.py:166-173`; `adore/branding.py:41-42`;
  `adore/web/executor_settings.py:186-217` (and its provider key list 28-41).
- `adore/local_execution.py`: OpenCode isolation (94-108, 160-204, 358-365),
  Codex/Pi homes (66-67, 214-215), sign-in paths (568-579).
- OpenCode-only modules: `adore/web/endpoint_probe.py`,
  `adore/opencode_catalogue.py`; endpoint editing in `adore/web/app.py`
  (1243-1337, 1579-1592, 3502-3515, 3689-3715); readiness (654-692);
  `adore/doctor.py` (50, 162, 574).
- Image: `04_Software/docker/Dockerfile.executor-base`,
  `04_Software/docker/verify-runtime.sh:268-272`.
- Web: `executorSettings.ts`, `ExecutorCredentials.tsx`, `EnrollmentWizard.tsx`,
  `serverImages.ts`, `App.tsx`, `settings.ts`, `settingHelp.ts`, `i18n.ts`.
- Tests: about 150 test functions, including `test_model_connection.py`,
  `test_local_execution.py`, `test_web_executor_configuration.py`,
  `test_web_launch_presets.py`, `web/e2e/executor-config.spec.ts`,
  `web/tests/settings.test.mjs`.
- Documentation: help (`executors.md`, `glossary.md`, `projects.md` in four
  locales), about 10 files in `01_Documentation`, 10 in `05_SoftwareDocu`, 6 in
  `.agentic/knowledge`, 11 requirements.

## 6. Delivery plan

Every ticket is written for an agentic implementation (Claude Code or Codex)
and is one AEGIS task. Epic: [#50](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/50). Sources and catalog: `Gitea_Issues/`.

| ID | Gitea | Ticket | Depends on | Priority | Effort |
|---|---|---|---|---|---|
| PI-01 | [#51](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/51) | Spike: confirm Pi 1.x headless contracts | - | P1 | 2-3 days (owner present) |
| PI-02 | [#52](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/52) | Run Pi through its RPC mode in the executor image | PI-01 | P1 | 3-5 days |
| PI-03 | [#53](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/53) | Remove OpenCode, Codex and Qwen Code | PI-02 | P1 | 3-4 days |
| PI-04 | [#54](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/54) | Provider, model, API key and OpenAI-compatible endpoint setup | PI-03 | P1 | 4-6 days |
| PI-05 | [#55](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/55) | Sign in with ChatGPT from the web interface | PI-04 | P1 | 4-6 days |
| PI-06 | [#56](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/56) | Web search, page reading and downloads behind an internet switch | PI-02, PI-04 | P2 | 3-5 days |
| PI-07 | [#57](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/57) | Pi installed on the server through an ADORE-managed installation | PI-02, PI-03 | P2 | 3-5 days |
| PI-08 | [#58](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/58) | Live acceptance, documentation audit and backlog cleanup | PI-03 to PI-07 | P1 | 2-3 days (owner present) |

Total about 5-7 weeks. PI-06 and PI-07 can run in parallel with PI-05.
Between PI-03 and PI-04 local endpoints (LM Studio) are not configurable; that
is acceptable while ADORE is in development.

## 7. Rules for every ticket

- Read `AGENTS.md` (authoritative; Claude Code also reads `CLAUDE.md`) and
  `.agentic/AGENTS.md`; implement the ticket as one AEGIS task.
- This plan and `SPIKE_FINDINGS.md` (written by PI-01) are the reference. When
  a ticket conflicts with them, or a decision turns out impossible, stop and
  ask the owner.
- No migrations or compatibility with earlier builds: refuse old data and keys
  with a message naming what to delete or fix.
- User-visible change: `CHANGELOG.md` and the four-locale
  `04_Software/adore/release_notes.toml`. Interface or workflow change: help in
  `04_Software/web/src/help/content/` (en, fr, de, ro).
- Offline tests only: fake Pi processes, no provider calls, no real keys.
- LF line endings; keep license headers.
- Work on branch `task/adore-web-interface`.
- `git commit -s`, no AI co-author trailers, never merge into master, push only
  when asked.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pi depends on one company (Earendil, since 2026-04-08); license could change in future versions | Pin versions; upgrade only with ADORE releases; keep the executor interface |
| Pi APIs changed after 1.0 | Use the documented RPC protocol, not the SDK; record events from PI-01 as test fixtures |
| No permission prompts in Pi | Container by default; explicit guard extension; dedicated account on the server |
| `pi-web-access` is a third-party extension | Pin it; MCP-based search as fallback |
| ChatGPT refresh fails after idle (`invalid_grant`, open upstream bug) | Clear "sign in again" state; one credential per host, never copied |
| OpenAI terms for hosted or paid products | If ADORE is offered that way, submit OpenAI's interest form first |
| Quality on GPT-5.x lower than Codex CLI | Accepted; revisit if most users run OpenAI models |

## 9. Revisit triggers

- GitHub Copilot becomes a requirement (officially supported only in OpenCode).
- Claude subscriptions are needed (Claude Code as a second, internal executor).
- Pi changes license or ownership terms, or breaks its RPC protocol.
- OpenCode v2 stabilizes and its web tools or permissions become decisive.

## 10. Effect on existing tickets

Closed as superseded on 2026-11-01, each with a comment naming its replacement:

- by PI-03 (#53): #43 (remove Qwen), #45 (Codex AGENTS.md), #46 (OpenCode local
  gaps), #33 (`OPENCODE_CONFIG_CONTENT` validation);
- by PI-07 (#57): #44 (Pi personal configuration), #32 (Windows local executor
  path);
- by PI-02 (#52): #34 (token usage parsed from truncated output).

Still open and related to PI-06: #26 (adaptive dependency installation).

## 11. Owner decisions (2026-11-01)

1. Internet access for the agent is **Off** by default.
2. **One ChatGPT credential per server**, shared by the projects that choose the
   ChatGPT subscription.
3. **Windows** support for server-installed Pi is in scope **now**, with Linux.
4. ADORE is a **free** product for the moment, so OpenAI's interest form for
   hosted or paid products does not apply; revisit if that changes.
5. The work happens on the **same branch**, `task/adore-web-interface`.

## 12. Sources (read 2026-11-01)

- Pi: https://github.com/earendil-works/pi (docs `sdk.md`, `rpc.md`, `json.md`,
  `providers.md`, `security.md`, CHANGELOG 0.99.0, 1.0.3, 1.2.0)
- Pi web extension: https://github.com/nicobailon/pi-web-access
- Sign in with ChatGPT: https://developers.openai.com/siwc/token-sharing-open-source
- ChatGPT refresh bug: https://github.com/openai/sign-in-with-chatgpt-devkit/issues/5
- OpenCode releases: https://github.com/anomalyco/opencode/releases
- Anthropic terms: https://code.claude.com/docs/en/legal-and-compliance
- Terminal-Bench 2.1: https://www.tbench.ai/news/terminal-bench-2-1
- Terminal-Bench 2.0 paper: https://arxiv.org/html/2601.11868v1
