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
@file app.py
@brief Authenticated same-origin HTTP API and bundled ADORE dashboard.
@details Routes select an explicit profile, enforce project grants before
         reading runtime state, and keep financial data on administrator routes.
"""

# IMPORTS
from collections.abc import Callable
from contextlib import contextmanager
import csv
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from io import StringIO
import json
import logging
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile
from threading import Lock
from time import monotonic
import tomllib
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from adore import __version__, doctor, metrics
from adore.aegis import RUN_KINDS
from adore.cli import _NOT_SECRET_KEYS, _SECRET_KEY_RE, _is_secret_key, _newline, _set_toml_scalar
from adore.clone_cleanup import project_clone_decision
from adore.config import (
    SELINUX_RELABEL_MODES,
    branch_naming_preview,
    default_config,
    load_config,
    valid_reviewers,
    validate_config,
)
from adore.config_edit import ConfigEditLockedError, config_edit_lock
from adore.forge import ForgeError, ForgeResponseError
from adore.forge_labels import ensure_labels, project_labels
from adore.isolation import ContainerManager, IsolationError
from adore.portable_settings import (
    MAX_SOURCE_BYTES,
    PORTABLE_FIELDS,
    PortableSettingsError,
    export_settings,
    parse_settings,
)
from adore.preparation import (
    PreparationError,
    effective_probe_config,
    preview_plan,
    public_plan,
    validate_plan,
)
from adore.profiles import ProfileError, ProfileStore, validate_display_name, validate_profile_id
from adore.release_notes import ReleaseNotesError, load_release_notes
from adore.repository_auth import (
    RepositoryAuthError,
    connection_view,
    project_runner,
    save_connection,
    verify_connection,
)
from adore.selection import start_blocker, start_preparation
from adore.state import StateError, StateStore
from adore.util import CommandRunner, force_rmtree, run_command, strict_json_loads
from adore.web import analytics
from adore.web.endpoint_probe import probe_endpoint
from adore.web.executor_configuration import (
    LAUNCH_PRESETS,
    SUPPORTED_AGENTS,
    selection_value,
    set_selection,
    valid_selection,
)
from adore.web.executor_settings import (
    PROVIDER_KEYS,
    ExecutorSettingsError,
    credential_binding,
    credential_view,
    model_evidence,
    save_model_evidence,
    update_credential,
)
from adore.web.implementation_settings import COLLECTION_KEYS, set_collection, valid_collection
from adore.web.jobs import JobReadError, read_jobs, sort_jobs
from adore.web.model_connection import probe_model_connection
from adore.web.repository_source import (
    RepositorySourceError,
    branch_exists,
    default_branch,
    detect_kind,
    ls_remote,
    origin_matches,
    parse_repository_url,
    read_origin,
    suggest_id,
    tea_logins,
)
from adore.web.repository_source import (
    clone as clone_repository,
)
from adore.web.store import WebStore, WebStoreError
from adore.web.tickets import (
    PICKUP_PAUSED,
    RunReadError,
    TicketReadError,
    comment_view,
    existing_job,
    open_forge,
    read_ticket,
    remove_ready_label,
    ticket_view,
    unfinished_run,
)
from adore.wizard import ScriptedAsker, WizardError, WizardSetup, run_wizard

# CONSTANTS
_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_SETTING_KEY_RE = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")
# Configuration sections whose single values the web may edit.
_EDITABLE_SECTIONS = frozenset({
    "agent", "platform", "polling", "readiness", "executor",
    "container", "execution", "local", "worktree", "workflow", "recovery", "budgets",
    "delivery", "review", "reconcile", "metrics", "labels",
})
# Container presets; local profiles accept validated installed native argv.
_LAUNCH_PRESETS = LAUNCH_PRESETS

_STATIC = Path(__file__).with_name("static")
_COOKIE = "adore_session"
_STORE_ERROR_CODES = {
    "password must contain at least 8 characters": "password_too_short",
    "current password is incorrect": "current_password_incorrect",
    "username already exists": "username_exists",
    "invalid username": "invalid_username",
    "invalid role": "invalid_role",
    "user not found": "user_not_found",
    "project changed during the update": "project_changed",
    "cannot disable the last administrator": "last_administrator",
    "project not found": "project_not_found",
    "project does not exist": "project_not_found",
    "price version already exists or actor is invalid": "price_exists",
    "invalid price": "invalid_price",
    "invalid price identity": "invalid_price",
    "price exceeds limit": "invalid_price",
    "invalid effective date": "invalid_effective_date",
    "idempotency key belongs to another operation": "idempotency_conflict",
    "invalid operation": "invalid_operation",
}
_HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}
_HTTP_FALLBACK_CODE = "request_failed"
_PROFILE_ERROR_CODES = {
    "invalid_project_name": "invalid_project_name",
    "reserved_project_name": "invalid_project_name",
    "invalid_display_name": "invalid_request",
    "project_corrupt": "project_corrupt",
}
_SETUP_ERROR_CODES = {
    "project_creation_failed": "project_setup_invalid",
    "project_rollback_failed": "project_setup_invalid",
    "project_setup_unavailable": "project_setup_invalid",
    "state_root_already_owned": "project_import_conflict",
    "readiness_corrupt": "readiness_probe_failed",
    "readiness_store_failed": "readiness_probe_failed",
    "identity_update_failed": "project_corrupt",
}
_REQUEST_PARTS = ("body", "query", "path", "header", "cookie")
_LOW_STORAGE_BYTES = 1024**3
_TERMINAL_RUN_LIFECYCLES = ("done", "failed", "cancelled", "handed-off")
_DELETABLE_RUN_LIFECYCLES = (*_TERMINAL_RUN_LIFECYCLES, "handoff-pending")


# DATA MODELS / TYPEDEFINITIONS
class Credentials(BaseModel):
    """@brief Browser username/password input."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class ExecutorCredentialInput(BaseModel):
    """@brief Exact revision-bound private provider key request."""
    model_config = ConfigDict(extra="forbid", strict=True)
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    variable: str = Field(min_length=1, max_length=64)
    token: str | None = Field(default=None, max_length=4096)


class NewUser(Credentials):
    """@brief Administrator account creation input."""

    role: str = "developer"


class UserWithAccess(Credentials):
    """@brief Explicit reviewed account and immutable project grants."""

    model_config = ConfigDict(extra="forbid", strict=True)
    role: Literal["admin", "developer"]
    project_ids: list[str] = Field(max_length=1000)
    allow_no_projects: bool = False


class PasswordChange(BaseModel):
    """@brief Authenticated own-password change input."""

    current: str
    replacement: str


class PasswordReset(BaseModel):
    """@brief Administrator recovery password input."""

    replacement: str = Field(min_length=8, max_length=1024)


class RepositoryConnectionInput(BaseModel):
    """@brief Explicit memory-only browser credential request."""
    model_config = ConfigDict(extra="forbid", strict=True)
    server: str = Field(min_length=1, max_length=512)
    token: str = Field(min_length=1, max_length=4096, repr=False)
    allow_http: bool = False


class PreferenceInput(BaseModel):
    """@brief One or both account-scoped presentation preferences."""

    model_config = ConfigDict(extra="forbid")
    language: Literal["en", "fr", "de", "ro"] | None = None
    theme: Literal["light", "dark", "system"] | None = None


class Memberships(BaseModel):
    """@brief Replacement project assignments."""

    projects: list[str]


class AccessChange(BaseModel):
    """@brief Grant or remove one developer's access to one project."""

    granted: bool


class AuditPolicyInput(BaseModel):
    """@brief Administrator-configured independent audit retention bounds."""

    model_config = ConfigDict(extra="forbid", strict=True)
    retention_days: int | None = Field(default=None, ge=1, le=36500)
    max_bytes: int | None = Field(default=None, ge=1, le=1073741824)


class ProjectInput(BaseModel):
    """@brief Guided project setup input."""

    model_config = ConfigDict(extra="forbid")
    name: str
    display_name: str | None = None
    kind: str
    repo: str
    repo_path: str
    reviewers: str = ""
    executor_cli: str = "opencode"
    execution_backend: Literal["container", "local"] = "container"
    executor_command: str = ""
    local_account: str = "current"
    local_home: str = ""
    local_path: str = ""
    local_cgroup_root: str = ""
    model: str = ""
    runtime: str = "docker"
    image: str = ""
    target_branch: str = "main"
    auth_mode: str = "host-auth"
    description: str = ""
    login: str = ""
    env_keys: list[str] | None = None
    ready_label: str = Field(default="agent-ready", min_length=1, max_length=120)
    approval_label: str = Field(default="agent-approved", min_length=1, max_length=120)
    max_iterations: int = Field(default=12, ge=1, le=10000, strict=True)
    max_wall_clock_seconds: int = Field(default=5400, ge=1, le=31536000, strict=True)
    max_cost_usd: float = Field(default=5.0, ge=0, le=1000000, allow_inf_nan=False)
    max_files_touched: int = Field(default=120, ge=1, le=1000000, strict=True)
    clone_url: str = Field(default="", max_length=512)


class RepositorySourceInput(BaseModel):
    """@brief A repository address to read before enrollment."""

    model_config = ConfigDict(extra="forbid")
    url: str = Field(max_length=512)


class ReviewedProjectInput(ProjectInput):
    """@brief Exact reviewed draft revision for explicit probe or guarded creation."""

    revision: str = Field(pattern=r"^[0-9a-f]{64}$")


class TransferSourceInput(BaseModel):
    """@brief Exact portable bytes or an immutable source-project identity."""

    model_config = ConfigDict(extra="forbid", strict=True)
    method: Literal["file", "project"]
    file_text: str | None = Field(default=None, max_length=65536)
    source_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class TransferInput(TransferSourceInput):
    """@brief Source-bound fresh target answers and explicit reference reconfirmation."""

    target: ProjectInput
    source_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    references_confirmed: bool


class ReviewedTransferInput(TransferInput):
    """@brief Exact reviewed portable target candidate for probe or publication."""

    revision: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProfileIDInput(BaseModel):
    """@brief Administrator advisory ID availability input."""

    model_config = ConfigDict(extra="forbid")
    name: str


class DisplayIdentityInput(BaseModel):
    """@brief Human display identity only; operational IDs remain unchanged."""

    model_config = ConfigDict(extra="forbid")
    display_name: str


class ProjectImportInput(BaseModel):
    """@brief A browser-provided TOML document and its reviewed revision."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64)
    display_name: str | None = None
    description: str = Field(default="", max_length=500)
    config_text: str = Field(min_length=1, max_length=524288)
    revision: str = ""


class ConfigEdit(BaseModel):
    """@brief One validated scalar configuration edit."""

    key: str
    value: str
    revision: str
    model: str | None = None
    auth_env: str | None = None
    protocol: Literal["openai-chat-completions"] | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    ca_file: str | None = None


class BranchPreview(BaseModel):
    """@brief Closed no-write branch template/rule draft tied to a config revision."""

    model_config = ConfigDict(extra="forbid", strict=True)
    template: str = Field(max_length=512)
    rule: str = Field(max_length=512)
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")


class ConfigApply(BaseModel):
    """@brief Exact pending candidate the administrator reviewed."""

    candidate_revision: str = Field(min_length=64, max_length=64)
    base_revision: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class PriceInput(BaseModel):
    """@brief Dated USD-per-million-token estimate configuration."""

    executor: str
    model: str
    effective_from: str
    input_usd_per_million: str
    output_usd_per_million: str


class ProjectDeleteInput(BaseModel):
    """@brief Typed-name confirmation for deleting an archived project."""

    confirm_name: str = Field(min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)
    remove_clone: bool = False


class TicketStartInput(BaseModel):
    """@brief A ticket start request: idempotency key and an optional priority label."""

    idempotency_key: str = Field(min_length=8, max_length=128)
    priority: str = Field(default="", max_length=128)


class TicketStopInput(BaseModel):
    """@brief A ticket stop request including an idempotency key."""

    idempotency_key: str = Field(min_length=8, max_length=128)


class OperationInput(BaseModel):
    """@brief A job operation including an idempotency key."""

    ticket_iid: int | None = None
    run_id: str = ""
    idempotency_key: str = Field(min_length=8, max_length=128)


# HELPER FUNCTIONS
def _error(status: int, code: str, message: str | None = None) -> HTTPException:
    """
    @brief Build a client error with a stable code and optional diagnostic text.
    @param[in] status HTTP status code.
    @param[in] code Lowercase snake_case identifier the browser localizes.
    @param[in] message Optional English diagnostic shown after the localized text.
    @return Exception for FastAPI to render as {"detail": {...}}.
    """
    detail = {"code": code}
    if message:
        detail["message"] = message
    return HTTPException(status_code=status, detail=detail)


def _store_error(status: int, exc: Exception) -> HTTPException:
    """@brief Translate a store sentence into its stable code, keeping unknown text."""
    text = str(exc)
    if text == "audit row is corrupt":
        return _error(503, "web_store_corrupt")
    code = _STORE_ERROR_CODES.get(text)
    return _error(status, code) if code else _error(status, "request_rejected", text)


def _validation_message(exc: RequestValidationError) -> str:
    """@brief Summarize failing request fields without echoing submitted values."""
    reasons = []
    for item in exc.errors():
        location = [str(part) for part in item.get("loc", ())]
        if location and location[0] in _REQUEST_PARTS:
            location = location[1:]
        field = ".".join(location)
        reason = str(item.get("msg", "invalid value"))
        reasons.append(f"{field}: {reason}" if field else reason)
    return "; ".join(reasons)


def _profile_name(name: str) -> str:
    if not _PROFILE_RE.fullmatch(name) or name in (".", ".."):
        raise _error(404, "project_not_found")
    return name


def _finding(code: str, field: str, remediation: str) -> dict:
    """@brief Construct a stable actionable finding without external values."""
    return {"code": code, "field": field, "remediation": remediation}


def _contract_rejection(code: str, field: str, remediation: str) -> HTTPException:
    """@brief Keep localized HTTP codes while exposing an exact backend finding."""
    return HTTPException(status_code=409 if code == "state_root_already_owned" else 503,
                         detail={"code": _SETUP_ERROR_CODES[code], "message": remediation,
                                 "issues": [_finding(code, field, remediation)]})


def _identity_error(exc: ProfileError) -> HTTPException:
    """@brief Map identity rejection to a value-free public contract."""
    issue = _finding(exc.code, exc.field,
                     "Choose an available portable ID." if exc.field == "name" else
                     "Use 1-120 trimmed printable characters for the display name.")
    return HTTPException(status_code=503 if exc.code == "project_corrupt" else 400,
                         detail={"code": _PROFILE_ERROR_CODES.get(exc.code, "project_corrupt"),
                                 "issues": [issue], "message": issue["remediation"]})


def _config_from_bytes(raw: bytes):
    """@brief Parse the exact configuration snapshot, independent of later edits."""
    with tempfile.TemporaryDirectory(prefix="adore-config-snapshot-") as temporary:
        path = Path(temporary) / "config.toml"
        path.write_bytes(raw)
        return load_config(path)


def _config_findings(config) -> list[dict]:
    """@brief Return field-addressable structural issues without config values."""
    secrets_found = _secret_config_keys(config.raw)
    if secrets_found:
        return [_finding("secret_value", key,
                         "Use a supported environment reference; supply credentials outside setup.")
                for key in secrets_found]
    findings = []
    for message in validate_config(config):
        match = re.match(r"\[([a-z][a-z0-9_.-]*)\]\s+([a-z][a-z0-9_]*)", message)
        field = ".".join(match.groups()) if match else "config"
        findings.append(_finding("config_invalid", field,
                                 "Correct this setting using the configuration reference."))
    return findings


def _verification_view(profiles: ProfileStore, profile, revision: str | None) -> dict:
    """@brief Strictly load revision-bound evidence; absent and stale remain distinct."""
    path = profiles.profile_dir(profile.name) / "readiness.json"
    if not path.exists():
        return {"status": "unverified", "revision": None, "checked_at": None}
    try:
        if path.stat().st_size > 16384:
            raise ValueError("oversized readiness")
        value = json.loads(path.read_text(encoding="utf-8"))
        keys = {"schema", "project_id", "revision", "checked_at", "context", "checks",
                "model_probe"}
        if (not isinstance(value, dict) or set(value) != keys
                or type(value["schema"]) is not int or value["schema"] != 1
                or value["project_id"] != profile.project_id
                or not isinstance(value["revision"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", value["revision"])
                or value["context"] != "api-host"
                or not isinstance(value["checked_at"], str)):
            raise ValueError("invalid readiness identity")
        stamp = datetime.fromisoformat(value["checked_at"])
        if (stamp.tzinfo is None or stamp.utcoffset() != timedelta(0)
                or stamp > datetime.now(UTC) + timedelta(seconds=5)):
            raise ValueError("invalid readiness time")
        checks = value["checks"]
        check_keys = {"git", "forge_cli", "forge_auth", "container_runtime", "executor_cli",
                      "aegis_files", "model_endpoint"}
        if not isinstance(checks, dict) or set(checks) != check_keys:
            raise ValueError("invalid readiness checks")
        for key, result in checks.items():
            if type(result) is not bool and not (
                key == "container_runtime" and result is None
                or key == "model_endpoint" and result == "not-checked"
            ):
                raise ValueError("invalid readiness check value")
        probe = value["model_probe"]
        reasons = {"ready", "credential-missing", "tool-stream-incompatible",
                   "redirect-rejected", "http-error", "endpoint-unreachable-or-incompatible",
                   "probe-failed", "not-configured", "unsupported-executor", "invalid-endpoint",
                   "invalid-provider-config", "invalid-credential-reference", "image-missing",
                   "timeout", "runtime-error"}
        if (not isinstance(probe, dict) or set(probe) != {"context", "ready", "model", "reason"}
                or probe["context"] not in {"executor-container", "executor-local"}
                or type(probe["ready"]) is not bool
                or not isinstance(probe["model"], str) or len(probe["model"]) > 200
                or not isinstance(probe["reason"], str)
                or not (probe["reason"] in reasons
                        or re.fullmatch(r"http-[45]\d\d", probe["reason"]))
                or probe["model"] and not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", probe["model"])):
            raise ValueError("invalid readiness model evidence")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise _contract_rejection("readiness_corrupt", "readiness",
                              "Inspect the stored readiness record on the ADORE host.") from exc
    status = ("stale" if revision != value["revision"] else
              "failed" if any(result is False for result in checks.values()) else
              "partial" if checks["container_runtime"] is None else "verified")
    return {**{key: item for key, item in value.items() if key != "schema"}, "status": status}


def _setup_display(body: ProjectInput | ProjectImportInput) -> str:
    """@brief Distinguish omitted legacy-compatible input from explicit invalid null."""
    return validate_display_name(body.display_name if "display_name" in body.model_fields_set
                                 else body.name)


def _probe_setup(config, probe_runner: CommandRunner, env_file: Path | None = None) -> dict:
    """@brief Run bounded redacted prerequisites for an explicit config snapshot.

    @param[in] config Validated configuration snapshot.
    @param[in] probe_runner Injectable external command boundary.
    @param[in] env_file Existing approved provider values for native checks.
    @return Typed prerequisite checks and redacted model evidence.
    @exception HTTPException A prerequisite command fails to produce usable evidence.
    """
    deadline = monotonic() + 30

    def bounded_runner(argv, *, cwd=None, timeout=None, env=None):
        """@brief Keep a doctor subprocess below one request's probe bound."""
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("host readiness deadline")
        tea_auth = argv[:2] == ["tea", "whoami"]
        if tea_auth:
            argv = ["tea", "api", "-i", "--method", "GET"]
            if config.platform.login:
                argv += ["--login", config.platform.login]
            argv += ["user"]
        result = probe_runner(argv, cwd=cwd,
                            timeout=min(timeout if timeout is not None else 8,
                                        8, remaining),
                            env=env)
        if tea_auth:
            def unique_fields(pairs):
                """@brief Reject duplicate identity fields from the forge boundary."""
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError("duplicate identity field")
                    value[key] = item
                return value

            try:
                if len(result.stdout) > 1_000_000:
                    raise ValueError("oversized identity")
                identity = json.loads(result.stdout, object_pairs_hook=unique_fields)
                statuses = re.findall(r"HTTP/\S+\s+(\d{3})", result.stderr)
                valid = (result.ok and bool(statuses) and 200 <= int(statuses[-1]) < 300
                         and isinstance(identity, dict)
                         and isinstance(identity.get("login"), str)
                         and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identity["login"]))
            except (ValueError, TypeError):
                valid = False
            if not valid:
                result = replace(result, exit_code=1)
        return result

    try:
        config = effective_probe_config(config, runner=bounded_runner)
        git = doctor.detect_git(bounded_runner)
        forge = doctor.detect_platform_cli(config.platform.kind, bounded_runner)
        auth = doctor.auth_status(config.platform.kind, bounded_runner)
        runtimes = (doctor.detect_runtimes(bounded_runner)
                    if config.execution.backend == "container" else None)
    except (OSError, UnicodeError, TypeError, ValueError,
            KeyError, TimeoutError, PreparationError) as exc:
        raise _error(503, "readiness_probe_failed") from exc
    if config.execution.backend == "local":
        from adore.local_execution import local_probe

        executor = False
        try:
            with local_probe(config, env_file) as (backend, target, _, _):
                backend.verify_required_tools("probe", [], env=target.env)
                executor = target.auth_available()
        except (IsolationError, OSError, ValueError):
            pass
        aegis_root = Path(config.worktree.repo_path) / ".agentic"
        return {"checks": {"git": git.present and not git.detail,
                            "forge_cli": forge.present and not forge.detail,
                            "forge_auth": auth.authenticated,
                            "container_runtime": True, "executor_cli": executor,
                            "aegis_files": (aegis_root / "aegis.py").is_file()
                            and (aegis_root / "aegis.toml").is_file(),
                            "model_endpoint": "not-checked"},
                "model_probe": {"context": "executor-local", "ready": False,
                                "model": "", "reason": "not-configured"}}
    try:
        image_runtime = ContainerManager(
            config.container.runtime, config.container.image,
            config.container.uv_cache_volume, config.container.npm_cache_volume,
            bounded_runner, run_args=config.container.run_args, pull_never=True,
            egress=config.container.egress,
            selinux_relabel=config.container.selinux_relabel,
        )
        executor = bounded_runner([
            *image_runtime.runtime_argv, "run", "--rm", "--pull=never",
            "--network", "none", "--entrypoint", "python",
            config.container.image, "-c",
            "import shutil,sys; sys.exit(0 if shutil.which(sys.argv[1]) else 1)",
            config.executor.default,
        ], timeout=8).ok
    except (IsolationError, OSError, TimeoutError, ValueError):
        executor = False
    runtime_name = config.container.runtime.strip()
    runtime = (runtimes.docker if runtime_name == "docker" else
               runtimes.podman if runtime_name == "podman" else None)
    aegis_root = Path(config.worktree.repo_path) / ".agentic"
    checks = {
        "git": git.present and not git.detail,
        "forge_cli": forge.present and not forge.detail,
        "forge_auth": auth.authenticated,
        "container_runtime": (runtime.present and not runtime.detail
                              if runtime is not None else None),
        "executor_cli": executor,
        "aegis_files": ((aegis_root / "aegis.py").is_file()
                        and (aegis_root / "aegis.toml").is_file()),
        "model_endpoint": "not-checked",
    }
    try:
        model_probe = probe_endpoint(config, bounded_runner)
    except (IsolationError, OSError, TimeoutError, ValueError) as exc:
        model_probe = {"context": "executor-container", "ready": False,
                       "model": config.executor.commands.get(
                           config.executor.default).model if config.executor.default
                           in config.executor.commands else "",
                       "reason": ("timeout" if isinstance(exc, TimeoutError)
                                  else "runtime-error")}
    if model_probe["reason"] not in ("not-configured", "unsupported-executor"):
        checks["model_endpoint"] = model_probe["ready"]
    return {"checks": checks, "model_probe": model_probe}


