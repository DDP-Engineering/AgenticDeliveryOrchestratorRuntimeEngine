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
@file    local_execution.py
@brief   Native installed-executor implementation of the shared backend contract.
@details Reuses existing account credentials in place. No container, recipe,
         tooling installation, account switching or host sandbox is provided.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy

# IMPORTS
from dataclasses import asdict
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile
from uuid import uuid4

from adore.execution import ExecutionPaths
from adore.isolation import IsolationError
from adore.local_process import (
    LocalExecutionError,
    LocalProcessController,
    NativeScopes,
    atomic_record,
    native_context,
    read_record,
)
from adore.util import CommandResult, automatic_environment, strict_json_loads

# CONSTANTS
SYSTEM_ENV_KEYS = frozenset(
    {
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "APPDATA",
        "LOCALAPPDATA",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "TZ",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "NODE_EXTRA_CA_CERTS",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "CODEX_HOME",
        "PI_CODING_AGENT_DIR",
    }
)
# Windows machine/system names that platform detection, executable lookup and
# %SystemDrive%-style folder expansion need; account-derived names stay managed.
WINDOWS_SYSTEM_ENV_KEYS = frozenset(
    {
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_ARCHITEW6432",
        "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL",
        "PROCESSOR_REVISION",
        "NUMBER_OF_PROCESSORS",
        "OS",
        "SYSTEMDRIVE",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "COMMONPROGRAMFILES",
        "COMMONPROGRAMFILES(X86)",
        "COMMONPROGRAMW6432",
        "ALLUSERSPROFILE",
        "PUBLIC",
    }
)
# Local OpenCode commands resolve this policy instead of the account's personal
# permissions: tools work non-interactively, push and forge CLIs are denied.
OPENCODE_PERMISSION_POLICY = {
    "edit": "allow",
    "bash": {
        "*": "allow",
        "git push*": "deny",
        "tea *": "deny",
        "gh *": "deny",
        "glab *": "deny",
    },
}
MANAGED_OPENCODE_ENV_KEYS = frozenset(
    {"XDG_CONFIG_HOME", "OPENCODE_DISABLE_CLAUDE_CODE", "OPENCODE_PERMISSION"}
)
RESOURCE_KEYS = {"kind", "id", "host", "account", "name", "worktree", "io"}
FORBIDDEN_EXECUTABLES = {
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "wsl",
    "wsl.exe",
    "bash",
    "bash.exe",
    "sh",
    "sh.exe",
}
LOCAL_PROBE_REASONS = frozenset({
    "ready", "executable-missing", "credential-missing", "credential-invalid",
    "executor-exit", "version-invalid", "timeout", "account-mismatch",
    "permission-denied", "scope-error", "cleanup-failed", "runtime-error",
})


class LocalPrerequisiteError(LocalExecutionError):
    """@brief Preserve a closed prerequisite cause and the measured process status."""

    def __init__(self, reason: str, exit_code: int | None = None):
        """@brief Carry safe diagnostic data without retaining command output."""
        super().__init__(reason)
        self.reason, self.exit_code = reason, exit_code

# LOCAL HELPERS


def fingerprint(value: dict) -> str:
    """@brief Canonical non-secret local identity digest.
    @param[in] value Closed native JSON record.
    @return Verified native operation result.
    """
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def local_argv(template: str, *, prompt: str, model: str, worktree: str) -> list[str]:
    """@brief Tokenize before substitution, keeping spaces/prompts as native data.
    @param[in] template Explicit argv template, with no shell compounds.
    @param[in] prompt Full gate instruction.
    @param[in] model Configured model identifier.
    @param[in] worktree Native ticket worktree.
    @return Fresh-session argv.
    @exception LocalExecutionError Unsupported or malformed argv template.
    """
    try:
        tokens = shlex.split(template)
        if not tokens or any(token in {"&&", "||", ";", "|", ">", "<", "&"} for token in tokens):
            raise ValueError
        result = [
            token.format(prompt=prompt, model=model, worktree=worktree)
            for token in tokens
        ]
        return [token for token in result if token]
    except (ValueError, KeyError, IndexError) as exc:
        raise LocalExecutionError("local executor requires a native argv template") from exc


