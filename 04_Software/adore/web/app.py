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
import base64
import binascii
from collections.abc import Callable
from contextlib import ExitStack, contextmanager
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
import shlex
import shutil
import subprocess
import tempfile
from threading import Lock
from time import monotonic
import tomllib
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from adore import __version__, chatgpt, doctor, metrics
from adore.aegis import RUN_KINDS
from adore.branding import EXECUTOR_BASE_IMAGE, EXECUTOR_NAME
from adore.build_bundle import BuildBundleError, export_build_bundle
from adore.cli import _NOT_SECRET_KEYS, _SECRET_KEY_RE, _is_secret_key, _newline, _set_toml_scalar
from adore.clone_cleanup import project_clone_decision
from adore.config import (
    REMOVED_AGENT_ENV_PREFIXES,
    SELINUX_RELABEL_MODES,
    branch_naming_preview,
    default_config,
    egress_policy,
    load_config,
    valid_reviewers,
    validate_config,
)
from adore.config_edit import ConfigEditLockedError, config_edit_lock
from adore.executor_recipes import RecipeStore, effective_recipe_config, recipe_status
from adore.forge import ForgeError, ForgeResponseError
from adore.forge_labels import ensure_labels, project_labels
from adore.gitea_auth import GiteaAuthError, portable_tea_runner
from adore.isolation import ContainerManager, IsolationError
from adore.pi_providers import (
    CHATGPT,
    ENDPOINT_APIS,
    MODEL_ID_RE,
    WEB_SEARCH_CHOICES,
    credential_variable,
    provider_ids,
    public_catalog,
    search_key_variable,
)
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
from adore.project_bundle import read_project_bundle, validate_bundle_image
from adore.recipe_sources import MAX_ARCHIVE_BYTES, RecipeError, parse_recipe
from adore.release_notes import ReleaseNotesError, load_release_notes
from adore.repository_auth import (
    RepositoryAuthError,
    connection_view,
    load_connection,
    project_runner,
    save_connection,
    verify_connection,
)
from adore.selection import start_blocker, start_preparation
from adore.state import LockHeldError, StateError, StateStore
from adore.util import (
    CommandResult,
    CommandRunner,
    force_rmtree,
    load_env_file,
    run_command,
    strict_json_loads,
)
from adore.web import analytics
from adore.web.configuration import ConfigurationTasks, effect_guard, probe_timeout
from adore.web.environment import EnvironmentError, EnvironmentPreparation
from adore.web.executor_configuration import (
    CONNECTION_KEY,
    CONNECTION_KEYS,
    LAUNCH_PRESETS,
    connection_value,
    set_connection,
    valid_connection,
)
from adore.web.executor_evidence import read_executor_output
from adore.web.executor_settings import (
    PROVIDER_KEYS,
    ExecutorSettingsError,
    credential_binding,
    credential_view,
    model_evidence,
    save_model_evidence,
    update_credential,
)
from adore.web.implementation_settings import (
    COLLECTION_KEYS,
    set_collection,
    valid_collection,
)
from adore.web.jobs import JobReadError, read_job_budget, read_jobs, read_overview_jobs, sort_jobs
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
    remote_branches,
    suggest_id,
    tea_logins,
)
from adore.web.repository_source import (
    clone as clone_repository,
)
from adore.web.settings_batch import BATCH_KEY, parse_batch
from adore.web.store import WebStore, WebStoreError
from adore.web.tickets import (
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
# Optional readiness checks that follow the internet switch.
_INTERNET_CHECKS = frozenset({"egress_proxy", "web_search_key"})
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


class ChatGptRedirectInput(BaseModel):
    """@brief The browser's redirect address of a pending Sign in with ChatGPT."""
    model_config = ConfigDict(extra="forbid", strict=True)
    redirect_url: str = Field(min_length=1, max_length=8192)


#: ChatGPT sign-in cause -> API code.
_CHATGPT_CODES = {
    "redirect-invalid": "chatgpt_redirect_invalid",
    "state-mismatch": "chatgpt_state_mismatch",
    "not-pending": "chatgpt_sign_in_not_pending",
    "unreadable": "chatgpt_credential_unreadable",
    "not-eligible": "chatgpt_not_eligible",
    "denied": "chatgpt_access_denied",
    "code-rejected": "chatgpt_code_rejected",
    "refused": "chatgpt_sign_in_refused",
    "failed": "chatgpt_sign_in_refused",
    "unavailable": "chatgpt_sign_in_unavailable",
    "helper-failed": "chatgpt_helper_failed",
}
#: HTTP status of a ChatGPT sign-in cause; an OpenAI refusal is 502.
_CHATGPT_STATUS = {"redirect-invalid": 400, "state-mismatch": 400, "not-pending": 409,
                   "unreadable": 409, "unavailable": 503, "helper-failed": 503}


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
    """@brief Partial account-scoped presentation preferences.
    @details Omission preserves a field. Explicit null is not a ticket mode.
    """

    model_config = ConfigDict(extra="forbid")
    language: Literal["en", "fr", "de", "ro"] | None = None
    theme: Literal["light", "dark", "system"] | None = None
    ticket_body_mode: Literal["rendered", "source"] | None = None

    @field_validator("ticket_body_mode")
    @classmethod
    def supplied_ticket_body_mode(cls, value: str | None) -> str:
        """@brief Reject explicit null; omitted defaults are not validated."""
        if value is None:
            raise ValueError("ticket body mode must be rendered or source")
        return value


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
    execution_backend: Literal["container", "local"] = "container"
    local_account: Literal["current"] = "current"
    local_path: str = ""
    provider: str = ""
    model: str = ""
    thinking: str = ""
    endpoint_base_url: str = Field(default="", max_length=512)
    endpoint_api: str = ""
    runtime: str = "docker"
    image: str = ""
    target_branch: str = "main"
    auth_mode: Literal["api-key"] = "api-key"
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
    evidence_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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
    evidence_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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


class ProjectImportPreviewInput(ProjectImportInput):
    """@brief A raw import preview may ask the server to suggest the project ID."""

    name: str | None = Field(default=None, min_length=1, max_length=64)


class ProjectBundleImportInput(BaseModel):
    """@brief Exact exported ZIP bytes and the identity accepted during preview."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64)
    display_name: str | None = None
    description: str = Field(default="", max_length=500)
    source: str = Field(min_length=1, max_length=MAX_ARCHIVE_BYTES * 4 // 3 + 4)
    revision: str = ""


class ProjectBundlePreviewInput(ProjectBundleImportInput):
    """@brief Optional identity allows the current import naming rules to suggest one."""

    name: str | None = Field(default=None, min_length=1, max_length=64)


class ConfigEdit(BaseModel):
    """@brief One validated scalar or complete settings-batch edit."""

    key: str
    value: str
    revision: str
    pending_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RecipeInput(BaseModel):
    """@brief Bounded source attachment bound to the project and image association."""

    model_config = ConfigDict(extra="forbid")
    image: str = Field(min_length=1, max_length=255)
    source: str = Field(min_length=1, max_length=MAX_ARCHIVE_BYTES * 4 // 3 + 4)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


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

    confirmed: bool = Field(default=False, strict=True)
    idempotency_key: str = Field(min_length=8, max_length=128)


class OperationInput(BaseModel):
    """@brief A job operation including an idempotency key."""

    ticket_iid: int | None = None
    run_id: str = ""
    confirmed: bool = Field(default=False, strict=True)
    state_revision: str = ""
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
        unknown = re.match(r"\[([a-z][a-z0-9_.-]*)\] unknown key '([^']+)'", message)
        removed = re.match(r"\[([a-z]+)\] ((?:runtime_env|environment)\.[A-Za-z_][A-Za-z0-9_]*)"
                           r" configures a removed coding agent", message)
        match = re.match(r"\[([a-z][a-z0-9_.-]*)\]\s+([a-z][a-z0-9_]*)", message)
        if unknown or removed:
            # Name exactly what to delete: this build has no migration.
            field = ".".join((unknown or removed).groups())
            remediation = "Remove this key from config.toml; this build does not read it."
        else:
            field = ".".join(match.groups()) if match else "config"
            remediation = "Correct this setting using the configuration reference."
        findings.append(_finding("config_invalid", field, remediation))
    return findings


def _readiness_host() -> str:
    """@brief Bind evidence to the actual machine and service account, without exposing it."""
    from adore.local_process import LocalExecutionError, native_context

    try:
        host = native_context()["host"]
        if not isinstance(host, str) or not re.fullmatch(r"[0-9a-f]{64}", host):
            raise ValueError("invalid host identity")
        return host
    except (LocalExecutionError, KeyError, ValueError, TypeError) as exc:
        raise _error(503, "readiness_probe_failed") from exc


def _readiness_binding(profiles: ProfileStore, name: str, config) -> str:
    """@brief Privately fingerprint effective auth inputs without returning their contents.

    @details Owned credentials and the ChatGPT credential are hashed as bytes.
             External CLI configuration and relevant environment values are hashed,
             never returned or logged.
    @param[in] profiles Server profile store.
    @param[in] name Project profile name, including a not-yet-published draft.
    @param[in] config Exact candidate configuration.
    @return SHA-256 context fingerprint.
    @exception HTTPException When a relevant source cannot be inspected safely.
    """
    env_names = (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GITLAB_TOKEN",
        "GITLAB_ACCESS_TOKEN",
        "OAUTH_TOKEN",
        "GH_HOST",
        "GITLAB_HOST",
        "GH_CONFIG_DIR",
        "GLAB_CONFIG_DIR",
        "XDG_CONFIG_HOME",
        "LOCALAPPDATA",
        "APPDATA",
        "HOME",
        "USERPROFILE",
    )
    environment = {key: os.environ.get(key) for key in env_names}
    directory = profiles.profile_dir(name)
    try:
        values = {
            "host": _readiness_host(),
            "environment": environment,
            "executor": credential_binding(directory, config),
        }
        paths = [directory / "repository-auth.json"]
        if config.executor.provider == CHATGPT:
            paths.append(chatgpt.credential_dir(profiles.home) / chatgpt.AUTH_FILE)
        for index, path in enumerate(paths):
            try:
                with path.open("rb") as source:
                    raw = source.read(1048577)
            except FileNotFoundError:
                raw = b""
            if len(raw) > 1048576:
                raise ValueError("oversized credential source")
            values[f"owned-{index}"] = sha256(raw).hexdigest()
        roots = [os.environ.get(key) for key in ("XDG_CONFIG_HOME", "LOCALAPPDATA", "APPDATA")]
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        if home:
            roots.append(str(Path(home) / ".config"))
        candidates = [
            Path(root) / suffix
            for root in roots
            if root and Path(root).is_absolute()
            for suffix in ("tea/config.yml", "gh/hosts.yml", "glab-cli/config.yml")
        ]
        for key, suffix in (("GH_CONFIG_DIR", "hosts.yml"), ("GLAB_CONFIG_DIR", "config.yml")):
            root = os.environ.get(key)
            if root and Path(root).is_absolute():
                candidates.append(Path(root) / suffix)
        if home and Path(home).is_absolute():
            candidates.append(Path(home) / ".tea/tea.yml")
        for path in sorted(set(candidates), key=str):
            try:
                with path.open("rb") as source:
                    raw = source.read(1048577)
                if len(raw) > 1048576:
                    raise ValueError("oversized CLI authentication source")
                values[str(path)] = sha256(raw).hexdigest()
            except FileNotFoundError:
                values[str(path)] = None
        return sha256(json.dumps(values, sort_keys=True).encode("utf-8")).hexdigest()
    except (OSError, ValueError, TypeError, ExecutorSettingsError) as exc:
        raise _error(503, "readiness_probe_failed") from exc


def _required_readiness_checks(config) -> set[str]:
    """@brief Return exactly the prerequisite checks required by this configuration."""
    required = {
        "git",
        "forge_cli",
        "forge_auth",
        "container_runtime",
        "executor_cli",
    }
    if config.executor.provider == CHATGPT:
        required.add("executor_sign_in")
    if config.execution.backend == "container" and egress_policy(config).mode == "allowlist-proxy":
        required.add("egress_proxy")
    if search_key_variable(config.executor, config.execution.backend):
        required.add("web_search_key")
    return required


def _readiness_auth_bound(profiles: ProfileStore, name: str, config) -> bool:
    """@brief Only a project-scoped credential gives an observable forge identity source."""
    try:
        return load_connection(profiles.profile_dir(name), config) is not None
    except RepositoryAuthError as exc:
        raise _error(503, exc.code) from exc


def _workflow_observation(config) -> str:
    """@brief Describe file presence without running or modifying repository code.

    @param[in] config Configuration containing the selected clone path.
    @return AEGIS, Direct or explicitly not-inspected for an unavailable clone.
    @exception HTTPException File inspection failed rather than proving absence.
    """
    try:
        clone = Path(config.worktree.repo_path)
        if not clone.is_dir():
            return "not-inspected"
        return "aegis" if (clone / ".agentic" / "aegis.py").is_file() else "direct"
    except OSError as exc:
        raise _error(503, "readiness_probe_failed") from exc


def _valid_workflow(value: object) -> bool:
    """@brief Validate the closed descriptive workflow domain at evidence boundaries."""
    return isinstance(value, str) and value in {"aegis", "direct", "not-inspected"}


def _valid_readiness_checks(checks: object, config) -> bool:
    """@brief Fail closed on malformed probe results before any evidence publication."""
    if not isinstance(checks, dict) or set(checks) != _required_readiness_checks(config):
        return False
    return all(
        type(value) is bool
        or key == "container_runtime"
        and value is None
        for key, value in checks.items()
    )


def _verification_view(profiles: ProfileStore, profile, revision: str | None) -> dict:
    """@brief Strictly load revision-bound evidence; absent and stale remain distinct."""
    path = profiles.profile_dir(profile.name) / "readiness.json"
    if not path.exists():
        return {"status": "unverified", "revision": None, "checked_at": None}
    try:
        if path.stat().st_size > 16384:
            raise ValueError("oversized readiness")
        value = strict_json_loads(path.read_text(encoding="utf-8"))
        keys = {
            "schema",
            "project_id",
            "revision",
            "checked_at",
            "context",
            "checks",
            "host",
            "binding",
            "auth_bound",
            "workflow",
        }
        if (
            not isinstance(value, dict)
            or set(value) != keys
            or type(value["schema"]) is not int
            or value["schema"] != 3
            or not _valid_workflow(value["workflow"])
            or value["project_id"] != profile.project_id
            or not isinstance(value["revision"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["revision"])
            or value["context"] != "api-host"
            or not isinstance(value["host"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["host"])
            or type(value["auth_bound"]) is not bool
            or not isinstance(value["binding"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["binding"])
            or not isinstance(value["checked_at"], str)
        ):
            raise ValueError("invalid readiness identity")
        stamp = datetime.fromisoformat(value["checked_at"])
        if (
            stamp.tzinfo is None
            or stamp.utcoffset() != timedelta(0)
            or stamp > datetime.now(UTC) + timedelta(seconds=5)
        ):
            raise ValueError("invalid readiness time")
        checks = value["checks"]
        check_keys = {
            "git",
            "forge_cli",
            "forge_auth",
            "container_runtime",
            "executor_cli",
        }
        # Optional checks: the server's ChatGPT sign-in, the egress proxy
        # image (internet off) and the web search key (internet on).
        if (
            not isinstance(checks, dict)
            or set(checks) - {"executor_sign_in", *_INTERNET_CHECKS} != check_keys
        ):
            raise ValueError("invalid readiness checks")
        if revision == value["revision"]:
            config = _config_from_bytes(profiles.config_path(profile.name).read_bytes())
            required = _required_readiness_checks(config)
            if set(checks) != required:
                raise ValueError("missing or unexpected configured checks")
        for key, result in checks.items():
            if type(result) is not bool and not (
                key == "container_runtime"
                and result is None
            ):
                raise ValueError("invalid readiness check value")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise _contract_rejection(
            "readiness_corrupt",
            "readiness",
            "Delete readiness.json in the affected project profile and check prerequisites again.",
        ) from exc
    stale = (
        revision != value["revision"]
        or value["host"] != _readiness_host()
        or value["binding"] != _readiness_binding(profiles, profile.name, config)
    )
    if not stale and value["auth_bound"] != _readiness_auth_bound(profiles, profile.name, config):
        raise _contract_rejection(
            "readiness_corrupt",
            "readiness",
            "Delete readiness.json in the affected project profile and check prerequisites again.",
        )
    status = (
        "stale"
        if stale
        else "failed"
        if any(result is False for result in checks.values())
        else "partial"
        if not value["auth_bound"] or any(type(result) is not bool for result in checks.values())
        else "verified"
    )
    return {
        **{key: item for key, item in value.items() if key not in {"schema", "host", "binding"}},
        "status": status,
        "required_checks": sorted(checks),
    }


def _internet_checks(config, runner: CommandRunner, env_file: Path | None) -> dict:
    """
    @brief      Readiness checks that follow the internet switch.
    @details    A container project with internet off runs behind the per-run
                egress proxy, so its image must be present (never pulled); a
                project with internet on that searches with Brave or Tavily
                needs that key in the server environment or the project's
                credential store. Values are never returned.
    @param[in]  config Validated configuration snapshot.
    @param[in]  runner Bounded command runner.
    @param[in]  env_file The project's credential store.
    @return     `{"egress_proxy": bool}`, `{"web_search_key": bool}`, both or neither.
    """
    checks: dict[str, bool] = {}
    policy = egress_policy(config)
    if config.execution.backend == "container" and policy.mode == "allowlist-proxy":
        try:
            checks["egress_proxy"] = runner(
                [*shlex.split(config.container.runtime), "image", "inspect",
                 policy.proxy_image], timeout=8).ok
        except (OSError, TimeoutError, ValueError):
            checks["egress_proxy"] = False
    variable = search_key_variable(config.executor, config.execution.backend)
    if variable:
        saved = {**(load_env_file(env_file) if env_file else {}), **os.environ}
        checks["web_search_key"] = bool(saved.get(variable))
    return checks


def _setup_display(body: ProjectInput | ProjectImportInput) -> str:
    """@brief Distinguish omitted legacy-compatible input from explicit invalid null."""
    return validate_display_name(body.display_name if "display_name" in body.model_fields_set
                                 else body.name)


def _container_probe(runner: CommandRunner, argv: list[str]) -> bool:
    """@brief Check bounded container prerequisites without exposing command output."""
    try:
        result = runner(argv, timeout=8)
    except (OSError, TimeoutError):
        return False
    return (isinstance(result, CommandResult) and type(result.exit_code) is int
            and result.exit_code == 0 and type(result.timed_out) is bool
            and not result.timed_out)


def _probe_setup(config, probe_runner: CommandRunner, env_file: Path | None = None,
                 chatgpt_dir: Path | None = None, *, external_auth: bool = True) -> dict:
    """@brief Run bounded redacted prerequisites for an explicit config snapshot.

    @param[in] config Validated configuration snapshot.
    @param[in] probe_runner Injectable external command boundary.
    @param[in] env_file Existing approved provider values for native checks.
    @param[in] external_auth Discover external auth; False when project_runner owns credentials.
    @param[in] chatgpt_dir The server's ChatGPT credential directory; a ChatGPT
               project gets the check `executor_sign_in`, read from its files.
    @return Typed prerequisites, separate read-only workflow and optional native diagnostics.
    @exception HTTPException A prerequisite command fails to produce usable evidence.
    """
    deadline = monotonic() + 30
    auth_runner = (portable_tea_runner(probe_runner, login=config.platform.login)
                   if config.platform.kind == "gitea" and external_auth else probe_runner)

    def bounded_runner(argv, *, cwd=None, timeout=None, env=None):
        """@brief Keep a doctor subprocess below one request's probe bound."""
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("host readiness deadline")
        tea_auth = (argv[:2] == ["tea", "whoami"]
                    or (argv[:2] == ["tea", "api"] and argv[-1] == "user"))
        if tea_auth:
            argv = ["tea", "api", "-i", "--method", "GET"]
            if config.platform.login:
                argv += ["--login", config.platform.login]
            argv += ["user"]
        try:
            result = auth_runner(argv, cwd=cwd,
                                 timeout=min(timeout if timeout is not None else 8,
                                             8, remaining), env=env)
        except GiteaAuthError as exc:
            if not tea_auth:
                raise
            result = CommandResult(argv=list(argv), exit_code=1, stderr=exc.code)
        if tea_auth:
            identity_valid = False
            statuses = re.findall(r"HTTP/\S+\s+(\d{3})", result.stderr)
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
                identity_valid = bool(
                    isinstance(identity, dict)
                    and isinstance(identity.get("login"), str)
                    and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identity["login"]))
                valid = (result.ok and bool(statuses) and 200 <= int(statuses[-1]) < 300
                         and identity_valid)
            except (ValueError, TypeError):
                valid = False
            if not valid:
                # Classify only exact known CLI errors; never log arbitrary stderr.
                error = result.stderr.strip()
                reason = (
                    "no-logins" if error == "Error: no available login" else
                    "login-missing" if config.platform.login and error == (
                        f"Error: login name '{config.platform.login}' does not exist") else
                    "other"
                )

                def config_present(root, suffix):
                    """@brief Observe config presence without opening credential contents."""
                    if not root:
                        return "unset"
                    try:
                        return "present" if (Path(root) / suffix).is_file() else "absent"
                    except OSError:
                        return "unavailable"

                environment = os.environ if env is None else env
                logging.getLogger(__name__).warning(
                    "forge_auth_failure kind=gitea exit=%s timeout=%s http=%s "
                    "identity_valid=%s stdout_length=%s stderr_length=%s named_login=%s "
                    "reason=%s config_override=%s local_config=%s roaming_config=%s "
                    "legacy_config=%s",
                    result.exit_code, result.timed_out, statuses[-1] if statuses else "missing",
                    identity_valid, len(result.stdout), len(result.stderr),
                    bool(config.platform.login), reason,
                    config_present(environment.get("XDG_CONFIG_HOME"), "tea/config.yml"),
                    config_present(environment.get("LOCALAPPDATA"), "tea/config.yml"),
                    config_present(environment.get("APPDATA"), "tea/config.yml"),
                    config_present(environment.get("USERPROFILE") or environment.get("HOME"),
                                   ".tea/tea.yml"),
                )
                result = replace(result, exit_code=1)
        return result

    try:
        config = effective_probe_config(config, runner=bounded_runner)
        git = doctor.detect_git(bounded_runner)
        forge = doctor.detect_platform_cli(config.platform.kind, bounded_runner)
        auth = doctor.auth_status(config.platform.kind, bounded_runner, external_auth=False)
    except (OSError, UnicodeError, TypeError, ValueError,
            KeyError, TimeoutError, PreparationError) as exc:
        raise _error(503, "readiness_probe_failed") from exc
    if config.execution.backend == "local":
        from adore.local_execution import probe_local_executor

        executor_probe = probe_local_executor(config, env_file, chatgpt_dir=chatgpt_dir)
        executor = executor_probe["ready"]
        return {"workflow": _workflow_observation(config),
                "local_probe": executor_probe, "checks": {"git": git.present and not git.detail,
                            "forge_cli": forge.present and not forge.detail,
                            "forge_auth": auth.authenticated,
                            "container_runtime": True, "executor_cli": executor,
                            **({"executor_sign_in": chatgpt.status(
                                chatgpt_dir or chatgpt.credential_dir()) == "signed-in"}
                               if config.executor.provider == CHATGPT else {}),
                            **_internet_checks(config, bounded_runner, env_file)}}
    prefix = doctor.inventory_runtime_argv(config.container.runtime.strip())
    runtime_ready = bool(prefix and _container_probe(bounded_runner, [*prefix, "info"]))
    executor = False
    try:
        image_runtime = ContainerManager(
            config.container.runtime, config.container.image,
            config.container.uv_cache_volume, config.container.npm_cache_volume,
            bounded_runner, run_args=config.container.run_args, pull_never=True,
            egress=egress_policy(config),
            selinux_relabel=config.container.selinux_relabel,
        )
        executor = runtime_ready and _container_probe(bounded_runner, [
            *image_runtime.runtime_argv, "run", "--rm", "--pull=never",
            "--network", "none", "--entrypoint", "python",
            config.container.image, "-c",
            "import shutil,sys; sys.exit(0 if shutil.which(sys.argv[1]) else 1)",
            EXECUTOR_NAME,
        ])
    except (IsolationError, OSError, TimeoutError, ValueError):
        executor = False
    checks = {
        "git": git.present and not git.detail,
        "forge_cli": forge.present and not forge.detail,
        "forge_auth": auth.authenticated,
        "container_runtime": runtime_ready,
        "executor_cli": executor,
    }
    if config.executor.provider == CHATGPT:
        checks["executor_sign_in"] = (
            chatgpt.status(chatgpt_dir or chatgpt.credential_dir()) == "signed-in")
    checks.update(_internet_checks(config, bounded_runner, env_file))
    return {"workflow": _workflow_observation(config), "checks": checks}


