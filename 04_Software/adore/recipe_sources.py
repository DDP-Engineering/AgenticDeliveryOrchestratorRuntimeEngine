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
@file    recipe_sources.py
@brief   Validate and serialize bounded, portable executor build definitions.
@details Sources are bytes, never extracted or executed. Static Dockerfile checks
         establish declared contexts and image dependencies, not build success.
"""

# IMPORTS
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from io import BytesIO
import json
from pathlib import PurePosixPath
import re
import shlex
import stat
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo
import zlib

# CONSTANTS
MAX_FILES = 128
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 18 * 1024 * 1024
MAX_DEFINITIONS = 32
MAX_METADATA_BYTES = 65536
LEGAL_HEADER = (
    "# Copyright (c) 2026 DDP Engineering\n"
    "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
    "# Commercial use requires a separate commercial license.\n"
    "# See the LICENSE.txt file for full license details. "
    "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n"
)
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
_DEVICE = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", re.I)
_IMAGE_COMPONENT = r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*"
_IMAGE = re.compile(
    rf"(?:[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[0-9]+)?/)?"
    rf"{_IMAGE_COMPONENT}(?:/{_IMAGE_COMPONENT})*"
)
_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
_ARGUMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STAGE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}")
_PUBLIC_BASES = frozenset(
    {
        "alpine",
        "ubuntu",
        "debian",
        "busybox",
        "python",
        "node",
        "golang",
        "rust",
        "nginx",
        "httpd",
        "fedora",
        "centos",
        "rockylinux",
        "almalinux",
        "amazonlinux",
        "registry",
    }
)
_METADATA = frozenset({"recipe.json", "config.toml", "compose.yaml", "BUILD.txt"})
_OPCODES = frozenset(
    {
        "FROM",
        "ARG",
        "RUN",
        "COPY",
        "ADD",
        "ENV",
        "LABEL",
        "CMD",
        "ENTRYPOINT",
        "EXPOSE",
        "VOLUME",
        "USER",
        "WORKDIR",
        "ONBUILD",
        "STOPSIGNAL",
        "HEALTHCHECK",
        "SHELL",
        "MAINTAINER",
    }
)
_SECRET_NAME = re.compile(r"(?:token|password|secret|credential|api.?key)", re.I)


# DATA MODELS / TYPEDEFINITIONS
class RecipeError(ValueError):
    """@brief Safe typed refusal with optional missing images and operator recovery."""

    def __init__(self, code="recipe_invalid", *, missing=(), recovery=""):
        """@brief Retain closed metadata without including untrusted source contents."""
        super().__init__(code)
        self.code = code
        self.missing = tuple(missing)
        self.recovery = recovery


@dataclass(frozen=True)
class Definition:
    """@brief One image's Dockerfile, complete selected context and non-secret inputs."""

    image: str
    dockerfile: str
    files: dict[str, tuple[bytes, int]]
    build_args: dict[str, str] = field(default_factory=dict)
    external_images: tuple[str, ...] = ()
    target: str | None = None


@dataclass(frozen=True)
class Recipe:
    """@brief A selected image and its explicitly supplied image definitions."""

    image: str
    definitions: dict[str, Definition]
    source: str = "managed"
    revision: str | None = None


# LOCAL HELPERS
def source_path(value: object, *, max_length: int = 240) -> str:
    """@brief Require a portable regular-source path and exclude credential locations."""
    if not isinstance(value, str) or not 1 <= len(value) <= max_length:
        raise RecipeError()
    parts = value.split("/")
    if any(
        not re.fullmatch(r"[A-Za-z0-9_.-]+", part)
        or part in {".", ".."}
        or part.endswith(".")
        or _DEVICE.fullmatch(part)
        for part in parts
    ):
        raise RecipeError()
    for part in parts:
        name = part.lower()
        if (
            name
            in {
                ".git",
                ".ssh",
                ".aws",
                ".azure",
                ".config",
                ".docker",
                ".npmrc",
                ".pypirc",
                ".netrc",
                ".gitconfig",
                "auth.json",
                "credentials",
                "credentials.json",
                "id_rsa",
                "id_ed25519",
            }
            or name.startswith((".env", "credentials."))
            or name.endswith((".key", ".pem", ".p12", ".pfx", ".kdbx"))
        ):
            raise RecipeError()
    return value


