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
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread

from adore.profiles import ProfileStore
from adore.state import RunState, StateStore
from adore.util import CommandResult
import adore.web.app as web_app
from adore.web.commands import CommandWorker
from adore.wizard import run_wizard
from fastapi import BackgroundTasks, HTTPException, Request
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
    @return Zero for ticket 42 and idle polls; seven for ticket 43.
    @exception ValueError An unexpected command reaches the fake boundary.
    """
    if argv[-2:] == ["run", "--once"]:
        return 0
    if argv[-4:-1] == ["run", "--once", "--ticket"]:
        if argv[-1] == "42":
            return 0
        if argv[-1] == "43":
            return 7
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
            profiles.create(name, repo=f"offline/{name}", store_root=str(root))
            text = (SOFTWARE / "config.example.toml").read_text(encoding="utf-8")
            text = text.replace('store_root = ".adore"',
                                f'store_root = "{root.as_posix()}"')
            profiles.config_path(name).write_text(text, encoding="utf-8")
            state = StateStore(root)
            state.pause()
            state.save(RunState(run_id="historical-job", ticket_iid=1, lifecycle="done"))

        web_app._STATIC = SOFTWARE / "web" / ".e2e-dist"
        web_app.run_wizard = offline_wizard
        app = web_app.create_app(home, probe_runner=offline_probe)
        store = app.state.web_store
        developer = store.create_user("developer", "test-password", "developer")
        store.set_memberships(developer["id"], ["alpha"])
        worker = CommandWorker(profiles, store, runner=simulated_command)
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