def _prepare_project(profiles: ProfileStore, body: ProjectInput) -> tuple[dict, WizardSetup | None]:
    """@brief Validate explicit web answers without persistence or live probes."""
    try:
        available = profiles.id_availability(body.name)
        display = _setup_display(body)
    except ProfileError as exc:
        raise _identity_error(exc) from exc
    issues = [] if available else [
        _finding("project_exists", "name", "Choose another available ID.")]
    answers = body.model_dump(exclude={"name", "display_name", "env_keys", "revision", "clone_url"})
    answers["budgets_choice"] = "custom"
    if not answers["executor_command"]:
        answers.pop("executor_command")
    elif body.execution_backend != "local":
        issues.append(_finding("setup_field_invalid", "executor_command",
                               "Custom native argv is available only for local execution."))
    # Reviewers are optional: an empty list requests no review on the MR/PR.
    for field in ("ready_label", "approval_label", "kind", "repo", "repo_path",
                  "runtime", "target_branch", "auth_mode", "executor_cli"):
        if not str(answers[field]).strip():
            issues.append(_finding("setup_field_invalid", field,
                                   "Supply a non-empty supported value."))
    for field in ("model", "image"):
        if field == "image" and body.execution_backend == "local":
            continue
        if field in body.model_fields_set and not str(answers[field]).strip():
            issues.append(_finding("setup_field_invalid", field,
                                   "Supply an explicit supported value."))
    if body.execution_backend != "local":
        for field, key in (("image", "container.image"), ("runtime", "container.runtime")):
            if str(answers[field]).strip() and not _valid_environment_value(key, answers[field]):
                issues.append(_finding("setup_field_invalid", field,
                                       "Use an image name:tag or docker/podman (optionally "
                                       "wrapped by wsl ... --)."))
    pending_clone = False
    if body.clone_url:
        # From a repository URL: the clone (proposed at <home>/repos/<ID>, editable) is made at
        # creation. Inside ADORE home only the repos folder may hold it.
        home = profiles.home.resolve()
        expected = Path(body.repo_path)  # As typed: no ~ expansion, so preview and clone agree.
        try:
            source = parse_repository_url(body.clone_url)
        except RepositorySourceError:
            source = None
            issues.append(_finding(
                "repository_url_invalid", "clone_url",
                "Use an https, http or ssh repository address without credentials."))
        if source is not None and source.repo.casefold() != body.repo.strip().casefold():
            issues.append(_finding("setup_field_invalid", "repo",
                                   "Use the repository named by the repository URL."))
        located = expected.is_absolute() and (
            not expected.resolve().is_relative_to(home)
            or expected.resolve().is_relative_to(home / "repos")
            and expected.resolve() != home / "repos")
        if not located:
            issues.append(_finding(
                "setup_field_invalid", "repo_path",
                "Use an absolute clone folder outside ADORE home or under its repos folder."))
        elif not expected.resolve().is_relative_to(home) and not expected.parent.is_dir():
            issues.append(_finding("setup_field_invalid", "repo_path",
                                   "Choose a folder whose parent already exists."))
        elif _cloning_marker(expected).exists() and (
                _cloning_active(_cloning_marker(expected)) or expected.exists()):
            # A running clone, or the folder an interrupted one left behind: never reuse it.
            issues.append(_finding("clone_path_occupied", "repo_path",
                                   "A clone into this folder is running or was interrupted; "
                                   "remove the partial folder and its .adore-cloning marker."))
        elif expected.exists():
            if not (expected / ".git").exists() or not origin_matches(
                    read_origin(expected) or "", body.clone_url):
                issues.append(_finding("clone_path_occupied", "repo_path",
                                       "Move the existing folder away or use an existing clone."))
        else:
            pending_clone = True
    clone = Path(body.repo_path).expanduser()
    if not pending_clone and not any(issue["field"] == "repo_path" for issue in issues) and (
            not clone.is_absolute() or not (clone / ".git").exists()):
        issues.append(_finding("setup_field_invalid", "repo_path",
                               "Use an absolute existing repository clone on the ADORE server."))
    # An executor whose image or service signs in by itself needs no forwarded names.
    if body.env_keys is not None and (
            len(body.env_keys) > 32 or len(set(body.env_keys)) != len(body.env_keys)
            or any(not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", key) for key in body.env_keys)
            or body.auth_mode in {"host-auth", "existing"} and body.env_keys):
        issues.append(_finding("setup_field_invalid", "env_keys",
                               "Use unique uppercase environment names outside host-auth mode."))
    for key in ("model", "image"):
        if not answers[key]:
            del answers[key]
    answers["confirm"] = "yes"
    answers["worktree_root"] = str((profiles.home / "worktrees" / body.name).resolve())
    candidate = None
    if not issues:
        try:
            candidate = run_wizard(profiles, asker=ScriptedAsker(answers, interactive=False),
                                   name=body.name, out=lambda _message: None, prepare_only=True,
                                   pending_clone=pending_clone)
            if not isinstance(candidate, WizardSetup):
                raise WizardError("invalid setup candidate")
            candidate.metadata["display_name"] = display
            candidate.document = re.sub(
                r"(?m)^# Generated by .*?$",
                "# Generated by ADORE web guided enrollment.", candidate.document)
            if body.env_keys is not None:
                env_line = "env_keys = " + json.dumps(body.env_keys)
                if re.search(r"(?m)^env_keys = ", candidate.document):
                    candidate.document = re.sub(r"(?m)^env_keys = .*?$",
                                                env_line, candidate.document)
                else:
                    candidate.document = candidate.document.replace(
                        "[executor]\n", "[executor]\n" + env_line + "\n", 1)
            issues.extend(_config_findings(_config_from_bytes(candidate.document.encode("utf-8"))))
        except WizardError as exc:
            issues.append(_finding("setup_field_invalid", exc.field,
                                   "Supply a supported value for this setup field."))
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise _contract_rejection("project_setup_unavailable", "config",
                                  "Check local setup storage and configuration access.") from exc
    preview = {"name": body.name, "display_name": display, "structural_valid": not issues,
               "issues": issues, "pickup": "stopped-on-create",
               "verification": {"status": "unverified"}, "revision": None,
               "config_revision": None, "review": None, "defaults": []}
    if candidate is not None and not issues:
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        snapshot = {"document": candidate.document, "name": body.name,
                    "display_name": display, "description": body.description,
                    "clone_url": body.clone_url}
        preview["revision"] = sha256(json.dumps(snapshot, sort_keys=True,
                                               ensure_ascii=False).encode("utf-8")).hexdigest()
        preview["config_revision"] = sha256(candidate.document.encode("utf-8")).hexdigest()
        preview["defaults"] = _preview_defaults(candidate.document)
        preview["review"] = {
            **body.model_dump(exclude={"revision", "env_keys"}),
            "display_name": display,
            "model": config.executor.commands[config.executor.default].model,
            "executor_command": config.executor.commands[config.executor.default].command,
            "image": config.container.image, "env_keys": config.executor.env_keys,
            "hold_label": config.labels.control.hold,
            "exclude_label": config.labels.control.exclude,
            "egress_mode": config.container.egress.mode,
            "branch_template": config.worktree.branch_template,
            "config_path": str(profiles.config_path(body.name).resolve()),
            "store_root": config.state.store_root, "worktree_root": config.worktree.root,
            "clone": ("new" if pending_clone else "existing") if body.clone_url else None,
        }
        if config.execution.backend == "local":
            from adore.local_process import native_context

            context = native_context()
            preview["review"]["local_execution"] = {
                key: context[key] for key in ("machine", "account", "system")}
    return preview, candidate


def _preview_defaults(document: str) -> list[dict]:
    """
    @brief      Editable settings of a candidate that stay at ADORE's default.
    @param[in]  document Candidate configuration TOML (after every copied rule).
    @return     [{key, value}] shown read-only on Review and create.
    """
    try:
        effective = _redact_config(_config_from_bytes(document.encode("utf-8")).to_dict())
        effective.pop("raw", None)
        metadata = _setting_metadata(effective, document.encode("utf-8"))
    except (ValueError, TypeError, AttributeError, tomllib.TOMLDecodeError):
        return []  # an informational list never blocks the review
    listed = []
    for item in metadata:
        value = _value_at(effective, item["key"])
        if item["editable"] and item["default"] is not None and value == item["default"]:
            listed.append({"key": item["key"], "value": value})
    return listed


def _transfer_paths(profiles: ProfileStore, config, name: str, *, own_target: bool = False) -> None:
    """
    @brief      Reject occupied, aliased or overlapping fresh target ownership.
    @param[in]  profiles Authoritative profile/config store.
    @param[in]  config Validated target snapshot with allocated absolute paths.
    @param[in]  name Fresh target directory identity.
    @param[in]  own_target Publication already owns its new directory/state lock.
    @exception  HTTPException Ambiguous/corrupt ownership fails closed without values.
    """
    directory = profiles.profile_dir(name).absolute()
    trees = Path(config.worktree.root).absolute()
    clone = Path(config.worktree.repo_path).resolve()

    def overlaps(first: Path, second: Path) -> bool:
        return first == second or first.is_relative_to(second) or second.is_relative_to(first)

    def conflict() -> None:
        raise _error(409, "project_import_conflict")

    try:
        if (directory.resolve() != directory or trees.resolve() != trees
                or trees.exists() or not own_target and directory.exists()
                or overlaps(directory, trees) or overlaps(directory, clone)
                or overlaps(trees, clone)):
            conflict()
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        for other in profiles.list_profiles():
            if own_target and other.name == name:
                continue
            with profiles.config_path(other.name).open("rb") as source:
                raw = source.read(MAX_SOURCE_BYTES + 1)
            export_settings(raw)  # Strict full source contract before ownership extraction.
            owned = _config_from_bytes(raw)
            if Path(other.store_root or profiles.default_store_root(other.name)).resolve() != (
                    Path(owned.state.store_root).resolve()):
                raise _error(503, "project_corrupt")
            if (config.platform.kind == owned.platform.kind
                    and config.platform.repo.casefold() == owned.platform.repo.casefold()):
                conflict()
            locations = [profiles.profile_dir(other.name), Path(owned.state.store_root),
                         Path(owned.worktree.root), Path(owned.worktree.repo_path),
                         Path(owned.metrics.db_path), Path(owned.metrics.export_jsonl),
                         Path(owned.metrics.html_out)]
            if any(overlaps(target, location.resolve()) for target in (directory, trees, clone)
                   for location in locations):
                conflict()
    except (OSError, ProfileError, PortableSettingsError, ValueError, TypeError) as exc:
        raise _error(503, "project_corrupt") from exc


def _prepare_transfer(profiles: ProfileStore, body: TransferInput,
                      settings: dict) -> tuple[dict, WizardSetup | None]:
    """
    @brief      Project complete portable rules onto an independently prepared target.
    @param[in]  profiles Target host profile store.
    @param[in]  body Explicit new target answers and reconfirmation.
    @param[in]  settings Complete strict parser output.
    @return     Canonical mapping/review and exact validated candidate or findings.
    @exception  HTTPException Invalid/ambiguous storage or ownership fails closed.
    """
    # Guided limits need not constrain the already validated portable numeric domain.
    # Prepare target nonportable fields with defaults, then project all portable fields.
    answers = body.target.model_copy(update={
        "max_iterations": 12, "max_wall_clock_seconds": 5400,
        "max_cost_usd": 5.0, "max_files_touched": 120,
    })
    preview, candidate = _prepare_project(profiles, answers)
    preview["source_revision"] = body.source_revision
    defaults = default_config().to_dict()
    preview["mapping"] = [{"key": f"{section}.{key}", "source_value": settings[section][key],
                           "server_value": defaults[section][key], "effect": "copy-rule"}
                          for section, keys in PORTABLE_FIELDS.items() for key in keys]
    if not body.references_confirmed:
        preview["issues"].append(_finding("setup_field_invalid", "references_confirmed",
                                         "Reconfirm target environment and connection setup."))
    if candidate is not None and not preview["issues"]:
        document = candidate.document
        for section, keys in PORTABLE_FIELDS.items():
            document = re.sub(r"(?ms)^\[" + section + r"\]\s*\n.*?(?=^\[|\Z)", "", document)
            document += "\n[" + section + "]\n" + "\n".join(
                key + " = " + json.dumps(settings[section][key]) for key in keys) + "\n"
        config = _config_from_bytes(document.encode("utf-8"))
        preview["issues"].extend(_config_findings(config))
        preview["defaults"] = []  # only a valid clone gets its (recomputed) defaults list
        if not preview["issues"]:
            _transfer_paths(profiles, config, body.target.name)
            candidate.document = document
            # The copied rules are no longer defaults.
            preview["defaults"] = _preview_defaults(document)
            preview["config_revision"] = sha256(document.encode("utf-8")).hexdigest()
            preview["revision"] = sha256(json.dumps({
                "config_revision": preview["config_revision"],
                "source_revision": body.source_revision,
                "name": body.target.name, "display_name": preview["display_name"],
                "description": body.target.description,
            }, sort_keys=True).encode()).hexdigest()
            preview["review"].update(settings["budgets"])
            preview["review"].update({"metrics_db": config.metrics.db_path,
                                      "metrics_jsonl": config.metrics.export_jsonl,
                                      "metrics_html": config.metrics.html_out})
    preview["structural_valid"] = not preview["issues"]
    if preview["issues"]:
        preview.update(revision=None, config_revision=None, review=None)
        candidate = None
    return preview, candidate


def _cloning_marker(dest: Path) -> Path:
    """@brief Sibling marker that keeps a clone in progress from looking reusable."""
    return dest.parent / f".{dest.name}.adore-cloning"


_STALE_CLONING_SECONDS = 15 * 60  # Longer than a clone may run; left behind by a restart.


def _cloning_active(marker: Path) -> bool:
    """@brief True for a marker younger than the clone bound (an older one outlived its request)."""
    try:
        age = datetime.now(UTC).timestamp() - marker.stat().st_mtime
        return -60 <= age < _STALE_CLONING_SECONDS  # A future time is stale too (clock moved).
    except OSError:
        return False


def _pending_clone(body: ProjectInput) -> bool:
    """@brief True when an enrollment from a repository URL still has to make its clone."""
    return bool(body.clone_url) and not Path(body.repo_path).exists()


def _clone_rejection(status: int, code: str, field: str, remediation: str) -> HTTPException:
    """@brief A coded clone failure with one field finding."""
    return HTTPException(status_code=status, detail={
        "code": code, "message": remediation, "issues": [_finding(code, field, remediation)]})


def _materialize_clone(body: ProjectInput, runner: CommandRunner, home: Path) -> Path | None:
    """
    @brief      Make a pending clone just before publication and verify it.
    @param[in]  body Reviewed answers whose clone location was validated by preview.
    @param[in]  runner Injectable command boundary.
    @param[in]  home ADORE home; parent folders are created only under its repos folder.
    @return     The fresh clone (the caller removes it if publication fails), or None.
    @exception  HTTPException The clone failed, lacks AEGIS or lacks the target branch (removed).
    """
    if not _pending_clone(body):
        return None
    dest = Path(body.repo_path)
    if dest.resolve().is_relative_to(home.resolve() / "repos"):
        dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        # An exclusive empty folder: a concurrent enrollment can never have its clone removed here.
        dest.mkdir()
    except FileExistsError as exc:
        raise _clone_rejection(409, "clone_path_occupied", "repo_path",
                               "Another enrollment is using this clone location.") from exc
    except OSError as exc:
        raise _clone_rejection(409, "setup_field_invalid", "repo_path",
                               "The server could not create the clone folder (permissions or "
                               "disk space).") from exc
    if not clone_repository(body.clone_url, dest, runner).ok:
        force_rmtree(dest)
        raise _clone_rejection(502, "repository_clone_failed", "clone_url",
                               "Check that the server account can read the repository.")
    aegis = dest / ".agentic"
    try:
        if not ((aegis / "aegis.py").is_file() and (aegis / "aegis.toml").is_file()):
            raise _clone_rejection(409, "repository_aegis_missing", "clone_url",
                                   "Install AEGIS in the repository before enrolling it.")
        if not branch_exists(dest, body.target_branch, runner):
            raise _clone_rejection(409, "repository_branch_missing", "target_branch",
                                   "Choose a branch that exists in the repository.")
    except HTTPException:
        force_rmtree(dest)
        raise
    return dest


def _publish_with_clone(body: ProjectInput, runner: CommandRunner, home: Path,
                        publish: Callable[[], dict]) -> dict:
    """@brief Clone a pending repository, publish, and remove a fresh clone if publication fails."""
    if not _pending_clone(body):
        return publish()
    marker = _cloning_marker(Path(body.repo_path))
    if Path(body.repo_path).resolve().is_relative_to(home.resolve() / "repos"):
        marker.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        try:
            marker.touch(exist_ok=False)
            break
        except FileExistsError as exc:
            if attempt == 1 and not _cloning_active(marker):
                try:
                    marker.unlink(missing_ok=True)  # Left behind by an interrupted request.
                    continue
                except OSError:
                    pass
            raise _clone_rejection(
                409, "clone_path_occupied", "repo_path",
                f"Another enrollment is cloning into this folder ({marker.name}).") from exc
        except OSError as exc:
            raise _clone_rejection(409, "setup_field_invalid", "repo_path",
                                   "The server could not prepare the clone folder; check that its "
                                   "parent exists and is writable.") from exc
    try:
        fresh = _materialize_clone(body, runner, home)
        try:
            return publish()
        except BaseException:
            if fresh is not None:
                force_rmtree(fresh)
            raise
    finally:
        marker.unlink(missing_ok=True)


def _publish_paused(profiles: ProfileStore, web: WebStore, actor: int, name: str,
                    raw: bytes, metadata: dict, *, imported: bool = False,
                    import_body: ProjectImportInput | None = None,
                    recheck: Callable[[], None] | None = None,
                    origin: str | None = None,
                    base_revision: str | None = None) -> dict:
    """@brief Keep lock, filesystem and parsing failures typed at the enrollment boundary."""
    try:
        return _publish_paused_locked(profiles, web, actor, name, raw, metadata,
                                      imported=imported, import_body=import_body,
                                      recheck=recheck, origin=origin, base_revision=base_revision)
    except (OSError, StateError, ProfileError, UnicodeError, ValueError, TypeError) as exc:
        raise _contract_rejection("project_creation_failed", "config",
                              "Check local enrollment storage before retrying.") from exc


def _publish_paused_locked(
    profiles: ProfileStore,
    web: WebStore,
    actor: int,
    name: str,
    raw: bytes,
    metadata: dict,
    *,
    imported: bool = False,
    import_body: ProjectImportInput | None = None,
    recheck: Callable[[], None] | None = None,
    origin: str | None = None,
    base_revision: str | None = None,
) -> dict:
    """@brief Publish metadata after pause, holding ownership and conductor locks."""
    with _web_config_edit_lock(profiles.home / "web-enrollment" / "config.toml"):
        try:
            if not profiles.id_availability(name):
                raise _error(409, "project_exists")
        except ProfileError as exc:
            raise _identity_error(exc) from exc
        config = _config_from_bytes(raw)
        root = Path(config.state.store_root).resolve()
        for other in profiles.list_profiles():
            other_root = Path(other.store_root or profiles.default_store_root(other.name)).resolve()
            if (
                root == other_root
                or root.is_relative_to(other_root)
                or other_root.is_relative_to(root)
            ):
                raise _contract_rejection(
                    "state_root_already_owned",
                    "state.store_root",
                    "Choose an absolute state root owned only by this project.",
                )
        if import_body is not None:
            _reviewed_import(profiles, import_body)
        if recheck is not None:
            recheck()
        attempt = web.begin_change(
            actor,
            origin or ("project-imported" if imported else "project-created"),
            resource_type="project",
            resource_id=name,
            candidate_revision=sha256(raw).hexdigest(),
            base_revision=base_revision,
            before={"exists": False},
        )
        directory = profiles.profile_dir(name)
        try:
            directory.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise _error(409, "project_exists") from exc
        state = StateStore(root, config.agent.slug)
        locked, previously_paused = False, False
        try:
            locked = state.acquire_lock()
            if not locked:
                raise _error(409, "project_has_active_work")
            previously_paused = state.is_paused()
            if state.invalid_runs() or any(
                run.lifecycle not in _TERMINAL_RUN_LIFECYCLES for run in state.list_runs()
            ):
                raise _error(409, "project_has_active_work")
            if import_body is not None:
                _reviewed_import(profiles, import_body, own_state_lock=True)
            if recheck is not None:
                recheck()
            profiles.config_path(name).write_bytes(raw)
            state.pause()
            item = profiles.create(name, **metadata)
            if recheck is not None:
                recheck()
            result = _profile_view(profiles, item)
            web.audit(
                actor,
                "project-imported" if imported else "project-created",
                name,
                confirmation_key=attempt,
                after={"exists": True, "pickup": "stopped"},
            )
            return result
        except Exception as exc:
            # Metadata is the visibility boundary. Remove it before unlock/resume.
            try:
                (directory / "profile.json").unlink(missing_ok=True)
                if imported and locked and not previously_paused:
                    state.resume()
                force_rmtree(directory)
            except OSError as rollback_exc:
                failure = _contract_rejection(
                    "project_rollback_failed",
                    "config",
                    "Inspect incomplete enrollment on the host before retrying.",
                )
                raise failure from rollback_exc
            if isinstance(exc, HTTPException):
                raise
            raise _contract_rejection(
                "project_creation_failed",
                "config",
                "Check local enrollment storage before retrying.",
            ) from exc
        finally:
            if locked:
                state.release_lock()


@contextmanager
def _web_config_edit_lock(path: Path):
    """@brief Map shared edit-lock contention to an HTTP conflict."""
    try:
        with config_edit_lock(path):
            yield
    except ConfigEditLockedError as exc:
        raise _error(409, "config_edit_locked") from exc


def _set_endpoint(text: str, value: str, model: str,
                  auth_env: str | None = None,
                  timeout_seconds: int | None = None,
                  ca_file: str | None = None) -> str:
    """@brief Configure OpenCode's compatible provider and endpoint."""
    provider_id, separator, model_id = model.partition("/")
    if (not separator or not re.fullmatch(r"[a-z][a-z0-9._-]*", provider_id)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model_id)):
        raise ValueError("OpenCode model must be provider/model")
    document = tomllib.loads(text)
    runtime_env = document.get("container", {}).get("runtime_env", {})
    if not isinstance(runtime_env, dict):
        raise ValueError("container.runtime_env is not a table")
    existing = runtime_env.get("OPENCODE_CONFIG_CONTENT", "{}")
    inline = json.loads(existing)
    if not isinstance(inline, dict):
        raise ValueError("OpenCode inline config is not an object")
    providers = inline.setdefault("provider", {})
    if not isinstance(providers, dict):
        raise ValueError("OpenCode provider config is not an object")
    options = {"baseURL": value}
    prior = providers.get(provider_id)
    if auth_env is None and isinstance(prior, dict):
        old_options = prior.get("options")
        if isinstance(old_options, dict):
            reference = old_options.get("apiKey")
            if isinstance(reference, str) and re.fullmatch(
                r"\{env:[A-Z][A-Z0-9_]{0,63}\}", reference
            ):
                options["apiKey"] = reference
    if auth_env:
        options["apiKey"] = f"{{env:{auth_env}}}"
    if timeout_seconds is not None:
        options["timeout"] = timeout_seconds * 1000
    elif isinstance(prior, dict) and isinstance(prior.get("options"), dict):
        prior_timeout = prior["options"].get("timeout")
        if type(prior_timeout) is int and 1000 <= prior_timeout <= 600000:
            options["timeout"] = prior_timeout
    providers[provider_id] = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "ADORE local endpoint",
        "options": options,
        "models": {model_id: {"name": model_id}},
    }
    key = "container.runtime_env.OPENAI_BASE_URL"
    if "[container.runtime_env]" in text:
        changed = _set_toml_scalar(text, key, value)
        changed = _set_toml_scalar(
            changed, "container.runtime_env.OPENCODE_CONFIG_CONTENT",
            json.dumps(inline, separators=(",", ":")),
        )
        return (_set_toml_scalar(changed, "container.runtime_env.NODE_EXTRA_CA_CERTS",
                                 ca_file) if ca_file is not None else changed)
    lines = text.split("\n")  # LF only: lines keep their CR (see _set_toml_scalar)
    inside_container = False
    inline_index = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[container]":
            inside_container = True
        elif stripped.startswith("[") and stripped.endswith("]"):
            inside_container = False
        elif inside_container and re.match(r"^\s*runtime_env\s*=", line):
            inline_index = index
            break
    if inline_index is None:
        changed = _set_toml_scalar(text, key, value)
        changed = _set_toml_scalar(
            changed, "container.runtime_env.OPENCODE_CONFIG_CONTENT",
            json.dumps(inline, separators=(",", ":")),
        )
        return (_set_toml_scalar(changed, "container.runtime_env.NODE_EXTRA_CA_CERTS",
                                 ca_file) if ca_file is not None else changed)
    runtime_env["OPENAI_BASE_URL"] = value
    removed_last = inline_index == len(lines) - 1
    del lines[inline_index]
    newline = _newline(text)
    section = f"{newline}[container.runtime_env]{newline}" + "".join(
        f"{name} = {json.dumps(item, ensure_ascii=False)}{newline}"
        for name, item in sorted(runtime_env.items())
    )
    kept = "\n".join(lines)  # every other line byte for byte
    if removed_last:
        # The removed line was the unterminated last one: give back the LF it
        # took from the line before it, so that line keeps its own ending.
        kept += "\n"
    elif kept and not kept.endswith("\n"):
        kept += newline  # the file had no final newline
    changed = kept + section
    changed = _set_toml_scalar(
        changed, "container.runtime_env.OPENCODE_CONFIG_CONTENT",
        json.dumps(inline, separators=(",", ":")),
    )
    return (_set_toml_scalar(changed, "container.runtime_env.NODE_EXTRA_CA_CERTS",
                             ca_file) if ca_file is not None else changed)


