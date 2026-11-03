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
@file test_chatgpt_stage.py
@brief A ChatGPT stage gets only a short-lived access token, in that gate's environment.
@details The conductor is wired with fakes; the token source stands in for the
         helper container that refreshes the server's sign-in.
"""

from __future__ import annotations

from adore.chatgpt import TOKEN_MARGIN_SECONDS, ChatGptError
from adore.executor.base import GateRun
import pytest

from tests.test_orchestrator import FakeExecutor, make_engine, make_run, task

TOKEN = "eyJ-fake-access-token-for-one-stage"


class RecordingExecutor(FakeExecutor):
    """@brief Keep the bound target each gate received."""

    def __init__(self) -> None:
        super().__init__(GateRun(exit_code=0))
        self.targets: list = []

    def run_gate(self, execute, worktree, io_dir, prompt, **kwargs):
        self.targets.append(execute)
        return super().run_gate(execute, worktree, io_dir, prompt, **kwargs)


def chatgpt_engine(tmp_path, source):
    """@brief A conductor for a ChatGPT project with an injected token source."""
    executor = RecordingExecutor()
    engine, *_ = make_engine(tmp_path, executor=executor)
    engine.config.executor.provider = "chatgpt"
    engine.config.executor.model = "gpt-5.6-luna"
    engine.config.budgets.per_gate_timeout_seconds = 1800
    engine.chatgpt_token = source
    run = make_run(engine)
    run.stage = "build"
    return engine, executor, run


def test_the_stage_token_reaches_only_this_gate_and_is_redacted(tmp_path):
    """@brief OPENAI_API_KEY in the gate env, valid for the stage limit plus the margin."""
    asked: list[int] = []
    engine, executor, run = chatgpt_engine(tmp_path, lambda seconds: asked.append(seconds) or TOKEN)
    result = engine._launch_stage(run, engine.forge.ticket, task("build"))
    assert result.exit_code == 0 and asked == [1800 + TOKEN_MARGIN_SECONDS]
    target = executor.targets[0]
    assert target.env["OPENAI_API_KEY"] == TOKEN
    assert target.redact(f"echo {TOKEN} done") == "echo [REDACTED] done"
    assert "OPENAI_API_KEY" not in engine._container_env(run)
    assert TOKEN not in str(engine.store.load(run.run_id).__dict__)


def test_a_stage_override_sets_the_requested_token_life(tmp_path):
    """@brief The stage's own limit decides how long the token must last."""
    asked: list[int] = []
    engine, _, run = chatgpt_engine(tmp_path, lambda seconds: asked.append(seconds) or TOKEN)
    engine.config.workflow.stage_timeout_overrides = {"build": 2400}
    engine._launch_stage(run, engine.forge.ticket, task("build"))
    assert asked == [2400 + TOKEN_MARGIN_SECONDS]


@pytest.mark.parametrize(("code", "words"), [
    ("not-signed-in", "not signed in with ChatGPT"),
    ("sign-in-again", "signs in again"),
    ("not-eligible", "subscription_sharing_user_not_eligible"),
    ("unavailable", "could not be reached"),
])
def test_no_token_fails_the_attempt_without_starting_pi(tmp_path, code, words):
    """@brief The attempt fails with the cause sentence; Pi never starts."""
    def refuse(_seconds):
        raise ChatGptError(code)

    engine, executor, run = chatgpt_engine(tmp_path, refuse)
    result = engine._launch_stage(run, engine.forge.ticket, task("build"))
    assert result.exit_code == 1 and words in result.stderr
    assert executor.prompts == [] and executor.targets == []


def test_an_api_key_project_gets_no_token(tmp_path):
    """@brief Only provider chatgpt asks for a ChatGPT token."""
    engine, executor, run = chatgpt_engine(tmp_path, lambda _s: pytest.fail("token requested"))
    engine.config.executor.provider = "openai"
    engine._launch_stage(run, engine.forge.ticket, task("build"))
    assert "OPENAI_API_KEY" not in executor.targets[0].env


# END OF FILE