def image_reference(value: object, *, tagged=False) -> str:
    """@brief Accept a bounded image reference; persisted outputs require an explicit tag."""
    if not isinstance(value, str) or not 1 <= len(value) <= 255:
        raise RecipeError()
    if "@" in value:
        name, separator, digest = value.partition("@sha256:")
        if tagged or not separator or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise RecipeError()
    else:
        last = value.rsplit("/", 1)[-1]
        if ":" in last:
            name, tag = value.rsplit(":", 1)
            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
                raise RecipeError()
        elif tagged:
            raise RecipeError()
        else:
            name = value
    if not _IMAGE.fullmatch(name):
        raise RecipeError()
    return value


def public_image(value: str) -> bool:
    """@brief Identify explicit registries and standard Docker Hub library prerequisites."""
    name = value.partition("@")[0]
    first = name.split("/", 1)[0]
    if "/" in name and ("." in first or ":" in first):
        host = first.rsplit(":", 1)[0] if ":" in first else first
        return host not in {"localhost", "127.0.0.1", "[::1]"}
    return name.split(":", 1)[0].removeprefix("docker.io/library/") in _PUBLIC_BASES


def canonical_image(value: str) -> str:
    """@brief Apply Docker's implicit latest tag without changing an explicit tag/digest."""
    image_reference(value)
    return value if "@" in value or ":" in value.rsplit("/", 1)[-1] else value + ":latest"


def _unique(pairs):
    """@brief Refuse duplicate JSON keys rather than selecting one definition."""
    value = dict(pairs)
    if len(value) != len(pairs):
        raise RecipeError()
    return value


def _json(raw):
    """@brief Parse bounded, duplicate-free current recipe metadata."""
    if len(raw) > MAX_METADATA_BYTES:
        raise RecipeError()
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)


def _expand(value, arguments):
    """@brief Resolve supported Dockerfile variables without guessing missing values."""

    def replace(match):
        """@brief Replace exactly one known argument."""
        key = match[1] or match[2]
        if key not in arguments or arguments[key] is None:
            raise RecipeError("recipe_dockerfile_unsupported")
        return arguments[key]

    result = _VARIABLE.sub(replace, value)
    if "$" in result:
        raise RecipeError("recipe_dockerfile_unsupported")
    return result


def _instructions(raw):
    """@brief Read the supported newline/backslash Dockerfile instruction syntax."""
    pending = ""
    for line in raw.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if re.match(r"#\s*escape\s*=\s*`", stripped, re.I):
                raise RecipeError("recipe_dockerfile_unsupported")
            continue
        pending += stripped[:-1] + " " if stripped.endswith("\\") else stripped
        if stripped.endswith("\\"):
            continue
        tokens = pending.split(None, 1)
        if len(tokens) != 2 or tokens[0].upper() not in _OPCODES:
            raise RecipeError("recipe_dockerfile_unsupported")
        instruction, argument = tokens
        yield instruction.upper(), argument.strip()
        pending = ""
    if pending:
        raise RecipeError("recipe_dockerfile_unsupported")


def _copy_operands(argument):
    """@brief Separate supported COPY/ADD flags from shell or JSON source operands."""
    origin = None
    while argument.startswith("--"):
        token, _, remainder = argument.partition(" ")
        flag, equals, value = token.partition("=")
        if flag in {"--from", "--chown", "--chmod", "--exclude", "--checksum"}:
            if not equals:
                value, _, remainder = remainder.partition(" ")
            if not value:
                raise RecipeError("recipe_dockerfile_unsupported")
            if flag == "--from":
                origin = value
        elif flag not in {"--link", "--parents", "--keep-git-dir"}:
            raise RecipeError("recipe_dockerfile_unsupported")
        argument = remainder.lstrip()
    if "<<" in argument:
        raise RecipeError("recipe_dockerfile_unsupported")
    operands = json.loads(argument) if argument.startswith("[") else shlex.split(argument)
    if (
        not isinstance(operands, list)
        or len(operands) < 2
        or any(not isinstance(value, str) or not value for value in operands)
    ):
        raise RecipeError("recipe_dockerfile_unsupported")
    return origin, operands[:-1]