def managed_opencode_config(config) -> Path | None:
    """@brief Locate the ADORE-managed OpenCode configuration home of a local profile.
    @param[in] config Validated local profile.
    @return `<state root>/executor-config` when OpenCode is the default executor, else None.
    """
    if config.executor.default != "opencode":
        return None
    return Path(config.state.store_root).resolve() / "executor-config"


def local_environment(config, context: dict, secrets: dict | None = None) -> dict[str, str]:
    """@brief Build the selected account's explicit environment without forge tokens.
    @param[in] config Validated local profile.
    @param[in] context Actual native account/machine defaults.
    @param[in] secrets Approved executor values supplied in memory only.
    @return Controlled environment shared by probes and gates.
    @exception LocalExecutionError Account assertion, home or platform is unsupported.
    """
    if context["system"] not in {"Windows", "Linux"}:
        raise LocalExecutionError("unsupported local execution platform")
    if (
        config.local.account != "current"
        and config.local.account.casefold() != context["account"].casefold()
    ):
        raise LocalExecutionError("local account differs from the ADORE process account")
    home = str(Path(config.local.home or context["home"]).expanduser().resolve())
    if not Path(home).is_dir():
        raise LocalExecutionError("selected local account home is unavailable")
    # Windows environment lookup is case-insensitive; filtering names is explicit.
    allowed = SYSTEM_ENV_KEYS
    if context["system"] == "Windows":
        allowed = allowed | WINDOWS_SYSTEM_ENV_KEYS
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    managed = managed_opencode_config(config)
    if managed is not None:
        # Replaces the account's personal OpenCode configuration home; explicit [local] values win.
        env.update(
            XDG_CONFIG_HOME=str(managed),
            OPENCODE_DISABLE_CLAUDE_CODE="1",
            OPENCODE_PERMISSION=json.dumps(OPENCODE_PERMISSION_POLICY, separators=(",", ":")),
        )
    if managed is not None and context["system"] == "Windows":
        # A differently cased explicit managed name replaces the managed entry.
        explicit = {key.upper() for key in config.local.environment} & MANAGED_OPENCODE_ENV_KEYS
        env = {key: value for key, value in env.items() if key not in explicit}
    env.update(config.local.environment)
    env.update(
        HOME=home,
        USERPROFILE=home,
        PATH=config.local.path or context["path"],
        USER=context["account"],
        LOGNAME=context["account"],
        USERNAME=context["account"],
    )
    env.setdefault("CODEX_HOME", str(Path(home) / ".codex"))
    env.setdefault("PI_CODING_AGENT_DIR", str(Path(home) / ".pi" / "agent"))
    approved = set(config.executor.env_keys)
    env.update({key: value for key, value in (secrets or {}).items() if key in approved})
    return automatic_environment(env)


def resolve_executable(command: str, env: dict[str, str], system: str) -> str:
    """@brief Resolve one installed native executable without a shell or installer.
    @param[in] command Explicit executable token.
    @param[in] env Selected native environment.
    @param[in] system Native Windows/Linux platform.
    @return Exact executable path used by gates/probes.
    @exception LocalExecutionError Missing CLI, shell wrapper or unsafe Windows shim.
    """
    found = command if Path(command).is_absolute() else None
    if found is None:
        for item in env["PATH"].split(";" if system == "Windows" else ":"):
            directory = Path(item)
            if not item or not directory.is_absolute():
                continue  # A checkout/current directory is never executable authority.
            candidate = directory / command
            if system == "Windows" and candidate.suffix == "":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                found = str(candidate)
                break
    if not found or not Path(found).is_file():
        raise LocalExecutionError("selected local executable is unavailable")
    path = Path(found).resolve()
    if path.name.casefold() in FORBIDDEN_EXECUTABLES:
        raise LocalExecutionError("local shell and Windows-to-WSL wrappers are unsupported")
    if system == "Windows" and path.suffix.casefold() != ".exe":
        raise LocalExecutionError(
            "local Windows requires an executable or explicit node entrypoint"
        )
    if system == "Linux" and not os.access(path, os.X_OK):
        raise LocalExecutionError("selected local executable is not executable")
    return str(path)


