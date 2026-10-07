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
@file    test_preparation.py
@brief   Public preparation plan and selection trust-boundary tests.
@details Uses injected Git responses; no source or runtime CLI is invoked.
"""

# IMPORTS
from pathlib import Path

from adore.config import default_config, load_config, validate_config
from adore.preparation import PreparationError, parse_recipe, resolve_plan, validate_plan
from adore.util import CommandResult
import pytest

# PUBLIC API / TESTS

RECIPE = """name: Prepare project
jobs:
  setup:
    container:
      image: project:1
    steps:
      - name: Check tools
        run: uv --version
      - name: Prepare dependencies
        run: |-
          echo "path with spaces"
          uv sync --locked
"""


def test_recipe_normalizes_multiline_and_quoted_text() -> None:
    """@brief Supported syntax preserves multiline shell text exactly."""
    recipe = parse_recipe(RECIPE, "setup")
    assert recipe["image"] == "project:1"
    assert recipe["steps"][1]["run"] == 'echo "path with spaces"\nuv sync --locked'
    assert (
        parse_recipe(RECIPE.replace("uv --version", "'echo ''quoted'' #literal'"), "setup")[
            "steps"
        ][0]["run"]
        == "echo 'quoted' #literal"
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s + "on: push\n",
        lambda s: s.replace("container:", "runs-on: linux\n    container:"),
        lambda s: s.replace("run: uv --version", "uses: actions/setup-node@v1"),
        lambda s: s.replace("run: uv --version", "run: yes"),
        lambda s: s.replace("run: uv --version", "run: &script echo hi"),
        lambda s: s.replace("run: uv --version", "run: *script"),
        lambda s: s.replace("run: uv --version", "run: !!str hi"),
        lambda s: s.replace("run: uv --version", "run: ${{ secrets.KEY }}"),
        lambda s: s.replace("run: uv --version", "run: []"),
        lambda s: s.replace("run: uv --version", "run: >\n          hello"),
        lambda s: s.replace("run: uv --version", "run: uv --version\n        run: npm ci"),
        lambda s: s.replace("  setup:", "   setup:"),
        lambda s: s.replace("image: project:1", "image: null"),
        lambda s: s.replace("uv --version", "x" * 9000),
        lambda s: s.replace("name: Prepare project", "name: Prepare project\nname: Again"),
        lambda s: s.replace("run: uv --version", 'run: "\\u0000"'),
        lambda s: s + "\ud800",
    ],
)
def test_recipe_rejects_unsupported_ambiguous_and_excessive_input(change) -> None:
    """@brief Every unimplemented YAML semantic is an explicit typed failure."""
    with pytest.raises(PreparationError):
        parse_recipe(change(RECIPE), "setup")


class SourceRunner:
    """@brief Exact Git source fake, including raw CRLF bytes and metadata."""

    def __init__(self, source=RECIPE, mode="100644", corrupt=""):
        self.source, self.mode, self.corrupt = source, mode, corrupt
        self.calls = []

    def __call__(self, argv, **kwargs):
        """@brief Supply Git contract responses without executing Git."""
        self.calls.append(argv)
        if self.corrupt == "exit":
            return CommandResult(exit_code=1)
        command = argv[3]
        if command == "rev-parse":
            out = "a" * 40
        elif command == "ls-tree":
            out = f"{self.mode} blob {'b' * 40}\tprepare.yml\x00"
        elif argv[4] == "-s":
            out = str(len(self.source.encode()))
        else:
            out = self.source
        if self.corrupt == command:
            out = "corrupt"
        return CommandResult(stdout=out)


def recipe_config():
    """@brief Select one reviewed recipe with no competing profile image."""
    config = default_config()
    config.execution.preparation = "prepare.yml#setup@" + "a" * 40
    return config


def test_plan_pins_exact_source_image_and_policy_without_installing() -> None:
    """@brief Source preview resolves the exact reviewed bytes and image."""
    runner = SourceRunner(RECIPE.replace("\n", "\r\n"))
    plan = resolve_plan(recipe_config(), runner=runner, expected_revision="a" * 40)
    assert plan["image"] == "project:1" and plan["image_source"] == "recipe"
    assert plan["source"] == runner.source
    assert validate_plan(plan) == plan
    assert all(argv[0] == "git" for argv in runner.calls)


@pytest.mark.parametrize("corrupt", ["rev-parse", "ls-tree", "cat-file", "exit"])
def test_plan_rejects_corrupt_git_output(corrupt) -> None:
    """@brief Git output never guesses source identity after a malformed result."""
    with pytest.raises(PreparationError):
        resolve_plan(recipe_config(), runner=SourceRunner(corrupt=corrupt))


@pytest.mark.parametrize("mode", ["120000", "160000", "040000"])
def test_plan_rejects_links_submodules_and_directories(mode) -> None:
    """@brief Only the clone's regular tracked source blob is admissible."""
    with pytest.raises(PreparationError, match="regular"):
        resolve_plan(recipe_config(), runner=SourceRunner(mode=mode))


