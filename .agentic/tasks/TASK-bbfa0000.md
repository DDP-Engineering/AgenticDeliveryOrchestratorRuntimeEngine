# TASK-bbfa0000 - Sign in with ChatGPT from the ADORE web interface (PI-05, #55)

stage: done
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-09ac930a, REQ-FUNC-055f8047, REQ-FUNC-74d90036, REQ-FUNC-0e27781c, REQ-FUNC-4efa960e, REQ-FUNC-f0076585, REQ-SEC-2689e1f5, REQ-SEC-0fb2bba3, REQ-FUNC-87f05705, REQ-FUNC-a5d65a57, REQ-FUNC-7d12bd00, REQ-FUNC-4388b030, REQ-FUNC-11308471, REQ-REL-acf4c32d, REQ-UX-0d58a662, REQ-FUNC-2ed827bf
parent:
branch: task/adore-web-interface
base: e80b37af05c72c41312046bc6ea6c1dd4bd762e3
opened: 2026-11-03

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

Problem: provider `chatgpt` exists since PI-04 but has no sign-in: Settings
shows "Sign in with ChatGPT is not available yet", Test AI connection reports
credential-missing and a run has no credential (OBSERVED `web/src/agentConnection.ts`
chatgptNote, `adore/pi_providers.py` credential_variable(chatgpt) = None).
Desired outcome: an administrator signs the ADORE server into one ChatGPT
Plus/Pro account from the web interface; projects with provider "ChatGPT
subscription" then run Pi on it without anyone copying files (STATED ticket #55 Goal).
Actors: administrator (Settings -> Agent and model), developer (no access), the
conductor launching Pi per stage, Test AI connection, readiness check.
Primary scenario: admin opens a chatgpt project's Agent and model, clicks Sign in
with ChatGPT, opens the shown link on their own computer, signs in, the browser
fails to load `http://127.0.0.1:1455/auth/callback?...`, the admin pastes that
address into ADORE, status becomes Signed in; the next stage of any chatgpt
project gets a fresh access token (STATED ticket Decisions; OBSERVED SPIKE Q7).
Examples: refresh fails with `invalid_grant` -> status "Sign in again" and the
stage fails with that sentence; OpenAI answers `subscription_sharing_user_not_eligible`
-> the sign-in ends with a sentence saying the plan cannot share its
subscription (STATED ticket Scope). A stage limit of 3600 s with provider chatgpt
is refused (RULING-001 "refuses or warns").
Counterexamples: a developer calling the routes gets 403; the legacy Codex-client
flow is not offered (STATED Decisions).
In scope: ticket Scope with RULING-001 replacing "mounted into containers": routes
to start, complete, show status and disconnect; Settings panel (four locales,
help); ADORE-owned credential directory; per-stage short-lived token; status
values; refusal and refresh-failure sentences; readiness check; ChatGPT model list
(SPIKE Plan changes 2); Test AI connection for chatgpt; docs/CHANGELOG/release notes.
Out of scope: API-key providers and endpoints (PI-04), internet switch (PI-06),
server-installed Pi including native ChatGPT runs (PI-07), live acceptance (PI-08)
(STATED ticket Out, PLAN 6).
Constraints: one credential per server (STATED PLAN 11.2); no migrations; offline
tests with a fake Pi and fake credential files; tokens, codes, redirect URLs,
e-mails and host IDs never in files other than the credential directory, logs,
audit or commits (STATED task brief); LF; license headers; `git commit -s`.
Success signals: the ticket's acceptance criteria with RULING-001 applied (the
helper container that refreshes is the only container that mounts the credential
directory, read-write, and nothing else); listed suites green; one live sign-in
and one live concurrent-token check with the owner.
Evidence: SPIKE_FINDINGS Q7 and Plan changes 1-2; Pi 1.4.0 sources (OBSERVED in the
PI-01 scratch prefix): `pi-ai/dist/auth/oauth/openai-chatgpt.js` (authorize URL,
manual paste, state check, `EXPIRY_MARGIN_MS` 3 min), `pi-ai/dist/cli.js` (random
device ID per login, auth.json in cwd 0644), `pi-coding-agent/dist/core/auth-storage.js`
(`AuthStorage` with proper-lockfile, mode 0600; not exported from the package
index), `pi-ai/dist/auth/resolve.js` (`refreshStoredOAuthCredential` exported;
a min-validity above the token life refreshes and then throws), `pi-coding-agent/
dist/main.js` (`auth print-bearer-token` prints only "Failed to resolve credential"
for a refresh failure, hiding invalid_grant); Codex catalog
`pi-ai/dist/providers/data/openai-codex.json` lists gpt-5.6-luna/sol/terra,
gpt-6-astra/luna/sol, gpt-6.1-sol, all in the openai catalog.
Assumptions: an access token stays valid until its own expiry after another
process rotates the refresh token (to confirm in the live concurrent check).
Unknowns: whether every listed ChatGPT model is served for every Plus/Pro plan
(only gpt-5.6-luna observed); the list is offered, free text stays allowed.
Decision-blocking questions: item 1 answered (RULING-001).
Proposed behaviors: see Design; accepted by the ticket Decisions and RULING-001.
Path and reason: full.

