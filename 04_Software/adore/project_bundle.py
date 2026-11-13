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
@file    project_bundle.py
@brief   Validate current complete project export archives without extraction.
@details Configuration bytes and retained recipes share one bounded import candidate.
"""

# IMPORTS
from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from adore.executor_recipes import effective_recipe_config
from adore.recipe_sources import (
    Recipe,
    RecipeError,
    canonical_image,
    image_dependencies,
    parse_recipe,
    public_image,
    recipe_compose,
)
from adore.util import run_command, strict_json_loads


# DATA MODELS / TYPEDEFINITIONS
@dataclass(frozen=True)
class ProjectBundle:
    """@brief Exact source configuration and its complete validated image graph."""

    config_raw: bytes
    recipe: Recipe


# PUBLIC API
def read_project_bundle(source: bytes) -> ProjectBundle:
    """
    @brief Validate an exported ZIP, retaining all source bytes only in memory.
    @param[in] source Bounded untrusted archive bytes.
    @return Exact UTF-8 TOML and a complete recipe with consistent Compose metadata.
    @exception RecipeError For corrupt, unsafe, incomplete or inconsistent input.
    """
    try:
        recipe = parse_recipe(source, None)
    except RecipeError as exc:
        if exc.code == "recipe_invalid":
            raise RecipeError("bundle_invalid") from exc
        raise
    try:
        with ZipFile(BytesIO(source)) as archive:
            if not {"config.toml", "recipe.json", "compose.yaml", "BUILD.txt"}.issubset(
                archive.namelist()
            ):
                raise RecipeError("bundle_invalid")
            raw = archive.read("config.toml")
            if not raw:
                raise RecipeError("bundle_invalid")
            raw.decode("utf-8")
            compose = "\n".join(
                line
                for line in archive.read("compose.yaml").decode("utf-8").splitlines()
                if not line.lstrip().startswith("#")
            )
            if strict_json_loads(compose) != recipe_compose(recipe):
                raise RecipeError("bundle_invalid")
    except (BadZipFile, OSError, ValueError, KeyError, RecursionError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError("bundle_invalid") from exc
    missing = set()
    for definition in recipe.definitions.values():
        for reference in image_dependencies(definition):
            image = canonical_image(reference)
            if (
                image not in recipe.definitions
                and reference not in definition.external_images
                and image not in definition.external_images
                and not public_image(image)
            ):
                missing.add(image)
    if missing:
        raise RecipeError("recipe_base_missing", missing=missing)
    return ProjectBundle(raw, recipe)


def validate_bundle_image(bundle: ProjectBundle, config, *, runner=run_command) -> None:
    """
    @brief Bind the declared source root to the configuration's effective executor.
    @param[in] bundle Validated exported source graph.
    @param[in] config Structurally valid project configuration.
    @param[in] runner Existing bounded local Git reader for preparation-selected images.
    @exception RecipeError For native configuration or an inconsistent image selection.
    """
    if config.execution.backend != "container":
        raise RecipeError("bundle_image_mismatch")
    selected = effective_recipe_config(config, runner=runner)
    if selected.container.image != bundle.recipe.image:
        raise RecipeError("bundle_image_mismatch")


# END OF FILE
