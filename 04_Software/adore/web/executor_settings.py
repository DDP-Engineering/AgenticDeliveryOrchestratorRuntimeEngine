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
@file    executor_settings.py
@brief   Private provider credentials and durable model connectivity evidence.
@details Uses the existing profile .env contract; malformed stored inputs fail closed.
"""

# IMPORTS
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile

from adore.web.model_connection import REASONS as MODEL_TEST_REASONS

# CONSTANTS
PROVIDER_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
        "DASHSCOPE_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "MISTRAL_API_KEY",
        "XAI_API_KEY",
        "GROQ_API_KEY",
    }
)
# One closed reason set for probing and for persisted evidence.
REASONS = frozenset(MODEL_TEST_REASONS)
RESULT_KEYS = {"project_id", "revision", "checked_at", "executor", "model", "ready", "reason"}


# DATA MODELS / TYPEDEFINITIONS
class ExecutorSettingsError(ValueError):
    """@brief Stable value-free credential/evidence contract error."""


# HELPER FUNCTIONS


def _pairs(pairs):
    """@brief Reject duplicate JSON fields, including nested objects."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise ExecutorSettingsError("executor_evidence_corrupt")
        value[key] = item
    return value


def _private_bytes(path: Path, limit: int) -> bytes | None:
    """@brief Read a bounded regular record without following a profile symlink."""
    if path.is_symlink():
        raise ExecutorSettingsError("executor_credentials_corrupt")
    try:
        if not path.exists():
            return None
        if not path.is_file() or path.stat().st_size > limit:
            raise ExecutorSettingsError("executor_credentials_corrupt")
        return path.read_bytes()
    except OSError as exc:
        raise ExecutorSettingsError("executor_credentials_corrupt") from exc


def _environment(directory: Path) -> tuple[list[str], dict[str, str]]:
    """@brief Strictly validate the existing dotenv contract before editing any bytes."""
    raw = _private_bytes(directory / ".env", 65536)
    try:
        lines = [] if raw is None else raw.decode("utf-8").splitlines()
        values = {}
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            key = key.strip()
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in values:
                raise ValueError
            value = value.strip()
            if (
                any(ord(c) < 32 for c in value)
                or value[:1] in {'"', "'"}
                and (len(value) < 2 or value[-1] != value[0])
            ):
                raise ValueError
            values[key] = value.strip("\"'")
        return lines, values
    except (UnicodeError, ValueError) as exc:
        raise ExecutorSettingsError("executor_credentials_corrupt") from exc


