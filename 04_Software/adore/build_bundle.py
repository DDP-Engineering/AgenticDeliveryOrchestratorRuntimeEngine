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
@file    build_bundle.py
@brief   Export reviewed executor build inputs from an immutable Git revision.
@details Reads only declared regular Git blobs through an injectable runner.
         Working files, external credentials and container runtimes are never read.
"""

# IMPORTS
from hashlib import sha1, sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
from tempfile import TemporaryDirectory

from adore.recipe_sources import (
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_INPUT_BYTES,
    PRIVATE_KEY,
    RecipeError,
    image_reference,
    source_path,
)
from adore.util import CommandResult, CommandRunner, run_command

# CONSTANTS
_GIT_DIGEST = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")
_GIT_SELECTION = {"GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_NAMESPACE",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"}



# DATA MODELS / TYPEDEFINITIONS
class BuildBundleError(ValueError):
    """@brief Safe export rejection containing a stable, non-secret code."""

    def __init__(self, code: str = "build_definition_invalid"):
        """@brief Retain the operator-facing error code without source contents."""
        super().__init__(code)
        self.code = code


# LOCAL HELPERS
def _path(value: object) -> str:
    """@brief Accept a portable repository file path and exclude credential paths."""
    try:
        return source_path(value)
    except RecipeError as exc:
        raise BuildBundleError() from exc



def _git(runner: CommandRunner, repo: str, *argv: str, timeout: int = 15) -> CommandResult:
    """@brief Read the local Git object database without a partial-clone fetch."""
    env = {key: value for key, value in os.environ.items() if key.upper() not in _GIT_SELECTION}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1")
    result = runner(["git", *argv], cwd=repo, timeout=timeout, env=env)
    if not result.ok or result.timed_out:
        raise BuildBundleError("build_source_unavailable")
    return result


def _inputs(repo: str, revision: str, paths: list[str],
            runner: CommandRunner) -> dict[str, tuple[bytes, int]]:
    """@brief Read bounded, exact regular Git blobs, rejecting archive transformations."""
    result = _git(runner, repo, "ls-tree", "-l", "-z", "--full-tree", revision, "--", *paths)
    if len(result.stdout) > 65536:
        raise BuildBundleError("build_source_unavailable")
    expected = {}
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        try:
            metadata, name = entry.split("\t")
            mode, kind, digest, size_text = metadata.split()
            size = int(size_text)
        except (ValueError, TypeError) as exc:
            raise BuildBundleError() from exc
        if (name not in paths or name in expected or kind != "blob"
                or mode not in {"100644", "100755"} or not _GIT_DIGEST.fullmatch(digest)
                or not 0 <= size <= MAX_FILE_BYTES):
            raise BuildBundleError()
        expected[name] = (digest, size, int(mode, 8) & 0o777)
    if set(expected) != set(paths) or sum(row[1] for row in expected.values()) > MAX_INPUT_BYTES:
        raise BuildBundleError("build_source_unavailable")
    with TemporaryDirectory(prefix="adore-build-export-") as temporary:
        archive_path = Path(temporary) / "inputs.tar"
        _git(runner, repo, "archive", "--format=tar", f"--output={archive_path}",
             revision, "--", *paths, timeout=30)
        if (not archive_path.is_file()
                or archive_path.stat().st_size > MAX_INPUT_BYTES + 1024 * 1024):
            raise BuildBundleError("build_source_unavailable")
        found = {}
        try:
            with tarfile.open(archive_path, "r:") as archive:
                for member in archive:
                    directory = member.name.rstrip("/") + "/"
                    if member.isdir() and any(name.startswith(directory) for name in paths):
                        continue
                    if not member.isfile() or member.name not in expected or member.name in found:
                        raise BuildBundleError()
                    digest, size, mode = expected[member.name]
                    if member.size != size:
                        raise BuildBundleError()
                    source = archive.extractfile(member)
                    if source is None:
                        raise BuildBundleError()
                    raw = source.read(MAX_FILE_BYTES + 1)
                    algorithm = sha1 if len(digest) == 40 else sha256
                    git_blob = b"blob " + str(size).encode("ascii") + b"\0" + raw
                    if (len(raw) != size
                            or algorithm(git_blob, usedforsecurity=False).hexdigest() != digest
                            or PRIVATE_KEY.search(raw)):
                        raise BuildBundleError()
                    found[member.name] = (raw, mode)
        except (OSError, tarfile.TarError) as exc:
            raise BuildBundleError("build_source_unavailable") from exc
    if set(found) != set(expected):
        raise BuildBundleError("build_source_unavailable")
    return found


def _unique_fields(pairs: list[tuple]) -> dict:
    """@brief Reject duplicate manifest fields rather than replacing a reviewed value."""
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise BuildBundleError()
    return fields


# PUBLIC API
def definition_parts(value: str) -> tuple[str, str] | None:
    """
    @brief Validate an optional reviewed manifest reference.
    @param[in] value Repository-relative JSON manifest followed by @full-commit.
    @return Manifest path and immutable revision, or None when not registered.
    @exception BuildBundleError For unsafe paths or mutable or malformed references.
    """
    if value == "":
        return None
    if not isinstance(value, str) or len(value) > 310:
        raise BuildBundleError()
    path, separator, revision = value.rpartition("@")
    if not separator or not _GIT_DIGEST.fullmatch(revision):
        raise BuildBundleError()
    if not path.endswith(".json"):
        raise BuildBundleError()
    return _path(path), revision


def read_git_recipe(config, *, runner: CommandRunner = run_command):
    """
    @brief Read exact declared Git blobs as an executor source definition.
    @param[in] config Saved image and immutable build-manifest reference.
    @param[in] runner Injectable bounded Git command reader.
    @return Validated in-memory recipe retaining source revision provenance.
    @exception BuildBundleError For missing, unsafe or transformed Git sources.
    """
    from adore.recipe_sources import Definition, Recipe, image_dependencies

    try:
        parts = definition_parts(config.container.build_definition)
        if parts is None:
            raise BuildBundleError("build_definition_unavailable")
        path, revision = parts
        repo = config.worktree.repo_path
        if not Path(repo).is_absolute():
            raise BuildBundleError("build_source_unavailable")
        root = _git(runner, repo, "rev-parse", "--show-toplevel").stdout.rstrip("\r\n")
        if not root or Path(root).resolve() != Path(repo).resolve():
            raise BuildBundleError("build_source_unavailable")
        commit = _git(runner, repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
        if commit.stdout.strip() != revision:
            raise BuildBundleError("build_source_unavailable")
        manifest_raw = _inputs(repo, revision, [path], runner)[path][0]
        if len(manifest_raw) > 65536:
            raise BuildBundleError()
        manifest = json.loads(manifest_raw.decode("utf-8"), object_pairs_hook=_unique_fields)
        if (not isinstance(manifest, dict)
                or set(manifest) != {"schema", "image", "dockerfile", "files"}
                or type(manifest["schema"]) is not int or manifest["schema"] != 1
                or not isinstance(manifest["files"], list)
                or not 1 <= len(manifest["files"]) <= MAX_FILES):
            raise BuildBundleError()
        dockerfile = _path(manifest["dockerfile"])
        files = [_path(name) for name in manifest["files"]]
        if (len(set(files)) != len(files) or len({name.casefold() for name in files}) != len(files)
                or dockerfile not in files
                or any(PurePosixPath(name) in PurePosixPath(other).parents
                       for name in files for other in files if name != other)):
            raise BuildBundleError()
        image = config.container.image
        if image != manifest["image"]:
            raise BuildBundleError()
        image_reference(image, tagged=True)
        inputs = _inputs(repo, revision, files, runner)
        definition = Definition(image, dockerfile, inputs)
        image_dependencies(definition)
        return Recipe(image, {image: definition}, source="git", revision=revision)
    except (BuildBundleError, RecipeError):
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise BuildBundleError() from exc



def export_build_bundle(config, raw: bytes, *, runner: CommandRunner = run_command,
                        home=None) -> bytes:
    """
    @brief Export saved configuration and a complete retained/Git/bundled image graph.
    @param[in] config Loaded current project configuration.
    @param[in] raw Exact standalone raw-export bytes.
    @param[in] runner Injectable bounded Git reader; never invokes a runtime.
    @param[in] home Trusted ADORE recipe catalog home.
    @return Portable source ZIP with Compose and every required local base definition.
    @exception BuildBundleError For unavailable container mode or invalid Git inputs.
    @exception RecipeError For unsafe, corrupt, cyclic or incomplete recipe sources.
    """
    from adore.executor_recipes import resolve_recipe
    from adore.recipe_sources import recipe_archive

    if config.execution.backend != "container":
        raise BuildBundleError("build_definition_unavailable")
    return recipe_archive(resolve_recipe(config, home=home, runner=runner), config_raw=raw)


# END OF FILE
