# TASK-5ceed61e - Pi provider, model, API key and OpenAI-compatible endpoint setup (PI-04, #54)

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-f5f4896f, REQ-FUNC-ae32f094, REQ-SEC-52b11734, REQ-FUNC-ae57faed, REQ-FUNC-f60cd4e1, REQ-FUNC-75711382, REQ-UX-e47cb172, REQ-FUNC-9110e185, REQ-FUNC-e346ccbd, REQ-FUNC-af2a8db8, REQ-FUNC-86cb2899, REQ-FUNC-2ed827bf, REQ-SEC-3d5fe8a6, REQ-FUNC-7ab1a48e, REQ-FUNC-de028c15, REQ-SEC-1c210f3f, REQ-FUNC-08cc2676, REQ-FUNC-8f369d55
parent:
branch: task/adore-web-interface
base: b6379b3c19d0c6cc5cd400df0a67d41e943ff4f4
opened: 2026-11-02

Edit Frame, Requirement coverage and Design directly. Write State, Log and
Rulings with `python .agentic/aegis.py` (advance, pause, log, ruling, verdict);
end each session with `advance` or `pause`.

## Done checklist (current stage)

- [ ] diff reviewed against scope, requirements, design, error paths,
      portability, security and unrequested work
- [ ] knowledge pages of changed components current with the reviewed code
- [ ] project and environment context reconciled with the candidate
- [ ] requirements re-read: status, prose, verification, paths and links true
- [ ] manual or inspection verification recorded where applicable
- [ ] explicit review approved, when enabled
- [ ] final `check --strict --run` result logged truthfully after the last edit
- [ ] remaining warnings and pre-existing failures explained
- [ ] `report` appended

## Frame