# PUBLIC API
def image_dependencies(definition: Definition) -> tuple[str, ...]:
    """
    @brief Validate Dockerfile source references and return external-to-stage images.
    @param[in] definition Reviewed bytes and explicit non-secret build inputs.
    @return Stable unique image references, including local bases requiring recipes.
    @exception RecipeError For unsupported syntax, unresolved variables or missing files.
    """
    arguments = {}
    global_arguments = {}
    environment = {}
    stage_scopes = []
    stage_names = {}
    aliases = set()
    dependencies = []
    stages = 0
    current_alias = None

    def variables():
        """@brief Apply Docker's stage ENV precedence over declared ARG values."""
        return {**arguments, **environment}

    def context_source(operand, *, patterns=True):
        """@brief Require a declared local context source without reading host files."""
        name = _expand(operand, variables()).removeprefix("./").rstrip("/")
        if name == ".":
            return
        if name.startswith("/") or ".." in name.split("/"):
            raise RecipeError()
        if not any(
            path == name or path.startswith(name + "/") or patterns and fnmatchcase(path, name)
            for path in definition.files
        ):
            raise RecipeError("recipe_context_incomplete")

    def origin(value, *, new_stage=False):
        """@brief Record one image reference after excluding an existing stage."""
        value = _expand(value, global_arguments if new_stage else variables())
        if not new_stage and (
            value.lower() == current_alias or value.isdecimal() and int(value) == stages - 1
        ):
            raise RecipeError("recipe_dockerfile_unsupported")
        if value.lower() in aliases or value.isdecimal() and int(value) < stages:
            return
        if value == "scratch":
            return
        image_reference(value)
        if value not in dependencies:
            dependencies.append(value)

    try:
        for opcode, argument in _instructions(definition.files[definition.dockerfile][0]):
            if not stages and opcode not in {"ARG", "FROM"}:
                raise RecipeError("recipe_dockerfile_unsupported")
            if opcode == "ARG":
                name, equals, default = argument.partition("=")
                if not _ARGUMENT.fullmatch(name):
                    raise RecipeError("recipe_dockerfile_unsupported")
                if name in definition.build_args:
                    arguments[name] = definition.build_args[name]
                elif equals:
                    if _SECRET_NAME.search(name) and default.strip("\"'") and "$" not in default:
                        raise RecipeError()
                    values = shlex.split(default)
                    if len(values) > 1:
                        raise RecipeError("recipe_dockerfile_unsupported")
                    arguments[name] = _expand(values[0] if values else "", variables())
                elif name not in arguments and name in global_arguments:
                    arguments[name] = global_arguments[name]
                if not stages and name in arguments:
                    global_arguments[name] = arguments[name]
            elif opcode == "FROM":
                values = shlex.split(argument)
                if values and values[0].startswith("--platform="):
                    values.pop(0)
                if (
                    not values
                    or len(values) not in (1, 3)
                    or len(values) == 3
                    and values[1].upper() != "AS"
                ):
                    raise RecipeError("recipe_dockerfile_unsupported")
                origin(values[0], new_stage=True)
                if stages:
                    stage_scopes.append((dict(arguments), dict(environment)))
                parent = _expand(values[0], global_arguments).lower()
                parent_index = (
                    int(parent)
                    if parent.isdecimal() and int(parent) < stages
                    else stage_names.get(parent)
                )
                if parent_index is None:
                    arguments, environment = {}, {}
                else:
                    inherited_args, inherited_env = stage_scopes[parent_index]
                    arguments, environment = dict(inherited_args), dict(inherited_env)
                stages += 1
                current_alias = None
                if len(values) == 3:
                    alias = values[2].lower()
                    if not _STAGE.fullmatch(alias) or alias in aliases:
                        raise RecipeError("recipe_dockerfile_unsupported")
                    aliases.add(alias)
                    current_alias = alias
                    stage_names[alias] = stages - 1
            elif opcode == "ENV":
                values = shlex.split(argument)
                if not values:
                    raise RecipeError("recipe_dockerfile_unsupported")
                if "=" not in values[0]:
                    values = [values[0] + "=" + " ".join(values[1:])]
                updates = {}
                for assignment in values:
                    name, _, value = assignment.partition("=")
                    if (
                        _SECRET_NAME.search(name)
                        and value
                        and "$" not in value
                        and not name.upper().endswith(("_PATH", "_DIR", "_FILE"))
                    ):
                        raise RecipeError()
                    try:
                        updates[name] = _expand(value, variables())
                    except RecipeError:
                        # Base-image variables (such as PATH) are unknown until a
                        # build. Keep unrelated ENV valid, but refuse references
                        # that would require guessing their context input.
                        updates[name] = None
                environment.update(updates)
            elif opcode in {"COPY", "ADD"}:
                if not stages:
                    raise RecipeError("recipe_dockerfile_unsupported")
                source, operands = _copy_operands(argument)
                if source is not None:
                    origin(source)
                    continue
                for operand in operands:
                    operand = _expand(operand, variables())
                    if opcode == "ADD" and operand.startswith(
                        ("https://", "http://", "git://", "git@")
                    ):
                        continue
                    context_source(operand)
            elif opcode == "RUN":
                for mount in re.findall(r"(?:^|\s)--mount=([^\s]+)", argument):
                    options = {}
                    for option in mount.split(","):
                        key, _, value = option.partition("=")
                        if key in options:
                            raise RecipeError("recipe_dockerfile_unsupported")
                        options[key] = value
                    if "from" in options:
                        origin(options["from"])
                    elif options.get("type", "bind") == "bind":
                        if "source" in options and "src" in options:
                            raise RecipeError("recipe_dockerfile_unsupported")
                        context_source(
                            options.get("source", options.get("src", ".")), patterns=False
                        )
            elif opcode == "ONBUILD":
                raise RecipeError("recipe_dockerfile_unsupported")
        if not stages or definition.target is not None and definition.target.lower() not in aliases:
            raise RecipeError("recipe_dockerfile_unsupported")
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError("recipe_dockerfile_unsupported") from exc
    return tuple(dependencies)


