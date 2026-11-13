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
@file    test_executor_recipes.py
@brief   Validate portable recipe input, retained sources and image dependency closure.
@details Temporary files and source bytes replace all external runtime operations.
"""

# IMPORTS
from io import BytesIO
import json
from pathlib import Path
import stat
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from adore.config import default_config
from adore.executor_recipes import RecipeStore, recipe_status, resolve_recipe
from adore.recipe_sources import RecipeError, parse_recipe, recipe_archive, recipe_compose
import pytest


# LOCAL HELPERS
def source_zip(files, *, manifest=None):
    """@brief Create a selected source archive, retaining caller-controlled entry names."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        if manifest is not None:
            archive.writestr("recipe.json", json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def config_for(image):
    """@brief Select one image in a direct, container-backed configuration."""
    config = default_config()
    config.container.image = image
    config.execution.backend = "container"
    return config


# PUBLIC CONTRACT TESTS
def test_context_recipe_is_retained_and_reexported_exactly(tmp_path):
    """@brief A context ZIP remains complete and independent of its original working files."""
    files = {
        "Dockerfile": b"FROM ubuntu:22.04\nCOPY setup.sh /setup.sh\n",
        "setup.sh": b"#!/bin/sh\nprintf 'project tooling'\n",
    }
    recipe = parse_recipe(source_zip(files), "sample-executor:1")
    store = RecipeStore(tmp_path)
    saved = store.put(recipe, expected_digest=None)
    assert saved
    selected = store.get("sample-executor:1")
    assert selected.image == "sample-executor:1"
    archive = recipe_archive(resolve_recipe(config_for(selected.image), home=tmp_path))
    with ZipFile(BytesIO(archive)) as output:
        manifest = json.loads(output.read("recipe.json"))
        assert manifest["image"] == selected.image
        assert output.read("context/setup.sh") == files["setup.sh"]
    restored = parse_recipe(archive, selected.image)
    assert restored.definitions[selected.image].files == selected.definitions[selected.image].files
    assert store.get("another-executor:1") is None


@pytest.mark.parametrize(
    "bad",
    [
        "traversal",
        "credential",
        "key",
        "symlink",
        "duplicate",
        "case",
        "oversized",
        "bad_json",
        "missing_copy",
        "unknown_schema",
    ],
)
def test_unsafe_recipe_input_is_refused_before_retention(tmp_path, bad):
    """@brief Archive, file and source-reference trust boundaries reject corrupt input."""
    files = {"Dockerfile": b"FROM scratch\n"}
    if bad == "traversal":
        files["../escape"] = b"bad"
    elif bad == "credential":
        files[".env"] = b"PRIVATE_FIXTURE=not-a-real-secret"
    elif bad == "key":
        files["file.txt"] = b"-----BEGIN OPENSSH PRIVATE KEY-----\nfixture\n"
    elif bad == "case":
        files.update({"tool.txt": b"one", "TOOL.txt": b"two"})
    elif bad == "oversized":
        files["large.bin"] = b"x" * (4 * 1024 * 1024 + 1)
    elif bad == "missing_copy":
        files["Dockerfile"] = b"FROM scratch\nCOPY unavailable.txt /input\n"
    if bad in {"symlink", "duplicate"}:
        buffer = BytesIO(source_zip(files))
        with ZipFile(buffer, "a") as archive:
            if bad == "duplicate":
                with pytest.warns(UserWarning):
                    archive.writestr("Dockerfile", b"FROM scratch\n")
            else:
                member = ZipInfo("linked")
                member.create_system = 3
                member.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(member, "outside")
        source = buffer.getvalue()
    elif bad == "bad_json":
        source = source_zip({**files, "recipe.json": b"{bad"})
    elif bad == "unknown_schema":
        source = source_zip(
            files, manifest={"schema": 99, "image": "sample-executor:1", "definitions": []}
        )
    else:
        source = source_zip(files)
    with pytest.raises(RecipeError):
        parse_recipe(source, "sample-executor:1")
    assert not (tmp_path / "executor-recipes").exists()


def test_image_chain_uses_all_local_sources_and_detects_missing_and_cycles(tmp_path):
    """@brief Multi-stage external references and ARG-resolved local bases close transitively."""
    store = RecipeStore(tmp_path)
    root = parse_recipe(
        b"ARG BASE=sample-middle:1\nFROM ${BASE} AS build\n"
        b"FROM scratch\nCOPY --from=build /tool /tool\n",
        "sample-executor:1",
    )
    store.put(root, expected_digest=None)
    config = config_for(root.image)
    assert recipe_status(config, home=tmp_path)["missing_images"] == ["sample-middle:1"]
    with pytest.raises(RecipeError, match="recipe_base_missing"):
        resolve_recipe(config, home=tmp_path)
    store.put(parse_recipe(b"FROM sample-bottom:1\n", "sample-middle:1"), expected_digest=None)
    assert recipe_status(config, home=tmp_path)["missing_images"] == ["sample-bottom:1"]
    store.put(parse_recipe(b"FROM alpine:3.21\n", "sample-bottom:1"), expected_digest=None)
    complete = resolve_recipe(config, home=tmp_path)
    compose = recipe_compose(complete)
    root_service = compose["services"]["executor"]
    assert root_service["build"]["additional_contexts"]["sample-middle:1"].startswith("service:")
    assert len(compose["services"]) == 3
    status = recipe_status(config, home=tmp_path)
    assert status["available"] is True
    store.put(
        parse_recipe(b"FROM sample-executor:1\n", "sample-bottom:1"),
        expected_digest=store.binding_digest("sample-bottom:1"),
    )
    with pytest.raises(RecipeError, match="recipe_cycle"):
        resolve_recipe(config, home=tmp_path)


def test_built_in_base_is_available_without_commands_or_registration(tmp_path):
    """@brief ADORE's own base and dependent projects include the shipped Pi tooling."""
    config = config_for("adore-executor-base:1.0.0")
    result = resolve_recipe(config, home=tmp_path)
    definition = result.definitions[config.container.image]
    assert "pi/adore-guard.ts" in definition.files
    assert "pi/adore-chatgpt.mjs" in definition.files
    assert "LICENSE.txt" in definition.files
    assert b"PI_PACKAGE=" in definition.files[definition.dockerfile][0]
    store = RecipeStore(tmp_path)
    store.put(
        parse_recipe(b"FROM adore-executor-base:1.0.0\n", "sample-executor:1"), expected_digest=None
    )
    assert len(resolve_recipe(config_for("sample-executor:1"), home=tmp_path).definitions) == 2
    assert recipe_status(config_for("unknown-executor:1"), home=tmp_path)["available"] is False


@pytest.mark.parametrize("corruption", ["binding_schema", "binding_image", "object", "linked"])
def test_corrupt_recipe_storage_is_not_repaired_or_hidden(tmp_path, corruption, monkeypatch):
    """@brief Corrupt selected data names recovery and leaves unrelated definitions readable."""
    store = RecipeStore(tmp_path)
    store.put(parse_recipe(b"FROM scratch\n", "sample-executor:1"), expected_digest=None)
    store.put(parse_recipe(b"FROM scratch\n", "other-executor:1"), expected_digest=None)
    binding = store.binding_path("sample-executor:1")
    if corruption == "object":
        digest = store.binding_digest("sample-executor:1")
        selected = store.root / "objects" / (digest + ".zip")
        selected.write_bytes(b"corrupt")
    elif corruption == "linked":
        selected = binding
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == selected or original(path))
    else:
        selected = binding
        data = json.loads(selected.read_bytes())
        data["schema" if corruption == "binding_schema" else "image"] = (
            77 if corruption == "binding_schema" else "unrelated:1"
        )
        selected.write_text(json.dumps(data))
    old = selected.read_bytes() if not selected.is_symlink() else None
    with pytest.raises(RecipeError) as error:
        store.get("sample-executor:1")
    assert error.value.code == "recipe_store_corrupt"
    assert "executor-recipes" in error.value.recovery
    assert not old or selected.read_bytes() == old
    assert store.get("other-executor:1").image == "other-executor:1"