def _atomic(path: Path, raw: bytes) -> None:
    """@brief Atomically replace a private record, retaining the original on failure."""
    fd, name = tempfile.mkstemp(prefix=".executor-", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temp.chmod(0o600)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


# PUBLIC API


def credential_view(directory: Path, config) -> dict:
    """@brief Return only configured API variable names and effective credential sources."""
    _, values = _environment(directory)
    return {
        "variables": [
            {
                "name": key,
                "source": "environment"
                if key in os.environ
                else "project"
                if values.get(key)
                else "missing",
            }
            for key in sorted(PROVIDER_KEYS.intersection(config.executor.env_keys))
        ]
    }


def update_credential(directory: Path, config, variable: str, token: str | None) -> None:
    """@brief Save/remove one approved project key without touching ambient or shared auth.
    @param[in] token None removes the selected key; a nonempty printable key saves it.
    @exception ExecutorSettingsError Unsafe input, ambient override or corrupt dotenv.
    """
    lines, _ = _environment(directory)
    if variable not in PROVIDER_KEYS or variable not in config.executor.env_keys:
        raise ExecutorSettingsError("executor_credential_invalid")
    if variable in os.environ:
        raise ExecutorSettingsError("executor_credential_external")
    if token is not None and (
        not isinstance(token, str)
        or not 1 <= len(token) <= 4096
        or any(ord(c) <= 32 or ord(c) >= 127 or c in "\"'" for c in token)
    ):
        raise ExecutorSettingsError("executor_credential_invalid")
    kept = [
        line
        for line in lines
        if line.strip().startswith("#") or line.partition("=")[0].strip() != variable
    ]
    if token is not None:
        kept.append(f"{variable}={token}")
    if not lines:
        kept = [
            "# Copyright (c) 2026 DDP Engineering",
            "# This software is licensed under the PolyForm Noncommercial License 1.0.0.",
            "# Commercial use requires a separate commercial license.",
            "# See the LICENSE.txt file for full license details.",
            "# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0",
            *kept,
        ]
    _atomic(directory / ".env", ("\n".join(kept) + "\n").encode("utf-8"))


def credential_binding(directory: Path, config) -> str:
    """@brief Bind evidence to effective allowlisted keys and known external auth files.
    @note The digest stays server-side. External auth is read only for change detection.
    """
    _, values = _environment(directory)
    effective = {
        key: os.environ[key] if key in os.environ else values.get(key, "")
        for key in config.executor.env_keys
    }
    paths = []
    if config.executor.stage_host_auth:
        relative = (
            ".codex/auth.json"
            if config.executor.default == "codex"
            else ".local/share/opencode/auth.json"
        )
        paths.append(Path.home() / relative)
    # Configured subscription mounts are trusted host configuration, never request paths.
    args = config.container.run_args
    for index, arg in enumerate(args):
        mount = (
            args[index + 1]
            if arg in ("-v", "--volume") and index + 1 < len(args)
            else arg.removeprefix("--volume=")
            if arg.startswith("--volume=")
            else ""
        )
        for target, files in (
            ("/home/adore/.pi/agent", ["auth.json", "models.json"]),
            ("/home/adore/.qwen", ["oauth_creds.json", "settings.json"]),
            ("/home/adore/.codex", ["auth.json"]),
            ("/home/adore/.local/share/opencode", ["auth.json"]),
        ):
            marker = ":" + target
            if marker in mount:
                root = Path(mount.split(marker)[0])
                suffix = mount.split(marker, 1)[1].split(":", 1)[0]
                if suffix in {"/" + name for name in files}:
                    paths.append(root)
                elif suffix == "":
                    paths.extend(root / name for name in files)
    try:
        for path in paths:
            if path.exists():
                if not path.is_file() or path.stat().st_size > 1048576:
                    raise ExecutorSettingsError("executor_credentials_corrupt")
                effective[str(path)] = sha256(path.read_bytes()).hexdigest()
            else:
                effective[str(path)] = "missing"
    except OSError as exc:
        raise ExecutorSettingsError("executor_credentials_corrupt") from exc
    return sha256(json.dumps(effective, sort_keys=True).encode("utf-8")).hexdigest()


def validate_model_result(value: dict, project_id: str) -> None:
    """@brief Validate exact public model evidence before persistence or staleness filtering."""
    try:
        if (
            not isinstance(value, dict)
            or set(value) != RESULT_KEYS
            or value["project_id"] != project_id
            or not re.fullmatch(r"[0-9a-f]{64}", value["revision"])
            or value["executor"] not in {"opencode", "pi", "codex", "qwen"}
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", value["model"])
            or type(value["ready"]) is not bool
            or value["reason"] not in REASONS
            or value["ready"] != (value["reason"] == "ready")
        ):
            raise ValueError
        stamp = datetime.fromisoformat(value["checked_at"])
        if stamp.utcoffset() != timedelta(0) or stamp > datetime.now(UTC) + timedelta(seconds=60):
            raise ValueError
    except (ValueError, TypeError, KeyError) as exc:
        raise ExecutorSettingsError("executor_evidence_corrupt") from exc


def model_evidence(directory: Path, config, project_id: str, revision: str) -> dict | None:
    """@brief Load current result; stale is absent, corrupt/foreign evidence fails closed."""
    raw = _private_bytes(directory / "model-connection.json", 16384)
    if raw is None:
        return None
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
        if not isinstance(value, dict) or set(value) != RESULT_KEYS | {"schema", "binding"}:
            raise ValueError
        if (
            type(value["schema"]) is not int
            or value["schema"] != 1
            or not re.fullmatch(r"[0-9a-f]{64}", value["binding"])
        ):
            raise ValueError
        result = {k: v for k, v in value.items() if k in RESULT_KEYS}
        validate_model_result(result, project_id)
        if (
            result["revision"] != revision
            or value["binding"] != credential_binding(directory, config)
            or result["executor"] != config.executor.default
            or result["model"] != config.executor.commands[config.executor.default].model
        ):
            return None
        return result
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ExecutorSettingsError("executor_evidence_corrupt") from exc


def save_model_evidence(directory: Path, result: dict, binding: str) -> None:
    """@brief Persist only validated closed evidence with a server-owned credential digest."""
    validate_model_result(result, result["project_id"])
    _atomic(
        directory / "model-connection.json",
        json.dumps({"schema": 1, "binding": binding, **result}).encode("utf-8"),
    )


# END OF FILE