def _definition(data, entries):
    """@brief Validate one current-format image definition against exact archive bytes."""
    required = {"image", "context", "dockerfile", "files"}
    if (
        not isinstance(data, dict)
        or not required <= set(data)
        or set(data) - required - {"build_args", "external_images", "target"}
    ):
        raise RecipeError()
    image = image_reference(data["image"], tagged=True)
    context = data["context"]
    prefix = "" if context == "." else source_path(context) + "/"
    dockerfile = source_path(data["dockerfile"])
    names = data["files"]
    if (
        not isinstance(names, list)
        or not 1 <= len(names) <= MAX_FILES
        or any(not isinstance(name, str) for name in names)
        or len(set(names)) != len(names)
        or len({name.casefold() for name in names}) != len(names)
    ):
        raise RecipeError()
    files = {source_path(name): entries[prefix + source_path(name)] for name in names}
    if dockerfile not in files:
        raise RecipeError()
    args = data.get("build_args", {})
    if (
        not isinstance(args, dict)
        or len(args) > 64
        or any(
            not _ARGUMENT.fullmatch(key)
            or not isinstance(value, str)
            or len(value) > 2048
            or any(ord(c) < 32 for c in value)
            or re.search(r"(?:token|password|secret|credential|api.?key)", key, re.I)
            for key, value in args.items()
        )
    ):
        raise RecipeError()
    external = data.get("external_images", [])
    if not isinstance(external, list) or len(external) > MAX_DEFINITIONS:
        raise RecipeError()
    external = tuple(image_reference(value) for value in external)
    target = data.get("target")
    if target is not None and (not isinstance(target, str) or not _STAGE.fullmatch(target)):
        raise RecipeError()
    definition = Definition(image, dockerfile, files, args, external, target)
    image_dependencies(definition)
    return definition, {prefix + name for name in files}