def local_policy(config, *, context: dict | None = None, resolver=resolve_executable) -> dict:
    """@brief Pin native account/environment and installed executable without commands.
    @param[in] config Validated profile.
    @param[in] context Injectable actual native context.
    @param[in] resolver Injectable executable filesystem boundary.
    @return Closed non-secret native plan policy.
    """
    context = context or native_context()
    env = local_environment(config, context)
    entry = config.executor.commands[config.executor.default]
    argv = local_argv(
        entry.command, prompt="", model=entry.model, worktree=config.worktree.repo_path
    )
    executable = resolver(argv[0], env, context["system"])
    details = Path(executable).stat()
    identity = {
        "size": details.st_size,
        "mtime_ns": details.st_mtime_ns,
        "inode": details.st_ino,
        "device": details.st_dev,
    }
    if Path(executable).stem.casefold() == "node":
        if len(argv) < 2:
            raise LocalExecutionError("explicit node launch needs an installed entrypoint")
        script = Path(argv[1])
        if (
            not script.is_absolute()
            or script.suffix.lower() not in {".js", ".mjs", ".cjs"}
            or not script.is_file()
            or script.resolve().is_relative_to(Path(config.worktree.repo_path).resolve())
        ):
            raise LocalExecutionError("node entrypoint must be installed outside the project")
        script_stat = script.stat()
        identity["entrypoint"] = {
            "path": str(script.resolve()),
            "size": script_stat.st_size,
            "mtime_ns": script_stat.st_mtime_ns,
            "inode": script_stat.st_ino,
            "device": script_stat.st_dev,
        }
    return {
        "settings": asdict(config.local),
        "host": context["host"],
        "account": context["account"],
        "system": context["system"],
        "environment_sha256": fingerprint(env),
        "executable": executable,
        "executable_sha256": fingerprint(identity),
    }


def validate_local_resource(resource: object) -> dict:
    """@brief Validate the closed additive native resource record.
    @param[in] resource Untrusted persisted mapping.
    @return Trusted local resource identity.
    @exception LocalExecutionError Unsupported or corrupt identity.
    """
    if (
        not isinstance(resource, dict)
        or set(resource) != RESOURCE_KEYS
        or any(
            not isinstance(value, str) or not value or "\x00" in value
            for value in resource.values()
        )
        or resource["kind"] != "local"
        or not re.fullmatch(r"[0-9a-f]{32}", resource["id"])
        or not re.fullmatch(r"[0-9a-f]{64}", resource["host"])
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", resource["name"])
        or any(
            not (Path(resource[key]).is_absolute() or ntpath.isabs(resource[key]))
            for key in ("worktree", "io")
        )
    ):
        raise LocalExecutionError("local resource identity is corrupt")
    return resource


# PUBLIC API


