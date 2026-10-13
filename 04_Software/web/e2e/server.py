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
@file       server.py
@brief      Isolated real-API server for offline browser regression tests.
@details    Creates disposable profiles and identities; all external command
            boundaries use injected runners. Serves the dedicated E2E build.
"""

# IMPORTS
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import sleep

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore, derive_run_id
from adore.util import CommandResult
import adore.web.app as web_app
from adore.web.commands import CommandWorker
from adore.wizard import run_wizard
from fastapi import BackgroundTasks, HTTPException, Request
from tests.test_image_build import ImageRuntime
import uvicorn

# CONSTANTS
SOFTWARE = Path(__file__).resolve().parents[2]


# LOCAL HELPERS
def offline_probe(_argv, **_kwargs) -> CommandResult:
    """@brief Reject every setup/readiness probe without invoking host tools."""
    return CommandResult(exit_code=127)


def offline_wizard(*args, **kwargs):
    """@brief Keep project-creation probes on the same simulated boundary."""
    kwargs["runner"] = offline_probe
    return run_wizard(*args, **kwargs)


def simulated_command(argv: list[str], _env: dict[str, str]) -> int:
    """@brief Simulate a conductor exit without launching an external process.

    @param[in] argv Fixed conductor command produced by the real worker.
    @param[in] _env Isolated environment supplied by the worker.
    @return Zero for tickets 42 and 44 and idle polls; seven for ticket 43.
    @exception ValueError An unexpected command reaches the fake boundary.
    """
    if argv[-2:] == ["run", "--once"]:
        return 0
    if argv[-4:-1] == ["run", "--once", "--ticket"]:
        if argv[-1] in {"42", "44"}:
            return 0
        if argv[-1] == "43":
            return 7
    if argv[-2] in {"retry", "cancel"} and argv[-1].startswith("ux-"):
        return 7 if argv[-2] == "retry" else 0
    raise ValueError("unsupported offline test command")


# PUBLIC API
def main() -> None:
    """@brief Run the temporary API and fake-boundary worker on loopback.

    @note Inherited ADORE_HOME is replaced before profiles or the worker exist.
    @exception RuntimeError A failed worker prevents server readiness.
    """
    with TemporaryDirectory(prefix="adore-e2e-") as directory:
        home = Path(directory)
        os.environ["ADORE_HOME"] = str(home)
        profiles = ProfileStore(home)
        for name in ("alpha", "beta"):
            root = home / "state" / name
            profiles.create(name, repo=f"offline/{name}", store_root=str(root), platform="gitlab")
            text = (SOFTWARE / "config.example.toml").read_text(encoding="utf-8")
            text = text.replace('store_root = ".adore"',
                                f'store_root = "{root.as_posix()}"')
            profiles.config_path(name).write_text(text, encoding="utf-8")
            state = StateStore(root)
            state.pause()
            state.save(RunState(run_id="historical-job", ticket_iid=1, lifecycle="done"))
            # A failed job for fixture ticket 24, so the ticket browser offers Retry.
            state.save(RunState(run_id=derive_run_id("gitlab", "group/subgroup/project", 24),
                                ticket_iid=24, lifecycle="failed"))

        web_app._STATIC = SOFTWARE / "web" / ".e2e-dist"
        web_app.run_wizard = offline_wizard
        clone = home / "fixture-clone"
        (clone / ".git").mkdir(parents=True)
        (clone / ".agentic").mkdir()
        for filename in ("aegis.py", "aegis.toml"):
            (clone / ".agentic" / filename).write_text(
                "# Copyright (c) 2026 DDP Engineering\n"
                "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
                "# Commercial use requires a separate commercial license.\n"
                "# See LICENSE.txt. SPDX-License-Identifier: "
                "LicenseRef-PolyForm-Noncommercial-1.0.0\n", encoding="utf-8")
        probe_mode = {"mode": "failed"}
        image_runtime = ImageRuntime()
        # Offline forge tickets shared by the fixture projects (their configs keep the
        # example repository); Stop really removes the ready label here.
        forge_issues = [
                {"iid": 21, "title": "Add export button", "description": "Export the table.\n- [ ] CSV",
                 "labels": ["agent-ready", "P2"], "author": {"username": "ana"}, "state": "opened",
                 "web_url": "https://gitlab.example/offline/alpha/-/issues/21",
                 "created_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-02T10:00:00Z"},
                {"iid": 22, "title": "<img src=x onerror=alert(1)> Fix login",
                 "description": "<script>window.__ticketInjected = true</script>Steps",
                 "labels": ["P2"], "author": {"username": "ion"}, "state": "opened",
                 "web_url": "javascript:alert(1)",
                 "created_at": "2026-10-01T11:00:00Z", "updated_at": "2026-10-03T10:00:00Z"},
                {"iid": 23, "title": "Paused migration", "description": "Waiting.", "labels": ["agent-hold"],
                 "author": {"username": "ana"}, "state": "opened", "web_url": "",
                 "created_at": "2026-10-01T12:00:00Z", "updated_at": "2026-10-03T11:00:00Z"},
                {"iid": 24, "title": "Retry the flaky build", "description": "Failed once.", "labels": ["P2"],
                 "author": {"username": "ion"}, "state": "opened", "web_url": "",
                 "created_at": "2026-10-01T13:00:00Z", "updated_at": "2026-10-03T12:00:00Z"},
                {"iid": 25, "title": "Unlabelled idea", "description": "Try it.", "labels": [],
                 "author": {"username": "ana"}, "state": "opened", "web_url": "",
                 "created_at": "2026-10-01T14:00:00Z", "updated_at": "2026-10-03T13:00:00Z"},
                {"iid": 43, "title": "Rejected by the engine", "description": "Fails.", "labels": ["agent-ready", "P2"],
                 "author": {"username": "ana"}, "state": "opened", "web_url": "",
                 "created_at": "2026-10-01T15:00:00Z", "updated_at": "2026-10-03T14:00:00Z"},
                {"iid": 44, "title": "Queue me", "description": "Succeeds.", "labels": ["agent-ready", "P2"],
                 "author": {"username": "ion"}, "state": "opened", "web_url": "",
                 "created_at": "2026-10-01T16:00:00Z", "updated_at": "2026-10-03T15:00:00Z"},
        ]
        forge_notes = {
            21: [{"id": 1, "body": "Please keep **bold** headers", "author": {"username": "ana"},
                  "created_at": "2026-10-02T09:00:00Z"},
                 {"id": 2, "body": "added ~agent-ready label", "author": {"username": "bot"},
                  "created_at": "2026-10-02T09:01:00Z", "system": True}],
            22: [{"id": 3, "body": "<b onclick=alert(1)>urgent</b>", "author": {"username": "ion"},
                  "created_at": "2026-10-03T09:00:00Z"}],
        }

        def fixture_forge(argv):
            """@brief Answer glab issue reads and label edits from the offline fixture."""
            issues = forge_issues
            if argv[:3] == ["glab", "issue", "list"]:
                return CommandResult(argv=argv, stdout=json.dumps(issues))
            if argv[:3] in (["glab", "issue", "view"], ["glab", "issue", "update"]):
                match = [item for item in issues if item["iid"] == int(argv[3])]
                if not match:
                    return CommandResult(argv=argv, exit_code=1, stderr="404 Not Found")
                if argv[2] == "update":
                    removed = {argv[i + 1] for i, word in enumerate(argv) if word == "--unlabel"}
                    added = [argv[i + 1] for i, word in enumerate(argv) if word == "--label"]
                    labels = [label for label in match[0]["labels"] if label not in removed]
                    match[0]["labels"] = labels + [label for label in added if label not in labels]
                    return CommandResult(argv=argv, stdout="")
                return CommandResult(argv=argv, stdout=json.dumps(match[0]))
            if argv[:2] == ["glab", "api"] and "/notes" in argv[2]:
                iid = int(argv[2].split("/issues/")[1].split("/")[0])
                return CommandResult(argv=argv, stdout=json.dumps(forge_notes.get(iid, [])))
            return None

        def fixture_probe(argv, **_kwargs):
            """@brief Simulate explicit readiness without any external services."""
            if "image-build" in Path(_kwargs.get("cwd") or ".").parts:
                return image_runtime(argv, **_kwargs)
            if argv[:1] == ["glab"]:
                answer = fixture_forge(list(argv))
                if answer is not None:
                    return answer
            if argv[:2] in (["glab", "api"], ["tea", "api"]) and any(
                    re.fullmatch(r"(repos/[^/]+/[^/]+|projects/[^/]+)/labels", part.split("?")[0])
                    for part in argv):
                # Repository labels: agent-ready exists, every other label is created;
                # a repository named labels-fail cannot be read.
                if any("labels-fail" in part for part in argv):
                    return CommandResult(argv=argv, exit_code=1, stderr="503 Service Unavailable")
                status = "HTTP/1.1 200 OK"
                if "--method" in argv and argv[argv.index("--method") + 1] == "POST":
                    return CommandResult(argv=argv, stdout="{}", stderr=status)
                return CommandResult(argv=argv, stdout=json.dumps([{"name": "agent-ready"}]),
                                     stderr=status)
            if argv[1:2] == ["images"]:
                # The server's images: docker lists three, podman cannot be queried.
                if argv[0] != "docker":
                    return CommandResult(argv=argv, exit_code=125, stderr="no podman")
                return CommandResult(argv=argv, stdout="adore-executor-base:1.0.0\n"
                                     "adore-executor-base:pi-0.87.1\n<none>:<none>\n"
                                     "adore-test:latest\n")
            if argv[:2] == ["git", "ls-remote"]:
                # A repository URL read: unreachable hosts fail, others report a main branch.
                if "unreachable" in argv[-2]:
                    return CommandResult(argv=argv, exit_code=128, stderr="Permission denied")
                return CommandResult(argv=argv, stdout="ref: refs/heads/main\tHEAD\n" + "c" * 40 + "\tHEAD\n")
            if argv[:3] == ["tea", "logins", "list"]:
                return CommandResult(argv=argv, stdout=json.dumps(
                    [{"name": "fixture", "url": "http://forge.e2e.invalid:3000"}]))
            if argv[:2] == ["git", "clone"]:
                # The clone made at creation: a repository with AEGIS installed.
                dest = Path(argv[-1])
                (dest / ".git").mkdir(parents=True)
                (dest / ".git" / "config").write_text(
                    f'[remote "origin"]\n\turl = {argv[-2]}\n', encoding="utf-8")
                (dest / ".agentic").mkdir()
                for item in ("aegis.py", "aegis.toml"):
                    (dest / ".agentic" / item).write_text("", encoding="utf-8")
                return CommandResult(argv=argv)
            if argv[:1] == ["git"] and "-C" in argv:
                recipe = ("jobs:\n  setup:\n    container:\n"
                          "      image: adore-executor-project:latest\n    steps:\n"
                          "      - name: Install project dependencies\n"
                          "        run: uv sync --locked\n")
                if "rev-parse" in argv:
                    output = "a" * 40
                elif "ls-tree" in argv:
                    output = f"100644 blob {'b' * 40}\tprepare.yml\x00"
                elif "-s" in argv:
                    output = str(len(recipe.encode()))
                else:
                    output = recipe
                return CommandResult(argv=argv, stdout=output)
            return CommandResult(argv=argv, exit_code=(
                127 if probe_mode["mode"] == "failed" else 0), stdout="fixture-1.0")

        app = web_app.create_app(home, probe_runner=fixture_probe)

        @app.post("/__e2e__/jobs")
        def jobs_fixture(request: Request, mode: str = "seed") -> dict:
            """
            @brief Persist realistic offline lifecycle evidence in the disposable profiles.
            @param[in] request Test-control header, never present in the shipped API.
            @param[in] mode Seed, reset, mutate or corrupt an owned fixture source.
            @return Composite identities for the browser assertions.
            @exception HTTPException For missing authorization or unsupported fixture mode.
            """
            if request.headers.get("X-ADORE-E2E") != "local-test" or mode not in {
                "seed", "reset", "mutate", "corrupt",
            }:
                raise HTTPException(403, "test runner header and supported mode required")
            roots = [StateStore(home / "state" / name) for name in ("alpha", "beta")]
            if mode in {"mutate", "corrupt"}:
                path = roots[0].run_dir("ux-working") / "state.json"
                if mode == "corrupt":
                    path.write_text("BROKEN_FIXTURE_SECRET", encoding="utf-8")
                else:
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["outcome"] = "Actual source changed"
                    path.write_text(json.dumps(value), encoding="utf-8")
                return {"mode": mode}
            for state in roots:
                for directory in state.runs_root.glob("ux-*"):
                    if directory.is_dir():
                        # Browser/worker reads may briefly hold Windows file handles.
                        for attempt in range(10):
                            try:
                                shutil.rmtree(directory)
                                break
                            except PermissionError:
                                if attempt == 9:
                                    raise
                                sleep(0.025)
            ids = {name: profiles.load(name).project_id for name in ("alpha", "beta")}
            if mode == "reset":
                return ids
            stamp = "2026-10-05T01:00:00Z"
            cases = {"working": "build", "publishing": "deliver", "parked-clarification": "build",
                     "awaiting-approval": "deliver", "in-review": "done",
                     "handoff-pending": "build",
                     "handed-off": "build", "done": "done", "failed": "build",
                     "cancelled": "build", "stale": "build"}
            for lifecycle, stage in cases.items():
                short = {"parked-clarification": "clarification", "awaiting-approval": "approval",
                         "in-review": "review"}.get(lifecycle, lifecycle)
                run_id = "ux-" + short
                run = RunState(run_id=run_id, ticket_iid=42, lifecycle=lifecycle, stage=stage,
                               created_at=stamp, updated_at=stamp)
                if lifecycle == "parked-clarification":
                    run.parked_at = stamp
                    run.question_comment_id = 7
                if lifecycle == "awaiting-approval":
                    run.approval_comment_id = 8
                    run.approval_presented_at = stamp
                    run.candidate_fingerprint = "a" * 64
                    run.candidate_base_ref = "b" * 40
                if lifecycle == "in-review":
                    run.mr_url = "https://forge.example/offline/alpha/pulls/3"
                if lifecycle == "done":
                    run.outcome = "done without merge evidence"
                roots[0].save(run)
                path = roots[0].run_dir(run_id) / "state.json"
                value = json.loads(path.read_text(encoding="utf-8"))
                value["updated_at"] = stamp
                path.write_text(json.dumps(value), encoding="utf-8")
                roots[0].save_ticket(run_id, {"iid": 42, "title": f"Actual {short} ticket",
                                            "web_url": "https://forge.example/offline/alpha/issues/42"})
                if lifecycle == "parked-clarification":
                    roots[0].journal(run_id, "parked", stage=stage, ts=stamp,
                                     questions="Which export format? token=fixture-secret")
                elif lifecycle == "awaiting-approval":
                    for observed in ("frame", "build", "validate"):
                        roots[0].journal(run_id, "gate-passed", stage=observed, ts=stamp)
                else:
                    roots[0].journal(run_id, "gate-started", stage=stage, executor="pi", ts=stamp)
            # Cross-project collision and real absent legacy ticket/journal/activity.
            roots[1].save(RunState(run_id="ux-working", ticket_iid=42, lifecycle="working",
                                   stage="build", updated_at=stamp))
            roots[1].save_ticket("ux-working", {"iid": 42, "title": "Actual beta collision",
                                              "web_url": "https://forge.example/offline/beta/issues/42"})
            roots[0].save(RunState(run_id="ux-missing", ticket_iid=99, stage="build"))
            missing = roots[0].run_dir("ux-missing") / "state.json"
            value = json.loads(missing.read_text(encoding="utf-8"))
            value.update(created_at="", updated_at="")
            missing.write_text(json.dumps(value), encoding="utf-8")
            return ids

        @app.post("/__e2e__/enrollment")
        def enrollment_fixture(request: Request, mode: str = "failed") -> dict:
            """@brief Return disposable server clone and select a fake probe outcome.

            @param[in] request Local test-control authorization.
            @param[in] mode Failed or partial offline evidence.
            @return Temporary clone path owned by this fixture.
            @exception HTTPException An unauthorized or unknown mode is rejected.
            """
            if request.headers.get("X-ADORE-E2E") != "local-test" or mode not in {
                "failed", "partial",
            }:
                raise HTTPException(403, "test runner header and supported mode required")
            probe_mode["mode"] = mode
            return {"clone": str(clone)}
        store = app.state.web_store
        developer = store.create_user("developer", "test-password", "developer")
        store.set_memberships(developer["id"], ["alpha"])
        worker = CommandWorker(
            profiles, store, runner=simulated_command, image_runner=image_runtime)
        stop = Event()

        @asynccontextmanager
        async def lifespan(_app):
            """@brief Stop and join the isolated worker on graceful shutdown."""
            thread = Thread(target=lambda: worker.run_forever(
                interval=0.05, heartbeat_interval=0.1, stop=stop), daemon=True)
            thread.start()
            try:
                yield
            finally:
                stop.set()
                thread.join(timeout=3)
                if thread.is_alive():
                    raise RuntimeError("offline worker did not stop")

        app.router.lifespan_context = lifespan
        server = uvicorn.Server(uvicorn.Config(
            app, host="127.0.0.1", port=18765, log_level="warning", proxy_headers=False,
        ))

        @app.post("/__e2e__/shutdown")
        def shutdown(request: Request, background: BackgroundTasks) -> dict:
            """@brief Allow the local test runner to clean up on Windows too.

            @param[in] request Fixture-control header required by teardown.
            @param[in,out] background Runs shutdown after returning the response.
            @return Fixture identity and acknowledgement.
            @exception HTTPException The fixture-control header is absent.
            @note This route exists only in this disposable test server.
            """
            if request.headers.get("X-ADORE-E2E") != "local-test":
                raise HTTPException(403, "test runner header required")
            background.add_task(setattr, server, "should_exit", True)
            return {"test_server": "stopping"}

        server.run()


if __name__ == "__main__":
    main()

# END OF FILE