def test_plan_rejects_stale_review_image_conflict_and_tampering() -> None:
    """@brief Stale target, contradictory image and altered persisted plans fail."""
    config = recipe_config()
    with pytest.raises(PreparationError, match="stale"):
        resolve_plan(config, runner=SourceRunner(), expected_revision="c" * 40)
    config.container.image = "different:1"
    with pytest.raises(PreparationError, match="conflicts"):
        resolve_plan(config, runner=SourceRunner())
    config.container.image = ""
    plan = resolve_plan(config, runner=SourceRunner())
    plan["steps"][0]["run"] = "other"
    with pytest.raises(PreparationError, match="fingerprint"):
        validate_plan(plan)


def test_profile_exposes_reviewed_preparation_selection(tmp_path: Path) -> None:
    """@brief Recipe profiles have one strict version-bound selection."""
    source = tmp_path / "config.toml"
    source.write_text('[execution]\npreparation = "prepare.yml#setup@' + "a" * 40 + '"\n')
    config = load_config(source)
    assert hasattr(config, "execution"), "profile has no shared execution selection"
    assert config.execution.backend == "container"
    assert config.execution.preparation.endswith("a" * 40)
    assert not any("execution" in issue for issue in validate_config(config))


@pytest.mark.parametrize(
    "selection", ["../x.yml#setup@" + "a" * 40, "x.yml#setup@HEAD", "C:/x.yml#setup@" + "a" * 40]
)
def test_profile_rejects_unsafe_preparation_selection(tmp_path: Path, selection: str) -> None:
    """@brief Unsafe selections fail at the human configuration boundary."""
    source = tmp_path / "config.toml"
    source.write_text(f'[execution]\npreparation = "{selection}"\n')
    assert any("execution" in issue for issue in validate_config(load_config(source)))


# END OF FILE


def test_readiness_uses_reviewed_effective_image_without_setup():
    """@brief Recipe readiness uses the same image without installing dependencies."""
    from adore.preparation import effective_probe_config

    config, runner = recipe_config(), SourceRunner()
    effective = effective_probe_config(config, runner=runner)
    assert effective.container.image == "project:1"
    assert config.container.image != effective.container.image
    assert all(argv[0] == "git" for argv in runner.calls)
    with pytest.raises(PreparationError):
        effective_probe_config(config, runner=SourceRunner(corrupt="rev-parse"))


@pytest.mark.parametrize(
    "field,value",
    [("selection", False), ("source", []), ("policy", {}), ("steps", {}), ("schema", True)],
)
def test_plan_rejects_rehashed_structural_corruption(field, value):
    """@brief A matching digest never excuses corrupt policy or source types."""
    from hashlib import sha256
    import json

    plan = resolve_plan(recipe_config(), runner=SourceRunner())
    plan[field] = value
    plan["fingerprint"] = sha256(
        json.dumps(
            {k: v for k, v in plan.items() if k != "fingerprint"},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    with pytest.raises(PreparationError):
        validate_plan(plan)


def test_job_ids_may_match_schema_field_names():
    """@brief A named job is independent of fields within that job."""
    recipe = parse_recipe(RECIPE.replace("  setup:", "  steps:"), "steps")
    assert recipe["image"] == "project:1"


def test_structural_inline_comments_and_unselected_invalid_jobs():
    """@brief Block comments are supported while every unselected job is validated."""
    assert (
        parse_recipe(RECIPE.replace("jobs:", "jobs: # project recipes"), "setup")["image"]
        == "project:1"
    )
    invalid = RECIPE + "  bad:\n    uses: remote/action\n"
    with pytest.raises(PreparationError):
        parse_recipe(invalid, "setup")
