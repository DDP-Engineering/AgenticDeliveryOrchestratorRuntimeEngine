#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file chatgpt.py
@brief The ADORE server's one ChatGPT sign-in and the short-lived tokens runs get.
@details One ChatGPT Plus/Pro credential per ADORE server lives in
         `<ADORE home>/chatgpt/`: Pi's `auth.json` (and its lock directory
         `auth.json.lock`), ADORE's stable installation id `device-id` (the
         OpenAI agent host id) and the mark `sign-in-again`, written when
         OpenAI refused a refresh. No run container ever mounts it.

         Pi does every OAuth step itself: ADORE's helper script
         (`/opt/adore/pi/adore-chatgpt.mjs` in the executor image) runs in a
         one-off helper container whose only mount is this directory, or as
         a trusted native process using ADORE-managed Node/Pi. `login`
         prints the authorization link and waits for the native callback
         or the pasted browser redirect address; `token` returns an access
         token valid for a requested time,
         refreshing it under Pi's credential lock. A stage then receives only
         that access token as `OPENAI_API_KEY`; the refresh token stays here.

         Status is read from the files without starting Pi. Messages never
         carry a token, code, link or redirect address.
"""

from __future__ import annotations

# IMPORTS
from collections.abc import Callable
from contextlib import suppress
import json
import math
import os
from pathlib import Path
from queue import Empty, Queue
import re
import subprocess
from threading import Lock, Thread, Timer
from time import monotonic, time
from typing import Any
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

from adore.branding import (
    CHATGPT_CREDENTIAL_DIR,
    CONTAINER_CHATGPT_MOUNT,
    CONTAINER_PI_CHATGPT_SCRIPT,
)
from adore.resource_lock import ResourceLockError, atomic_write, resource_lock
from adore.util import background_process_options, run_command, strict_json_loads

# CONSTANTS
CONTAINER_SCRIPT = CONTAINER_PI_CHATGPT_SCRIPT
AUTH_FILE = "auth.json"
DEVICE_FILE = "device-id"
MARK_FILE = "sign-in-again"
#: The redirect address of Pi's OpenAI sign-in; a browser without Pi beside it
#: fails to load it, and the administrator pastes it into ADORE.
CALLBACK_URL = "http://127.0.0.1:1455/auth/callback"
AUTHORIZE_PREFIX = "https://auth.openai.com/"
#: Longest stage limit a ChatGPT project accepts: an access token lasts 60
#: minutes minus Pi's 3-minute margin, and ADORE asks for 5 minutes more.
MAX_STAGE_SECONDS = 3000
TOKEN_MARGIN_SECONDS = 300
#: The only variable a ChatGPT stage receives (Pi provider `openai`).
TOKEN_VARIABLE = "OPENAI_API_KEY"
#: How long a started sign-in waits for the redirect address.
SIGN_IN_SECONDS = 900
TOKEN_TIMEOUT_SECONDS = 90.0
STATUSES = ("signed-in", "not-signed-in", "sign-in-again")
#: Environment of a helper container: Pi's agent directory is the mount.
HELPER_ENV = {
    "PI_CODING_AGENT_DIR": CONTAINER_CHATGPT_MOUNT,
    "PI_TELEMETRY": "0",
    "PI_SKIP_VERSION_CHECK": "1",
}
#: Cause codes the helper script may answer with.
HELPER_CODES = frozenset({
    "not-signed-in", "sign-in-again", "not-eligible", "denied", "code-rejected",
    "unavailable", "unreadable", "too-long", "refused", "failed",
})
#: One English sentence per cause, for run evidence and logs.
SENTENCES = {
    "not-signed-in": "ADORE is not signed in with ChatGPT; an administrator signs in under "
                     "Settings > Agent and model.",
    "sign-in-again": "The ChatGPT sign-in can no longer be refreshed; an administrator signs in "
                     "again under Settings > Agent and model.",
    "not-eligible": "OpenAI refused the ChatGPT account: its plan cannot share the subscription "
                    "with Pi (subscription_sharing_user_not_eligible).",
    "denied": "The ChatGPT sign-in was declined in the browser.",
    "code-rejected": "OpenAI rejected the sign-in code; it expired or was already used. Start "
                     "the sign-in again.",
    "refused": "OpenAI refused the ChatGPT sign-in.",
    "unavailable": "OpenAI could not be reached for the ChatGPT sign-in; check the server's "
                   "network and try again.",
    "unreadable": "The stored ChatGPT sign-in cannot be read; disconnect it, then sign in again.",
    "too-long": "A ChatGPT access token does not last as long as this stage limit; use a stage "
                f"limit of at most {MAX_STAGE_SECONDS} seconds.",
    "redirect-invalid": f"Paste the full address the browser showed, starting with {CALLBACK_URL}.",
    "state-mismatch": "This address belongs to another sign-in attempt; paste the address that "
                      "follows the latest link.",
    "not-pending": "No ChatGPT sign-in is waiting; start it again.",
    "helper-failed": "ADORE's ChatGPT helper could not run. For native execution check "
                     "Node and run 'adore pi install'; for containers rebuild the executor image.",
    "failed": "The ChatGPT sign-in failed.",
}
_TOKEN_RE = re.compile(r"[A-Za-z0-9._~+/=-]{16,16384}")
_STATE_RE = re.compile(r"[A-Za-z0-9._~-]{8,512}")
_AUTH_LIMIT = 1_048_576
_LINE_LIMIT = 65_536
_EOF = object()

# DATA MODELS / TYPEDEFINITIONS


class ChatGptError(RuntimeError):
    """
    @brief   A typed, value-free ChatGPT sign-in or token failure.
    @details `code` is one of `SENTENCES`; the interface localizes it.
    """

    def __init__(self, code: str) -> None:
        """@brief Carry one cause code."""
        super().__init__(code)
        self.code = code if isinstance(code, str) and code in SENTENCES else "failed"

    def sentence(self) -> str:
        """@brief The English sentence for evidence and logs."""
        return SENTENCES[self.code]


# HELPER FUNCTIONS


class NativeHelper:
    """@brief Trusted native OAuth transport, with no project code or shell.
    @details Uses only verified managed Node/Pi and the packaged helper. The
             helper never loads project extensions and never starts children.
    """

    def __init__(self, *, runner=run_command) -> None:
        """@brief Bind the injectable native command boundary."""
        self.runner = runner

    def command(self, directory: Path, args: list[str]) -> tuple[list[str], dict]:
        """@brief Return verified argv and an isolated native child environment.
        @param[in] directory ADORE-owned credential directory outside the project.
        @param[in] args Trusted helper operation and validity limit.
        @return Native argv and explicit cwd/environment options.
        @exception ChatGptError Missing managed prerequisites or packaged helper.
        """
        from adore.pi_installation import PI_PACKAGE, PiInstallationError, verify_pi

        script = Path(__file__).with_name("executor") / "adore-chatgpt.mjs"
        try:
            pi = verify_pi(runner=self.runner)
            if not script.is_file() or script.is_symlink():
                raise ChatGptError("helper-failed")
        except TimeoutError as exc:
            raise ChatGptError("unavailable") from exc
        except (PiInstallationError, OSError) as exc:
            raise ChatGptError("helper-failed") from exc
        directory = directory.resolve()
        keep = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR",
                "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS"}
        env = {key: value for key, value in os.environ.items() if key.upper() in keep}
        env.update(PI_CODING_AGENT_DIR=str(directory), PI_TELEMETRY="0",
                   PI_SKIP_VERSION_CHECK="1", HOME=str(directory), USERPROFILE=str(directory),
                   APPDATA=str(directory), LOCALAPPDATA=str(directory),
                   XDG_CONFIG_HOME=str(directory), XDG_CACHE_HOME=str(directory),
                   PATH=str(pi.node.parent),
                   ADORE_PI_PACKAGE=str(pi.prefix / "node_modules" / PI_PACKAGE))
        return [str(pi.node), str(script), *args], {"cwd": directory, "env": env}


def helper_for(config, manager, *, runner=None):
    """@brief Select trusted native OAuth or the existing project helper container.
    @param[in] config Validated project snapshot.
    @param[in] manager Container manager retained for container projects.
    @param[in] runner Optional injectable native command boundary.
    @return The helper transport for this backend.
    """
    if config.execution.backend == "local":
        return NativeHelper(runner=runner or run_command)
    return manager


def _command(manager, name: str, directory: Path, args: list[str], *, interactive=False):
    """@brief Build one helper operation without changing its shared protocol."""
    if isinstance(manager, NativeHelper):
        return manager.command(directory, args)
    return manager.helper_command(
        name, ["node", CONTAINER_SCRIPT, *args],
        mount=(directory, CONTAINER_CHATGPT_MOUNT), env=HELPER_ENV,
        interactive=interactive), {}


def _helper_name() -> str:
    """@brief A unique helper operation name."""
    return "adore-chatgpt-" + uuid4().hex[:16]


def _answer(stdout: str) -> dict | None:
    """
    @brief      The helper's answer: its last non-empty line as one JSON object.
    @param[in]  stdout Captured helper output.
    @return     The object, or None when the output is not the protocol.
    """
    lines = [line for line in stdout[-_LINE_LIMIT:].splitlines() if line.strip()]
    if not lines:
        return None
    try:
        value = strict_json_loads(lines[-1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _unmark(directory: Path) -> None:
    """@brief Forget a refused refresh."""
    (directory / MARK_FILE).unlink(missing_ok=True)


def _mark(directory: Path) -> None:
    """@brief Remember that OpenAI refused the last refresh."""
    (directory / MARK_FILE).write_bytes(b"")


def _remove_helper(manager, name: str) -> None:
    """
    @brief      Remove a stopped-waiting helper container, even past a caller's bound.
    @details    Ending the runtime client does not stop the container. A
                bounded runner (the web probe's) raises again once its deadline
                is gone, so removal then runs on its own short bound.
    @param[in]  manager ContainerManager that started the helper.
    @param[in]  name Owned helper name.
    """
    if isinstance(manager, NativeHelper):
        return
    try:
        manager.remove_helper(name)
    except (TimeoutError, OSError):
        run_command([*manager.runtime_argv, "rm", "--force", name], timeout=15)


def _query(url: str) -> dict[str, str] | None:
    """@brief Single-valued query parameters, or None for a repeated name."""
    pairs = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    values = dict(pairs)
    return values if len(values) == len(pairs) else None


# PUBLIC API


def credential_dir(home: str | Path | None = None) -> Path:
    """
    @brief      The server's ChatGPT credential directory.
    @param[in]  home ADORE home; the resolved `adore_home()` when omitted.
    @return     `<home>/chatgpt`.
    """
    if home is None:
        from adore.profiles import adore_home

        home = adore_home()
    return Path(home) / CHATGPT_CREDENTIAL_DIR


def prepare(directory: Path) -> Path:
    """
    @brief      Create the private directory and its stable installation id.
    @details    The id is a UUID written once with mode 0600 and kept across
                sign-ins and Disconnect, so OpenAI sees one agent host.
    @param[in]  directory Credential directory.
    @return     The directory.
    @exception  OSError When the directory cannot be created.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        directory.chmod(0o700)
    device = directory / DEVICE_FILE
    try:
        with resource_lock(directory / "device.lock"):
            if device.is_symlink() or device.exists() and not device.is_file():
                raise OSError("ChatGPT device identity storage is unsafe")
            if not device.exists():
                atomic_write(device, str(uuid4()) + "\n")
    except ResourceLockError as exc:
        raise OSError("ChatGPT device identity is busy or unavailable") from exc
    return directory


def status(directory: Path) -> str:
    """
    @brief      The sign-in status, read from the files without starting Pi.
    @param[in]  directory Credential directory.
    @return     `not-signed-in` without an OpenAI entry; `sign-in-again` for an
                unreadable file or entry, or after a refused refresh;
                otherwise `signed-in`.
    """
    path = directory / AUTH_FILE
    try:
        if path.is_symlink() or (path.exists() and (not path.is_file()
                                                    or path.stat().st_size > _AUTH_LIMIT)):
            return "sign-in-again"
        raw = path.read_bytes()
    except FileNotFoundError:
        return "not-signed-in"
    except OSError:
        return "sign-in-again"
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        return "sign-in-again"
    if not isinstance(data, dict):
        return "sign-in-again"
    entry = data.get("openai")
    if entry is None:
        return "not-signed-in"
    if (not isinstance(entry, dict) or entry.get("type") != "oauth"
            or not all(isinstance(entry.get(key), str) and entry[key]
                       for key in ("access", "refresh"))
            or isinstance(entry.get("expires"), bool)
            or not isinstance(entry.get("expires"), int | float)):
        return "sign-in-again"
    return "sign-in-again" if (directory / MARK_FILE).exists() else "signed-in"


def disconnect(directory: Path) -> None:
    """
    @brief      Delete the stored credential and the mark; keep the installation id.
    @param[in]  directory Credential directory.
    @exception  OSError When a file cannot be removed.
    """
    if not directory.exists():
        return
    try:
        with resource_lock(directory / "refresh.lock"):
            for name in (AUTH_FILE, MARK_FILE):
                (directory / name).unlink(missing_ok=True)
    except ResourceLockError as exc:
        raise OSError("ChatGPT credential mutation is busy or unavailable") from exc


def check_redirect(url: object, state: str) -> str:
    """
    @brief      Validate a pasted redirect address before Pi sees it.
    @details    The address must be Pi's callback with a code and the `state`
                of the pending link; an `error` parameter is OpenAI's refusal.
    @param[in]  url The pasted address.
    @param[in]  state `state` of the pending authorization link.
    @return     The address, trimmed.
    @exception  ChatGptError redirect-invalid, state-mismatch, or a refusal
                (denied, not-eligible, refused).
    """
    if not isinstance(url, str):
        raise ChatGptError("redirect-invalid")
    url = url.strip()
    if (not url or len(url) > 8192 or any(ord(char) <= 32 or ord(char) == 127 for char in url)):
        raise ChatGptError("redirect-invalid")
    try:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}{parts.path}"
    except ValueError as exc:
        raise ChatGptError("redirect-invalid") from exc
    query = _query(url)
    if origin != CALLBACK_URL or query is None:
        raise ChatGptError("redirect-invalid")
    if query.get("error"):
        if query.get("state") not in (None, state):
            raise ChatGptError("state-mismatch")
        raise ChatGptError({"access_denied": "denied",
                            "subscription_sharing_user_not_eligible": "not-eligible"}
                           .get(query["error"], "refused"))
    if not query.get("code"):
        raise ChatGptError("redirect-invalid")
    if query.get("state") != state:
        raise ChatGptError("state-mismatch")
    return url