class LocalBackend:
    """@brief Native preinstalled-executor adapter on the shared lifecycle boundary."""

    paths = ExecutionPaths(shell="")

    def __init__(
        self, config, *, controller=None, context=None, resolver=resolve_executable
    ) -> None:
        """@brief Select current native account; inject scopes/processes for offline proof."""
        from adore.config import validate_config

        issues = [
            issue
            for issue in validate_config(config)
            if issue.startswith(("[local]", "[execution]"))
        ]
        if config.execution.backend != "local" or issues:
            raise LocalExecutionError("invalid local profile: " + "; ".join(issues))
        self.config = config
        self.context = context or native_context()
        self.resolver = resolver
        self.policy = local_policy(config, context=self.context, resolver=resolver)
        self.environment = local_environment(config, self.context)
        managed = managed_opencode_config(config)
        if managed is not None and self.environment.get("XDG_CONFIG_HOME") == str(managed):
            try:
                managed.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise LocalExecutionError(
                    "managed executor configuration directory is unavailable"
                ) from exc
        self.controller = controller or LocalProcessController(
            NativeScopes(self.context["system"], config.local.cgroup_root)
        )
        self.targets: dict[str, dict] = {}

    def executor_environment(self, executor: str) -> dict[str, str]:
        """@brief Return the actual selected native home/environment without auth copies.
        @param[in] executor Selected executor kind.
        @return Verified native operation result.
        """
        return dict(self.environment)

    def auth_directory(self, executor: str) -> str:
        """@brief Native auth is reused in place; container staging is unsupported.
        @param[in] executor Selected executor kind.
        """
        raise LocalExecutionError("local authentication is reused in place, never staged")

    def image_identity(self, image: str) -> str:
        """@brief Local execution never inspects or creates executor images.
        @param[in] image Absent in local mode.
        """
        raise LocalExecutionError("local execution has no image identity")

    def _control(self, resource: dict) -> Path:
        """@brief Resolve only the configured state-owned native control directory."""
        validate_local_resource(resource)
        io = Path(resource["io"])
        root = Path(self.config.state.store_root).resolve() / "runs"
        if (
            resource["host"] != self.context["host"]
            or resource["account"] != self.context["account"]
            or not io.resolve().is_relative_to(root)
            or io.name != "io"
            or io.is_symlink()
        ):
            raise LocalExecutionError(
                "local runtime belongs to a different machine/account/state root"
            )
        control = io.parent / "local-control"
        if control.resolve() != control:
            raise LocalExecutionError("native control directory is linked or aliased")
        return control

    def revalidate_for_retry(self, name: str, expected: dict, previous_policy: dict) -> None:
        """@brief Refresh an owned native receipt after explicit Retry authorization.
        @param[in] name Persisted resource name.
        @param[in] expected Unchanged run resource identity.
        @param[in] previous_policy Previously pinned local policy, checked by the conductor.
        @exception LocalExecutionError Corrupt receipt or foreign ownership.
        """
        control = self._control(expected)
        receipt = read_record(control / "runtime.json")
        if (
            set(receipt) != {"schema", "resource", "policy_sha256"}
            or type(receipt["schema"]) is not int or receipt["schema"] != 1
            or receipt["resource"] != expected or expected["name"] != name
            or receipt["policy_sha256"] not in (
                fingerprint(previous_policy), fingerprint(self.policy)
            )
        ):
            raise LocalExecutionError("native Retry receipt differs from the saved job")
        self.controller.recover(control, expected["id"], expected["host"])
        atomic_record(control / "runtime.json", {
            "schema": 1, "resource": expected, "policy_sha256": fingerprint(self.policy),
        })
        self.targets[name] = expected

    def verify_identity(self, name: str, expected: dict) -> dict:
        """@brief Refuse state/config/resource drift before commands or controls.
        @param[in] name Owned native resource or Job name.
        @param[in] expected Pinned persisted native resource identity.
        @return Verified native operation result.
        """
        control = self._control(expected)
        receipt = read_record(control / "runtime.json")
        current = local_policy(self.config, context=self.context, resolver=self.resolver)
        if (
            set(receipt) != {"schema", "resource", "policy_sha256"}
            or type(receipt["schema"]) is not int
            or receipt["schema"] != 1
            or receipt["resource"] != expected
            or expected["name"] != name
            or receipt["policy_sha256"] != fingerprint(current)
            or current != self.policy
        ):
            raise LocalExecutionError(
                "local runtime or selected account/environment/executable drifted"
            )
        return expected

    def provision(self, name, repo, worktree, io, env, *, image=None) -> str:
        """@brief Create/resume native control identity; no tools, images or recipes.
        @param[in] name Existing run resource name.
        @param[in] repo Main clone (owned by WorktreeManager).
        @param[in] worktree Dedicated native ticket worktree.
        @param[in] io Parent-owned native exchange directory.
        @param[in] env Approved executor environment values.
        @param[in] image Must be absent in local mode.
        @return Created or resumed native target.
        """
        if image is not None:
            raise LocalExecutionError("local execution cannot provision an image")
        worktree, io = Path(worktree).resolve(), Path(io).resolve()
        if not worktree.is_dir() or io.is_relative_to(worktree):
            raise LocalExecutionError("local IO must be outside the dedicated worktree")
        control = io.parent / "local-control"
        receipt = control / "runtime.json"
        if receipt.exists():
            record = read_record(receipt)
            resource = validate_local_resource(record.get("resource"))
            if resource["worktree"] != str(worktree) or resource["io"] != str(io):
                raise LocalExecutionError("local native paths changed")
            self.verify_identity(name, resource)
            self.controller.recover(control, resource["id"], resource["host"])
            outcome = "resumed"
        else:
            resource = {
                "kind": "local",
                "id": uuid4().hex,
                "host": self.context["host"],
                "account": self.context["account"],
                "name": name,
                "worktree": str(worktree),
                "io": str(io),
            }
            self._control(resource)
            atomic_record(
                receipt,
                {"schema": 1, "resource": resource, "policy_sha256": fingerprint(self.policy)},
            )
            outcome = "created"
        io.mkdir(parents=True, exist_ok=True)
        self.targets[name] = resource
        return outcome

    def resource_identity(self, name: str) -> dict:
        """@brief Return verified native run identity, distinct from process leases.
        @param[in] name Owned native resource or Job name.
        @return Verified native operation result.
        """
        if name not in self.targets:
            raise LocalExecutionError("local target is not bound")
        return dict(self.verify_identity(name, self.targets[name]))

    def bind(self, name: str, env: dict, expected: dict | None = None):
        """@brief Bind native commands and paths to exact durable run ownership.
        @param[in] name Owned native resource or Job name.
        @param[in] env Controlled account environment and approved values.
        @param[in] expected Pinned persisted native resource identity.
        @return Verified native operation result.
        """
        resource = expected or self.targets.get(name)
        if resource is None:
            raise LocalExecutionError("local target identity is missing")
        self.verify_identity(name, resource)
        return LocalTarget(self, name, env, resource)

    def verify_required_tools(self, name: str, checks, *, env: dict) -> None:
        """@brief Check only executor availability; project tools remain user-owned.
        @param[in] name Owned native resource or Job name.
        @param[in] checks Empty; project tools are user-owned.
        @param[in] env Controlled account environment and approved values.
        """
        if checks:
            raise LocalExecutionError(
                "local project tool discovery/check manifests are unsupported"
            )
        target = self.bind(name, env)
        entry = self.config.executor.commands[self.config.executor.default]
        argv = local_argv(
            entry.command, prompt="", model=entry.model, worktree=target.paths.worktree
        )
        prefix = argv[:2] if Path(argv[0]).stem.casefold() == "node" else argv[:1]
        checked = target([*prefix, "--version"], timeout=10)
        if checked.timed_out:
            raise LocalPrerequisiteError("timeout", checked.exit_code)
        if not checked.ok:
            raise LocalPrerequisiteError("executor-exit", checked.exit_code)
        # Native CLIs may report their version on stderr. Require an actual
        # version line, rather than accepting digits in an unrelated warning.
        version = (r"(?:(?:opencode|pi(?:-coding-agent)?|codex(?:-cli)?|qwen(?:-code)?)"
                   r"(?: version)?:?\s*)?v?\d+\.\d+(?:\.\d+)?(?:[-+][\w.-]+)?")
        if not any(re.fullmatch(version, line.strip(), re.I)
                   for line in re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "",
                                      checked.stdout + "\n" + checked.stderr).splitlines()):
            raise LocalPrerequisiteError("version-invalid", checked.exit_code)

    def interrupt(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Terminate only verified native command scope, never a bare PID.
        @param[in] name Owned native resource or Job name.
        @param[in] expected Pinned persisted native resource identity.
        """
        resource = expected or self.targets.get(name)
        if resource is None:
            raise LocalExecutionError("local control identity is missing")
        self.verify_identity(name, resource)
        self.controller.interrupt(self._control(resource), resource["id"], resource["host"])

    def stop(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Park without a live process; retain worktree, evidence and identity.
        @param[in] name Owned native resource or Job name.
        @param[in] expected Pinned persisted native resource identity.
        """
        self.interrupt(name, expected=expected)
        resource = expected or self.targets[name]
        self.controller.recover(self._control(resource), resource["id"], resource["host"])

    def remove(self, name: str, *, expected: dict | None = None) -> None:
        """@brief Release only verified run control; preserve all installed tools/auth.
        @param[in] name Owned native resource or Job name.
        @param[in] expected Pinned persisted native resource identity.
        """
        resource = expected or self.targets.get(name)
        if resource is None:
            raise LocalExecutionError("local cleanup identity is missing")
        control = self._control(resource)
        if not (control / "runtime.json").exists():
            if (control / "active-process.json").exists():
                raise LocalExecutionError("local cleanup ownership receipt is missing")
            return
        self.interrupt(name, expected=resource)
        self.controller.recover(control, resource["id"], resource["host"])
        (control / "runtime.json").unlink()
        self.targets.pop(name, None)


class LocalTarget:
    """@brief Native argv/file target carrying the existing backend path contract."""

    def __init__(self, backend: LocalBackend, name: str, env: dict, resource: dict) -> None:
        self.backend, self.name, self.env, self.resource = backend, name, dict(env), resource
        self.paths = ExecutionPaths(worktree=resource["worktree"], io=resource["io"], shell="")
        # Bound for non-AEGIS native output; Test AI connection raises it on its probe target.
        self.output_limit = 65536

    def _auth_path(self) -> Path:
        """@brief Locate the installed executor's existing account credential store."""
        config = self.backend.config
        home = Path(self.env["HOME"])
        locations = {
            "opencode": Path(self.env.get("XDG_DATA_HOME", str(home / ".local/share")))
            / "opencode/auth.json",
            "codex": Path(self.env["CODEX_HOME"]) / "auth.json",
            "pi": Path(self.env["PI_CODING_AGENT_DIR"]) / "auth.json",
            "qwen": home / ".qwen/oauth_creds.json",
        }
        return locations[config.executor.default]

    def auth_available(self) -> bool:
        """@brief Check bounded existing auth or approved provider values without login."""
        self._secrets()
        return self._auth_path().is_file() or any(
            self.env.get(key) for key in self.backend.config.executor.env_keys
        )

    def _secrets(self) -> list[str]:
        """@brief Read approved existing auth values only for in-memory redaction."""
        config = self.backend.config
        values = {self.env[key] for key in config.executor.env_keys if self.env.get(key)}
        path = self._auth_path()
        if path.exists():
            try:
                if path.stat().st_size > 131072 or path.resolve().is_relative_to(
                    Path(self.paths.worktree)
                ):
                    raise ValueError
                data = strict_json_loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError
                pending = [(data, 0)]
                while pending:
                    item, depth = pending.pop()
                    if depth > 16:
                        raise ValueError
                    if isinstance(item, str) and item:
                        item.encode("utf-8")
                        values.add(item)
                    elif isinstance(item, (dict, list)):
                        pending.extend(
                            (v, depth + 1)
                            for v in (item.values() if isinstance(item, dict) else item)
                        )
            except (OSError, ValueError, TypeError) as exc:
                raise LocalExecutionError("local executor auth store is corrupt or unsafe") from exc
        return sorted(values, key=len, reverse=True)

    def redact(self, text: str) -> str:
        """@brief Remove known account/provider values before retained file evidence.
        @param[in] text Evidence text to redact before retention.
        @return Verified native operation result.
        """
        for value in self._secrets():
            text = text.replace(value, "[REDACTED]")
        return text

    def read_output(self, path: Path, *, optional: bool = False) -> str:
        """@brief Validate and redact bounded native file evidence before retention.
        @param[in] path Owned exchange or questions file.
        @param[in] optional Permit an absent questions file.
        @return Strict UTF-8 redacted evidence.
        @exception LocalExecutionError Missing, linked, oversized or corrupt output.
        """
        try:
            from adore.aegis import AEGIS_STDOUT_FILE, MAX_JSON_BYTES

            limit = MAX_JSON_BYTES if path.name == AEGIS_STDOUT_FILE else self.output_limit
            if optional and not path.exists() and not path.is_symlink():
                return ""
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size > limit
                or not any(
                    path.resolve().is_relative_to(Path(root))
                    for root in (self.paths.io, self.paths.worktree)
                )
            ):
                raise ValueError
            text = self.redact(path.read_text(encoding="utf-8"))
            path.write_text(text, encoding="utf-8", newline="\n")
            return text
        except (OSError, ValueError) as exc:
            raise LocalExecutionError("native output evidence missing or corrupt") from exc

    def run_files(self, argv, stdout: Path, stderr: Path, *, timeout=None) -> CommandResult:
        """@brief Execute native argv with owned scopes and bounded redacted file output.
        @param[in] argv Native argv; no shell interpretation.
        @param[in] stdout Owned bounded stdout file.
        @param[in] stderr Owned bounded stderr file.
        @param[in] timeout Positive finite wall-time bound.
        @return Verified native operation result.
        """
        backend = self.backend
        from adore.aegis import AEGIS_STDOUT_FILE, MAX_JSON_BYTES

        backend.verify_identity(self.name, self.resource)
        argv = list(argv)
        if not argv or any(not isinstance(v, str) or "\x00" in v for v in argv):
            raise LocalExecutionError("invalid native argv")
        for path in (stdout, stderr):
            if path.is_symlink() or not path.resolve().is_relative_to(Path(self.paths.io)):
                raise LocalExecutionError("native output must stay in the owned exchange directory")
        argv[0] = backend.resolver(argv[0], self.env, backend.context["system"])
        secrets = self._secrets()
        result = backend.controller.run_files(
            argv,
            cwd=Path(self.paths.worktree),
            env=self.env,
            timeout=30 if timeout is None else timeout,
            stdout=stdout,
            stderr=stderr,
            control=backend._control(self.resource),
            run_id=self.resource["id"],
            host=self.resource["host"],
            secrets=secrets,
            stdout_limit=MAX_JSON_BYTES if stdout.name == AEGIS_STDOUT_FILE else self.output_limit,
        )
        self.read_output(stdout)
        self.read_output(stderr)
        return result

    def __call__(self, argv, *, timeout=None) -> CommandResult:
        """@brief Run one backend command with its same controlled native environment."""
        directory = Path(self.paths.io) / ("native-command-" + uuid4().hex)
        directory.mkdir()
        stdout, stderr = directory / "stdout.txt", directory / "stderr.txt"
        result = self.run_files(argv, stdout, stderr, timeout=timeout)
        result.stdout = self.read_output(stdout)
        result.stderr = self.read_output(stderr)
        return result


