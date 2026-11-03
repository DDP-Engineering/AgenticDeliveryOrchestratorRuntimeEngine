#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_chatgpt.py
@brief The server's ChatGPT credential: status, disconnect, stage tokens and sign-in.
@details A fake helper (`fake_chatgpt_helper.py`) stands in for Pi in the
         executor image; the fake runtime starts it in place of `<runtime> run`
         and finds the credential directory from the helper's only mount.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
import time

from adore import chatgpt
from adore.chatgpt import ChatGptError
from adore.isolation import ContainerManager
from adore.util import CommandResult
import pytest

FAKE = Path(__file__).with_name("fake_chatgpt_helper.py")
MOUNT = "/adore/chatgpt"
CALLBACK = "http://127.0.0.1:1455/auth/callback"


class FakeRuntime:
    """@brief Fake container runtime: `run` starts the fake helper on the mounted directory."""

    def __init__(self, *options: str, timeout: bool = False) -> None:
        self.options = list(options)
        self.timeout = timeout
        self.calls: list[list[str]] = []

    def _fake(self, argv: list[str]) -> list[str]:
        volumes = [argv[i + 1] for i, part in enumerate(argv) if part == "--volume"]
        assert len(volumes) == 1 and volumes[0].endswith(":" + MOUNT), volumes
        directory = volumes[0][: -len(":" + MOUNT)]
        script = argv.index(chatgpt.CONTAINER_SCRIPT)
        return [sys.executable, "-I", str(FAKE), "--dir", directory, *self.options,
                *argv[script + 1:]]

    def runner(self, argv, **kwargs) -> CommandResult:
        """@brief Run the fake helper for `run`; answer `rm` without a container."""
        argv = [str(part) for part in argv]
        self.calls.append(argv)
        if "run" not in argv:
            return CommandResult(argv)
        if self.timeout:
            return CommandResult(argv, 124, timed_out=True)
        done = subprocess.run(self._fake(argv), capture_output=True, text=True,  # noqa: S603
                              timeout=30, check=False)
        return CommandResult(argv, done.returncode, done.stdout, done.stderr)

    def popen(self, argv, **kwargs):
        """@brief Start the fake login helper with live pipes."""
        argv = [str(part) for part in argv]
        self.calls.append(argv)
        return subprocess.Popen(self._fake(argv), stdin=subprocess.PIPE,  # noqa: S603
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def manager(runtime: FakeRuntime) -> ContainerManager:
    """@brief A container manager bound to the fake runtime."""
    return ContainerManager("docker", "adore-executor-base:1.0.0", "uv", "npm",
                            runtime.runner, run_args=["--userns=keep-id"])


def signed_in(directory: Path, *, expires_in_ms: int = 3_600_000) -> None:
    """@brief Store a fake OAuth credential the way Pi does."""
    chatgpt.prepare(directory)
    (directory / "auth.json").write_text(json.dumps({"openai": {
        "type": "oauth", "access": "fake-access-token-1", "refresh": "fake-refresh-1",
        "expires": int(time.time() * 1000) + expires_in_ms, "clientId": "c", "scopes": []}}))


@pytest.mark.parametrize(("content", "mark", "expected"), [
    (None, False, "not-signed-in"),
    ("{}", False, "not-signed-in"),
    ('{"anthropic": {"type": "api_key", "key": "x"}}', False, "not-signed-in"),
    ('{"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": 1}}', False,
     "signed-in"),
    ('﻿{"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": 1}}', False,
     "signed-in"),
    ('{"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": 1}}', True,
     "sign-in-again"),
    ('{"openai": {"type": "oauth", "access": "a", "expires": 1}}', False, "sign-in-again"),
    ('{"openai": {"type": "api_key", "key": "k"}}', False, "sign-in-again"),
    ("{broken", False, "sign-in-again"),
    ("[]", False, "sign-in-again"),
])
def test_status_reads_the_credential_files_only(tmp_path, content, mark, expected):
    """@brief Three states from fake credential files; nothing is started."""
    directory = tmp_path / "chatgpt"
    if content is not None:
        directory.mkdir()
        (directory / "auth.json").write_text(content, encoding="utf-8")
    if mark:
        (directory / "sign-in-again").write_text("", encoding="utf-8")
    assert chatgpt.status(directory) == expected


def test_credential_directory_is_private_and_keeps_one_device_id(tmp_path):
    """@brief prepare() creates the directory and a stable installation id."""
    directory = chatgpt.credential_dir(tmp_path)
    assert directory == tmp_path / "chatgpt"
    chatgpt.prepare(directory)
    first = (directory / "device-id").read_text(encoding="utf-8")
    chatgpt.prepare(directory)
    assert (directory / "device-id").read_text(encoding="utf-8") == first
    if os.name == "posix":
        assert directory.stat().st_mode & 0o777 == 0o700
        assert (directory / "device-id").stat().st_mode & 0o777 == 0o600


def test_disconnect_deletes_the_credential_and_keeps_the_device_id(tmp_path):
    """@brief Disconnect removes auth.json and the mark; the installation id stays."""
    directory = tmp_path / "chatgpt"
    signed_in(directory)
    (directory / "sign-in-again").write_text("", encoding="utf-8")
    chatgpt.disconnect(directory)
    assert chatgpt.status(directory) == "not-signed-in"
    assert not (directory / "auth.json").exists()
    assert not (directory / "sign-in-again").exists()
    assert (directory / "device-id").is_file()
    chatgpt.disconnect(directory)
    chatgpt.disconnect(tmp_path / "absent")


def test_stage_token_mounts_only_the_credential_directory(tmp_path):
    """@brief One helper container, one read-write mount, token on stdout only."""
    directory = tmp_path / "chatgpt"
    signed_in(directory)
    runtime = FakeRuntime()
    token = chatgpt.bearer_token(manager(runtime), directory, 2100)
    assert token == "fake-access-token-1"
    run = next(argv for argv in runtime.calls if "run" in argv)
    assert run[:4] == ["docker", "run", "--rm", "--name"]
    assert "--pull=never" in run and "--userns=keep-id" in run
    volumes = [run[i + 1] for i, part in enumerate(run) if part == "--volume"]
    assert volumes == [f"{directory.resolve().as_posix()}:{MOUNT}"]
    assert f"PI_CODING_AGENT_DIR={MOUNT}" in run
    assert run[run.index(chatgpt.CONTAINER_SCRIPT) + 1:] == [
        "token", "--min-validity-seconds", "2100"]
    assert "fake-access" not in " ".join(run)


@pytest.mark.parametrize(("setup", "options", "code", "started"), [
    ("none", [], "not-signed-in", False),
    ("marked", [], "sign-in-again", False),
    ("corrupt", [], "sign-in-again", False),
    ("expiring", ["--refuse"], "sign-in-again", True),
    ("valid", ["--answer", "not-eligible"], "not-eligible", True),
    ("valid", ["--answer", "unavailable"], "unavailable", True),
    ("valid", ["--answer", "garbage"], "helper-failed", True),
])
def test_stage_token_failures_are_typed(tmp_path, setup, options, code, started):
    """@brief Missing, refused and unreadable answers fail closed with their code."""
    directory = tmp_path / "chatgpt"
    if setup in {"valid", "marked", "expiring"}:
        signed_in(directory, expires_in_ms=60_000 if setup == "expiring" else 3_600_000)
    if setup == "marked":
        (directory / "sign-in-again").write_text("", encoding="utf-8")
    if setup == "corrupt":
        chatgpt.prepare(directory)
        (directory / "auth.json").write_text("{broken", encoding="utf-8")
    runtime = FakeRuntime(*options)
    with pytest.raises(ChatGptError) as caught:
        chatgpt.bearer_token(manager(runtime), directory, 2100)
    assert caught.value.code == code
    assert caught.value.sentence()
    assert any("run" in argv for argv in runtime.calls) is started
    if setup == "expiring":
        assert chatgpt.status(directory) == "sign-in-again"


def test_a_successful_refresh_clears_the_sign_in_again_mark(tmp_path):
    """@brief The mark is ADORE's memory of a refused refresh; a good token clears it."""
    directory = tmp_path / "chatgpt"
    signed_in(directory, expires_in_ms=60_000)
    assert chatgpt.bearer_token(manager(FakeRuntime()), directory, 2100) == "fake-access-token-2"
    assert chatgpt.status(directory) == "signed-in"


def test_a_helper_timeout_removes_the_helper_container(tmp_path):
    """@brief A wedged helper is reported unavailable and force-removed by name."""
    directory = tmp_path / "chatgpt"
    signed_in(directory)
    runtime = FakeRuntime(timeout=True)
    with pytest.raises(ChatGptError) as caught:
        chatgpt.bearer_token(manager(runtime), directory, 2100)
    assert caught.value.code == "unavailable"
    name = next(argv for argv in runtime.calls if "run" in argv)[4]
    assert ["docker", "rm", "--force", name] in runtime.calls


def test_concurrent_token_requests_share_the_credential_lock(tmp_path):
    """@brief Two stages at once: one rotation, one valid credential, the same token."""
    directory = tmp_path / "chatgpt"
    signed_in(directory, expires_in_ms=60_000)
    tokens: list[str] = []
    threads = [Thread(target=lambda: tokens.append(
        chatgpt.bearer_token(manager(FakeRuntime()), directory, 2100))) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    stored = json.loads((directory / "auth.json").read_text(encoding="utf-8"))["openai"]
    assert tokens == ["fake-access-token-2", "fake-access-token-2"]
    assert stored["refresh"] == "fake-refresh-2"
    assert not (directory / "auth.json.lock").exists()


def start(tmp_path, *options: str) -> tuple[chatgpt.SignIn, FakeRuntime, Path, Path]:
    """@brief Start a fake sign-in that records the pasted line."""
    directory = tmp_path / "chatgpt"
    record = tmp_path / "pasted.txt"
    runtime = FakeRuntime("--record", str(record), *options)
    session = chatgpt.SignIn(manager(runtime), directory, popen=runtime.popen)
    return session, runtime, directory, record


def test_sign_in_returns_the_link_and_stores_the_credential(tmp_path):
    """@brief Link out, matching redirect address in, credential stored, mark cleared."""
    session, runtime, directory, record = start(tmp_path)
    url = session.start()
    assert url.startswith("https://auth.openai.com/") and "state=fake-state" in url
    login = runtime.calls[0]
    assert login[:5] == ["docker", "run", "--rm", "-i", "--name"]
    assert [login[i + 1] for i, part in enumerate(login) if part == "--volume"] == [
        f"{directory.resolve().as_posix()}:{MOUNT}"]
    assert (directory / "device-id").is_file()
    (directory / "sign-in-again").write_text("", encoding="utf-8")
    redirect = f"{CALLBACK}?code=fake-code&state=fake-state-0123456789&client_id=x"
    session.submit(redirect)
    assert record.read_text(encoding="utf-8") == redirect + "\n"
    assert chatgpt.status(directory) == "signed-in"
    assert session.finished


@pytest.mark.parametrize(("address", "code"), [
    ("https://example.com/auth/callback?code=c&state=fake-state-0123456789", "redirect-invalid"),
    ("http://127.0.0.1:1455/other?code=c&state=fake-state-0123456789", "redirect-invalid"),
    (f"{CALLBACK}?state=fake-state-0123456789", "redirect-invalid"),
    ("not a url", "redirect-invalid"),
    (f"{CALLBACK}?code=c&state=another-state", "state-mismatch"),
    (f"{CALLBACK}?code=c", "state-mismatch"),
])
def test_a_wrong_address_is_refused_and_the_sign_in_stays_pending(tmp_path, address, code):
    """@brief Nothing reaches the helper; a correct paste afterwards still signs in."""
    session, _, directory, record = start(tmp_path)
    session.start()
    with pytest.raises(ChatGptError) as caught:
        session.submit(address)
    assert caught.value.code == code
    assert not record.exists() and not session.finished
    session.submit(f"{CALLBACK}?code=c&state=fake-state-0123456789")
    assert chatgpt.status(directory) == "signed-in"


@pytest.mark.parametrize(("address", "options", "code"), [
    (f"{CALLBACK}?error=access_denied&state=fake-state-0123456789", [], "denied"),
    (f"{CALLBACK}?error=subscription_sharing_user_not_eligible&state=fake-state-0123456789",
     [], "not-eligible"),
    (f"{CALLBACK}?error=server_error&state=fake-state-0123456789", [], "refused"),
    (f"{CALLBACK}?code=c&state=fake-state-0123456789", ["--answer", "not-eligible"],
     "not-eligible"),
    (f"{CALLBACK}?code=c&state=fake-state-0123456789", ["--answer", "code-rejected"],
     "code-rejected"),
    (f"{CALLBACK}?code=c&state=fake-state-0123456789", ["--answer", "unavailable"],
     "unavailable"),
])
def test_an_openai_refusal_ends_the_sign_in(tmp_path, address, options, code):
    """@brief A refusal ends the pending sign-in and keeps the stored credential."""
    session, _, directory, _ = start(tmp_path, *options)
    signed_in(directory)
    before = (directory / "auth.json").read_bytes()
    session.start()
    with pytest.raises(ChatGptError) as caught:
        session.submit(address)
    assert caught.value.code == code and session.finished
    assert (directory / "auth.json").read_bytes() == before
    with pytest.raises(ChatGptError) as again:
        session.submit(f"{CALLBACK}?code=c&state=fake-state-0123456789")
    assert again.value.code == "not-pending"


def test_cancel_and_expiry_end_the_helper(tmp_path):
    """@brief Cancel stops the waiting helper; an expired sign-in is not pending."""
    session, runtime, _, _ = start(tmp_path)
    session.start()
    name = runtime.calls[0][5]
    session.cancel()
    assert session.finished and ["docker", "rm", "--force", name] in runtime.calls
    clock = [0.0]
    session, _, _, _ = start(tmp_path)
    session.clock = lambda: clock[0]
    session.start()
    clock[0] = chatgpt.SIGN_IN_SECONDS + 1
    assert session.expired
    with pytest.raises(ChatGptError) as caught:
        session.submit(f"{CALLBACK}?code=c&state=fake-state-0123456789")
    assert caught.value.code == "not-pending"


def test_a_helper_that_never_shows_a_link_is_unavailable(tmp_path):
    """@brief A start that produces no link in time fails and cleans up."""
    session, runtime, _, _ = start(tmp_path, "--hang")
    with pytest.raises(ChatGptError) as caught:
        session.start(timeout=1)
    assert caught.value.code == "unavailable" and session.finished
    assert any(argv[1:3] == ["rm", "--force"] for argv in runtime.calls)


def test_a_helper_silent_after_the_address_is_ended_without_blocking(tmp_path):
    """@brief A helper that never answers is killed and removed; the call returns."""
    session, runtime, _, _ = start(tmp_path, "--hang-after")
    session.start()
    started = time.monotonic()
    with pytest.raises(ChatGptError) as caught:
        session.submit(f"{CALLBACK}?code=c&state=fake-state-0123456789", timeout=1)
    assert caught.value.code == "unavailable" and session.finished
    assert time.monotonic() - started < 10
    assert ["docker", "rm", "--force", session.name] in runtime.calls


def test_a_bounded_runner_timeout_removes_the_helper(tmp_path):
    """@brief A runner that raises TimeoutError (the web probe's bound) still cleans up."""
    directory = tmp_path / "chatgpt"
    signed_in(directory)
    runtime = FakeRuntime()

    def bounded(argv, **kwargs):
        if "run" in [str(part) for part in argv]:
            runtime.calls.append([str(part) for part in argv])
            raise TimeoutError()
        return runtime.runner(argv, **kwargs)

    container = manager(runtime)
    container.runner = bounded
    with pytest.raises(ChatGptError) as caught:
        chatgpt.bearer_token(container, directory, 2100)
    assert caught.value.code == "unavailable"
    name = next(argv for argv in runtime.calls if "run" in argv)[4]
    assert ["docker", "rm", "--force", name] in runtime.calls


def test_an_abandoned_sign_in_ends_itself(tmp_path, monkeypatch):
    """@brief After SIGN_IN_SECONDS the helper is stopped without another request."""
    monkeypatch.setattr(chatgpt, "SIGN_IN_SECONDS", 0.5)
    session, runtime, _, _ = start(tmp_path)
    session.start()
    deadline = time.monotonic() + 10
    while not session.finished and time.monotonic() < deadline:
        time.sleep(0.05)
    assert session.finished
    assert ["docker", "rm", "--force", session.name] in runtime.calls


# END OF FILE