def bearer_token(manager, directory: Path, min_validity_seconds: int, *,
                 timeout: float = TOKEN_TIMEOUT_SECONDS) -> str:
    """
    @brief      An access token valid for at least `min_validity_seconds`.
    @details    Runs Pi through the selected trusted native/container helper;
                only the helper opens the credential store. Pi refreshes an expiring
                credential under its own lock. A refused refresh marks the
                status sign-in-again; a good answer clears the mark. Nothing
                starts when the status is not signed-in.
    @param[in]  manager Selected NativeHelper or project ContainerManager.
    @param[in]  directory Credential directory.
    @param[in]  min_validity_seconds Seconds the token must stay valid.
    @param[in]  timeout Wall-clock bound of the helper.
    @return     The access token (memory only).
    @exception  ChatGptError With the cause code.
    """
    try:
        with resource_lock(directory / "refresh.lock", timeout=timeout):
            state = status(directory)
            if state != "signed-in":
                raise ChatGptError(state)
            name = _helper_name()
            argv, options = _command(
                manager, name, directory,
                ["token", "--min-validity-seconds", str(int(min_validity_seconds))])
            try:
                result = manager.runner(argv, timeout=timeout, **options)
            except TimeoutError as exc:
                _remove_helper(manager, name)
                raise ChatGptError("unavailable") from exc
            except OSError as exc:
                raise ChatGptError("helper-failed") from exc
            if result.timed_out:
                _remove_helper(manager, name)
                raise ChatGptError("unavailable")
            answer = _answer(result.stdout)
            code = answer.get("status") if answer else None
            if (result.ok and code == "ok" and set(answer) == {"status", "token", "expires"}
                    and isinstance(answer["token"], str) and _TOKEN_RE.fullmatch(answer["token"])
                    and type(answer["expires"]) in (int, float)
                    and (type(answer["expires"]) is int or math.isfinite(answer["expires"]))
                    and answer["expires"] >= (time() + min_validity_seconds) * 1000):
                _unmark(directory)
                return answer["token"]
            if code == "sign-in-again":
                _mark(directory)
            raise ChatGptError(
                code if isinstance(code, str) and code in HELPER_CODES else "helper-failed")
    except ResourceLockError as exc:
        raise ChatGptError("unavailable") from exc


