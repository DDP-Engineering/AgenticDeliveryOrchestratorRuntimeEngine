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
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import tarfile
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from adore.util import CommandResult, CommandRunner, run_command

# CONSTANTS
MAX_FILES = 128
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_INPUT_BYTES = 16 * 1024 * 1024
_GIT_DIGEST = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")
_WINDOWS_DEVICE = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", re.I)
_PRIVATE_KEY = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
_IMAGE_COMPONENT = r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*"
_IMAGE_NAME = re.compile(
    rf"(?:[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[0-9]+)?/)?"
    rf"{_IMAGE_COMPONENT}(?:/{_IMAGE_COMPONENT})*"
)
_GIT_SELECTION = {"GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_NAMESPACE",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"}
LEGAL_HEADER = (
    "# Copyright (c) 2026 DDP Engineering\n"
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "# Commercial use requires a separate commercial license.\n"
    "# See the LICENSE.txt file for full license details. "
    "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
)


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
    if not isinstance(value, str) or len(value) > 240:
        raise BuildBundleError()
    parts = value.split("/")
    if (not parts or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part)
                         or part.endswith(".") or _WINDOWS_DEVICE.fullmatch(part)
                         for part in parts)
            or any(part.lower() in {".git", ".ssh", ".aws", ".azure", ".config",
                                    ".docker", ".npmrc", ".pypirc", ".netrc", ".gitconfig",
                                    "auth.json", "credentials", "credentials.json",
                                    "id_rsa", "id_ed25519"}
                   or part.lower().startswith((".env", "credentials."))
                   or part.lower().endswith((".key", ".pem", ".p12", ".pfx", ".kdbx"))
                   for part in parts)):
        raise BuildBundleError()
    return value


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
                            or _PRIVATE_KEY.search(raw)):
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


def export_build_bundle(config, raw: bytes, *, runner: CommandRunner = run_command) -> bytes:
    """
    @brief Assemble exact saved TOML and declared Git inputs with Docker Compose.
    @param[in] config Loaded current project configuration.
    @param[in] raw Exact standalone raw-export bytes.
    @param[in] runner Injectable bounded Git runner; never calls Docker or a forge.
    @return In-memory portable ZIP archive with relative paths.
    @exception BuildBundleError For absent, unsafe, unavailable or changed build inputs.
    @note Operators review the Dockerfile, base images and build network prerequisites.
    """
    try:
        parts = definition_parts(config.container.build_definition)
        runtime = shlex.split(config.container.runtime)
        if (parts is None or config.execution.backend != "container"
                or not {"docker", "docker.exe"}.intersection(runtime)):
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
        name, colon, tag = image.rpartition(":")
        if (image != manifest["image"] or not colon or len(image) > 255
                or not _IMAGE_NAME.fullmatch(name)
                or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag)):
            raise BuildBundleError()
        inputs = _inputs(repo, revision, files, runner)
        compose = {"services": {"executor": {"image": image, "build": {
            "context": "./context", "dockerfile": dockerfile}}}}
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as output:
            output.writestr("config.toml", raw)
            output.writestr("compose.yaml", LEGAL_HEADER + json.dumps(compose, indent=2) + "\n")
            output.writestr("BUILD.txt", LEGAL_HEADER +
                "Review the declared Dockerfile before building.\n"
                "Prerequisites: Docker Engine, Docker Compose v2, access to base images\n"
                "and any package sources used by the Dockerfile. Configure registry\n"
                "authentication separately on the destination host.\n"
                "Run docker compose build from this extracted directory.\n"
                "This builds the configured image. Enroll config.toml separately after\n"
                "reviewing server-specific paths and account access.\n"
                f"Reviewed source commit: {revision}\n")
            for name, (contents, mode) in sorted(inputs.items()):
                info = ZipInfo("context/" + name)
                info.create_system = 3
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = ZIP_DEFLATED
                output.writestr(info, contents)
        return buffer.getvalue()
    except BuildBundleError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise BuildBundleError() from exc


# END OF FILE
