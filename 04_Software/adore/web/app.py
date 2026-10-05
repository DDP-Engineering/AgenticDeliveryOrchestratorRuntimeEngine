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
from contextlib import contextmanager
import csv
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from io import StringIO
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
from statistics import median
import tempfile
from threading import Lock
from time import monotonic
import tomllib
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from adore import __version__, doctor, metrics
from adore.aegis import RUN_KINDS
from adore.cli import _NOT_SECRET_KEYS, _SECRET_KEY_RE, _is_secret_key, _newline, _set_toml_scalar
from adore.config import SELINUX_RELABEL_MODES, default_config, load_config, validate_config
from adore.config_edit import ConfigEditLockedError, config_edit_lock
from adore.isolation import ContainerManager, IsolationError
from adore.profiles import ProfileError, ProfileStore, validate_display_name, validate_profile_id
from adore.state import RunState, StateError, StateStore
from adore.util import CommandRunner, force_rmtree, run_command
from adore.web.endpoint_probe import probe_endpoint
from adore.web.jobs import JobReadError, read_jobs
from adore.web.store import WebStore, WebStoreError
from adore.wizard import ScriptedAsker, WizardError, WizardSetup, run_wizard

# CONSTANTS
_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_SETTING_KEY_RE = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")
# Configuration sections whose single values the web may edit.
_EDITABLE_SECTIONS = frozenset({
    "agent", "platform", "polling", "readiness", "executor",
    "container", "worktree", "workflow", "recovery", "budgets",
    "delivery", "review", "reconcile", "metrics", "labels",
})
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
_TERMINAL_JOURNAL_EVENTS = {
    "done": {"done"},
    "failed": {"failed", "immediate-failure", "stage-failed", "notification-blocked"},
    "cancelled": {"cancelled"},
    "handed-off": {"handed-off"},
}


# DATA MODELS / TYPEDEFINITIONS
class Credentials(BaseModel):
    """@brief Browser username/password input."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class NewUser(Credentials):
    """@brief Administrator account creation input."""

    role: str = "developer"


class PasswordChange(BaseModel):
    """@brief Authenticated own-password change input."""

    current: str
    replacement: str


class PasswordReset(BaseModel):
    """@brief Administrator recovery password input."""

    replacement: str = Field(min_length=8, max_length=1024)


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
    reviewers: str
    executor_cli: str = "opencode"
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


class ReviewedProjectInput(ProjectInput):
    """@brief Exact reviewed draft revision for explicit probe or guarded creation."""

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


class ConfigApply(BaseModel):
    """@brief Exact pending candidate the administrator reviewed."""

    candidate_revision: str = Field(min_length=64, max_length=64)
    base_revision: str | None = Field(default=None, min_length=64, max_length=64,
                                      pattern=r"^[0-9a-f]{64}$")


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
                or probe["context"] != "executor-container" or type(probe["ready"]) is not bool
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


def _probe_setup(config, probe_runner: CommandRunner) -> dict:
    """@brief Run bounded redacted prerequisites for an explicit config snapshot.

    @param[in] config Validated configuration snapshot.
    @param[in] probe_runner Injectable external command boundary.
    @return Typed prerequisite checks and redacted model evidence.
    @exception HTTPException A prerequisite command fails to produce usable evidence.
    """
    deadline = monotonic() + 30

    def bounded_runner(argv, *, cwd=None, timeout=None, env=None):
        """@brief Keep a doctor subprocess below one request's probe bound."""
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("host readiness deadline")
        if argv[:2] == ["tea", "whoami"] and config.platform.login:
            argv = [*argv, "--login", config.platform.login]
        return probe_runner(argv, cwd=cwd,
                            timeout=min(timeout if timeout is not None else 8,
                                        8, remaining),
                            env=env)

    try:
        git = doctor.detect_git(bounded_runner)
        forge = doctor.detect_platform_cli(config.platform.kind, bounded_runner)
        auth = doctor.auth_status(config.platform.kind, bounded_runner)
        runtimes = doctor.detect_runtimes(bounded_runner)
    except (OSError, UnicodeError, TypeError, ValueError,
            KeyError, TimeoutError) as exc:
        raise _error(503, "readiness_probe_failed") from exc
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
    answers = body.model_dump(exclude={"name", "display_name", "env_keys", "revision"})
    answers["budgets_choice"] = "custom"
    for field in ("ready_label", "approval_label", "kind", "repo", "repo_path",
                  "reviewers", "runtime", "target_branch", "auth_mode", "executor_cli"):
        if not str(answers[field]).strip():
            issues.append(_finding("setup_field_invalid", field,
                                   "Supply a non-empty supported value."))
    for field in ("model", "image"):
        if field in body.model_fields_set and not str(answers[field]).strip():
            issues.append(_finding("setup_field_invalid", field,
                                   "Supply an explicit supported value."))
    clone = Path(body.repo_path).expanduser()
    if not clone.is_absolute() or not (clone / ".git").exists():
        issues.append(_finding("setup_field_invalid", "repo_path",
                               "Use an absolute existing repository clone on the ADORE server."))
    if body.env_keys is not None and (not body.env_keys and body.auth_mode == "api-key"
            or len(body.env_keys) > 32 or len(set(body.env_keys)) != len(body.env_keys)
            or any(not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", key) for key in body.env_keys)
            or body.auth_mode == "host-auth" and body.env_keys):
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
                                   name=body.name, out=lambda _message: None, prepare_only=True)
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
               "config_revision": None, "review": None}
    if candidate is not None and not issues:
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        snapshot = {"document": candidate.document, "name": body.name,
                    "display_name": display, "description": body.description}
        preview["revision"] = sha256(json.dumps(snapshot, sort_keys=True,
                                               ensure_ascii=False).encode("utf-8")).hexdigest()
        preview["config_revision"] = sha256(candidate.document.encode("utf-8")).hexdigest()
        preview["review"] = {
            **body.model_dump(exclude={"revision", "env_keys"}),
            "display_name": display,
            "model": config.executor.commands[config.executor.default].model,
            "image": config.container.image, "env_keys": config.executor.env_keys,
            "hold_label": config.labels.control.hold,
            "exclude_label": config.labels.control.exclude,
            "egress_mode": config.container.egress.mode,
            "branch_template": config.worktree.branch_template,
            "config_path": str(profiles.config_path(body.name).resolve()),
            "store_root": config.state.store_root, "worktree_root": config.worktree.root,
        }
    return preview, candidate


def _publish_paused(profiles: ProfileStore, web: WebStore, actor: int, name: str,
                    raw: bytes, metadata: dict, *, imported: bool = False,
                    import_body: ProjectImportInput | None = None) -> dict:
    """@brief Keep lock, filesystem and parsing failures typed at the enrollment boundary."""
    try:
        return _publish_paused_locked(profiles, web, actor, name, raw, metadata,
                                      imported=imported, import_body=import_body)
    except (OSError, StateError, ProfileError, UnicodeError, ValueError, TypeError) as exc:
        raise _contract_rejection("project_creation_failed", "config",
                              "Check local enrollment storage before retrying.") from exc


