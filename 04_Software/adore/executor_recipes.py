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
@file    executor_recipes.py
@brief   Retain image-shared executor sources and resolve complete image definitions.
@details Recipe metadata is independent of project/job configuration. No Docker,
         forge, model or caller-selected host-file commands are executed here.
"""

# IMPORTS
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from adore.config import EXECUTOR_BASE_IMAGE
from adore.profiles import ProfileStore
from adore.recipe_sources import (
    MAX_ARCHIVE_BYTES,
    MAX_DEFINITIONS,
    MAX_FILES,
    MAX_INPUT_BYTES,
    Definition,
    Recipe,
    RecipeError,
    canonical_image,
    image_dependencies,
    image_reference,
    parse_recipe,
    public_image,
    recipe_archive,
)
from adore.state import StateStore
from adore.util import run_command


# DATA MODELS / TYPEDEFINITIONS
class RecipeStore:
    """@brief Immutable source objects and independently validated exact-image bindings."""

    def __init__(self, home: Path):
        """@brief Select a trusted ADORE home without creating a store during reads."""
        self.root = Path(home) / "executor-recipes"

    def binding_path(self, image: str) -> Path:
        """@brief Derive an opaque safe filename from a validated exact image tag."""
        image_reference(image, tagged=True)
        return self.root / "images" / (sha256(image.encode()).hexdigest() + ".json")

    def _refuse(self, path):
        """@brief Name only the affected relative record for explicit operator recovery."""
        selected = path.relative_to(self.root)
        # Shared-object deletion alone strands its image bindings. An explicit
        # catalog reset removes both sides; a bad binding remains recoverable
        # independently. Never perform either deletion in the application.
        suffix = "." if selected.parts[:1] == ("objects",) else selected.as_posix()
        relative = "executor-recipes" + ("/" + suffix if suffix != "." else "")
        raise RecipeError("recipe_store_corrupt", recovery=relative)

    def _parents(self, path):
        """@brief Refuse links in the controlled recipe-store hierarchy."""
        try:
            for parent in (self.root, path.parent, path):
                if parent.is_symlink():
                    self._refuse(parent)
            for parent in (self.root, path.parent):
                if parent.exists() and not parent.is_dir():
                    self._refuse(parent)
        except OSError as exc:
            raise RecipeError("recipe_store_corrupt", recovery="executor-recipes") from exc

    def _binding(self, image):
        """@brief Validate one current binding without reading another image's metadata."""
        path = self.binding_path(image)
        self._parents(path)
        if not path.exists():
            return None
        try:
            with path.open("rb") as source:
                raw = source.read(2049)
            if len(raw) > 2048:
                self._refuse(path)
            value = json.loads(raw, object_pairs_hook=_unique_record)
            if (
                not isinstance(value, dict)
                or set(value) != {"schema", "image", "digest"}
                or type(value["schema"]) is not int
                or value["schema"] != 1
                or value["image"] != image
                or not isinstance(value["digest"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", value["digest"])
            ):
                self._refuse(path)
            return value
        except (OSError, ValueError, TypeError, RecursionError):
            self._refuse(path)

    def binding_digest(self, image: str) -> str | None:
        """@brief Read the observed association revision, or None when unregistered."""
        binding = self._binding(image)
        return binding["digest"] if binding else None

    def get(self, image: str) -> Recipe | None:
        """
        @brief Load exact retained sources after binding, digest and schema validation.
        @param[in] image Exact output image tag.
        @return A recipe or None for a missing association.
        @exception RecipeError For corrupt selected records; no fallback or repair occurs.
        """
        binding = self._binding(image)
        if binding is None:
            return None
        path = self.root / "objects" / (binding["digest"] + ".zip")
        self._parents(path)
        try:
            with path.open("rb") as source:
                raw = source.read(MAX_ARCHIVE_BYTES + 1)
            if len(raw) > MAX_ARCHIVE_BYTES or sha256(raw).hexdigest() != binding["digest"]:
                self._refuse(path)
            document = parse_recipe(raw, None)
        except (OSError, ValueError, TypeError):
            self._refuse(path)
        if image not in document.definitions:
            self._refuse(self.binding_path(image))
        selected = {}

        def include(name):
            """@brief Select only the requested image and its embedded dependency sources."""
            if name in selected:
                return
            selected[name] = document.definitions[name]
            for reference in image_dependencies(selected[name]):
                target = canonical_image(reference)
                if target in document.definitions:
                    include(target)

        include(image)
        return replace(document, image=image, definitions=selected)

    def put(self, recipe: Recipe, *, expected_digest: str | None) -> str:
        """
        @brief Retain a validated immutable source object and atomically bind its image.
        @param[in] recipe Selected image and source definitions.
        @param[in] expected_digest Previously observed association, None for absent.
        @return SHA-256 of the canonical retained source archive.
        @exception RecipeError For unsafe input, corrupt data, contention or stale replacement.
        """
        if expected_digest is not None and (
            not isinstance(expected_digest, str)
            or not re.fullmatch(r"[a-f0-9]{64}", expected_digest)
        ):
            raise RecipeError()
        raw = recipe_archive(recipe)
        parse_recipe(raw, recipe.image)
        digest = sha256(raw).hexdigest()
        binding = self.binding_path(recipe.image)
        self._parents(binding)
        lock = StateStore(self.root, "adore-recipes")
        try:
            acquired = lock.acquire_lock()
        except OSError as exc:
            raise RecipeError("recipe_write_failed") from exc
        if not acquired:
            raise RecipeError("recipe_changed")
        try:
            previous = self.binding_digest(recipe.image)
            if previous != expected_digest:
                raise RecipeError("recipe_changed")
            if previous is not None:
                self.get(recipe.image)
            objects = self.root / "objects"
            self._parents(objects / (digest + ".zip"))
            objects.mkdir(exist_ok=True)
            binding.parent.mkdir(exist_ok=True)
            object_path = objects / (digest + ".zip")
            if object_path.exists():
                with object_path.open("rb") as source:
                    if source.read(MAX_ARCHIVE_BYTES + 1) != raw:
                        self._refuse(object_path)
            with TemporaryDirectory(prefix=".recipe-", dir=self.root) as directory:
                temporary = Path(directory)
                if not object_path.exists():
                    staged = temporary / "source.zip"
                    staged.write_bytes(raw)
                    staged.chmod(0o600)
                    os.replace(staged, object_path)
                created = []
                try:
                    # Previously unregistered bases are shared; reviewed bindings
                    # and the bundled default are never replaced implicitly.
                    supplemental = sorted(
                        set(recipe.definitions) - {recipe.image, EXECUTOR_BASE_IMAGE}
                    )
                    for image in [*supplemental, recipe.image]:
                        target = self.binding_path(image)
                        if image != recipe.image and (target.exists() or target.is_symlink()):
                            continue
                        encoded = (
                            json.dumps(
                                {"schema": 1, "image": image, "digest": digest}, sort_keys=True
                            )
                            + "\n"
                        ).encode()
                        staged = temporary / "binding.json"
                        staged.write_bytes(encoded)
                        staged.chmod(0o600)
                        os.replace(staged, target)
                        if image != recipe.image:
                            created.append((target, encoded))
                except OSError:
                    for target, encoded in created:
                        try:
                            with target.open("rb") as source:
                                unchanged = source.read(2049) == encoded
                            if unchanged:
                                target.unlink()
                        except OSError:
                            pass  # Sources remain valid; no previous binding is lost.
                    raise
            return digest
        except OSError as exc:
            raise RecipeError("recipe_write_failed") from exc
        finally:
            try:
                lock.release_lock()
            except OSError as exc:
                raise RecipeError("recipe_write_failed") from exc


# LOCAL HELPERS
def _unique_record(pairs):
    """@brief Refuse duplicate keys in persisted image associations."""
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate recipe record field")
    return value


def _builtin(image):
    """@brief Read the same canonical base assets in a source checkout or installed wheel."""
    if image != EXECUTOR_BASE_IMAGE:
        return None
    packaged = Path(__file__).parent / "_executor_recipe"
    source = Path(__file__).parent.parent / "docker"
    base = packaged if packaged.exists() else source
    dockerfile = "Dockerfile" if base == packaged else "Dockerfile.executor-base"
    try:
        files = {
            name: ((base / name).read_bytes(), 0o644)
            for name in (dockerfile, "pi/adore-guard.ts", "pi/adore-chatgpt.mjs")
        }
        license_path = (
            base / "LICENSE.txt" if base == packaged else base.parent.parent / "LICENSE.txt"
        )
        files["LICENSE.txt"] = (license_path.read_bytes(), 0o644)
        # Normalize the canonical source Dockerfile name, keeping COPY paths unchanged.
        files["Dockerfile"] = files.pop(dockerfile)
        definition = Definition(image, "Dockerfile", files)
        image_dependencies(definition)
        return Recipe(image, {image: definition}, source="builtin")
    except (OSError, ValueError, TypeError) as exc:
        raise RecipeError("recipe_builtin_unavailable") from exc


def _resolve(config, *, home, runner, overrides):
    """@brief Resolve a bounded source graph and report unavailable local bases separately."""
    config = effective_recipe_config(config, runner=runner)
    selected = config.container.image
    image_reference(selected, tagged=True)
    store = RecipeStore(home)
    known = {}
    missing = set()
    visiting = set()
    complete = {}
    observed = set()
    root_source = "missing"
    root_revision = None

    def load(image):
        """@brief Select explicit overrides, retained sources, root Git sources or built-ins."""
        if image in overrides:
            return overrides[image]
        retained = store.get(image)
        if retained is not None:
            return retained
        if image == selected and config.container.build_definition:
            from adore.build_bundle import read_git_recipe

            return read_git_recipe(config, runner=runner)
        return _builtin(image)

    def visit(image):
        """@brief Close one local image's dependencies, refusing cycles and conflicting sources."""
        nonlocal root_source, root_revision
        if image in visiting:
            raise RecipeError("recipe_cycle")
        if image in complete or image in missing:
            return
        observed.add(image)
        if len(observed) > MAX_DEFINITIONS:
            raise RecipeError()
        if image not in known:
            recipe = load(image)
            if recipe is None:
                missing.add(image)
                return
            if image == selected:
                root_source, root_revision = recipe.source, recipe.revision
            for key, value in recipe.definitions.items():
                if key in known and known[key] != value:
                    raise RecipeError("recipe_definition_conflict")
                known[key] = value
            if (
                len(known) > MAX_DEFINITIONS
                or sum(len(value.files) for value in known.values()) > MAX_FILES
                or sum(len(raw) for value in known.values() for raw, _ in value.files.values())
                > MAX_INPUT_BYTES
            ):
                raise RecipeError()
        if image not in known:
            raise RecipeError()
        visiting.add(image)
        definition = known[image]
        for original in image_dependencies(definition):
            reference = canonical_image(original)
            if reference in known or reference in overrides:
                visit(reference)
            elif original in definition.external_images or reference in definition.external_images:
                continue
            else:
                try:
                    image_reference(reference, tagged=True)
                except RecipeError:
                    retained = None
                else:
                    retained = store.get(reference)
                if retained is not None or not public_image(reference):
                    visit(reference)
        visiting.remove(image)
        complete[image] = definition

    visit(selected)
    return Recipe(selected, complete, source=root_source, revision=root_revision), sorted(missing)


# PUBLIC API
def effective_recipe_config(config, *, runner=run_command):
    """@brief Select preparation's effective image in memory, preserving saved configuration."""
    if config.execution.backend != "container":
        return config
    from adore.preparation import PreparationError, effective_probe_config

    try:
        normalized = effective_probe_config(config, runner=runner)
    except PreparationError as exc:
        raise RecipeError("execution_plan_invalid") from exc
    image = canonical_image(normalized.container.image)
    if "@" in image or image.startswith("sha256:"):
        raise RecipeError("recipe_image_tag_required")
    return replace(
        normalized,
        container=replace(normalized.container, image=image),
        execution=replace(normalized.execution, preparation=""),
    )


def resolve_recipe(config, *, home=None, runner=run_command, overrides=None) -> Recipe:
    """
    @brief Resolve every local image required by the selected executor recipe.
    @param[in] config Saved project configuration.
    @param[in] home Trusted ADORE home containing retained image definitions.
    @param[in] runner Injectable Git source reader; never invokes a container runtime.
    @param[in] overrides Validated preview candidates replacing exact images in memory.
    @return Complete source-only image graph.
    @exception RecipeError For missing local images, corrupt sources or cycles.
    """
    recipe, missing = _resolve(
        config, home=home or ProfileStore().home, runner=runner, overrides=overrides or {}
    )
    if missing:
        raise RecipeError("recipe_base_missing", missing=missing)
    return recipe


def recipe_status(config, *, home=None, runner=run_command, overrides=None) -> dict:
    """@brief Expose non-secret availability metadata without creating catalog records."""
    home = home or ProfileStore().home
    if config.execution.backend != "container":
        return {
            "image": None,
            "available": False,
            "missing_images": [],
            "digest": None,
            "source": "native",
        }
    recipe, missing = _resolve(config, home=home, runner=runner, overrides=overrides or {})
    return {
        "image": recipe.image,
        "available": not missing,
        "missing_images": missing,
        "digest": RecipeStore(home).binding_digest(recipe.image),
        "source": recipe.source,
    }


# END OF FILE