| Criterion | Holds? | Evidence |
|---|---|---|
| no new externally observable behavior | no | sign-in routes, Settings panel, statuses |
| no new interface or data format | no | routes, credential directory, catalog `chatgpt_models` |
| no new dependency | yes | stdlib, existing web stack, Pi already in the image |
| an existing requirement already covers the behavior | no | new behaviors |
| no security or data-handling change | no | OAuth credential per server |

## Requirement coverage

| Behavior | Requirement | Status |
|---|---|---|
| Start sign-in in a helper container, link returned, local refused | REQ-FUNC-09ac930a | created |
| Complete sign-in with a matching redirect address | REQ-FUNC-055f8047 | created |
| Wrong address / state / nothing pending refused, sign-in kept | REQ-FUNC-74d90036 | created |
| OpenAI refusal ends the sign-in with a localized cause | REQ-FUNC-0e27781c | created |
| Status signed-in / not-signed-in / sign-in-again from files | REQ-FUNC-4efa960e | created |
| Disconnect deletes the credential | REQ-FUNC-f0076585 | created |
| Admin-only, CSRF, audit without secrets | REQ-SEC-2689e1f5 | created |
| Per-stage short-lived token, only OPENAI_API_KEY in the exec env | REQ-SEC-0fb2bba3 | created |
| No token -> attempt fails with a clear sentence, refresh refusal marks sign-in-again | REQ-FUNC-87f05705 | created |
| chatgpt refused for local runs and stage limits above 3000 s | REQ-FUNC-a5d65a57 | created |
| ChatGPT model list from the pinned Pi | REQ-FUNC-7d12bd00 | created |
| Test AI connection for chatgpt, new reasons | REQ-FUNC-4388b030 | created |
| Readiness check executor_sign_in | REQ-FUNC-11308471 | created |
| Concurrent token requests share Pi's lock | REQ-REL-acf4c32d | created |
| Settings panel and help in four locales | REQ-UX-0d58a662 | created |
| credential-missing applies to API-key providers only | REQ-FUNC-2ed827bf | revised |

## Design

**Credential directory.** `<ADORE home>/chatgpt/` (0700 on POSIX), shared by the
web server and every conductor of the host (both resolve `adore_home()`). Pi owns
`auth.json` and its lock directory `auth.json.lock`; ADORE owns `device-id` (a
stable UUID, the OpenAI agent host id, kept across sign-ins and Disconnect) and
the mark `sign-in-again` (written when OpenAI refuses a refresh, removed by a
successful sign-in or refresh). No run container mounts it (RULING-001).

