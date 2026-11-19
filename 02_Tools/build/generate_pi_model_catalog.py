#!/usr/bin/env python3
"""Write ADORE's Pi provider and model catalog from the pinned Pi, offline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

OUTPUT = Path(__file__).resolve().parents[2] / "04_Software" / "adore" / "pi_catalog.json"
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
    "qwen-token-plan-cn": "Qwen Token Plan (China)",
    "qwen-token-plan-individual": "Qwen Individual",
    "qwen-token-plan-individual-cn": "Qwen Individual (China)",
}
PLACEHOLDER = "adore-catalog-placeholder"
_ROW = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*`(?P<variable>[A-Z][A-Z0-9_]*)`\s*\|\s*$")


def provider_table(docs: Path) -> list[tuple[str, str]]:
    """
    Read Pi's single-variable API-key provider table.
    docs: Pi's `docs/providers.md`.
    Returns: (display name, variable) rows in Pi's order.
    Raises SystemExit: When the table is missing.
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
    List the models Pi offers when only `variable` holds a credential.
    node: Node executable.
    cli: Pi's `cli.js`.
    variable: Provider key variable set to a placeholder.
    Returns: Provider id -> model ids in Pi's order.
    Raises SystemExit: When Pi fails or prints an unexpected table.
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


def pi_ai_data(package: Path) -> Path:
    """
    The provider data directory of the installed pi-ai package.
    package: Installed pi-coding-agent package directory.
    Returns: `.../pi-ai/dist/providers/data`.
    Raises SystemExit: When it is missing.
    """
    data = Path("dist") / "providers" / "data"
    candidates = (package / "node_modules" / "@earendil-works" / "pi-ai" / data,
                  package.parent / "pi-ai" / data)
    path = next((item for item in candidates if item.is_dir()), None)
    if path is None:
        raise SystemExit("Pi's provider data (pi-ai dist/providers/data) was not found")
    return path


def provider_hosts(data: Path, provider: str) -> list[str]:
    """
    Host names of every base URL Pi uses for a provider.
    data: pi-ai provider data directory.
    provider: Provider id.
    Returns: Sorted unique host names.
    Raises SystemExit: When the provider has no data file or no concrete host.
    """
    path = data / f"{provider}.json"
    if not path.is_file():
        raise SystemExit(f"Pi has no provider data for {provider}")
    hosts: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "baseUrl" and isinstance(item, str):
                    host = urlsplit(item).hostname
                    if not host or "{" in item:
                        raise SystemExit(f"{provider} has a base URL without a fixed host: {item}")
                    hosts.add(host)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(json.loads(path.read_text(encoding="utf-8")))
    if not hosts:
        raise SystemExit(f"{provider} lists no base URL")
    return sorted(hosts)


def model_thinking(data: Path, provider: str, models: list[str]) -> dict[str, list[str]]:
    """Derive conservative supported levels from pinned Pi model data."""
    levels = ("off", "minimal", "low", "medium", "high", "xhigh", "max")
    source = json.loads((data / f"{provider}.json").read_text(encoding="utf-8"))
    found: dict[str, list[set[str]]] = {}
    for group in source.values():
        if not isinstance(group, dict):
            continue
        for item in group.values():
            if not isinstance(item, dict) or item.get("type") != "chat":
                continue
            model = item.get("id")
            if model not in models:
                continue
            mapping = item.get("thinkingLevelMap", {})
            supported = {level for level in levels if (
                level == "off" and not item.get("reasoning") or item.get("reasoning")
                and mapping.get(level, True) is not None
                and (level not in ("xhigh", "max") or level in mapping))}
            found.setdefault(model, []).append(supported)
    return {model: [level for level in levels if all(level in group for group in found[model])]
            for model in models if model in found}


def chatgpt_models(package: Path, openai: list[str]) -> list[str]:
    """
    The models a ChatGPT subscription serves, from Pi's own catalog.
    Pi's ChatGPT-backed catalog (`openai-codex`, the legacy client's
                provider) lists the chat models of a ChatGPT account; Sign in
                with ChatGPT runs them as provider `openai`, so only those that
                are also openai models are kept, in Pi's order.
    package: Installed pi-coding-agent package directory.
    openai: Models Pi lists for provider openai.
    Returns: Model ids.
    Raises SystemExit: When the catalog is missing or empty.
    """
    path = pi_ai_data(package) / "openai-codex.json"
    if not path.is_file():
        raise SystemExit("Pi's ChatGPT catalog (pi-ai openai-codex.json) was not found")
    chat = json.loads(path.read_text(encoding="utf-8")).get("openai-codex-responses", {})
    models = [key.split(":", 1)[1] for key in chat if key.startswith("chat:")]
    models = [model for model in models if model in openai]
    if not models:
        raise SystemExit("Pi's ChatGPT catalog lists no openai chat model")
    return models


def supplement_chatgpt_catalog(openai: dict, chatgpt: list[str]) -> None:
    """Keep models verified after the pinned provider snapshot was published."""
    model = "gpt-6.2-sol"
    if model not in openai["models"]:
        openai["models"].append(model)
        openai["models"].sort()
    # OpenAI Codex models-manager/models.json lists these levels plus ultra,
    # which is outside ADORE's Pi reasoning options.
    openai["thinking"].setdefault(model, ["low", "medium", "high", "xhigh", "max"])
    if model not in chatgpt:
        chatgpt.append(model)


def main() -> int:
    """
    Generate the catalog file.
    Returns: Process exit code.
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
                                   "variable": variable, "models": models,
                                   "hosts": provider_hosts(pi_ai_data(package), provider),
                                   "thinking": model_thinking(pi_ai_data(package), provider, models)}
    catalog = {"pi_version": version,
               "providers": sorted(providers.values(), key=lambda item: item["name"].casefold()),
               "chatgpt_models": chatgpt_models(package, providers["openai"]["models"])}
    supplement_chatgpt_catalog(providers["openai"], catalog["chatgpt_models"])
    options.out.write_bytes((json.dumps(catalog, indent=1, ensure_ascii=False) + "\n")
                            .encode("utf-8"))
    print(f"wrote {options.out}: Pi {version}, {len(providers)} providers, "
          f"{sum(len(item['models']) for item in providers.values())} models, "
          f"{len(catalog['chatgpt_models'])} ChatGPT models")
    return 0


if __name__ == "__main__":
    sys.exit(main())