def _prepare_project(profiles: ProfileStore, body: ProjectInput) -> tuple[dict, WizardSetup | None]:
    """@brief Validate explicit web answers without persistence or live probes."""
    try:
        available = profiles.id_availability(body.name)
        display = _setup_display(body)
    except ProfileError as exc:
        raise _identity_error(exc) from exc
    issues = (
        [] if available else [_finding("project_exists", "name", "Choose another available ID.")]
    )
    answers = body.model_dump(
        exclude={
            "name",
            "display_name",
            "env_keys",
            "revision",
            "clone_url",
            "evidence_token",
            "thinking",
        }
    )
    answers["budgets_choice"] = "custom"
    # Reviewers are optional: an empty list requests no review on the MR/PR.
    for field in ("ready_label", "approval_label", "kind", "repo", "repo_path",
                  "runtime", "target_branch", "auth_mode"):
        if not str(answers[field]).strip():
            issues.append(_finding("setup_field_invalid", field,
                                   "Supply a non-empty supported value."))
    for field in ("provider", "model", "image"):
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
    if body.env_keys is not None and (
            len(body.env_keys) > 32 or len(set(body.env_keys)) != len(body.env_keys)
            or any(not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", key) for key in body.env_keys)):
        issues.append(_finding("setup_field_invalid", "env_keys",
                               "Use unique uppercase environment names."))
    for key in ("provider", "model", "image", "endpoint_base_url", "endpoint_api"):
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
            if body.thinking:
                candidate.document = candidate.document.replace(
                    "[executor]\n", "[executor]\nthinking = " + json.dumps(body.thinking) + "\n", 1)
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
        preview["workflow"] = _workflow_observation(config)
        preview["defaults"] = _preview_defaults(candidate.document)
        # Normalize the Windows spelling for display only; preserve POSIX path case and identity.
        def shown_path(value: str) -> str:
            """@brief Present one host path consistently without changing the configuration."""
            return str(Path(value).resolve()) if os.name == "nt" else value

        preview["review"] = {
            **body.model_dump(exclude={"revision", "env_keys", "evidence_token"}),
            "display_name": display,
            "provider": config.executor.provider,
            "model": config.executor.model,
            "endpoint_base_url": (
                config.executor.endpoint.base_url if config.executor.provider == "custom" else ""
            ),
            "endpoint_api": (
                config.executor.endpoint.api if config.executor.provider == "custom" else ""
            ),
            "credential_variable": credential_variable(config.executor.provider),
            "image": config.container.image,
            "env_keys": config.executor.env_keys,
            "repo_path": shown_path(config.worktree.repo_path),
            "hold_label": config.labels.control.hold,
            "exclude_label": config.labels.control.exclude,
            "egress_mode": egress_policy(config).mode,
            "branch_template": config.worktree.branch_template,
            "config_path": str(profiles.config_path(body.name).resolve()),
            "store_root": shown_path(config.state.store_root),
            "worktree_root": shown_path(config.worktree.root),
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
    @exception  HTTPException The clone failed or lacks the target branch (removed).
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
    try:
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


def _publish_paused(
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
    readiness: dict | None = None,
) -> dict:
    """@brief Keep lock, filesystem and parsing failures typed at the enrollment boundary."""
    try:
        return _publish_paused_locked(
            profiles,
            web,
            actor,
            name,
            raw,
            metadata,
            imported=imported,
            import_body=import_body,
            recheck=recheck,
            origin=origin,
            base_revision=base_revision,
            readiness=readiness,
        )
    except (OSError, StateError, ProfileError, UnicodeError, ValueError, TypeError) as exc:
        raise _contract_rejection(
            "project_creation_failed", "config", "Check local enrollment storage before retrying."
        ) from exc


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
    readiness: dict | None = None,
) -> dict:
    """@brief Publish metadata after pause, holding ownership and conductor locks."""
    with ExitStack() as enrollment:
        enrollment.enter_context(
            _web_config_edit_lock(profiles.home / "web-enrollment" / "config.toml"))
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
        effect_guard()
        try:
            directory.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise _error(409, "project_exists") from exc
        state = StateStore(root, config.agent.slug)
        locked, released, previously_paused = False, False, False
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
            if readiness is not None and readiness["binding"] != _readiness_binding(
                profiles, name, config
            ):
                raise _error(409, "stale_config_revision")
            if readiness is not None:
                _write_pending_config(
                    directory / "readiness.json",
                    {
                        "schema": 3,
                        "workflow": readiness["workflow"],
                        "project_id": item.project_id,
                        "host": readiness["host"],
                        "binding": readiness["binding"], "auth_bound": readiness["auth_bound"],
                        "revision": sha256(raw).hexdigest(),
                        "context": "api-host",
                        "checked_at": readiness["checked_at"],
                        "checks": readiness["checks"],
                    },
                )
            if recheck is not None:
                recheck()
            result = _profile_view(profiles, item)
            # Confirm audit success only after final filesystem cleanup succeeds.
            state.release_lock()
            released = True
            enrollment.close()
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
            if locked and not released:
                state.release_lock()


@contextmanager
def _web_config_edit_lock(path: Path):
    """@brief Map shared edit-lock contention to an HTTP conflict."""
    effect_guard()
    try:
        with config_edit_lock(path):
            yield
    except ConfigEditLockedError as exc:
        raise _error(409, "config_edit_locked") from exc


def _store_for(profiles: ProfileStore, profile) -> StateStore:
    root = profile.store_root or str(profiles.default_store_root(profile.name))
    return StateStore(root)


def _removed_agent_environment(path: str) -> bool:
    """
    @brief      Whether a dotted key is an environment variable of a removed coding agent.
    @details    Validation refuses such a configuration, but the configuration view still
                renders it; its value (for example an inline provider JSON) is never shown.
    @param[in]  path Dotted configuration key.
    @return     True for `container.runtime_env.*` / `local.environment.*` removed-agent names.
    """
    for section in ("container.runtime_env.", "local.environment."):
        if path.startswith(section):
            return path[len(section):].upper().startswith(REMOVED_AGENT_ENV_PREFIXES)
    return False


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
            if (_is_secret_key(path) or _removed_agent_environment(path)
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


def _profile_view(profiles: ProfileStore, profile, *, overview: bool = False) -> dict:
    """
    @brief Project profile metadata and verified job activity.
    @param[in] profiles Profile storage.
    @param[in] profile Authorized profile.
    @param[in] overview Keep the profile available when a job has invalid activity.
    @return Project metadata with only verified activity and run counts.
    """
    if any(not isinstance(value, str) for value in (
        profile.name, profile.description, profile.platform, profile.repo,
        profile.runtime, profile.display_name,
    )):
        raise _error(503, "project_corrupt")
    store = _store_for(profiles, profile)
    invalid_runs = set(store.invalid_runs())
    runs = store.list_runs()
    run_count = len(runs)
    last_activity: datetime | None = None
    for run in runs:
        try:
            changed = datetime.fromisoformat(run.updated_at)
            if changed.tzinfo is None or changed.utcoffset() is None:
                raise ValueError("naive activity timestamp")
            changed = changed.astimezone(UTC)
        except (TypeError, ValueError, OverflowError) as exc:
            if not overview:
                raise _error(503, "run_state_corrupt") from exc
            invalid_runs.add(run.run_id)
            run_count -= 1
            continue
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
        "archived"
        if profile.archived
        else "invalid-state"
        if invalid_runs
        else "paused"
        if paused
        else "needs-config"
        if not config_valid
        else "configured"
    )
    return {
        "id": profile.project_id,
        "name": profile.name,
        "display_name": profile.display_name,
        "validation": {"structural_valid": config_valid, "issues": findings},
        "pickup_state": "archived" if profile.archived else "stopped" if paused else "active",
        "verification": _verification_view(profiles, profile, revision if config_valid else None),
        "verification_requirements": sorted(_required_readiness_checks(config))
        if config_valid
        else [],
        "description": profile.description,
        "platform": config.platform.kind if config_valid and config else profile.platform,
        "repo": config.platform.repo if config_valid and config else profile.repo,
        "runtime": ("local" if config.execution.backend == "local" else config.container.runtime)
        if config_valid and config
        else profile.runtime,
        "executor": EXECUTOR_NAME if config_valid and config else "",
        "config_valid": config_valid,
        "readiness": readiness,
        "last_activity": last_activity.isoformat() if last_activity else None,
        "archived": profile.archived,
        "paused": paused,
        "invalid_runs": sorted(invalid_runs),
        "runs": run_count,
    }


def _valid_candidate_scalar(key: str, proposed: object, backend: str = "container") -> bool:
    """
    @brief Enforce scalar types and the dedicated reviewer-list type for pending edits.
    @param[in] key TOML file key of the single candidate edit.
    @param[in] proposed Parsed candidate value.
    @return True for a declared scalar type or an exact approved collection.
    """
    if key == BATCH_KEY:
        return (isinstance(proposed, dict) and 1 <= len(proposed) <= 100
                and all(_editable_setting_key(member) and not _external_environment_key(member)
                        and member != BATCH_KEY
                        and _valid_candidate_scalar(member, item, backend)
                        for member, item in proposed.items()))
    if key in COLLECTION_KEYS:
        return valid_collection(key, proposed)
    if key == CONNECTION_KEY:
        return valid_connection(proposed)
    if key == "delivery.reviewers":
        return valid_reviewers(proposed)
    if key in {"container.image", "container.runtime"}:
        return _valid_environment_value(key, proposed)
    if key.endswith(".command"):
        return backend != "local" and proposed in _LAUNCH_PRESETS.get(key, ())
    expected = _value_at(default_config().to_dict(), key)
    if key == "executor.model":
        return isinstance(proposed, str) and MODEL_ID_RE.fullmatch(proposed) is not None
    if type(expected) is float:
        return type(proposed) in (int, float) and math.isfinite(proposed)
    if isinstance(expected, str | int | bool):
        return type(proposed) is type(expected)
    if key.startswith("workflow.kind_labels."):
        return isinstance(proposed, str) and proposed in RUN_KINDS
    if key.startswith("workflow.stage_timeout_overrides."):
        return type(proposed) is int and proposed > 0
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
    if key == BATCH_KEY:
        for member, wire in parse_batch(value):
            if _external_environment_key(member):
                raise _error(400, "environment_managed_externally")
            if not _editable_setting_key(member):
                raise _error(400, "setting_not_editable")
            text = _set_candidate_value(text, member, wire)
        return text
    if key in COLLECTION_KEYS:
        return set_collection(text, key, value)
    if key == CONNECTION_KEY:
        return set_connection(text, value)
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


def _candidate_value(tree: dict, key: str, wire: str = ""):
    """@brief Read one scalar or collection value, or the complete connection review."""
    if key == BATCH_KEY:
        return {member: _candidate_value(tree, member) for member, _ in parse_batch(wire)}
    return connection_value(tree) if key == CONNECTION_KEY else _value_at(tree, key)


def _candidate_config_edit(path: Path, body: ConfigEdit) -> tuple[bytes, str]:
    """@brief Produce one validated scalar or reviewer-list edit without changing live TOML."""
    if not _editable_setting_key(body.key):
        raise _error(400, "setting_not_editable")
    try:
        raw = path.read_bytes()
        if not secrets.compare_digest(sha256(raw).hexdigest(), body.revision):
            raise _error(409, "stale_config_revision")
        current = raw.decode("utf-8")
        if body.key.endswith(".command") and (
            not _valid_candidate_scalar(body.key, body.value,
                    tomllib.loads(current).get("execution", {}).get("backend", "container"))
            or not isinstance(_value_at(tomllib.loads(current), body.key), str | None)
        ):
            raise _error(400, "invalid_config")
        changed = _set_candidate_value(current, body.key, body.value)
        parsed_change = tomllib.loads(changed)
        if not _valid_candidate_scalar(
            body.key, _candidate_value(parsed_change, body.key, body.value),
            parsed_change.get("execution", {}).get("backend", "container")
        ):
            raise _error(400, "invalid_config")
        if _secret_config_keys({"setting": _candidate_value(parsed_change, body.key, body.value)}):
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


def _prepare_config_candidate(path: Path, body: ConfigEdit,
                              runner: CommandRunner) -> tuple[bytes, str, dict]:
    """@brief Build one canonical candidate for no-write preview or preparation.
    @param[in] path Active project configuration.
    @param[in] body Exact scalar or batch edit and inspected base revision.
    @param[in] runner Injectable read-only execution-plan command boundary.
    @return Active bytes, candidate TOML and current-format candidate record.
    @exception HTTPException Invalid edits, stale source or unavailable plan.
    """
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
        "restart_required": _restart_required(body.key, body.value),
    }
    candidate_config = _config_from_bytes(changed.encode())
    if (candidate_config.execution.preparation
            or candidate_config.execution.backend == "local"):
        try:
            value["execution_plan"] = preview_plan(candidate_config, runner=runner)
        except PreparationError as exc:
            raise _error(400, "execution_plan_invalid", message=str(exc)) from exc
    if sha256(path.read_bytes()).hexdigest() != value["base_revision"]:
        raise _error(409, "stale_config_revision")
    _public_pending_config(value, active_text=raw.decode("utf-8"))
    return raw, changed, value


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
                or value["restart_required"] != _restart_required(value["key"], value["value"])
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
            isinstance(value.get("key"), str) and _external_environment_key(value["key"])):
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
        if not _editable_setting_key(value["key"]):
            raise ValueError("unreviewable setting")
        proposed = _candidate_value(candidate, value["key"], value["value"])
        if not _valid_candidate_scalar(value["key"], proposed,
                                       candidate.get("execution", {}).get("backend", "container")):
            raise ValueError("invalid proposed value")
        if _secret_config_keys({"setting": proposed}):
            raise ValueError("unsafe proposed value")
        claimed = (_candidate_value(
                       tomllib.loads(_set_candidate_value("", value["key"], value["value"])),
                       value["key"], value["value"])
                   if value["key"] == BATCH_KEY else strict_json_loads(value["value"])
                   if value["key"] in COLLECTION_KEYS or value["key"] == CONNECTION_KEY
                   else _value_at(tomllib.loads(_set_candidate_value(
                       "", value["key"], value["value"])), value["key"]))
        if type(claimed) is not type(proposed) or claimed != proposed:
            raise ValueError("candidate review metadata differs from its value")
        if ((value["key"] in COLLECTION_KEYS
                or value["key"] in {CONNECTION_KEY, BATCH_KEY})
                and active_text is not None
                and sha256(active_text.encode("utf-8")).hexdigest() == value["base_revision"]
                and candidate != tomllib.loads(_set_candidate_value(
                    active_text, value["key"], value["value"]))):
            raise ValueError("candidate changed unrelated settings")
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
    except (HTTPException, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        raise _error(503, "pending_config_corrupt") from exc
    return public


def _restart_required(key: str, wire: str = "") -> bool:
    """@brief Classify edits that change project identity or runtime wiring."""
    if key == BATCH_KEY:
        return any(_restart_required(member) for member, _ in parse_batch(wire))
    return key.startswith(("agent.", "platform.", "worktree.",
                           "container.", "execution.", "local.", "executor."))


# Environment settings an administrator chooses in the web (reviewed edits only).
_CHOSEN_ENVIRONMENT_KEYS = frozenset({
    "execution.backend", "container.runtime", "container.image", "container.system_packages",
    "container.build_definition",
    "local.path",
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
        return isinstance(value, str) and (
            bool(_RUNTIME_COMMAND.fullmatch(value))
            or doctor.inventory_runtime_argv(value) is not None
        )
    return True


def _external_environment_key(key: str) -> bool:
    """@brief Identify externally owned environment keys at web mutation boundaries.
    @param[in] key Dotted configuration key.
    @return True for operator-owned environment settings.
    """
    return (key not in {"worktree.branch_template", "worktree.branch_rule"}
            and key not in _CHOSEN_ENVIRONMENT_KEYS
            and not _is_secret_key(key)
            and key.startswith(("container.", "execution.", "local.", "worktree.")))


def _editable_setting_key(key: str) -> bool:
    """
    @brief      The one rule for which configuration keys the web may edit.
    @details    Used by the edit endpoints and by the per-setting metadata the
                configuration view returns, so the two always agree.
    @param[in]  key Dotted TOML key.
    @return     True when the key may be staged from the browser.
    """
    if key in {"metrics.db_path", "metrics.export_jsonl", "metrics.html_out",
               "workflow.aegis_python", "workflow.verify_command"}:
        return False
    if key in {"clarification.answer_timeout", "clarification.max_rounds",
               CONNECTION_KEY, BATCH_KEY}:
        return True
    if key in CONNECTION_KEYS:
        return False
    return not (
        _is_secret_key(key)
        or not _SETTING_KEY_RE.fullmatch(key)
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
    @param[in] config Redacted configuration; provider names and presets supply choices.
    @param[in] declared Built-in model default supplying the declared type.
    @return Type, allowed choices and inclusive numeric bounds for browser guidance.
    @note Full configuration validation remains authoritative for dependent rules.
    """
    expected = declared
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
        "executor.provider": list(provider_ids()),
        "executor.endpoint.api": list(ENDPOINT_APIS),
        "executor.env_keys": sorted(
            PROVIDER_KEYS | set(config.get("executor", {}).get("env_keys", []))),
        "clarification.timeout_state": ["failed", "stale"],
        "container.selinux_relabel": list(SELINUX_RELABEL_MODES),
        "container.parked_ttl_mode": ["seconds", "polls"],
        "executor.web.search": list(WEB_SEARCH_CHOICES),
        "execution.backend": ["container", "local"],
        "delivery.draft": [True, False],
        "review.trigger": ["label"],
        "review.on_pipeline_failure": ["revise", "notify", "ignore"],
        "workflow.default_kind": list(RUN_KINDS),
        "reconcile.on_ticket_deleted": ["abort-cleanup", "ignore"],
        "reconcile.on_ticket_closed": ["cancel", "ignore"],
        "reconcile.on_trigger_removed": ["pause", "abort", "ignore"],
    }.get(key, [])
    if key in _LAUNCH_PRESETS:
        choices = list(_LAUNCH_PRESETS[key])
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
                project's TOML file. A setting is from the
                project when its key is a leaf of the file, whatever its
                value; it is editable when the shared key rule accepts the
                key and its value has a supported scalar or closed collection type. Its
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
    for key, value in leaves:
        edit_key = CONNECTION_KEY if key in CONNECTION_KEYS else key
        settings.append({
            "key": key,
            "edit_key": edit_key,
            "source": "project" if (key in in_file or edit_key in COLLECTION_KEYS
                                     and any(k.startswith(edit_key + ".") for k in in_file))
            else "default",
            "editable": (not _external_environment_key(edit_key)
                         and _editable_setting_key(edit_key)
                         and not (edit_key == "executor.command"
                                  and config.get("execution", {}).get("backend") == "local")
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
    effect_guard()
    descriptor, candidate_name = tempfile.mkstemp(prefix="pending-config-", dir=path.parent)
    candidate = Path(candidate_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        effect_guard()
        candidate.replace(path)
    finally:
        candidate.unlink(missing_ok=True)


def _secret_config_keys(value: object, prefix: str = "") -> list[str]:
    """@brief Find embedded secret values without returning their contents."""
    if isinstance(value, list):
        return [key for child in value for key in _secret_config_keys(child, prefix)]
    if not isinstance(value, dict):
        return []
    found = []
    for key, child in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if name in _NOT_SECRET_KEYS and type(child) is bool:
            continue
        if _SECRET_KEY_RE.search(key) and child:
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
            found.extend(_secret_config_keys(child, name))
    return found


def _import_preview_identity(profiles: ProfileStore,
                             body: ProjectImportPreviewInput) -> ProjectImportInput:
    """@brief Resolve an optional preview ID without changing the submitted TOML.
    @param[in] profiles Current ownership store.
    @param[in] body Preview text and optional identity overrides.
    @return Exact preview input with an explicit project identity.
    @exception HTTPException Invalid encoding, oversized text or unavailable identity.
    """
    if body.name is not None:
        return body
    try:
        if len(body.config_text.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise _error(413, "config_too_large")
    except UnicodeError as exc:
        raise _error(400, "config_invalid") from exc
    try:
        platform = tomllib.loads(body.config_text).get("platform")
    except (ValueError, RecursionError):
        platform = None  # The exact inspection returns the file's structural findings.
    repo = platform.get("repo") if isinstance(platform, dict) else None
    # Suggest names only from repository identifiers, never from URLs or userinfo.
    label = (repo.rsplit("/", 1)[-1]
             if isinstance(repo, str) and re.fullmatch(r"[\w.-]+(?:/[\w.-]+)*", repo)
             else "project")

    def available(name: str) -> bool:
        """@brief Skip reserved ID spellings and propagate ownership errors."""
        try:
            return profiles.id_availability(name)
        except ProfileError as exc:
            if exc.code == "invalid_project_name":
                return False
            raise

    try:
        name = suggest_id(label, available)
    except RepositorySourceError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "project_exists",
                    "issues": [_finding("project_exists", "name", "Choose another ID.")]},
        ) from exc
    except ProfileError as exc:
        raise _identity_error(exc) from exc
    except OSError as exc:
        raise _contract_rejection("project_creation_failed", "config",
                                  "Check server profile storage.") from exc
    identity = {"name": name}
    if "display_name" not in body.model_fields_set:
        try:
            identity["display_name"] = validate_display_name(label)
        except ProfileError:
            identity["display_name"] = name
    return body.model_copy(update=identity)


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
                      "executor": {"provider": config.executor.provider,
                                   "model": config.executor.model,
                                   "endpoint_base_url": (
                                       config.executor.endpoint.base_url
                                       if config.executor.provider == "custom" else ""),
                                   "env_keys": config.executor.env_keys},
                      "container": {"runtime": ("local" if config.execution.backend == "local"
                                                else config.container.runtime),
                                    "image": config.container.image,
                                    "egress": egress_policy(config).mode}}
    except (AttributeError, TypeError, ValueError, RecursionError):
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


def _inspect_bundle_import(profiles: ProfileStore, body: ProjectBundlePreviewInput,
                           runner: CommandRunner):
    """
    @brief Bind exact ZIP bytes to native import inspection and image associations.
    @param[in] profiles Current project and source ownership store.
    @param[in] body Untrusted bounded base64 source and optional identity.
    @param[in] runner Existing bounded Git reader for preparation-selected images.
    @return Preview, native import input, complete bundle and association revisions.
    @exception RecipeError Invalid archive, mismatched image or corrupt/conflicting sources.
    @exception HTTPException Invalid configuration or ownership inspection failure.
    """
    try:
        source = base64.b64decode(body.source, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RecipeError("bundle_invalid") from exc
    bundle = read_project_bundle(source)
    identity = {key: getattr(body, key) for key in ("name", "display_name", "description")
                if key in body.model_fields_set}
    native = _import_preview_identity(profiles, ProjectImportPreviewInput(
        config_text=bundle.config_raw.decode("utf-8"), **identity))
    preview, config = _inspect_project_import(profiles, native)
    revisions = {}
    if preview["validation"]["structural_valid"]:
        validate_bundle_image(bundle, config, runner=runner)
        revisions = RecipeStore(profiles.home).preview_import(bundle.recipe)
    native = native.model_copy(update={"revision": preview["revision"]})
    bundle_revision = sha256(source).hexdigest()
    revision = sha256(json.dumps({"bundle": bundle_revision, "config": preview["revision"],
                                 "bindings": revisions}, sort_keys=True).encode()).hexdigest()
    return ({**preview, "revision": revision, "bundle_revision": bundle_revision},
            native, bundle, revisions)


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
            web.reconcile_usage(profile.project_id, run.run_id, events,
                                current_source=lambda run_id=run.run_id:
                                    analytics.read_sources(store, run_id=run_id)[0][1])
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
               *, probe_runner: CommandRunner = run_command,
               environment_runner: CommandRunner | None = None,
               chatgpt_popen: Callable[..., subprocess.Popen] = subprocess.Popen) -> FastAPI:
    """
    @brief Construct the optional web service for a profile home.
    @param[in] home ADORE_HOME override used by tests and deployment.
    @param[in] probe_runner Injectable runner for explicit readiness probes.
    @param[in] environment_runner Optional separate boundary for shared image preparation.
    @param[in] chatgpt_popen Process factory of the ChatGPT sign-in helper.
    @return Configured FastAPI application.
    """
    def guarded_runner(original):
        """@brief Fence each external command using the current task's authority and budget."""
        def run(*args, **kwargs):
            """@brief Authorize and bound the command, then recheck before retaining its result."""
            effect_guard()
            kwargs["timeout"] = probe_timeout(kwargs.get("timeout"))
            result = original(*args, **kwargs)
            effect_guard()
            return result
        return run

    probe_runner = guarded_runner(probe_runner)
    if environment_runner is not None:
        environment_runner = guarded_runner(environment_runner)

    profiles = ProfileStore(home)
    web = WebStore(profiles.home / "web.db")
    configuration = ConfigurationTasks(profiles, web)
    environment = EnvironmentPreparation(profiles.home, environment_runner or probe_runner)
    enrollment_evidence: dict[str, tuple[int, str, str, float, dict]] = {}
    enrollment_lock = Lock()

    def issue_evidence(
        actor: int, draft_revision: str, config_revision: str, evidence: dict
    ) -> str:
        """@brief Retain bounded, expiring server-owned evidence for one creation."""
        with enrollment_lock:
            now = monotonic()
            for key in [key for key, value in enrollment_evidence.items() if value[3] < now]:
                del enrollment_evidence[key]
            if len(enrollment_evidence) >= 256:
                raise _error(503, "readiness_probe_failed")
            token = secrets.token_hex(32)
            enrollment_evidence[token] = (
                actor,
                draft_revision,
                config_revision,
                now + 900,
                evidence,
            )
            return token

    def consume_evidence(
        token: str | None, actor: int, draft_revision: str, config_revision: str,
        name: str, config,
    ) -> dict | None:
        """@brief Refuse unissued, expired, replayed or differently bound evidence."""
        if token is None:
            return None
        with enrollment_lock:
            stored = enrollment_evidence.pop(token, None)
        if (
            stored is None
            or stored[:3] != (actor, draft_revision, config_revision)
            or stored[3] < monotonic()
            or stored[4]["host"] != _readiness_host()
            or stored[4]["binding"] != _readiness_binding(profiles, name, config)
        ):
            raise _error(409, "stale_config_revision")
        return stored[4]

    # The server's one ChatGPT sign-in and at most one sign-in waiting for its
    # redirect address (memory only: a restart ends a pending sign-in).
    chatgpt_dir = chatgpt.credential_dir(profiles.home)
    chatgpt_lock = Lock()
    chatgpt_pending: dict[str, chatgpt.SignIn | None] = {"session": None}
    app = FastAPI(title="ADORE", version=__version__, docs_url=None, redoc_url=None)
    app.state.web_store = web
    app.state.profiles = profiles
    app.state.configuration_tasks = configuration

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
                       "/api/v1/projects/transfer-create", "/api/v1/projects/setup-environment",
                       "/api/v1/projects/import-environment",
                       "/api/v1/projects/transfer-environment"}
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
        effect_guard()
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
            effect_guard()
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
        return {"status": "ready", "worker": "ready", "activity": web.worker_activity()}

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
        try:
            user["factory_password"] = web.factory_password(user["id"])
        except WebStoreError as exc:
            raise _error(503, "account_credentials_corrupt") from exc
        return {"user": user, "csrf": csrf}

    @app.get("/api/v1/me")
    def me(user: Annotated[dict, Depends(account_principal)]) -> dict:
        try:
            factory_password = web.factory_password(user["id"])
        except WebStoreError as exc:
            raise _error(503, "account_credentials_corrupt") from exc
        return {"user": {**{key: value for key, value in user.items() if key != "csrf"},
                         "factory_password": factory_password}, "csrf": user["csrf"]}

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
        """@brief Save supplied presentation preferences for the current account."""
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
        overview: bool = False,
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
            view = _profile_view(profiles, item, overview=overview)
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
    @configuration.route(lane="long")
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

    @app.get("/api/v1/host-folders")
    def host_folders(response: Response,
                     _user: Annotated[dict, Depends(administrator)],
                     path: Annotated[str | None, Query(max_length=4096)] = None) -> dict:
        """@brief List bounded directory metadata on the host for administrator clone selection."""
        from adore.web.host_folders import HostFolderError, list_host_folders

        response.headers["Cache-Control"] = "no-store"
        try:
            return list_host_folders(path)
        except HostFolderError as exc:
            raise _error(400, "host_folder_unavailable") from exc

    @app.get("/api/v1/local-executors")
    def local_executors(response: Response,
                        _user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Read native host executor suggestions without executing any CLI."""
        from adore.executor_discovery import discover_executors
        from adore.local_process import LocalExecutionError

        response.headers["Cache-Control"] = "no-store"
        try:
            return discover_executors()
        except LocalExecutionError as exc:
            raise _error(503, "local_host_identity_unavailable") from exc


    @app.get("/api/v1/pi-providers")
    def pi_providers(_user: Annotated[dict, Depends(principal)]) -> dict:
        """@brief Pi's API-key providers and models (pinned catalog) plus chatgpt/custom."""
        try:
            return public_catalog()
        except ValueError as exc:
            raise _error(503, "provider_catalog_unavailable") from exc

    @app.get("/api/v1/executor-runtimes")
    def executor_runtimes(response: Response,
                          _user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief List bounded host container CLI suggestions for administrators."""
        response.headers["Cache-Control"] = "no-store"
        return {"commands": doctor.discover_container_commands(probe_runner)}

    @app.get("/api/v1/executor-images")
    def executor_images(runtime: Annotated[str, Query(max_length=160)],
                        _user: Annotated[dict, Depends(administrator)]) -> dict:
        """
        @brief Tagged container images on the ADORE server, for image suggestions.
        @details Read-only and bounded; a runtime that cannot be queried is reported
                 as unavailable rather than as an error.
        """
        prefix = doctor.inventory_runtime_argv(runtime)
        if prefix is None or (prefix[0] == doctor.WSL and doctor.detect_os() != "windows"):
            raise _error(422, "invalid_request", "Unsupported runtime for image listing.")
        result = probe_runner([*prefix, "images", "--format", "{{.Repository}}:{{.Tag}}"],
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
        try:
            branches = remote_branches(listing.stdout)
        except RepositorySourceError as exc:
            raise _error(502, "repository_branches_invalid") from exc
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
                "default_branch": default_branch(listing.stdout), "branches": branches,
                "name": name,
                "display_name": parsed.name, "repo_path": str(path),
                "clone": "existing" if path.exists() else "new"}

    @app.post("/api/v1/projects/setup-preview")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def preview_project_setup(
        body: ProjectInput, _user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Preview exact setup and separate direct-only file hints, without probes."""
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
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def preview_transfer_source(
        body: TransferSourceInput, request: Request, _user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Review only recognized portable rules without target writes or probes."""
        return transfer_source(body, request)

    def prepare_transfer(body: TransferInput, request: Request):
        """@brief Bind an exact source to freshly supplied independent target setup."""
        source = transfer_source(body, request)
        if not secrets.compare_digest(body.source_revision, source["source_revision"]):
            raise _error(409, "portable_settings_changed")
        return _prepare_transfer(profiles, body, source["settings"])

    @app.post("/api/v1/projects/transfer-preview")
    @configuration.route(scope="global", lane="long", resource="enrollment")
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
            raise HTTPException(
                status_code=409 if duplicate else 400,
                detail={
                    "code": "project_exists" if duplicate else "project_setup_invalid",
                    "issues": preview["issues"],
                },
            )
        if not secrets.compare_digest(body.revision, preview["revision"]):
            raise _error(409, "portable_settings_changed")
        return preview, candidate

    @app.post("/api/v1/projects/transfer-check")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def check_transfer(
        body: ReviewedTransferInput,
        request: Request,
        _user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Explicitly probe exact target; reread authorization/source after probes."""
        preview, candidate = reviewed_transfer(body, request)
        host = _readiness_host()
        config = _config_from_bytes(candidate.document.encode())
        binding = _readiness_binding(profiles, body.target.name, config)
        auth_bound = _readiness_auth_bound(profiles, body.target.name, config)
        evidence = _probe_setup(config, probe_runner, chatgpt_dir=chatgpt_dir)
        reviewed_transfer(body, request)
        if (
            host != _readiness_host()
            or binding != _readiness_binding(profiles, body.target.name, config)
            or auth_bound != _readiness_auth_bound(profiles, body.target.name, config)
        ):
            raise _error(409, "stale_config_revision")
        if not isinstance(evidence, dict) or not _valid_workflow(evidence.get("workflow")):
            raise _error(503, "readiness_probe_failed")
        checks = evidence.get("checks")
        if not _valid_readiness_checks(checks, config):
            raise _error(503, "readiness_probe_failed")
        status = (
            "failed"
            if any(value is False for value in checks.values())
            else "partial"
            if not auth_bound or any(type(value) is not bool for value in checks.values())
            else "verified"
        )
        checked_at = datetime.now(UTC).isoformat()
        token = issue_evidence(
            _user["id"],
            preview["revision"],
            preview["config_revision"],
            {
                "checked_at": checked_at,
                "checks": dict(checks),
                "workflow": evidence["workflow"],
                "host": host,
                "binding": binding,
                "auth_bound": auth_bound,
            },
        )
        return {
            **evidence,
            "status": status,
            "revision": preview["config_revision"],
            "draft_revision": preview["revision"],
            "context": "api-host",
            "checked_at": checked_at,
            "evidence_token": token,
            "required_checks": sorted(checks),
            "auth_bound": auth_bound,
        }

    def prepare_environment(config, user: dict, name: str) -> dict:
        """Start shared preparation only after the enrollment's exact review passes."""
        try:
            job = environment.prepare(config)
        except EnvironmentError as exc:
            raise _error(503, exc.code) from exc
        web.audit(user["id"], "environment-preparation-started", name)
        return job

    @app.get("/api/v1/environment-preparations/{job_id}")
    def read_environment_preparation(job_id: str,
                                     _user: Annotated[dict, Depends(administrator)]) -> dict:
        """Expose only bounded, value-free progress to server administrators."""
        try:
            job = environment.read(job_id)
        except EnvironmentError as exc:
            raise _error(503, exc.code, "Delete ADORE_HOME/environment/jobs/" + job_id
                + ".json to discard corrupt preparation evidence before starting fresh.") from exc
        if job is None:
            raise _error(404, "environment_preparation_expired")
        return job

    @app.post("/api/v1/projects/transfer-environment", status_code=202)
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def prepare_transfer_environment(body: ReviewedTransferInput, request: Request,
                                    user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        _preview, candidate = reviewed_transfer(body, request)
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        return prepare_environment(config, user, body.target.name)

    @app.post("/api/v1/projects/transfer-create")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def create_transfer(
        body: ReviewedTransferInput,
        request: Request,
        user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Atomically publish fresh stopped target with source/role rechecks."""
        _preview, candidate = reviewed_transfer(body, request)
        config = _config_from_bytes(candidate.document.encode())
        readiness = consume_evidence(
            body.evidence_token,
            user["id"],
            _preview["revision"],
            _preview["config_revision"],
            body.target.name,
            config,
        )

        def recheck() -> None:
            """@brief Reauthorize/reinspect source and independent ownership before visibility."""
            source = transfer_source(body, request)
            if not secrets.compare_digest(body.source_revision, source["source_revision"]):
                raise _error(409, "portable_settings_changed")
            _transfer_paths(profiles, config, body.target.name, own_target=True)

        def publish() -> dict:
            return _publish_paused(
                profiles,
                web,
                user["id"],
                body.target.name,
                candidate.document.encode(),
                candidate.metadata,
                recheck=recheck,
                origin="project-cloned" if body.method == "project" else "settings-imported",
                base_revision=body.source_revision,
                readiness=readiness,
            )

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
            raise HTTPException(
                status_code=409 if duplicate else 400,
                detail={
                    "code": ("project_exists" if duplicate else "project_setup_invalid"),
                    "issues": preview["issues"],
                },
            )
        if not secrets.compare_digest(body.revision, preview["revision"]):
            raise _error(409, "stale_config_revision")
        return preview, candidate

    @app.post("/api/v1/projects/setup-environment", status_code=202)
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def prepare_setup_environment(body: ReviewedProjectInput,
                                  user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        _preview, candidate = reviewed_setup(body)
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        return prepare_environment(config, user, body.name)

    @app.post("/api/v1/projects/setup-check")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def check_project_setup(
        body: ReviewedProjectInput, _user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Explicitly probe a reviewed draft without storing or publishing it.

        @param[in] body Reviewed answers and candidate revision.
        @param[in] _user Authorized administrator after CSRF validation.
        @return Redacted checks, status, time and exact draft/config revisions.
        @exception HTTPException Setup or probe failure is returned deterministically.
        """
        preview, candidate = reviewed_setup(body)
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        host = _readiness_host()
        binding = _readiness_binding(profiles, body.name, config)
        auth_bound = _readiness_auth_bound(profiles, body.name, config)
        evidence = _probe_setup(config, probe_runner, chatgpt_dir=chatgpt_dir)
        reviewed_setup(body)
        if (
            host != _readiness_host()
            or binding != _readiness_binding(profiles, body.name, config)
            or auth_bound != _readiness_auth_bound(profiles, body.name, config)
        ):
            raise _error(409, "stale_config_revision")
        if not isinstance(evidence, dict) or not _valid_workflow(evidence.get("workflow")):
            raise _error(503, "readiness_probe_failed")
        checks = evidence.get("checks")
        if not _valid_readiness_checks(checks, config):
            raise _error(503, "readiness_probe_failed")
        status = (
            "failed"
            if any(value is False for value in checks.values())
            else "partial"
            if not auth_bound or any(type(value) is not bool for value in checks.values())
            else "verified"
        )
        checked_at = datetime.now(UTC).isoformat()
        token = issue_evidence(
            _user["id"],
            preview["revision"],
            preview["config_revision"],
            {
                "checked_at": checked_at,
                "checks": dict(checks),
                "workflow": evidence["workflow"],
                "host": host,
                "binding": binding,
                "auth_bound": auth_bound,
            },
        )
        return {
            **evidence,
            "status": status,
            "revision": preview["config_revision"],
            "draft_revision": preview["revision"],
            "context": "api-host",
            "checked_at": checked_at,
            "evidence_token": token,
            "required_checks": sorted(checks),
            "auth_bound": auth_bound,
        }

    @app.post("/api/v1/projects/setup-create")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def create_reviewed_project(
        body: ReviewedProjectInput, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Publish only the exact reviewed configuration with pickup stopped.

        @param[in] body Reviewed answers and candidate revision.
        @param[in] user Authorized administrator recorded in the audit.
        @return Complete project whose pickup is already stopped.
        @exception HTTPException Invalid, stale or conflicting setup is rejected.
        """
        _preview, candidate = reviewed_setup(body)
        config = _config_from_bytes(candidate.document.encode("utf-8"))
        readiness = consume_evidence(body.evidence_token, user["id"], _preview["revision"],
                                     _preview["config_revision"], body.name, config)
        return _publish_with_clone(body, probe_runner, profiles.home, lambda: _publish_paused(
            profiles, web, user["id"], body.name, candidate.document.encode("utf-8"),
            candidate.metadata, readiness=readiness))

    @app.post("/api/v1/projects")
    @configuration.route(scope="global", lane="long", resource="enrollment")
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
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def preview_project_import(
        body: ProjectImportPreviewInput,
        _user: Annotated[dict, Depends(admin_mutation)],
    ) -> dict:
        """@brief Review an unchanged TOML import before saving it."""
        candidate = _import_preview_identity(profiles, body)
        preview, _config = _inspect_project_import(profiles, candidate)
        web.audit(
            _user["id"],
            "toml-import-prepared",
            phase="prepare",
            result="prepared",
            resource_type="project",
            resource_id=candidate.name,
            candidate_revision=preview.get("revision"),
        )
        return preview

    @app.post("/api/v1/projects/import-environment", status_code=202)
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def prepare_import_environment(body: ProjectImportInput,
                                   user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        _preview, config = _reviewed_import(profiles, body)
        return prepare_environment(config, user, body.name)

    @app.post("/api/v1/projects/import/bundle-environment", status_code=202)
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def prepare_bundle_environment(body: ProjectBundleImportInput,
                                   user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """Prepare the execution environment bound to the reviewed complete ZIP."""
        try:
            preview, native, _bundle, _revisions = _inspect_bundle_import(
                profiles, body, probe_runner)
            if (not re.fullmatch(r"[0-9a-f]{64}", body.revision)
                    or not secrets.compare_digest(body.revision, preview["revision"])):
                raise _error(409, "stale_import_preview")
            _native_preview, config = _reviewed_import(profiles, native)
            return prepare_environment(config, user, native.name)
        except RecipeError as exc:
            raise recipe_failure(exc) from exc

    @app.post("/api/v1/projects/import/bundle-preview")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def preview_project_bundle(body: ProjectBundlePreviewInput,
                               user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Automatically validate the exact complete ZIP without retaining sources."""
        try:
            preview, native, _bundle, _revisions = _inspect_bundle_import(
                profiles, body, probe_runner)
        except RecipeError as exc:
            raise recipe_failure(exc) from exc
        web.audit(user["id"], "toml-import-prepared", phase="prepare", result="prepared",
                  resource_type="project", resource_id=native.name,
                  candidate_revision=preview["revision"])
        return preview

    @app.post("/api/v1/projects/import/bundle")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def import_project_bundle(body: ProjectBundleImportInput,
                              user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Publish exact project configuration and retained image sources together."""
        try:
            preview, native, bundle, revisions = _inspect_bundle_import(
                profiles, body, probe_runner)
            if (not re.fullmatch(r"[0-9a-f]{64}", body.revision)
                    or not secrets.compare_digest(body.revision, preview["revision"])):
                raise _error(409, "stale_import_preview")
            _native_preview, config = _reviewed_import(profiles, native)

            def publish():
                """@brief Keep the existing profile, pause, ownership and failure boundaries."""
                return _publish_paused(profiles, web, user["id"], native.name, bundle.config_raw, {
                    "display_name": preview["display_name"], "description": body.description,
                    "platform": config.platform.kind, "repo": config.platform.repo,
                    "runtime": config.container.runtime,
                    "config_path": str(profiles.config_path(native.name)),
                    "store_root": config.state.store_root,
                }, imported=True, import_body=native, base_revision=body.revision)

            return RecipeStore(profiles.home).publish_import(
                bundle.recipe, revisions=revisions, publish=publish)
        except RecipeError as exc:
            raise recipe_failure(exc) from exc

    @app.post("/api/v1/projects/import-check")
    @configuration.route(scope="global", lane="long", resource="enrollment")
    def check_project_import(body: ProjectImportInput,
                             _user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly probe the exact reviewed import without publishing.

        @param[in] body Exact reviewed TOML, identity and revision.
        @param[in] _user Administrator authenticated after CSRF validation.
        @return Ephemeral redacted revision/time-bound prerequisite evidence.
        @exception HTTPException Invalid/stale input or unusable probe fails closed.
        """
        preview, config = _reviewed_import(profiles, body)
        auth_bound = _readiness_auth_bound(profiles, body.name, config)
        evidence = _probe_setup(config, probe_runner, chatgpt_dir=chatgpt_dir)
        _reviewed_import(profiles, body)
        if auth_bound != _readiness_auth_bound(profiles, body.name, config):
            raise _error(409, "stale_config_revision")
        if (not isinstance(evidence, dict)
                or not _valid_workflow(evidence.get("workflow"))
                or not _valid_readiness_checks(evidence.get("checks"), config)):
            raise _error(503, "readiness_probe_failed")
        checks = evidence["checks"]
        status = ("failed" if any(value is False for value in checks.values()) else
                  "partial" if not auth_bound or any(type(value) is not bool
                                                     for value in checks.values())
                  else "verified")
        return {**evidence, "status": status, "revision": preview["revision"],
                "required_checks": sorted(checks), "auth_bound": auth_bound,
                "config_revision": preview["config_revision"], "context": "api-host",
                "checked_at": datetime.now(UTC).isoformat()}

    @app.post("/api/v1/projects/import")
    @configuration.route(scope="global", lane="long", resource="enrollment")
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
    @configuration.route(lane="long")
    def connect_repository(name: str, body: RepositoryConnectionInput,
                           user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Verify scoped forge credentials before protected idle publication."""
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
            with (
                _web_config_edit_lock(path),
                guard_direct_config_apply(item, path, "repository.auth"),
            ):
                effect_guard()
            verified = verify_connection(config, item.project_id, body.server, body.token,
                                         body.allow_http, probe_runner)
            with (
                _web_config_edit_lock(path),
                guard_direct_config_apply(item, path, "repository.auth"),
            ):
                current = project(name, user)
                if (current.project_id != item.project_id
                        or sha256(path.read_bytes()).hexdigest() != revision):
                    raise _error(409, "stale_config_revision")
                confirmation = web.begin_change(
                    user["id"], "repository-connected", item.name)
                _verification_view(profiles, item, revision)
                effect_guard()
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
    @configuration.route(lane="fast")
    def executor_credentials_write(name: str, body: ExecutorCredentialInput, request: Request,
                                   user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Atomically save/remove an approved key while the project is idle."""
        deleting = request.method == "DELETE"
        if (deleting and body.token is not None or not deleting and body.token is None):
            raise _error(400, "executor_credential_invalid")
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
                _verification_view(profiles, item, revision)
                effect_guard()
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

    def chatgpt_view() -> dict:
        """@brief The server's sign-in status and whether a sign-in waits (lock held)."""
        session = chatgpt_pending["session"]
        if session is not None and not session.pending:
            session.cancel()
            chatgpt_pending["session"] = session = None
        return {"status": chatgpt.status(chatgpt_dir), "pending": session is not None}

    def chatgpt_failure(user: dict, exc: chatgpt.ChatGptError, project_name: str = "") -> None:
        """@brief Audit a sign-in failure by cause code only and raise its API error."""
        code = _CHATGPT_CODES.get(exc.code, "chatgpt_sign_in_refused")
        status = _CHATGPT_STATUS.get(exc.code, 502)
        if exc.code not in {"redirect-invalid", "state-mismatch", "not-pending"}:
            web.audit(user["id"], "chatgpt-sign-in-failed", project_name, detail=code)
        raise _error(status, code) from exc

    @app.get("/api/v1/chatgpt-sign-in")
    @configuration.route(scope="global", lane="global", resource="chatgpt")
    def chatgpt_sign_in_read(user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Report the server's ChatGPT sign-in without starting Pi."""
        with chatgpt_lock:
            effect_guard()
            chatgpt_view()  # Expire an abandoned attempt before reading its pipe.
            session = chatgpt_pending["session"]
            if session is not None:
                try:
                    completed = session.poll()
                except chatgpt.ChatGptError as exc:
                    chatgpt_pending["session"] = None
                    chatgpt_failure(user, exc)
                if completed:
                    chatgpt_pending["session"] = None
                    web.audit(user["id"], "chatgpt-sign-in-completed")
            return chatgpt_view()

    @app.post("/api/v1/projects/{name}/chatgpt-sign-in")
    @configuration.route(lane="long")
    def chatgpt_sign_in_start(name: str,
                              user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Start Sign in with ChatGPT with this project's runtime and image."""
        item = project(name, user)
        if item.archived:
            raise _error(409, "project_archived")
        try:
            config = _config_from_bytes(profiles.config_path(item.name).read_bytes())
        except (OSError, ValueError, TypeError) as exc:
            raise _error(503, "config_corrupt") from exc
        if _config_findings(config):
            raise _error(409, "invalid_config")
        manager = None if config.execution.backend == "local" else ContainerManager(
            config.container.runtime, config.container.image or EXECUTOR_BASE_IMAGE,
            config.container.uv_cache_volume, config.container.npm_cache_volume,
            probe_runner, run_args=config.container.run_args,
            selinux_relabel=config.container.selinux_relabel)
        if manager is not None:
            for command, code in (
                ([*manager.runtime_argv, "info"], "container_runtime_unavailable"),
                ([*manager.runtime_argv, "image", "inspect", manager.image],
                 "executor_image_unavailable"),
            ):
                if not _container_probe(probe_runner, command):
                    web.audit(user["id"], "chatgpt-sign-in-failed", item.name, detail=code)
                    raise _error(503, code)
        manager = chatgpt.helper_for(config, manager, runner=probe_runner)
        with chatgpt_lock:
            effect_guard()
            previous = chatgpt_pending["session"]
            if previous is not None:
                previous.cancel()
            chatgpt_pending["session"] = None
            session = chatgpt.SignIn(manager, chatgpt_dir, popen=chatgpt_popen)
            try:
                effect_guard()
                url = session.start()
            except chatgpt.ChatGptError as exc:
                chatgpt_failure(user, exc, item.name)
            except OSError as exc:
                session.cancel()
                raise _error(503, "chatgpt_sign_in_unavailable") from exc
            chatgpt_pending["session"] = session
            web.audit(user["id"], "chatgpt-sign-in-started", item.name)
            return {"authorize_url": url, "expires_in": chatgpt.SIGN_IN_SECONDS}

    @app.put("/api/v1/chatgpt-sign-in")
    @configuration.route(scope="global", lane="global", resource="chatgpt")
    def chatgpt_sign_in_complete(body: ChatGptRedirectInput,
                                 user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Pass the pasted redirect address to the waiting sign-in."""
        with chatgpt_lock:
            effect_guard()
            chatgpt_view()
            session = chatgpt_pending["session"]
            if session is None:
                raise _error(409, "chatgpt_sign_in_not_pending")
            try:
                effect_guard()
                session.submit(body.redirect_url)
            except chatgpt.ChatGptError as exc:
                if session.finished:
                    chatgpt_pending["session"] = None
                chatgpt_failure(user, exc)
            chatgpt_pending["session"] = None
            web.audit(user["id"], "chatgpt-sign-in-completed")
            return chatgpt_view()

    @app.delete("/api/v1/chatgpt-sign-in/pending")
    @configuration.route(scope="global", lane="global", resource="chatgpt")
    def chatgpt_sign_in_cancel(user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief End a waiting sign-in; the stored credential stays."""
        with chatgpt_lock:
            effect_guard()
            session = chatgpt_pending["session"]
            chatgpt_pending["session"] = None
            if session is not None:
                session.cancel()
                web.audit(user["id"], "chatgpt-sign-in-cancelled")
            return chatgpt_view()

    @app.delete("/api/v1/chatgpt-sign-in")
    @configuration.route(scope="global", lane="global", resource="chatgpt")
    def chatgpt_disconnect(user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Delete the server's ChatGPT credential and end a waiting sign-in."""
        with chatgpt_lock:
            effect_guard()
            session = chatgpt_pending["session"]
            chatgpt_pending["session"] = None
            if session is not None:
                session.cancel()
            try:
                effect_guard()
                chatgpt.disconnect(chatgpt_dir)
            except OSError as exc:
                raise _error(503, "chatgpt_credential_unreadable") from exc
            web.audit(user["id"], "chatgpt-disconnected")
            return chatgpt_view()

    @app.post("/api/v1/projects/{name}/model-connection-test")
    @configuration.route(lane="long")
    def model_connection_test(name: str, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Test the configured model explicitly and persist scoped access evidence."""
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
            with (
                _web_config_edit_lock(path),
                guard_direct_config_apply(item, path, "model.connection-test"),
            ):
                directory = profiles.profile_dir(item.name)
                binding = credential_binding(directory, config)
                model_evidence(directory, config, item.project_id, revision)
            result = probe_model_connection(
                config, probe_runner, directory / ".env", chatgpt_dir=chatgpt_dir)
            with (
                _web_config_edit_lock(path),
                guard_direct_config_apply(item, path, "model.connection-test"),
            ):
                if (
                    project(name, user).project_id != item.project_id
                    or sha256(path.read_bytes()).hexdigest() != revision
                ):
                    raise _error(409, "stale_config_revision")
                if credential_binding(directory, config) != binding:
                    raise _error(409, "stale_config_revision")
                if (
                    result.get("executor") != EXECUTOR_NAME
                    or result.get("model") != config.executor.model
                ):
                    raise ExecutorSettingsError("executor_evidence_corrupt")
                result = {
                    **result,
                    "project_id": item.project_id,
                    "revision": revision,
                    "checked_at": datetime.now(UTC).isoformat(),
                }
                effect_guard()
                save_model_evidence(directory, result, binding)
                web.audit(user["id"], "model-connection-tested", item.name)
                return result
        except (OSError, ValueError, TypeError, IsolationError) as exc:
            raise _error(503, "model_test_failed") from exc

    @app.post("/api/v1/projects/{name}/readiness-check")
    @configuration.route(lane="long")
    def readiness_check(name: str, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Probe selected host prerequisites on explicit admin request."""
        item = project(name, user)
        try:
            raw = profiles.config_path(item.name).read_bytes()
            revision = sha256(raw).hexdigest()
            config = _config_from_bytes(raw)
            if _config_findings(config):
                raise _error(409, "invalid_config")
        except (
            OSError,
            AttributeError,
            UnicodeError,
            TypeError,
            ValueError,
            tomllib.TOMLDecodeError,
        ) as exc:
            raise _error(503, "config_corrupt") from exc
        _verification_view(profiles, item, revision)
        host = _readiness_host()
        binding = _readiness_binding(profiles, item.name, config)
        auth_bound = _readiness_auth_bound(profiles, item.name, config)
        try:
            evidence = _probe_setup(
                config,
                project_runner(profiles.profile_dir(item.name), config, probe_runner),
                profiles.config_path(item.name).parent / ".env",
                chatgpt_dir,
                external_auth=False,
            )
        except RepositoryAuthError as exc:
            raise _error(503, exc.code) from exc
        if (not isinstance(evidence, dict)
                or not _valid_workflow(evidence.get("workflow"))
                or not _valid_readiness_checks(evidence.get("checks"), config)):
            raise _error(503, "readiness_probe_failed")
        checked_plan = None
        if config.execution.preparation or config.execution.backend == "local":
            try:
                checked_plan = preview_plan(config, runner=probe_runner)
            except PreparationError as exc:
                raise _error(503, "readiness_probe_failed") from exc
        value = {
            "schema": 3,
            "workflow": evidence["workflow"],
            "project_id": item.project_id,
            "revision": revision,
            "host": host,
            "binding": binding,
            "auth_bound": auth_bound,
            "context": "api-host",
            "checked_at": datetime.now(UTC).isoformat(),
            "checks": evidence["checks"],
        }
        try:
            with _web_config_edit_lock(profiles.config_path(item.name)):
                current = project(name, user)
                current_revision = sha256(
                    profiles.config_path(item.name).read_bytes()
                ).hexdigest()
                if (
                    current.project_id != item.project_id
                    or current_revision != revision
                    or host != _readiness_host()
                    or binding != _readiness_binding(profiles, item.name, config)
                    or auth_bound != _readiness_auth_bound(profiles, item.name, config)
                ):
                    raise _error(409, "stale_config_revision")
                _verification_view(profiles, current, current_revision)
                if checked_plan is not None:
                    configuration.save_execution_plan(item, revision, checked_plan)
                _write_pending_config(profiles.profile_dir(item.name) / "readiness.json", value)
                web.audit(user["id"], "readiness-checked", item.name)
                view = _verification_view(profiles, current, revision)
                if "local_probe" in evidence:
                    view["local_probe"] = evidence["local_probe"]
                return view
        except OSError as exc:
            raise _contract_rejection(
                "readiness_store_failed",
                "readiness",
                "Check local evidence storage before retrying.",
            ) from exc

    @app.post("/api/v1/projects/{name}/archive")
    def archive_project(name: str, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Stop pickup while retaining project configuration and history."""
        item = project(name, user)
        if not item.archived:
            state = _store_for(profiles, item)
            try:
                with state.project_barrier():
                    if (any(run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
                            for run in state.list_runs())
                            or web.has_unfinished_operations(item.name)):
                        raise _error(409, "project_has_active_work")
                    item.archived = True
                    profiles.save(item)
                    web.audit(user["id"], "project-archived", item.name)
            except LockHeldError as exc:
                raise _error(409, "project_has_active_work") from exc
            except StateError as exc:
                raise _error(503, "run_state_corrupt") from exc
        return _profile_view(profiles, item)

    @app.post("/api/v1/projects/{name}/restore")
    def restore_project(name: str,
                        user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Re-enable project pickup without changing retained history."""
        item = project(name, user)
        if item.archived:
            if web.has_unfinished_operations(item.name):
                raise _error(409, "project_has_active_work")
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
        try:
            with state.project_barrier():
                if any(run.lifecycle not in _DELETABLE_RUN_LIFECYCLES
                       for run in state.list_runs()):
                    raise _error(409, "project_has_active_work")
                if body.remove_clone and not clone_view(item)["removable"]:
                    raise _error(409, "clone_not_removable")
                operation = web.enqueue(user["id"], item.name, "delete",
                                        "remove-clone" if body.remove_clone else "",
                                        body.idempotency_key)
        except LockHeldError as exc:
            raise _error(409, "project_has_active_work") from exc
        except StateError as exc:
            raise _error(503, "run_state_corrupt") from exc
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
        try:
            settings = _setting_metadata(data, raw)
        except (UnicodeError, ValueError, TypeError, tomllib.TOMLDecodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        try:
            connection = model_evidence(profiles.profile_dir(item.name), config,
                                        item.project_id, sha256(raw).hexdigest())
            # A ChatGPT result holds only while the server stays signed in.
            if (connection is not None and config.executor.provider == CHATGPT
                    and chatgpt.status(chatgpt_dir) != "signed-in"):
                connection = None
        except ExecutorSettingsError as exc:
            raise _error(503, "executor_evidence_corrupt") from exc
        issues = validate_config(config)
        # Read only explicitly checked current evidence; never probe host/Git from a settings read.
        plan = configuration.execution_plan(item, sha256(raw).hexdigest()) if not issues else None
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

    def recipe_failure(exc):
        """@brief Translate closed recipe metadata without exposing uploaded file contents."""
        if isinstance(exc, BuildBundleError):
            return _error(400, exc.code)
        status = (503 if exc.code in {"recipe_store_corrupt", "recipe_builtin_unavailable",
                                     "recipe_write_failed"} else
                  409 if exc.code in {"recipe_changed", "recipe_import_conflict"} else 400)
        return HTTPException(status, {"code": exc.code, "missing_images": list(exc.missing),
                                      "recovery": exc.recovery})

    def recipe_source_bytes(path):
        """@brief Bound every recipe config read and translate unsafe/missing sources."""
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("invalid project source")
            with path.open("rb") as source:
                raw = source.read(MAX_SOURCE_BYTES + 1)
            if not raw or len(raw) > MAX_SOURCE_BYTES or path.is_symlink():
                raise ValueError("invalid project source")
            return raw
        except (OSError, ValueError, TypeError) as exc:
            raise _error(503, "config_corrupt") from exc

    def recipe_config(name, user):
        """@brief Read one authorized source snapshot before consulting recipe metadata."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        try:
            raw = recipe_source_bytes(path)
            config = _config_from_bytes(raw)
        except (OSError, ValueError, TypeError) as exc:
            raise _error(503, "config_corrupt") from exc
        try:
            config = effective_recipe_config(config, runner=probe_runner)
        except RecipeError as exc:
            raise recipe_failure(exc) from exc
        return item, path, raw, config

    @app.get("/api/v1/projects/{name}/executor-recipe")
    @configuration.route(lane="long")
    def executor_recipe(name: str, user: Annotated[dict, Depends(administrator)]) -> dict:
        """@brief Read image-shared definition availability without changing project or jobs."""
        _, path, raw, config = recipe_config(name, user)
        try:
            result = recipe_status(config, home=profiles.home, runner=probe_runner)
        except (RecipeError, BuildBundleError) as exc:
            raise recipe_failure(exc) from exc
        if recipe_source_bytes(path) != raw:
            raise _error(409, "stale_config_revision")
        return {**result, "revision": sha256(raw).hexdigest()}

    def inspect_recipe(name, body, user):
        """@brief Validate one selected/root-or-missing-base attachment before retention."""
        item, path, raw, config = recipe_config(name, user)
        if sha256(raw).hexdigest() != body.revision:
            raise _error(409, "stale_config_revision")
        if config.execution.backend != "container":
            raise _error(400, "recipe_native")
        try:
            if body.image != config.container.image:
                current = recipe_status(config, home=profiles.home, runner=probe_runner)
                if body.image not in current["missing_images"]:
                    raise RecipeError("recipe_image_mismatch")
            source = base64.b64decode(body.source, validate=True)
            if len(source) > MAX_ARCHIVE_BYTES:
                raise RecipeError()
            document = parse_recipe(source, body.image)
            # A selected corrupt association must be recovered explicitly, not replaced silently.
            catalog = RecipeStore(profiles.home)
            catalog.get(body.image)
            observed = catalog.binding_digest(body.image)
            result = recipe_status(config, home=profiles.home, runner=probe_runner,
                                   overrides={body.image: document})
        except (RecipeError, BuildBundleError) as exc:
            raise recipe_failure(exc) from exc
        except (binascii.Error, ValueError) as exc:
            raise _error(400, "recipe_invalid") from exc
        if recipe_source_bytes(path) != raw or project(name, user).project_id != item.project_id:
            raise _error(409, "stale_config_revision")
        return path, raw, config, document, {**result, "expected_digest": observed,
                                             "upload_image": body.image,
                                             "revision": sha256(raw).hexdigest()}

    @app.post("/api/v1/projects/{name}/executor-recipe/preview")
    @configuration.route(lane="long")
    def preview_executor_recipe(name: str, body: RecipeInput,
                                user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Check the selected source and graph in memory; no catalog writes occur."""
        _, _, _, _, result = inspect_recipe(name, body, user)
        return result

    @app.put("/api/v1/projects/{name}/executor-recipe")
    @configuration.route(lane="long")
    def save_executor_recipe(name: str, body: RecipeInput,
                             user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Save source metadata with image/config binding, independent of job admission."""
        item = project(name, user)
        path, raw, config, document, _ = inspect_recipe(name, body, user)
        try:
            with _web_config_edit_lock(path):
                if recipe_source_bytes(path) != raw:
                    raise _error(409, "stale_config_revision")
                effect_guard()
                saved_digest = RecipeStore(profiles.home).put(
                    document, expected_digest=body.expected_digest)
            result = recipe_status(config, home=profiles.home, runner=probe_runner)
        except (RecipeError, BuildBundleError) as exc:
            raise recipe_failure(exc) from exc
        web.audit(user["id"], "executor-recipe-saved", item.name,
                  resource_type="config", resource_id="executor-recipe", phase="apply",
                  result="applied", base_revision=body.expected_digest,
                  candidate_revision=saved_digest)
        return {**result, "revision": body.revision}

    @app.get("/api/v1/projects/{name}/config/raw")
    def raw_config(name: str, user: Annotated[dict, Depends(administrator)],
                   download: bool = False, include_build: bool = False) -> Response:
        """
        @brief      Read the administrator's original saved TOML without redaction.
        @param[in]  name Authorized profile name or immutable project ID.
        @param[in]  user Administrator resolved before any config read.
        @param[in]  download Return the fixed config.toml attachment filename.
        @param[in]  include_build Download the reviewed Docker build bundle.
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
            parsed = tomllib.loads(raw.decode("utf-8"))
            with path.open("rb") as source:
                unchanged = source.read(MAX_SOURCE_BYTES + 1) == raw
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            raise _error(503, "config_corrupt") from exc
        if not unchanged or project(name, user).project_id != item.project_id:
            raise _error(409, "stale_config_revision")
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        if include_build:
            if _secret_config_keys(parsed):
                raise _error(400, "build_config_has_secrets")
            try:
                config = _config_from_bytes(raw)
                bundle = export_build_bundle(config, raw, runner=probe_runner, home=profiles.home)
                with path.open("rb") as source:
                    unchanged = source.read(MAX_SOURCE_BYTES + 1) == raw
            except BuildBundleError as exc:
                raise _error(400, exc.code) from exc
            except RecipeError as exc:
                raise recipe_failure(exc) from exc
            except (OSError, ValueError, TypeError) as exc:
                raise _error(503, "config_corrupt") from exc
            if (not unchanged or path.is_symlink()
                    or project(name, user).project_id != item.project_id):
                raise _error(409, "stale_config_revision")
            headers["Content-Disposition"] = 'attachment; filename="adore-docker-build.zip"'
            return Response(content=bundle, media_type="application/zip", headers=headers)
        if download:
            headers["Content-Disposition"] = 'attachment; filename="config.toml"'
        return Response(content=raw, media_type="text/plain", headers=headers)

    @app.put("/api/v1/projects/{name}/config")
    @configuration.route(lane="fast")
    def config_update(
        name: str, body: ConfigEdit, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        item = project(name, user)
        if body.key in {"executor.env_keys", BATCH_KEY}:
            raise _error(409, "pending_config_required")
        if _external_environment_key(body.key):
            raise _error(400, "environment_managed_externally")
        if not _editable_setting_key(body.key):
            raise _error(400, "setting_not_editable")
        if body.key.startswith(("execution.", "local.")) or body.key in _CHOSEN_ENVIRONMENT_KEYS:
            raise _error(409, "pending_config_required")
        path = profiles.config_path(item.name)
        with (
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
                    or not isinstance(_value_at(tomllib.loads(current), body.key), str | None)
                ):
                    raise _error(400, "invalid_config")
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
                    before={"value": _candidate_value(
                        tomllib.loads(raw.decode()), body.key, body.value)},
                )
                effect_guard()
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

    @app.post("/api/v1/projects/{name}/config/preview")
    @configuration.route(lane="long")
    def preview_config(
        name: str, body: ConfigEdit, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Validate effects without publishing active or pending settings."""
        item = project(name, user)
        if _external_environment_key(body.key):
            raise _error(400, "environment_managed_externally")
        path = profiles.config_path(item.name)
        raw, _changed, value = _prepare_config_candidate(path, body, probe_runner)
        effect_guard()
        return _public_pending_config(value, active_text=raw.decode("utf-8"))

    @app.post("/api/v1/projects/{name}/config/pending")
    @configuration.route(lane="settings")
    def stage_config(
        name: str, body: ConfigEdit, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Save a validated candidate revision while live config stays put."""
        item = project(name, user)
        if _external_environment_key(body.key):
            raise _error(400, "environment_managed_externally")
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        raw, changed, value = _prepare_config_candidate(path, body, probe_runner)
        with _web_config_edit_lock(path):
            if sha256(path.read_bytes()).hexdigest() != value["base_revision"]:
                raise _error(409, "stale_config_revision")
            previous = _read_pending_config(pending_path)
            if previous is not None:
                if body.pending_revision is None:
                    raise _error(409, "pending_config_exists")
                try:
                    active_text = path.read_bytes().decode("utf-8")
                except (OSError, UnicodeError) as exc:
                    raise _error(503, "config_corrupt") from exc
                _public_pending_config(previous, active_text=active_text)
                if not secrets.compare_digest(
                        body.pending_revision, previous["candidate_revision"]):
                    raise _error(409, "stale_pending_revision")
                if not secrets.compare_digest(body.revision, previous["base_revision"]):
                    raise _error(409, "stale_config_revision")
            elif body.pending_revision is not None:
                raise _error(409, "stale_pending_revision")
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
                before={"value": _candidate_value(
                    tomllib.loads(raw.decode()), body.key, body.value)},
            )
            effect_guard()
            _write_pending_config(pending_path, value)
            web.confirm_change(
                attempt,
                after={"value": _candidate_value(tomllib.loads(changed), body.key, body.value)},
                detail=body.key,
            )
        return public

    @app.post("/api/v1/projects/{name}/config/apply")
    @configuration.route(lane="settings")
    def apply_config(
        name: str, body: ConfigApply, user: Annotated[dict, Depends(admin_mutation)]
    ) -> dict:
        """@brief Apply the reviewed candidate only at a quiescent boundary."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        inspected = _read_pending_config(pending_path)
        if inspected is None:
            raise _error(404, "pending_config_not_found")
        try:
            inspected_active = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise _error(503, "config_corrupt") from exc
        _public_pending_config(inspected, active_text=inspected_active)
        if "execution_plan" in inspected:
            configuration.execution_plan(item, sha256(inspected_active.encode("utf-8")).hexdigest())
        try:
            proposed = _config_from_bytes(inspected["candidate_text"].encode("utf-8"))
            if validate_config(proposed):
                raise _error(503, "pending_config_corrupt")
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise _error(503, "pending_config_corrupt") from exc
        if proposed.execution.preparation or proposed.execution.backend == "local":
            try:
                if preview_plan(proposed, runner=probe_runner) != inspected.get("execution_plan"):
                    raise PreparationError("reviewed execution plan changed")
            except PreparationError as exc:
                raise _error(409, "execution_plan_stale") from exc
        with _web_config_edit_lock(path):
            pending = _read_pending_config(pending_path)
            if pending != inspected:
                raise _error(409, "stale_pending_revision")
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
            budget_keys = {"budgets.max_iterations", "budgets.max_wall_clock_seconds",
                           "budgets.per_gate_timeout_seconds", "budgets.max_cost_usd",
                           "budgets.max_files_touched"}
            members = (parse_batch(pending["value"]) if pending["key"] == BATCH_KEY
                       else ((pending["key"], pending["value"]),))
            budget_only = bool(members) and all(key in budget_keys for key, _ in members)
            if budget_only and not already_applied:
                expected = _set_candidate_value(
                    raw.decode("utf-8"), pending["key"], pending["value"])
                if tomllib.loads(expected) != tomllib.loads(pending["candidate_text"]):
                    raise _error(503, "pending_config_corrupt")
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
                        run.lifecycle not in _TERMINAL_RUN_LIFECYCLES
                        and not (budget_only and run.lifecycle == "parked-clarification")
                        for run in state.list_runs()
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
                        {"value": _candidate_value(
                            tomllib.loads(raw.decode()), pending["key"], pending["value"])}
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
                        if sha256(path.read_bytes()).hexdigest() != pending["base_revision"]:
                            raise _error(409, "stale_config_revision")
                        effect_guard()
                        candidate.replace(path)
                    _sync_profile_config_identity(profiles, item, path)
                    web.confirm_change(
                        attempt,
                        after={
                            "value": _candidate_value(
                                tomllib.loads(pending["candidate_text"]),
                                pending["key"], pending["value"]
                            )
                        },
                        detail=pending["key"],
                    )
                    if "execution_plan" in pending:
                        configuration.save_execution_plan(
                            item, pending["candidate_revision"], pending["execution_plan"],
                            after_apply=True)
                    effect_guard(revision=False)
                    pending_path.unlink()
                finally:
                    if candidate is not None:
                        candidate.unlink(missing_ok=True)
            finally:
                state.release_lock()
        return {"revision": sha256(path.read_bytes()).hexdigest()}

    @app.delete("/api/v1/projects/{name}/config/pending")
    @configuration.route(lane="fast")
    def discard_config(name: str, user: Annotated[dict, Depends(admin_mutation)]) -> dict:
        """@brief Explicitly discard a staged candidate, including corrupt ones."""
        item = project(name, user)
        path = profiles.config_path(item.name)
        pending_path = profiles.profile_dir(item.name) / "pending_config.json"
        with _web_config_edit_lock(path):
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
            effect_guard()
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

    def job_snapshot(
        user: dict, project_id: str | None = None, *, overview: bool = False,
    ) -> tuple[list, str, list[str]]:
        """
        @brief Recheck authorization/profile identity after the complete local read.
        @param[in] user Current authenticated principal.
        @param[in] project_id Optional immutable single-project selector.
        @param[in] overview Isolate projects with unreadable job state for Overview.
        @return Authorized rows, optimistic source revision and unreadable project IDs.
        @exception JobReadError For corrupt or changed authorized source evidence.
        """
        selected = job_projects(user, project_id)
        if overview:
            rows, revision, unreadable = read_overview_jobs(profiles, selected)
        else:
            rows, revision = read_jobs(profiles, selected)
            unreadable = []
        if selected != job_projects(user, project_id):
            raise JobReadError("job_snapshot_changed", 409)
        return rows, revision, unreadable

    @app.get("/api/v1/jobs-page")
    def jobs_page(
        user: Annotated[dict, Depends(principal)],
        project_id: str | None = None,
        q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        status_group: Literal["active", "waiting", "review", "terminal"] | None = None,
        attention: bool = False,
        overview: bool = False,
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
        @param[in] overview Include verified projects and report unreadable ones.
        @param[in] limit Bounded page size or all.
        @param[in] offset Nonnegative matched-row offset.
        @param[in] snapshot Optional expected source-content revision.
        @param[in] sort Column ordering every matched job before paging.
        @param[in] order Direction; newest activity first, otherwise ascending, by default.
        @return Matched page, verified counts, source revision and any unreadable projects.
        """
        if limit != "all" and (len(limit) > 3 or not limit.isascii() or not limit.isdecimal()
                               or not 1 <= int(limit) <= 100):
            raise _error(422, "invalid_run_limit")
        needle = q.strip().casefold() if q is not None else None
        if needle == "":
            raise _error(422, "invalid_job_search")
        rows, revision, unreadable = job_snapshot(user, project_id, overview=overview)
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
        visible = [{key: value for key, value in row.items() if key not in {"timeline", "direct"}}
                   for row in matched[offset:offset + page_limit]]
        return {"items": visible, "total": len(matched),
                "counts": counts, "groups": groups, "limit": page_limit, "offset": offset,
                "complete": True, "snapshot": revision,
                "snapshot_semantics": "optimistic-source-revision",
                **({"unreadable_projects": unreadable} if unreadable else {})}

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
        rows, revision, _ = job_snapshot(user, project_id)
        row = next((row for row in rows if row["run_id"] == run_id), None)
        if row is None:
            raise _error(404, "run_not_found")
        item = next(item for item in job_projects(user, project_id)
                    if item.project_id == project_id)
        row["budget"] = read_job_budget(profiles, item, run_id, row["state_revision"])
        if item not in job_projects(user, project_id):
            raise JobReadError("job_snapshot_changed", 409)
        return {"job": row, "complete": True, "snapshot": revision}

    @app.get("/api/v1/jobs/{project_id}/{run_id}/executor-output")
    def job_executor_output(project_id: str, run_id: str,
                            user: Annotated[dict, Depends(principal)]) -> dict:
        """@brief Read only authorized journal-bound operational executor evidence."""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", run_id):
            raise _error(404, "run_not_found")
        rows, revision, _ = job_snapshot(user, project_id)
        row = next((row for row in rows if row["run_id"] == run_id), None)
        if row is None:
            raise _error(404, "run_not_found")
        item = next(item for item in job_projects(user, project_id)
                    if item.project_id == project_id)
        result = read_executor_output(profiles, item, run_id, row["state_revision"])
        if item not in job_projects(user, project_id):
            raise JobReadError("job_snapshot_changed", 409)
        return result

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
                        current_source=lambda state=state, run_id=run.run_id:
                            state.read_journal(run_id),
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
        if action not in ("start", "retry", "cancel", "restart", "pause", "resume"):
            raise _error(404, "operation_not_found")
        if action in ("pause", "resume") and user["role"] != "admin":
            raise _error(403, "admin_required")
        if action == "cancel" and not body.confirmed:
            raise _error(400, "invalid_operation")
        if action == "start":
            if body.ticket_iid is None or body.ticket_iid < 1 or body.run_id:
                raise _error(400, "ticket_required")
            target = str(body.ticket_iid)
        elif action in ("retry", "cancel", "restart"):
            if not re.fullmatch(r"[a-zA-Z0-9._-]{1,160}", body.run_id):
                raise _error(400, "run_required")
            target = body.run_id
            if action == "restart":
                if not body.confirmed or not re.fullmatch(r"[0-9a-f]{64}", body.state_revision):
                    raise _error(400, "invalid_operation")
                replayed = web.operation_for_key(user["id"], body.idempotency_key)
                target = f"{body.run_id}.{body.state_revision}"
                if replayed:
                    if (replayed["project_id"] != item.project_id
                            or replayed["action"] != "restart" or replayed["run_id"] != target):
                        raise _error(409, "idempotency_conflict")
                    return {"id": replayed["id"], "status": replayed["status"]}
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
            if action == "restart":
                try:
                    raw = (state.run_dir(body.run_id) / "state.json").read_bytes()
                except OSError as exc:
                    raise _error(409, "job_snapshot_changed") from exc
                if run.lifecycle != "failed" or sha256(raw).hexdigest() != body.state_revision:
                    raise _error(409, "job_snapshot_changed")
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
        except GiteaAuthError as exc:
            raise _error(503, exc.code) from exc
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
        @details Manual admission preserves stopped automatic monitoring and other gates.
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
        if not body.confirmed:
            raise _error(400, "invalid_operation")
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
        if operation["action"] == "configure":
            if user["role"] != "admin":
                raise _error(404, "operation_not_found")
            if operation["project_id"]:
                project(operation["project_id"], user)
            try:
                outcome = configuration.outcome(operation)
            except WebStoreError as exc:
                raise _error(503, "web_store_corrupt", "Delete ADORE_HOME/configuration-tasks/"
                    + operation["run_id"] + ".result.json to discard corrupt outcome evidence; "
                    "inspect active settings before submitting another request.") from exc
            return {**{key: operation[key] for key in (
                "id", "project_id", "domain", "action", "status", "result", "reason",
                "created_at", "updated_at")}, "outcome": outcome}
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
