<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: ChatGPT sign-in (`adore/chatgpt.py`)

## 1. Purpose

Let a project use a ChatGPT Plus or Pro subscription (`[executor] provider =
"chatgpt"`) instead of a provider API key. The ADORE server holds one ChatGPT
sign-in, made once by an administrator in the web interface, and every stage of
every `chatgpt` project on that server gets only a short-lived access token
from it. Pi does every OAuth step itself; ADORE never implements OpenAI's flow.

## 2. Responsibilities

- Own the credential directory `<ADORE home>/chatgpt` and read the sign-in
  status from its files without starting Pi.
- Run ADORE's helper script in a one-off helper container to sign in (`login`)
  and to get an access token (`token`).
- Hold the state of one pending sign-in (`SignIn`): link, pasted redirect
  address, 15-minute expiry, Cancel.
- Delete the stored credential on Disconnect.
- Turn every failure into a value-free cause code with one English sentence.

Not owned: the web routes, locks and audit (`web/app.py`, see
[Web API](Component_Web_API.md)), the sign-in panel (`ChatGptSignIn.tsx`, see
[Web frontend](Component_Web_Frontend.md)), the per-stage injection
(`orchestrator.py`, see [Executor launcher](Component_Executor_Launcher.md)),
the configuration refusals (`config.py`, see [Config](Component_Config.md)) and
the probe reasons (`web/model_connection.py`, see
[Model connection](Component_Model_Connection.md)).

## 3. Implementation Overview

Files:

- `04_Software/adore/chatgpt.py` - status, directory, helper calls, `SignIn`.
- `04_Software/docker/pi/adore-chatgpt.mjs` - the helper script, copied into
  the executor image as `/opt/adore/pi/adore-chatgpt.mjs`; it imports the
  pinned Pi's own modules by file path (`openaiChatGPTOAuth`,
  `refreshStoredOAuthCredential`, `AuthStorage`).
- `04_Software/adore/isolation.py` - `ContainerManager.helper_command` and
  `remove_helper`.
- `04_Software/adore/branding.py` - `CHATGPT_CREDENTIAL_DIR = "chatgpt"`,
  `CONTAINER_CHATGPT_MOUNT = "/adore/chatgpt"`,
  `CONTAINER_PI_CHATGPT_SCRIPT = "/opt/adore/pi/adore-chatgpt.mjs"`.

Public API of `adore/chatgpt.py`:

- `credential_dir(home=None)` - `<home>/chatgpt`, with `adore_home()` when
  `home` is omitted. The web server and every conductor of the host resolve
  the same directory.
- `prepare(directory)` - creates the directory (mode 0700 on POSIX) and, once,
  `device-id`: a UUID written with mode 0600 and kept across sign-ins and
  Disconnect, so OpenAI sees one agent host.
- `status(directory)` - one of `signed-in`, `not-signed-in`, `sign-in-again`.
- `disconnect(directory)` - deletes `auth.json` and `sign-in-again`; keeps
  `device-id`. An `OSError` propagates.
- `check_redirect(url, state)` - validates a pasted redirect address before Pi
  sees it.
- `bearer_token(manager, directory, min_validity_seconds, *, timeout=90)` - an
  access token valid for at least the requested seconds, in memory only.
- `SignIn(manager, directory, *, popen, clock)` - one pending sign-in with
  `start()`, `submit(url)`, `cancel()`, `pending` and `expired`.
- `ChatGptError(code)` with `sentence()`; an unknown code becomes `failed`.

Constants: `MAX_STAGE_SECONDS = 3000`, `TOKEN_MARGIN_SECONDS = 300`,
`TOKEN_VARIABLE = "OPENAI_API_KEY"`, `SIGN_IN_SECONDS = 900`,
`TOKEN_TIMEOUT_SECONDS = 90`, `CALLBACK_URL =
"http://127.0.0.1:1455/auth/callback"`, `AUTHORIZE_PREFIX =
"https://auth.openai.com/"`.