@contextmanager
def local_probe(config, env_file: Path | None = None):
    """@brief Yield the same owned native target/environment for explicit bounded probes.
    @param[in] config Selected local configuration.
    @param[in] env_file Approved provider values, reused only in memory.
    @return Context yielding backend, target, worktree and exchange directory.
    @exception LocalExecutionError Unconfirmed cleanup preserves the temporary workspace.
    """
    from adore.util import load_env_file

    root = Path(tempfile.mkdtemp(prefix="adore-local-probe-"))
    selected = deepcopy(config)
    selected.state.store_root = str(root / "state")
    work, exchange = root / "work", root / "state/runs/probe/io"
    work.mkdir()
    backend = None
    resource = None
    try:
        backend = LocalBackend(selected)
        saved = {**(load_env_file(env_file) if env_file else {}), **os.environ}
        env = local_environment(selected, backend.context, saved)
        backend.provision("probe", work, work, exchange, env)
        resource = backend.resource_identity("probe")
        yield backend, backend.bind("probe", env, resource), work, exchange
    finally:
        if backend is not None and resource is not None:
            backend.remove("probe", expected=resource)
        shutil.rmtree(root)


def validate_local_probe(value: object, ready: bool) -> dict:
    """@brief Refuse corrupt or contradictory optional prerequisite evidence.
    @param[in] value Untrusted persisted diagnostic object.
    @param[in] ready Authoritative executor_cli check.
    @return Closed diagnostic with no external text.
    @exception ValueError Unknown keys, types, reasons or inconsistent status.
    """
    if (not isinstance(value, dict) or set(value) != {"ready", "reason", "exit_code"}
            or type(value["ready"]) is not bool or value["ready"] is not ready
            or not isinstance(value["reason"], str) or value["reason"] not in LOCAL_PROBE_REASONS
            or value["ready"] != (value["reason"] == "ready")
            or value["exit_code"] is not None and (
                type(value["exit_code"]) is not int or not -2147483648 <= value["exit_code"]
                <= 4294967295)
            or value["reason"] in {"ready", "version-invalid", "credential-missing"}
            and value["exit_code"] != 0
            or value["reason"] == "executor-exit" and value["exit_code"] in {None, 0}):
        raise ValueError("invalid local prerequisite evidence")
    return value


