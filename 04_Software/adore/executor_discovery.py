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
@file    executor_discovery.py
@brief   Read-only discovery of installed native coding-agent entrypoints.
@details Searches bounded absolute host paths and known npm layouts without
         executing tools, interpreting shims, reading auth or installing files.
"""

from __future__ import annotations

# IMPORTS
import os
from pathlib import Path
import platform
import shlex

from adore.config import PI_NATIVE_COMMAND
from adore.local_process import native_context

# CONSTANTS
AGENTS = ("pi",)
MAX_ROOTS = 64
MAX_INSTALLATIONS = 12
NPM_SCRIPTS = {
    "pi": (
        "@earendil-works/pi-coding-agent/dist/bundle/cli.js",
        "@earendil-works/pi-coding-agent/dist/cli.js",
        "@mariozechner/pi-coding-agent/dist/cli.js",
    ),
}


# LOCAL HELPERS
def _quote(path: Path) -> str:
    """@brief Quote native paths for the existing shlex-based launch grammar."""
    return '"' + str(path).replace("\\", "/") + '"'


def _usable(path: Path, system: str, excluded: tuple[Path, ...], *, script=False) -> Path | None:
    """@brief Accept installed files outside project trees, with bounded ancestry."""
    try:
        spelling = str(path)
        if (
            not path.is_absolute()
            or len(spelling) > 2048
            or any(char in spelling for char in '\r\n\x00"{}')
            or spelling.startswith(("\\\\", "//"))
        ):
            return None
        if any(path.is_relative_to(root) for root in excluded):
            return None
        resolved = path.resolve()
        if not resolved.is_file() or any(resolved.is_relative_to(root) for root in excluded):
            return None
        for parent in [*list(path.parents)[:32], *list(resolved.parents)[:32]]:
            if (parent / ".git").exists() or (parent / ".agentic").is_dir():
                return None
        if script:
            return resolved if resolved.suffix.lower() in {".js", ".mjs", ".cjs"} else None
        if resolved.stem.casefold() in {"cmd", "powershell", "pwsh", "wsl", "bash", "sh"}:
            return None
        if system == "Windows":
            return resolved if resolved.suffix.lower() == ".exe" else None
        return resolved if os.access(resolved, os.X_OK) else None
    except (OSError, ValueError, RuntimeError):
        return None


# PUBLIC API
def discover_executors(
    *,
    system: str | None = None,
    environment: dict | None = None,
    home: Path | None = None,
    excluded: tuple[Path, ...] | None = None,
) -> dict:
    """@brief List native launch suggestions for the current ADORE service account.
    @param[in] system Host OS; injectable for offline Windows/Linux filesystem tests.
    @param[in] environment Host environment snapshot; only path locations are used.
    @param[in] home Existing account home, defaulting to its native environment.
    @param[in] excluded Project directories whose files cannot be auto-selected.
    @return Closed host/account and supported-agent installation listing.
    @note Filesystem failure yields fewer suggestions; manual configuration remains valid.
    """
    system = system or platform.system()
    env = dict(os.environ if environment is None else environment)
    home = home or Path(env.get("USERPROFILE" if system == "Windows" else "HOME") or Path.home())
    excluded = tuple(
        path.resolve() for path in (excluded if excluded is not None else (Path.cwd(),))
    )
    context = native_context()
    result = {
        "system": system,
        "machine": context["machine"],
        "account": context["account"],
        "executors": [{"agent": agent, "installations": []} for agent in AGENTS],
    }
    if system not in {"Windows", "Linux"}:
        return result
    separator = ";" if system == "Windows" else ":"
    roots: list[Path] = []
    raw_roots = env.get("PATH", "")[:32768].split(separator)[:MAX_ROOTS]
    raw_roots += [str(home / ".local/bin")]
    if system == "Windows":
        raw_roots += [
            str(Path(env.get("APPDATA") or home / "AppData/Roaming") / "npm"),
            str(home / "scoop/shims"),
        ]
    else:
        raw_roots += [str(home / ".npm-global/bin")]
    for raw in raw_roots:
        path = Path(raw)
        if raw and path.is_absolute() and len(raw) <= 2048 and path not in roots:
            roots.append(path)
    roots = roots[:MAX_ROOTS]

    def native_name(name: str) -> str:
        return name + (".exe" if system == "Windows" else "")

    node = next(
        (
            found
            for root in roots
            if (found := _usable(root / native_name("node"), system, excluded))
        ),
        None,
    )
    for record in result["executors"]:
        agent = record["agent"]
        seen: set[tuple[str, str]] = set()

        def add(
            binary: Path,
            source: str,
            script: Path | None = None,
            *,
            record=record,
            agent=agent,
            seen=seen,
        ) -> None:
            """@brief Add a canonical launch only after both native identities are usable."""
            executable = _usable(binary, system, excluded)
            entrypoint = _usable(script, system, excluded, script=True) if script else None
            if executable is None or script is not None and entrypoint is None:
                return
            key = (str(executable), str(entrypoint or ""))
            if key in seen or len(record["installations"]) >= MAX_INSTALLATIONS:
                return
            seen.add(key)
            prefix = _quote(executable) + (" " + _quote(entrypoint) if entrypoint else "")
            command = prefix + " " + PI_NATIVE_COMMAND.partition(" ")[2]
            # Keep the same closed launch grammar as actual local execution.
            if len(command) > 4096 or not shlex.split(command):
                return
            record["installations"].append(
                {
                    "executable": str(executable),
                    "entrypoint": str(entrypoint) if entrypoint else None,
                    "command": command,
                    "source": source,
                }
            )

        for root in roots:
            add(root / native_name(agent), "PATH")
            for packages in (root / "node_modules", root.parent / "lib/node_modules"):
                if node:
                    for relative in NPM_SCRIPTS.get(agent, ()):
                        add(node, "npm", packages / relative)
    return result


# END OF FILE