class SignIn:
    """
    @brief   One pending Sign in with ChatGPT, held by the web server.
    @details `start` runs the helper's `login` in an interactive helper
             container and returns OpenAI's authorization link; `submit`
             validates the pasted redirect address and passes it on; the
             helper stores the credential through Pi's own store. A sign-in
             ends on success, on a refusal, on `cancel` or after
             `SIGN_IN_SECONDS`.
    """

    def __init__(self, manager, directory: Path, *,
                 popen: Callable[..., Any] = subprocess.Popen,
                 clock: Callable[[], float] = monotonic) -> None:
        """
        @brief      Bind a sign-in to the selected trusted helper transport.
        @param[in]  manager NativeHelper or the project's ContainerManager.
        @param[in]  directory Credential directory.
        @param[in]  popen Process factory (tests inject a fake helper).
        @param[in]  clock Monotonic clock (tests move it).
        """
        self.manager, self.directory = manager, directory
        self.popen, self.clock = popen, clock
        self.name = _helper_name()
        self.process = None
        self.state = ""
        self.started_at: float | None = None
        self.finished = False
        self._lines: Queue = Queue()
        self._lock = Lock()

    @property
    def expired(self) -> bool:
        """@brief Whether the sign-in waited longer than `SIGN_IN_SECONDS`."""
        return (self.started_at is not None
                and self.clock() - self.started_at > SIGN_IN_SECONDS)

    @property
    def pending(self) -> bool:
        """@brief Whether a redirect address can still be submitted."""
        return self.started_at is not None and not self.finished and not self.expired

    def _read(self, stream) -> None:
        """@brief Reader thread: queue each protocol object, then end-of-output."""
        try:
            for raw in iter(lambda: stream.readline(_LINE_LIMIT), b""):
                try:
                    value = strict_json_loads(raw.decode("utf-8"))
                except (UnicodeError, ValueError):
                    continue
                if isinstance(value, dict):
                    self._lines.put(value)
        except (OSError, ValueError):
            pass
        self._lines.put(_EOF)

    def _next(self, timeout: float) -> object:
        """@brief The next protocol object, `_EOF`, or None after `timeout`."""
        try:
            return self._lines.get(timeout=timeout)
        except Empty:
            return None

    def _end(self, answered: bool) -> bool:
        """
        @brief      Mark finished and make sure the helper is gone.
        @details    A helper that answered exits on its own once its stdin
                    closes; a silent one is killed and its container removed
                    at once. The reader thread owns stdout and ends at EOF, so
                    stdout is never closed here (closing it would wait for a
                    blocked read).
        @param[in]  answered Whether the helper sent its final answer.
        @return     True only for a clean helper exit before forced cleanup.
        """
        self.finished = True
        process = self.process
        if process is None:
            return False
        with suppress(OSError, ValueError):
            process.stdin.close()
        if answered:
            try:
                return process.wait(timeout=10) == 0
            except subprocess.TimeoutExpired:
                pass
        process.kill()
        _remove_helper(self.manager, self.name)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=10)
        return False

    def start(self, timeout: float = 60.0) -> str:
        """
        @brief      Start the helper and return OpenAI's authorization link.
        @param[in]  timeout Seconds to wait for the link.
        @return     The link (shown to the administrator, never logged).
        @exception  ChatGptError unavailable (no link in time), helper-failed,
                    or the helper's cause code.
        """
        prepare(self.directory)
        argv, options = _command(self.manager, self.name, self.directory, ["login"],
                                 interactive=True)
        try:
            self.process = self.popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, **options,
                                      **background_process_options())
        except OSError as exc:
            self.finished = True
            raise ChatGptError("helper-failed") from exc
        Thread(target=self._read, args=(self.process.stdout,), daemon=True).start()
        answer = self._next(timeout)
        url = answer.get("url") if isinstance(answer, dict) else None
        if (isinstance(answer, dict) and answer.get("event") == "auth_url"
                and isinstance(url, str) and url.startswith(AUTHORIZE_PREFIX) and len(url) <= 8192):
            query = _query(url)
            state = query.get("state", "") if query else ""
            if _STATE_RE.fullmatch(state):
                self.state, self.started_at = state, self.clock()
                # An abandoned sign-in stops its helper by itself.
                expiry = Timer(SIGN_IN_SECONDS, self.cancel)
                expiry.daemon = True
                expiry.start()
                return url
        self.cancel()
        if answer is None:
            raise ChatGptError("unavailable")
        code = answer.get("code") if isinstance(answer, dict) else None
        raise ChatGptError(
            code if isinstance(code, str) and code in HELPER_CODES else "helper-failed")

    def _finish(self, answer: object) -> None:
        """@brief Validate and reap a manual or automatic helper completion.
        @param[in] answer Untrusted helper protocol object or end-of-output.
        @exception ChatGptError Refusal, corrupt store, bad output or failed exit.
        """
        clean_exit = self._end(isinstance(answer, dict))
        if isinstance(answer, dict) and answer.get("event") == "signed-in":
            if not clean_exit:
                raise ChatGptError("helper-failed")
            _unmark(self.directory)
            if status(self.directory) != "signed-in":
                raise ChatGptError("unreadable")
            return
        if answer is None:
            raise ChatGptError("unavailable")
        code = answer.get("code") if isinstance(answer, dict) else None
        raise ChatGptError(
            code if isinstance(code, str) and code in HELPER_CODES else "helper-failed")

    def _poll(self, timeout: float = 0) -> bool:
        """@brief Consume a queued completion without requiring a manual redirect.
        @param[in] timeout Bounded grace for a pipe-close/completion race.
        @return True for completed login, False if no event is queued.
        @exception ChatGptError A queued failure or invalid completion.
        """
        answer = self._next(timeout)
        if answer is None:
            return False
        self._finish(answer)
        return True

    def poll(self) -> bool:
        """@brief Observe an already-running helper's automatic callback completion.
        @return True when completed, False while still waiting or already ended.
        @exception ChatGptError A queued refusal or invalid completion.
        @note Starts no process and performs no new model or refresh request.
        """
        with self._lock:
            return self._poll() if self.pending else False

    def submit(self, url: object, timeout: float = 60.0) -> None:
        """
        @brief      Pass the pasted redirect address to the waiting sign-in.
        @details    A malformed address or another attempt's `state` is refused
                    and the sign-in stays pending; an OpenAI refusal ends it.
        @param[in]  url The redirect address the browser showed.
        @param[in]  timeout Seconds to wait for Pi's answer.
        @exception  ChatGptError With the cause code.
        """
        with self._lock:
            if not self.pending:
                raise ChatGptError("not-pending")
            try:
                address = check_redirect(url, self.state)
            except ChatGptError as exc:
                if exc.code not in {"redirect-invalid", "state-mismatch"}:
                    self.cancel()
                raise
            if self._poll():
                return
            try:
                self.process.stdin.write(address.encode("utf-8") + b"\n")
                self.process.stdin.flush()
            except (OSError, ValueError) as exc:
                # Pi may have won the race through its native loopback callback.
                if self._poll(timeout=1):
                    return
                self.cancel()
                raise ChatGptError("helper-failed") from exc
            self._finish(self._next(timeout))

    def cancel(self) -> None:
        """@brief End the sign-in and remove its helper container (idempotent)."""
        if self.finished:
            return
        self.finished = True
        process = self.process
        if process is not None and process.poll() is None:
            process.kill()
        if process is not None:
            _remove_helper(self.manager, self.name)
            with suppress(subprocess.TimeoutExpired):
                process.wait(timeout=10)


# END OF FILE