**Helper script (image).** `docker/pi/adore-chatgpt.mjs`, copied to
`/opt/adore/pi/adore-chatgpt.mjs`, imports the pinned Pi's own modules by file
path: `openaiChatGPTOAuth` (pi-ai `auth/oauth/openai-chatgpt.js`),
`refreshStoredOAuthCredential` (pi-ai `auth/resolve.js`) and `AuthStorage`
(pi-coding-agent `dist/core/auth-storage.js`, proper-lockfile, 0600). Commands,
one JSON object per stdout line, never a token except the `token` answer:
`login` -> `{"event":"auth_url","url"}`, reads one stdin line (the redirect
address), stores the credential with `AuthStorage.modify`, then
`{"event":"signed-in"}` or `{"event":"error","code"}`; `token
--min-validity-seconds N` -> `{"status":"ok","token","expires"}` or
`{"status":<code>}`. Codes: not-signed-in, sign-in-again, not-eligible, denied,
code-rejected, refused, unavailable, unreadable, too-long, failed. Rejected:
`pi-ai login` dev CLI (random device id per login, auth.json 0644 in cwd, free
text output) and `pi auth print-bearer-token` (prints only "Failed to resolve
credential" for a refused refresh, so ADORE could not tell sign-in-again from a
network failure; OBSERVED Pi `dist/main.js`).