def _publish_paused_locked(profiles: ProfileStore, web: WebStore, actor: int, name: str,
                           raw: bytes, metadata: dict, *, imported: bool = False,
                           import_body: ProjectImportInput | None = None) -> dict:
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
            if (root == other_root or root.is_relative_to(other_root)
                    or other_root.is_relative_to(root)):
                raise _contract_rejection("state_root_already_owned", "state.store_root",
                                      "Choose an absolute state root owned only by this project.")
        if import_body is not None:
            _reviewed_import(profiles, import_body)
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
            if (state.invalid_runs() or any(run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
                                           for run in state.list_runs())):
                raise _error(409, "project_has_active_work")
            if import_body is not None:
                _reviewed_import(profiles, import_body, own_state_lock=True)
            profiles.config_path(name).write_bytes(raw)
            state.pause()
            item = profiles.create(name, **metadata)
            web.audit(actor, "project-imported" if imported else "project-created", name)
            return _profile_view(profiles, item)
        except Exception as exc:
            # Metadata is the visibility boundary. Remove it before unlock/resume.
            try:
                (directory / "profile.json").unlink(missing_ok=True)
                if imported and locked and not previously_paused:
                    state.resume()
                force_rmtree(directory)
            except OSError as rollback_exc:
                failure = _contract_rejection(
                    "project_rollback_failed", "config",
                    "Inspect incomplete enrollment on the host before retrying.")
                raise failure from rollback_exc
            if isinstance(exc, HTTPException):
                raise
            raise _contract_rejection("project_creation_failed", "config",
                                  "Check local enrollment storage before retrying.") from exc
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


def _event_day(event: dict, zone=UTC) -> str | None:
    """@brief Assign a dated journal event to the selected reporting day."""
    stamp = event.get("ts")
    if not isinstance(stamp, str):
        return None
    try:
        if len(stamp) == 10:
            return date.fromisoformat(stamp).isoformat()
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(zone).date().isoformat()
    except ValueError:
        return None


def _completion_day(run: RunState, events: list[dict], zone=UTC) -> str | None:
    """@brief Use terminal evidence, not later recovery activity, for completion trends."""
    terminal = _TERMINAL_JOURNAL_EVENTS.get(run.lifecycle, set())
    for event in reversed(events):
        if event.get("event") in terminal:
            return _event_day(event, zone)
    # Older imported runs may lack an explicit terminal event in their journals.
    return _event_day({"ts": run.updated_at}, zone)


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
        if run.updated_at == "":
            continue
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
        "runtime": config.container.runtime if config_valid and config else profile.runtime,
        "executor": config.executor.default if config_valid and config else "",
        "config_valid": config_valid,
        "readiness": readiness,
        "last_activity": last_activity.isoformat() if last_activity else None,
        "archived": profile.archived,
        "paused": paused,
        "invalid_runs": invalid_runs,
        "runs": len(runs),
    }


def _valid_candidate_scalar(key: str, proposed: object) -> bool:
    """
    @brief Enforce the configuration model's scalar type for pending edits.
    @param[in] key TOML file key of the single candidate edit.
    @param[in] proposed Parsed candidate value.
    @return True for the declared scalar type, including finite numeric values.
    """
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
    return False


def _candidate_config_edit(path: Path, body: ConfigEdit) -> tuple[bytes, str]:
    """@brief Produce one validated scalar edit without changing live TOML."""
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
            changed = _set_toml_scalar(current, body.key, body.value)
        parsed_change = tomllib.loads(changed)
        if not _valid_candidate_scalar(body.key, _value_at(parsed_change, body.key)):
            raise _error(400, "invalid_config")
        if _secret_config_keys({"setting": _value_at(parsed_change, body.key)}):
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
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > 2097152:
            raise ValueError("pending config too large")
        value = json.loads(path.read_text(encoding="utf-8"))
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