def local_probe_failure(error: Exception, fallback: str = "runtime-error") -> str:
    """@brief Classify known native failures without exposing arbitrary exception text.
    @param[in] error Native boundary failure.
    @param[in] fallback Current failed phase, used for unclassified failures.
    @return Closed cause; raw provider/OS/credential strings never escape.
    """
    if isinstance(error, PermissionError):
        return "permission-denied"
    if isinstance(error, LocalPrerequisiteError):
        return error.reason
    text = str(error)
    causes = {
        "selected local executable is unavailable": "executable-missing",
        "local Windows requires an executable or explicit node entrypoint": "executable-missing",
        "local shell and Windows-to-WSL wrappers are unsupported": "executable-missing",
        "selected local executable is not executable": "permission-denied",
        "local executor auth store is corrupt or unsafe": "credential-invalid",
        "local account differs from the ADORE process account": "account-mismatch",
        "selected local account home is unavailable": "account-mismatch",
    }
    if text in causes:
        return causes[text]
    if "cleanup" in text or "drain" in text or "recovery" in text:
        return "cleanup-failed"
    cause = error.__cause__
    for _ in range(8):
        if cause is None:
            break
        if isinstance(cause, PermissionError):
            return "permission-denied"
        cause = cause.__cause__
    if text == "native launch ownership failed":
        return "scope-error"
    return fallback


def probe_local_executor(config, env_file: Path | None = None) -> dict:
    """@brief Measure installed executor/version/auth and preserve a safe failed phase.
    @param[in] config Validated current-account configuration.
    @param[in] env_file Selected approved provider values.
    @return Closed ready/reason/exit_code evidence after verified cleanup.
    """
    value = {"ready": False, "reason": "scope-error", "exit_code": None}
    phase = "scope-error"
    try:
        with local_probe(config, env_file) as (backend, target, _, _):
            phase = "runtime-error"
            backend.verify_required_tools("probe", [], env=target.env)
            value["exit_code"] = 0
            phase = "credential-invalid"
            ready = target.auth_available()
            value.update(ready=ready, reason="ready" if ready else "credential-missing")
            phase = "cleanup-failed"
    except (IsolationError, OSError, ValueError) as exc:
        value.update(ready=False, reason=local_probe_failure(exc, phase))
        if isinstance(exc, LocalPrerequisiteError):
            value["exit_code"] = exc.exit_code
    return validate_local_probe(value, value["ready"])


# END OF FILE
