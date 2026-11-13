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
@file    test_prompts.py
@brief   File-backed prompt contracts and pre-extraction byte oracles.
@details Offline resources and fake conductors exercise eager failure, literal
         data insertion and unchanged selection/whitespace. Baseline expectations
         were captured from original code before extracting any prompt literals.
"""

# IMPORTS
from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
from string import Template

from adore import orchestrator as orchestrator_module
from adore.config import egress_policy
from adore.executor.base import GateRun
from adore.executor.launcher import PiExecutor, pi_rpc_argv
from adore.util import CommandResult
import pytest

from tests.test_orchestrator import (
    TASK_ID,
    FakeAegis,
    make_config,
    make_engine,
    make_run,
    task,
)
from tests.test_pi_rpc import FakePi, SpawnTarget

# CONSTANTS
BASELINE = json.loads((Path(__file__).parent / "fixtures/prompts/baseline.json").read_text(
    encoding="utf-8"))
NETWORK_BASELINE = json.loads((Path(__file__).parent / "fixtures/prompts/network-baseline.json")
                              .read_text(encoding="utf-8"))


# HELPER FUNCTIONS
@pytest.fixture
def prompts():
    """@brief Require the catalog behavior before importing the new module."""
    assert importlib.util.find_spec("adore.prompts") is not None, "prompt catalog is missing"
    return importlib.import_module("adore.prompts")


@pytest.fixture
def resources(tmp_path, monkeypatch, prompts):
    """@brief Copy all shipped files and redirect only the test resource seam."""
    root = tmp_path / "prompts"
    shutil.copytree(prompts.PROMPT_ROOT, root)
    monkeypatch.setattr(prompts, "PROMPT_ROOT", root)
    return root


# PUBLIC API
@pytest.mark.parametrize("case", BASELINE["cases"], ids=lambda c: (
    f"{c['stage']}-{c['quick']}-{c['packages']}-{c['mode']}-{c['extra']}"))
def test_stage_bytes(tmp_path, case):
    """@brief Preserve historical captures; mode here is requested, not effective.

    @note All historical container captures used internet=False, hence the
          allowlist proxy. The supplemental matrix proves effective policies.
    """
    engine, forge, *_ = make_engine(tmp_path)
    values = BASELINE["values"]
    forge.ticket.title = values["title"]
    forge.ticket.description = " \n" + values["description"] + "\n "
    forge.ticket.labels = ["agent-quick"] if case["quick"] else []
    engine.config.execution.backend = "local" if case["mode"] == "native" else "container"
    engine.config.container.system_packages = case["packages"]
    engine.config.container.egress.mode = "open" if case["mode"] == "native" else case["mode"]
    actual = engine._stage_prompt(make_run(engine), forge.ticket, task(case["stage"]),
                                 values["context"] if case["extra"] else "",
                                 values["thread"] if case["extra"] else "")
    assert actual.encode("utf-8") == case["expected"].encode("utf-8")


def test_network_oracle_covers_effective_policies():
    """@brief Captures distinguish reachable policies, native and injected none."""
    cases = NETWORK_BASELINE["cases"]
    assert Counter(case["effective_mode"] for case in cases) == {
        "open": 6, "allowlist-proxy": 6, "native": 2, "none": 2,
    }
    assert {(case["requested_mode"], case["internet"], case["packages"])
            for case in cases if not case["injected_none"]
            and case["effective_mode"] != "native"} == {
                (mode, internet, packages)
                for mode in ("open", "none", "allowlist-proxy")
                for internet in (False, True) for packages in (False, True)
            }
    for case in cases:
        mode = case["effective_mode"]
        assert case["injected_none"] == (mode == "none")
        if mode == "native":
            assert "Network policy is independently configured as" not in case["expected"]
        else:
            assert f"Network policy is independently configured as {mode}." in case["expected"]


@pytest.mark.parametrize("case", NETWORK_BASELINE["cases"], ids=lambda c: (
    f"{c['requested_mode']}-internet-{c['internet']}-packages-{c['packages']}"
    f"-injected-{c['injected_none']}"))
def test_effective_network_stage_bytes(tmp_path, monkeypatch, case):
    """@brief Real effective policies match original bytes; none is composition-only."""
    engine, forge, *_ = make_engine(tmp_path)
    values = BASELINE["values"]
    forge.ticket.title = values["title"]
    forge.ticket.description = " \n" + values["description"] + "\n "
    forge.ticket.labels = ["agent-quick"]
    native = case["requested_mode"] == "native"
    engine.config.execution.backend = "local" if native else "container"
    engine.config.container.system_packages = case["packages"]
    engine.config.container.egress.mode = "open" if native else case["requested_mode"]
    engine.config.executor.internet = case["internet"]
    effective = "native" if native else egress_policy(engine.config).mode
    assert effective == ("allowlist-proxy" if case["injected_none"]
                         else case["effective_mode"])
    if case["injected_none"]:
        # The current config derives only open/proxy. Exercise the retained
        # generic mode interpolation separately, without claiming a real policy.
        monkeypatch.setattr(orchestrator_module, "egress_policy", lambda config: replace(
            egress_policy(config), mode="none"))
        assert orchestrator_module.egress_policy(engine.config).mode == case["effective_mode"]
    actual = engine._stage_prompt(make_run(engine), forge.ticket, task("frame"),
                                 values["context"], values["thread"])
    assert actual.encode("utf-8") == case["expected"].encode("utf-8")


def test_all_shipped_fragments_match_original_bytes(prompts):
    """@brief Inventory, placeholder completeness and original bodies are proven together."""
    catalog = prompts.PromptCatalog()
    inventory = {p.relative_to(prompts.PROMPT_ROOT).as_posix()
                 for p in prompts.PROMPT_ROOT.rglob("*.md")}
    assert inventory == set(BASELINE["fragments"]) | {"direct/implementation.md"}
    assert inventory == set(prompts.FRAGMENTS)
    for fragment, expected in BASELINE["fragments"].items():
        actual = catalog.render(fragment, **BASELINE["values"])
        assert actual.encode("utf-8") == expected.encode("utf-8"), fragment
        assert "Copyright" not in actual and "<!--" not in actual, fragment


@pytest.mark.parametrize("bad", [None, b"\xff", b"$9", b"missing license"])
def test_direct_resource_is_eagerly_required(resources, prompts, tmp_path, bad):
    """@brief The direct fragment is required even for construction of an AEGIS conductor."""
    fragment = "direct/implementation.md"
    path = resources / fragment
    path.parent.mkdir(exist_ok=True)
    if bad is None:
        path.unlink(missing_ok=True)
    else:
        prefix = b"" if bad == b"missing license" else prompts.LEGAL_PREFIX.encode()
        path.write_bytes(prefix + bad)
    with pytest.raises(prompts.PromptError, match=fragment):
        make_engine(tmp_path)


@pytest.mark.parametrize("case", NETWORK_BASELINE["cases"])
def test_direct_prompt_reuses_identical_permission_and_network_paragraph(
    tmp_path, monkeypatch, case,
):
    """@brief Direct composition reuses the exact shared notice without AEGIS procedure."""
    engine, forge, *_ = make_engine(tmp_path)
    native = case["requested_mode"] == "native"
    engine.config.execution.backend = "local" if native else "container"
    engine.config.container.system_packages = case["packages"]
    engine.config.container.egress.mode = "open" if native else case["requested_mode"]
    engine.config.executor.internet = case["internet"]
    if case["injected_none"]:
        monkeypatch.setattr(orchestrator_module, "egress_policy", lambda config: replace(
            egress_policy(config), mode="none"))
    run = make_run(engine)
    prompt = engine._direct_prompt(run, forge.ticket, "recover ${x}", "reply {x} $ £")
    if native:
        assert "Network policy is independently configured as" not in prompt
        assert "System package installation" not in prompt
    else:
        permission = engine.prompts.render("stage/packages-enabled.md" if case["packages"]
                                           else "stage/packages-disabled.md")
        network = engine.prompts.render("stage/network.md", mode=case["effective_mode"])
        assert permission + network in prompt
    assert "recover ${x}" in prompt and "reply {x} $ £" in prompt
    assert "TASK-" not in prompt and "AEGIS" not in prompt


def test_template_semantics_and_literal_data(resources, prompts):
    """@brief Values are substituted once, dollars escape and ordinary braces remain data."""
    fragment = "stage/ticket.md"
    body = "$name / ${name} / $$ / {x} / $empty"
    (resources / fragment).write_bytes((prompts.LEGAL_PREFIX + body).encode())
    catalog = prompts.PromptCatalog()
    data = "$name ${name} $$ $ {x} é"
    assert catalog.render(fragment, name=data, empty="") == f"{data} / {data} / $ / {{x}} / "
    for missing in ("name", "empty"):
        values = {"name": data, "empty": ""}
        del values[missing]
        with pytest.raises(prompts.PromptError, match=fragment):
            catalog.render(fragment, **values)


def test_header_removal_preserves_body_bytes(resources, prompts):
    """@brief Only the exact leading legal prefix is removed, not body comments/whitespace."""
    fragment = "stage/intro.md"
    body = " \n  é <!-- body comment -->\r\nend  \n"
    (resources / fragment).write_bytes((prompts.LEGAL_PREFIX + body).encode())
    assert prompts.PromptCatalog().render(fragment).encode() == body.encode()


@pytest.mark.parametrize("bad", [b"\xff", b"$", b"$9", b"${unclosed", b"no legal header"])
def test_bad_resource_refused_eagerly(resources, prompts, bad):
    """@brief Unused malformed UTF-8, template syntax and legal prefixes fail closed."""
    fragment = "system/server-internet.md"
    prefix = b"" if bad == b"no legal header" else prompts.LEGAL_PREFIX.encode()
    (resources / fragment).write_bytes(prefix + bad)
    with pytest.raises(prompts.PromptError, match=fragment):
        prompts.PromptCatalog()


def test_missing_unused_file_refuses_conductor(resources, prompts, tmp_path):
    """@brief Missing unused resources refuse construction, not only their later render."""
    fragment = "system/server-internet.md"
    (resources / fragment).unlink()
    with pytest.raises(prompts.PromptError, match=fragment):
        make_engine(tmp_path)


def test_unreadable_file_refused(resources, prompts, monkeypatch):
    """@brief OS read errors are typed even when the test account could bypass chmod."""
    fragment = "stage/frame.md"
    original = Path.read_bytes

    def read(path):
        if path == resources / fragment:
            raise PermissionError("test denial")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(prompts.PromptError, match=fragment):
        prompts.PromptCatalog()


def test_unknown_fragment_refused(prompts):
    """@brief No implicit path access or fallback is available at render time."""
    with pytest.raises(prompts.PromptError, match="unknown.md"):
        prompts.PromptCatalog().render("../unknown.md")


def test_catalog_is_eager_and_render_never_rereads(prompts, monkeypatch, tmp_path):
    """@brief Conductor construction reads the complete inventory exactly once."""
    reads = []
    original = Path.read_bytes

    def read(path):
        if path.is_relative_to(prompts.PROMPT_ROOT):
            reads.append(path.relative_to(prompts.PROMPT_ROOT).as_posix())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    engine, forge, *_ = make_engine(tmp_path)
    assert Counter(reads) == Counter(prompts.FRAGMENTS)
    run = make_run(engine)
    for stage in ("frame", "build", "done"):
        engine._stage_prompt(run, forge.ticket, task(stage), "evidence", "author: body")
    engine.prompts.render("system/internet-off.md")
    assert Counter(reads) == Counter(prompts.FRAGMENTS)


def test_shipped_placeholder_sets_are_complete(prompts):
    """@brief Every shipped placeholder has an exact captured caller value."""
    for fragment in prompts.FRAGMENTS:
        body = (prompts.PROMPT_ROOT / fragment).read_bytes().decode()[len(prompts.LEGAL_PREFIX):]
        assert set(Template(body).get_identifiers()) <= BASELINE["values"].keys()


def test_production_factory_shares_one_eager_catalog(prompts, monkeypatch, tmp_path):
    """@brief Production conductor and Pi launcher share one complete resource read."""
    reads = []
    original = Path.read_bytes

    def read(path):
        if path.is_relative_to(prompts.PROMPT_ROOT):
            reads.append(path.relative_to(prompts.PROMPT_ROOT).as_posix())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    monkeypatch.setattr(orchestrator_module, "build_forge", lambda *a, **k: object())
    monkeypatch.setattr(orchestrator_module, "project_runner", lambda *a: None)
    engine = orchestrator_module.Orchestrator.from_config(make_config(tmp_path), tmp_path / ".env")
    assert engine.executor.prompts is engine.prompts
    assert Counter(reads) == Counter(prompts.FRAGMENTS)
    engine.executor.prompts.render("system/internet-off.md")
    assert Counter(reads) == Counter(prompts.FRAGMENTS)


@pytest.mark.parametrize("scenario", [
    "revalidation-route", "integration-conflict", "continuation", "no-progress",
])
def test_recovery_callers_preserve_original_context(tmp_path, monkeypatch, scenario):
    """@brief Every recovery branch passes complete original context to its launch."""
    engine, forge, worktrees, *_ = make_engine(tmp_path)
    run = make_run(engine)
    evidence = BASELINE["values"]["evidence"]
    stage = {"revalidation-route": "done", "integration-conflict": "validate",
             "strict-verification": "done"}.get(scenario, "build")
    run.stage = "validate" if scenario == "revalidation-route" else stage
    if scenario == "revalidation-route":
        run.validation_evidence = {"agent_review_required": True}
    before = task(stage)
    after = replace(before, log=(evidence,)) if scenario == "continuation" else before
    client = FakeAegis([before, after, after])
    if scenario == "integration-conflict":
        monkeypatch.setattr(worktrees, "merge", lambda *a: CommandResult(exit_code=1))
    contexts = []

    def launch(state, ticket, current, **kwargs):
        context = kwargs.get("failure_context", "")
        if not context and scenario in {"continuation", "no-progress"}:
            if scenario == "continuation":
                worktrees.progress_fingerprint += "changed"
            return GateRun(exit_code=0)
        contexts.append(context)
        return GateRun(exit_code=0, has_questions=True, questions="stop fixture")

    monkeypatch.setattr(engine, "_launch_stage", launch)
    engine._conduct_task(run, forge.ticket, client, "")
    expected = BASELINE["fragments"][f"recovery/{scenario}.md"].replace(
        BASELINE["values"]["task_id"], TASK_ID)
    assert contexts == [expected]
    assert run.lifecycle == "parked-clarification"


@pytest.mark.parametrize("native,internet", [(False, False), (False, True),
                                             (True, False), (True, True)])
def test_notice_bytes_reach_pi(tmp_path, native, internet):
    """@brief Actual native/container launch branches send the captured notice bytes."""
    worktree = tmp_path / "work"
    worktree.mkdir()
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")

    class NativeTarget:
        """@brief Minimal owned native-session seam, backed by offline fake Pi."""
        pi_argv = staticmethod(pi_rpc_argv)

        @contextmanager
        def pi_session(self, argv, placements):
            """@brief Lend fake process pipes; the RPC client owns shutdown."""
            yield fake(argv, {})

        def read_output(self, path, *, optional=False):
            return ""

    target = NativeTarget() if native else SpawnTarget(fake)
    result = PiExecutor("pi", "m", internet=internet, web_search="none").run_gate(
        target, worktree, tmp_path / "io", "fixture prompt", timeout=10)
    assert result.ok and fake.all_exited()
    if not native and internet:
        assert "--append-system-prompt" not in fake.argv
    else:
        key = "system/server-internet.md" if native else "system/internet-off.md"
        actual = fake.argv[fake.argv.index("--append-system-prompt") + 1]
        assert actual.encode() == BASELINE["fragments"][key].encode()


def test_review_callers_preserve_original_bytes(tmp_path, monkeypatch):
    """@brief Review brief and changed-ticket thread use the original text."""
    engine, forge, *_ = make_engine(tmp_path)
    assert engine._pipeline_brief().encode() == BASELINE["fragments"]["review/pipeline.md"].encode()
    run = make_run(engine)
    run.lifecycle = "parked-clarification"
    run.parked_at = orchestrator_module.utc_now_iso()
    run.question_comment_id = 42
    engine.store.save(run)
    forge.ticket.description += " changed"
    forge.ticket.labels.append("agent-answered")
    forge.ticket_comments[200] = "Use updated behavior."
    threads = []
    monkeypatch.setattr(engine, "_conduct", lambda state, ticket, thread="": threads.append(thread))
    engine._reconcile_clarification(run, {"resumed": 0, "timed_out": 0})
    note = BASELINE["fragments"]["review/ticket-content-changed.md"]
    assert threads and threads[0].endswith(note)


# END OF FILE
