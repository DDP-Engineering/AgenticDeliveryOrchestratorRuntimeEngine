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
@file    configuration.py
@brief   Durable scoped configuration dispatch outside HTTP and executor pools.
@details Existing route handlers are the only implementation of their contracts.
         Protected records hold inputs/results; SQLite contains opaque references.
         Fast, long and global lanes have finite capacity and no hidden pool queue.
"""

from __future__ import annotations

# IMPORTS
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from hashlib import sha256
import inspect
import json
import re
import secrets
from threading import Lock
import time
from typing import Annotated, get_args, get_origin

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from adore.profiles import ProfileError
from adore.state import StateStore
from adore.util import strict_json_loads
from adore.web.executor_settings import read_private_record, write_private_record
from adore.web.ownership import OwnershipError
from adore.web.store import WebStoreError

# CONSTANTS
_EFFECT = ContextVar("configuration_effect", default=None)
_CLEANUP = ContextVar("configuration_owned_cleanup", default=False)
_OWNER_GUARD = ContextVar("configuration_owner_guard", default=None)
_OPERATION = ContextVar("configuration_operation", default=0)
MAX_RECORD = 32 * 1024 * 1024
MAX_PENDING = 256
_DEADLINE = ContextVar("configuration_deadline", default=None)
TASK_SECONDS = 3600


# PUBLIC API
def effect_guard(*, revision: bool = True) -> None:
    """@brief Recheck the current configuration claim immediately before an effect."""
    if _CLEANUP.get():
        guard = _OWNER_GUARD.get()
        if guard is not None:
            guard()
        return
    guard = _EFFECT.get()
    if guard is not None:
        try:
            guard(revision=revision)
        except (OwnershipError, HTTPException) as exc:
            if not revision:
                raise OwnershipError(
                    "configuration confirmation lost authority",
                    reason="configuration_confirmation_failed",
                ) from exc
            raise


@contextmanager
def owned_cleanup():
    """@brief Retain ownership-only authority for an exact internally owned disposable resource.
    @note Actor revocation/deadlines refuse new work and publication, never required cleanup.
          Ancestry and durable worker ownership remain mandatory while a task is attached.
    """
    token = _CLEANUP.set(True)
    try:
        yield
    finally:
        _CLEANUP.reset(token)


def probe_timeout(requested: float | None = None) -> float:
    """@brief Bound an external probe by the remaining task wall-clock budget."""
    if _CLEANUP.get():
        return min(requested or 8, 8)
    deadline = _DEADLINE.get()
    return min(
        requested or TASK_SECONDS,
        max(0.01, deadline - time.monotonic()) if deadline else TASK_SECONDS,
    )


def current_operation() -> int:
    """@brief Identify the current request when checking for other unfinished work."""
    return _OPERATION.get()


class ConfigurationTasks:
    """@brief Register existing typed routes and publish opaque protected requests."""

    def __init__(self, profiles, web):
        self.profiles, self.web = profiles, web
        self.handlers = {}
        self.submit_lock = Lock()
        self.directory = profiles.home / "configuration-tasks"

    def route(self, *, scope="project", lane="fast", resource=""):
        """@brief Wrap a typed endpoint; HTTP always submits, worker invokes its body.
        @param[in] scope Explicit project or global domain; no active-profile fallback.
        @param[in] lane Fixed bounded fast, long or global worker lane.
        """
        if scope not in ("project", "global") or lane not in ("fast", "long", "global", "settings"):
            raise ValueError("invalid configuration scope")

        def decorate(handler):
            """@brief Retain the typed handler and wrap HTTP calls with durable submission."""
            signature = inspect.signature(handler)
            self.handlers[handler.__name__] = (handler, signature, scope, lane, resource)

            @wraps(handler)
            def submit(*args, **kwargs):
                """@brief Persist validated work and return acceptance without effects."""
                values = dict(signature.bind(*args, **kwargs).arguments)
                actor = values.get("user", values.get("_user"))
                if not isinstance(actor, dict) or actor.get("role") != "admin":
                    raise HTTPException(403, detail={"code": "admin_required"})
                project_id, revision = "", ""
                if scope == "project":
                    name = values.get("name")
                    if not isinstance(name, str) or not name:
                        raise HTTPException(422, detail={"code": "configuration_scope_required"})
                    try:
                        named = self.profiles.load(name) if self.profiles.exists(name) else None
                        identified = (
                            self.profiles.find_by_id(name)
                            if re.fullmatch(r"[a-f0-9]{32}", name)
                            else None
                        )
                        if (
                            named is not None
                            and identified is not None
                            and named.project_id != identified.project_id
                        ):
                            raise HTTPException(503, detail={"code": "project_identity_ambiguous"})
                        profile = identified or named
                    except ProfileError as exc:
                        raise HTTPException(503, detail={"code": "project_corrupt"}) from exc
                    if profile is None:
                        raise HTTPException(404, detail={"code": "project_not_found"})
                    if profile.archived:
                        raise HTTPException(409, detail={"code": "project_archived"})
                    project_id = profile.project_id
                    try:
                        inspected = self.configuration_bytes(profile)
                        inspected.decode("utf-8")
                        revision = sha256(inspected).hexdigest()
                    except (OSError, UnicodeError) as exc:
                        raise HTTPException(503, detail={"code": "config_corrupt"}) from exc
                    values["name"] = project_id
                payload = {}
                for key, value in values.items():
                    if key in ("user", "_user"):
                        continue
                    if isinstance(value, BaseModel):
                        payload[key] = value.model_dump(mode="json")
                    elif isinstance(value, Request):
                        payload[key] = {
                            "method": value.method,
                            "headers": {
                                key: value.headers[key]
                                for key in ("cookie", "x-csrf-token")
                                if key in value.headers
                            },
                        }
                    elif value is None or isinstance(value, str | int | bool | float):
                        payload[key] = value
                    else:
                        raise HTTPException(422, detail={"code": "invalid_request"})
                envelope = {
                    "schema": 1,
                    "nonce": secrets.token_hex(16),
                    "handler": handler.__name__,
                    "actor_id": actor["id"],
                    "project_id": project_id,
                    "revision": revision,
                    "credential_revision": self.credential_revision(profile)
                    if scope == "project"
                    else "",
                    "scope": scope,
                    "lane": self.settings_lane(profile, payload) if lane == "settings" else lane,
                    "resource": self.resource_name(resource, handler.__name__, payload),
                    "arguments": payload,
                }
                encoded = json.dumps(envelope, ensure_ascii=True, sort_keys=True).encode()
                reference = sha256(encoded).hexdigest()[:32]
                serial_key = (
                    sha256(envelope["resource"].encode()).hexdigest()[:32]
                    if resource == "enrollment"
                    else ""
                )
                if len(encoded) > MAX_RECORD:
                    raise HTTPException(413, detail={"code": "configuration_request_too_large"})
                with self.submit_lock:
                    if len(self.web.pending_configuration()) >= MAX_PENDING:
                        raise HTTPException(503, detail={"code": "configuration_queue_full"})
                    self.directory.mkdir(parents=True, exist_ok=True)
                    if self.directory.is_symlink():
                        raise WebStoreError("configuration storage is corrupt")
                    target = self.directory / (reference + ".request.json")
                    write_private_record(target, encoded)
                    try:
                        operation = self.web.enqueue_configuration(
                            actor["id"],
                            reference,
                            serial_key + ":" + reference if serial_key else reference,
                            project_id=project_id if scope == "project" else None,
                            serial_key=serial_key,
                        )
                    except WebStoreError as exc:
                        target.unlink(missing_ok=True)
                        if str(exc) == "configuration resource is busy":
                            raise HTTPException(
                                409, detail={"code": "project_creation_in_progress"}
                            ) from exc
                        if str(exc) == "configuration queue is full":
                            raise HTTPException(
                                503, detail={"code": "configuration_queue_full"}
                            ) from exc
                        raise
                    except BaseException:
                        target.unlink(missing_ok=True)
                        raise
                return JSONResponse(
                    status_code=202,
                    content={
                        "id": operation["id"],
                        "status": operation["status"],
                        "domain": operation["domain"],
                        "project_id": operation["project_id"],
                    },
                    headers={
                        "Location": "/api/v1/operations/" + str(operation["id"]),
                        "Cache-Control": "no-store",
                    },
                )

            return submit

        return decorate

    def configuration_bytes(self, profile):
        """@brief Read one current regular UTF-8 config with the existing 1 MiB bound."""
        path = self.profiles.config_path(profile.name)
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("invalid configuration file")
            with path.open("rb") as source:
                raw = source.read(1048577)
            if not raw or len(raw) > 1048576:
                raise ValueError("invalid configuration size")
            raw.decode("utf-8")
            return raw
        except (OSError, ValueError) as exc:
            raise HTTPException(503, detail={"code": "config_corrupt"}) from exc

    def save_execution_plan(self, profile, revision, plan, *, after_apply=False):
        """@brief Cache an explicitly checked current plan without probing from later HTTP reads."""
        from adore.preparation import validate_plan

        validated = validate_plan(plan)
        try:
            # Refuse foreign/corrupt formats before replacement.
            self.execution_plan(profile, revision)
        except HTTPException as exc:
            if after_apply:
                raise OwnershipError("configuration cache confirmation refused",
                                     reason="configuration_confirmation_failed") from exc
            raise
        effect_guard(revision=not after_apply)
        value = {
            "schema": 1,
            "project_id": profile.project_id,
            "revision": revision,
            "plan": validated,
        }
        write_private_record(
            self.profiles.profile_dir(profile.name) / "execution-plan.json",
            json.dumps(value).encode(),
        )

    def execution_plan(self, profile, revision):
        """@brief Read current checked plan evidence, with unknown for missing or stale data."""
        from adore.preparation import PreparationError, public_plan, validate_plan

        try:
            raw = read_private_record(
                self.profiles.profile_dir(profile.name) / "execution-plan.json", MAX_RECORD
            )
            if raw is None:
                return None
            value = strict_json_loads(raw.decode("utf-8"))
            if (
                not isinstance(value, dict)
                or set(value) != {"schema", "project_id", "revision", "plan"}
                or type(value["schema"]) is not int
                or value["schema"] != 1
                or value["project_id"] != profile.project_id
                or not isinstance(value["revision"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", value["revision"])
            ):
                raise ValueError("invalid execution plan evidence")
            plan = validate_plan(value["plan"])
            return public_plan(plan) if value["revision"] == revision else None
        except (OSError, ValueError, TypeError, KeyError, PreparationError) as exc:
            raise HTTPException(
                503,
                detail={
                    "code": "config_corrupt",
                    "message": "Delete this project's execution-plan.json "
                    "to discard refused plan evidence.",
                },
            ) from exc

    def credential_revision(self, profile):
        """@brief Bind protected project inputs without putting any secret in queue/history."""
        digest = sha256()
        try:
            for name in (".env", "repository-auth.json"):
                raw = read_private_record(self.profiles.profile_dir(profile.name) / name, 65536)
                digest.update(name.encode())
                digest.update(b"missing" if raw is None else b"present" + raw)
        except (OSError, ValueError) as exc:
            raise HTTPException(503, detail={"code": "executor_credentials_corrupt"}) from exc
        return digest.hexdigest()

    @staticmethod
    def resource_name(resource, handler, payload):
        """@brief Separate enrollment scheduling by explicit prospective project."""
        if resource == "enrollment":
            body = payload.get("body", {})
            target = body.get("target", body)
            return "enrollment:" + str(target.get("name", handler))
        return resource or handler

    def settings_lane(self, profile, payload):
        """@brief Reserve fast capacity for settings with no model/host/image plan probe."""
        import tomllib

        try:
            config = tomllib.loads(self.configuration_bytes(profile).decode("utf-8"))
        except (OSError, ValueError):
            return "fast"
        execution = config.get("execution", {})
        if not isinstance(execution, dict):
            raise HTTPException(503, detail={"code": "config_corrupt"})
        body = payload.get("body", {})
        if (
            execution.get("backend") == "local"
            or execution.get("preparation")
            or body.get("key") in ("execution.backend", "execution.preparation")
            or body.get("key") == "settings.batch"
            and "execution.backend" in body.get("value", "")
        ):
            return "long"
        # Apply follows the reviewed candidate, which may switch to a probed backend.
        if "candidate_revision" in body:
            pending = profile and self.profiles.profile_dir(profile.name) / "pending_config.json"
            if pending.is_file():
                try:
                    raw = read_private_record(pending, MAX_RECORD)
                    value = strict_json_loads(raw.decode("utf-8"))
                    proposed = tomllib.loads(value["candidate_text"]).get("execution", {})
                    if not isinstance(proposed, dict):
                        return "fast"  # Existing candidate parser refuses corrupt stored structure.
                    if proposed.get("backend") == "local" or proposed.get("preparation"):
                        return "long"
                except (OSError, ValueError, TypeError, KeyError):
                    pass  # The declared handler returns the existing corrupt-candidate error.
        return "fast"

    def read(self, reference, suffix):
        """@brief Read a bounded protected work/result record with a closed format."""
        if not re.fullmatch(r"[a-f0-9]{32}", reference) or self.directory.is_symlink():
            raise WebStoreError("configuration storage is corrupt")
        try:
            raw = read_private_record(self.directory / (reference + suffix), MAX_RECORD)
            if raw is None:
                raise WebStoreError("configuration request is missing")
            if suffix == ".request.json" and sha256(raw).hexdigest()[:32] != reference:
                raise ValueError("configuration request binding changed")
            result = strict_json_loads(raw.decode("utf-8"))
            if not isinstance(result, dict):
                raise ValueError("invalid record")
            return result
        except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
            raise WebStoreError("configuration storage is corrupt") from exc

    def outcome(self, operation):
        """@brief Return only a confirmed public result, never the protected input."""
        if operation["status"] not in ("succeeded", "failed"):
            return None
        path = self.directory / (operation["run_id"] + ".result.json")
        if (
            not path.exists()
            and not path.is_symlink()
            and operation["status"] == "failed"
            and operation["reason"]
            in (
                "permission_revoked",
                "project_corrupt",
                "project_identity_changed",
                "project_archived",
            )
        ):
            return {
                "status_code": 409,
                "body": {"detail": {"code": operation["reason"] or "configuration_refused"}},
            }
        result = self.read(operation["run_id"], ".result.json")
        if (
            set(result) != {"schema", "operation_id", "status_code", "body"}
            or type(result["schema"]) is not int
            or result["schema"] != 1
            or type(result["operation_id"]) is not int
            or result["operation_id"] != operation["id"]
            or type(result["status_code"]) is not int
            or not 200 <= result["status_code"] <= 599
            or not isinstance(result["body"], dict | list | type(None))
            or (operation["status"] == "succeeded") != (result["status_code"] < 400)
        ):
            raise WebStoreError("configuration outcome is corrupt")
        return {"status_code": result["status_code"], "body": result["body"]}


class ConfigurationWorker:
    """@brief Independent bounded lanes with one in-flight configure task per project."""

    def __init__(self, tasks, *, owner=None, long_slots=4, fast_slots=4, clock=time.monotonic):
        """@brief Create independent finite pools under one configuration process owner.
        @param[in] tasks Registered typed handlers and protected record storage.
        @param[in] owner Existing supervised owner, or a new standalone configuration owner.
        @param[in] long_slots Long-probe capacity, from one to sixteen.
        @param[in] fast_slots Fast-save capacity, from one to sixteen.
        @param[in] clock Injectable monotonic task-budget clock.
        """
        if not 1 <= long_slots <= 16 or not 1 <= fast_slots <= 16:
            raise ValueError("invalid configuration capacity")
        self.tasks, self.web, self.profiles = tasks, tasks.web, tasks.profiles
        self.clock = clock
        self.owner = owner or self.web.register_worker("configuration")
        self.owners = {"": self.owner}
        self.pools = {
            "long": ThreadPoolExecutor(long_slots),
            "fast": ThreadPoolExecutor(fast_slots),
            "global": ThreadPoolExecutor(1),
        }
        self.limits = {"long": long_slots, "fast": fast_slots, "global": 1}
        self.running = {}

    def scoped_owner(self, project_id):
        """@brief Retain one durable owner per explicit project during all its work."""
        if project_id not in self.owners:
            self.web.recover_interrupted(role="configuration", project_id=project_id)
            self.owners[project_id] = self.web.register_worker(
                "configuration", project_id=project_id
            )
        return self.owners[project_id]

    def tick(self):
        """@brief Drain completed work, immediate controls and bounded new requests."""
        from adore.web.processes import assert_ancestry

        assert_ancestry()
        for identity, (future, _) in list(self.running.items()):
            if future.done():
                future.result()
                del self.running[identity]
        for owner in self.owners.values():
            self.web.touch_worker(owner)
        # No pool slot or configure completion is needed for admission controls.
        for domain, identity in self.web.pending_domains(actions=("pause", "resume")):
            owner = self.scoped_owner(identity)
            operation = self.web.claim_next(owner, domain=domain, actions=("pause", "resume"))
            if operation is None or operation["status"] != "running":
                continue
            try:
                self.web.authorize_effect(
                    operation["id"], owner=owner, generation=operation["generation"]
                )
                profile = self.profiles.find_by_id(identity)
                if profile is None:
                    raise OwnershipError("control project is unavailable")
                state = StateStore(
                    profile.store_root or self.profiles.default_store_root(profile.name)
                )
                state.before_write = lambda operation=operation, owner=owner: (
                    self.web.authorize_effect(
                        operation["id"], owner=owner, generation=operation["generation"]
                    )
                )
                getattr(state, operation["action"])()
                self.web.finish(
                    operation["id"],
                    "succeeded",
                    "completed",
                    owner=owner,
                    generation=operation["generation"],
                )
            except (OSError, RuntimeError, ValueError, TypeError):
                self.web.finish(
                    operation["id"],
                    "failed",
                    "control refused",
                    reason="control_refused",
                    owner=owner,
                    generation=operation["generation"],
                )
        pending_identities = {row["project_id"] for row in self.web.pending_configuration()}
        control_identities = {
            identity for _, identity in self.web.pending_domains(actions=("pause", "resume"))
        }
        for identity, owner in list(self.owners.items()):
            if (
                identity
                and identity not in self.running
                and identity not in pending_identities | control_identities
            ):
                self.web.clear_worker(owner)
                del self.owners[identity]
        used = {lane: sum(item[1] == lane for item in self.running.values()) for lane in self.pools}
        for pending in self.web.pending_configuration():
            if pending["status"] != "pending":
                continue
            identity = pending["project_id"]
            try:
                envelope = self.tasks.read(pending["run_id"], ".request.json")
                schedule = identity or "global:" + str(envelope.get("resource", "invalid"))
                lane = envelope.get("lane")
                if lane not in self.pools:
                    lane = "fast"  # Invalid envelopes still get a durable failed result.
            except (OSError, RuntimeError, ValueError):
                lane, schedule = "fast", identity or "global:invalid"
            if schedule in self.running:
                continue
            if used[lane] >= self.limits[lane]:
                continue
            owner = self.scoped_owner(identity)
            operation = self.web.claim_next(
                owner, domain=pending["domain"], action="configure", operation_id=pending["id"]
            )
            if operation is None:
                continue
            if operation["status"] != "running":
                (self.tasks.directory / (operation["run_id"] + ".request.json")).unlink(
                    missing_ok=True
                )
                continue
            used[lane] += 1
            self.running[schedule] = (self.pools[lane].submit(self.execute, operation, owner), lane)
        self.web.set_worker_activity(self.owner, "busy" if self.running else "idle")

    def execute(self, operation, owner):
        """@brief Rehydrate a declared handler under current authority and revision fencing."""
        reference = operation["run_id"]
        deadline = self.clock() + TASK_SECONDS

        def authorize(*, revision=True):
            """@brief Fence current rights, immutable target, revision and finite lifetime."""
            from adore.web.processes import assert_ancestry

            assert_ancestry()
            self.web.authorize_effect(
                operation["id"], owner=owner, generation=operation["generation"]
            )
            if self.clock() >= deadline:
                raise HTTPException(409, detail={"code": "configuration_timeout"})
            if operation["project_id"]:
                profile = self.profiles.find_by_id(operation["project_id"])
                if profile is None:
                    raise OwnershipError("configuration project identity changed")
                if (
                    revision
                    and sha256(self.tasks.configuration_bytes(profile)).hexdigest()
                    != envelope["revision"]
                ):
                    raise HTTPException(409, detail={"code": "stale_config_revision"})
                if (
                    revision
                    and self.tasks.credential_revision(profile) != envelope["credential_revision"]
                ):
                    raise HTTPException(409, detail={"code": "stale_config_revision"})

        token, current, time_token, owner_token = None, None, None, None
        handler_started = False
        handler_completed = False
        code, body, status, reason = 200, None, "succeeded", ""
        try:
            envelope = self.tasks.read(reference, ".request.json")
            expected = {
                "schema",
                "nonce",
                "handler",
                "actor_id",
                "project_id",
                "revision",
                "credential_revision",
                "scope",
                "lane",
                "arguments",
                "resource",
            }
            if (
                set(envelope) != expected
                or type(envelope["schema"]) is not int
                or envelope["schema"] != 1
                or envelope["actor_id"] != operation["actor_id"]
                or envelope["project_id"] != operation["project_id"]
                or envelope["handler"] not in self.tasks.handlers
            ):
                raise WebStoreError("configuration request is corrupt")
            handler, signature, scope, lane, resource = self.tasks.handlers[envelope["handler"]]
            if (
                envelope["scope"] != scope
                or (
                    envelope["lane"] not in ("fast", "long")
                    if lane == "settings"
                    else envelope["lane"] != lane
                )
                or envelope["resource"]
                != self.tasks.resource_name(resource, envelope["handler"], envelope["arguments"])
                or (scope == "project") != bool(operation["project_id"])
                or not isinstance(envelope["arguments"], dict)
                or scope == "project"
                and not re.fullmatch(r"[a-f0-9]{64}", envelope["revision"])
                or scope == "global"
                and envelope["revision"] != ""
            ):
                raise WebStoreError("configuration scope is corrupt")
            authorize()
            arguments = dict(envelope["arguments"])
            if scope == "project" and arguments.get("name") != operation["project_id"]:
                raise WebStoreError("configuration target is corrupt")
            actor_parameter = "user" if "user" in signature.parameters else "_user"
            arguments[actor_parameter] = self.web.user_by_id(operation["actor_id"])
            for name, value in list(arguments.items()):
                annotation = signature.parameters[name].annotation
                if get_origin(annotation) is Annotated:
                    annotation = get_args(annotation)[0]
                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    arguments[name] = annotation.model_validate(value)
                elif annotation is Request:
                    if (
                        not isinstance(value, dict)
                        or set(value) != {"method", "headers"}
                        or not isinstance(value["headers"], dict)
                        or not set(value["headers"]).issubset({"cookie", "x-csrf-token"})
                        or value["method"] not in ("POST", "PUT", "DELETE")
                    ):
                        raise WebStoreError("configuration request method is corrupt")
                    arguments[name] = Request(
                        {
                            "type": "http",
                            "method": value["method"],
                            "headers": [
                                (key.encode(), val.encode())
                                for key, val in value["headers"].items()
                            ],
                        }
                    )
            signature.bind(**arguments)

            def authorize_cleanup():
                """@brief Fence exact worker ownership/ancestry without revoked actor authority."""
                from adore.web.processes import assert_ancestry

                assert_ancestry()
                self.web.assert_worker(owner)

            token = _EFFECT.set(authorize)
            owner_token = _OWNER_GUARD.set(authorize_cleanup)
            time_token = _DEADLINE.set(deadline)
            current = _OPERATION.set(operation["id"])
            handler_started = True
            body = handler(**arguments)
            handler_completed = True
            effect_guard(revision=False)
        except HTTPException as exc:
            code, body, status = exc.status_code, {"detail": exc.detail}, "failed"
            reason = (
                exc.detail.get("code", "configuration_refused")
                if isinstance(exc.detail, dict)
                else "configuration_refused"
            )
        except OwnershipError as exc:
            code, reason, status = (
                (409, "configuration_confirmation_failed", "uncertain")
                if handler_completed or exc.reason == "configuration_confirmation_failed"
                else (409, exc.reason or "permission_revoked", "failed")
            )
            body = {"detail": {"code": reason}}
        except WebStoreError:
            code, reason, status = (
                (503, "configuration_confirmation_failed", "uncertain")
                if handler_started
                else (503, "configuration_request_corrupt", "failed")
            )
            body = {"detail": {"code": reason}}
            if not handler_started:
                body["detail"]["message"] = (
                    "Delete ADORE_HOME/configuration-tasks/"
                    + reference
                    + ".request.json to discard this refused request before starting fresh."
                )
        except (ValueError, TypeError, KeyError):
            code, reason, status = 422, "invalid_request", "failed"
            body = {"detail": {"code": reason}}
        except (OSError, RuntimeError):
            code, reason, status = 503, "configuration_failed", "uncertain"
            body = {"detail": {"code": reason}}
        finally:
            if token is not None:
                _EFFECT.reset(token)
                _OPERATION.reset(current)
                _DEADLINE.reset(time_token)
                _OWNER_GUARD.reset(owner_token)
        # No raw exception, command output or request is copied into SQLite/history.
        if status != "uncertain":
            result = {
                "schema": 1,
                "operation_id": operation["id"],
                "status_code": code,
                "body": body,
            }
            write_private_record(
                self.tasks.directory / (reference + ".result.json"), json.dumps(result).encode()
            )
        self.web.finish(
            operation["id"],
            status,
            "completed" if status == "succeeded" else reason,
            owner=owner,
            generation=operation["generation"],
            reason=reason,
        )
        if reason != "configuration_request_corrupt":
            (self.tasks.directory / (reference + ".request.json")).unlink(missing_ok=True)

    def close(self):
        """@brief Drain finite tasks on orderly exit and relinquish exact ownership."""
        for pool in self.pools.values():
            pool.shutdown(wait=True)
        for owner in self.owners.values():
            self.web.clear_worker(owner)


# END OF FILE
