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
@file fake_chatgpt_helper.py
@brief Offline stand-in for ADORE's ChatGPT helper script in the executor image.
@details Speaks the same one-JSON-object-per-line contract as
         `docker/pi/adore-chatgpt.mjs` against a host credential directory:
         `login` prints an authorization link, reads the pasted redirect
         address and stores a fake OAuth credential; `token` locks
         `auth.json.lock` (a directory, as Pi's proper-lockfile does), rotates
         a credential that expires too soon and prints the access token. No
         network and no real token: values are `fake-access-token-<n>`.
@example python fake_chatgpt_helper.py --dir <cred> token --min-validity-seconds 2100
"""

from __future__ import annotations

# IMPORTS
import argparse
import json
import os
from pathlib import Path
import sys
import time

# CONSTANTS
STATE = "fake-state-0123456789"
AUTHORIZE = ("https://auth.openai.com/api/accounts/authorize?client_id=dynamic_agent_client"
             "&redirect_uri=http%3A%2F%2F127.0.0.1%3A1455%2Fauth%2Fcallback&state=" + STATE)
HOUR_MS = 3_600_000


# HELPER FUNCTIONS


def emit(value: dict) -> None:
    """@brief Write one protocol line and flush it."""
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()


def credential(number: int) -> dict:
    """@brief A fake OAuth credential, rotation `number`, valid for one hour."""
    return {"type": "oauth", "access": f"fake-access-token-{number}",
            "refresh": f"fake-refresh-{number}",
            "expires": int(time.time() * 1000) + HOUR_MS, "clientId": "fake-client",
            "scopes": ["openid", "offline_access"]}


def write_auth(directory: Path, data: dict) -> None:
    """@brief Replace auth.json with mode 0600."""
    path = directory / "auth.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    path.chmod(0o600)


def login(directory: Path, options) -> int:
    """@brief Emulate `adore-chatgpt.mjs login`."""
    if not (directory / "device-id").is_file():
        emit({"event": "error", "code": "failed"})
        return 1
    if options.hang:
        time.sleep(600)
    emit({"event": "auth_url", "url": AUTHORIZE})
    line = sys.stdin.readline()
    if options.record:
        Path(options.record).write_text(line, encoding="utf-8")
    if not line:
        emit({"event": "error", "code": "failed"})
        return 1
    if options.hang_after:
        time.sleep(600)
    if options.answer != "signed-in":
        emit({"event": "error", "code": options.answer})
        return 1
    write_auth(directory, {"openai": credential(1)})
    emit({"event": "signed-in"})
    return 0


def token(directory: Path, options) -> int:
    """@brief Emulate `adore-chatgpt.mjs token` under the credential lock."""
    if options.answer == "garbage":
        print("not json")
        return 0
    if options.answer != "signed-in":
        emit({"status": options.answer})
        return 1
    lock = directory / "auth.json.lock"
    deadline = time.monotonic() + 10
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                emit({"status": "unavailable"})
                return 1
            time.sleep(0.02)
    try:
        data = json.loads((directory / "auth.json").read_text(encoding="utf-8"))
        current = data.get("openai")
        if not current:
            emit({"status": "not-signed-in"})
            return 1
        if current["expires"] - time.time() * 1000 < options.min_validity_seconds * 1000:
            if options.refuse:
                emit({"status": "sign-in-again"})
                return 1
            number = int(current["refresh"].rsplit("-", 1)[1]) + 1
            time.sleep(0.3)
            current = credential(number)
            write_auth(directory, {**data, "openai": current})
    finally:
        lock.rmdir()
    emit({"status": "ok", "token": current["access"], "expires": current["expires"]})
    return 0


# PUBLIC API


def main() -> int:
    """@brief Parse the helper command and run it."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--answer", default="signed-in")
    parser.add_argument("--record", default="")
    parser.add_argument("--hang", action="store_true")
    parser.add_argument("--hang-after", action="store_true")
    parser.add_argument("--refuse", action="store_true")
    parser.add_argument("command", choices=("login", "token"))
    parser.add_argument("--min-validity-seconds", type=int, default=0)
    options = parser.parse_args()
    directory = Path(options.dir)
    if not directory.is_dir() or os.environ.get("FAKE_HELPER_FAIL"):
        return 127
    return login(directory, options) if options.command == "login" else token(directory, options)


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