def _store_for(profiles: ProfileStore, profile) -> StateStore:
    root = profile.store_root or str(profiles.default_store_root(profile.name))
    return StateStore(root)


def _redact_config(value, prefix: str = ""):
    """
    @brief      Drop credential-looking values before rendering host config.
    @details    Expects `Config.to_dict()` output. Each key is judged by its
                full dotted name (_is_secret_key); an exempt name stays hidden
                unless its value is a boolean, so a secret pasted there by hand
                never shows.
    @param[in]  value Configuration mapping (or a value inside it).
    @param[in]  prefix Dotted path of `value`.
    @return     The mapping without secret-named keys.
    """
    if isinstance(value, dict):
        shown = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if (_is_secret_key(path) or key == "OPENCODE_CONFIG_CONTENT"
                    or (path in _NOT_SECRET_KEYS and type(item) is not bool)):
                continue
            shown[key] = _redact_config(item, path)
        return shown
    if isinstance(value, list):
        return [_redact_config(item, prefix) for item in value]
    if isinstance(value, str) and value.lower().startswith(("https://", "http://")):
        try:
            url = urlsplit(value)
            if (url.username or url.password
                    or any(_SECRET_KEY_RE.search(key) for key, _ in parse_qsl(url.query))):
                return "[redacted]"
        except ValueError:
            return "[redacted]"
    return value


def _csv_text(value: str) -> str:
    """@brief Keep external profile labels from becoming spreadsheet formulas."""
    if value and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _profile_view(profiles: ProfileStore, profile) -> dict:
    if any(not isinstance(value, str) for value in (
        profile.name, profile.description, profile.platform, profile.repo,
        profile.runtime, profile.display_name,
    )):
        raise _error(503, "project_corrupt")
    store = _store_for(profiles, profile)
    invalid_runs = store.invalid_runs()
    runs = store.list_runs()
    last_activity: datetime | None = None
    for run in runs:
        try:
            changed = datetime.fromisoformat(run.updated_at)
            if changed.tzinfo is None or changed.utcoffset() is None:
                raise ValueError("naive activity timestamp")
        except (TypeError, ValueError) as exc:
            raise _error(503, "run_state_corrupt") from exc
        changed = changed.astimezone(UTC)
        if last_activity is None or changed > last_activity:
            last_activity = changed
    raw = None
    try:
        raw = profiles.config_path(profile.name).read_bytes()
        revision = sha256(raw).hexdigest()
        config = _config_from_bytes(raw)
        findings = _config_findings(config)
        config_valid = not findings
    except (OSError, AttributeError, TypeError, ValueError, tomllib.TOMLDecodeError):
        config_valid = False
        config = None
        revision = sha256(raw).hexdigest() if raw is not None else None
        findings = [_finding("config_invalid", "config",
                             "Supply a valid project TOML configuration.")]
    paused = store.is_paused()
    readiness = (
        "archived" if profile.archived else
        "invalid-state" if invalid_runs else
        "paused" if paused else
        "needs-config" if not config_valid else "configured"
    )
    return {
        "id": profile.project_id,
        "name": profile.name,
        "display_name": profile.display_name,
        "validation": {"structural_valid": config_valid, "issues": findings},
        "pickup_state": "archived" if profile.archived else "stopped" if paused else "active",
        "verification": _verification_view(profiles, profile, revision),
        "description": profile.description,
        "platform": config.platform.kind if config_valid and config else profile.platform,
        "repo": config.platform.repo if config_valid and config else profile.repo,
        "runtime": ("local" if config.execution.backend == "local" else config.container.runtime)
        if config_valid and config else profile.runtime,
        "executor": config.executor.default if config_valid and config else "",
        "config_valid": config_valid,
        "readiness": readiness,
        "last_activity": last_activity.isoformat() if last_activity else None,
        "archived": profile.archived,
        "paused": paused,
        "invalid_runs": invalid_runs,
        "runs": len(runs),
    }


def _valid_candidate_scalar(key: str, proposed: object, backend: str = "container") -> bool:
    """
    @brief Enforce scalar types and the dedicated reviewer-list type for pending edits.
    @param[in] key TOML file key of the single candidate edit.
    @param[in] proposed Parsed candidate value.
    @return True for a declared scalar type or an exact approved collection.
    """
    if key == "executor.selection":
        return valid_selection(proposed)
    if key in COLLECTION_KEYS:
        return valid_collection(key, proposed)
    if key == "delivery.reviewers":
        return valid_reviewers(proposed)
    if key in {"container.image", "container.runtime"}:
        return _valid_environment_value(key, proposed)
    if key.endswith(".command"):
        return isinstance(proposed, str) and (backend == "local" and bool(proposed.strip())
                                              or proposed in _LAUNCH_PRESETS.get(key, ()))
    expected = _value_at(default_config().to_dict(), key)
    if (re.fullmatch(r"executor\.[^.]+\.model", key)
            or key == "container.runtime_env.OPENAI_BASE_URL"):
        expected = ""
    if type(expected) is float:
        return type(proposed) in (int, float) and math.isfinite(proposed)
    if isinstance(expected, str | int | bool):
        return type(proposed) is type(expected)
    if key.startswith("workflow.kind_labels."):
        return isinstance(proposed, str) and proposed in RUN_KINDS
    if key.startswith("workflow.stage_timeout_overrides."):
        return type(proposed) is int and proposed > 0
    if key.startswith("local.environment."):
        return isinstance(proposed, str)
    return False


def _set_candidate_value(text: str, key: str, value: str) -> str:
    """
    @brief Write a scalar or the closed reviewer-list edit, retaining unrelated TOML.
    @param[in] text Active TOML text.
    @param[in] key Authorized candidate key.
    @param[in] value Scalar wire value or JSON reviewer list.
    @return Candidate text, preserving unrelated keys and line endings.
    @exception ValueError When collection input or existing key spelling is unsupported.
    """
    if key == "executor.selection":
        return set_selection(text, value)
    if key in COLLECTION_KEYS:
        return set_collection(text, key, value)
    if key != "delivery.reviewers":
        return _set_toml_scalar(text, key, value)
    reviewers = json.loads(value)
    if not valid_reviewers(reviewers):
        raise ValueError("invalid reviewer list")
    newline = _newline(text)
    literal = "reviewers = " + json.dumps(reviewers, ensure_ascii=False)
    lines = text.splitlines(keepends=True)
    header = None
    inside = False
    for index, line in enumerate(lines):
        if re.match(r'^\s*\[', line):
            inside = bool(re.fullmatch(r"\s*\[delivery\]\s*(?:#.*)?", line.strip()))
            if inside:
                header = index
        if inside and re.match(r'^\s*(?:reviewers|"reviewers"|\'reviewers\')\s*=', line):
            for end in range(index + 1, len(lines) + 1):
                try:
                    fragment = tomllib.loads("".join(lines[index:end]))
                except tomllib.TOMLDecodeError:
                    continue
                if set(fragment) != {"reviewers"}:
                    raise ValueError("unsupported reviewer key spelling")
                lines[index:end] = [literal + (newline if lines[end - 1].endswith("\n") else "")]
                return "".join(lines)
            raise ValueError("unsupported reviewer array")
    if header is None:
        if _value_at(tomllib.loads(text), key) is not None:
            raise ValueError("unsupported reviewer key spelling")
        return text + ("" if not text or text.endswith("\n") else newline) + (
            newline + "[delivery]" + newline + literal + newline
        )
    lines[header] = lines[header].rstrip("\r\n") + newline
    lines.insert(header + 1, literal + newline)
    return "".join(lines)


def _candidate_value(tree: dict, key: str):
    """@brief Read one scalar/collection or the complete synthetic agent review."""
    return selection_value(tree) if key == "executor.selection" else _value_at(tree, key)


def _candidate_config_edit(path: Path, body: ConfigEdit) -> tuple[bytes, str]:
    """@brief Produce one validated scalar or reviewer-list edit without changing live TOML."""
    endpoint_key = body.key == "container.runtime_env.OPENAI_BASE_URL"
    if (body.model is not None or body.auth_env is not None
            or body.protocol is not None or body.timeout_seconds is not None
            or body.ca_file is not None) and not endpoint_key:
        raise _error(400, "model_requires_endpoint")
    if not _editable_setting_key(body.key, endpoint=endpoint_key):
        raise _error(400, "setting_not_editable")
    if endpoint_key:
        if (body.ca_file and (not body.value.startswith("https://")
                or not body.ca_file.startswith("/")
                or ".." in Path(body.ca_file).parts
                or any(ord(char) < 32 for char in body.ca_file)
                or len(body.ca_file) > 256)):
            raise _error(400, "invalid_endpoint_ca")
        try:
            endpoint = urlsplit(body.value)
            valid = (
                endpoint.scheme in ("http", "https")
                and bool(endpoint.hostname)
                and endpoint.username is None
                and endpoint.password is None
                and not endpoint.fragment
                and not endpoint.query
            )
        except ValueError:
            valid = False
        if not valid:
            raise _error(400, "invalid_endpoint_url")
    try:
        raw = path.read_bytes()
        if not secrets.compare_digest(sha256(raw).hexdigest(), body.revision):
            raise _error(409, "stale_config_revision")
        current = raw.decode("utf-8")
        if body.key.endswith(".command") and (
            not _valid_candidate_scalar(body.key, body.value,
                    tomllib.loads(current).get("execution", {}).get("backend", "container"))
            or not isinstance(_value_at(tomllib.loads(current), body.key), str)
        ):
            raise _error(400, "invalid_config")
        if endpoint_key:
            active = load_config(path)
            if active.executor.default != "opencode":
                raise _error(400, "unsupported_local_endpoint_executor")
            if (body.auth_env is not None
                    and (not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", body.auth_env)
                         or body.auth_env not in active.executor.env_keys)):
                raise _error(400, "invalid_endpoint_auth_reference")
            model = (body.model if body.model is not None
                     else active.executor.commands["opencode"].model)
            if body.model is not None:
                current = _set_toml_scalar(current, "executor.opencode.model", body.model)
            changed = _set_endpoint(current, body.value, model, body.auth_env,
                                    body.timeout_seconds, body.ca_file)
        else:
            changed = _set_candidate_value(current, body.key, body.value)
        parsed_change = tomllib.loads(changed)
        if not _valid_candidate_scalar(
            body.key, _candidate_value(parsed_change, body.key),
            parsed_change.get("execution", {}).get("backend", "container")
        ):
            raise _error(400, "invalid_config")
        if _secret_config_keys({"setting": _candidate_value(parsed_change, body.key)}):
            raise _error(400, "invalid_config")
        if len(changed.encode("utf-8")) > 1048576:
            raise _error(413, "config_too_large")
        with tempfile.TemporaryDirectory(prefix="config.web-", dir=path.parent) as temp:
            candidate = Path(temp) / "candidate.toml"
            candidate.write_bytes(changed.encode("utf-8"))  # bytes: keep line endings
            if validate_config(load_config(candidate)):
                raise _error(400, "invalid_config")
    except (UnicodeError, OSError, ValueError, TypeError, KeyError,
            tomllib.TOMLDecodeError) as exc:
        raise _error(400, "invalid_config") from exc
    return raw, changed


def _read_pending_config(path: Path) -> dict | None:
    """@brief Read and verify a durable staged edit, failing closed on corruption."""
    if path.is_symlink():
        raise _error(503, "pending_config_corrupt")
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > 2097152:
            raise ValueError("pending config too large")
        value = strict_json_loads(path.read_text(encoding="utf-8"))
        if (not isinstance(value, dict) or type(value.get("schema")) is not int
                or value["schema"] != 1
                or any(not isinstance(value.get(key), str) for key in (
                    "base_revision", "candidate_revision", "candidate_text",
                    "key", "value", "created_at",
                ))
                or re.fullmatch(r"[0-9a-f]{64}", value["base_revision"]) is None
                or re.fullmatch(r"[0-9a-f]{64}", value["candidate_revision"]) is None
                or type(value.get("restart_required")) is not bool
                or value["restart_required"] != _restart_required(value["key"])
                or len(value["candidate_text"].encode("utf-8")) > 1048576
                or sha256(value["candidate_text"].encode("utf-8")).hexdigest()
                != value["candidate_revision"]):
            raise ValueError("invalid pending config record")
        changed = datetime.fromisoformat(value["created_at"])
        if changed.tzinfo is None or changed.utcoffset() is None:
            raise ValueError("undated pending config")
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise _error(503, "pending_config_corrupt") from exc
    return value


def _public_pending_config(value: dict, *, active_text: str | None = None) -> dict:
    """@brief Return review metadata without exposing the full TOML document."""
    # Only an earlier build could stage an image binding or an operator-owned key.
    if "image_build" in value or (
            isinstance(value.get("key"), str) and _external_environment_key(
                value["key"], endpoint=value["key"] == "container.runtime_env.OPENAI_BASE_URL")):
        raise _error(503, "pending_config_corrupt")
    public = {key: value[key] for key in (
        "base_revision", "candidate_revision", "key", "value", "created_at",
        "restart_required",
    )}
    if "execution_plan" in value:
        try:
            public["execution_plan"] = public_plan(validate_plan(value["execution_plan"]))
        except PreparationError as exc:
            raise _error(503, "pending_config_corrupt") from exc
    try:
        candidate = tomllib.loads(value["candidate_text"])
        endpoint_key = value["key"] == "container.runtime_env.OPENAI_BASE_URL"
        if not _editable_setting_key(value["key"], endpoint=endpoint_key):
            raise ValueError("unreviewable setting")
        proposed = _candidate_value(candidate, value["key"])
        if not _valid_candidate_scalar(value["key"], proposed,
                                       candidate.get("execution", {}).get("backend", "container")):
            raise ValueError("invalid proposed value")
        if _secret_config_keys({"setting": proposed}):
            raise ValueError("unsafe proposed value")
        claimed = (strict_json_loads(value["value"])
                   if value["key"] in COLLECTION_KEYS or value["key"] == "executor.selection"
                   else _value_at(tomllib.loads(_set_candidate_value(
                       "", value["key"], value["value"])), value["key"]))
        if type(claimed) is not type(proposed) or claimed != proposed:
            raise ValueError("candidate review metadata differs from its value")
        if ((value["key"] in COLLECTION_KEYS or value["key"] == "executor.selection")
                and active_text is not None
                and sha256(active_text.encode("utf-8")).hexdigest() == value["base_revision"]
                and candidate != tomllib.loads(_set_candidate_value(
                    active_text, value["key"], value["value"]))):
            raise ValueError("collection candidate changed unrelated settings")
        public["proposed_value"] = proposed
        public["value"] = (json.dumps(proposed, ensure_ascii=False, separators=(",", ":"))
                           if isinstance(proposed, (list, dict)) else
                           str(proposed).lower() if type(proposed) is bool else str(proposed))
        if (value["key"] == "container.image"
                and active_text is not None
                and sha256(active_text.encode("utf-8")).hexdigest() == value["base_revision"]):
            active = tomllib.loads(active_text)
            if (candidate.get("container", {}).get("required_tool_checks", [])
                    != active.get("container", {}).get("required_tool_checks", [])):
                raise ValueError("image candidate lost its tool-check review binding")
    except (KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        raise _error(503, "pending_config_corrupt") from exc
    if endpoint_key:
        try:
            model = candidate["executor"]["opencode"]["model"]
            if not isinstance(model, str) or not model.strip():
                raise ValueError("invalid endpoint model")
            provider = model.partition("/")[0]
            runtime_env = candidate["container"]["runtime_env"]
            options = json.loads(runtime_env[
                "OPENCODE_CONFIG_CONTENT"])["provider"][provider]["options"]
            auth_ref = options.get("apiKey", "")
            if (auth_ref and (not re.fullmatch(
                    r"\{env:[A-Z][A-Z0-9_]{0,63}\}", auth_ref)
                    or auth_ref[5:-1] not in candidate["executor"]["env_keys"])):
                raise ValueError("invalid auth reference")
            if (candidate["executor"]["default"] != "opencode"
                    or json.loads(runtime_env["OPENCODE_CONFIG_CONTENT"])["provider"][provider]
                    .get("npm") != "@ai-sdk/openai-compatible"
                    or options.get("baseURL") != proposed
                    or options.get("timeout") is not None and (
                        type(options["timeout"]) is not int
                        or not 1000 <= options["timeout"] <= 600000
                        or options["timeout"] % 1000)):

                raise ValueError("invalid endpoint profile")
            ca_file = runtime_env.get("NODE_EXTRA_CA_CERTS")
            if (ca_file is not None and not isinstance(ca_file, str)
                    or ca_file and (not proposed.startswith("https://")
                        or not ca_file.startswith("/") or ".." in Path(ca_file).parts
                        or any(ord(char) < 32 for char in ca_file) or len(ca_file) > 256)):
                raise ValueError("invalid endpoint CA path")
            public["endpoint"] = {
                "protocol": "openai-chat-completions", "model": model,
                "auth_env": auth_ref[5:-1] if auth_ref else None,
                "timeout_seconds": (options["timeout"] // 1000
                                    if type(options.get("timeout")) is int else None),
                "ca_file": ca_file or None,
            }
        except (KeyError, TypeError, ValueError, tomllib.TOMLDecodeError,
                json.JSONDecodeError) as exc:
            raise _error(503, "pending_config_corrupt") from exc
    return public


def _restart_required(key: str) -> bool:
    """@brief Classify edits that change project identity or runtime wiring."""
    return key.startswith(("agent.", "platform.", "worktree.",
                           "container.", "execution.", "local.", "executor."))


# Environment settings an administrator chooses in the web (reviewed edits only).
_CHOSEN_ENVIRONMENT_KEYS = frozenset({
    "execution.backend", "container.runtime", "container.image",
    "local.account", "local.home", "local.path", "local.cgroup_root",
})
_IMAGE_LIST_TIMEOUT = 15
_IMAGE_LIST_LIMIT = 1000
# An image reference (never an option or argv); the runtime is the bare command or a WSL wrapper.
_IMAGE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:@-]{0,254}")
_RUNTIME_COMMAND = re.compile(r"(?:wsl(?: -[A-Za-z] [A-Za-z0-9._-]+)* -- )?(?:docker|podman)")


def _valid_environment_value(key: str, value: object) -> bool:
    """@brief Web-written image and runtime values; other keys are not checked here."""
    if key == "container.image":
        return isinstance(value, str) and bool(_IMAGE_REFERENCE.fullmatch(value))
    if key == "container.runtime":
        return isinstance(value, str) and bool(_RUNTIME_COMMAND.fullmatch(value))
    return True


