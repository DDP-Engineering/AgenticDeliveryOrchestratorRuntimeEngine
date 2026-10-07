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
@file    image_build.py
@brief   Project-owned Dockerfile artifacts and bounded image build evidence.
@details Stores explicit administrator input outside the checkout. Existing
         configuration, queue and runtime backends retain their authority.
"""

from __future__ import annotations

# IMPORTS
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
import time
from uuid import uuid4

from adore.branding import EXECUTOR_BASE_IMAGE
from adore.config import load_config
from adore.execution import ContainerBackend
from adore.isolation import ContainerManager, IsolationError, wsl_mount_path
from adore.local_process import native_context
from adore.repository_auth import RepositoryAuthError, load_connection
from adore.util import strict_json_loads
from adore.web.executor_settings import ExecutorSettingsError, credential_values

# CONSTANTS
MAX_SOURCE_BYTES = 65536
MAX_LOG_BYTES = 65536
MAX_OPERATIONS = 10
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_UUID = re.compile(r"[0-9a-f]{32}\Z")
_PHASES = frozenset(
    {
        "queued",
        "inspecting",
        "building",
        "verifying",
        "verified",
        "failed",
        "cancelled",
        "uncertain",
        "interrupted",
    }
)
_OP_KEYS = frozenset(
    {
        "schema",
        "project_id",
        "id",
        "draft",
        "config_revision",
        "runtime",
        "tag",
        "phase",
        "image_id",
        "base_id",
        "runtime_identity",
        "context_sha256",
        "resource",
        "error",
        "verified_checks",
        "host",
    }
)
_PROJECT_LABEL = "org.ddp.adore.project-id"
_OP_LABEL = "org.ddp.adore.image-operation"
_DRAFT_KEYS = frozenset(
    {
        "schema",
        "project_id",
        "dockerfile",
        "checks",
        "network",
        "timeout_seconds",
        "memory_mib",
        "revision",
    }
)
_CREDENTIAL = re.compile(
    r"(?i)(?:\b(?:[A-Z_]*(?:TOKEN|PASSWORD|SECRET|API_KEY|PRIVATE_KEY)[A-Z_]*)"
    r"\s*=\s*[^\s]+|https?://[^\s/@:]+:[^\s/@]+@|BEGIN [A-Z ]*PRIVATE KEY)"
)


# DATA MODELS / TYPEDEFINITIONS
class ImageBuildError(RuntimeError):
    """@brief Typed safe artifact/runtime error with a stable operator code."""

    def __init__(self, code: str) -> None:
        """@brief Retain a value-free error code.
        @param[in] code Stable safe error category.
        """
        self.code = code
        super().__init__(code)


# LOCAL HELPERS
def _fingerprint(value: dict) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _image_id(value: object) -> str:
    """@brief Canonicalize only strict equivalent OCI IDs from the shared backend."""
    if not isinstance(value, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", value):
        raise ImageBuildError("image_identity_invalid")
    return value if value.startswith("sha256:") else "sha256:" + value


def _text(value: object, maximum: int) -> str:
    """@brief Validate strict text before any persisted artifact write."""
    try:
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.encode("utf-8")) > maximum
            or any(ord(c) < 32 and c not in "\n\r\t" for c in value)
        ):
            raise ValueError
    except (ValueError, UnicodeError) as exc:
        raise ImageBuildError("image_source_invalid") from exc
    return value


def _validate_source(source: str, secrets: list[str]) -> None:
    """@brief Enforce minimal supported context, without a sandbox claim."""
    _text(source, MAX_SOURCE_BYTES)
    if (
        len(source.splitlines()) > 1024
        or _CREDENTIAL.search(source)
        or any(value and value in source for value in secrets)
    ):
        raise ImageBuildError("image_source_invalid")
    instructions = []
    continued = ""
    for raw in source.splitlines():
        line = raw.strip()
        if not continued and (not line or line.startswith("#")):
            if re.match(r"(?i)#\s*(?:syntax|escape)\s*=", line):
                raise ImageBuildError("image_context_unsupported")
            continue
        continued += line
        if continued.endswith("\\"):
            continued = continued[:-1] + " "
            continue
        match = re.fullmatch(r"([A-Za-z]+)\s+(.+)", continued)
        if not match:
            raise ImageBuildError("image_source_invalid")
        name, body = match[1].upper(), match[2]
        if name in {"COPY", "ADD", "ONBUILD", "ARG"} or "<<" in body:
            raise ImageBuildError("image_context_unsupported")
        if name == "RUN" and body.startswith("--"):
            raise ImageBuildError("image_context_unsupported")
        if name not in {
            "FROM",
            "RUN",
            "USER",
            "ENV",
            "LABEL",
            "WORKDIR",
            "EXPOSE",
            "CMD",
            "ENTRYPOINT",
            "HEALTHCHECK",
            "STOPSIGNAL",
            "SHELL",
        }:
            raise ImageBuildError("image_context_unsupported")
        instructions.append((name, body))
        continued = ""
    if continued or not instructions or instructions[0] != ("FROM", EXECUTOR_BASE_IMAGE):
        raise ImageBuildError("image_base_invalid")
    if sum(name == "FROM" for name, _ in instructions) != 1:
        raise ImageBuildError("image_context_unsupported")
    users = [body for name, body in instructions if name == "USER"]
    if not users or users[-1] != "adore":
        raise ImageBuildError("image_user_invalid")


def _validate_draft(value: object, project_id: str, secrets: list[str]) -> dict:
    """@brief Validate the complete closed persisted draft and checksum."""
    if (
        not isinstance(value, dict)
        or set(value) != _DRAFT_KEYS
        or type(value["schema"]) is not int
        or value["schema"] != 1
        or value["project_id"] != project_id
        or not isinstance(value["revision"], str)
        or not _HEX.fullmatch(value["revision"])
        or value["revision"]
        != _fingerprint({key: item for key, item in value.items() if key != "revision"})
    ):
        raise ImageBuildError("image_artifact_corrupt")
    _validate_source(value["dockerfile"], secrets)
    checks = value["checks"]
    if not isinstance(checks, list) or len(checks) > 32:
        raise ImageBuildError("image_checks_invalid")
    for check in checks:
        _text(check, 512)
        try:
            tokens = shlex.split(check)
            if (
                not tokens
                or any(mark in check for mark in (";", "|", "&", "\n", "\r", "`", "$", ">", "<"))
                or _CREDENTIAL.search(check)
                or any(secret and secret in check for secret in secrets)
            ):
                raise ValueError
        except ValueError as exc:
            raise ImageBuildError("image_checks_invalid") from exc
    if (
        not isinstance(value["network"], str)
        or value["network"] not in {"none", "default"}
        or type(value["timeout_seconds"]) is not int
        or not 30 <= value["timeout_seconds"] <= 1800
        or type(value["memory_mib"]) is not int
        or not 512 <= value["memory_mib"] <= 4096
    ):
        raise ImageBuildError("image_policy_invalid")
    return value


# PUBLIC API
def dockerfile_template() -> str:
    """@brief Supply the legal single-base non-root project tooling template.
    @return UTF-8 editable Dockerfile with an installed ADORE base.
    """
    return (
        "# Copyright (c) 2026 DDP Engineering\n"
        "# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n"
        "# Commercial use requires a separate commercial license.\n"
        "# See the LICENSE.txt file for full license details. "
        "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n\n"
        f"FROM {EXECUTOR_BASE_IMAGE}\n"
        "USER root\n"
        "# Add RUN commands to install your project's system tools here.\n"
        "# Library preparation belongs to the project's per-worktree recipe.\n"
        "USER adore\n"
    )


class ImageBuildStore:
    """@brief Closed, bounded, project-owned image definition/evidence storage."""

    def __init__(self, profile: Path, project_id: str, *, secrets=()) -> None:
        """@brief Select an already authorized profile directory.
        @param[in] profile Profile-owned directory, outside the project checkout.
        @param[in] project_id Immutable project UUID.
        @param[in] secrets Known credentials used only to reject/redact retention.
        @exception ImageBuildError Invalid identity or linked ownership.
        """
        if not isinstance(project_id, str) or not _UUID.fullmatch(project_id):
            raise ImageBuildError("image_project_invalid")
        self.profile, self.project_id = Path(profile).absolute(), project_id
        self.root = self.profile / "image-build"
        self.secrets = sorted({str(value) for value in secrets if value}, key=len, reverse=True)

    def owned_path(self, relative: str) -> Path:
        """@brief Resolve only unlinked paths beneath this profile artifact root.
        @param[in] relative Internal relative artifact name, never server input.
        @return Owned regular path; missing paths are allowed before writes.
        @exception ImageBuildError Links, traversal or non-regular file ownership.
        """
        parts = Path(relative).parts
        if Path(relative).is_absolute() or not parts or any(p in {".", ".."} for p in parts):
            raise ImageBuildError("image_storage_unsafe")
        path = self.root / relative
        for parent in [self.profile, self.root, *list(path.parents)[:-1], path]:
            junction = getattr(parent, "is_junction", lambda: False)
            try:
                reparse = getattr(parent.lstat(), "st_file_attributes", 0) & getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
                )
            except FileNotFoundError:
                reparse = 0
            except OSError as exc:
                raise ImageBuildError("image_storage_unsafe") from exc
            if parent.is_symlink() or junction() or reparse:
                raise ImageBuildError("image_storage_unsafe")
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ImageBuildError("image_storage_unsafe")
        if path.exists() and not (path.is_file() or path.is_dir()):
            raise ImageBuildError("image_storage_unsafe")
        return path

    def read_json(self, relative: str, *, maximum: int = 524288) -> dict | None:
        """@brief Read strict bounded JSON without guessing corrupt state away.
        @param[in] relative Owned record name.
        @param[in] maximum Maximum retained bytes.
        @return Decoded mapping, or None only for a missing record.
        @exception ImageBuildError Corrupt or unreadable persisted evidence.
        """
        path = self.owned_path(relative)
        if not path.exists():
            return None
        try:
            if not path.is_file() or path.stat().st_size > maximum:
                raise ValueError
            value = strict_json_loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (OSError, ValueError, UnicodeError) as exc:
            raise ImageBuildError("image_artifact_corrupt") from exc

    def write_json(self, relative: str, value: dict) -> None:
        """@brief Atomically write one bounded owned non-secret record.
        @param[in] relative Internal artifact name.
        @param[in] value Validated mapping.
        @exception ImageBuildError Unsafe storage or write failure.
        """
        path = self.owned_path(relative)
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        if len(raw) > 524288:
            raise ImageBuildError("image_artifact_too_large")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            descriptor, name = tempfile.mkstemp(prefix="record-", dir=path.parent)
            temporary = Path(name)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        except OSError as exc:
            raise ImageBuildError("image_storage_failed") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def read(self) -> dict | None:
        """@brief Read the current validated definition without runtime probes.
        @return Current draft or None when no definition exists.
        @exception ImageBuildError Corrupt/foreign/unsupported stored definition.
        """
        value = self.read_json("draft.json")
        try:
            return (
                _validate_draft(value, self.project_id, self.secrets) if value is not None else None
            )
        except (TypeError, ValueError, UnicodeError) as exc:
            raise ImageBuildError("image_artifact_corrupt") from exc

    def save(
        self,
        dockerfile: str,
        checks: list[str],
        *,
        revision: str,
        network: str = "none",
        timeout_seconds: int = 600,
        memory_mib: int = 1024,
    ) -> dict:
        """@brief Save an explicitly reviewed bounded definition after revision check.
        @param[in] dockerfile Administrator-authored UTF-8 Dockerfile.
        @param[in] checks Explicit project-image check commands.
        @param[in] revision Current definition revision; empty for first creation.
        @param[in] network Explicit build download mode, independent of run egress.
        @param[in] timeout_seconds Operation wall-clock bound.
        @param[in] memory_mib Per-build-step memory/swap limit in MiB.
        @return Complete versioned content-bound draft.
        @exception ImageBuildError Invalid/stale input or storage failure.
        """
        current = self.read()
        if revision != (current["revision"] if current else ""):
            raise ImageBuildError("image_draft_stale")
        value = {
            "schema": 1,
            "project_id": self.project_id,
            "dockerfile": dockerfile,
            "checks": checks,
            "network": network,
            "timeout_seconds": timeout_seconds,
            "memory_mib": memory_mib,
        }
        try:
            value["revision"] = _fingerprint(value)
        except (ValueError, TypeError, UnicodeError) as exc:
            raise ImageBuildError("image_source_invalid") from exc
        _validate_draft(value, self.project_id, self.secrets)
        self.write_json("draft.json", value)
        return value

    def export(self) -> dict:
        """@brief Export only the project's validated definition and bounded evidence.
        @return Safe source/check/policy snapshot; credentials are never included.
        @exception ImageBuildError Missing/corrupt definition.
        """
        value = self.read()
        if value is None:
            raise ImageBuildError("image_draft_missing")
        return value

    def operation(self, operation_id: str) -> dict:
        """@brief Read closed identity-bound operation evidence, failing on corruption.
        @param[in] operation_id Immutable owned operation UUID.
        @return Validated durable operation.
        @exception ImageBuildError Missing, foreign or malformed evidence.
        """
        if not isinstance(operation_id, str) or not _UUID.fullmatch(operation_id):
            raise ImageBuildError("image_operation_invalid")
        value = self.read_json(operation_id + "/record.json")
        try:
            if (
                value is None
                or set(value) != _OP_KEYS
                or type(value["schema"]) is not int
                or value["schema"] != 1
                or value["id"] != operation_id
                or value["project_id"] != self.project_id
                or value["tag"] != f"adore-built-{self.project_id}:{operation_id}"
                or value["phase"] not in _PHASES
                or not _HEX.fullmatch(value["config_revision"])
                or not isinstance(value["runtime"], str)
                or not isinstance(value["host"], dict)
                or set(value["host"]) != {"system", "account", "host", "machine", "home", "path"}
                or not all(isinstance(v, str) for v in value["host"].values())
                or not _HEX.fullmatch(value["host"]["host"])
                or not isinstance(value["verified_checks"], list)
                or not all(isinstance(c, str) for c in value["verified_checks"])
            ):
                raise ValueError
            _validate_draft(value["draft"], self.project_id, self.secrets)
            for field in ("image_id", "base_id"):
                if value[field] and not re.fullmatch(r"sha256:[0-9a-f]{64}", value[field]):
                    raise ValueError
            if value["context_sha256"] and not _HEX.fullmatch(value["context_sha256"]):
                raise ValueError
            if (
                not isinstance(value["runtime_identity"], str)
                or not isinstance(value["error"], str)
                or not re.fullmatch(r"[a-z_]*", value["error"])
            ):
                raise ValueError
            resource = value["resource"]
            if resource is not None and (
                not isinstance(resource, dict)
                or set(resource) != {"container_id", "image_id", "status"}
                or not _HEX.fullmatch(resource["container_id"])
                or _image_id(resource["image_id"]) != value["image_id"]
                or resource["status"] != "running"
            ):
                raise ValueError
            if value["phase"] == "verified" and (
                not all(
                    value[f] for f in ("image_id", "base_id", "runtime_identity", "context_sha256")
                )
                or resource is not None
                or value["error"]
            ):
                raise ValueError
            return value
        except (TypeError, ValueError, KeyError, UnicodeError) as exc:
            raise ImageBuildError("image_operation_corrupt") from exc

    def operations(self) -> list[dict]:
        """@brief List bounded retained records without replaying operations.
        @return Validated project records; corrupt ownership fails closed.
        """
        root = self.owned_path("operations")  # Parent ownership check only.
        if not root.parent.exists():
            return []
        children = list(root.parent.iterdir())
        if any(not p.is_dir() and p.name != "draft.json" for p in children):
            raise ImageBuildError("image_storage_unsafe")
        directories = [p for p in children if p.is_dir()]
        if len(directories) > MAX_OPERATIONS:
            raise ImageBuildError("image_retention_invalid")
        return [self.operation(p.name) for p in sorted(directories)]

    def cancel(self, operation_id: str) -> None:
        """@brief Persist cancellation separately from worker phase updates.
        @param[in] operation_id Current owned nonterminal operation.
        @exception ImageBuildError Terminal operations cannot be cancelled.
        """
        value = self.operation(operation_id)
        if value["phase"] not in {"queued", "inspecting", "building", "verifying"}:
            raise ImageBuildError("image_operation_terminal")
        self.write_json(
            operation_id + "/cancel.json",
            {"schema": 1, "project_id": self.project_id, "id": operation_id},
        )

    def cancelled(self, operation_id: str) -> bool:
        """@brief Check a closed durable cancellation signal.
        @return Whether the owned request is cancelled.
        """
        value = self.read_json(operation_id + "/cancel.json")
        if value is not None and value != {
            "schema": 1,
            "project_id": self.project_id,
            "id": operation_id,
        }:
            raise ImageBuildError("image_operation_corrupt")
        return value is not None

    def log(self, operation_id: str) -> str:
        """@brief Read only bounded, redacted project operation output.
        @return At most 64 KiB retained UTF-8 output.
        """
        self.operation(operation_id)
        path = self.owned_path(operation_id + "/log.txt")
        if not path.exists():
            return ""
        try:
            if not path.is_file() or path.stat().st_size > MAX_LOG_BYTES:
                raise ValueError
            return self.redact(path.read_text(encoding="utf-8"))
        except (ValueError, OSError, UnicodeError) as exc:
            raise ImageBuildError("image_log_corrupt") from exc

    def live_log(self, operation_id: str) -> str:
        """@brief Read redacted bounded native output while the build is running.
        @return At most 64 KiB combining retained history and current client output.
        @exception ImageBuildError Unsafe or oversized evidence fails closed.
        """
        value = self.operation(operation_id)
        text = self.log(operation_id)
        if value["phase"] in {"inspecting", "building", "verifying"}:
            for stream in ("stdout", "stderr"):
                path = self.owned_path(operation_id + "/" + stream + ".txt")
                try:
                    if path.exists():
                        if not path.is_file() or path.stat().st_size > MAX_LOG_BYTES:
                            raise ValueError
                        text += self.redact(path.read_bytes().decode("utf-8", errors="replace"))
                except (OSError, ValueError) as exc:
                    raise ImageBuildError("image_log_corrupt") from exc
        return self.redact(text.encode("utf-8")[-MAX_LOG_BYTES:].decode("utf-8", errors="ignore"))

    def redact(self, text: str) -> str:
        """@brief Redact known values and common runtime credential output.
        @param[in] text Untrusted runtime output.
        @return Redacted bounded text.
        """
        for secret in self.secrets:
            text = text.replace(secret, "[redacted]")
        text = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[redacted]", text)
        text = _CREDENTIAL.sub("[redacted]", text)
        return text.encode("utf-8", errors="replace")[:MAX_LOG_BYTES].decode(
            "utf-8", errors="ignore"
        )

    def append_log(self, operation_id: str, text: str) -> None:
        """@brief Retain a bounded redacted tail; credentials never persist.
        @param[in] operation_id Owned operation UUID.
        @param[in] text Runtime text to redact before storage.
        """
        path = self.owned_path(operation_id + "/log.txt")
        previous = self.log(operation_id)
        raw = self.redact(text)
        combined = (previous + raw).encode("utf-8")[-MAX_LOG_BYTES:]
        path.write_bytes(combined.decode("utf-8", errors="ignore").encode("utf-8"))


def controlled_environment(home: Path) -> dict[str, str]:
    """@brief Construct runtime-client environment without credentials/proxies.
    @param[in] home Isolated owned operation runtime home.
    @return Minimal OS environment and isolated runtime authentication paths.
    @exception ImageBuildError Credentialed/remote daemon overrides are unsupported.
    """
    endpoint = os.environ.get("DOCKER_HOST", "")
    if (
        endpoint
        and not endpoint.startswith(("unix:///", "npipe:////"))
        or os.environ.get("DOCKER_TLS_VERIFY")
        or os.environ.get("DOCKER_CONTEXT")
    ):
        raise ImageBuildError("image_runtime_environment_unsupported")
    home.mkdir(parents=True, exist_ok=True)
    env = {
        k: os.environ[k] for k in ("PATH", "SystemRoot", "WINDIR", "TEMP", "TMP") if k in os.environ
    }
    env.update(
        HOME=str(home),
        USERPROFILE=str(home),
        DOCKER_CONFIG=str(home),
        REGISTRY_AUTH_FILE=str(home / "auth.json"),
        DOCKER_BUILDKIT="0",
    )
    if os.name != "nt":
        env["XDG_DATA_HOME"] = str(Path(native_context()["home"]) / ".local" / "share")
        env["XDG_CONFIG_HOME"] = str(home)
        env["XDG_RUNTIME_DIR"] = "/run/user/" + str(os.geteuid())
    (home / "auth.json").write_text('{"auths": {}}', encoding="utf-8")
    if endpoint:
        env["DOCKER_HOST"] = endpoint
    return env


class ImageBuildService:
    """@brief Durable bounded project image pipeline; never applies configuration."""

    def __init__(self, profiles, *, runner=None) -> None:
        """@brief Inject the existing command-runner seam for offline proof.
        @param[in] profiles Authorized profile registry.
        @param[in] runner Optional runtime runner; production uses native ownership.
        """
        self.profiles, self.runner = profiles, runner

    def store(self, name: str) -> ImageBuildStore:
        """@brief Resolve immutable profile identity and known credential values.
        @return Authorized profile artifact store.
        """
        profile = self.profiles.load(name)
        secrets = [
            v
            for k, v in os.environ.items()
            if any(marker in k.upper() for marker in ("TOKEN", "PASSWORD", "SECRET", "API_KEY"))
        ]
        try:
            directory = self.profiles.profile_dir(name)
            secrets.extend(credential_values(directory))
            config_path = self.profiles.config_path(name)
            if config_path.exists():
                connection = load_connection(directory, load_config(config_path))
                if connection:
                    secrets.append(connection["token"])
        except (RepositoryAuthError, ExecutorSettingsError, ValueError, OSError) as exc:
            raise ImageBuildError("image_credentials_corrupt") from exc
        return ImageBuildStore(self.profiles.profile_dir(name), profile.project_id, secrets=secrets)

    def prepare(self, name: str, revision: str, config_revision: str) -> dict:
        """@brief Snapshot a current definition into one unique queued operation.
        @param[in] name Authorized profile name.
        @param[in] revision Current saved draft revision.
        @param[in] config_revision Current raw configuration checksum.
        @return Immutable queued build request, with no runtime effects.
        @exception ImageBuildError Stale, local or retention-limited request.
        """
        store = self.store(name)
        draft = store.export()
        path = self.profiles.config_path(name)
        config = load_config(path)
        if config.execution.backend != "container":
            raise ImageBuildError("image_local_unavailable")
        if (
            revision != draft["revision"]
            or config_revision != sha256(path.read_bytes()).hexdigest()
        ):
            raise ImageBuildError("image_revision_stale")
        self.runtime_argv(config.container.runtime)
        if len(store.operations()) >= MAX_OPERATIONS:
            raise ImageBuildError("image_retention_full")
        operation_id = uuid4().hex
        value = {
            "schema": 1,
            "project_id": store.project_id,
            "id": operation_id,
            "draft": draft,
            "config_revision": config_revision,
            "runtime": config.container.runtime,
            "tag": f"adore-built-{store.project_id}:{operation_id}",
            "phase": "queued",
            "image_id": "",
            "base_id": "",
            "runtime_identity": "",
            "context_sha256": "",
            "resource": None,
            "error": "",
            "verified_checks": [],
            "host": native_context(),
        }
        store.write_json(operation_id + "/record.json", value)
        return store.operation(operation_id)

    @staticmethod
    def runtime_argv(runtime: str) -> list[str]:
        """@brief Accept fixed Docker/Podman and supported WSL wrapper grammar.
        @return Parsed shell-free runtime prefix.
        @exception ImageBuildError Unsupported runtime options/wrappers.
        """
        try:
            argv = shlex.split(runtime)
            stem = Path(argv[0]).stem.lower()
            if len(argv) == 1 and stem in {"docker", "podman"}:
                return argv
            if (
                stem == "wsl"
                and len(argv) in {3, 5}
                and argv[-2] == "--"
                and argv[-1] in {"docker", "podman"}
                and (
                    len(argv) == 3
                    or argv[1] in {"-d", "--distribution"}
                    and re.fullmatch(r"[A-Za-z0-9._-]{1,80}", argv[2])
                )
            ):
                return argv
        except (ValueError, IndexError, TypeError):
            pass
        raise ImageBuildError("image_runtime_unsupported")

    def set_phase(self, name: str, operation_id: str, phase: str, **fields) -> dict:
        """@brief Persist one observed phase and bounded verified evidence.
        @param[in] name Profile name.
        @param[in] operation_id Owned UUID.
        @param[in] phase Observed pipeline phase.
        @return Updated validated operation.
        """
        store = self.store(name)
        value = store.operation(operation_id)
        value.update(fields, phase=phase)
        store.write_json(operation_id + "/record.json", value)
        return store.operation(operation_id)

    def _current(self, name: str, value: dict, *, applied_revision=None) -> None:
        store = self.store(name)
        if (
            store.export()["revision"] != value["draft"]["revision"]
            or sha256(self.profiles.config_path(name).read_bytes()).hexdigest()
            not in {value["config_revision"], applied_revision}
            or value["host"] != native_context()
        ):
            raise ImageBuildError("image_revision_stale")

    def _runner(self, store: ImageBuildStore, value: dict, *, cancel=True):
        if self.runner is not None:
            return self.runner
        from adore.web.image_build_runner import ImageBuildRunner

        return ImageBuildRunner(store, value, watch_cancel=cancel)

    def _commands(self, store: ImageBuildStore, value: dict, *, cancel=True):
        runner = self._runner(store, value, cancel=cancel)
        home = store.owned_path(value["id"] + "/runtime-home")
        env = controlled_environment(home)
        prefix = self.runtime_argv(value["runtime"])
        wsl = Path(prefix[0]).stem.lower() == "wsl"
        deadline = time.monotonic() + (value["draft"]["timeout_seconds"] if cancel else 30)
        linux_data = linux_runtime = ""
        if wsl and prefix[-1] == "podman":
            # Fixed identity queries preserve rootless storage without copying its auth.
            home_result = runner(
                [*prefix[:-1], "printenv", "HOME"],
                cwd=store.owned_path(value["id"]),
                timeout=min(30, max(0.001, deadline - time.monotonic())),
                env=env,
            )
            uid_result = runner(
                [*prefix[:-1], "id", "-u"],
                cwd=store.owned_path(value["id"]),
                timeout=min(30, max(0.001, deadline - time.monotonic())),
                env=env,
            )
            linux_home = home_result.stdout.strip()
            uid = uid_result.stdout.strip()
            if (
                not home_result.ok
                or not uid_result.ok
                or home_result.timed_out
                or uid_result.timed_out
                or not re.fullmatch(r"/[A-Za-z0-9_./-]+", linux_home)
                or ".." in Path(linux_home).parts
                or not re.fullmatch(r"[0-9]{1,10}", uid)
            ):
                raise ImageBuildError("image_runtime_environment_unsupported")
            linux_data, linux_runtime = linux_home + "/.local/share", "/run/user/" + uid
        calls = 0

        def command(argv, *, cwd=None, timeout=None, env=None):
            """@brief Enforce shared deadline/environment on backend commands."""
            nonlocal calls
            calls += 1
            if calls > 160 or time.monotonic() >= deadline:
                raise ImageBuildError("image_timeout_unconfirmed")
            if cancel and store.cancelled(value["id"]):
                raise ImageBuildError("image_cancel_unconfirmed")
            actual = list(argv)
            if wsl:
                linux_home = wsl_mount_path(home)
                # Clear inherited WSL credentials/proxies before invoking the runtime.
                linux_env = (
                    [f"XDG_DATA_HOME={linux_data}", f"XDG_RUNTIME_DIR={linux_runtime}"]
                    if linux_data
                    else []
                )
                actual = [
                    *prefix[:-1],
                    "env",
                    "-i",
                    "PATH=/usr/local/bin:/usr/bin:/bin",
                    f"HOME={linux_home}",
                    f"DOCKER_CONFIG={linux_home}",
                    f"REGISTRY_AUTH_FILE={linux_home}/auth.json",
                    f"XDG_CONFIG_HOME={linux_home}",
                    "DOCKER_BUILDKIT=0",
                    *linux_env,
                    prefix[-1],
                    *actual[len(prefix) :],
                ]
                if cwd is not None and "build" in actual:
                    actual[-1] = wsl_mount_path(Path(cwd))
                    actual[actual.index("--file") + 1] = wsl_mount_path(Path(cwd) / "Dockerfile")
            remaining = deadline - time.monotonic()
            limit = min(float(timeout or 30), remaining)
            result = runner(
                actual, cwd=cwd or store.owned_path(value["id"]), timeout=limit, env=controlled
            )
            if (
                not hasattr(result, "timed_out")
                or type(result.exit_code) is not int
                or type(result.timed_out) is not bool
                or not isinstance(result.stdout, str)
                or not isinstance(result.stderr, str)
                or len(result.stdout.encode("utf-8")) > MAX_LOG_BYTES
                or len(result.stderr.encode("utf-8")) > MAX_LOG_BYTES
            ):
                raise ImageBuildError("image_runtime_output_invalid")
            store.append_log(value["id"], result.stdout + result.stderr)
            if result.timed_out:
                raise ImageBuildError("image_timeout_unconfirmed")
            if cancel and store.cancelled(value["id"]):
                raise ImageBuildError("image_cancel_unconfirmed")
            return result

        controlled = env
        return prefix, command

    @staticmethod
    def _runtime_identity(prefix: list[str], command) -> str:
        result = command([*prefix, "info", "--format", "{{json .}}"], timeout=30)
        try:
            data = strict_json_loads(result.stdout)
            docker = Path(prefix[-1]).stem.lower() == "docker"
            if not result.ok or not isinstance(data, dict):
                raise ValueError
            if docker:
                if (
                    data.get("OSType") != "linux"
                    or not isinstance(data.get("ID"), str)
                    or not data["ID"]
                    or any(
                        data.get(k) is not True
                        for k in ("MemoryLimit", "CpuCfsQuota", "CpuCfsPeriod")
                    )
                ):
                    raise ValueError
                identity = data["ID"]
            else:
                host = data["host"]
                if (
                    host["os"] != "linux"
                    or host["cgroupVersion"] != "v2"
                    or not {"cpu", "memory"} <= set(host["cgroupControllers"])
                    or not isinstance(host["hostname"], str)
                    or not host["hostname"]
                ):
                    raise ValueError
                store = data["store"]
                if (
                    not isinstance(store, dict)
                    or not all(
                        isinstance(store.get(k), str)
                        and store[k].startswith("/")
                        and len(store[k]) <= 4096
                        for k in ("graphRoot", "runRoot")
                    )
                    or not isinstance(store.get("graphDriverName"), str)
                    or not re.fullmatch(r"[a-z0-9_-]{1,32}", store["graphDriverName"])
                ):
                    raise ValueError
                identity = _fingerprint(
                    {
                        "host": host["hostname"],
                        "store": {
                            key: store[key] for key in ("graphRoot", "runRoot", "graphDriverName")
                        },
                    }
                )
            if len(identity) > 256 or any(ord(c) < 32 for c in identity):
                raise ValueError
            return identity
        except (KeyError, TypeError, ValueError) as exc:
            raise ImageBuildError("image_runtime_capabilities_unsupported") from exc

    @staticmethod
    def _metadata(prefix, command, value) -> None:
        result = command([*prefix, "image", "inspect", value["image_id"]], timeout=30)
        try:
            data = strict_json_loads(result.stdout)
            if not result.ok or not isinstance(data, list) or len(data) != 1:
                raise ValueError
            item = data[0]
            labels = item["Config"]["Labels"]
            if (
                _image_id(item["Id"]) != value["image_id"]
                or item["Config"]["User"] != "adore"
                or labels[_PROJECT_LABEL] != value["project_id"]
                or labels[_OP_LABEL] != value["id"]
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError) as exc:
            raise ImageBuildError("image_verification_failed") from exc

    def _backend(self, value, command) -> ContainerBackend:
        return ContainerBackend(
            ContainerManager(
                value["runtime"], value["tag"], "", "", runner=command, pull_never=True
            )
        )

    def run(self, name: str, operation_id: str) -> dict:
        """@brief Execute exactly one queued build and verify owned image/tool identity.
        @param[in] name Authorized stopped profile.
        @param[in] operation_id Queued immutable operation UUID.
        @return Terminal verified/failed/cancelled/uncertain evidence.
        @exception ImageBuildError Nonqueued/corrupt evidence is never replayed.
        """
        store = self.store(name)
        value = store.operation(operation_id)
        if value["phase"] != "queued":
            raise ImageBuildError("image_operation_terminal")
        if store.cancelled(operation_id):
            return self.set_phase(name, operation_id, "cancelled", error="image_cancelled")
        backend = None
        context = store.owned_path(operation_id + "/context")
        resource_name = f"adore-image-check-{operation_id}"
        terminal, error = "failed", ""
        try:
            self._current(name, value)
            value = self.set_phase(name, operation_id, "inspecting")
            prefix, command = self._commands(store, value)
            backend = self._backend(value, command)
            runtime_id = self._runtime_identity(prefix, command)
            base_id = backend.image_identity(EXECUTOR_BASE_IMAGE)
            if not base_id.startswith("sha256:"):
                base_id = "sha256:" + base_id
            source = re.sub(
                r"(?m)^\s*FROM\s+[^\r\n]+",
                "FROM " + base_id,
                value["draft"]["dockerfile"],
                count=1,
                flags=re.IGNORECASE,
            )
            if "Copyright (c) 2026 DDP Engineering" not in source:
                source = dockerfile_template().partition("FROM ")[0] + source
            context.mkdir(parents=True, exist_ok=False)
            (context / "Dockerfile").write_bytes(source.encode("utf-8"))
            value = self.set_phase(
                name,
                operation_id,
                "building",
                base_id=base_id,
                runtime_identity=runtime_id,
                context_sha256=sha256(source.encode("utf-8")).hexdigest(),
            )
            draft = value["draft"]
            memory = str(draft["memory_mib"]) + "m"
            docker = Path(prefix[-1]).stem.lower() == "docker"
            build = [
                *prefix,
                "build",
                "--pull=false" if docker else "--pull=never",
                "--network",
                draft["network"],
                "--memory",
                memory,
                "--memory-swap",
                memory,
                "--cpu-period",
                "100000",
                "--cpu-quota",
                "100000",
                "--force-rm",
                "--label",
                _PROJECT_LABEL + "=" + store.project_id,
                "--label",
                _OP_LABEL + "=" + operation_id,
                "--tag",
                value["tag"],
                "--file",
                "Dockerfile",
                ".",
            ]
            if not docker:
                build[len(prefix) + 1 : len(prefix) + 1] = ["--http-proxy=false", "--jobs", "1"]
            result = command(build, cwd=context, timeout=draft["timeout_seconds"])
            if not result.ok:
                raise ImageBuildError("image_build_failed")
            image_id = backend.image_identity(value["tag"])
            if not image_id.startswith("sha256:"):
                image_id = "sha256:" + image_id
            value = self.set_phase(name, operation_id, "verifying", image_id=image_id)
            self._metadata(prefix, command, value)
            result = command(
                [
                    *prefix,
                    "run",
                    "--detach",
                    "--name",
                    resource_name,
                    "--label",
                    _PROJECT_LABEL + "=" + store.project_id,
                    "--label",
                    _OP_LABEL + "=" + operation_id,
                    "--network",
                    "none",
                    "--pull",
                    "never",
                    "--memory",
                    memory,
                    "--memory-swap",
                    memory,
                    "--cpus",
                    "1",
                    "--entrypoint",
                    "sleep",
                    image_id,
                    "infinity",
                ],
                timeout=30,
            )
            if not result.ok or not _HEX.fullmatch(result.stdout.strip()):
                raise ImageBuildError("image_resource_unconfirmed")
            # Persist create receipt before another command; inspect cannot grant ownership.
            receipt = {
                "container_id": result.stdout.strip(),
                "image_id": image_id,
                "status": "running",
            }
            value = self.set_phase(name, operation_id, "verifying", resource=receipt)
            observed = backend.resource_identity(resource_name)
            if (
                observed["container_id"] != receipt["container_id"]
                or _image_id(observed["image_id"]) != image_id
                or observed["status"] != "running"
            ):
                raise ImageBuildError("image_resource_unconfirmed")
            # Retain the backend's exact resource representation for its bound controls.
            receipt = observed
            value = self.set_phase(name, operation_id, "verifying", resource=receipt)
            target = backend.bind(resource_name, {}, receipt)
            config = load_config(self.profiles.config_path(name))
            checks = [config.executor.default + " --version", *draft["checks"]]
            for check in checks:
                if not target(shlex.split(check), timeout=30).ok:
                    raise ImageBuildError("image_tool_check_failed")
            self._current(name, value)
            if (
                self._runtime_identity(prefix, command) != runtime_id
                or _image_id(backend.image_identity(EXECUTOR_BASE_IMAGE)) != base_id
                or _image_id(backend.image_identity(value["tag"])) != image_id
            ):
                raise ImageBuildError("image_identity_changed")
            self._metadata(prefix, command, value)
            value = self.set_phase(name, operation_id, "verifying", verified_checks=checks)
            terminal = "verified"
        except (ImageBuildError, IsolationError, OSError, ValueError) as exc:
            error = exc.code if isinstance(exc, ImageBuildError) else "image_runtime_failed"
            if error in {
                "image_cancel_unconfirmed",
                "image_timeout_unconfirmed",
                "image_resource_unconfirmed",
                "image_process_control_unconfirmed",
            }:
                terminal = "uncertain"
        finally:
            value = store.operation(operation_id)
            try:
                if value["resource"] is not None and backend is not None:
                    # Cancellation must not prevent exact-identity resource cleanup.
                    _prefix, cleanup = self._commands(store, value, cancel=False)
                    if self._runtime_identity(_prefix, cleanup) != value["runtime_identity"]:
                        raise ImageBuildError("image_identity_changed")
                    self._backend(value, cleanup).remove(resource_name, expected=value["resource"])
                    value = self.set_phase(name, operation_id, "verifying", resource=None)
                if terminal != "uncertain" and context.exists():
                    store.owned_path(operation_id + "/context/Dockerfile").unlink()
                    context.rmdir()
            except (ImageBuildError, IsolationError, OSError, ValueError):
                terminal, error = "uncertain", "image_cleanup_unconfirmed"
        return self.set_phase(name, operation_id, terminal, error=error)

    def recover(self, name: str, operation_id: str) -> dict:
        """@brief Reconcile only owned native scope; never replay an interrupted build.
        @param[in] name Profile name.
        @param[in] operation_id Persisted in-flight operation.
        @return Interrupted or uncertain terminal evidence, ineligible for apply.
        """
        store = self.store(name)
        value = store.operation(operation_id)
        if value["phase"] not in {"queued", "inspecting", "building", "verifying"}:
            return value
        try:
            if self.runner is None:
                self._runner(store, value).recover()
            if value["resource"] is not None:
                prefix, command = self._commands(store, value, cancel=False)
                if self._runtime_identity(prefix, command) != value["runtime_identity"]:
                    raise ImageBuildError("image_identity_changed")
                self._backend(value, command).remove(
                    f"adore-image-check-{operation_id}", expected=value["resource"]
                )
            return self.set_phase(
                name, operation_id, "interrupted", resource=None, error="image_build_interrupted"
            )
        except (ImageBuildError, IsolationError, OSError, ValueError):
            return self.set_phase(
                name, operation_id, "uncertain", error="image_recovery_unconfirmed"
            )

    def review(self, name: str, operation_id: str, *, applied_revision=None) -> dict:
        """@brief Recheck current immutable verified evidence before stage/apply.
        @return Closed image binding for the existing configuration review.
        @exception ImageBuildError Stale or unverified result cannot be selected.
        """
        store = self.store(name)
        value = store.operation(operation_id)
        if value["phase"] != "verified":
            raise ImageBuildError("image_not_verified")
        self._current(name, value, applied_revision=applied_revision)
        config = load_config(self.profiles.config_path(name))
        if value["verified_checks"] != [
            config.executor.default + " --version",
            *value["draft"]["checks"],
        ]:
            raise ImageBuildError("image_operation_corrupt")
        prefix, command = self._commands(store, value)
        backend = self._backend(value, command)
        if (
            self._runtime_identity(prefix, command) != value["runtime_identity"]
            or _image_id(backend.image_identity(EXECUTOR_BASE_IMAGE)) != value["base_id"]
            or _image_id(backend.image_identity(value["tag"])) != value["image_id"]
        ):
            raise ImageBuildError("image_identity_changed")
        self._metadata(prefix, command, value)
        return {
            key: value[key]
            for key in (
                "id",
                "project_id",
                "config_revision",
                "runtime",
                "runtime_identity",
                "base_id",
                "image_id",
                "context_sha256",
                "verified_checks",
            )
        } | {"draft_revision": value["draft"]["revision"]}


# END OF FILE