### Status rules

`status` reads `auth.json` only:

- no `auth.json`, or no `openai` entry in it -> `not-signed-in`;
- `auth.json` that is a symlink, not a regular file, larger than 1 MiB,
  unreadable, not UTF-8 JSON or not an object -> `sign-in-again`;
- an `openai` entry that is not `type: "oauth"` with non-empty string `access`
  and `refresh` and a numeric `expires` -> `sign-in-again`;
- the mark `sign-in-again` present -> `sign-in-again`;
- otherwise `signed-in`.

### Helper container

`ContainerManager.helper_command(name, argv, mount=..., env=..., interactive=...)`
builds `<runtime> run --rm [-i] --name adore-chatgpt-<16 hex> <run_args>
--pull=never --volume <credential directory>:/adore/chatgpt[:relabel]
--workdir /adore/chatgpt --env PI_CODING_AGENT_DIR=/adore/chatgpt --env
PI_TELEMETRY=0 --env PI_SKIP_VERSION_CHECK=1 --entrypoint node <image>
/opt/adore/pi/adore-chatgpt.mjs <command>`. The credential directory is its
only bind mount; it uses the default network (it is ADORE's tool, not the
agent) and its environment holds no secret. `-i` is set only for `login`.
`remove_helper(name)` runs `<runtime> rm --force <name>` for a helper ADORE had
to stop. The runtime, image, `run_args` and SELinux relabel come from the
project whose manager is used.

### Helper protocol

The helper prints one JSON object per line; ADORE reads only that protocol.