**Helper container.** `ContainerManager.helper_command(name, argv, mount, env)`
-> `<runtime> run --rm [-i for login] --name adore-chatgpt-<hex> <run_args> --pull=never
--volume <credential dir>:/adore/chatgpt[:relabel] --workdir /adore/chatgpt
--env PI_CODING_AGENT_DIR=/adore/chatgpt --env PI_TELEMETRY=0 --env
PI_SKIP_VERSION_CHECK=1 --entrypoint node <image> /opt/adore/pi/adore-chatgpt.mjs
...`: the only bind mount, default network (it is ADORE's tool, not the agent).
A hung helper is removed with `<runtime> rm --force <name>`.

**`adore/chatgpt.py`.** `credential_dir(home)`, `status(dir)` (file-only:
missing auth.json/openai -> not-signed-in; unparsable JSON, a non-oauth entry or
missing access/refresh/expires, or the mark -> sign-in-again; else signed-in),
`disconnect(dir)`, `ChatGptError(code)` with `sentence()`,
`bearer_token(manager, dir, min_validity_seconds, *, timeout)` (runs on
`manager.runner`; strict one-line JSON,
token shape check, mark on sign-in-again, clear mark on ok), `SignIn` (Popen of
the login helper, reader thread, 15-minute expiry, `submit(url)` validates the
address first: origin+path `http://127.0.0.1:1455/auth/callback`, `error`
param -> refusal codes, `code` present, `state` equal to the link's), constants
`MAX_STAGE_SECONDS = 3000`, `TOKEN_MARGIN_SECONDS = 300`, `TOKEN_VARIABLE =
"OPENAI_API_KEY"`.

**Runs.** `Orchestrator(chatgpt_token=...)`; by default `__init__` binds
`bearer_token` to the project's ContainerManager and `credential_dir()`; it is
called only when the provider is chatgpt. `_launch_stage` mints `timeout + 300` s before `run_gate`;
a ChatGptError returns a failed GateRun (exit 1, the English sentence) without
spawning Pi, so the ordinary retry policy applies and a sign-in made meanwhile
lets the next attempt run. The token joins only that gate's bound target:
`ContainerBackend.bind(..., secrets=(token,))`, `BoundTarget.redact` masks it in
Pi's evidence (pi_rpc already accepts `redact`).

**Configuration.** `config.py` refuses chatgpt with backend local (the token
needs the image's Pi until PI-07) and per-gate/override limits above 3000 s
(token life 60 min minus Pi's 3 min margin, minus the 5 min request margin).

**Catalog.** `generate_pi_catalog.py` adds `chatgpt_models`: the chat models of
the pinned pi-ai `providers/data/openai-codex.json` that are also openai models;
`pi_providers` validates it and `public_catalog()["chatgpt"]["models"]`; the
editor's datalist and the wizard offer it.

**Test AI connection.** chatgpt: mint (90 s + margin) before provisioning;
not-signed-in/sign-in-again -> `sign-in-required`, not-eligible ->
`subscription-refused`, unavailable -> `connection-failed`, other helper errors ->
`runtime-error`; the token rides on the spawn env and the redaction list. pi_rpc
gains failure class `subscription` (`subscription_sharing_user_not_eligible`,
matched first); a ChatGPT `rate-limit` maps to `usage-limit`.

**Web.** Admin-only routes: `GET /api/v1/chatgpt-sign-in` -> `{status,
pending}`; `POST /api/v1/projects/{name}/chatgpt-sign-in` (start, uses that
project's runtime/image) -> `{authorize_url, expires_in}`; `PUT
/api/v1/chatgpt-sign-in` `{redirect_url}` -> `{status, pending}`; `DELETE
/api/v1/chatgpt-sign-in/pending` (cancel); `DELETE /api/v1/chatgpt-sign-in`
(disconnect). Changes use `admin_mutation` (CSRF). One in-memory pending
sign-in per server under a lock; `create_app(chatgpt_popen=...)` is the test
seam. Audit actions `chatgpt-sign-in-started|completed|failed|cancelled`,
`chatgpt-disconnected`, detail = cause code only. Readiness: `executor_sign_in`
(true/false, present only for chatgpt projects; other records unchanged) in `_probe_setup` and the three web key
lists. Model evidence of a chatgpt project counts as stale while the server is
not signed in.

**Frontend.** `chatgptCopy.ts` (panel copy in four locales, response
parsing; the `chatgpt_*` error sentences live in `errors.ts`) and `ChatGptSignIn.tsx` in the Agent and model
authentication slot in place of the API-key form for chatgpt; the link opens in
a new tab (`noopener noreferrer`); the pasted address lives only in component
state and is cleared after each attempt. Help `executors.md` (four locales).

**Rejected.** Mounting the directory as each run's agent directory (RULING-001).
A Python reimplementation of OpenAI's OAuth (not Pi's official flow; would
duplicate Pi's lock and file format). Requiring an idle project for sign-in
(the credential is the server's, not project configuration).

## Log

- 2026-11-03 frame: journal opened
- 2026-11-03 frame: interaction set to autopilot: delegated ticket session (PI-05) whose Decisions are the owner's; same mode as PI-02/PI-03/PI-04; item 1 asked and answered (RULING-001)
- 2026-11-03 frame: completed; next specify - scope recorded (autopilot) (7 Done checklist item(s) left unticked)
- 2026-11-03 specify: completed; next design (7 Done checklist item(s) left unticked)
- 2026-11-03 design: DEVIATION design: ChatGPT subscription runs only on the container backend in PI-05; a local (server-installed) run is refused by configuration until PI-07 ships ADORE's own Pi on the server - the ticket Goal says 'in containers and on the server'; minting a token needs the pinned Pi, which today exists only in the image; PI-07 must lift REQ-FUNC-a5d65a57's local clause
- 2026-11-03 design: completed; next build - design recorded (autopilot) (6 Done checklist item(s) left unticked)
- 2026-11-03 build: red: uv run python -m pytest tests/test_chatgpt.py exit 2 - no adore.chatgpt: no status/disconnect/stage token/sign-in session (REQ-FUNC-4efa960e, REQ-FUNC-f0076585, REQ-SEC-0fb2bba3, REQ-FUNC-87f05705, REQ-REL-acf4c32d, REQ-FUNC-09ac930a, REQ-FUNC-055f8047, REQ-FUNC-74d90036, REQ-FUNC-0e27781c)
- 2026-11-03 build: green: uv run python -m pytest tests/test_chatgpt.py exit 0, 38 passed (REQ-FUNC-4efa960e, REQ-FUNC-f0076585, REQ-SEC-0fb2bba3 helper mount, REQ-FUNC-87f05705 typed causes, REQ-REL-acf4c32d fake-process lock, REQ-FUNC-09ac930a, REQ-FUNC-055f8047, REQ-FUNC-74d90036, REQ-FUNC-0e27781c)
- 2026-11-03 build: red: uv run python -m pytest tests/test_pi_providers.py -k chatgpt_is_refused exit 1 - chatgpt accepted with backend local and stage limits above 3000 s (REQ-FUNC-a5d65a57)
- 2026-11-03 build: green: uv run python -m pytest tests/test_pi_providers.py tests/test_config.py exit 0, 91 passed (REQ-FUNC-a5d65a57)
- 2026-11-03 build: red: uv run python -m pytest tests/test_chatgpt_stage.py exit 1, 6 failed - no ChatGPT token source on the conductor, no per-gate OPENAI_API_KEY or redaction (REQ-SEC-0fb2bba3, REQ-FUNC-87f05705)
- 2026-11-03 build: green: uv run python -m pytest tests/test_chatgpt_stage.py tests/test_orchestrator.py tests/test_execution.py exit 0, 7 + 152 passed (REQ-SEC-0fb2bba3, REQ-FUNC-87f05705)
- 2026-11-03 build: red: uv run python -m pytest tests/test_pi_providers.py -k 'chatgpt_models or corrupt_catalog' exit 1 - catalog has no chatgpt_models and does not validate it (REQ-FUNC-7d12bd00)
- 2026-11-03 build: green: python 02_Tools/generate_pi_catalog.py (pinned Pi 1.4.0 from the PI-01 prefix, offline) exit 0 - 34 providers, 7 ChatGPT models, diff adds only chatgpt_models; uv run python -m pytest tests/test_pi_providers.py tests/test_web_executor_configuration.py tests/test_wizard.py exit 0, 88 passed (REQ-FUNC-7d12bd00)
- 2026-11-03 build: red: uv run python -m pytest tests/test_model_connection.py exit 1, 25 failed - no chatgpt_dir/token path, chatgpt reported credential-missing, no subscription-refused/usage-limit reasons (REQ-FUNC-4388b030, REQ-SEC-0fb2bba3)
- 2026-11-03 build: green: uv run python -m pytest tests/test_model_connection.py tests/test_pi_rpc.py exit 0, 61 passed (REQ-FUNC-4388b030, REQ-SEC-0fb2bba3, REQ-FUNC-2ed827bf)
- 2026-11-03 build: red: uv run python -m pytest tests/test_web_chatgpt.py exit 1, 14 failed - no sign-in routes, no executor_sign_in readiness check (REQ-FUNC-09ac930a, REQ-FUNC-055f8047, REQ-FUNC-74d90036, REQ-FUNC-0e27781c, REQ-FUNC-4efa960e, REQ-FUNC-f0076585, REQ-SEC-2689e1f5, REQ-FUNC-11308471)
- 2026-11-03 build: green: uv run python -m pytest tests/test_web_chatgpt.py tests/test_executor_settings.py tests/test_web_rbac.py tests/test_model_connection.py tests/test_web_config.py exit 0, 116 passed; audit store keeps only a chatgpt_<code> detail for chatgpt-sign-in-failed (REQ-SEC-2689e1f5 and the route requirements)
- 2026-11-03 build: green: web npm run typecheck exit 0; node --test tests/chatgpt.test.mjs tests/readiness.test.mjs tests/agentConnection.test.mjs tests/errors.test.mjs tests/modelEvidence.test.mjs exit 0; npm run build:e2e exit 0; playwright e2e/executor-config.spec.ts -g 'signs the server in with ChatGPT' exit 0, 1 passed (REQ-UX-0d58a662, REQ-FUNC-0e27781c four-locale sentences, REQ-FUNC-7d12bd00 web list, REQ-FUNC-11308471 web parser, REQ-FUNC-4388b030 web reasons)
- 2026-11-03 build: DEVIATION build: web unit tests (chatgpt.test.mjs, readiness/agentConnection additions) and the Playwright flow were written after the components, no red run recorded - accepted: they pin copy parity, transports and the browser flow; the backend contracts they rely on were red-first
- 2026-11-03 build: help: updated (executors.md en/fr/de/ro: ChatGPT subscription bullet, new #chatgpt section with steps, statuses, token model, 3000 s limit and OpenAI interest-form note; Test AI connection reasons)
- 2026-11-03 build: release-notes: updated (merged ChatGPT sign-in into the existing new 'Agent and model' entry in four locales; 'new' stays at 10); python 02_Tools/check_release_notes.py --since e80b37a exit 0
- 2026-11-03 build: Manual (REQ-REL-acf4c32d, REQ-FUNC-09ac930a, REQ-FUNC-055f8047, REQ-SEC-0fb2bba3, REQ-SEC-2689e1f5, REQ-FUNC-f0076585): live 2026-11-03 on a throwaway ADORE web instance (127.0.0.1:18766, WSL Docker 29.6.1, image adore-executor-base:pi05-check built from this tree, verify-runtime.sh 22/22 incl. new step 14). Owner signed in with ChatGPT through the web panel (link + pasted redirect) -> Signed in. Two concurrent token requests (3400 s, forcing a refresh) on the mounted directory: 2.7 s, same 2106-char token for both, refresh token rotated exactly once, auth.json valid, lock released, status signed-in. Test AI connection (gpt-5.6-luna, token only in Pi's exec env) -> ready. Scan of every file and audit row of the instance: no access/refresh token, link, redirect address or host id. Disconnect via API -> not-signed-in, only device-id left; instance and folder removed
- 2026-11-03 build: green: uv run python -m pytest (full) exit 0, 1975 passed, 3 skipped; ruff check adore tests exit 0; web npm test 111 pass, typecheck, build:e2e exit 0; playwright e2e/executor-config.spec.ts e2e/settings.spec.ts 37 passed
- 2026-11-03 build: completed; next validate (6 Done checklist item(s) left unticked)
- 2026-11-03 validate: review round 1: spec - (1) web/e2e/enrollment.spec.ts still expects 'Sign in with ChatGPT is not available yet'; (2) stale 'not available' text in web/src/settingHelp.ts (4 locales), config.example.toml, Web_Interface.md, help executors.md 'container project always uses the provider's API key' (4 locales); (3) REQ-FUNC-09ac930a second start untested and verification names chatgpt_sign_in_unavailable where the test asserts chatgpt_helper_failed. quality - (1) SignIn._end closes stdout before killing a silent helper, hanging the request and the web chatgpt_lock; (2) helper maps 408/429 refresh failures to sign-in-again (permanent mark); (3) bearer_token leaves the helper container when the probe's bounded runner raises TimeoutError; (4) no offline test of the Node helper's cause mapping; (5) an expired pending sign-in is cleaned up only lazily
- 2026-11-03 validate: returned to build - review round 1 findings (spec 1-3, quality 1-5)
- 2026-11-03 build: red: pytest tests/test_chatgpt.py -k 'silent_after or bounded_runner or abandoned' - silent-helper test hung (quality 1), bounded-runner and abandoned tests failed (quality 3, 5); pytest tests/test_chatgpt_helper_script.py exit 1, 3 failed - 429/408/404 refresh answers mapped to sign-in-again (quality 2, 4)
- 2026-11-03 build: green (round-1 fixes): SignIn._end kills a silent helper and never closes stdout under the reader; bearer_token removes the helper on a raised TimeoutError (fallback rm on its own bound); a Timer cancels an abandoned sign-in after SIGN_IN_SECONDS; helper maps only invalid_grant/400/401/403 to sign-in-again; new tests/test_chatgpt_helper_script.py (stub Pi package, Node); second-start test; stale 'not available' text fixed in settingHelp.ts (4 locales), config.example.toml, Web_Interface.md, help executors.md (4 locales), enrollment.spec.ts; REQ-FUNC-09ac930a verification corrected. ruff exit 0; pytest test_chatgpt*/test_web_chatgpt/test_model_connection exit 0, 110 passed; web typecheck, build:e2e exit 0; help/settingHelp tests 14 pass; playwright enrollment.spec.ts 17 passed
- 2026-11-03 build: completed; next validate - round-1 findings fixed (6 Done checklist item(s) left unticked)
- 2026-11-03 validate: Inspection: rebuilt adore-executor-base:pi05-check with the fixed helper; IMAGE=adore-executor-base:pi05-check verify-runtime.sh all 22 steps passed (step 14: helper loads the pinned Pi)
- 2026-11-03 validate: review round 2: quality approved (low notes, no change required: expiry Timer not cancelled on finish; _mark OSError not mapped; stray extra helper event); spec - help executors.md 'Where jobs run' Sign-in row (4 locales) still says a container uses only the provider's API key
- 2026-11-03 validate: returned to build - review round 2 spec finding: help Sign-in row
- 2026-11-03 build: green (round-2 fix): help executors.md 'Where jobs run' Sign-in row now names the ChatGPT short-lived token (en/fr/de/ro); same class also fixed in projects.md enrollment step 2 and host-check list (4 locales); node --test tests/help.test.mjs exit 0, 10 pass
- 2026-11-03 build: completed; next validate - round-2 finding fixed (6 Done checklist item(s) left unticked)
- 2026-11-03 validate: review round 3: quality approved; spec - 01_Documentation/Web_Interface.md ~587-591 still says a ChatGPT subscription does not reach a container Pi run
- 2026-11-03 validate: returned to build - review round 3 spec finding: stale Web_Interface.md paragraph
- 2026-11-03 build: green (round-3 fix): Web_Interface.md container-Pi paragraph and Configuration_Reference.md credential paragraph now name the ChatGPT short-lived token; sweep of 01_Documentation, 05_SoftwareDocu, knowledge and web/src for 'always uses provider API key' / 'does not reach' found no other match
- 2026-11-03 build: completed; next validate - round-3 finding fixed (6 Done checklist item(s) left unticked)
- 2026-11-03 validate: review round 4: spec approved, quality approved (cosmetic note left: Web_Interface.md ~72 enrollment help could also name the ChatGPT exception; not a contradiction)
- 2026-11-03 validate: DEVIATION validate: final proof is the ticket's list (full pytest, ruff, npm test, typecheck, build:e2e, Playwright executor-config/settings/enrollment, check_release_notes) plus 'check --task --strict' without --run, instead of 'check --strict --run' whose frontend command runs the whole Playwright suite - standing instruction: targeted e2e only; other Playwright specs not re-run
- 2026-11-03 validate: final: uv run python -m pytest exit 0 (1993 passed, 3 skipped); ruff check adore tests exit 0; npm test exit 0 (111 pass); npm run typecheck exit 0; npm run build:e2e exit 0; playwright e2e/executor-config.spec.ts e2e/settings.spec.ts e2e/enrollment.spec.ts exit 0 (54 passed); python 02_Tools/check_release_notes.py --since e80b37a exit 0; aegis check --task TASK-bbfa0000 --strict: errors=0, warnings pre-existing or accepted (docker/config outside layout globs, test files are linked_tests, test-only developer password, other journals' headers)
- 2026-11-03 validate: completed; next done - validated; review round 4 approved (9 Done checklist item(s) left unticked)

## Rulings

- RULING-001 | date=2026-11-03 | decision=ChatGPT credential reaches runs as a short-lived access token (SPIKE_FINDINGS Plan changes item 1, option b): ADORE keeps the one per-server sign-in in an ADORE-owned host directory, refreshes it there under Pi's own lock before each stage, and gives each run only OPENAI_API_KEY=<access token>; the refresh token never enters a run container. ADORE refuses or warns when a ChatGPT stage limit exceeds the token life. | reason=Owner's choice on 2026-11-03 when asked to decide item 1 in PI-05: keeps the refresh token out of agent containers and per-project models.json/web-search.json out of the shared directory; the ~57-minute token life only bites when a stage limit is raised above it (default 1800 s). | source=user | supersedes=none


## State

status: done
reported: validate - completed
next: implementation guidance complete; commit, push and integration belong to the developer
must_read: .agentic/tasks/TASK-bbfa0000.md
changed: PI-05 ChatGPT sign-in
evidence: full pytest exit 0 (1993 passed); ruff 0; npm test 0; typecheck 0; build:e2e 0; playwright 54 passed; release notes ok
issues: ChatGPT local (server-installed) runs refused until PI-07; bundled adore/web/static not rebuilt (per epic plan)
spec_compliance: approved
implementation_quality: approved
review_round: 4

## Delivery report (2026-11-03)

- stage: validate; type: feature; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-09ac930a - Start Sign in with ChatGPT from a container project
  - REQ-FUNC-055f8047 - Complete Sign in with ChatGPT with the pasted redirect address
  - REQ-FUNC-74d90036 - Refuse a pasted address that is not this sign-in's callback
  - REQ-FUNC-0e27781c - End a sign-in that OpenAI refuses with a localized cause
  - REQ-FUNC-4efa960e - Report the server's ChatGPT sign-in status
  - REQ-FUNC-f0076585 - Disconnect ChatGPT deletes the server credential
  - REQ-SEC-2689e1f5 - ChatGPT sign-in routes are admin-only, CSRF-protected and audited without secrets
  - REQ-SEC-0fb2bba3 - Each ChatGPT stage receives only a short-lived access token
  - REQ-FUNC-87f05705 - Fail a ChatGPT stage clearly when no access token can be obtained
  - REQ-FUNC-a5d65a57 - Refuse ChatGPT for a local run or a stage limit beyond the token life
  - REQ-FUNC-7d12bd00 - Offer the ChatGPT model list
  - REQ-FUNC-4388b030 - Test AI connection signs a ChatGPT project's challenge with a fresh access token
  - REQ-FUNC-11308471 - Readiness check reports the ChatGPT sign-in
  - REQ-REL-acf4c32d - Concurrent ChatGPT token requests share Pi's credential lock
  - REQ-UX-0d58a662 - ChatGPT sign-in panel in Settings with help in four locales
  - REQ-FUNC-2ed827bf - Report a missing credential in Test AI connection
- deviations: 3 recorded
  - design: ChatGPT subscription runs only on the container backend in PI-05; a local (server-installed) run is refused by configuration until PI-07 ships ADORE's own Pi on the server - the ticket Goal says 'in containers and on the server'; minting a token needs the pinned Pi, which today exists only in the image; PI-07 must lift REQ-FUNC-a5d65a57's local clause
  - build: web unit tests (chatgpt.test.mjs, readiness/agentConnection additions) and the Playwright flow were written after the components, no red run recorded - accepted: they pin copy parity, transports and the browser flow; the backend contracts they rely on were red-first
  - validate: final proof is the ticket's list (full pytest, ruff, npm test, typecheck, build:e2e, Playwright executor-config/settings/enrollment, check_release_notes) plus 'check --task --strict' without --run, instead of 'check --strict --run' whose frontend command runs the whole Playwright suite - standing instruction: targeted e2e only; other Playwright specs not re-run
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=4
- diff vs task base e80b37a: 91 file(s) changed, 4051 line(s) added
- checks: errors=0 warnings=24 notes=23
- checklist: 0/9 done; open: diff reviewed against scope, requirements, design, error paths, portability, security and unrequested work; knowledge pages of changed components current with the reviewed code; project and environment context reconciled with the candidate; requirements re-read: status, prose, verification, paths and links true; manual or inspection verification recorded where applicable; explicit review approved, when enabled; final `check --strict --run` result logged truthfully after the last edit; remaining warnings and pre-existing failures explained; `report` appended