def parse_recipe(source: bytes, image: str | None) -> Recipe:
    """
    @brief Read a selected Dockerfile, context ZIP or complete exported recipe ZIP.
    @param[in] source Bounded untrusted source bytes.
    @param[in] image Output tag, or None to read a stored ZIP's declared root.
    @return Validated definitions; unresolved local bases are resolved separately.
    @exception RecipeError Before retention for invalid, unsafe or unsupported input.
    """
    if image is not None:
        image_reference(image, tagged=True)
    if not isinstance(source, bytes) or not 1 <= len(source) <= MAX_ARCHIVE_BYTES:
        raise RecipeError()
    try:
        entries = {}
        if source.startswith(b"PK"):
            with ZipFile(BytesIO(source)) as archive:
                if len(archive.infolist()) > MAX_FILES * 4:
                    raise RecipeError()
                seen = set()
                total = 0
                portable = any(item.filename == "recipe.json" for item in archive.infolist())
                for item in archive.infolist():
                    path = source_path(item.filename.rstrip("/"), max_length=512)
                    if path.casefold() in seen:
                        raise RecipeError()
                    seen.add(path.casefold())
                    kind = stat.S_IFMT(item.external_attr >> 16)
                    if item.is_dir():
                        if kind not in (0, stat.S_IFDIR):
                            raise RecipeError()
                        continue
                    metadata = portable and path in _METADATA
                    limit = (
                        (524288 if path == "config.toml" else MAX_METADATA_BYTES)
                        if metadata
                        else MAX_FILE_BYTES
                    )
                    if (
                        kind not in (0, stat.S_IFREG)
                        or item.flag_bits & 1
                        or item.compress_type not in (ZIP_STORED, ZIP_DEFLATED)
                        or item.external_attr >> 16 & 0o7000
                        or not 0 <= item.file_size <= limit
                    ):
                        raise RecipeError()
                    total += 0 if metadata else item.file_size
                    if total > MAX_INPUT_BYTES or len(entries) >= MAX_FILES + len(_METADATA):
                        raise RecipeError()
                    with archive.open(item) as member:
                        raw = member.read(limit + 1)
                    if len(raw) != item.file_size or PRIVATE_KEY.search(raw):
                        raise RecipeError()
                    entries[path] = (raw, item.external_attr >> 16 & 0o777 or 0o644)
        else:
            if len(source) > MAX_FILE_BYTES or PRIVATE_KEY.search(source):
                raise RecipeError()
            entries["Dockerfile"] = (source, 0o644)
        if any(
            PurePosixPath(name.casefold()) in PurePosixPath(other.casefold()).parents
            for name in entries
            for other in entries
            if name != other
        ):
            raise RecipeError()
        if "recipe.json" not in entries:
            if image is None:
                raise RecipeError()
            definition, _ = _definition(
                {
                    "image": image,
                    "context": ".",
                    "dockerfile": "Dockerfile",
                    "files": list(entries),
                },
                entries,
            )
            return Recipe(image, {image: definition})
        metadata = _json(entries["recipe.json"][0])
        if (
            not isinstance(metadata, dict)
            or set(metadata) != {"schema", "image", "definitions"}
            or type(metadata["schema"]) is not int
            or metadata["schema"] != 1
            or image is not None
            and metadata["image"] != image
            or not isinstance(metadata["definitions"], list)
            or not 1 <= len(metadata["definitions"]) <= MAX_DEFINITIONS
        ):
            raise RecipeError()
        image = image_reference(metadata["image"], tagged=True)
        definitions = {}
        declared = set()
        for data in metadata["definitions"]:
            definition, names = _definition(data, entries)
            if definition.image in definitions:
                raise RecipeError()
            definitions[definition.image] = definition
            declared.update(names)
        if image not in definitions or set(entries) - declared - _METADATA:
            raise RecipeError()
        if (
            len(declared) > MAX_FILES
            or sum(
                len(raw)
                for definition in definitions.values()
                for raw, _ in definition.files.values()
            )
            > MAX_INPUT_BYTES
        ):
            raise RecipeError()
        reached = set()
        visiting = set()

        def visit(name):
            """@brief Reject cyclic or unrelated embedded definitions before retention."""
            if name in visiting:
                raise RecipeError("recipe_cycle")
            if name in reached:
                return
            visiting.add(name)
            for reference in image_dependencies(definitions[name]):
                target = canonical_image(reference)
                if target in definitions:
                    visit(target)
            visiting.remove(name)
            reached.add(name)

        visit(image)
        if reached != set(definitions):
            raise RecipeError()
        return Recipe(image, definitions)
    except (
        BadZipFile,
        zlib.error,
        EOFError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        NotImplementedError,
    ) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError() from exc