- `login`: prints `{"event":"auth_url","url":"<authorization link>"}`, reads one
  stdin line (the pasted redirect address), stores the credential with Pi's
  `AuthStorage` (Pi's lock, mode 0600), then prints `{"event":"signed-in"}` or
  `{"event":"error","code":"<code>"}`. A `device-id` that is missing or not a
  UUID gives `failed`; an unreadable `auth.json` gives `unreadable`.
- `token --min-validity-seconds N`: prints `{"status":"ok","token":"<access
  token>","expires":<ms>}` with a token valid for at least N seconds, refreshing
  it under Pi's lock when needed, or `{"status":"<code>"}`. A token that still
  expires too soon after a refresh gives `too-long`.

Helper codes: `not-signed-in`, `sign-in-again`, `not-eligible`, `denied`,
`code-rejected`, `unavailable`, `unreadable`, `too-long`, `refused`, `failed`.
The helper classifies Pi's error texts into these codes and never prints them;
a refused refresh (`invalid_grant`, or a 400, 401 or 403 token answer) is
`sign-in-again`; any other 4xx (such as 408 or 429), a 5xx or a network
failure is `unavailable` and is retried by the next request.
ADORE adds `redirect-invalid`, `state-mismatch`, `not-pending` and
`helper-failed` (output that is not the protocol, or a helper that cannot
start). `docker/verify-runtime.sh` step 14 runs `token` against an empty
directory and expects `{"status":"not-signed-in"}`.

### Stage token flow

`bearer_token` starts nothing unless the status is `signed-in`; otherwise it
raises that status as the code. It runs `token` in a helper container through
`manager.runner` with a 90 s wall-clock bound; a timed-out helper is removed and
reported as `unavailable`. It accepts only an answer whose last non-empty line
is exactly `{status: "ok", token, expires}` with a token of 16-16384 token-safe
characters; that answer removes the `sign-in-again` mark. A `sign-in-again`
answer writes the mark, so `status` reports `sign-in-again` until the next
successful sign-in or refresh.

Callers request:

- a stage: the stage limit (`per_gate_timeout_seconds` or the stage override)
  plus 300 s, minted in `Orchestrator._launch_stage` before Pi starts;
- Test AI connection: 90 s plus 300 s, minted before the probe container is
  provisioned.

A ChatGPT access token lasts 60 minutes minus Pi's 3-minute margin, and ADORE
asks for 5 minutes more, so it accepts stage limits of at most 3000 s
(`MAX_STAGE_SECONDS`);
`config.py` refuses larger limits. The token is not refreshed during a stage.
The stage receives it only as `OPENAI_API_KEY` in that gate's bound target
(`ContainerBackend.bind(..., secrets=(token,))`), and Pi runs with provider
`openai`.

### Sign-in session lifecycle

1. `start()` calls `prepare`, starts `login` in an interactive helper container
   through `popen`, and waits up to 60 s for the first protocol object. It
   accepts only an `auth_url` event whose link starts with
   `https://auth.openai.com/`, is at most 8192 characters and carries one
   `state` of 8-512 safe characters; it then records that `state` and the
   start time and returns the link. No link in time is `unavailable`; any
   other answer cancels the helper and raises its code or `helper-failed`.
2. The administrator opens the link in their own browser and signs in. The
   browser then fails to load `http://127.0.0.1:1455/auth/callback?...`, and
   the administrator pastes that full address.
3. `submit(url)` refuses when the sign-in is not pending (`not-pending`). It
   calls `check_redirect`: the address must be at most 8192 characters without
   whitespace or control characters, have exactly the callback origin and
   path, single-valued query parameters, a `code` and the pending link's
   `state`. A malformed address (`redirect-invalid`) or another attempt's
   state (`state-mismatch`) leaves the sign-in pending. An `error` parameter is
   OpenAI's refusal: `access_denied` -> `denied`,
   `subscription_sharing_user_not_eligible` -> `not-eligible`, anything else
   -> `refused`; a refusal ends the sign-in.
4. Only a checked address is written to the helper's stdin. ADORE waits up to
   60 s for the answer, then ends the helper: one that answered exits once
   its stdin closes, a silent one is killed and its container removed at
   once. `signed-in` removes the `sign-in-again` mark; no answer is
   `unavailable`; an error raises its code.
5. A sign-in ends on success, on a refusal, on `cancel()` (kills the process
   and removes the helper container) or 900 s after the link was shown
   (`expired`; a timer then cancels it without waiting for another request).

### Security properties

- The refresh token stays in `<ADORE home>/chatgpt`; no run container mounts
  that directory (RULING-001). A stage gets only the access token, which
  `BoundTarget.redact` masks in Pi's evidence; the probe masks it the same way.
- A token, authorization code, link or redirect address never appears in a
  command line, log message, cause sentence, error response or audit row. The
  token travels only in the helper's stdout and the gate's environment (a bare
  `--env OPENAI_API_KEY` whose value is in the runtime client's process
  environment, as for every secret); the
  redirect address only on the helper's stdin; the link only in the start
  response to the administrator. ADORE never reads or keeps the helper's
stderr.
- Cause codes and their sentences carry no value. The audit keeps only the
  `chatgpt_<code>` error code as the detail of `chatgpt-sign-in-failed`.
- The helper environment holds only `PI_CODING_AGENT_DIR`, `PI_TELEMETRY=0`
  and `PI_SKIP_VERSION_CHECK=1`.
- Pi writes `auth.json` with mode 0600; `device-id` is 0600 and the directory
  0700 on POSIX.

### Concurrency

The web server and every conductor of the host may run helpers at once. Pi's
`AuthStorage` locks `auth.json` with proper-lockfile, whose lock is the
directory `auth.json.lock` beside the file. Because ADORE mounts the credential
directory, not the file, every helper container sees the same lock, so two
refreshes never race. The web server keeps at most one pending sign-in in
memory, guarded by one lock; starting a new sign-in cancels the previous one.

## 4. Dependencies

- Internal: `adore.branding` (paths), `adore.util.strict_json_loads`,
  `adore.profiles.adore_home`, `adore.isolation.ContainerManager`
  (`helper_command`, `remove_helper`, `runner`).
- Users: `adore.orchestrator` (`chatgpt_token` seam, default
  `bearer_token(self.containers, credential_dir(), seconds)`), `adore.config`
  (`MAX_STAGE_SECONDS`), `adore.web.app` (routes, readiness check
  `executor_sign_in`, model evidence), `adore.web.model_connection` (probe
  token).
- External: Docker or Podman, and the executor image with the pinned Pi 1.4.0
  and the helper script. OpenAI's sign-in and token endpoints, reached from
  the helper container.

## 5. Data Contracts

Credential directory `<ADORE home>/chatgpt` (mounted at `/adore/chatgpt`):

| Entry | Owner | Content |
|---|---|---|
| `auth.json` | Pi | `{"openai": {"type": "oauth", "access", "refresh", "expires", ...}}`, mode 0600 |
| `auth.json.lock` | Pi | proper-lockfile lock directory |
| `device-id` | ADORE | one UUID line, mode 0600, kept on Disconnect |
| `sign-in-again` | ADORE | empty mark: OpenAI refused the last refresh |

Web transports: status `{status, pending}`; start `{authorize_url,
expires_in}` with `expires_in` 900.

## 6. Usage

An administrator sets `provider = "chatgpt"` for a container project, opens
Settings → Agent and model and uses **Sign in with ChatGPT**. The CLI wizard
names this as the first next step. Readiness shows a **ChatGPT sign-in** check
for `chatgpt` projects. **Disconnect ChatGPT** deletes the stored credential;
stages then fail with `ChatGPT sign-in: <sentence>` and retry under the normal
policy until an administrator signs in again.

## 7. Validation And Tests

- `tests/test_chatgpt.py` - status from the files, private directory and one
  `device-id`, Disconnect, the helper's single mount, typed token failures,
  the mark cleared by a successful refresh, a timed-out helper removed,
  concurrent token requests sharing the lock, sign-in link and stored
  credential, wrong address kept pending, refusals ending the sign-in, cancel
  and expiry, and a helper that shows no link.
- `tests/test_chatgpt_helper_script.py` - runs `adore-chatgpt.mjs` with Node
  against a stub Pi package: refresh-failure causes (only a refused grant asks
  for a new sign-in), the stored or refreshed token, bad requests (skipped
  without Node).
- `tests/test_chatgpt_stage.py` - the stage token reaches only that gate and is
  redacted, a stage override sets the requested token life, no token fails the
  attempt without starting Pi, an API-key project gets no token.
- `tests/test_web_chatgpt.py` - sign-in and Disconnect through the routes,
  refusal codes and audit, cancel, not pending, a local project, a helper that
  cannot start, Admin-only roles and CSRF, and the `executor_sign_in` check for
  `chatgpt` projects only.
- `tests/fake_chatgpt_helper.py` - an offline stand-in for the helper script
  with the same protocol, a fake credential and the `auth.json.lock`
  directory lock; it uses no network and no real token.
- `web/tests/chatgpt.test.mjs` - four-locale copy and error sentences, exact
  status and start transports.
- `web/e2e/executor-config.spec.ts` - "an administrator signs the server in
  with ChatGPT and disconnects it".
- `docker/verify-runtime.sh` step 14 - the helper loads the pinned Pi in the
  built image.

Minimum validation after a change: `uv run --group dev pytest
tests/test_chatgpt.py tests/test_chatgpt_stage.py tests/test_web_chatgpt.py
tests/test_chatgpt_helper_script.py`.

## 8. Limitations And Future Work

- A ChatGPT subscription runs only on the container backend: minting a token
  needs the pinned Pi, which exists only in the executor image until ADORE
  ships its own Pi on the server. `config.py` refuses `chatgpt` with a local
  run.
- Stage limits are at most 3000 s, because the access token is not refreshed
  during a stage.
- There is no callback receiver: the administrator pastes the redirect
  address the browser shows.
- The pending sign-in lives in the web server's memory; a restart ends it.
- One sign-in per ADORE server; projects cannot use different ChatGPT
  accounts.
