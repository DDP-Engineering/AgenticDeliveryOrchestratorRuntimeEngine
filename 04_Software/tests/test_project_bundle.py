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
@file    test_project_bundle.py
@brief   Validate complete export archives at their in-memory import boundary.
@details Source bytes replace external tools and hostile ZIPs remain unextracted.
"""

# IMPORTS
from dataclasses import replace
from io import BytesIO
import json
import stat
from zipfile import ZipFile, ZipInfo

from adore.config import default_config
from adore.executor_recipes import RecipeStore, resolve_recipe
from adore.project_bundle import read_project_bundle, validate_bundle_image
from adore.recipe_sources import Definition, Recipe, RecipeError, recipe_archive
import pytest


# LOCAL HELPERS
def graph():
    """@brief Use a declared local base and an executable source file."""
    return Recipe(
        "bundle:1",
        {
            "bundle:1": Definition(
                "bundle:1",
                "Dockerfile",
                {
                    "Dockerfile": (b"FROM base:1\nCOPY tool.sh /tool.sh\n", 0o644),
                    "tool.sh": (b"# fixture\nprintf fixture\n", 0o755),
                },
            ),
            "base:1": Definition(
                "base:1",
                "Dockerfile",
                {
                    "Dockerfile": (b"FROM ubuntu:22.04\n", 0o644),
                },
            ),
        },
    )


def rewrite(source, *, updates=None, remove=(), extra=None):
    """@brief Alter selected untrusted entries without extracting the source ZIP."""
    out = BytesIO()
    with ZipFile(BytesIO(source)) as source_zip, ZipFile(out, "w") as target:
        for entry in source_zip.infolist():
            if entry.filename not in remove:
                target.writestr(
                    entry, (updates or {}).get(entry.filename, source_zip.read(entry.filename))
                )
        if extra:
            target.writestr(*extra)
    return out.getvalue()


# PUBLIC API / CONTRACT TESTS
def test_complete_bundle_preserves_config_and_source_modes_without_execution():
    """@brief The current exported archive roundtrips exact bytes and image selection."""
    expected = graph()
    source = recipe_archive(expected, config_raw=b"# exact config\r\n")
    bundle = read_project_bundle(source)
    assert bundle.config_raw == b"# exact config\r\n"
    assert bundle.recipe.definitions == expected.definitions
    config = default_config()
    config.container.image = expected.image

    def runner(*args, **kwargs):
        """@brief A directly configured image has no external inspection step."""
        raise AssertionError("unexpected command")

    validate_bundle_image(bundle, config, runner=runner)


@pytest.mark.parametrize(
    "bad",
    [
        "not_zip",
        "missing_config",
        "missing_compose",
        "missing_build",
        "no_utf8",
        "empty_config",
        "traversal",
        "symlink",
        "duplicate",
        "unknown_schema",
        "compose_mismatch",
        "compose_duplicate",
        "large_source",
        "private_key",
        "missing_base",
        "cycle",
    ],
)
def test_bundle_rejects_unsafe_incomplete_and_inconsistent_input(bad):
    """@brief Trust-boundary corruption is refused before callers can retain anything."""
    source = recipe_archive(graph(), config_raw=b"# exact config\n")
    if bad == "not_zip":
        source = b"not a current project ZIP"
    elif bad.startswith("missing_") and bad != "missing_base":
        source = rewrite(
            source,
            remove=(
                {
                    "missing_config": "config.toml",
                    "missing_compose": "compose.yaml",
                    "missing_build": "BUILD.txt",
                }[bad],
            ),
        )
    elif bad in {"no_utf8", "empty_config", "private_key"}:
        content = {
            "no_utf8": b"\xff",
            "empty_config": b"",
            "private_key": b"-----BEGIN OPENSSH PRIVATE KEY-----\nfixture",
        }[bad]
        source = rewrite(source, updates={"config.toml": content})
    elif bad == "traversal":
        source = rewrite(source, extra=("../outside", b"fixture"))
    elif bad == "symlink":
        entry = ZipInfo("link")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        source = rewrite(source, extra=(entry, "outside"))
    elif bad == "duplicate":
        with pytest.warns(UserWarning):
            source = rewrite(source, extra=("config.toml", b"# duplicate"))
    elif bad == "unknown_schema":
        with ZipFile(BytesIO(source)) as z:
            metadata = json.loads(z.read("recipe.json"))
        metadata["schema"] = 99
        source = rewrite(source, updates={"recipe.json": json.dumps(metadata).encode()})
    elif bad == "compose_mismatch":
        source = rewrite(source, updates={"compose.yaml": b'{"services":{}}'})
    elif bad == "compose_duplicate":
        source = rewrite(source, updates={"compose.yaml": b'{"services":{},"services":{}}'})
    elif bad == "large_source":
        source = rewrite(source, updates={"context/tool.sh": b"x" * (4 * 1024 * 1024 + 1)})
    elif bad == "missing_base":
        source = recipe_archive(
            replace(graph(), definitions={"bundle:1": graph().definitions["bundle:1"]}),
            config_raw=b"# config",
        )
    elif bad == "cycle":
        definitions = dict(graph().definitions)
        definitions["base:1"] = Definition(
            "base:1",
            "Dockerfile",
            {
                "Dockerfile": (b"FROM bundle:1\n", 0o644),
            },
        )
        source = recipe_archive(replace(graph(), definitions=definitions), config_raw=b"# config")
    with pytest.raises(RecipeError):
        read_project_bundle(source)


@pytest.mark.parametrize("selection", ["other:1", "native"])
def test_bundle_refuses_configuration_image_mismatch(selection):
    """@brief A ZIP cannot attach an unrelated definition or a container to native config."""
    bundle = read_project_bundle(recipe_archive(graph(), config_raw=b"# config"))
    config = default_config()
    if selection == "native":
        config.execution.backend = "local"
    else:
        config.container.image = selection
    with pytest.raises(RecipeError, match="bundle_image_mismatch"):
        validate_bundle_image(bundle, config)


@pytest.mark.parametrize("image", ["bundle:1", "different:1"])
def test_preparation_selected_image_is_checked_without_rewriting_configuration(monkeypatch, image):
    """@brief Existing preparation resolution owns the effective image selection."""
    from adore import preparation

    bundle = read_project_bundle(recipe_archive(graph(), config_raw=b"# config"))
    config = default_config()
    config.execution.preparation = "environment.toml@" + "a" * 40
    config.container.image = "configured-base:1"
    monkeypatch.setattr(preparation, "preview_plan", lambda config, *, runner: {"image": image})
    if image == "bundle:1":
        validate_bundle_image(bundle, config)
    else:
        with pytest.raises(RecipeError, match="bundle_image_mismatch"):
            validate_bundle_image(bundle, config)
    assert config.container.image == "configured-base:1"
    assert config.execution.preparation.startswith("environment.toml@")


def test_changed_association_under_publication_lock_cannot_be_overwritten(tmp_path):
    """@brief A source writer between preview and lock acquisition invalidates the import."""
    from adore.recipe_sources import parse_recipe

    store = RecipeStore(tmp_path)
    source = graph()
    observed = store.preview_import(source)
    other = parse_recipe(b"FROM ubuntu:24.04\n", "base:1")
    digest = store.put(other, expected_digest=None)

    def publish():
        """@brief Stale archive sources must not reach project publication."""
        raise AssertionError("unexpected publication")

    with pytest.raises(RecipeError, match="recipe_changed"):
        store.publish_import(source, revisions=observed, publish=publish)
    assert store.binding_digest("base:1") == digest
    assert store.binding_digest("bundle:1") is None


def test_import_preserves_the_implicit_standard_base_until_sources_match(tmp_path):
    """@brief An import cannot silently replace bundled sources under their existing tag."""
    from adore.recipe_sources import parse_recipe

    builtin = resolve_recipe(default_config(), home=tmp_path)
    store = RecipeStore(tmp_path)
    with pytest.raises(RecipeError, match="recipe_import_conflict"):
        store.preview_import(parse_recipe(b"FROM scratch\n", builtin.image))
    observed = store.preview_import(builtin)
    assert store.publish_import(builtin, revisions=observed, publish=lambda: {"paused": True}) == {
        "paused": True
    }
    assert store.get(builtin.image).definitions == builtin.definitions


# END OF FILE