Problem: After PI-03 a project configures only `[executor] model` (provider/model
form) plus a names-only `env_keys` list; there is no provider choice, no
OpenAI-compatible endpoint (LM Studio, Ollama, vLLM) and the container Test AI
connection still runs `pi -p` instead of RPC (OBSERVED `adore/config.py`
ExecutorConfig, `adore/web/model_connection.py` `_RUNNER`; PLAN.md section 6
"between PI-03 and PI-04 local endpoints are not configurable").
Desired outcome: an administrator configures provider, model and credential (an
API key for one of Pi's providers, or an OpenAI-compatible endpoint); "Test AI
connection" proves it over RPC; the ChatGPT option appears and is completed in
PI-05 (STATED ticket #54 Goal).
Actors: administrator (Settings -> Agent and model, enrollment step 2), operator
(config.toml, CLI wizard), the orchestrator launching Pi per stage.
Primary scenario: Settings -> Agent and model: choose provider "OpenAI", model
"gpt-5.4" (from Pi's list or typed), Prepare change, review, apply; save the
API key (stored in the project credential store as OPENAI_API_KEY); Test AI
connection -> ready. Endpoint variant: provider "OpenAI-compatible endpoint",
base URL as seen from the container, API type, optional key.
Examples: `provider = "custom"` with `[executor.endpoint] base_url =
"http://192.168.1.20:1234/v1"`, `api = "openai-completions"` produces
`{"providers": {"adore-endpoint": {"baseUrl": ..., "api": ..., "apiKey":
"adore-no-key", "models": [{"id": "qwen/qwen3.5-9b"}]}}}` (OBSERVED live check
2026-11-02 against Pi 1.4.0 and a fake endpoint: completed, key reached the
endpoint as Bearer when `$ADORE_ENDPOINT_API_KEY` was set). `[executor]
api_key = "sk-..."` -> refused naming `api_key`.
Counterexamples: `[executor.endpoint]` with `provider = "openai"` is refused (the
table exists only for custom; STATED PLAN.md 4.2 comment).
In scope: ticket Scope (schema and validation, Settings, enrollment step 2,
credential wiring, models.json, RPC Test AI connection with distinct errors,
container access documentation) plus the CLI wizard that web enrollment runs.
Out of scope: ChatGPT sign-in and its model list (PI-05), internet switch and
`[executor.web]` (PI-06), server install and native RPC (PI-07) (STATED ticket Out).
Constraints: keys only in the credential store, never config.toml/logs/audit/API
responses/browser; no migrations; offline tests with fake Pi; LF; license
headers; `git commit -s` without AI trailers (STATED ticket, AGENTS.md).
Success signals: ticket acceptance criteria; the listed suites green.
Evidence: PLAN.md 4.2/4.3; SPIKE_FINDINGS.md Q6, Q10, Plan changes 2 and 3;
Pi 1.4.0 `docs/providers.md` table; `pi --list-models` with PI_OFFLINE=1
(OBSERVED: lists a provider's catalog when its variable holds any value, none
without; no network needed).
Assumptions: Pi 1.4.0 stays the pinned version (PI-02 Dockerfile).
Unknowns: none blocking. Stop conditions checked: every listed provider takes
its key from one environment variable, and the model list is read from the
pinned Pi offline (OBSERVED, see Evidence).
Decision-blocking questions: none; the ticket's Decisions stand.
Proposed behaviors: accepted by the ticket Decisions; design choices below.
Path and reason: full.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | provider/endpoint settings, new probe reasons |
| no new interface or data format | no | `[executor] provider`, `[executor.endpoint]`, models.json, catalog endpoint |
| no new dependency | yes | stdlib and existing web stack only |
| an existing requirement already covers the behavior | no | new behaviors |
| no security or data-handling change | no | new credential variable per provider |

## Requirement coverage

| Behavior | Requirement | Status |
|---|---|---|
| Schema: provider/model/endpoint validated, unknown keys refused by name | REQ-FUNC-f5f4896f | created |
| Custom endpoint refused for a local run | REQ-FUNC-7ab1a48e | created |
| Providers and models offered from the pinned Pi catalog, free text allowed | REQ-FUNC-ae32f094 | created |
| Provider key reaches Pi only as its environment variable | REQ-SEC-52b11734 | created |
| models.json written for a custom endpoint | REQ-FUNC-ae57faed | created |
| `--provider`/`--model` on every launch | REQ-FUNC-f60cd4e1 | created |
| Provider, model and endpoint reviewed and applied as one change | REQ-FUNC-75711382 | created |
| Settings and enrollment fields with help in four locales | REQ-UX-e47cb172 | created |
| Test AI connection ready over RPC (reply + shell nonce) | REQ-FUNC-9110e185 | created |
| Test AI connection: invalid key | REQ-FUNC-e346ccbd | created |
| Test AI connection: unreachable endpoint | REQ-FUNC-af2a8db8 | created |
| Test AI connection: unknown model | REQ-FUNC-86cb2899 | created |
| Test AI connection: missing credential | REQ-FUNC-2ed827bf | created |
| Keys never in config.toml, logs, audit, API responses, browser | REQ-SEC-3d5fe8a6 | created |
| Container Test AI connection runs over RPC | REQ-FUNC-de028c15 | revised |
| Credential lifecycle follows the configured provider's variable | REQ-SEC-1c210f3f | revised |
| env_keys are additional names besides the provider variable | REQ-FUNC-08cc2676 | revised |
| Native shell-call challenge (container now RPC) | REQ-FUNC-8f369d55 | revised |

## Design

**Catalog (RULING-001).** `02_Tools/generate_pi_catalog.py` runs the pinned Pi
offline (`--list-models`, `PI_OFFLINE=1`, a placeholder in one provider variable
at a time, variables from Pi's `docs/providers.md` table) and writes
`04_Software/adore/pi_catalog.json` (`pi_version`, providers `id`, `name`,
`variable`, `models`). `adore/pi_providers.py` loads it (corrupt -> error) and
owns the provider rules: `CHATGPT = "chatgpt"` (Pi provider `openai`, no key
variable until PI-05), `CUSTOM = "custom"` (Pi provider `adore-endpoint`, key
variable `ADORE_ENDPOINT_API_KEY`, optional), endpoint API types
`openai-completions`, `openai-responses`, `anthropic-messages`,
`google-generative-ai`, `credential_variable()`, `pi_provider()`,
`models_json(config, has_key)` and `secret_names(config)` = env_keys plus the
provider variable. GitHub Copilot and TypeSafe are excluded by the generator.

**Schema.** `ExecutorConfig` gains `provider = ""` and `endpoint:
ExecutorEndpointConfig(base_url = "", api = "openai-completions")`; `env_keys`
defaults to `[]` (additional names). Validation: provider required and known;
model required, no whitespace/control characters, at most 200 characters;
`[executor.endpoint]` present in the file exactly when custom (the loader keeps
whether the table was given); base_url http/https with host, no user info,
query or fragment; api in the closed set; custom with backend local refused.
Unknown keys are refused by the existing `_unknown_key_issues` (nested table
included).

**Launch.** `build_executor(command, model, questions_file, provider=...,
endpoint=...)`; `PiExecutor` passes `--provider <pi provider> --model <id>` on
RPC and `{model}` = `<pi provider>/<id>` on the native template. For custom,
before spawning, it writes `io/pi-models.json` (host side) and runs `cp` through
the exec seam into `CONTAINER_PI_AGENT_DIR/models.json`; a failed copy fails
the gate without starting Pi. `has_key` comes from the run's secret
environment (orchestrator) / probe environment.

**Credentials.** The orchestrator, local execution, preparation and the probe
use `secret_names(config)` instead of `env_keys`. `executor_settings`:
`credential_view` returns only the configured provider's variable (none for
chatgpt); `update_credential` accepts only that variable; `credential_binding`
covers `secret_names`. Values stay in the profile `.env` (0600).

**Test AI connection (container).** Pre-check: model id, credential present
(else `credential-missing`, no container). Provision the temporary container as
today, write models.json for custom, then `run_pi_rpc` through
`ContainerManager.spawn` (injectable `popen`) with the shell+reply challenge,
60 s bound. Map: completed -> shell nonce + exact reply check (`ready`,
`tool-call-failed`, `invalid-response`); failure class credential/sign-in ->
`credential-invalid`, model -> `model-unavailable`, network ->
`connection-failed`, rate-limit -> `rate-limited`, provider -> `provider-error`;
timed-out -> `timeout`; protocol exit 126/127 -> `cli-missing`, other ->
`invalid-response`. Native path unchanged apart from provider/model.

**Web.** `GET /api/v1/pi-providers` (authenticated) returns the catalog plus the
chatgpt/custom entries. A virtual edit key `executor.connection` (strict JSON
`{provider, model, base_url, api}`) rewrites `[executor] provider/model` and
adds/replaces/removes `[executor.endpoint]` atomically
(`executor_configuration.py`, precedent: the retired `executor.selection`);
settings metadata maps `executor.provider`, `executor.model` and
`executor.endpoint.*` rows to that edit key; review shows the object
field-by-field. Frontend: `AgentConnectionEditor.tsx` (provider select, model
input with datalist, endpoint URL/API when custom, ChatGPT note);
`ExecutorCredentials` accepts any server-named variable; enrollment step 2 adds
provider/model/endpoint fields (no secrets; the help names the variable to save
after creation). New reasons in `modelEvidence.ts`. CLI wizard asks provider
(+ endpoint) and model.

**Rejected.** Running Pi in a container at settings time for the list (needs a
runtime and an image in Settings; same data as the pinned snapshot). Mounting
models.json at provision (warm containers would keep a stale file and it needs
a new mount contract). Taking the API key during enrollment (breaks the
existing no-secrets enrollment contract; the store exists only after creation).

## Log

- 2026-11-02 frame: journal opened
- 2026-11-02 frame: interaction set to autopilot: delegated ticket session (PI-04) whose Decisions are the owner's; same mode as PI-02/PI-03
- 2026-11-02 frame: completed; next specify - scope recorded (autopilot) (7 Done checklist item(s) left unticked)
- 2026-11-02 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-02 design: completed; next build - design recorded (autopilot) (6 Done checklist item(s) left unticked)
- 2026-11-02 build: red: uv run python -m pytest tests/test_pi_providers.py exit 1 - 20 failed: no [executor] provider/endpoint schema, no secret_names/models_json behavior (REQ-FUNC-f5f4896f, REQ-FUNC-7ab1a48e, REQ-FUNC-ae32f094, REQ-SEC-52b11734, REQ-FUNC-ae57faed)
- 2026-11-02 build: green: uv run python -m pytest tests/test_pi_providers.py tests/test_config.py exit 0 (REQ-FUNC-f5f4896f, REQ-FUNC-7ab1a48e; catalog/secret_names/models_json helpers for REQ-FUNC-ae32f094, REQ-SEC-52b11734, REQ-FUNC-ae57faed)
- 2026-11-02 build: red: uv run python -m pytest tests/test_pi_rpc.py -k provider/models_json/native exit 1 - PiExecutor has no provider/models (REQ-FUNC-f60cd4e1, REQ-FUNC-ae57faed)
- 2026-11-02 build: red: uv run python -m pytest tests/test_model_connection.py exit 1 - 16 failed: probe still runs pi -p, no RPC/popen seam, no credential-missing/rate-limited reasons, no models.json (REQ-FUNC-9110e185, REQ-FUNC-e346ccbd, REQ-FUNC-af2a8db8, REQ-FUNC-86cb2899, REQ-FUNC-2ed827bf, REQ-FUNC-de028c15, REQ-FUNC-ae57faed, REQ-SEC-52b11734)
- 2026-11-02 build: green: uv run python -m pytest tests/test_model_connection.py tests/test_pi_rpc.py tests/test_pi_providers.py exit 0, 77 passed (REQ-FUNC-9110e185, REQ-FUNC-e346ccbd, REQ-FUNC-af2a8db8, REQ-FUNC-86cb2899, REQ-FUNC-2ed827bf, REQ-FUNC-de028c15, REQ-FUNC-f60cd4e1, REQ-FUNC-ae57faed, REQ-SEC-52b11734)
- 2026-11-02 build: red: uv run python -m pytest tests/test_web_executor_configuration.py exit 1 - no executor.connection edit and no /api/v1/pi-providers (REQ-FUNC-75711382, REQ-FUNC-ae32f094)
- 2026-11-02 build: green: uv run python -m pytest tests/test_web_executor_configuration.py tests/test_web_pending_config.py tests/test_web_setting_catalog.py tests/test_executor_settings.py tests/test_web_config.py exit 0 (REQ-FUNC-75711382, REQ-FUNC-ae32f094, REQ-SEC-1c210f3f)
- 2026-11-02 build: DEVIATION build: tests/test_executor_settings.py credential-follows-provider and key-never-leaves tests were written after the executor_settings rewiring, so no red run was recorded - accepted: both are green now and cover REQ-SEC-1c210f3f and REQ-SEC-3d5fe8a6 end to end through the API
- 2026-11-02 build: green: uv run python -m pytest tests/test_executor_settings.py exit 0, 25 passed (REQ-SEC-1c210f3f, REQ-SEC-3d5fe8a6)
- 2026-11-02 build: DEVIATION build: web unit tests (tests/agentConnection.test.mjs) were written after the TypeScript modules, no red run recorded - accepted: they pin the transport, copy parity and guidance contracts; Playwright specs below exercise the UI
- 2026-11-02 build: green: npm test exit 0; npm run build:e2e exit 0; playwright e2e/executor-config.spec.ts e2e/settings.spec.ts e2e/enrollment.spec.ts exit 0, 52 passed; enrollment step-2 provider/endpoint test passed (REQ-UX-e47cb172, REQ-FUNC-75711382)
- 2026-11-02 build: help: updated (executors.md provider/model, new #endpoint section, authentication, Test AI connection reasons; projects.md enrollment step 2; glossary Model; en/fr/de/ro)
- 2026-11-02 build: release-notes: updated (merged the two new Executors entries; added new 'Agent and model' provider/model/endpoint entry; updated the fixed Test AI connection entry; categories stay at 10)
- 2026-11-02 build: check: python .agentic/aegis.py check --task TASK-5ceed61e - 0 errors; remaining warnings pre-existing (other tasks' journal headers, ticket-ref, layout globs for config.example.toml/config.toml/.claude) or by convention (release_notes.toml and e2e specs not in affected_paths; e2e specs are linked_tests)
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: review round 1 findings: (spec) stage-run wiring in Orchestrator.from_config untested for provider/models.json/has_key; REQ-SEC-52b11734 verification claims gate.sh and binding checks not linked; enrollment credential field interpretation not recorded; (quality, low) set_connection type-infers numeric/boolean model ids; endpoint URL rule duplicated three ways; (doc agent) TOML import review omits provider
- 2026-11-02 validate: returned to build - round 1 review findings: orchestrator wiring test, REQ-SEC-52b11734 verification, enrollment deviation record, quoted connection strings, shared endpoint URL rule, import review provider
- 2026-11-02 build: DEVIATION design: enrollment step 2 'credential field' is the named credential variable (help note + review row 'Credential to save after creation'); the key itself is saved in Settings after creation - keeps the existing no-secrets enrollment contract; the credential store exists only after creation
- 2026-11-02 build: green: uv run python -m pytest tests/test_orchestrator.py -k wires_the_provider exit 0 (2 passed); mutation (secret_names->env_keys) makes it fail (REQ-SEC-52b11734, REQ-FUNC-f60cd4e1, REQ-FUNC-ae57faed)
- 2026-11-02 build: red: pytest test_web_import review/test_web_executor_configuration numeric model/test_pi_providers quoted URL exit 1 - import review lacks provider; '7'/'1.5'/'true'/'007' models written as non-strings; config accepts a quote in base_url (round-1 findings; REQ-FUNC-75711382, REQ-FUNC-f5f4896f)
- 2026-11-02 build: green: pytest test_web_import test_web_executor_configuration test_pi_providers test_wizard test_web_enrollment test_config test_web_pending_config exit 0 (330 passed); ruff exit 0; tsc -b and tsc -p tsconfig.e2e.json exit 0 - round-1 fixes: shared pi_providers.valid_endpoint_url in config/web/wizard, provider/model written as explicit TOML strings, TOML import review shows provider and endpoint (REQ-FUNC-75711382, REQ-FUNC-f5f4896f)
- 2026-11-02 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-02 validate: DEVIATION validate: final proof is the ticket's list (full pytest, ruff, npm test, typecheck, build:e2e, Playwright executor-config/settings/enrollment specs, check_release_notes) plus 'check --task --strict' without --run, instead of 'check --strict --run' whose frontend command runs the whole Playwright suite - standing instruction: targeted e2e only; other Playwright specs not re-run
- 2026-11-02 validate: final: uv run python -m pytest exit 0 (1904 passed, 3 skipped); uv run ruff check adore tests exit 0; npm test exit 0 (106); npm run typecheck exit 0; npm run build:e2e exit 0; playwright settings/enrollment/executor-config exit 0 (53 passed); python 02_Tools/check_release_notes.py --since b6379b3 exit 0; aegis check --task --strict errors=0, 22 warnings all pre-existing or by convention (other tasks' journal headers, ticket-ref, layout globs for config files/.claude, release_notes.toml and e2e specs not in affected_paths); follow-ups: rebuild adore/web/static before release (not in this ticket by instruction); execution_policy does not pin provider/endpoint
- 2026-11-02 validate: completed; next done (9 Done checklist item(s) left unticked)

## Rulings

- RULING-001 | date=2026-11-02 | decision=Model list = catalog generated from the pinned Pi 1.4.0 by 02_Tools/generate_pi_catalog.py (pi --list-models, PI_OFFLINE=1, a placeholder in each provider variable from Pi's docs/providers.md table) into adore/pi_catalog.json; free text allowed. GitHub Copilot (a GitHub token is a forge credential) and TypeSafe (classifier models only) are not offered; multi-variable providers (Azure, Bedrock, Cloudflare, Vertex) are not offered. | reason=Ticket: model list from Pi by the spike's method, no network at settings time; Pi is pinned by ADORE so the snapshot matches the shipped Pi; no container runtime needed in Settings | source=technical | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-5ceed61e.md
changed: pi_providers + catalog + generator, config schema, launcher models.json/--provider, RPC Test AI connection, credential store wiring, executor.connection edit, pi-providers route, web editor/enrollment/credentials, help x4, CHANGELOG, release notes, docs
evidence: full pytest 1904 passed; ruff; npm test 106; typecheck; build:e2e; 3 Playwright specs 53 passed; check_release_notes ok - all exit 0
issues: none blocking; follow-ups: static bundle rebuild, execution_policy pinning provider/endpoint
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-11-02)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-f5f4896f - Validate the Pi provider, model and endpoint schema
  - REQ-FUNC-ae32f094 - Offer Pi's providers and models from the pinned Pi catalog
  - REQ-SEC-52b11734 - Pass the provider API key to Pi only as its environment variable
  - REQ-FUNC-ae57faed - Write Pi's models.json for an OpenAI-compatible endpoint
  - REQ-FUNC-f60cd4e1 - Select the Pi provider and model on every launch
  - REQ-FUNC-75711382 - Review and apply the agent connection as one change
  - REQ-UX-e47cb172 - Show provider, model and credential fields with help in four locales
  - REQ-FUNC-9110e185 - Report a ready AI connection after an RPC model reply and shell nonce
  - REQ-FUNC-e346ccbd - Report an invalid API key in Test AI connection
  - REQ-FUNC-af2a8db8 - Report an unreachable endpoint in Test AI connection
  - REQ-FUNC-86cb2899 - Report an unknown model in Test AI connection
  - REQ-FUNC-2ed827bf - Report a missing credential in Test AI connection
  - REQ-SEC-3d5fe8a6 - Keep provider keys out of configuration, logs, audit, API responses and the browser
  - REQ-FUNC-7ab1a48e - Refuse an OpenAI-compatible endpoint for a local run
  - REQ-FUNC-de028c15 - Explicit configured executor AI connection test
  - REQ-SEC-1c210f3f - Project provider API credential lifecycle
  - REQ-FUNC-08cc2676 - Reviewed provider variable selection preserves private credentials
  - REQ-FUNC-8f369d55 - Prove a shell tool call in the local Test AI connection
- deviations: 4 recorded
  - build: tests/test_executor_settings.py credential-follows-provider and key-never-leaves tests were written after the executor_settings rewiring, so no red run was recorded - accepted: both are green now and cover REQ-SEC-1c210f3f and REQ-SEC-3d5fe8a6 end to end through the API
  - build: web unit tests (tests/agentConnection.test.mjs) were written after the TypeScript modules, no red run recorded - accepted: they pin the transport, copy parity and guidance contracts; Playwright specs below exercise the UI
  - design: enrollment step 2 'credential field' is the named credential variable (help note + review row 'Credential to save after creation'); the key itself is saved in Settings after creation - keeps the existing no-secrets enrollment contract; the credential store exists only after creation
  - validate: final proof is the ticket's list (full pytest, ruff, npm test, typecheck, build:e2e, Playwright executor-config/settings/enrollment specs, check_release_notes) plus 'check --task --strict' without --run, instead of 'check --strict --run' whose frontend command runs the whole Playwright suite - standing instruction: targeted e2e only; other Playwright specs not re-run
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base b6379b3: 115 file(s) changed, 5035 line(s) added
- checks: errors=0 warnings=22 notes=23
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