def _public_pending_config(value: dict) -> dict:
    """@brief Return review metadata without exposing the full TOML document."""
    public = {key: value[key] for key in (
        "base_revision", "candidate_revision", "key", "value", "created_at",
        "restart_required",
    )}
    try:
        candidate = tomllib.loads(value["candidate_text"])
        endpoint_key = value["key"] == "container.runtime_env.OPENAI_BASE_URL"
        if not _editable_setting_key(value["key"], endpoint=endpoint_key):
            raise ValueError("unreviewable setting")
        proposed = _value_at(candidate, value["key"])
        if not _valid_candidate_scalar(value["key"], proposed):
            raise ValueError("invalid proposed value")
        if _secret_config_keys({"setting": proposed}):
            raise ValueError("unsafe proposed value")
        claimed = _value_at(tomllib.loads(_set_toml_scalar(
            "", value["key"], value["value"])), value["key"])
        if type(claimed) is not type(proposed) or claimed != proposed:
            raise ValueError("candidate review metadata differs from its value")
        public["proposed_value"] = proposed
        public["value"] = str(proposed).lower() if type(proposed) is bool else str(proposed)
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
                           "container.", "executor."))


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
    return not (
        _is_secret_key(key)
        or (not endpoint and not _SETTING_KEY_RE.fullmatch(key))
        or key.split(".")[0] not in _EDITABLE_SECTIONS
        or key.endswith(".command")
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
    @param[in] config Redacted configuration; configured executor names are choices.
    @param[in] declared Built-in model default supplying the declared type.
    @return Type, allowed choices and inclusive numeric bounds for browser guidance.
    @note Full configuration validation remains authoritative for dependent rules.
    """
    expected = declared
    if key.startswith("executor.commands.") and key.endswith((".model", ".command")):
        expected = ""
    if key.startswith("workflow.stage_timeout_overrides."):
        expected = 1
    if key.startswith("workflow.kind_labels.") or key.startswith("container.runtime_env."):
        expected = ""
    if expected is not None:
        numeric = type(expected) is float and type(value) in (int, float) and math.isfinite(value)
        if (type(expected) is float and not numeric
                or type(expected) is not float and type(value) is not type(expected)):
            raise ValueError("configuration scalar type differs from its model")
    model_value = expected if expected is not None else value
    choices = {
        "platform.kind": ["gitlab", "github", "gitea"],
        "state.channel": ["comments", "labels", "both"],
        "polling.mode": ["loop", "once"],
        "executor.mode": ["thick", "headless"],
        "executor.default": list(config.get("executor", {}).get("commands", {})),
        "clarification.timeout_state": ["failed", "stale"],
        "container.selinux_relabel": list(SELINUX_RELABEL_MODES),
        "container.parked_ttl_mode": ["seconds", "polls"],
        "container.egress.mode": ["open", "allowlist-proxy", "none"],
        "delivery.draft": [True],
        "review.trigger": ["label"],
        "review.on_pipeline_failure": ["revise", "notify", "ignore"],
        "workflow.default_kind": list(RUN_KINDS),
        "reconcile.on_ticket_deleted": ["abort-cleanup", "ignore"],
        "reconcile.on_ticket_closed": ["cancel", "ignore"],
        "reconcile.on_trigger_removed": ["pause", "abort", "ignore"],
    }.get(key, [])
    if key.startswith("workflow.kind_labels."):
        choices = list(RUN_KINDS)
    positive = {
        "polling.poll_interval_seconds", "polling.max_concurrent_runs",
        "clarification.max_rounds", "recovery.max_stage_failures",
        "recovery.max_transient_retries", "budgets.max_iterations",
        "budgets.max_wall_clock_seconds", "budgets.per_gate_timeout_seconds",
        "budgets.max_files_touched", "review.max_review_rounds",
        "container.egress.proxy_port",
    }
    minimum = (1 if key in positive or key.startswith("workflow.stage_timeout_overrides.")
               else 0 if key in {"polling.poll_jitter_seconds", "budgets.max_cost_usd"}
               else None)
    kind = ("boolean" if type(model_value) is bool else "integer" if type(model_value) is int
            else "number" if type(model_value) is float else "list" if isinstance(model_value, list)
            else "map" if isinstance(model_value, dict) else "text")
    return {"type": kind, "choices": choices, "minimum": minimum,
            "maximum": 65535 if key == "container.egress.proxy_port" else None}


def _setting_metadata(config: dict, raw: bytes) -> list[dict]:
    """
    @brief      Source, editability and restart need of every effective setting.
    @details    `config` is the redacted effective configuration; `raw` the
                project's TOML file. The file key of an executor command field
                is `executor.<name>.<field>`, while the effective configuration
                nests it under `executor.commands`. A setting is from the
                project when its file key is a leaf of the file, whatever its
                value; it is editable when the shared key rule accepts the file
                key and its value is a single string, number or boolean. Its
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
    for key, value in _toml_leaves(config):
        edit_key = ("executor." + key.removeprefix("executor.commands.")
                    if key.startswith("executor.commands.") else key)
        settings.append({
            "key": key,
            "edit_key": edit_key,
            "source": "project" if edit_key in in_file else "default",
            "editable": (_editable_setting_key(edit_key)
                         and isinstance(value, str | int | float)),
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
    item.runtime = config.container.runtime
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
                      "container": {"runtime": config.container.runtime,
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
            "runtime": config.container.runtime if review else None,
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


def _check_metric_range(day_from: date | None, day_to: date | None) -> None:
    """@brief Reject a reversed reporting period."""
    if day_from is not None and day_to is not None and day_from > day_to:
        raise _error(422, "invalid_date_range")


def _reporting_zone(name: str) -> ZoneInfo:
    """@brief Resolve a bounded IANA timezone or reject unsupported input."""
    if (not isinstance(name, str) or len(name) > 64
            or not re.fullmatch(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*", name)):
        raise _error(422, "invalid_reporting_timezone")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise _error(422, "invalid_reporting_timezone") from exc


def _trend_start(day: str, granularity: str) -> str:
    """@brief Return the local ISO date beginning a day, Monday-week or month."""
    current = date.fromisoformat(day)
    if granularity == "day":
        return day
    if granularity == "week":
        return (current - timedelta(days=current.weekday())).isoformat()
    return current.replace(day=1).isoformat()


def _trend_rows(days: list[dict], granularity: str) -> list[dict]:
    """@brief Combine selected local-day buckets without losing cost coverage."""
    if granularity == "day":
        return days
    grouped: dict[str, dict] = {}
    for row in days:
        key = _trend_start(row["date"], granularity)
        target = grouped.setdefault(key, {"date": key, **{
            field: None if field in ("cost_usd", "estimated_cost_usd") else 0
            for field in row if field != "date"
        }})
        for field, value in row.items():
            if field == "date" or value is None:
                continue
            target[field] = (target[field] or 0) + value
    return [grouped[key] for key in sorted(grouped)]


def _duration_samples(summaries: list[metrics.RunSummary], zone=UTC) -> list[tuple[str, int]]:
    """@brief Validate terminal spans and assign local completion days."""
    samples = []
    for summary in summaries:
        start, end, span = summary.started_at, summary.ended_at, summary.span_seconds
        if (not isinstance(start, str) or not isinstance(end, str)
                or not isinstance(span, int) or isinstance(span, bool) or span < 0):
            raise _error(503, "metrics_corrupt")
        if summary.lifecycle not in _TERMINAL_RUN_LIFECYCLES:
            continue
        if not start and not end and span == 0:
            continue  # Legacy summary without elapsed-time evidence.
        if not start or not end:
            raise _error(503, "metrics_corrupt")
        try:
            first = datetime.fromisoformat(start)
            last = datetime.fromisoformat(end)
            if (first.tzinfo is None or first.utcoffset() is None
                    or last.tzinfo is None or last.utcoffset() is None
                    or last < first or int((last - first).total_seconds()) != span):
                raise ValueError("inconsistent elapsed span")
        except (TypeError, ValueError, OverflowError) as exc:
            raise _error(503, "metrics_corrupt") from exc
        samples.append((last.astimezone(zone).date().isoformat(), span))
    return samples


def _duration_totals(samples: list[tuple[str, int]]) -> dict:
    """@brief Return nullable average/median and the number of measured jobs."""
    spans = [span for _, span in samples]
    return {"sampled_runs": len(spans),
            "avg_span_seconds": round(sum(spans) / len(spans)) if spans else None,
            "median_span_seconds": median(spans) if spans else None}


def _usage_view(profiles: ProfileStore, profile, admin: bool, web: WebStore,
                day_from: date | None, day_to: date | None,
                executor: str | None, model: str | None,
                timezone: str = "UTC",
                granularity: Literal["day", "week", "month"] = "day") -> dict:
    """@brief Group dated, identified journal usage without inventing run identity."""
    _check_metric_range(day_from, day_to)
    zone = _reporting_zone(timezone)
    if executor is not None and not executor.strip():
        raise _error(422, "invalid_executor_filter")
    if model is not None and not model.strip():
        raise _error(422, "invalid_model_filter")
    store = _store_for(profiles, profile)
    if store.invalid_runs():
        raise _error(503, "run_state_corrupt")
    try:
        prices = web.list_prices(profile.name) if admin else []
    except WebStoreError as exc:
        raise _error(503, "price_storage_corrupt") from exc
    buckets: dict[tuple[str, str | None, str | None], dict] = {}
    unpriced = 0
    for run in store.list_runs():
        try:
            events = web.reconcile_usage(profile.project_id, run.run_id,
                                         store.read_journal(run.run_id))
        except (metrics.MetricsError, WebStoreError) as exc:
            raise _error(503, "usage_corrupt") from exc
        for event in events:
            if not isinstance(event, dict):
                raise _error(503, "usage_corrupt")
            if event.get("event") != "usage":
                continue
            identity = (event.get("executor"), event.get("model"))
            if any(value is not None and (not isinstance(value, str)
                                           or len(value) > 200) for value in identity):
                raise _error(503, "usage_corrupt")
            day = _event_day(event, zone)
            if (day is None or (day_from is not None and day < day_from.isoformat())
                    or (day_to is not None and day > day_to.isoformat())
                    or (executor is not None and identity[0] != executor)
                    or (model is not None and identity[1] != model)):
                continue
            period_key = _trend_start(day, granularity)
            try:
                incoming = event.get("tokens_in", 0)
                outgoing = event.get("tokens_out", 0)
                money = event.get("cost_usd", 0)
                cache_read = event.get("cache_read_tokens")
                cache_write = event.get("cache_write_tokens")
                if (not isinstance(incoming, int) or isinstance(incoming, bool)
                        or not isinstance(outgoing, int) or isinstance(outgoing, bool)
                        or not isinstance(money, (int, float)) or isinstance(money, bool)
                        or min(incoming, outgoing, money) < 0
                        or not math.isfinite(money)
                        or any(value is not None and
                               (type(value) is not int or value < 0)
                               for value in (cache_read, cache_write))
                        or ((cache_read is not None or cache_write is not None)
                            and event.get("input_includes_cache") is not True)):
                    raise ValueError("invalid usage numbers")
            except (TypeError, ValueError, OverflowError):
                raise _error(503, "usage_corrupt") from None
            row = buckets.setdefault((period_key, *identity), {
                "date": period_key, "executor": identity[0], "model": identity[1],
                "events": 0, "tokens_in": 0, "tokens_out": 0,
                "cache_read_tokens": None, "cache_write_tokens": None,
                "reported_cost_usd": None, "estimated_cost_usd": None,
            })
            row["events"] += 1
            row["tokens_in"] += incoming
            row["tokens_out"] += outgoing
            for field, amount in (("cache_read_tokens", cache_read),
                                  ("cache_write_tokens", cache_write)):
                if amount is not None:
                    row[field] = (row[field] or 0) + amount
            if admin:
                if event.get("cost_reported") is True or money > 0:
                    row["reported_cost_usd"] = (row["reported_cost_usd"] or 0) + money
                elif incoming or outgoing:
                    matching = [price for price in prices
                                if price["executor"] == identity[0]
                                and price["model"] == identity[1]
                                and price["effective_from"] <= _event_day(event)]
                    if matching:
                        price = matching[-1]
                        estimate = ((Decimal(incoming) * Decimal(price["input_usd_per_million"])
                                     + Decimal(outgoing) * Decimal(price["output_usd_per_million"]))
                                    / Decimal(1_000_000))
                        row["estimated_cost_usd"] = (
                            (row["estimated_cost_usd"] or Decimal(0)) + estimate
                        )
                    else:
                        unpriced += 1
    rows = [buckets[key] for key in sorted(buckets, key=lambda item: (
        item[0], item[1] or "", item[2] or ""))]
    totals = {key: sum(row[key] for row in rows)
              for key in ("events", "tokens_in", "tokens_out")}
    for field in ("cache_read_tokens", "cache_write_tokens"):
        amounts = [row[field] for row in rows if row[field] is not None]
        totals[field] = sum(amounts) if amounts else None
    if admin:
        for key in ("reported_cost_usd", "estimated_cost_usd"):
            amounts = [row[key] for row in rows if row[key] is not None]
            totals[key] = round(float(sum(amounts)), 6) if amounts else None
        totals["unpriced_events"] = unpriced
        for row in rows:
            if row["estimated_cost_usd"] is not None:
                row["estimated_cost_usd"] = float(row["estimated_cost_usd"])
    else:
        for row in rows:
            row.pop("reported_cost_usd")
            row.pop("estimated_cost_usd")
    return {"daily": rows, "totals": totals,
            "timezone": timezone, "granularity": granularity,
            "filters": {"day_from": day_from.isoformat() if day_from else None,
                        "day_to": day_to.isoformat() if day_to else None,
                        "executor": executor, "model": model}}


def _usage_csv(views: list[tuple[object, dict]], admin: bool,
               global_view: bool) -> Response:
    """@brief Export attributed usage under the caller's financial boundary."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    columns = ["date", "executor", "model", "events", "tokens_in", "tokens_out",
               "cache_read_tokens", "cache_write_tokens"]
    if admin:
        columns.extend(("reported_cost_usd", "estimated_cost_usd"))
    writer.writerow((["project", "repository"] if global_view else []) + columns)
    for profile, view in views:
        for row in view["daily"]:
            values = [(_csv_text(row[key]) if key in ("executor", "model")
                       else row[key]) if row[key] is not None else ""
                      for key in columns]
            writer.writerow(([_csv_text(profile.name), _csv_text(profile.repo)]
                             if global_view else []) + values)
    name = "adore-global-usage.csv" if global_view else f"adore-{views[0][0].name}-usage.csv"
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _usage_observation(event: dict, run_id: str) -> tuple:
    """@brief Validate a persisted launch observation and return replay identity."""
    try:
        return metrics.validate_usage_observation(event, run_id)
    except metrics.MetricsError as exc:
        raise _error(503, "metrics_corrupt") from exc


def _metric_view(profiles: ProfileStore, profile, admin: bool,
                 web: WebStore, day_from: date | None = None,
                 day_to: date | None = None, timezone: str = "UTC",
                 granularity: Literal["day", "week", "month"] = "day") -> dict:
    _check_metric_range(day_from, day_to)
    zone = _reporting_zone(timezone)
    store = _store_for(profiles, profile)
    if store.invalid_runs():
        raise _error(503, "run_state_corrupt")
    try:
        summaries = metrics.load_summaries(store.root / "metrics.db")
    except (sqlite3.DatabaseError, OSError, ValueError) as exc:
        raise _error(503, "metrics_corrupt") from exc
    duration_samples = _duration_samples(summaries, zone)
    if admin:
        try:
            prices = web.list_prices(profile.name)
        except WebStoreError as exc:
            raise _error(503, "price_storage_corrupt") from exc
    else:
        prices = []
    daily: dict[str, dict] = {}
    usage_runs = 0
    cost_runs = 0
    estimated_runs = 0
    unpriced_events = 0
    unclassified_revisions = 0
    reported_token_launches = 0
    unavailable_token_launches = 0
    disabled_launches = 0
    reported_cost_launches = 0
    unavailable_cost_launches = 0
    mr_revisions = 0
    pipeline_repairs = 0
    cost_run_ids: set[str] = set()
    journal_usage_run_ids: set[str] = set()
    run_estimates: dict[str, Decimal] = {}
    run_reported: dict[str, Decimal] = {}
    revisions: list[dict] = []
    runs = store.list_runs()
    quality = {
        "reviewed_jobs": 0, "reworked_jobs": 0, "open_review_jobs": 0,
        "validated_jobs": 0, "first_pass_validations": 0,
        "human_merged_jobs": 0, "first_pass_merges": 0,
        "stage_failures": 0, "operator_retries": 0,
    }
    completed_reported: list[Decimal] = []
    completed_estimated: list[Decimal] = []
    merged_reported: list[Decimal] = []
    merged_estimated: list[Decimal] = []

    def bucket(day: str) -> dict:
        """@brief Return one daily metrics bucket."""
        return daily.setdefault(day, {
            "started": 0, "completed": 0, "tokens_in": 0,
            "tokens_out": 0, "mr_revisions": 0, "pipeline_repairs": 0,
            "cost_usd": None, "estimated_cost_usd": None,
        })

    for run in runs:
        try:
            events = metrics.unique_usage_events(store.read_journal(run.run_id),
                                                  run.run_id)
        except metrics.MetricsError as exc:
            raise _error(503, "metrics_corrupt") from exc
        has_usage = False
        has_cost = False
        has_estimate = False
        active_revision = None
        revision_number = 0
        reviewed = False
        reviewer_rework = False
        first_verdict = None
        observations: dict[str, tuple] = {}
        if events:
            started = _event_day(events[0], zone)
            if started is not None:
                bucket(started)["started"] += 1
            if run.lifecycle in _TERMINAL_RUN_LIFECYCLES:
                ended = _completion_day(run, events, zone)
                if ended is not None:
                    bucket(ended)["completed"] += 1
        for event in events:
            if event.get("event") == "usage-observation":
                observation = _usage_observation(event, run.run_id)
                event_id = observation[0]
                prior = observations.get(event_id)
                if prior is not None:
                    if prior != observation:
                        raise _error(503, "metrics_corrupt")
                    continue
                observations[event_id] = observation
                token_status = event["token_status"]
                cost_status = event["cost_status"]
                reported_token_launches += token_status == "reported"
                unavailable_token_launches += token_status == "unavailable"
                disabled_launches += token_status == "disabled"
                reported_cost_launches += cost_status == "reported"
                unavailable_cost_launches += cost_status == "unavailable"
            if event.get("event") in ("mr-opened", "mr-adopted"):
                reviewed = True
            if event.get("event") == "stage-failed":
                quality["stage_failures"] += 1
            if event.get("event") == "operator-retry":
                quality["operator_retries"] += 1
            if event.get("event") == "strict-verification":
                verdict = event.get("passed")
                if not isinstance(verdict, bool):
                    raise _error(503, "metrics_corrupt")
                if first_verdict is None:
                    first_verdict = verdict
            if event.get("event") == "revision-started":
                stamp = _event_day(event, zone)
                trigger = event.get("trigger")
                if trigger == "revise-label":
                    reviewer_rework = True
                revision_number += 1
                if admin:
                    active_revision = {
                        "run_id": run.run_id, "revision": revision_number,
                        "trigger": trigger if trigger in ("revise-label", "pipeline-failed")
                        else "unclassified", "date": stamp,
                        "tokens_in": 0, "tokens_out": 0,
                        "reported_cost_usd": None, "estimated_cost_usd": None,
                    }
                    revisions.append(active_revision)
                if stamp is None or trigger not in ("revise-label", "pipeline-failed"):
                    unclassified_revisions += 1
                elif trigger == "revise-label":
                    bucket(stamp)["mr_revisions"] += 1
                    mr_revisions += 1
                else:
                    bucket(stamp)["pipeline_repairs"] += 1
                    pipeline_repairs += 1
            if event.get("event") != "usage":
                continue
            stamp = _event_day(event, zone)
            if stamp is None:
                continue
            try:
                incoming = int(event.get("tokens_in", 0) or 0)
                outgoing = int(event.get("tokens_out", 0) or 0)
                money = float(event.get("cost_usd", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                continue
            if min(incoming, outgoing, money) < 0 or not math.isfinite(money):
                continue
            day_bucket = bucket(stamp)
            day_bucket["tokens_in"] += incoming
            day_bucket["tokens_out"] += outgoing
            if active_revision is not None:
                active_revision["tokens_in"] += incoming
                active_revision["tokens_out"] += outgoing
            if event.get("cost_reported") is True or money > 0:
                day_bucket["cost_usd"] = (day_bucket["cost_usd"] or 0.0) + money
                if active_revision is not None:
                    active_revision["reported_cost_usd"] = (
                        (active_revision["reported_cost_usd"] or 0.0) + money
                    )
                has_cost = True
                run_reported[run.run_id] = (
                    run_reported.get(run.run_id, Decimal(0)) + Decimal(str(money))
                )
            elif admin and (incoming or outgoing):
                matching = [price for price in prices
                            if price["executor"] == event.get("executor")
                            and price["model"] == event.get("model")
                            and price["effective_from"] <= _event_day(event)]
                if matching:
                    price = matching[-1]
                    estimate = ((Decimal(incoming) * Decimal(price["input_usd_per_million"])
                                 + Decimal(outgoing) * Decimal(price["output_usd_per_million"]))
                                / Decimal(1_000_000))
                    day_bucket["estimated_cost_usd"] = (
                        (day_bucket["estimated_cost_usd"] or Decimal(0)) + estimate
                    )
                    run_estimates[run.run_id] = (
                        run_estimates.get(run.run_id, Decimal(0)) + estimate
                    )
                    if active_revision is not None:
                        active_revision["estimated_cost_usd"] = (
                            (active_revision["estimated_cost_usd"] or Decimal(0))
                            + estimate
                        )
                    has_estimate = True
                else:
                    unpriced_events += 1
            has_usage = True
        if first_verdict is not None:
            quality["validated_jobs"] += 1
            quality["first_pass_validations"] += first_verdict
        if reviewed:
            quality["reviewed_jobs"] += 1
            quality["reworked_jobs"] += reviewer_rework
            quality["open_review_jobs"] += run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
            if run.lifecycle == "done" and run.outcome == "merged by human":
                quality["human_merged_jobs"] += 1
                quality["first_pass_merges"] += not reviewer_rework
        if run.lifecycle == "done":
            if run.run_id in run_reported:
                completed_reported.append(run_reported[run.run_id])
            if run.run_id in run_estimates:
                completed_estimated.append(run_estimates[run.run_id])
            if run.outcome == "merged by human":
                if run.run_id in run_reported:
                    merged_reported.append(run_reported[run.run_id])
                if run.run_id in run_estimates:
                    merged_estimated.append(run_estimates[run.run_id])
        usage_runs += has_usage
        if has_usage:
            journal_usage_run_ids.add(run.run_id)
        cost_runs += has_cost
        estimated_runs += has_estimate
        if has_cost:
            cost_run_ids.add(run.run_id)
    rows = []
    for summary in summaries:
        row = asdict(summary)
        if not admin:
            row.pop("cost_usd")
        else:
            if summary.run_id not in cost_run_ids:
                row["cost_usd"] = None
            row["estimated_cost_usd"] = (
                float(run_estimates[summary.run_id])
                if summary.run_id in run_estimates else None
            )
        rows.append(row)
    totals = metrics.aggregate(summaries).get("all", {})
    totals["runs"] = len(runs)
    totals["mr_revisions"] = mr_revisions
    totals["pipeline_repairs"] = pipeline_repairs
    totals["tokens_in"] = sum(day["tokens_in"] for day in daily.values()) + sum(
        summary.tokens_in for summary in summaries
        if summary.run_id not in journal_usage_run_ids
    )
    totals["tokens_out"] = sum(day["tokens_out"] for day in daily.values()) + sum(
        summary.tokens_out for summary in summaries
        if summary.run_id not in journal_usage_run_ids
    )
    if not admin:
        totals.pop("cost_usd", None)
    else:
        reported = [day["cost_usd"] for day in daily.values()
                    if day["cost_usd"] is not None]
        totals["cost_usd"] = round(sum(reported), 6) if reported else None
    if admin:
        totals["estimated_cost_usd"] = (
            float(sum(run_estimates.values(), Decimal(0)))
            if run_estimates else None
        )
    days = [{"date": day, **values} for day, values in sorted(daily.items())]
    if not admin:
        for day in days:
            day.pop("cost_usd")
            day.pop("estimated_cost_usd")
    else:
        for day in days:
            if day["estimated_cost_usd"] is not None:
                day["estimated_cost_usd"] = float(day["estimated_cost_usd"])
        for revision in revisions:
            if revision["estimated_cost_usd"] is not None:
                revision["estimated_cost_usd"] = float(revision["estimated_cost_usd"])
    days = [item for item in days
            if (day_from is None or item["date"] >= day_from.isoformat())
            and (day_to is None or item["date"] <= day_to.isoformat())]
    period = {
        "from": day_from.isoformat() if day_from else None,
        "to": day_to.isoformat() if day_to else None,
        "basis": "dated_events",
        **{key: sum(item[key] for item in days) for key in (
            "started", "completed", "tokens_in", "tokens_out",
            "mr_revisions", "pipeline_repairs")},
        "duration": _duration_totals([
            sample for sample in duration_samples
            if (day_from is None or sample[0] >= day_from.isoformat())
            and (day_to is None or sample[0] <= day_to.isoformat())]),
    }
    if admin:
        reported = [item["cost_usd"] for item in days
                    if item["cost_usd"] is not None]
        estimated = [item["estimated_cost_usd"] for item in days
                     if item["estimated_cost_usd"] is not None]
        period["cost_usd"] = round(sum(reported), 6) if reported else None
        period["estimated_cost_usd"] = round(sum(estimated), 6) if estimated else None
    quality["review_rework_rate"] = (quality["reworked_jobs"] / quality["reviewed_jobs"]
                                     if quality["reviewed_jobs"] else None)
    quality["first_validation_rate"] = (
        quality["first_pass_validations"] / quality["validated_jobs"]
        if quality["validated_jobs"] else None)
    quality["first_pass_merge_rate"] = (
        quality["first_pass_merges"] / quality["human_merged_jobs"]
        if quality["human_merged_jobs"] else None)
    if admin:
        quality["cost_efficiency"] = {
            key: {"jobs_with_evidence": len(values),
                  "usd_per_job": (float(sum(values, Decimal(0)) / len(values))
                  if values else None)}
            for key, values in (
                ("reported_per_completed", completed_reported),
                ("estimated_per_completed", completed_estimated),
                ("reported_per_human_merged", merged_reported),
                ("estimated_per_human_merged", merged_estimated),
            )
        }
    result = {"totals": totals, "duration": _duration_totals(duration_samples),
            "runs": rows, "daily": _trend_rows(days, granularity),
            "timezone": timezone, "granularity": granularity,
            "period": period, "quality": quality,
            "coverage": {"runs_with_usage": usage_runs,
                         "revision_events_unclassified": unclassified_revisions,
                         "launches_with_reported_tokens": reported_token_launches,
                         "launches_with_unavailable_tokens": unavailable_token_launches,
                         "launches_capture_disabled": disabled_launches,
                         **({"runs_with_reported_cost": cost_runs,
                             "runs_with_estimated_cost": estimated_runs,
                             "launches_with_reported_cost": reported_cost_launches,
                             "launches_with_unavailable_cost": unavailable_cost_launches,
                             "usage_events_unpriced": unpriced_events} if admin else {})}}
    if admin:
        result["revisions"] = revisions
    return result


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
                       "/api/v1/projects/setup-create"}
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
                                "low": reading.free < _LOW_STORAGE_BYTES})
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
        return {"name": "ADORE", "version": __version__,
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
            web.change_password(user["id"], body.current, body.replacement)
        except WebStoreError as exc:
            raise _store_error(400, exc) from exc
        web.audit(user["id"], "password-changed")
        return {"ok": True}

    @app.get("/api/v1/users")
    def users(_user: Annotated[dict, Depends(administrator)]) -> list[dict]:
        return [{**account, "projects": sorted(web.memberships(account["id"]))}
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
    def audit_page(_user: Annotated[dict, Depends(administrator)],
                   limit: str = "25",
                   offset: Annotated[int, Query(ge=0)] = 0) -> dict:
        """@brief Return one newest-first audit slice with the retained total."""
        if limit == "all":
            size = None
        elif (len(limit) > 3 or not limit.isascii() or not limit.isdecimal()
              or not 1 <= int(limit) <= 100):
            raise _error(422, "invalid_audit_limit")
        else:
            size = int(limit)
        items, total = web.audit_page(size, offset)
        return {"items": items, "total": total, "limit": size, "offset": offset}

    @app.get("/api/v1/audit-policy")
    def get_audit_policy(_user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Return persisted audit limits; null means unlimited."""
        return web.audit_policy()

    @app.put("/api/v1/audit-policy")
    def update_audit_policy(body: AuditPolicyInput,
                            user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Apply administrator limits and record the policy change."""
        result = web.set_audit_policy(body.retention_days, body.max_bytes)
        web.audit(user["id"], "audit-policy-changed")
        return result

    @app.post("/api/v1/users")
    def add_user(body: NewUser, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            created = web.create_user(body.username, body.password, body.role)
        except WebStoreError as exc:
            raise _store_error(400, exc) from exc
        web.audit(user["id"], "user-created", detail=body.username)
        return created

    @app.put("/api/v1/users/{user_id}/projects")
    def assign(user_id: int, body: Memberships,
               user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        for name in body.projects:
            _profile_name(name)
            try:
                profiles.load(name)
            except ProfileError as exc:
                raise _error(404, "project_not_found") from exc
        try:
            web.set_memberships(user_id, body.projects)
        except WebStoreError as exc:
            raise _store_error(404, exc) from exc
        web.audit(user["id"], "membership-changed", detail=str(user_id))
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
    def change_project_access(name: str, user_id: int, body: AccessChange,
                              user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Grant or remove one developer's access to this project only."""
        item = project(name, user)
        account = web.user_by_id(user_id)
        if account is None:
            raise _error(404, "user_not_found")
        if account["role"] != "developer":
            raise _error(400, "user_not_developer")
        try:
            web.set_membership(user_id, item.name, body.granted)
        except WebStoreError as exc:
            raise _store_error(409 if str(exc) == "project changed during the update" else 404,
                               exc) from exc
        web.audit(user["id"], "membership-changed", item.name,
                  f"user {user_id} {'granted' if body.granted else 'removed'}")
        return {"id": user_id, "granted": body.granted}

    @app.post("/api/v1/users/{user_id}/disable")
    def disable(user_id: int, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            web.disable_user(user_id)
        except WebStoreError as exc:
            raise _store_error(409, exc) from exc
        web.audit(user["id"], "user-disabled", detail=str(user_id))
        return {"ok": True}

    @app.post("/api/v1/users/{user_id}/enable")
    def enable(user_id: int, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            web.enable_user(user_id)
        except WebStoreError as exc:
            raise _store_error(404, exc) from exc
        web.audit(user["id"], "user-enabled", detail=str(user_id))
        return {"ok": True}

    @app.post("/api/v1/users/{user_id}/reset-password")
    def reset_password(user_id: int, body: PasswordReset,
                       user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        try:
            web.reset_password(user_id, body.replacement)
        except WebStoreError as exc:
            raise _store_error(404 if "not found" in str(exc) else 400, exc) from exc
        web.audit(user["id"], "password-reset", detail=str(user_id))
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

    @app.post("/api/v1/projects/setup-preview")
    def preview_project_setup(body: ProjectInput,
                              _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Validate setup locally without commands or profile publication."""
        preview, _candidate = _prepare_project(profiles, body)
        return preview

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
        return _publish_paused(profiles, web, user["id"], body.name,
                               candidate.document.encode("utf-8"), candidate.metadata)

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
        return _publish_paused(profiles, web, user["id"], body.name,
                               candidate.document.encode("utf-8"), candidate.metadata)

    @app.post("/api/v1/projects/import-preview")
    def preview_project_import(
        body: ProjectImportInput,
        _user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Review an unchanged TOML import before saving it."""
        preview, _config = _inspect_project_import(profiles, body)
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
                                   "runtime": config.container.runtime,
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

    @app.get("/api/v1/projects/{name}")
    def project_detail(name: str, user: Annotated[dict, Depends(principal)]) -> dict:
        return _profile_view(profiles, project(name, user))

    @app.post("/api/v1/projects/{name}/readiness-check")
    def readiness_check(name: str,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Probe selected host prerequisites on explicit admin request."""
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
        evidence = _probe_setup(config, probe_runner)
        checks, model_probe = evidence["checks"], evidence["model_probe"]
        value = {"schema": 1, "project_id": item.project_id, "revision": revision,
                 "context": "api-host", "checked_at": datetime.now(UTC).isoformat(),
                 "checks": checks, "model_probe": model_probe}
        try:
            with _web_config_edit_lock(profiles.config_path(item.name)):
                current = project(name, user)
                current_revision = sha256(profiles.config_path(item.name).read_bytes()).hexdigest()
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

    @app.post("/api/v1/projects/{name}/delete")
    def delete_project(name: str, body: ProjectDeleteInput,
                       user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """
        @brief Queue deletion of a confirmed, archived and idle project.
        @details The command worker rechecks role, archive state and identity,
                 then runs `adore profile delete <name> --force --remove-resources`.
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
        try:
            operation = web.enqueue(user["id"], item.name, "delete", "",
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
        return {"config": data, "revision": sha256(raw).hexdigest(),
                "issues": validate_config(config),
                "local_endpoint_timeout_seconds": timeout_seconds,
                "local_endpoint": endpoint_profile,
                "settings": settings}

    @app.put("/api/v1/projects/{name}/config")
    def config_update(name: str, body: ConfigEdit,
                      user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        item = project(name, user)
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
        path = profiles.config_path(item.name)
        with config_lock, _web_config_edit_lock(path), guard_direct_config_apply(
            item, path, body.key,
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
                        current = _set_toml_scalar(
                            current, "executor.opencode.model", body.model,
                        )
                    changed = _set_endpoint(
                        current, body.value, model, body.auth_env,
                        body.timeout_seconds, body.ca_file,
                    )
                else:
                    changed = _set_toml_scalar(current, body.key, body.value)
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
                candidate.replace(path)
                _sync_profile_config_identity(profiles, item, path)
            except (UnicodeError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
                raise _error(400, "invalid_config") from exc
            finally:
                if candidate is not None:
                    candidate.unlink(missing_ok=True)
        web.audit(user["id"], "config-updated", item.name, body.key)
        return {"revision": sha256(path.read_bytes()).hexdigest()}

    @app.get("/api/v1/projects/{name}/config/pending")
    def pending_config(name: str,
                       user: Annotated[dict, Depends(administrator)]) -> dict | None:
        """@brief Show a saved candidate without returning its full TOML text."""
        item = project(name, user)
        value = _read_pending_config(profiles.profile_dir(item.name) / "pending_config.json")
        return _public_pending_config(value) if value else None

    @app.post("/api/v1/projects/{name}/config/pending")
    def stage_config(name: str, body: ConfigEdit,
                     user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Save a validated candidate revision while live config stays put."""
        item = project(name, user)
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
            public = _public_pending_config(value)
            _write_pending_config(pending_path, value)
        web.audit(user["id"], "config-staged", item.name, body.key)
        return public

    @app.post("/api/v1/projects/{name}/config/apply")
    def apply_config(name: str, body: ConfigApply,
                     user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Apply the reviewed candidate only at a quiescent boundary."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        with config_lock, _web_config_edit_lock(path):
            pending = _read_pending_config(pending_path)
            if pending is None:
                raise _error(404, "pending_config_not_found")
            _public_pending_config(pending)
            if (body.base_revision is not None
                    and not secrets.compare_digest(body.base_revision, pending["base_revision"])):
                raise _error(409, "stale_config_revision")
            if not secrets.compare_digest(body.candidate_revision,
                                          pending["candidate_revision"]):
                raise _error(409, "stale_pending_revision")
            try:
                raw = path.read_bytes()
                current = load_config(path)
            except (OSError, UnicodeError, ValueError, TypeError,
                    tomllib.TOMLDecodeError) as exc:
                raise _error(503, "config_corrupt") from exc
            current_revision = sha256(raw).hexdigest()
            already_applied = current_revision == pending["candidate_revision"]
            if current_revision != pending["base_revision"] and not already_applied:
                raise _error(409, "stale_config_revision")
            if (not item.store_root or not Path(item.store_root).is_absolute()
                    or Path(item.store_root).resolve()
                    != Path(current.state.store_root).resolve()):
                raise _error(409, "unmanaged_state_root")
            state = StateStore(item.store_root, current.agent.slug)
            if not state.acquire_lock():
                raise _error(409, "project_has_active_work")
            try:
                if (state.invalid_runs()
                        or any(run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
                               for run in state.list_runs())
                        or web.has_unfinished_operations(item.name)
                        or pending.get("restart_required") and not state.is_paused()):
                    raise _error(409, "project_has_active_work")
                candidate: Path | None = None
                try:
                    if already_applied:
                        if validate_config(current):
                            raise _error(503, "config_corrupt")
                    else:
                        descriptor, candidate_name = tempfile.mkstemp(
                            prefix="config.apply-", suffix=".toml", dir=path.parent,
                        )
                        os.close(descriptor)
                        candidate = Path(candidate_name)
                        candidate.write_bytes(pending["candidate_text"].encode("utf-8"))
                        if validate_config(load_config(candidate)):
                            raise _error(400, "invalid_config")
                        if sha256(path.read_bytes()).hexdigest() != pending["base_revision"]:
                            raise _error(409, "stale_config_revision")
                        candidate.replace(path)
                    _sync_profile_config_identity(profiles, item, path)
                    pending_path.unlink()
                finally:
                    if candidate is not None:
                        candidate.unlink(missing_ok=True)
            finally:
                state.release_lock()
        web.audit(user["id"], "config-applied", item.name, pending["key"])
        return {"revision": sha256(path.read_bytes()).hexdigest()}

    @app.delete("/api/v1/projects/{name}/config/pending")
    def discard_config(name: str,
                       user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly discard a staged candidate, including corrupt ones."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        with config_lock, _web_config_edit_lock(path):
            if not pending_path.is_file():
                raise _error(404, "pending_config_not_found")
            pending_path.unlink()
        web.audit(user["id"], "config-discarded", item.name)
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
        lifecycle: Literal["working", "publishing", "awaiting-approval", "parked-clarification",
                           "in-review", "done", "failed", "cancelled", "stale",
                           "handoff-pending", "handed-off"] | None = None,
        stage: Literal["frame", "specify", "design", "build", "validate", "deliver", "done",
                       "publishing"] | None = None,
        executor: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
        outcome: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        updated_from: date | None = None,
        updated_to: date | None = None,
        attention: bool = False,
        limit: str = "25",
        offset: Annotated[int, Query(ge=0)] = 0,
        snapshot: Annotated[str | None, Query(pattern=r"^[0-9a-f]{64}$")] = None,
    ) -> dict:
        """
        @brief Globally search/order/page complete authorized local job evidence.
        @param[in] user Current authenticated principal.
        @param[in] project_id Optional immutable authorized project scope.
        @param[in] q Optional bounded case-insensitive search text.
        @param[in] status_group Optional lifecycle group.
        @param[in] lifecycle Optional exact lifecycle.
        @param[in] stage Optional exact persisted AEGIS stage.
        @param[in] executor Optional exact observed executor identity.
        @param[in] outcome Optional case-insensitive saved outcome fragment.
        @param[in] updated_from Inclusive stored-update UTC day lower bound.
        @param[in] updated_to Inclusive stored-update UTC day upper bound.
        @param[in] attention Select jobs awaiting intervention or recovery.
        @param[in] limit Bounded page size or all.
        @param[in] offset Nonnegative matched-row offset.
        @param[in] snapshot Optional expected source-content revision.
        @return Complete matched page, scoped counts and source revision.
        """
        if limit != "all" and (len(limit) > 3 or not limit.isascii() or not limit.isdecimal()
                               or not 1 <= int(limit) <= 100):
            raise _error(422, "invalid_run_limit")
        needle = q.strip().casefold() if q is not None else None
        if needle == "":
            raise _error(422, "invalid_job_search")
        outcome_filter = outcome.strip().casefold() if outcome is not None else None
        if outcome_filter == "":
            raise _error(422, "invalid_outcome_filter")
        if executor is not None and not executor.strip():
            raise _error(422, "invalid_executor_filter")
        if updated_from and updated_to and updated_from > updated_to:
            raise _error(422, "invalid_date_range")
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
                   })
                   and (lifecycle is None or row["lifecycle"] == lifecycle)
                   and (stage is None or row["stage"] == stage)
                   and (executor is None or executor in row["observed_executors"])
                   and (outcome_filter is None or outcome_filter in row["outcome"].casefold())
                   and (not (updated_from or updated_to) or row["updated_at"] is not None
                        and (updated_from is None
                             or datetime.fromisoformat(row["updated_at"]).date() >= updated_from)
                        and (updated_to is None
                             or datetime.fromisoformat(row["updated_at"]).date() <= updated_to))]
        page_limit = len(matched) if limit == "all" else int(limit)
        visible = [{key: value for key, value in row.items()
                    if key not in {"timeline", "observed_executors"}}
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
        return {"job": {key: value for key, value in row.items()
                        if key != "observed_executors"}, "complete": True, "snapshot": revision}

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
        stage: Literal["frame", "specify", "design", "build", "validate", "deliver"] | None = None,
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
        columns = ["date", "started", "completed", "tokens_in", "tokens_out",
                   "mr_revisions", "pipeline_repairs"]
        if admin:
            columns.extend(("reported_cost_usd", "estimated_cost_usd"))
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(columns)
        for day in view["daily"]:
            row = [day[key] for key in columns
                   if key not in ("reported_cost_usd", "estimated_cost_usd")]
            if admin:
                row.append(day["cost_usd"] if day["cost_usd"] is not None else "")
                row.append(day["estimated_cost_usd"]
                           if day["estimated_cost_usd"] is not None else "")
            writer.writerow(row)
        return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition":
                                 f'attachment; filename="adore-{item.name}-{granularity}.csv"'})

    @app.get("/api/v1/metrics.csv")
    def global_metrics_csv(
        _user: Annotated[dict, Depends(administrator)],
        day_from: date | None = None,
        day_to: date | None = None,
        timezone: Annotated[str, Query(max_length=64)] = "UTC",
        granularity: Literal["day", "week", "month"] = "day",
    ) -> Response:
        """@brief Export administrator daily costs with project provenance."""
        _check_metric_range(day_from, day_to)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(("project", "repository", "date", "started", "completed",
                         "tokens_in", "tokens_out", "mr_revisions",
                         "pipeline_repairs", "reported_cost_usd",
                         "estimated_cost_usd"))
        for item in profiles.list_profiles():
            for day in _metric_view(profiles, item, True, web, day_from,
                                    day_to, timezone, granularity)["daily"]:
                writer.writerow((
                    _csv_text(item.name), _csv_text(item.repo), day["date"],
                    day["started"], day["completed"], day["tokens_in"],
                    day["tokens_out"], day["mr_revisions"],
                    day["pipeline_repairs"],
                    day["cost_usd"] if day["cost_usd"] is not None else "",
                    day["estimated_cost_usd"]
                    if day["estimated_cost_usd"] is not None else "",
                ))
        return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition":
                                 f'attachment; filename="adore-global-{granularity}.csv"'})

    @app.get("/api/v1/metrics")
    def global_metrics(_user: Annotated[dict, Depends(administrator)],
                       day_from: date | None = None,
                       day_to: date | None = None,
                       timezone: Annotated[str, Query(max_length=64)] = "UTC",
                       granularity: Literal["day", "week", "month"] = "day") -> dict:
        _check_metric_range(day_from, day_to)
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
        _check_metric_range(day_from, day_to)
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
        _check_metric_range(day_from, day_to)
        if profiles.invalid_profiles():
            raise _error(503, "project_corrupt")
        return _usage_csv([
            (item, _usage_view(profiles, item, True, web, day_from, day_to,
                               executor, model, timezone, granularity))
            for item in profiles.list_profiles()
        ], True, True)

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
        web.audit(user["id"], "operation-submitted", item.name,
                  f"{action}:{target}")
        return {"id": operation["id"], "status": operation["status"]}

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
                ("id", "project", "action", "status", "result", "created_at", "updated_at")}

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