def test_unknown_variables_and_stage_cycles_are_not_treated_as_external_images():
    """@brief Unsupported dynamic inputs cannot masquerade as complete portable sources."""
    for source in (
        b"FROM ${UNKNOWN}\n",
        b"FROM alpine AS stage\nFROM stage AS stage\n",
        b"FROM scratch\nCOPY <<EOF /x\ncontents\nEOF\n",
    ):
        with pytest.raises(RecipeError):
            parse_recipe(source, "sample-executor:1")


def test_registered_public_named_base_is_retained_in_the_export(tmp_path):
    """@brief An explicitly retained local base wins over its public-looking image name."""
    store = RecipeStore(tmp_path)
    store.put(
        parse_recipe(b"FROM scratch\nLABEL local=base\n", "ubuntu:22.04"), expected_digest=None
    )
    store.put(parse_recipe(b"FROM ubuntu:22.04\n", "sample-executor:1"), expected_digest=None)
    result = resolve_recipe(config_for("sample-executor:1"), home=tmp_path)
    assert "ubuntu:22.04" in result.definitions


def test_maximum_context_roundtrips_with_export_metadata():
    """@brief Export metadata does not consume the declared 16 MiB build-input allowance."""
    dockerfile = b"FROM scratch\n"
    files = {
        "Dockerfile": dockerfile,
        **{f"part-{i}.bin": b"x" * (4 * 1024 * 1024) for i in range(3)},
        "last.bin": b"x" * (4 * 1024 * 1024 - len(dockerfile)),
    }
    original = parse_recipe(source_zip(files), "sample-executor:1")
    result = parse_recipe(
        recipe_archive(original, config_raw=b"# saved configuration\n"), "sample-executor:1"
    )
    assert result.definitions[result.image].files == original.definitions[original.image].files


