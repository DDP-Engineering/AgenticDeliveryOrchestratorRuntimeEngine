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
@file generate_pi_catalog.py
@brief Write ADORE's Pi provider and model catalog from the pinned Pi, offline.
@details Reads the single-variable API-key provider table from the installed
         Pi package's `docs/providers.md`, then runs `pi --list-models` once per
         variable with only that variable set to a placeholder, `PI_OFFLINE=1`
         and an empty agent directory. Pi lists the built-in catalog of every
         provider that has a credential, so each run yields the provider ids
         and models behind one variable; no network call is made and no real
         key is used. The result is `04_Software/adore/pi_catalog.json`.
         Providers whose key is a forge token (GitHub Copilot) or that list
         no chat models (TypeSafe classifiers) are left out. Run it again
         whenever the pinned Pi version changes.
@example
    python 02_Tools/generate_pi_catalog.py --node <node22>/node.exe \
        --cli <prefix>/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js
"""

from __future__ import annotations

# IMPORTS
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

# CONSTANTS
OUTPUT = Path(__file__).resolve().parents[1] / "04_Software" / "adore" / "pi_catalog.json"
#: Variables ADORE does not offer: a GitHub token is a forge credential, and
#: TypeSafe serves classifier models only.
EXCLUDED_VARIABLES = frozenset({"COPILOT_GITHUB_TOKEN", "TYPESAFE_API_KEY"})
#: Names for the provider ids that share one variable in Pi's table.
SPLIT_NAMES = {
    "opencode": "OpenCode Zen",
    "opencode-go": "OpenCode Go",
    "moonshotai": "Moonshot AI",
    "moonshotai-cn": "Moonshot AI (China)",
    "qwen-token-plan": "Qwen Token Plan",
    "qwen-token-plan-individual": "Qwen Individual",
}
PLACEHOLDER = "adore-catalog-placeholder"
_ROW = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*`(?P<variable>[A-Z][A-Z0-9_]*)`\s*\|\s*$")


# HELPER FUNCTIONS


def provider_table(docs: Path) -> list[tuple[str, str]]:
    """
    @brief      Read Pi's single-variable API-key provider table.
    @param[in]  docs Pi's `docs/providers.md`.
    @return     (display name, variable) rows in Pi's order.
    @exception  SystemExit When the table is missing.
    """
    text = docs.read_text(encoding="utf-8")
    section = text.split("## Use an API key from the environment", 1)[-1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        match = _ROW.match(line)
        if match:
            name = re.sub(r"\s*\(\[.*?\]\(.*?\)\)", "", match["name"]).strip()
            rows.append((name, match["variable"]))
    if not rows:
        raise SystemExit(f"no provider table found in {docs}")
    return rows


def list_models(node: str, cli: str, variable: str) -> dict[str, list[str]]:
    """
    @brief      List the models Pi offers when only `variable` holds a credential.
    @param[in]  node Node executable.
    @param[in]  cli Pi's `cli.js`.
    @param[in]  variable Provider key variable set to a placeholder.
    @return     Provider id -> model ids in Pi's order.
    @exception  SystemExit When Pi fails or prints an unexpected table.
    """
    with tempfile.TemporaryDirectory(prefix="adore-pi-catalog-") as home:
        env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP")
               if key in os.environ}
        env.update(HOME=home, USERPROFILE=home, PI_CODING_AGENT_DIR=str(Path(home) / "agent"),
                   PI_OFFLINE="1", PI_TELEMETRY="0", PI_SKIP_VERSION_CHECK="1",
                   **{variable: PLACEHOLDER})
        result = subprocess.run(  # noqa: S603 - fixed argv
            [node, cli, "--list-models"], env=env, cwd=home, capture_output=True,
            text=True, encoding="utf-8", timeout=120, check=False)
    lines = result.stdout.splitlines()
    if result.returncode or not lines or lines[0].split()[:2] != ["provider", "model"]:
        raise SystemExit(f"pi --list-models failed for {variable}: {result.stderr.strip()}")
    models: dict[str, list[str]] = {}
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            raise SystemExit(f"unexpected --list-models line for {variable}: {line!r}")
        models.setdefault(parts[0], []).append(parts[1])
    return models


# PUBLIC API


def main() -> int:
    """
    @brief      Generate the catalog file.
    @return     Process exit code.
    """
    parser = argparse.ArgumentParser(description="Write adore/pi_catalog.json from the pinned Pi.")
    parser.add_argument("--node", required=True, help="Node 22 executable")
    parser.add_argument("--cli", required=True, help="pinned Pi dist/bundle/cli.js")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    options = parser.parse_args()
    package = Path(options.cli).resolve().parents[2]
    version = json.loads((package / "package.json").read_text(encoding="utf-8"))["version"]
    providers: dict[str, dict] = {}
    for name, variable in provider_table(package / "docs" / "providers.md"):
        if variable in EXCLUDED_VARIABLES:
            continue
        listed = list_models(options.node, options.cli, variable)
        if not listed:
            raise SystemExit(f"Pi listed no models for {variable}")
        for provider, models in listed.items():
            if provider in providers:
                raise SystemExit(f"provider {provider} appears under two variables")
            if len(listed) > 1 and provider not in SPLIT_NAMES:
                raise SystemExit(f"name the provider {provider} in SPLIT_NAMES")
            providers[provider] = {"id": provider, "name": SPLIT_NAMES.get(provider, name),
                                   "variable": variable, "models": models}
    catalog = {"pi_version": version,
               "providers": sorted(providers.values(), key=lambda item: item["name"].casefold())}
    options.out.write_bytes((json.dumps(catalog, indent=1, ensure_ascii=False) + "\n")
                            .encode("utf-8"))
    print(f"wrote {options.out}: Pi {version}, {len(providers)} providers, "
          f"{sum(len(item['models']) for item in providers.values())} models")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