def _external_environment_key(key: str, *, endpoint: bool = False) -> bool:
    """@brief Identify externally owned environment keys at web mutation boundaries.
    @param[in] key Dotted configuration key.
    @param[in] endpoint Dedicated validated AI endpoint editing exception.
    @return True for operator-owned environment settings.
    """
    return (not endpoint and key not in {"worktree.branch_template", "worktree.branch_rule"}
            and key not in _CHOSEN_ENVIRONMENT_KEYS
            and not _is_secret_key(key)
            and key.startswith(("container.", "execution.", "local.", "worktree.")))


def _editable_setting_key(key: str, *, endpoint: bool = False) -> bool:
    """
    @brief      The one rule for which configuration keys the web may edit.
    @details    Used by the edit endpoints and by the per-setting metadata the
                configuration view returns, so the two always agree.
    @param[in]  key Dotted TOML key.
    @param[in]  endpoint True for the OpenAI-compatible endpoint key, which is
                edited through its own validated form.
    @return     True when the key may be staged from the browser.
    """
    if key in {"metrics.db_path", "metrics.export_jsonl", "metrics.html_out",
               "workflow.aegis_python"}:
        return False
    if key in {"clarification.answer_timeout", "clarification.max_rounds"}:
        return True
    return not (
        _is_secret_key(key)
        or (not endpoint and not _SETTING_KEY_RE.fullmatch(key))
        or key.split(".")[0] not in _EDITABLE_SECTIONS
        or key.endswith(".command") and key not in _LAUNCH_PRESETS
    )


def _toml_leaves(value, prefix: str = "") -> list[tuple[str, object]]:
    """
    @brief      Dotted keys and values of the leaves of a nested mapping.
    @details    A non-empty mapping is walked; an empty mapping, a list or a
                scalar is a leaf.
    @param[in]  value Mapping (or leaf value).
    @param[in]  prefix Dotted path of `value`.
    @return     (dotted key, value) pairs in mapping order.
    """
    if isinstance(value, dict) and value:
        return [leaf for key, child in value.items()
                for leaf in _toml_leaves(child, f"{prefix}.{key}" if prefix else key)]
    return [(prefix, value)]


def _value_at(tree: dict, key: str):
    """
    @brief      Value at a dotted key of a nested mapping, leaf or sub-table.
    @param[in]  tree Nested mapping.
    @param[in]  key Dotted path.
    @return     The value, or None when the path does not exist.
    """
    node = tree
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _setting_domain(key: str, value: object, config: dict, declared: object) -> dict:
    """
    @brief Project the current configuration validation domain for a setting.
    @param[in] key Effective dotted configuration key.
    @param[in] value Redacted effective value; establishes scalar/list/map type.
    @param[in] config Redacted configuration; supported agents and provider names supply choices.
    @param[in] declared Built-in model default supplying the declared type.
    @return Type, allowed choices and inclusive numeric bounds for browser guidance.
    @note Full configuration validation remains authoritative for dependent rules.
    """
    expected = declared
    if key.startswith("executor.commands.") and key.endswith((".model", ".command")):
        expected = ""
    if key.startswith("workflow.stage_timeout_overrides."):
        expected = 1
    if key.startswith(("workflow.kind_labels.", "container.runtime_env.", "local.environment.")):
        expected = ""
    if expected is not None:
        numeric = type(expected) is float and type(value) in (int, float) and math.isfinite(value)
        if (type(expected) is float and not numeric
                or type(expected) is not float and type(value) is not type(expected)):
            raise ValueError("configuration scalar type differs from its model")
    model_value = expected if expected is not None else value
    choices = {
        "platform.kind": ["gitlab", "github", "gitea"],
        "polling.mode": ["loop", "once"],
        "executor.mode": ["thick", "headless"],
        "executor.default": list(SUPPORTED_AGENTS),
        "executor.env_keys": sorted(
            PROVIDER_KEYS | set(config.get("executor", {}).get("env_keys", []))),
        "clarification.timeout_state": ["failed", "stale"],
        "container.selinux_relabel": list(SELINUX_RELABEL_MODES),
        "container.parked_ttl_mode": ["seconds", "polls"],
        "container.egress.mode": ["open", "allowlist-proxy", "none"],
        "execution.backend": ["container", "local"],
        "delivery.draft": [True, False],
        "review.trigger": ["label"],
        "review.on_pipeline_failure": ["revise", "notify", "ignore"],
        "workflow.default_kind": list(RUN_KINDS),
        "reconcile.on_ticket_deleted": ["abort-cleanup", "ignore"],
        "reconcile.on_ticket_closed": ["cancel", "ignore"],
        "reconcile.on_trigger_removed": ["pause", "abort", "ignore"],
    }.get(key, [])
    if key.startswith("executor.commands.") and key.endswith(".command"):
        choices = list(_LAUNCH_PRESETS.get(
            "executor." + key.removeprefix("executor.commands."), (),
        ))
    if key.endswith(".command") and config.get("execution", {}).get("backend") == "local":
        choices = []
    if key.startswith("workflow.kind_labels."):
        choices = list(RUN_KINDS)
    positive = {
        "polling.poll_interval_seconds", "polling.max_concurrent_runs",
        "clarification.max_rounds", "recovery.max_stage_failures",
        "recovery.max_transient_retries", "budgets.max_iterations",
        "budgets.max_wall_clock_seconds", "budgets.per_gate_timeout_seconds",
        "budgets.max_files_touched", "review.max_review_rounds",
        "container.egress.proxy_port", "execution.preparation_step_timeout_seconds",
        "execution.preparation_total_timeout_seconds", "execution.preparation_max_attempts",
    }
    minimum = (1 if key in positive or key.startswith("workflow.stage_timeout_overrides.")
               else 0 if key in {"polling.poll_jitter_seconds", "budgets.max_cost_usd"}
               else None)
    kind = ("boolean" if type(model_value) is bool else "integer" if type(model_value) is int
            else "number" if type(model_value) is float else "list" if isinstance(model_value, list)
            else "map" if isinstance(model_value, dict) else "text")
    return {"type": kind, "choices": choices, "minimum": minimum,
            "maximum": {"container.egress.proxy_port": 65535,
                        "execution.preparation_step_timeout_seconds": 1800,
                        "execution.preparation_total_timeout_seconds": 3600,
                        "execution.preparation_max_attempts": 3}.get(key)}


def _setting_metadata(config: dict, raw: bytes) -> list[dict]:
    """
    @brief      Source, editability and restart need of every effective setting.
    @details    `config` is the redacted effective configuration; `raw` the
                project's TOML file. The file key of an executor command field
                is `executor.<name>.<field>`, while the effective configuration
                nests it under `executor.commands`. A setting is from the
                project when its file key is a leaf of the file, whatever its
                value; it is editable when the shared key rule accepts the file
                key and its value has a supported scalar or closed collection type. Missing
                agent fields expose noneditable preset metadata for the atomic
                selection editor. Its
                default is the value at the same key in ADORE's built-in
                configuration (names derived, redacted) - the whole built-in
                map for a map the project emptied - or None when that
                configuration has no such key.
    @param[in]  config Redacted effective configuration mapping.
    @param[in]  raw Project configuration file bytes.
    @return     One entry per setting, sorted by key.
    @exception  tomllib.TOMLDecodeError When the file is not valid TOML.
    """
    in_file = {key for key, _ in _toml_leaves(tomllib.loads(raw.decode("utf-8")))}
    defaults = _redact_config(default_config().to_dict())
    settings = []
    leaves = [(key, value) for key, value in _toml_leaves(config)
              if key != "workflow.stage_timeout_overrides"
              and not key.startswith("workflow.stage_timeout_overrides.")]
    leaves.append(("workflow.stage_timeout_overrides",
                   config.get("workflow", {}).get("stage_timeout_overrides", {})))
    present = {key for key, _ in leaves}
    virtual = set()
    for agent in SUPPORTED_AGENTS:
        for field in ("command", "model"):
            key = f"executor.commands.{agent}.{field}"
            if key not in present:
                leaves.append((key, ""))
                virtual.add(key)
    for key, value in leaves:
        edit_key = ("executor." + key.removeprefix("executor.commands.")
                    if key.startswith("executor.commands.") else key)
        source_key = edit_key
        if key == "executor.default":
            edit_key = "executor.selection"
        settings.append({
            "key": key,
            "edit_key": edit_key,
            "source": "project" if (source_key in in_file or edit_key in COLLECTION_KEYS
                                     and any(k.startswith(edit_key + ".") for k in in_file))
            else "default",
            "editable": (key not in virtual and not _external_environment_key(edit_key)
                         and _editable_setting_key(edit_key)
                         and (isinstance(value, str | int | float)
                              or edit_key == "delivery.reviewers" and valid_reviewers(value)
                              or edit_key in COLLECTION_KEYS
                              and valid_collection(edit_key, value))),
            "restart": _restart_required(edit_key),
            "default": _value_at(defaults, key),
            **_setting_domain(key, value, config, _value_at(defaults, key)),
        })
    return sorted(settings, key=lambda item: item["key"])


def _sync_profile_config_identity(profiles: ProfileStore, item, path: Path) -> None:
    """@brief Keep profile directory labels aligned with the committed TOML."""
    config = load_config(path)
    item = profiles.load(item.name)
    item.platform = config.platform.kind
    item.repo = config.platform.repo
    item.runtime = "local" if config.execution.backend == "local" else config.container.runtime
    profiles.save(item)