def _locations(recipe):
    """@brief Assign non-colliding portable context and Compose service names."""
    others = sorted(set(recipe.definitions) - {recipe.image})
    return {
        recipe.image: ("context", "executor"),
        **{
            image: (f"bases/{index}/context", f"base_{index}") for index, image in enumerate(others)
        },
    }


def recipe_compose(recipe: Recipe) -> dict:
    """@brief Describe the exact source graph as explicit Compose build dependencies."""
    locations = _locations(recipe)
    services = {}
    for image, definition in recipe.definitions.items():
        context, name = locations[image]
        build = {"context": "./" + context, "dockerfile": definition.dockerfile}
        dependencies = {
            value: "service:" + locations[canonical_image(value)][1]
            for value in image_dependencies(definition)
            if canonical_image(value) in locations
        }
        if dependencies:
            build["additional_contexts"] = dependencies
        if definition.build_args:
            build["args"] = definition.build_args
        if definition.target:
            build["target"] = definition.target
        services[name] = {"image": image, "build": build}
    return {"services": services}


def recipe_archive(recipe: Recipe, *, config_raw: bytes | None = None) -> bytes:
    """
    @brief Package retained definitions or a complete source-only project export.
    @param[in] recipe Validated source graph; callers resolve local dependencies for export.
    @param[in] config_raw Exact saved project TOML when making a project export.
    @return Deterministic ZIP bytes retaining regular-file executable permissions.
    """
    locations = _locations(recipe)
    definitions = []
    output_files = {}
    for image, definition in sorted(recipe.definitions.items()):
        context, _ = locations[image]
        metadata = {
            "image": image,
            "context": context,
            "dockerfile": definition.dockerfile,
            "files": sorted(definition.files),
            "build_args": definition.build_args,
            "external_images": list(definition.external_images),
        }
        if definition.target:
            metadata["target"] = definition.target
        definitions.append(metadata)
        output_files.update(
            {context + "/" + name: contents for name, contents in definition.files.items()}
        )
    manifest = {"schema": 1, "image": recipe.image, "definitions": definitions}
    if (
        len(output_files) > MAX_FILES
        or sum(len(raw) for raw, _ in output_files.values()) > MAX_INPUT_BYTES
    ):
        raise RecipeError()
    output_files["recipe.json"] = (
        (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
        0o644,
    )
    if len(output_files["recipe.json"][0]) > MAX_METADATA_BYTES:
        raise RecipeError()
    if config_raw is not None:
        output_files["config.toml"] = (config_raw, 0o600)
        output_files["compose.yaml"] = (
            (LEGAL_HEADER + json.dumps(recipe_compose(recipe), indent=2) + "\n").encode(),
            0o644,
        )
        output_files["BUILD.txt"] = (
            (
                LEGAL_HEADER + "Review the source definitions before building.\n"
                "Requires Docker Engine with BuildKit and Compose v2.17+; access to public\n"
                "base images and package sources is needed. "
                "Supply registry authentication separately.\n"
                "Run: docker compose build\n"
                "Local base definitions are included and linked as build dependencies.\n"
                "Import this ZIP directly in ADORE after reviewing server paths.\n"
                "Agent-installed packages and running job/container contents "
                "are not part of this export.\n"
                + (f"Reviewed source commit: {recipe.revision}\n" if recipe.revision else "")
            ).encode(),
            0o644,
        )
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, (contents, mode) in sorted(output_files.items()):
            info = ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, contents)
    if len(buffer.getvalue()) > MAX_ARCHIVE_BYTES:
        raise RecipeError()
    return buffer.getvalue()


# END OF FILE
