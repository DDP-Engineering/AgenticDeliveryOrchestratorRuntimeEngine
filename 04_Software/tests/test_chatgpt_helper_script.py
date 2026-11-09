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
@file test_chatgpt_helper_script.py
@brief ADORE's ChatGPT helper script against a stub Pi package, offline.
@details Runs `docker/pi/adore-chatgpt.mjs` with Node and `ADORE_PI_PACKAGE`
         pointing at a stub of the three Pi modules it imports; the stub's
         refresh fails with the message in `STUB_ERROR`. Skipped without Node.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "docker" / "pi" / "adore-chatgpt.mjs"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node is not installed")

_OAUTH = """export const openaiChatGPTOAuth = {
  async login() { throw new Error("not used"); },
};
"""
_RESOLVE = """export async function refreshStoredOAuthCredential(storage, id, oauth, needs) {
  if (process.env.STUB_ERROR) {
    throw new Error(`OAuth refresh failed for ${id}`, {cause: new Error(process.env.STUB_ERROR)});
  }
  return {type: "oauth", access: "stub-access-token-refreshed", refresh: "r2",
          expires: Date.now() + 3600000};
}
"""
_STORAGE = """export class AuthStorage {
  static create() { return {modify: async (_id, fn) => fn()}; }
}
"""


def stub(root: Path) -> Path:
    """@brief A stub pi-coding-agent package with a nested pi-ai."""
    package = root / "pi-coding-agent"
    ai = package / "node_modules" / "@earendil-works" / "pi-ai"
    for path, text in ((ai / "dist" / "auth" / "oauth" / "openai-chatgpt.js", _OAUTH),
                       (ai / "dist" / "auth" / "resolve.js", _RESOLVE),
                       (package / "dist" / "core" / "auth-storage.js", _STORAGE)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    for directory in (package, ai):
        (directory / "package.json").write_bytes(b'{"type": "module"}\n')
    return package


def run(tmp_path: Path, *args: str, error: str = "", expires_in_ms: int = 60_000) -> dict:
    """@brief Run the script's command against the stub and return its answer."""
    credential = tmp_path / "cred"
    credential.mkdir(exist_ok=True)
    (credential / "auth.json").write_bytes(json.dumps({"openai": {
        "type": "oauth", "access": "stub-access-token-current", "refresh": "r1",
        "expires": int(time.time() * 1000) + expires_in_ms}}).encode("utf-8"))
    env = {**os.environ, "ADORE_PI_PACKAGE": str(stub(tmp_path)),
           "PI_CODING_AGENT_DIR": str(credential), "STUB_ERROR": error}
    done = subprocess.run([NODE, str(SCRIPT), *args], capture_output=True, text=True,  # noqa: S603
                          env=env, timeout=60, check=False)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, (done.stdout, done.stderr)
    return json.loads(lines[0])


@pytest.mark.parametrize(("error", "status"), [
    ('OpenAI OAuth token request failed (400): {"error":"invalid_grant"}', "sign-in-again"),
    ("OpenAI OAuth token request failed (401): unauthorized", "sign-in-again"),
    ("OpenAI OAuth token request failed (403): forbidden", "sign-in-again"),
    ("OpenAI OAuth token request failed (429): rate limited", "unavailable"),
    ("OpenAI OAuth token request failed (408): request timeout", "unavailable"),
    ("OpenAI OAuth token request failed (404): not found", "unavailable"),
    ("OpenAI OAuth token request failed (503): unavailable", "unavailable"),
    ("fetch failed", "unavailable"),
    ("subscription_sharing_user_not_eligible", "not-eligible"),
    ("something unexpected", "failed"),
])
def test_a_refused_refresh_is_reduced_to_one_cause(tmp_path, error, status):
    """@brief Only a refused grant asks for a new sign-in; transient answers do not."""
    assert run(tmp_path, "token", "--min-validity-seconds", "600", error=error) == {
        "status": status}


def test_a_valid_token_needs_no_refresh_and_a_refresh_returns_the_new_one(tmp_path):
    """@brief The stored token when it lasts long enough; otherwise Pi's refreshed one."""
    current = run(tmp_path, "token", "--min-validity-seconds", "600", expires_in_ms=3_000_000)
    assert current["status"] == "ok" and current["token"] == "stub-access-token-current"
    refreshed = run(tmp_path, "token", "--min-validity-seconds", "600")
    assert refreshed["status"] == "ok" and refreshed["token"] == "stub-access-token-refreshed"


@pytest.mark.parametrize("args", [["token"], ["token", "--min-validity-seconds", "0"],
                                  ["token", "--min-validity-seconds", "soon"]])
def test_a_bad_token_request_fails_closed(tmp_path, args):
    """@brief Missing or invalid validity is refused without a token."""
    assert run(tmp_path, *args) == {"status": "failed"}


# END OF FILE