def _write_pending_config(path: Path, value: dict) -> None:
    """@brief Replace one staged JSON record atomically."""
    descriptor, candidate_name = tempfile.mkstemp(prefix="pending-config-", dir=path.parent)
    candidate = Path(candidate_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        candidate.replace(path)
    finally:
        candidate.unlink(missing_ok=True)


def _secret_config_keys(value: object, prefix: str = "", *, provider: bool = False) -> list[str]:
    """@brief Find embedded secret values without returning their contents."""
    if isinstance(value, list):
        return [key for child in value
                for key in _secret_config_keys(child, prefix, provider=provider)]
    if not isinstance(value, dict):
        return []
    found = []
    for key, child in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if name in _NOT_SECRET_KEYS and type(child) is bool:
            continue
        if key == "OPENCODE_CONFIG_CONTENT":
            try:
                inline = json.loads(child)
                if not isinstance(inline, dict):
                    raise ValueError("invalid provider config")
                found.extend(_secret_config_keys(inline, name, provider=True))
            except (ValueError, TypeError):
                found.append(name)
        elif _SECRET_KEY_RE.search(key) and child:
            if not (provider and key == "apiKey" and isinstance(child, str)
                    and re.fullmatch(r"\{env:[A-Z][A-Z0-9_]{0,63}\}", child)):
                found.append(name)
        elif isinstance(child, str) and child.lower().startswith(("https://", "http://")):
            try:
                url = urlsplit(child)
                if url.username or url.password or any(_SECRET_KEY_RE.search(query_key)
                                                       for query_key, _ in parse_qsl(url.query)):
                    found.append(name)
            except ValueError:
                found.append(name)
        else:
            found.extend(_secret_config_keys(child, name, provider=provider))
    return found


def _inspect_project_import(
    profiles: ProfileStore, body: ProjectImportInput, *, own_state_lock: bool = False,
) -> tuple[dict, object]:
    """@brief Inspect exact TOML, safe review and current ownership/state evidence.

    @param[in] profiles Server profile ownership store.
    @param[in] body Exact UTF-8 text and declared display identity.
    @param[in] own_state_lock Publication already owns this candidate conductor lock.
    @return Field-addressable findings, bound revisions and safe review/config.
    @exception HTTPException Corrupt ownership or inaccessible inspection fails closed.
    """
    try:
        name = validate_profile_id(body.name)
        display = _setup_display(body)
        available = own_state_lock or profiles.id_availability(name)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
    except ProfileError as exc:
        raise _identity_error(exc) from exc
    except OSError as exc:
        raise _contract_rejection("project_creation_failed", "config",
                                  "Check server profile storage.") from exc
    try:
        raw = body.config_text.encode("utf-8")
    except UnicodeError as exc:
        raise _error(400, "config_invalid") from exc
    if len(raw) > 524288:
        raise _error(413, "config_too_large")
    config_revision = sha256(raw).hexdigest()
    findings = [] if available else [_finding("project_exists", "name", "Choose another ID.")]
    config, review, ownership, state_evidence = None, None, [], []
    resolved_paths = {}
    try:
        config = _config_from_bytes(raw)
        findings.extend(_config_findings(config))
        paths = {"state.store_root": config.state.store_root,
                 "worktree.repo_path": config.worktree.repo_path,
                 "worktree.root": config.worktree.root,
                 "metrics.db_path": config.metrics.db_path,
                 "metrics.export_jsonl": config.metrics.export_jsonl,
                 "metrics.html_out": config.metrics.html_out}
        for key, value in paths.items():
            if not isinstance(value, str) or not Path(value).is_absolute():
                findings.append(_finding("absolute_path_required", key,
                                         "Set an absolute location on this ADORE server."))
            elif Path(value).resolve() == Path(Path(value).resolve().anchor):
                findings.append(_finding("path_must_not_be_volume_root", key,
                                         "Choose a project location below the volume root."))
        if not findings:
            resolved_paths = {key: str(Path(value).resolve()) for key, value in paths.items()}
            root = Path(config.state.store_root).resolve()
            for other in profiles.list_profiles():
                other_root = Path(other.store_root or
                                  profiles.default_store_root(other.name)).resolve()
                ownership.append([other.project_id, str(other_root)])
                if (root == other_root or root.is_relative_to(other_root)
                        or other_root.is_relative_to(root)):
                    findings.append(_finding("state_root_already_owned", "state.store_root",
                                             "Set an unowned state location in the source file."))
            state = StateStore(root, config.agent.slug)
            if not own_state_lock and state.lock_path.exists():
                findings.append(_finding("project_has_active_work", "state.store_root",
                                         "Finish work and release its conductor lock."))
            if state.invalid_runs():
                findings.append(_finding("run_state_corrupt", "state.store_root",
                                         "Repair corrupt server run state before enrollment."))
            runs = state.list_runs()
            state_evidence = sorted([run.run_id, run.lifecycle, run.updated_at] for run in runs)
            if any(run.lifecycle not in _TERMINAL_RUN_LIFECYCLES for run in runs):
                findings.append(_finding("project_has_active_work", "state.store_root",
                                         "Finish existing server jobs before enrollment."))
        if not findings:
            review = {"name": name, "display_name": display, "description": body.description,
                      "config_path": str(profiles.config_path(name).resolve()), "paths": paths,
                      "resolved_paths": resolved_paths,
                      "platform": {"kind": config.platform.kind, "repo": config.platform.repo,
                                   "login": config.platform.login},
                      "target_branch": config.delivery.target_branch,
                      "agent": {"name": config.agent.name, "slug": config.agent.slug,
                                "email": config.agent.email},
                      "executor": {"default": config.executor.default,
                                   "model": config.executor.commands[config.executor.default].model,
                                   "env_keys": config.executor.env_keys,
                                   "stage_host_auth": config.executor.stage_host_auth},
                      "container": {"runtime": ("local" if config.execution.backend == "local"
                                                else config.container.runtime),
                                    "image": config.container.image,
                                    "egress": config.container.egress.mode}}
    except (AttributeError, TypeError, ValueError, tomllib.TOMLDecodeError):
        findings = [_finding("config_invalid", "config", "Supply a valid UTF-8 TOML document.")]
        config, review = None, None
    except (OSError, StateError, ProfileError) as exc:
        raise _contract_rejection("project_creation_failed", "config",
                                  "Check server configuration and state storage.") from exc
    revision = sha256(json.dumps({"config_revision": config_revision, "name": name,
                                 "display_name": display, "description": body.description,
                                 "resolved_paths": resolved_paths,
                                 "ownership": sorted(ownership), "state": state_evidence},
                                sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"name": name, "display_name": display, "revision": revision,
            "config_revision": config_revision,
            "issues": [item["code"] if item["field"] == "config" or item["code"] in {
                "project_exists", "state_root_already_owned"} else
                "state_root_must_not_be_volume_root" if item["code"] ==
                "path_must_not_be_volume_root" and item["field"] == "state.store_root" else
                f'{item["code"]}:{item["field"]}' for item in findings],
            "validation": {"structural_valid": not findings, "issues": findings},
            "review": review, "unchanged": True, "paused_on_import": True,
            "platform": config.platform.kind if review else None,
            "repo": config.platform.repo if review else None,
            "runtime": (("local" if config.execution.backend == "local"
                         else config.container.runtime) if review else None),
            "store_root": config.state.store_root if review else None,
            "verification": {"status": "unverified"}}, config


def _reviewed_import(profiles: ProfileStore, body: ProjectImportInput,
                     *, own_state_lock: bool = False) -> tuple[dict, object]:
    """@brief Reject a stale or invalid import at each publication/probe boundary.

    @param[in] profiles Current ownership store.
    @param[in] body Reviewed candidate and revision.
    @param[in] own_state_lock Ignore only the publication's own conductor lock.
    @return Current valid preview/config.
    @exception HTTPException Stale revision or invalid candidate is rejected.
    """
    preview, config = _inspect_project_import(profiles, body, own_state_lock=own_state_lock)
    if (not re.fullmatch(r"[0-9a-f]{64}", body.revision)
            or not secrets.compare_digest(body.revision, preview["revision"])):
        raise _error(409, "stale_import_preview")
    if preview["issues"] or config is None:
        conflicts = {"project_has_active_work", "run_state_corrupt",
                     "state_root_already_owned", "project_exists"}
        status = (409 if any(item["code"] in conflicts
                             for item in preview["validation"]["issues"]) else 400)
        raise HTTPException(status_code=status, detail={"code": "config_invalid",
                                                       "issues": preview["validation"]["issues"]})
    return preview, config


def _check_reporting_scope(day_from, day_to, timezone, granularity, executor=None, model=None):
    """@brief Validate global scope even when no project contributes data."""
    try:
        scope = analytics.Scope.create(day_from, day_to, timezone, granularity)
        analytics.usage_report([], "", scope, [], False, executor, model)
    except analytics.AnalyticsError as exc:
        raise _error(exc.status, exc.code) from exc


def _analytics_sources(profiles, profile, web, admin):
    """@brief Strictly inspect authorized evidence and preserve projection cursors."""
    store = _store_for(profiles, profile)
    sources = analytics.read_sources(store)
    try:
        prices = web.list_prices(profile.name) if admin else []
    except WebStoreError as exc:
        raise _error(503, "price_storage_corrupt") from exc
    for run, events in sources:
        try:
            web.reconcile_usage(profile.project_id, run.run_id, events)
        except (metrics.MetricsError, WebStoreError) as exc:
            raise analytics.AnalyticsError("usage_corrupt") from exc
    return store, sources, prices


def _usage_view(profiles: ProfileStore, profile, admin: bool, web: WebStore,
                day_from: date | None, day_to: date | None,
                executor: str | None, model: str | None,
                timezone: str = "UTC",
                granularity: Literal["day", "week", "month"] = "day") -> dict:
    """@brief Return shared scoped, nullable consumption with composite jobs."""
    try:
        scope = analytics.Scope.create(day_from, day_to, timezone, granularity)
        analytics.usage_report([], "", scope, [], False, executor, model)
        store, sources, prices = _analytics_sources(profiles, profile, web, admin)
        summaries = _configured_summaries(profiles, profile, store)
        result = analytics.usage_report(sources, profile.project_id, scope, prices,
                                        admin, executor, model, summaries)
    except metrics.MetricsError as exc:
        raise _error(503, "usage_corrupt") from exc
    except analytics.AnalyticsError as exc:
        code = "usage_corrupt" if exc.status == 503 and exc.code == "metrics_corrupt" else exc.code
        raise _error(exc.status, code) from exc
    result["filters"] = {"day_from": day_from.isoformat() if day_from else None,
                         "day_to": day_to.isoformat() if day_to else None,
                         "executor": executor, "model": model}
    return result


def _analytical_csv(views: list[tuple[object, dict]], admin: bool,
                    global_view: bool, kind: str,
                    empty_scope: analytics.Scope | None = None) -> Response:
    """@brief Export selected rows with scope, source coverage and financial RBAC."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    scope_columns = ["project_id", "timezone", "granularity", "scope_mode",
                     "scope_from", "scope_to"]
    if kind == "metrics":
        columns = ["date", "started", "completed", "failed", "tokens_in", "tokens_out",
                   "mr_revisions", "pipeline_repairs"]
    elif kind == "usage":
        columns = ["date", "executor", "model", "events", "tokens_in", "tokens_out",
                   "cache_read_tokens", "cache_write_tokens"]
    else:
        columns = ["run_id", "source"]
        fields = ["tokens_in", "tokens_out", "cache_read_tokens", "cache_write_tokens"]
        if admin:
            fields.extend(("reported_cost_usd", "estimated_cost_usd"))
        columns.extend(f"{period}_{field}" for period in ("lifetime", "in_period", "unallocated")
                       for field in fields)
    if admin and kind != "jobs-usage":
        columns.extend(("reported_cost_usd", "estimated_cost_usd"))
    prefix = ["project", "repository"] if global_view else []
    coverage_columns = ["summary_only_runs"]
    writer.writerow(prefix + scope_columns + coverage_columns + columns)
    for profile, view in views:
        scope = view["scope"]
        scope_values = [profile.project_id, scope["timezone"], scope["granularity"],
                        scope["mode"], scope["from"], scope["to"]]
        for row in view["jobs"] if kind == "jobs-usage" else view["daily"]:
            if kind == "jobs-usage":
                projected = {"run_id": row["run_id"], "source": row["source"],
                             **{f"{period}_{field}": row[period][field]
                                for period in ("lifetime", "in_period", "unallocated")
                                for field in fields}}
            else:
                projected = {**row}
                if kind == "metrics" and admin:
                    projected["reported_cost_usd"] = projected["cost_usd"]
            values = [projected[key] for key in columns]
            values = [_csv_text(v) if isinstance(v, str) else v for v in values]
            writer.writerow(([_csv_text(profile.name), _csv_text(profile.repo)]
                             if global_view else []) + scope_values
                            + [view["coverage"].get(key, 0) for key in coverage_columns] + values)
    scopes = [v["scope"] for _, v in views]
    if not scopes and empty_scope is not None:
        scopes = [empty_scope.public("") | {"project_ids": []}]
    label = "global" if global_view else views[0][0].name
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             f'attachment; filename="adore-{label}-{kind}.csv"',
                             "X-ADORE-Scope": json.dumps(scopes),
                             "X-ADORE-Coverage": json.dumps([v["coverage"] for _, v in views])})


def _usage_csv(views: list[tuple[object, dict]], admin: bool, global_view: bool,
               empty_scope: analytics.Scope | None = None) -> Response:
    """@brief Export attributed consumption using the common scope formatter."""
    return _analytical_csv(views, admin, global_view, "usage", empty_scope)


def _configured_summaries(
    profiles: ProfileStore, profile, store: StateStore,
) -> list[metrics.RunSummary]:
    """
    @brief      Read analytical summaries from the same configured path as CLI.
    @param[in]  profiles Profile configuration owner.
    @param[in]  profile Authorized project identity.
    @param[in]  store Historical state owner for metadata-only profiles.
    @return     Validated summaries without creating or modifying the database.
    @exception  metrics.MetricsError Unreadable or malformed configuration/evidence.
    @note       Relative paths use the process working folder, matching CLI.
                Metadata-only profiles retain their existing state-root history.
    """
    path = profiles.config_path(profile.name)
    try:
        config = load_config(path)
        declared = config.raw.get("metrics", {})
        if not isinstance(declared, dict) or not isinstance(declared.get("db_path", ""), str):
            raise ValueError("invalid statistics database declaration")
        database = config.metrics.db_path
        if not isinstance(database, str) or not database.strip() or "\0" in database:
            raise ValueError("invalid statistics database path")
    except FileNotFoundError as exc:
        if path.is_symlink():
            raise metrics.MetricsError("statistics configuration unavailable") from exc
        database = store.root / "metrics.db"
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise metrics.MetricsError("statistics configuration invalid") from exc
    return metrics.load_analytical_summaries(database)


def _metric_view(profiles: ProfileStore, profile, admin: bool,
                 web: WebStore, day_from: date | None = None,
                 day_to: date | None = None, timezone: str = "UTC",
                 granularity: Literal["day", "week", "month"] = "day") -> dict:
    """@brief Return one authorized half-open analytical scope and current stock."""
    try:
        scope = analytics.Scope.create(day_from, day_to, timezone, granularity)
        store, sources, prices = _analytics_sources(profiles, profile, web, admin)
        summaries = _configured_summaries(profiles, profile, store)
        return analytics.metric_report(sources, summaries, profile.project_id,
                                        scope, prices, admin)
    except metrics.MetricsError as exc:
        raise _error(503, "metrics_corrupt") from exc
    except analytics.AnalyticsError as exc:
        code = "metrics_corrupt" if exc.code == "usage_corrupt" else exc.code
        raise _error(exc.status, code) from exc


def _run_view(run) -> dict:
    try:
        parsed_mr_url = urlsplit(run.mr_url)
        mr_url = (run.mr_url if parsed_mr_url.scheme in ("http", "https")
                  and parsed_mr_url.hostname and not parsed_mr_url.username
                  and not parsed_mr_url.password else "")
    except ValueError:
        mr_url = ""
    return {
        "run_id": run.run_id, "ticket_iid": run.ticket_iid,
        "stage": run.stage, "lifecycle": run.lifecycle,
        "outcome": run.outcome, "stage_failures": run.stage_failures,
        "review_rounds": run.review_rounds, "mr_url": mr_url,
        "updated_at": run.updated_at,
    }


# PUBLIC API
def create_app(home: str | Path | None = None,
               *, probe_runner: CommandRunner = run_command) -> FastAPI:
    """
    @brief Construct the optional web service for a profile home.
    @param[in] home ADORE_HOME override used by tests and deployment.
    @param[in] probe_runner Injectable runner for explicit readiness probes.
    @return Configured FastAPI application.
    """
    profiles = ProfileStore(home)
    web = WebStore(profiles.home / "web.db")
    config_lock = Lock()
    app = FastAPI(title="ADORE", version=__version__, docs_url=None, redoc_url=None)
    app.state.web_store = web
    app.state.profiles = profiles

    @app.exception_handler(WebStoreError)
    async def web_store_failure(_request: Request, _exc: WebStoreError) -> JSONResponse:
        """@brief Expose corrupt identity/grant evidence as a typed service error."""
        return JSONResponse(status_code=503,
                            content={"detail": {"code": "web_store_corrupt"}})

    @app.exception_handler(JobReadError)
    async def job_read_failure(_request: Request, exc: JobReadError) -> JSONResponse:
        """@brief Return typed job failures without exposing source values or partial totals."""
        return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code}})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """@brief Report schema failures with one code and field-level reasons."""
        issues = [_finding("invalid_request_field",
                           ".".join(str(part) for part in item.get("loc", ())[1:]),
                           "Supply this field using its documented type and allowed values.")
                  for item in exc.errors()]
        detail = {"code": "invalid_request", "message": _validation_message(exc)}
        setup_paths = {"/api/v1/projects", "/api/v1/projects/setup-preview",
                       "/api/v1/projects/id-availability", "/api/v1/projects/import-preview",
                       "/api/v1/projects/import", "/api/v1/projects/import-check",
                       "/api/v1/projects/setup-check",
                       "/api/v1/projects/setup-create", "/api/v1/projects/transfer-source",
                       "/api/v1/projects/transfer-preview", "/api/v1/projects/transfer-check",
                       "/api/v1/projects/transfer-create"}
        if _request.url.path in setup_paths or _request.url.path.endswith("/identity"):
            detail["issues"] = issues
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(StarletteHTTPException)
    async def coded_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """@brief Keep coded errors and give framework text errors a stable code."""
        detail = exc.detail
        if not (isinstance(detail, dict) and isinstance(detail.get("code"), str)):
            detail = {"code": _HTTP_ERROR_CODES.get(exc.status_code, _HTTP_FALLBACK_CODE),
                      "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail},
                            headers=getattr(exc, "headers", None))

    def account_principal(request: Request) -> dict:
        """@brief Resolve the session for routes that manage the account itself."""
        user = web.session_user(request.cookies.get(_COOKIE, ""))
        if user is None:
            raise _error(401, "authentication_required")
        return user

    def principal(user: Annotated[dict, Depends(account_principal)]) -> dict:
        """@brief Admit an account that has no outstanding required password change."""
        if user["password_change_required"]:
            raise _error(403, "password_change_required")
        return user

    def _require_csrf(request: Request, user: dict) -> dict:
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(csrf, user["csrf"]):
            raise _error(403, "csrf_required")
        return user

    def account_mutation(request: Request,
                         user: Annotated[dict, Depends(account_principal)]) -> dict:
        """@brief CSRF-protected change to the signed-in account itself."""
        return _require_csrf(request, user)

    def mutation(request: Request, user: Annotated[dict, Depends(principal)]) -> dict:
        return _require_csrf(request, user)

    def administrator(user: Annotated[dict, Depends(principal)]) -> dict:
        if user["role"] != "admin":
            raise _error(403, "admin_required")
        return user

    def admin_mutation(user: Annotated[dict, Depends(mutation)]) -> dict:
        if user["role"] != "admin":
            raise _error(403, "admin_required")
        return user

    def project(name: str, user: dict):
        name = _profile_name(name)
        try:
            named = profiles.load(name) if profiles.exists(name) else None
            identified = profiles.find_by_id(name) if len(name) == 32 else None
            if (named is not None and identified is not None
                    and named.project_id != identified.project_id):
                raise _error(503, "project_identity_ambiguous")
            item = identified or named
        except ProfileError as exc:
            raise _error(503, "project_corrupt") from exc
        if item is None or (user["role"] != "admin"
                            and item.name not in web.memberships(user["id"])):
            raise _error(404, "project_not_found")
        return item

    @contextmanager
    def guard_direct_config_apply(item, path: Path, key: str):
        """@brief Keep direct API edits behind the conductor's safe boundary."""
        try:
            current = load_config(path)
        except (OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        if (item.store_root and Path(item.store_root).resolve()
                != Path(current.state.store_root).resolve()):
            raise _error(409, "unmanaged_state_root")
        state = StateStore(
            item.store_root or profiles.default_store_root(item.name),
            current.agent.slug,
        )
        if not state.acquire_lock():
            raise _error(409, "project_has_active_work")
        try:
            if (_read_pending_config(profiles.profile_dir(item.name)
                                     / "pending_config.json") is not None
                    or state.invalid_runs()
                    or any(run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
                           for run in state.list_runs())
                    or web.has_unfinished_operations(item.name)
                    or _restart_required(key) and not state.is_paused()):
                raise _error(409, "project_has_active_work")
            yield
        finally:
            state.release_lock()

    @app.get("/api/v1/health")
    def health() -> dict:
        """@brief Report that the API process is serving HTTP requests."""
        return {"status": "alive"}

    @app.get("/api/v1/ready")
    def ready() -> dict:
        """@brief Require a recent control-worker heartbeat for readiness."""
        if not web.worker_ready():
            raise _error(503, "worker_unavailable")
        return {"status": "ready", "worker": "ready"}

    @app.get("/api/v1/system/storage")
    def storage_status(_user: Annotated[dict, Depends(administrator)]) -> dict:
        """
        @brief Report low free space on the home and project-state volumes.
        @return Administrator-only volume measurements and alert status.
        @exception HTTPException When profile or disk evidence cannot be read.
        """
        try:
            if profiles.invalid_profiles():
                raise _error(503, "project_corrupt")
            targets = [("home", None, profiles.home)] + [
                ("project", item.name,
                 Path(item.store_root or profiles.default_store_root(item.name)))
                for item in profiles.list_profiles()
            ]
            volumes = []
            for scope, name, target in targets:
                path = target.resolve()
                while not path.exists() and path != path.parent:
                    path = path.parent
                reading = shutil.disk_usage(path)
                if reading.total <= 0 or reading.free < 0 or reading.free > reading.total:
                    raise ValueError("invalid disk capacity")
                volumes.append({"scope": scope, "project": name,
                                "free_bytes": reading.free,
                                "total_bytes": reading.total,
                                "low": reading.free < _LOW_STORAGE_BYTES,
                                "volume_id": str(path.stat().st_dev)})
        except HTTPException:
            raise
        except (OSError, ValueError, ProfileError) as exc:
            raise _error(503, "storage_check_failed") from exc
        return {"threshold_bytes": _LOW_STORAGE_BYTES,
                "low": any(item["low"] for item in volumes), "volumes": volumes}

    @app.get("/api/v1/about")
    def about() -> dict:
        license_path = _STATIC / "LICENSE.txt"
        notices_path = _STATIC / "THIRD_PARTY_NOTICES.md"
        try:
            release_notes = load_release_notes()
        except (OSError, UnicodeError, ReleaseNotesError):
            # About stays available; the repository check guards the file's content. Standard
            # logging (stderr via the last-resort handler) suffices for this one server warning.
            logging.getLogger("adore.web").warning("release notes unavailable", exc_info=True)
            release_notes = []
        return {"name": "ADORE", "version": __version__, "release_notes": release_notes,
                "license": "PolyForm Noncommercial License 1.0.0",
                "license_text": license_path.read_text(encoding="utf-8")
                if license_path.is_file() else "",
                "third_party_notices": notices_path.read_text(encoding="utf-8")
                if notices_path.is_file() else ""}

    @app.post("/api/v1/session")
    def login(body: Credentials, response: Response, request: Request) -> dict:
        client = request.client.host if request.client else "unknown"
        if not web.allow_login(body.username, client):
            raise _error(429, "login_rate_limited")
        user = web.authenticate(body.username, body.password)
        if user is None:
            web.record_login(body.username, client, success=False)
            raise _error(401, "invalid_credentials")
        web.record_login(body.username, client, success=True)
        token, csrf = web.create_session(user["id"])
        response.set_cookie(_COOKIE, token, httponly=True, secure=request.url.scheme == "https",
                            samesite="strict", max_age=43200, path="/")
        web.audit(user["id"], "login")
        return {"user": user, "csrf": csrf}

    @app.get("/api/v1/me")
    def me(user: Annotated[dict, Depends(account_principal)]) -> dict:
        return {"user": {key: value for key, value in user.items() if key != "csrf"},
                "csrf": user["csrf"]}

    @app.get("/api/v1/me/preferences")
    def get_preferences(user: Annotated[dict, Depends(account_principal)]) -> dict:
        """@brief Return saved preferences for the authenticated account."""
        try:
            return web.preferences(user["id"])
        except WebStoreError as exc:
            raise _error(503, "preferences_corrupt") from exc

    @app.patch("/api/v1/me/preferences")
    def update_preferences(body: PreferenceInput,
                           user: Annotated[dict, Depends(account_mutation)]) -> dict:
        """@brief Save a validated language or theme for the current account."""
        try:
            return web.set_preferences(user["id"], body.model_dump(exclude_unset=True))
        except WebStoreError as exc:
            if str(exc) == "invalid account preferences":
                raise _error(422, "invalid_preferences") from exc
            raise _error(503, "preferences_corrupt") from exc

    @app.delete("/api/v1/session")
    def logout(request: Request, response: Response,
               user: Annotated[dict, Depends(account_mutation)]) -> dict:
        web.revoke_session(request.cookies.get(_COOKIE, ""))
        response.delete_cookie(_COOKIE, path="/")
        web.audit(user["id"], "logout")
        return {"ok": True}

    @app.post("/api/v1/me/password")
    def change_password(body: PasswordChange,
                        user: Annotated[dict, Depends(account_mutation)]) -> dict:
        try:
            web.change_password(user["id"], body.current, body.replacement, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(400, exc) from exc
        return {"ok": True}

    @app.get("/api/v1/users")
    def users(_user: Annotated[dict, Depends(administrator)]) -> list[dict]:
        return [{**account, "projects": sorted(web.memberships(account["id"])),
                 "project_ids": web.membership_ids(account["id"])}
                for account in web.list_users()]

    @app.get("/api/v1/audit")
    def audit_history(_user: Annotated[dict, Depends(administrator)],
                      limit: str = "100") -> list[dict]:
        if limit == "all":
            return web.recent_audit(None)
        if (len(limit) > 3 or not limit.isascii() or not limit.isdecimal()
                or not 1 <= int(limit) <= 500):
            raise _error(422, "invalid_audit_limit")
        return web.recent_audit(int(limit))

    @app.get("/api/v1/audit-page")
    def audit_page(
        user: Annotated[dict, Depends(principal)],
        limit: str = "25",
        offset: Annotated[int, Query(ge=0, le=2**63 - 1)] = 0,
        actor_id: Annotated[int | None, Query(ge=1, le=2**63 - 1)] = None,
        project_id: str | None = None,
        action: str | None = None,
        from_time: Annotated[str | None, Query(alias="from")] = None,
        to_time: Annotated[str | None, Query(alias="to")] = None,
    ) -> dict:
        """@brief Filter/count authorized stable-project evidence before SQL paging."""
        if user["role"] != "admin":
            if project_id is None:
                raise _error(403, "admin_required")
            # Return the same denial for malformed, missing or unassigned identity.
            if project_id not in web.membership_ids(user["id"]):
                raise _error(403, "project_not_found")
        if limit == "all":
            size = None
        elif (
            len(limit) > 3
            or not limit.isascii()
            or not limit.isdecimal()
            or not 1 <= int(limit) <= 100
        ):
            raise _error(422, "invalid_audit_limit")
        else:
            size = int(limit)
        try:
            items, total = web.audit_page(
                size,
                offset,
                actor_id=actor_id,
                project_id=project_id,
                action=action,
                from_time=from_time,
                to_time=to_time,
                project_reader=user["role"] != "admin",
            )
        except WebStoreError as exc:
            if str(exc).startswith("invalid audit"):
                raise _error(422, "invalid_request") from exc
            raise
        return {"items": items, "total": total, "limit": size, "offset": offset}

    @app.get("/api/v1/audit-policy")
    def get_audit_policy(_user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Return persisted audit limits; null means unlimited."""
        return web.audit_policy()

    @app.put("/api/v1/audit-policy")
    def update_audit_policy(
        body: AuditPolicyInput, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Apply administrator limits and record the policy change."""
        result = web.set_audit_policy(body.retention_days, body.max_bytes, actor_id=user["id"])
        return result

    @app.post("/api/v1/users/with-access")
    def add_user_with_access(body: UserWithAccess,
                             user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Create exactly the reviewed account/grants in one transaction."""
        with config_lock:
            try:
                return web.create_user_with_access(
                    body.username, body.password, body.role, body.project_ids,
                    body.allow_no_projects, user["id"],
                )
            except WebStoreError as exc:
                codes = {
                    "invalid grants": (400, "invalid_request"),
                    "project archived": (400, "project_archived"),
                    "project changed during the update": (409, "project_changed"),
                    "administrator required": (403, "admin_required"),
                    "project metadata is corrupt": (503, "project_corrupt"),
                    "duplicate project identity": (503, "project_corrupt"),
                    "user creation storage failed": (503, "request_rejected"),
                    "audit policy is corrupt": (503, "web_store_corrupt"),
                    "audit policy is missing": (503, "web_store_corrupt"),
                    "audit row is corrupt": (503, "web_store_corrupt"),
                }
                if str(exc) in codes:
                    status, code = codes[str(exc)]
                    raise _error(status, code) from exc
                raise _store_error(400, exc) from exc

    @app.post("/api/v1/users")
    def add_user(body: NewUser, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            created = web.create_user(body.username, body.password, body.role, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(400, exc) from exc
        return created

    @app.put("/api/v1/users/{user_id}/projects")
    def assign(
        user_id: int, body: Memberships, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        for name in body.projects:
            _profile_name(name)
            try:
                profiles.load(name)
            except ProfileError as exc:
                raise _error(404, "project_not_found") from exc
        try:
            web.set_memberships(user_id, body.projects, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(404, exc) from exc
        return {"projects": sorted(set(body.projects))}

    @app.get("/api/v1/projects/{name}/access")
    def project_access(name: str, user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Every developer account and whether it can access the project."""
        item = project(name, user)
        try:
            members = web.project_members(item.name)
        except WebStoreError as exc:
            raise _store_error(404, exc) from exc
        return {"developers": [
            {"id": account["id"], "username": account["username"],
             "disabled": account["disabled"], "granted": account["id"] in members}
            for account in web.list_users() if account["role"] == "developer"
        ]}

    @app.put("/api/v1/projects/{name}/access/{user_id}")
    def change_project_access(
        name: str, user_id: int, body: AccessChange, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Grant or remove one developer's access to this project only."""
        item = project(name, user)
        account = web.user_by_id(user_id)
        if account is None:
            raise _error(404, "user_not_found")
        if account["role"] != "developer":
            raise _error(400, "user_not_developer")
        try:
            web.set_membership(user_id, item.name, body.granted, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(
                409 if str(exc) == "project changed during the update" else 404, exc
            ) from exc
        return {"id": user_id, "granted": body.granted}

    @app.post("/api/v1/users/{user_id}/disable")
    def disable(user_id: int, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            web.disable_user(user_id, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(409, exc) from exc
        return {"ok": True}

    @app.post("/api/v1/users/{user_id}/enable")
    def enable(user_id: int, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            web.enable_user(user_id, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(404, exc) from exc
        return {"ok": True}

    @app.post("/api/v1/users/{user_id}/reset-password")
    def reset_password(
        user_id: int, body: PasswordReset, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        try:
            web.reset_password(user_id, body.replacement, actor_id=user["id"])
        except WebStoreError as exc:
            raise _store_error(404 if "not found" in str(exc) else 400, exc) from exc
        return {"ok": True}

    @app.get("/api/v1/projects")
    def list_projects(
        user: Annotated[dict, Depends(principal)],
        q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        state: Literal["configured", "needs-config", "paused", "archived",
                       "invalid-state"] | None = None,
    ) -> list[dict]:
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        needle = q.strip().casefold() if q is not None else None
        if needle == "":
            raise _error(422, "invalid_project_search")
        allowed = None if user["role"] == "admin" else web.memberships(user["id"])
        visible = []
        for item in profiles.list_profiles():
            if not _PROFILE_RE.fullmatch(item.name) or (
                allowed is not None and item.name not in allowed
            ):
                continue
            view = _profile_view(profiles, item)
            if needle is not None and not any(
                needle in view[key].casefold()
                for key in ("name", "description", "repo")
            ):
                continue
            if state is not None and view["readiness"] != state:
                continue
            visible.append(view)
        return visible

    @app.post("/api/v1/projects/id-availability")
    def id_availability(body: ProfileIDInput,
                        _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Check a portable ID without reserving or creating a project."""
        try:
            available = profiles.id_availability(body.name)
        except ProfileError as exc:
            raise _identity_error(exc) from exc
        return {"name": body.name, "available": available,
                "issues": [] if available else [
                    _finding("project_exists", "name", "Choose another available ID.")]}

    @app.post("/api/v1/projects/{name}/labels/ensure")
    def ensure_project_labels(name: str,
                              user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """
        @brief Create the project's missing ADORE labels in its repository.
        @details Reads the repository's labels once and creates only the missing ones;
                 existing labels are never changed. Per-label failures are reported.
        """
        item = project(name, user)
        config = ticket_config(item)
        forge = ticket_forge(item, config)
        # Same failure mapping as ticket reads: malformed data 502, unavailable forge 503.
        report = ticket_read(lambda: ensure_labels(forge, project_labels(config)))
        web.audit(user["id"], "labels-ensured", item.name,
                  f"created={len(report['created'])} existing={len(report['existing'])} "
                  f"failed={len(report['failed'])}")
        return report

    @app.get("/api/v1/executor-images")
    def executor_images(runtime: Literal["docker", "podman"],
                        _user: Annotated[dict, Depends(administrator)]) -> dict:
        """
        @brief Tagged container images on the ADORE server, for image suggestions.
        @details Read-only and bounded; a runtime that cannot be queried is reported
                 as unavailable rather than as an error.
        """
        result = probe_runner([runtime, "images", "--format", "{{.Repository}}:{{.Tag}}"],
                              timeout=_IMAGE_LIST_TIMEOUT)
        if not result.ok:
            return {"runtime": runtime, "available": False, "images": []}
        images = {line.strip() for line in result.stdout.splitlines()}
        return {"runtime": runtime, "available": True, "images": sorted(
            image for image in images if image and "<none>" not in image
            and len(image) <= 255)[:_IMAGE_LIST_LIMIT]}

    @app.post("/api/v1/projects/repository-source")
    def repository_source(body: RepositorySourceInput,
                          _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """
        @brief      Read a repository address: forge, repository, branch, ID and clone location.
        @param[in]  body Repository URL typed by the administrator.
        @param[in]  _user Authorized administrator after CSRF validation.
        @return     Detected values for confirmation; nothing is written on the server.
        @exception  HTTPException Unsupported address, unreachable remote or no free ID.
        """
        try:
            parsed = parse_repository_url(body.url)
        except RepositorySourceError as exc:
            raise _error(400, "repository_url_invalid") from exc
        listing = ls_remote(parsed.url, probe_runner)
        if not listing.ok:
            raise _error(502, "repository_unreachable")
        kind, login = detect_kind(parsed.host, tea_logins(probe_runner))

        def location(name: str) -> Path:
            return (profiles.home / "repos" / name).resolve()

        def usable(name: str) -> bool:
            # Free, unreserved ID whose clone location is empty or already holds this repository.
            path = location(name)
            try:
                available = profiles.id_availability(name)
            except ProfileError:
                return False
            return available and (
                not path.exists() or origin_matches(read_origin(path) or "", parsed.url))

        try:
            name = suggest_id(parsed.name, usable)
        except (RepositorySourceError, ProfileError) as exc:
            raise _error(409, "project_exists") from exc
        path = location(name)
        return {"url": parsed.url, "kind": kind, "login": login, "repo": parsed.repo,
                "default_branch": default_branch(listing.stdout), "name": name,
                "display_name": parsed.name, "repo_path": str(path),
                "clone": "existing" if path.exists() else "new"}

    @app.post("/api/v1/projects/setup-preview")
    def preview_project_setup(
        body: ProjectInput, _user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Validate setup locally without commands or profile publication."""
        preview, _candidate = _prepare_project(profiles, body)
        web.audit(
            _user["id"],
            "enrollment-prepared",
            phase="prepare",
            result="prepared",
            resource_type="project",
            resource_id=body.name,
            candidate_revision=preview.get("config_revision"),
        )
        return preview

    def transfer_source(body: TransferSourceInput, request: Request) -> dict:
        """
        @brief      Reauthorize and strictly read exact file or active project bytes.
        @param[in]  body Closed source selection; project input uses immutable identity.
        @param[in]  request Session/CSRF authority rechecked at every boundary.
        @return     Allowlisted rules and exact source revision only.
        @exception  HTTPException Missing, changed, incompatible or corrupt source.
        """
        user = admin_mutation(mutation(request, principal(account_principal(request))))
        if ((body.method == "file" and (body.file_text is None or body.source_id is not None))
                or (body.method == "project"
                    and (body.source_id is None or body.file_text is not None))):
            raise _error(400, "portable_settings_invalid")
        try:
            if body.method == "file":
                raw = body.file_text.encode("utf-8")
                settings = parse_settings(raw)
                revision = sha256(raw).hexdigest()
            else:
                item = project(body.source_id, user)
                with profiles.config_path(item.name).open("rb") as source:
                    raw = source.read(MAX_SOURCE_BYTES + 1)
                settings = parse_settings(export_settings(raw))
                if project(body.source_id, user).project_id != item.project_id:
                    raise _error(409, "portable_settings_changed")
                revision = sha256((item.project_id + sha256(raw).hexdigest()).encode()).hexdigest()
        except PortableSettingsError as exc:
            raise _error(400, exc.code) from exc
        except (OSError, UnicodeError) as exc:
            raise _error(503, "portable_settings_invalid") from exc
        return {"source_revision": revision, "settings": settings}

    @app.post("/api/v1/projects/transfer-source")
    def preview_transfer_source(body: TransferSourceInput, request: Request,
                                _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Review only recognized portable rules without target writes or probes."""
        return transfer_source(body, request)

    def prepare_transfer(body: TransferInput, request: Request):
        """@brief Bind an exact source to freshly supplied independent target setup."""
        source = transfer_source(body, request)
        if not secrets.compare_digest(body.source_revision, source["source_revision"]):
            raise _error(409, "portable_settings_changed")
        return _prepare_transfer(profiles, body, source["settings"])

    @app.post("/api/v1/projects/transfer-preview")
    def preview_transfer(
        body: TransferInput, request: Request, _user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Return target rules/mapping and canonical validated review without writes."""
        preview, _candidate = prepare_transfer(body, request)
        web.audit(
            _user["id"],
            "clone-prepared" if body.method == "project" else "settings-import-prepared",
            phase="prepare",
            result="prepared",
            resource_type="project",
            resource_id=body.target.name,
            base_revision=body.source_revision,
            candidate_revision=preview.get("config_revision"),
        )
        return preview

    def reviewed_transfer(body: ReviewedTransferInput, request: Request):
        """@brief Reject invalid, duplicate or changed source/target confirmation."""
        preview, candidate = prepare_transfer(body, request)
        if not preview["structural_valid"] or candidate is None:
            duplicate = any(issue["code"] == "project_exists" for issue in preview["issues"])
            raise HTTPException(status_code=409 if duplicate else 400, detail={
                "code": "project_exists" if duplicate else "project_setup_invalid",
                "issues": preview["issues"]})
        if not secrets.compare_digest(body.revision, preview["revision"]):
            raise _error(409, "portable_settings_changed")
        return preview, candidate

    @app.post("/api/v1/projects/transfer-check")
    def check_transfer(body: ReviewedTransferInput, request: Request,
                       _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly probe exact target; reread authorization/source after probes."""
        preview, candidate = reviewed_transfer(body, request)
        evidence = _probe_setup(_config_from_bytes(candidate.document.encode()), probe_runner)
        reviewed_transfer(body, request)
        checks = evidence["checks"]
        if _pending_clone(body.target):
            checks["aegis_files"] = "not-checked"  # The clone is made at creation.
        status = ("failed" if any(value is False for value in checks.values()) else
                  "partial" if any(type(value) is not bool for value in checks.values())
                  else "verified")
        return {**evidence, "status": status, "revision": preview["config_revision"],
                "draft_revision": preview["revision"], "context": "api-host",
                "checked_at": datetime.now(UTC).isoformat()}

    @app.post("/api/v1/projects/transfer-create")
    def create_transfer(body: ReviewedTransferInput, request: Request,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Atomically publish fresh stopped target with source/role rechecks."""
        _preview, candidate = reviewed_transfer(body, request)
        config = _config_from_bytes(candidate.document.encode())

        def recheck() -> None:
            """@brief Reauthorize/reinspect source and independent ownership before visibility."""
            source = transfer_source(body, request)
            if not secrets.compare_digest(body.source_revision, source["source_revision"]):
                raise _error(409, "portable_settings_changed")
            _transfer_paths(profiles, config, body.target.name, own_target=True)

        def publish() -> dict:
            return _publish_paused(profiles, web, user["id"], body.target.name,
                                   candidate.document.encode(), candidate.metadata, recheck=recheck,
                                   origin="project-cloned" if body.method == "project"
                                   else "settings-imported", base_revision=body.source_revision)

        def locked() -> dict:
            if body.method == "project":
                item = project(body.source_id, user)
                with _web_config_edit_lock(profiles.config_path(item.name)):
                    return publish()
            return publish()

        return _publish_with_clone(body.target, probe_runner, profiles.home, locked)

    def reviewed_setup(body: ReviewedProjectInput):
        """@brief Rebuild and compare an exact memory draft before acting on it.

        @param[in] body Secret-free reviewed answers and candidate revision.
        @return Structurally valid preview and exact wizard candidate.
        @exception HTTPException Invalid, duplicate or stale setup fails closed.
        """
        preview, candidate = _prepare_project(profiles, body)
        if not preview["structural_valid"] or candidate is None:
            duplicate = any(issue["code"] == "project_exists" for issue in preview["issues"])
            raise HTTPException(status_code=409 if duplicate else 400,
                                detail={"code": ("project_exists" if duplicate else
                                                 "project_setup_invalid"),
                                        "issues": preview["issues"]})
        if not secrets.compare_digest(body.revision, preview["revision"]):
            raise _error(409, "stale_config_revision")
        return preview, candidate

    @app.post("/api/v1/projects/setup-check")
    def check_project_setup(body: ReviewedProjectInput,
                            _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly probe a reviewed draft without storing or publishing it.

        @param[in] body Reviewed answers and candidate revision.
        @param[in] _user Authorized administrator after CSRF validation.
        @return Redacted checks, status, time and exact draft/config revisions.
        @exception HTTPException Setup or probe failure is returned deterministically.
        """
        preview, candidate = reviewed_setup(body)
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        evidence = _probe_setup(config, probe_runner)
        checks = evidence["checks"]
        if _pending_clone(body):
            checks["aegis_files"] = "not-checked"  # The clone is made at creation.
        status = ("failed" if any(value is False for value in checks.values()) else
                  "partial" if any(type(value) is not bool for value in checks.values())
                  else "verified")
        return {**evidence, "status": status, "revision": preview["config_revision"],
                "draft_revision": preview["revision"], "context": "api-host",
                "checked_at": datetime.now(UTC).isoformat()}

    @app.post("/api/v1/projects/setup-create")
    def create_reviewed_project(body: ReviewedProjectInput,
                                user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Publish only the exact reviewed configuration with pickup stopped.

        @param[in] body Reviewed answers and candidate revision.
        @param[in] user Authorized administrator recorded in the audit.
        @return Complete project whose pickup is already stopped.
        @exception HTTPException Invalid, stale or conflicting setup is rejected.
        """
        _preview, candidate = reviewed_setup(body)
        return _publish_with_clone(body, probe_runner, profiles.home, lambda: _publish_paused(
            profiles, web, user["id"], body.name, candidate.document.encode("utf-8"),
            candidate.metadata))

    @app.post("/api/v1/projects")
    def add_project(body: ProjectInput,
                    user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        preview, candidate = _prepare_project(profiles, body)
        if not preview["structural_valid"] or candidate is None:
            duplicate = any(issue["code"] == "project_exists" for issue in preview["issues"])
            code = "project_exists" if duplicate else "project_setup_invalid"
            raise HTTPException(status_code=409 if code == "project_exists" else 400,
                                detail={"code": code, "issues": preview["issues"],
                                        "message": "; ".join(issue["remediation"]
                                                             for issue in preview["issues"])})
        return _publish_with_clone(body, probe_runner, profiles.home, lambda: _publish_paused(
            profiles, web, user["id"], body.name, candidate.document.encode("utf-8"),
            candidate.metadata))

    @app.post("/api/v1/projects/import-preview")
    def preview_project_import(
        body: ProjectImportInput,
        _user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Review an unchanged TOML import before saving it."""
        preview, _config = _inspect_project_import(profiles, body)
        web.audit(
            _user["id"],
            "toml-import-prepared",
            phase="prepare",
            result="prepared",
            resource_type="project",
            resource_id=body.name,
            candidate_revision=preview.get("revision"),
        )
        return preview

    @app.post("/api/v1/projects/import-check")
    def check_project_import(body: ProjectImportInput,
                             _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly probe the exact reviewed import without publishing.

        @param[in] body Exact reviewed TOML, identity and revision.
        @param[in] _user Administrator authenticated after CSRF validation.
        @return Ephemeral redacted revision/time-bound prerequisite evidence.
        @exception HTTPException Invalid/stale input or unusable probe fails closed.
        """
        preview, config = _reviewed_import(profiles, body)
        evidence = _probe_setup(config, probe_runner)
        _reviewed_import(profiles, body)
        checks = evidence["checks"]
        status = ("failed" if any(value is False for value in checks.values()) else
                  "partial" if any(type(value) is not bool for value in checks.values())
                  else "verified")
        return {**evidence, "status": status, "revision": preview["revision"],
                "config_revision": preview["config_revision"], "context": "api-host",
                "checked_at": datetime.now(UTC).isoformat()}

    @app.post("/api/v1/projects/import")
    def import_project(
        body: ProjectImportInput,
        user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Import reviewed TOML with pickup paused and history intact."""
        preview, config = _reviewed_import(profiles, body)
        return _publish_paused(profiles, web, user["id"], body.name,
                               body.config_text.encode("utf-8"), {
                                   "display_name": preview["display_name"],
                                   "description": body.description,
                                   "platform": config.platform.kind, "repo": config.platform.repo,
                                   "runtime": ("local" if config.execution.backend == "local"
                                               else config.container.runtime),
                                   "config_path": str(profiles.config_path(body.name)),
                                   "store_root": config.state.store_root,
                               }, imported=True, import_body=body)

    @app.put("/api/v1/projects/{name}/identity")
    def update_identity(name: str, body: DisplayIdentityInput,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Change only the human label while retaining every operational identity."""
        item = project(name, user)
        try:
            display = validate_display_name(body.display_name)
        except ProfileError as exc:
            raise _identity_error(exc) from exc
        with _web_config_edit_lock(profiles.config_path(item.name)):
            current = project(name, user)
            if current.project_id != item.project_id:
                raise _error(409, "project_changed")
            current.display_name = display
            profiles.save(current)
            web.audit(user["id"], "project-display-name-changed", current.name)
            return _profile_view(profiles, current)

    @app.get("/api/v1/projects/{name}/config/portable-settings")
    def portable_settings(name: str, user: Annotated[dict, Depends(administrator)],
                          download: bool = False, checksum: str | None = None) -> Response:
        """
        @brief      Export validated active portable rules after Admin authorization.
        @param[in]  name Current project name or immutable ID.
        @param[in]  user Administrator resolved before project/config access.
        @param[in]  download Add the fixed attachment filename.
        @param[in]  checksum Optional portable preview binding.
        @return     Canonical JSON bytes, never pending or redacted read data.
        @exception  HTTPException Invalid source or changed preview fails closed.
        """
        item = project(name, user)
        try:
            with profiles.config_path(item.name).open("rb") as source:
                encoded = export_settings(source.read(MAX_SOURCE_BYTES + 1))
        except (OSError, PortableSettingsError) as exc:
            raise _error(503, "portable_settings_invalid") from exc
        if project(name, user).project_id != item.project_id:
            raise _error(409, "project_changed")
        if checksum is not None and (re.fullmatch(r"[0-9a-f]{64}", checksum) is None
                or not secrets.compare_digest(checksum, json.loads(encoded)["checksum"])):
            raise _error(409, "portable_settings_changed")
        headers = {"Cache-Control": "no-store"}
        if download:
            headers["Content-Disposition"] = 'attachment; filename="adore-project-settings.json"'
        return Response(content=encoded, media_type="application/json", headers=headers)

    @app.get("/api/v1/projects/{name}")
    def project_detail(name: str, user: Annotated[dict, Depends(principal)]) -> dict:
        return _profile_view(profiles, project(name, user))

    @app.post("/api/v1/projects/{name}/repository-connection")
    def connect_repository(name: str, body: RepositoryConnectionInput,
                           user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Verify scoped forge credentials before protected idle publication."""
        with config_lock:
            item = project(name, user)
            if item.archived:
                raise _error(409, "project_archived")
            path = profiles.config_path(item.name)
            try:
                raw = path.read_bytes()
                revision = sha256(raw).hexdigest()
                config = _config_from_bytes(raw)
                if _config_findings(config):
                    raise _error(409, "invalid_config")
                with (_web_config_edit_lock(path),
                      guard_direct_config_apply(item, path, "repository.auth")):
                    verified = verify_connection(config, item.project_id, body.server, body.token,
                                                 body.allow_http, probe_runner)
                    current = project(name, user)
                    if (current.project_id != item.project_id
                            or sha256(path.read_bytes()).hexdigest() != revision):
                        raise _error(409, "stale_config_revision")
                    confirmation = web.begin_change(
                        user["id"], "repository-connected", item.name)
                    save_connection(profiles.profile_dir(item.name), verified)
                    web.audit(user["id"], "repository-connected", item.name,
                              confirmation_key=confirmation)
                    return connection_view(verified)
            except RepositoryAuthError as exc:
                status = 422 if exc.code == "repository_connection_invalid" else (
                    400 if exc.code == "repository_connection_failed" else 503)
                raise _error(status, exc.code) from exc
            except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError) as exc:
                raise _error(503, "config_corrupt") from exc

    @app.get("/api/v1/projects/{name}/executor-credentials")
    def executor_credentials_read(name: str, user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Expose private key source/presence without returning credential values."""
        with config_lock:
            item = project(name, user)
            path = profiles.config_path(item.name)
            try:
                raw = path.read_bytes()
                config = _config_from_bytes(raw)
                if _config_findings(config):
                    raise _error(409, "invalid_config")
                return {"project_id": item.project_id, "revision": sha256(raw).hexdigest(),
                        **credential_view(profiles.profile_dir(item.name), config)}
            except (OSError, ValueError, TypeError) as exc:
                raise _error(503, "executor_credentials_corrupt") from exc

    @app.put("/api/v1/projects/{name}/executor-credentials")
    @app.delete("/api/v1/projects/{name}/executor-credentials")
    def executor_credentials_write(name: str, body: ExecutorCredentialInput, request: Request,
                                   user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Atomically save/remove an approved key while the project is idle."""
        deleting = request.method == "DELETE"
        if (deleting and body.token is not None or not deleting and body.token is None):
            raise _error(400, "executor_credential_invalid")
        with config_lock:
            item = project(name, user)
            if item.archived:
                raise _error(409, "project_archived")
            path = profiles.config_path(item.name)
            try:
                with (_web_config_edit_lock(path),
                      guard_direct_config_apply(item, path, "executor.credentials")):
                    raw = path.read_bytes()
                    revision = sha256(raw).hexdigest()
                    if revision != body.revision:
                        raise _error(409, "stale_config_revision")
                    config = _config_from_bytes(raw)
                    if _config_findings(config):
                        raise _error(409, "invalid_config")
                    directory = profiles.profile_dir(item.name)
                    model_evidence(directory, config, item.project_id, revision)
                    action = ("executor-credential-removed" if deleting
                              else "executor-credential-saved")
                    confirmation = web.begin_change(user["id"], action, item.name)
                    update_credential(directory, config, body.variable, body.token)
                    (directory / "model-connection.json").unlink(missing_ok=True)
                    web.audit(user["id"], action, item.name, confirmation_key=confirmation)
                    return {"project_id": item.project_id, "revision": revision,
                            **credential_view(directory, config)}
            except ExecutorSettingsError as exc:
                code = str(exc)
                status = (400 if code == "executor_credential_invalid" else
                          409 if code == "executor_credential_external" else 503)
                raise _error(status, code) from exc
            except (OSError, ValueError, TypeError) as exc:
                raise _error(503, "executor_credentials_corrupt") from exc

    @app.post("/api/v1/projects/{name}/model-connection-test")
    def model_connection_test(name: str,
                              user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Test the configured model explicitly and persist scoped access evidence."""
        with config_lock:
            item = project(name, user)
            if item.archived:
                raise _error(409, "project_archived")
            path = profiles.config_path(item.name)
            try:
                raw = path.read_bytes()
                revision = sha256(raw).hexdigest()
                config = _config_from_bytes(raw)
                if _config_findings(config):
                    raise _error(409, "invalid_config")
                with (_web_config_edit_lock(path),
                      guard_direct_config_apply(item, path, "model.connection-test")):
                    if sha256(path.read_bytes()).hexdigest() != revision:
                        raise _error(409, "stale_config_revision")
                    directory = profiles.profile_dir(item.name)
                    binding = credential_binding(directory, config)
                    model_evidence(directory, config, item.project_id, revision)
                    result = probe_model_connection(
                        config, probe_runner, profiles.profile_dir(item.name) / ".env")
                    if (project(name, user).project_id != item.project_id
                            or sha256(path.read_bytes()).hexdigest() != revision):
                        raise _error(409, "stale_config_revision")
                    if credential_binding(directory, config) != binding:
                        raise _error(409, "stale_config_revision")
                    if (result.get("executor") != config.executor.default
                            or result.get("model") !=
                            config.executor.commands[config.executor.default].model):
                        raise ExecutorSettingsError("executor_evidence_corrupt")
                    result = {**result, "project_id": item.project_id, "revision": revision,
                              "checked_at": datetime.now(UTC).isoformat()}
                    save_model_evidence(directory, result, binding)
                    web.audit(user["id"], "model-connection-tested", item.name)
                    return result
            except (OSError, ValueError, TypeError, IsolationError) as exc:
                raise _error(503, "model_test_failed") from exc

    @app.post("/api/v1/projects/{name}/readiness-check")
    def readiness_check(name: str,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Probe selected host prerequisites on explicit admin request."""
        with config_lock:
            item = project(name, user)
            try:
                raw = profiles.config_path(item.name).read_bytes()
                revision = sha256(raw).hexdigest()
                config = _config_from_bytes(raw)
                if _config_findings(config):
                    raise _error(409, "invalid_config")
            except (OSError, AttributeError, UnicodeError, TypeError, ValueError,
                    tomllib.TOMLDecodeError) as exc:
                raise _error(503, "config_corrupt") from exc
            try:
                evidence = _probe_setup(
                    config, project_runner(profiles.profile_dir(item.name), config, probe_runner),
                    profiles.config_path(item.name).parent / ".env")
            except RepositoryAuthError as exc:
                raise _error(503, exc.code) from exc
            checks, model_probe = evidence["checks"], evidence["model_probe"]
            value = {"schema": 1, "project_id": item.project_id, "revision": revision,
                     "context": "api-host", "checked_at": datetime.now(UTC).isoformat(),
                     "checks": checks, "model_probe": model_probe}
            try:
                with _web_config_edit_lock(profiles.config_path(item.name)):
                    current = project(name, user)
                    current_revision = sha256(
                        profiles.config_path(item.name).read_bytes()).hexdigest()
                    if current.project_id != item.project_id or current_revision != revision:
                        raise _error(409, "stale_config_revision")
                    _write_pending_config(profiles.profile_dir(item.name) / "readiness.json", value)
                    web.audit(user["id"], "readiness-checked", item.name)
                    return _verification_view(profiles, current, revision)
            except OSError as exc:
                raise _contract_rejection("readiness_store_failed", "readiness",
                                          "Check local evidence storage before retrying.") from exc

    @app.post("/api/v1/projects/{name}/archive")
    def archive_project(name: str,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Stop pickup while retaining project configuration and history."""
        with config_lock:
            item = project(name, user)
            if not item.archived:
                state = _store_for(profiles, item)
                if not state.acquire_lock():
                    raise _error(409, "project_has_active_work")
                try:
                    if (state.invalid_runs()
                            or any(run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
                                   for run in state.list_runs())
                            or web.has_unfinished_operations(item.name)):
                        raise _error(409, "project_has_active_work")
                    item.archived = True
                    profiles.save(item)
                    web.audit(user["id"], "project-archived", item.name)
                finally:
                    state.release_lock()
            return _profile_view(profiles, item)

    @app.post("/api/v1/projects/{name}/restore")
    def restore_project(name: str,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Re-enable project pickup without changing retained history."""
        with config_lock:
            item = project(name, user)
            if item.archived:
                item.archived = False
                profiles.save(item)
                web.audit(user["id"], "project-restored", item.name)
            return _profile_view(profiles, item)

    def clone_view(item) -> dict:
        """@brief The removal decision for an archived project's local clone."""
        try:
            config = load_config(profiles.config_path(item.name))
            runs = _store_for(profiles, item).list_runs()
            return project_clone_decision(profiles, item.name, config, runs, probe_runner).view()
        except (OSError, ValueError, TypeError, AttributeError, tomllib.TOMLDecodeError,
                StateError):
            return {"path": "", "removable": False, "reason": "unknown"}

    @app.get("/api/v1/projects/{name}/delete-preview")
    def delete_preview(name: str, user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief What Delete project would do with the local clone of an archived project."""
        item = project(name, user)
        if not item.archived:
            raise _error(409, "project_not_archived")
        return {"clone": clone_view(item)}

    @app.post("/api/v1/projects/{name}/delete")
    def delete_project(name: str, body: ProjectDeleteInput,
                       user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """
        @brief Queue deletion of a confirmed, archived and idle project.
        @details The command worker rechecks role, archive state and identity,
                 then runs `adore profile delete <name> --force --remove-resources`
                 (plus `--remove-clone` when chosen and the clone is removable now).
        """
        item = project(name, user)
        if not item.archived:
            raise _error(409, "project_not_archived")
        if body.confirm_name != item.name:
            raise _error(422, "delete_confirmation_mismatch")
        if web.has_unfinished_operations(item.name):
            raise _error(409, "project_has_active_work")
        state = _store_for(profiles, item)
        if state.invalid_runs():
            raise _error(503, "run_state_corrupt")
        if any(run.lifecycle not in _DELETABLE_RUN_LIFECYCLES for run in state.list_runs()):
            raise _error(409, "project_has_active_work")
        if body.remove_clone and not clone_view(item)["removable"]:
            raise _error(409, "clone_not_removable")
        try:
            operation = web.enqueue(user["id"], item.name, "delete",
                                    "remove-clone" if body.remove_clone else "",
                                    body.idempotency_key)
        except WebStoreError as exc:
            raise _store_error(409, exc) from exc
        web.audit(user["id"], "project-delete-requested", item.name)
        return {"id": operation["id"], "status": operation["status"]}

    @app.get("/api/v1/projects/{name}/config")
    def config_view(name: str, user: Annotated[dict, Depends(principal)]) -> dict:
        """@brief Return redacted effective settings for an authorized project."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        try:
            raw = path.read_bytes()
            config = load_config(path)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        data = _redact_config(config.to_dict())
        data.pop("raw", None)
        if user["role"] != "admin":
            data.get("budgets", {}).pop("max_cost_usd", None)
        timeout_seconds = None
        endpoint_profile = None
        try:
            inline = json.loads(config.container.runtime_env.get(
                "OPENCODE_CONFIG_CONTENT", "{}"))
            provider = config.executor.commands["opencode"].model.partition("/")[0]
            options = inline["provider"][provider]["options"]
            auth_ref = options.get("apiKey", "")
            if auth_ref and not re.fullmatch(r"\{env:[A-Z][A-Z0-9_]{0,63}\}", auth_ref):
                raise ValueError("unsafe credential reference")
            if inline["provider"][provider].get("npm") == "@ai-sdk/openai-compatible":
                endpoint_profile = {"protocol": "openai-chat-completions",
                                    "auth_env": auth_ref[5:-1] if auth_ref else None}
            milliseconds = options.get("timeout")
            if type(milliseconds) is int and milliseconds % 1000 == 0:
                timeout_seconds = milliseconds // 1000
        except (KeyError, TypeError, ValueError):
            pass
        try:
            settings = _setting_metadata(data, raw)
        except (UnicodeError, ValueError, TypeError, tomllib.TOMLDecodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        try:
            connection = model_evidence(profiles.profile_dir(item.name), config,
                                        item.project_id, sha256(raw).hexdigest())
        except ExecutorSettingsError as exc:
            raise _error(503, "executor_evidence_corrupt") from exc
        issues = validate_config(config)
        plan = None
        if (config.execution.preparation or config.execution.backend == "local") and not issues:
            try:
                plan = public_plan(preview_plan(config, runner=probe_runner))
            except PreparationError as exc:
                issues.append(str(exc))
        local_context = None
        if config.execution.backend == "local":
            from adore.local_process import native_context

            context = native_context()
            local_context = {key: context[key] for key in ("machine", "account", "system")}
        return {"config": data, "revision": sha256(raw).hexdigest(),
                "executor_environment": {
                    "backend": config.execution.backend,
                    "image": ((plan["image"] if plan else
                               (None if config.execution.preparation else config.container.image))
                              if config.execution.backend == "container" else None),
                    "config_path": str(path.resolve()) if user["role"] == "admin" else None,
                },
                "local_execution": local_context,
                "issues": issues, "execution_plan": plan,
                "local_endpoint_timeout_seconds": timeout_seconds,
                "local_endpoint": endpoint_profile,
                "model_connection": connection if not issues else None, "settings": settings}

    @app.post("/api/v1/projects/{name}/config/branch-preview")
    def branch_preview(name: str, body: BranchPreview,
                       user: Annotated[dict, Depends(mutation)]) -> dict:
        """
        @brief Preview naming for an authorized current profile without writes.
        @param[in] name Selected profile name or immutable project identity.
        @param[in] body Bounded template/rule pair and the displayed revision.
        @param[in] user Scoped authenticated user with same-origin CSRF proof.
        @return Sample and Python rule findings bound to the inspected revision.
        @exception HTTPException Stale, corrupt or unauthorized source fails closed.
        """
        # Coordinate source/profile reads with atomic config application, also
        # on Windows where an open reader can prevent replacing the source.
        with config_lock:
            item = project(name, user)
            path = profiles.config_path(item.name)
            try:
                raw = path.read_bytes()
                if not secrets.compare_digest(sha256(raw).hexdigest(), body.revision):
                    raise _error(409, "stale_config_revision")
                config = load_config(path)
                result = branch_naming_preview(body.template, body.rule, config.agent.slug)
                if path.read_bytes() != raw or project(name, user).project_id != item.project_id:
                    raise _error(409, "stale_config_revision")
            except (OSError, ValueError, TypeError) as exc:
                raise _error(503, "config_corrupt") from exc
        return {**result, "revision": body.revision}

    @app.get("/api/v1/projects/{name}/config/raw")
    def raw_config(name: str, user: Annotated[dict, Depends(administrator)],
                   download: bool = False) -> Response:
        """
        @brief      Read the administrator's original saved TOML without redaction.
        @param[in]  name Authorized profile name or immutable project ID.
        @param[in]  user Administrator resolved before any config read.
        @param[in]  download Return the fixed config.toml attachment filename.
        @return     Exact saved UTF-8 bytes, including comments and inline secrets.
        @exception  HTTPException Corrupt, unreadable or changed source fails closed.
        @note       External credential files and environment values are not read.
        """
        item = project(name, user)
        path = profiles.config_path(item.name)
        try:
            if path.is_symlink():
                raise ValueError("linked source")
            with path.open("rb") as source:
                raw = source.read(MAX_SOURCE_BYTES + 1)
            if not raw or len(raw) > MAX_SOURCE_BYTES:
                raise ValueError("invalid source size")
            tomllib.loads(raw.decode("utf-8"))
            with path.open("rb") as source:
                unchanged = source.read(MAX_SOURCE_BYTES + 1) == raw
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            raise _error(503, "config_corrupt") from exc
        if not unchanged or project(name, user).project_id != item.project_id:
            raise _error(409, "stale_config_revision")
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        if download:
            headers["Content-Disposition"] = 'attachment; filename="config.toml"'
        return Response(content=raw, media_type="text/plain", headers=headers)

    @app.put("/api/v1/projects/{name}/config")
    def config_update(
        name: str, body: ConfigEdit, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        item = project(name, user)
        if body.key in {"executor.selection", "executor.env_keys"}:
            raise _error(409, "pending_config_required")
        endpoint_key = body.key == "container.runtime_env.OPENAI_BASE_URL"
        if (
            body.model is not None
            or body.auth_env is not None
            or body.protocol is not None
            or body.timeout_seconds is not None
            or body.ca_file is not None
        ) and not endpoint_key:
            raise _error(400, "model_requires_endpoint")
        if _external_environment_key(body.key, endpoint=endpoint_key):
            raise _error(400, "environment_managed_externally")
        if not _editable_setting_key(body.key, endpoint=endpoint_key):
            raise _error(400, "setting_not_editable")
        if body.key.startswith(("execution.", "local.")) or body.key in _CHOSEN_ENVIRONMENT_KEYS:
            raise _error(409, "pending_config_required")
        if endpoint_key:
            if body.ca_file and (
                not body.value.startswith("https://")
                or not body.ca_file.startswith("/")
                or ".." in Path(body.ca_file).parts
                or any(ord(char) < 32 for char in body.ca_file)
                or len(body.ca_file) > 256
            ):
                raise _error(400, "invalid_endpoint_ca")
            try:
                endpoint = urlsplit(body.value)
                valid = (
                    endpoint.scheme in ("http", "https")
                    and bool(endpoint.hostname)
                    and endpoint.username is None
                    and endpoint.password is None
                    and not endpoint.fragment
                    and not endpoint.query
                )
            except ValueError:
                valid = False
            if not valid:
                raise _error(400, "invalid_endpoint_url")
        path = profiles.config_path(item.name)
        with (
            config_lock,
            _web_config_edit_lock(path),
            guard_direct_config_apply(
                item,
                path,
                body.key,
            ),
        ):
            try:
                raw = path.read_bytes()
            except OSError as exc:
                raise _error(503, "config_corrupt") from exc
            if not secrets.compare_digest(sha256(raw).hexdigest(), body.revision):
                raise _error(409, "stale_config_revision")
            candidate: Path | None = None
            try:
                current = raw.decode("utf-8")
                if (body.key.endswith(".command")
                        and tomllib.loads(current).get("execution", {}).get("backend") == "local"):
                    raise _error(409, "pending_config_required")
                if body.key.endswith(".command") and (
                    not _valid_candidate_scalar(body.key, body.value,
                    tomllib.loads(current).get("execution", {}).get("backend", "container"))
                    or not isinstance(_value_at(tomllib.loads(current), body.key), str)
                ):
                    raise _error(400, "invalid_config")
                if endpoint_key:
                    active = load_config(path)
                    if active.executor.default != "opencode":
                        raise _error(400, "unsupported_local_endpoint_executor")
                    if body.auth_env is not None and (
                        not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", body.auth_env)
                        or body.auth_env not in active.executor.env_keys
                    ):
                        raise _error(400, "invalid_endpoint_auth_reference")
                    model = (
                        body.model
                        if body.model is not None
                        else active.executor.commands["opencode"].model
                    )
                    if body.model is not None:
                        current = _set_toml_scalar(
                            current,
                            "executor.opencode.model",
                            body.model,
                        )
                    changed = _set_endpoint(
                        current,
                        body.value,
                        model,
                        body.auth_env,
                        body.timeout_seconds,
                        body.ca_file,
                    )
                else:
                    changed = _set_candidate_value(current, body.key, body.value)
                descriptor, candidate_name = tempfile.mkstemp(
                    prefix="config.web-", suffix=".toml", dir=path.parent
                )
                os.close(descriptor)
                candidate = Path(candidate_name)
                candidate.write_bytes(changed.encode("utf-8"))  # bytes: keep line endings
                parsed = load_config(candidate)
                issues = validate_config(parsed)
                if issues:
                    raise _error(400, "invalid_config")
                if sha256(path.read_bytes()).digest() != sha256(raw).digest():
                    raise _error(409, "stale_config_revision")
                attempt = web.begin_change(
                    user["id"],
                    "config-updated",
                    item.name,
                    resource_type="config",
                    resource_id=body.key,
                    base_revision=sha256(raw).hexdigest(),
                    candidate_revision=sha256(candidate.read_bytes()).hexdigest(),
                    before={"value": _candidate_value(tomllib.loads(raw.decode()), body.key)},
                )
                candidate.replace(path)
                _sync_profile_config_identity(profiles, item, path)
                web.confirm_change(
                    attempt,
                    after={"value": _value_at(
                        tomllib.loads(path.read_text(encoding="utf-8")), body.key)},
                    detail=body.key,
                )
            except (UnicodeError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
                raise _error(400, "invalid_config") from exc
            finally:
                if candidate is not None:
                    candidate.unlink(missing_ok=True)
        return {"revision": sha256(path.read_bytes()).hexdigest()}

    @app.get("/api/v1/projects/{name}/config/pending")
    def pending_config(name: str,
                       user: Annotated[dict, Depends(administrator)]) -> dict | None:
        """@brief Show a saved candidate without returning its full TOML text."""
        item = project(name, user)
        value = _read_pending_config(profiles.profile_dir(item.name) / "pending_config.json")
        if value is None:
            return None
        try:
            active_text = profiles.config_path(item.name).read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        return _public_pending_config(value, active_text=active_text)

    @app.post("/api/v1/projects/{name}/config/pending")
    def stage_config(
        name: str, body: ConfigEdit, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Save a validated candidate revision while live config stays put."""
        item = project(name, user)
        if _external_environment_key(
                body.key, endpoint=body.key == "container.runtime_env.OPENAI_BASE_URL"):
            raise _error(400, "environment_managed_externally")
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        with config_lock, _web_config_edit_lock(path):
            if _read_pending_config(pending_path) is not None:
                raise _error(409, "pending_config_exists")
            raw, changed = _candidate_config_edit(path, body)
            if sha256(path.read_bytes()).digest() != sha256(raw).digest():
                raise _error(409, "stale_config_revision")
            value = {
                "schema": 1,
                "base_revision": sha256(raw).hexdigest(),
                "candidate_revision": sha256(changed.encode("utf-8")).hexdigest(),
                "candidate_text": changed,
                "key": body.key,
                "value": body.value,
                "created_at": datetime.now(UTC).isoformat(),
                "restart_required": _restart_required(body.key),
            }
            candidate_config = _config_from_bytes(changed.encode())
            if (candidate_config.execution.preparation
                    or candidate_config.execution.backend == "local"):
                try:
                    value["execution_plan"] = preview_plan(candidate_config, runner=probe_runner)
                except PreparationError as exc:
                    raise _error(400, "execution_plan_invalid", message=str(exc)) from exc
            public = _public_pending_config(value)
            attempt = web.begin_change(
                user["id"],
                "config-staged",
                item.name,
                resource_type="config",
                resource_id=body.key,
                phase="prepare",
                base_revision=value["base_revision"],
                candidate_revision=value["candidate_revision"],
                before={"value": _value_at(tomllib.loads(raw.decode()), body.key)},
            )
            _write_pending_config(pending_path, value)
            web.confirm_change(
                attempt,
                after={"value": _candidate_value(tomllib.loads(changed), body.key)},
                detail=body.key,
            )
        return public

    @app.post("/api/v1/projects/{name}/config/apply")
    def apply_config(
        name: str, body: ConfigApply, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Apply the reviewed candidate only at a quiescent boundary."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        with config_lock, _web_config_edit_lock(path):
            pending = _read_pending_config(pending_path)
            if pending is None:
                raise _error(404, "pending_config_not_found")
            _public_pending_config(pending)
            if not secrets.compare_digest(body.base_revision, pending["base_revision"]):
                raise _error(409, "stale_config_revision")
            if not secrets.compare_digest(body.candidate_revision, pending["candidate_revision"]):
                raise _error(409, "stale_pending_revision")
            try:
                raw = path.read_bytes()
                current = load_config(path)
            except (OSError, UnicodeError, ValueError, TypeError, tomllib.TOMLDecodeError) as exc:
                raise _error(503, "config_corrupt") from exc
            current_revision = sha256(raw).hexdigest()
            _public_pending_config(pending, active_text=raw.decode("utf-8"))
            already_applied = current_revision == pending["candidate_revision"]
            if current_revision != pending["base_revision"] and not already_applied:
                raise _error(409, "stale_config_revision")
            if (
                not item.store_root
                or not Path(item.store_root).is_absolute()
                or Path(item.store_root).resolve() != Path(current.state.store_root).resolve()
            ):
                raise _error(409, "unmanaged_state_root")
            state = StateStore(item.store_root, current.agent.slug)
            if not state.acquire_lock():
                raise _error(409, "project_has_active_work")
            try:
                if (
                    state.invalid_runs()
                    or any(
                        run.lifecycle not in _TERMINAL_RUN_LIFECYCLES for run in state.list_runs()
                    )
                    or web.has_unfinished_operations(item.name)
                    or pending.get("restart_required")
                    and not state.is_paused()
                ):
                    raise _error(409, "project_has_active_work")
                candidate: Path | None = None
                attempt = web.begin_change(
                    user["id"],
                    "config-applied",
                    item.name,
                    correlation=f"config:{item.project_id}:{pending['created_at']}:{pending['candidate_revision']}",
                    resource_type="config",
                    resource_id=pending["key"],
                    base_revision=pending["base_revision"],
                    candidate_revision=pending["candidate_revision"],
                    before=(
                        {"value": _value_at(tomllib.loads(raw.decode()), pending["key"])}
                        if not already_applied
                        else None
                    ),
                )
                try:
                    if already_applied:
                        if validate_config(current):
                            raise _error(503, "config_corrupt")
                    else:
                        descriptor, candidate_name = tempfile.mkstemp(
                            prefix="config.apply-",
                            suffix=".toml",
                            dir=path.parent,
                        )
                        os.close(descriptor)
                        candidate = Path(candidate_name)
                        candidate.write_bytes(pending["candidate_text"].encode("utf-8"))
                        if validate_config(load_config(candidate)):
                            raise _error(400, "invalid_config")
                        proposed = load_config(candidate)
                        if proposed.execution.preparation or proposed.execution.backend == "local":
                            try:
                                plan = preview_plan(proposed, runner=probe_runner)
                                if plan != pending.get("execution_plan"):
                                    raise PreparationError("reviewed execution plan changed")
                            except PreparationError as exc:
                                raise _error(409, "execution_plan_stale") from exc
                        if sha256(path.read_bytes()).hexdigest() != pending["base_revision"]:
                            raise _error(409, "stale_config_revision")
                        candidate.replace(path)
                    _sync_profile_config_identity(profiles, item, path)
                    web.confirm_change(
                        attempt,
                        after={
                            "value": _value_at(
                                tomllib.loads(pending["candidate_text"]), pending["key"]
                            )
                        },
                        detail=pending["key"],
                    )
                    pending_path.unlink()
                finally:
                    if candidate is not None:
                        candidate.unlink(missing_ok=True)
            finally:
                state.release_lock()
        return {"revision": sha256(path.read_bytes()).hexdigest()}

    @app.delete("/api/v1/projects/{name}/config/pending")
    def discard_config(name: str, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly discard a staged candidate, including corrupt ones."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        with config_lock, _web_config_edit_lock(path):
            if not pending_path.is_file():
                raise _error(404, "pending_config_not_found")
            # Corrupt candidates remain explicitly discardable; do not fabricate their diff.
            attempt = web.begin_change(
                user["id"],
                "config-discarded",
                item.name,
                resource_type="config",
                resource_id="pending",
                phase="discard",
                before={"exists": True},
            )
            pending_path.unlink()
            web.confirm_change(attempt, after={"exists": False})
        return {"ok": True}

    def job_projects(user: dict, project_id: str | None = None) -> list:
        """
        @brief Select authorized history profiles before accessing run evidence.
        @param[in] user Current authenticated principal.
        @param[in] project_id Optional immutable single-project selector.
        @return All authorized selected current and archived profiles.
        """
        try:
            if project_id is not None:
                if not re.fullmatch(r"[0-9a-f]{32}", project_id):
                    raise _error(404, "project_not_found")
                return [project(project_id, user)]
            if user["role"] == "admin":
                if profiles.invalid_profiles():
                    raise JobReadError("project_corrupt")
                return profiles.list_profiles()
            return [profiles.load(name) for name in sorted(web.memberships(user["id"]))]
        except (ProfileError, OSError, UnicodeError, RecursionError) as exc:
            raise JobReadError("project_corrupt") from exc

    def job_snapshot(user: dict, project_id: str | None = None) -> tuple[list, str]:
        """
        @brief Recheck authorization/profile identity after the complete local read.
        @param[in] user Current authenticated principal.
        @param[in] project_id Optional immutable single-project selector.
        @return Complete authorized rows and optimistic source revision.
        @exception JobReadError For corrupt or changed authorized source evidence.
        """
        selected = job_projects(user, project_id)
        rows, revision = read_jobs(profiles, selected)
        if selected != job_projects(user, project_id):
            raise JobReadError("job_snapshot_changed", 409)
        return rows, revision

    @app.get("/api/v1/jobs-page")
    def jobs_page(
        user: Annotated[dict, Depends(principal)],
        project_id: str | None = None,
        q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        status_group: Literal["active", "waiting", "review", "terminal"] | None = None,
        attention: bool = False,
        limit: str = "25",
        offset: Annotated[int, Query(ge=0)] = 0,
        snapshot: Annotated[str | None, Query(pattern=r"^[0-9a-f]{64}$")] = None,
        sort: Literal["activity", "ticket", "project", "status"] = "activity",
        order: Literal["asc", "desc"] | None = None,
    ) -> dict:
        """
        @brief Globally search/order/page complete authorized local job evidence.
        @param[in] user Current authenticated principal.
        @param[in] project_id Optional immutable authorized project scope.
        @param[in] q Optional bounded case-insensitive search text.
        @param[in] status_group Optional lifecycle group.
        @param[in] attention Select jobs awaiting intervention or recovery.
        @param[in] limit Bounded page size or all.
        @param[in] offset Nonnegative matched-row offset.
        @param[in] snapshot Optional expected source-content revision.
        @param[in] sort Column ordering every matched job before paging.
        @param[in] order Direction; newest activity first, otherwise ascending, by default.
        @return Complete matched page, scoped counts and source revision.
        """
        if limit != "all" and (len(limit) > 3 or not limit.isascii() or not limit.isdecimal()
                               or not 1 <= int(limit) <= 100):
            raise _error(422, "invalid_run_limit")
        needle = q.strip().casefold() if q is not None else None
        if needle == "":
            raise _error(422, "invalid_job_search")
        rows, revision = job_snapshot(user, project_id)
        if snapshot is not None and snapshot != revision:
            raise JobReadError("job_snapshot_changed", 409)
        searched = [row for row in rows if needle is None or any(
            needle in str(row[key] or "").casefold()
            for key in ("project_name", "project_display_name", "run_id", "ticket_iid",
                        "ticket_title", "lifecycle", "stage", "outcome"))]
        counts: dict[str, int] = {}
        groups = dict.fromkeys(("active", "waiting", "review", "terminal"), 0)
        for row in searched:
            counts[row["lifecycle"]] = counts.get(row["lifecycle"], 0) + 1
            groups[row["status_group"]] += 1
        matched = [row for row in searched
                   if (status_group is None or row["status_group"] == status_group)
                   and (not attention or row["lifecycle"] in {
                       "parked-clarification", "awaiting-approval", "in-review", "failed",
                       "stale", "handoff-pending",
                   })]
        descending = (order or ("desc" if sort == "activity" else "asc")) == "desc"
        matched = sort_jobs(matched, sort, descending)
        page_limit = len(matched) if limit == "all" else int(limit)
        visible = [{key: value for key, value in row.items() if key != "timeline"}
                   for row in matched[offset:offset + page_limit]]
        return {"items": visible, "total": len(matched),
                "counts": counts, "groups": groups, "limit": page_limit, "offset": offset,
                "complete": True, "snapshot": revision,
                "snapshot_semantics": "optimistic-source-revision"}

    @app.get("/api/v1/jobs/{project_id}/{run_id}")
    def job_detail(project_id: str, run_id: str,
                   user: Annotated[dict, Depends(principal)]) -> dict:
        """
        @brief Resolve composite job identity with authorization before source reads.
        @param[in] project_id Immutable owning project identity.
        @param[in] run_id Safe run identity within that project.
        @param[in] user Current authenticated principal.
        @return One strict safe evidence model and selected-project revision.
        """
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", run_id):
            raise _error(404, "run_not_found")
        rows, revision = job_snapshot(user, project_id)
        row = next((row for row in rows if row["run_id"] == run_id), None)
        if row is None:
            raise _error(404, "run_not_found")
        return {"job": row, "complete": True, "snapshot": revision}

    @app.get("/api/v1/projects/{name}/runs")
    def runs(name: str, user: Annotated[dict, Depends(principal)]) -> list[dict]:
        item = project(name, user)
        store = _store_for(profiles, item)
        if store.invalid_runs():
            raise _error(503, "run_state_corrupt")
        return [_run_view(run) for run in store.list_runs()]

    @app.get("/api/v1/projects/{name}/runs-page")
    def runs_page(
        name: str,
        user: Annotated[dict, Depends(principal)],
        limit: str = "25",
        offset: Annotated[int, Query(ge=0)] = 0,
        lifecycle: Annotated[list[Literal[
            "working", "publishing", "awaiting-approval", "parked-clarification",
            "in-review", "done", "failed", "cancelled",
            "handoff-pending", "handed-off",
        ]] | None, Query()] = None,
        stage: Literal["frame", "specify", "design", "build", "validate"] | None = None,
        updated_from: date | None = None,
        updated_to: date | None = None,
        outcome: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        executor: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    ) -> dict:
        """@brief Return a bounded run page with scoped lifecycle and text filters."""
        item = project(name, user)
        if limit != "all" and (len(limit) > 3 or not limit.isascii() or not limit.isdecimal()
                               or not 1 <= int(limit) <= 100):
            raise _error(422, "invalid_run_limit")
        if updated_from and updated_to and updated_from > updated_to:
            raise _error(422, "invalid_date_range")
        outcome_filter = outcome.strip().casefold() if outcome is not None else None
        if outcome_filter == "":
            raise _error(422, "invalid_outcome_filter")
        if executor is not None and not executor.strip():
            raise _error(422, "invalid_executor_filter")
        store = _store_for(profiles, item)
        if store.invalid_runs():
            raise _error(503, "run_state_corrupt")
        all_runs = store.list_runs()
        counts: dict[str, int] = {}
        for run in all_runs:
            if not isinstance(run.outcome, str):
                raise _error(503, "run_state_corrupt")
            counts[run.lifecycle] = counts.get(run.lifecycle, 0) + 1
        matched = [run for run in all_runs
                   if (not lifecycle or run.lifecycle in lifecycle)
                   and (stage is None or run.stage == stage)
                   and (outcome_filter is None
                        or outcome_filter in run.outcome.casefold())]
        if executor is not None:
            observed = []
            for run in matched:
                try:
                    events = store.read_journal(run.run_id)
                except (OSError, UnicodeError) as exc:
                    raise _error(503, "run_journal_corrupt") from exc
                identities = set()
                for event in events:
                    if not isinstance(event, dict):
                        raise _error(503, "run_journal_corrupt")
                    if "executor" in event:
                        name = event["executor"]
                        if (not isinstance(name, str) or not name.strip()
                                or len(name) > 200):
                            raise _error(503, "run_journal_corrupt")
                        identities.add(name)
                if executor in identities:
                    observed.append(run)
            matched = observed
        if updated_from or updated_to:
            dated = []
            for run in matched:
                stamp = run.updated_at
                try:
                    parsed = datetime.fromisoformat(stamp)
                    if parsed.tzinfo is None or parsed.utcoffset() is None:
                        raise ValueError("naive update timestamp")
                    day = parsed.astimezone(UTC).date()
                except (TypeError, ValueError):
                    raise _error(503, "run_state_corrupt") from None
                if ((updated_from is None or day >= updated_from)
                        and (updated_to is None or day <= updated_to)):
                    dated.append(run)
            matched = dated
        matched.sort(key=lambda run: (run.updated_at, run.run_id), reverse=True)
        page_limit = len(matched) if limit == "all" else int(limit)
        return {"items": [_run_view(run) for run in matched[offset:offset + page_limit]],
                "total": len(matched), "counts": counts,
                "limit": page_limit, "offset": offset}

    @app.get("/api/v1/projects/{name}/runs/{run_id}")
    def run_detail(name: str, run_id: str,
                   user: Annotated[dict, Depends(principal)]) -> dict:
        item = project(name, user)
        if not re.fullmatch(r"[a-zA-Z0-9._-]{1,160}", run_id):
            raise _error(404, "run_not_found")
        store = _store_for(profiles, item)
        try:
            run = store.load(run_id)
        except FileNotFoundError as exc:
            raise _error(404, "run_not_found") from exc
        except StateError as exc:
            raise _error(503, "run_state_corrupt") from exc
        events = store.read_journal(run_id)
        visible = {"ts", "event", "stage", "round", "passed", "outcome", "code"}
        if user["role"] == "admin":
            visible |= {"tokens_in", "tokens_out", "cost_usd", "cost_reported",
                        "executor", "model", "review_round"}
        events = [{key: value for key, value in event.items() if key in visible}
                  for event in events]
        return {"run": _run_view(run), "events": events[-200:]}

    @app.get("/api/v1/projects/{name}/metrics")
    def project_metrics(name: str,
                        user: Annotated[dict, Depends(principal)],
                        day_from: date | None = None,
                        day_to: date | None = None,
                        timezone: Annotated[str, Query(max_length=64)] = "UTC",
                        granularity: Literal["day", "week", "month"] = "day") -> dict:
        return _metric_view(profiles, project(name, user),
                            user["role"] == "admin", web, day_from, day_to,
                            timezone, granularity)

    @app.get("/api/v1/projects/{name}/usage")
    def project_usage(
        name: str, user: Annotated[dict, Depends(principal)],
        day_from: date | None = None, day_to: date | None = None,
        executor: Annotated[str | None, Query(max_length=200)] = None,
        model: Annotated[str | None, Query(max_length=200)] = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> dict:
        """@brief Return project-scoped dated usage with observed model identity."""
        return _usage_view(profiles, project(name, user), user["role"] == "admin",
                           web, day_from, day_to, executor, model,
                           timezone, granularity)

    @app.get("/api/v1/projects/{name}/usage.csv")
    def project_usage_csv(
        name: str, user: Annotated[dict, Depends(principal)],
        day_from: date | None = None, day_to: date | None = None,
        executor: Annotated[str | None, Query(max_length=200)] = None,
        model: Annotated[str | None, Query(max_length=200)] = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> Response:
        """@brief Export the same attributed usage and role boundary as JSON."""
        item = project(name, user)
        admin = user["role"] == "admin"
        return _usage_csv([(item, _usage_view(profiles, item, admin, web,
                                              day_from, day_to, executor, model,
                                              timezone, granularity))],
                          admin, False)

    @app.get("/api/v1/projects/{name}/prices")
    def project_prices(name: str,
                       user: Annotated[dict, Depends(administrator)]) -> list[dict]:
        item = project(name, user)
        try:
            return web.list_prices(item.name)
        except WebStoreError as exc:
            raise _error(503, "price_storage_corrupt") from exc

    @app.post("/api/v1/projects/{name}/prices", status_code=201)
    def add_project_price(name: str, body: PriceInput,
                          user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        item = project(name, user)
        try:
            created = web.add_price(
                item.name, body.executor, body.model, body.effective_from,
                body.input_usd_per_million, body.output_usd_per_million,
                user["id"],
            )
        except WebStoreError as exc:
            status = 409 if "already exists" in str(exc) else 400
            raise _store_error(status, exc) from exc
        web.audit(user["id"], "price-created", item.name,
                  f'{body.executor}:{body.model}:{body.effective_from}')
        return created

    @app.get("/api/v1/projects/{name}/metrics.csv")
    def project_metrics_csv(name: str,
                            user: Annotated[dict, Depends(principal)],
                            day_from: date | None = None,
                            day_to: date | None = None,
                            timezone: Annotated[str, Query(max_length=64)] = "UTC",
                            granularity: Literal["day", "week", "month"] = "day") -> Response:
        item = project(name, user)
        admin = user["role"] == "admin"
        view = _metric_view(profiles, item, admin, web, day_from, day_to,
                            timezone, granularity)
        return _analytical_csv([(item, view)], admin, False, "metrics")

    @app.get("/api/v1/metrics.csv")
    def global_metrics_csv(
        _user: Annotated[dict, Depends(administrator)],
        day_from: date | None = None,
        day_to: date | None = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> Response:
        """@brief Export administrator daily costs with project provenance."""
        _check_reporting_scope(day_from, day_to, timezone, granularity)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        return _analytical_csv([
            (item, _metric_view(profiles, item, True, web, day_from, day_to,
                                timezone, granularity)) for item in profiles.list_profiles()
        ], True, True, "metrics",
            analytics.Scope.create(day_from, day_to, timezone, granularity))

    @app.get("/api/v1/metrics")
    def global_metrics(_user: Annotated[dict, Depends(administrator)],
                       day_from: date | None = None,
                       day_to: date | None = None,
                       timezone: Annotated[str, Query(max_length=64)] = "UTC",
                       granularity: Literal["day", "week", "month"] = "day") -> dict:
        _check_reporting_scope(day_from, day_to, timezone, granularity)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        return {item.name: _metric_view(profiles, item, True, web, day_from,
                                        day_to, timezone, granularity)
                for item in profiles.list_profiles()}

    @app.get("/api/v1/usage")
    def global_usage(
        _user: Annotated[dict, Depends(administrator)],
        day_from: date | None = None, day_to: date | None = None,
        executor: Annotated[str | None, Query(max_length=200)] = None,
        model: Annotated[str | None, Query(max_length=200)] = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> dict:
        """@brief Return attributed usage for every project to administrators."""
        _check_reporting_scope(day_from, day_to, timezone, granularity, executor, model)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        return {item.name: _usage_view(profiles, item, True, web, day_from,
                                       day_to, executor, model, timezone, granularity)
                for item in profiles.list_profiles()}

    @app.get("/api/v1/usage.csv")
    def global_usage_csv(
        _user: Annotated[dict, Depends(administrator)],
        day_from: date | None = None, day_to: date | None = None,
        executor: Annotated[str | None, Query(max_length=200)] = None,
        model: Annotated[str | None, Query(max_length=200)] = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> Response:
        """@brief Export administrator usage with project provenance."""
        _check_reporting_scope(day_from, day_to, timezone, granularity, executor, model)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        return _usage_csv([
            (item, _usage_view(profiles, item, True, web, day_from, day_to,
                               executor, model, timezone, granularity))
            for item in profiles.list_profiles()
        ], True, True, analytics.Scope.create(day_from, day_to, timezone, granularity))

    @app.get("/api/v1/projects/{name}/jobs-usage.csv")
    def project_jobs_usage_csv(
        name: str, user: Annotated[dict, Depends(principal)],
        day_from: date | None = None, day_to: date | None = None,
        executor: Annotated[str | None, Query(max_length=200)] = None,
        model: Annotated[str | None, Query(max_length=200)] = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> Response:
        """@brief Export composite job lifetime and selected-period measurements."""
        item = project(name, user)
        admin = user["role"] == "admin"
        view = _usage_view(profiles, item, admin, web, day_from, day_to,
                           executor, model, timezone, granularity)
        return _analytical_csv([(item, view)], admin, False, "jobs-usage")

    @app.get("/api/v1/jobs-usage.csv")
    def global_jobs_usage_csv(
        _user: Annotated[dict, Depends(administrator)],
        day_from: date | None = None, day_to: date | None = None,
        executor: Annotated[str | None, Query(max_length=200)] = None,
        model: Annotated[str | None, Query(max_length=200)] = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> Response:
        """@brief Export Admin job consumption with project provenance."""
        _check_reporting_scope(day_from, day_to, timezone, granularity, executor, model)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        return _analytical_csv([
            (item, _usage_view(profiles, item, True, web, day_from, day_to,
                               executor, model, timezone, granularity))
            for item in profiles.list_profiles()
        ], True, True, "jobs-usage",
            analytics.Scope.create(day_from, day_to, timezone, granularity))

    @app.post("/api/v1/usage/rebuild")
    def rebuild_usage_projection(
        user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Reconstruct append-only usage from retained journals."""
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        projects = runs = events = 0
        for item in profiles.list_profiles():
            state = _store_for(profiles, item)
            if state.invalid_runs():
                raise _error(503, "run_state_corrupt")
            projects += 1
            for run in state.list_runs():
                try:
                    projected = web.reconcile_usage(
                        item.project_id, run.run_id,
                        state.read_journal(run.run_id),
                    )
                except (WebStoreError, metrics.MetricsError) as exc:
                    raise _error(503, "usage_corrupt") from exc
                runs += 1
                events += len(projected)
        web.audit(user["id"], "usage-rebuilt", detail=f"{runs} runs")
        return {"projects": projects, "runs": runs, "usage_events": events}

    @app.post("/api/v1/projects/{name}/operations/{action}")
    def submit(name: str, action: str, body: OperationInput,
               user: Annotated[dict, Depends(mutation)]) -> dict:
        item = project(name, user)
        if item.archived:
            raise _error(409, "project_archived")
        if action not in ("start", "retry", "cancel", "pause", "resume"):
            raise _error(404, "operation_not_found")
        if action in ("pause", "resume") and user["role"] != "admin":
            raise _error(403, "admin_required")
        if action == "start":
            if body.ticket_iid is None or body.ticket_iid < 1 or body.run_id:
                raise _error(400, "ticket_required")
            target = str(body.ticket_iid)
        elif action in ("retry", "cancel"):
            if not re.fullmatch(r"[a-zA-Z0-9._-]{1,160}", body.run_id):
                raise _error(400, "run_required")
            state = _store_for(profiles, item)
            try:
                run = state.load(body.run_id)
            except FileNotFoundError as exc:
                raise _error(404, "run_not_found") from exc
            except StateError as exc:
                raise _error(503, "run_state_corrupt") from exc
            if action == "cancel" and run.lifecycle in (*_TERMINAL_RUN_LIFECYCLES,
                                                         "handoff-pending"):
                raise _error(409, "run_already_finished")
            target = body.run_id
        else:
            if body.ticket_iid is not None or body.run_id:
                raise _error(400, "unexpected_operation_target")
            target = ""
        try:
            operation = web.enqueue(user["id"], item.name, action,
                                    target, body.idempotency_key)
        except WebStoreError as exc:
            raise _store_error(409, exc) from exc
        return {"id": operation["id"], "status": operation["status"]}

    def ticket_config(item):
        """@brief Load a project's validated config for one ticket request."""
        try:
            config = _config_from_bytes(profiles.config_path(item.name).read_bytes())
        except (OSError, AttributeError, UnicodeError, TypeError, ValueError,
                tomllib.TOMLDecodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        if _config_findings(config):
            raise _error(409, "invalid_config")
        return config

    def ticket_forge(item, config):
        """@brief Build the project's bounded, credential-scoped forge for one request."""
        try:
            runner = project_runner(profiles.profile_dir(item.name), config, probe_runner)
            return open_forge(config, runner)
        except RepositoryAuthError as exc:
            raise _error(503, exc.code) from exc
        except ForgeError as exc:
            raise _error(503, "forge_read_failed") from exc

    def ticket_read(read):
        """@brief Run one forge read, mapping failures to typed API errors."""
        try:
            return read()
        except (TicketReadError, ForgeResponseError) as exc:
            raise _error(502, "forge_response_invalid") from exc
        except RunReadError as exc:
            raise _error(503, "run_state_corrupt") from exc
        except RepositoryAuthError as exc:
            raise _error(503, exc.code) from exc
        except (ForgeError, TimeoutError, OSError) as exc:
            raise _error(503, "forge_read_failed") from exc

    @app.get("/api/v1/projects/{name}/tickets")
    def project_tickets(name: str, user: Annotated[dict, Depends(principal)]) -> dict:
        """@brief Read a project's open forge tickets with pickup eligibility on request."""
        item = project(name, user)
        config = ticket_config(item)
        forge = ticket_forge(item, config)
        value = ticket_read(lambda: ticket_view(forge, config, _store_for(profiles, item)))
        return {"project_id": item.project_id, **value}

    @app.get("/api/v1/projects/{name}/tickets/{iid}/comments")
    def ticket_comments(name: str, iid: int, user: Annotated[dict, Depends(principal)]) -> dict:
        """@brief Read one ticket's human comments on explicit request."""
        item = project(name, user)
        if iid < 1:
            raise _error(404, "ticket_not_found")
        forge = ticket_forge(item, ticket_config(item))
        value = ticket_read(lambda: comment_view(forge, iid))
        if value is None:
            raise _error(404, "ticket_not_found")
        return value

    @app.post("/api/v1/projects/{name}/tickets/{iid}/start")
    def start_ticket(name: str, iid: int, body: TicketStartInput,
                     user: Annotated[dict, Depends(mutation)]) -> dict:
        """@brief Add a ticket's missing ready/priority labels, then queue its start.
        @details Refused with pickup_paused, before any forge call, while pickup is stopped.
        """
        item = project(name, user)
        if item.archived:
            raise _error(409, "project_archived")
        if iid < 1:
            raise _error(404, "ticket_not_found")
        # A replayed key returns its original operation, even after the worker created the run.
        replayed = web.operation_for_key(user["id"], body.idempotency_key)
        if replayed is not None:
            binding = (replayed["action"], replayed["run_id"], replayed["project"])
            if binding != ("start", str(iid), item.name):
                raise _error(409, "idempotency_conflict")
            return {"operation_id": replayed["id"], "status": replayed["status"],
                    "labels_added": []}
        if _store_for(profiles, item).is_paused():
            raise _error(409, "ticket_not_startable", PICKUP_PAUSED)
        config = ticket_config(item)
        job = ticket_read(lambda: existing_job(_store_for(profiles, item), config, iid))
        forge = ticket_forge(item, config)
        ticket = ticket_read(lambda: read_ticket(forge, iid))
        if ticket is None:
            raise _error(404, "ticket_not_found")
        preparation = start_preparation(ticket, config, has_run=job is not None)
        if preparation is None:
            reason = start_blocker(ticket, config, has_run=job is not None) or "not_startable"
            raise _error(409, "ticket_not_startable", reason)
        adds_ready, needs_priority = preparation
        added = [config.labels.lifecycle.ready] if adds_ready else []
        if needs_priority:
            if body.priority not in config.labels.selection.priority_order():
                raise _error(400, "priority_required")
            added.append(body.priority)
        def uncertain() -> None:
            """@brief Record a start whose forge labels may have changed without a queued job."""
            web.audit(user["id"], "ticket-start-prepared", item.name, f"#{iid}",
                      resource_type="operation", resource_id=str(iid), result="uncertain")

        if added:
            try:
                forge.add_labels(iid, added)
            except RepositoryAuthError as exc:
                uncertain()
                raise _error(503, exc.code) from exc
            except (ForgeError, TimeoutError, OSError) as exc:
                uncertain()
                raise _error(503, "forge_write_failed") from exc
        try:
            operation = web.enqueue(user["id"], item.name, "start", str(iid), body.idempotency_key)
        except WebStoreError as exc:
            if added:
                uncertain()
            raise _store_error(409, exc) from exc
        web.audit(user["id"], "ticket-start-prepared", item.name, f"#{iid}",
                  resource_type="operation", resource_id=str(iid), operation_id=operation["id"])
        return {"operation_id": operation["id"], "status": operation["status"],
                "labels_added": added}

    @app.post("/api/v1/projects/{name}/tickets/{iid}/stop")
    def stop_ticket(name: str, iid: int, body: TicketStopInput,
                    user: Annotated[dict, Depends(mutation)]) -> dict:
        """@brief Cancel a ticket's unfinished job and remove its ready label from the forge."""
        item = project(name, user)
        if item.archived:
            raise _error(409, "project_archived")
        if iid < 1:
            raise _error(404, "ticket_not_found")
        config = ticket_config(item)
        run_id = ticket_read(lambda: unfinished_run(_store_for(profiles, item), config, iid))
        operation_id = None
        if run_id is not None:
            # Cancelling local work comes first: it must not wait on, or be lost to, a forge outage.
            try:
                operation_id = web.enqueue(
                    user["id"], item.name, "cancel", run_id, body.idempotency_key
                )["id"]
            except WebStoreError as exc:
                raise _store_error(409, exc) from exc
        # The forge is built only now, so unusable credentials never block the local cancel.
        label, label_error, ticket = "absent", None, None
        try:
            runner = project_runner(profiles.profile_dir(item.name), config, probe_runner)
            ticket, removed = remove_ready_label(open_forge(config, runner), config, iid)
            label = "removed" if removed else "absent"
        except RepositoryAuthError as exc:
            label, label_error = "failed", exc.code
        except ForgeResponseError:
            label, label_error = "failed", "forge_response_invalid"
        except (ForgeError, TimeoutError, OSError):
            label, label_error = "failed", "forge_write_failed"
        if ticket is None and label_error is None and operation_id is None:
            raise _error(404, "ticket_not_found")
        web.audit(user["id"], "ticket-stopped", item.name,
                  f"#{iid} cancel={'queued' if operation_id else 'none'} ready_label={label}",
                  resource_type="operation", resource_id=str(iid), operation_id=operation_id,
                  result="applied" if label_error is None else "uncertain")
        return {"cancel_operation_id": operation_id, "ready_label": label,
                "ready_label_error": label_error}

    @app.get("/api/v1/operations/{operation_id}")
    def operation_status(operation_id: int,
                         user: Annotated[dict, Depends(principal)]) -> dict:
        operation = web.operation(operation_id)
        if operation is None:
            raise _error(404, "operation_not_found")
        if not operation["project_id"]:
            raise _error(404, "operation_not_found")
        try:
            project(operation["project_id"], user)
        except HTTPException as exc:
            # A finished delete outlives its project; administrators keep its outcome.
            gone = (exc.status_code == 404 and operation["action"] == "delete"
                    and user["role"] == "admin")
            if not gone:
                raise
        return {key: operation[key] for key in
                ("id", "project", "action", "status", "result", "reason", "detail",
                 "created_at", "updated_at")}

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            raise _error(404, "not_found", "Not Found")
        if not _STATIC.is_dir():
            raise _error(503, "frontend_not_built")
        target = (_STATIC / path).resolve()
        if target.is_file() and target.is_relative_to(_STATIC.resolve()):
            return FileResponse(target)
        return FileResponse(_STATIC / "index.html")

    return app


# END OF FILE