def test_long_portable_context_paths_roundtrip_after_export_prefixing():
    """@brief A maximum-length source path remains valid in the exported context directory."""
    name = "x" * 240
    original = parse_recipe(
        source_zip({"Dockerfile": b"FROM scratch\n", name: b"input"}), "sample-executor:1"
    )
    restored = parse_recipe(recipe_archive(original), original.image)
    assert name in restored.definitions[restored.image].files


def test_corrupt_compressed_bytes_raise_a_typed_recipe_error():
    """@brief Broken deflate input cannot escape as an untyped decompressor exception."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Dockerfile", b"FROM scratch\n")
    source = bytearray(buffer.getvalue())
    offset = 30 + len("Dockerfile")
    source[offset] = 0xFF
    with pytest.raises(RecipeError):
        parse_recipe(bytes(source), "sample-executor:1")


def test_atomic_recipe_binding_write_failure_keeps_previous_definition(tmp_path, monkeypatch):
    """@brief A failed association replacement cannot erase the previous verified source."""
    from adore import executor_recipes

    store = RecipeStore(tmp_path)
    first = store.put(parse_recipe(b"FROM scratch\n", "sample-executor:1"), expected_digest=None)
    binding = store.binding_path("sample-executor:1")
    original = binding.read_bytes()
    replace = executor_recipes.os.replace

    def unavailable(source, destination):
        """@brief Model a failed final filesystem replacement only."""
        if Path(destination) == binding:
            raise OSError("fixture storage unavailable")
        return replace(source, destination)

    monkeypatch.setattr(executor_recipes.os, "replace", unavailable)
    with pytest.raises(RecipeError, match="recipe_write_failed"):
        store.put(
            parse_recipe(b"FROM scratch\nLABEL changed=yes\n", "sample-executor:1"),
            expected_digest=first,
        )
    assert binding.read_bytes() == original
    assert store.binding_digest("sample-executor:1") == first
    assert store.get("sample-executor:1").image == "sample-executor:1"


def test_prepared_project_selects_its_effective_image_without_changing_configuration(
    tmp_path, monkeypatch
):
    """@brief Preparation selects the same effective image as readiness."""
    from adore import preparation

    config = config_for("configured-base:1")
    config.execution.preparation = "environment.toml@" + "a" * 40
    monkeypatch.setattr(
        preparation, "preview_plan", lambda config, *, runner: {"image": "effective-executor:1"}
    )
    RecipeStore(tmp_path).put(
        parse_recipe(b"FROM scratch\n", "effective-executor:1"), expected_digest=None
    )
    status = recipe_status(config, home=tmp_path)
    assert status["image"] == "effective-executor:1"
    assert status["available"] is True
    assert config.container.image == "configured-base:1"
    assert config.execution.preparation.startswith("environment.toml@")


@pytest.mark.parametrize(
    "source",
    [
        b"FROM scratch\nNOTANINSTRUCTION invalid\n",
        b"FROM scratch\nARG API_KEY=fixture-private\n",
        b"FROM scratch\nENV ACCESS_TOKEN=fixture-private\n",
    ],
)
def test_invalid_instructions_and_literal_secret_defaults_are_refused(source):
    """@brief Recognizable literal credentials and invalid syntax are not retained as recipes."""
    with pytest.raises(RecipeError):
        parse_recipe(source, "sample-executor:1")


def test_embedded_base_sources_are_reusable_without_overwriting_existing_bindings(tmp_path):
    """@brief A complete snapshot supplies reusable bases and keeps its pinned inputs."""
    manifest = {
        "schema": 1,
        "image": "sample-executor:1",
        "definitions": [
            {
                "image": "sample-executor:1",
                "context": "app",
                "dockerfile": "Dockerfile",
                "files": ["Dockerfile"],
                "build_args": {"BASE": "sample-base:1"},
            },
            {
                "image": "sample-base:1",
                "context": "base",
                "dockerfile": "Dockerfile",
                "files": ["Dockerfile"],
            },
        ],
    }
    document = parse_recipe(
        source_zip(
            {
                "app/Dockerfile": b"ARG BASE\nFROM ${BASE}\n",
                "base/Dockerfile": b"FROM scratch\nLABEL pinned=yes\n",
            },
            manifest=manifest,
        ),
        "sample-executor:1",
    )
    store = RecipeStore(tmp_path)
    store.put(document, expected_digest=None)
    base = store.get("sample-base:1")
    assert base is not None
    assert set(base.definitions) == {"sample-base:1"}
    previous = store.binding_digest("sample-base:1")
    store.put(
        parse_recipe(b"FROM scratch\nLABEL revised=yes\n", "sample-base:1"),
        expected_digest=previous,
    )
    selected = resolve_recipe(config_for("sample-base:1"), home=tmp_path)
    assert b"revised=yes" in selected.definitions[selected.image].files["Dockerfile"][0]
    complete = resolve_recipe(config_for("sample-executor:1"), home=tmp_path)
    assert b"pinned=yes" in complete.definitions["sample-base:1"].files["Dockerfile"][0]


def test_unrelated_embedded_definitions_are_not_published_as_global_recipes():
    """@brief A portable upload cannot attach unrelated image definitions implicitly."""
    manifest = {
        "schema": 1,
        "image": "sample-executor:1",
        "definitions": [
            {"image": name, "context": context, "dockerfile": "Dockerfile", "files": ["Dockerfile"]}
            for name, context in (("sample-executor:1", "app"), ("unrelated:1", "other"))
        ],
    }
    with pytest.raises(RecipeError):
        parse_recipe(
            source_zip(
                {"app/Dockerfile": b"FROM scratch\n", "other/Dockerfile": b"FROM scratch\n"},
                manifest=manifest,
            ),
            "sample-executor:1",
        )


def test_recipe_store_lock_io_failure_is_typed(tmp_path, monkeypatch):
    """@brief Unavailable metadata storage is not an untyped service exception."""
    from adore import executor_recipes

    def unavailable(_store):
        """@brief Model a failed lock-file create at the filesystem boundary."""
        raise OSError("fixture storage unavailable")

    monkeypatch.setattr(executor_recipes.StateStore, "acquire_lock", unavailable)
    with pytest.raises(RecipeError, match="recipe_write_failed"):
        RecipeStore(tmp_path).put(
            parse_recipe(b"FROM scratch\n", "sample-executor:1"), expected_digest=None
        )


def test_stage_arguments_do_not_hide_a_local_from_dependency(tmp_path):
    """@brief FROM uses global ARG values even after a stage redeclares the name."""
    recipe = parse_recipe(
        b"ARG BASE=sample-local:1\nFROM ubuntu:24.04 AS build\n"
        b"ARG BASE=ubuntu:24.04\nFROM ${BASE}\n",
        "sample-executor:1",
    )
    RecipeStore(tmp_path).put(recipe, expected_digest=None)
    assert recipe_status(config_for(recipe.image), home=tmp_path)["missing_images"] == [
        "sample-local:1"
    ]


def test_loopback_registry_requires_its_local_recipe(tmp_path):
    """@brief A host-local registry is not an external portable build prerequisite."""
    recipe = parse_recipe(b"FROM 127.0.0.1:5000/sample:1\n", "sample-executor:1")
    RecipeStore(tmp_path).put(recipe, expected_digest=None)
    assert recipe_status(config_for(recipe.image), home=tmp_path)["missing_images"] == [
        "127.0.0.1:5000/sample:1"
    ]


@pytest.mark.parametrize("field", ["source", "src"])
def test_run_bind_context_sources_must_be_present(field):
    """@brief Default-context RUN bind mounts require the selected source bytes."""
    dockerfile = (
        "FROM ubuntu:24.04\nRUN --mount=type=bind,"
        + field
        + "=input.txt,target=/input cat /input\n"
    ).encode()
    with pytest.raises(RecipeError, match="recipe_context_incomplete"):
        parse_recipe(dockerfile, "sample-executor:1")
    recipe = parse_recipe(
        source_zip({"Dockerfile": dockerfile, "input.txt": b"source"}), "sample-executor:1"
    )
    restored = parse_recipe(recipe_archive(recipe), recipe.image)
    assert restored.definitions[recipe.image].files["input.txt"][0] == b"source"


def test_stage_environment_selects_actual_context_source():
    """@brief ENV precedence and unrelated-stage boundaries cannot hide missing COPY files."""
    dockerfile = (
        b"ARG FILE=present.txt\nFROM ubuntu:24.04\nENV FILE=missing.txt\nCOPY ${FILE} /input\n"
    )
    with pytest.raises(RecipeError, match="recipe_context_incomplete"):
        parse_recipe(
            source_zip({"Dockerfile": dockerfile, "present.txt": b"wrong"}), "sample-executor:1"
        )
    recipe = parse_recipe(
        source_zip({"Dockerfile": dockerfile, "missing.txt": b"right"}), "sample-executor:1"
    )
    assert "missing.txt" in recipe.definitions[recipe.image].files
    # A prior, unrelated stage's argument is unavailable in the next stage.
    with pytest.raises(RecipeError, match="recipe_dockerfile_unsupported"):
        parse_recipe(
            source_zip(
                {
                    "Dockerfile": b"FROM ubuntu AS first\nARG FILE=present.txt\n"
                    b"FROM scratch\nCOPY $FILE /input\n",
                    "present.txt": b"wrong",
                }
            ),
            "sample-executor:1",
        )
    inherited = b"FROM ubuntu AS first\nENV FILE=present.txt\nFROM first\nCOPY $FILE /input\n"
    assert parse_recipe(
        source_zip({"Dockerfile": inherited, "present.txt": b"right"}), "sample-executor:1"
    )


@pytest.mark.parametrize("failure", ["missing_object", "corrupt_object", "object_collision"])
def test_reported_object_recovery_allows_a_fresh_attachment(tmp_path, failure):
    """@brief Deleting exactly the reported catalog removes dangling links and restores saves."""
    import shutil

    home = tmp_path / "home"
    store = RecipeStore(home)
    recipe = parse_recipe(b"FROM scratch\n", "sample-executor:1")
    digest = store.put(recipe, expected_digest=None)
    obj = store.root / "objects" / (digest + ".zip")
    if failure == "missing_object":
        obj.unlink()
    else:
        obj.write_bytes(b"corrupt")
    if failure == "object_collision":
        store.binding_path(recipe.image).unlink()
    with pytest.raises(RecipeError) as caught:
        if failure == "object_collision":
            store.put(recipe, expected_digest=None)
        else:
            store.get(recipe.image)
    assert caught.value.recovery == "executor-recipes"
    recovery = home / caught.value.recovery
    assert recovery.resolve().is_relative_to(home.resolve())
    shutil.rmtree(recovery)  # Explicit operator action against the test's temporary home.
    assert store.get(recipe.image) is None
    store.put(recipe, expected_digest=None)
    assert store.get(recipe.image).definitions == recipe.definitions


# END OF FILE
