#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file cli.py
@brief Command-line interface over the ADORE runtime package.
@details Defines the `adore` command surface (lifecycle, operations, statistics,
         config) using only the standard library (argparse). `config set`
         edits one scalar key in the resolved config file, preserving comments,
         and refuses to write unless the resulting config still validates.
         Destructive commands (delete, reset) require --force per design 8c.
         `adore init` runs the assisted-config wizard to create a
         runtime-project profile; `adore profile ...` manages profiles (with
         run statistics).
"""

from __future__ import annotations

# IMPORTS
import argparse
from collections.abc import Iterator
import contextlib
from dataclasses import asdict
import json
from pathlib import Path
import re
import tomllib

from adore import __version__, metrics
from adore.branding import PACKAGE_NAME, PRODUCT_NAME
from adore.config import Config, load_config, validate_config
from adore.config_edit import ConfigEditLockedError, config_edit_lock
from adore.orchestrator import LockHeldError, Orchestrator
from adore.preparation import PreparationError, preview_plan, public_plan
from adore.process_log import ProcessLogger, process_log_path
from adore.profiles import ProfileError, ProfileStore, resolve_config_path
from adore.state import StateError, StateStore
from adore.util import parse_duration, run_command
from adore.wizard import ConsoleAsker, ScriptedAsker, WizardError, run_wizard

# CONSTANTS

EXIT_OK = 0
EXIT_ERROR = 1

# config-key path components that would carry a secret VALUE; config.toml only
# ever holds the NAMES of secrets ([executor] env_keys), so `config set` on one
# of these is refused and the operator is pointed at .env.
_SECRET_KEY_RE = re.compile(
    r"(?:^|[._-])(?:token|secret|password|passwd|api[_-]?key|apikey|credential"
    r"|private[_-]?key)s?(?:$|[._-])",
    re.IGNORECASE,
)
# ADORE's own settings whose names look like credentials but hold no secret.
_NOT_SECRET_KEYS = frozenset({"metrics.capture_tokens"})


def _is_secret_key(dotted_key: str) -> bool:
    """@brief Whether a dotted config key names a secret (see _SECRET_KEY_RE)."""
    return dotted_key not in _NOT_SECRET_KEYS and bool(_SECRET_KEY_RE.search(dotted_key))


# HELPER FUNCTIONS


def _build_parser() -> argparse.ArgumentParser:
    """
    @brief   Build the top-level argument parser and subcommands.
    @return  Configured argparse.ArgumentParser.
    """
    parser = argparse.ArgumentParser(prog=PACKAGE_NAME, description=PRODUCT_NAME)
    parser.add_argument(
        "--version", action="version", version=f"{PACKAGE_NAME} {__version__}"
    )
    parser.add_argument("-c", "--config", default=None,
                        help="Path to config.toml (overrides --profile / active profile)")
    parser.add_argument("--profile", metavar="NAME",
                        help="Use a runtime-project profile's config")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the poller")
    run.add_argument("--loop", action="store_true", help="Long-running loop")
    run.add_argument("--once", action="store_true", help="Single poll pass")
    run.add_argument("--dry-run", action="store_true", help="Show actions without side effects")
    run.add_argument("--ticket", type=int, metavar="IID",
                     help="Run one eligible ticket (with --once); readiness still applies")

    sub.add_parser("status", help="Show overall state")
    sub.add_parser("runs", help="List schema-1 working/parked/approval/review runs")
    sub.add_parser("pause", help="Stop picking new tickets")
    sub.add_parser("resume", help="Allow picking new tickets")
    sub.add_parser("cleanup", help="Remove this project's finished and orphaned run resources")

    for name in ("retry", "cancel", "logs", "handoff"):
        p = sub.add_parser(name, help=f"{name} a run")
        p.add_argument("run_id")
        if name == "retry":
            p.add_argument(
                "--reprepare",
                action="store_true",
                help=("Acknowledge full recipe replay in a fresh owned container "
                      "with retained worktree"),
            )

    delete = sub.add_parser("delete", help="Hard-remove a run including state")
    delete.add_argument("run_id")
    delete.add_argument("--force", action="store_true")

    reset = sub.add_parser("reset", help="Force a run back to a stage")
    reset.add_argument("run_id")
    reset.add_argument("--to", required=True,
                       help="Target stage (an AEGIS stage or 'publishing')")
    reset.add_argument("--force", action="store_true",
                       help="Required: resetting re-runs work (cost, churn)")

    stats = sub.add_parser("stats", help="Show statistics")
    stats.add_argument("--since", help='Window, e.g. "30d" or "12h"')
    stats.add_argument("--by", choices=["priority", "outcome"])
    stats.add_argument("--html", action="store_true",
                       help="Write the static HTML dashboard")
    stats.add_argument("--rebuild", action="store_true",
                       help="Re-summarize all terminal runs into the database")

    report = sub.add_parser("report", help="Show a run report")
    report.add_argument("run_id")

    export = sub.add_parser("export", help="Export metrics")
    export.add_argument("--csv", action="store_true")

    cfg = sub.add_parser("config", help="Config helpers")
    cfg.add_argument("action", choices=["show", "validate", "plan", "set"])
    cfg.add_argument("key", nargs="?")
    cfg.add_argument("value", nargs="?")

    init = sub.add_parser("init", help="Assisted setup: create a runtime-project profile")
    init.add_argument("name", nargs="?", help="Profile name (asked if omitted)")
    init.add_argument("--force", action="store_true", help="Overwrite an existing profile")
    init.add_argument("--answers", metavar="FILE",
                      help="TOML file of answers for non-interactive setup (field key = value)")

    prof = sub.add_parser("profile", help="Manage runtime-project profiles")
    prof_sub = prof.add_subparsers(dest="profile_action", required=True)
    prof_sub.add_parser("list", help="List profiles")
    for action in ("show", "use"):
        p = prof_sub.add_parser(action, help=f"{action} a profile")
        p.add_argument("name")
    p_rename = prof_sub.add_parser("rename", help="Rename a profile")
    p_rename.add_argument("old")
    p_rename.add_argument("new")
    p_delete = prof_sub.add_parser("delete", help="Delete a profile and its state")
    p_delete.add_argument("name")
    p_delete.add_argument("--force", action="store_true")
    p_delete.add_argument("--remove-resources", action="store_true",
                          help="Also remove the project's containers and worktrees, "
                               "keeping human-owned ones")
    p_path = prof_sub.add_parser("path", help="Print a profile's config.toml path")
    p_path.add_argument("name", nargs="?", help="Defaults to the active profile")

    return parser


def _load(args: argparse.Namespace) -> Config | None:
    """
    @brief      Resolve and load the config (explicit -c > --profile > active
                profile > ./config.toml) and load it.
    @details    Sets args.config to the resolved path so handlers display it,
                and records a use on the resolved profile (use_count /
                last_used_at). Resolution and load errors print a readable hint.
    @param[in]  args Parsed arguments (args.config, args.profile).
    @return     The Config, or None after printing a readable error.
    """
    store = ProfileStore()
    try:
        path, profile = resolve_config_path(
            getattr(args, "config", None), getattr(args, "profile", None), store=store
        )
    except ProfileError as exc:
        print(f"error: {exc}")
        print("hint: list profiles with `adore profile list`")
        return None
    args.config = str(path)
    try:
        config = load_config(path)
    except FileNotFoundError:
        print(f"error: config file not found: {path}")
        if profile:
            print(f"hint: profile {profile!r} has no config.toml; "
                  f"re-create it with `adore init {profile} --force`")
        else:
            print("hint: copy config.example.toml to config.toml, or create a "
                  "profile with `adore init <name>`")
        return None
    except tomllib.TOMLDecodeError as exc:
        print(f"error: {path} is not valid TOML: {exc}")
        return None
    if profile:
        with contextlib.suppress(ProfileError):
            store.touch(profile)
    return config


def _store(config: Config) -> StateStore:
    """
    @brief      Build the state store from config.
    @param[in]  config Loaded configuration.
    @return     The StateStore for this deployment.
    """
    return StateStore(config.state.store_root, config.agent.slug)


def _env_file_for_config(config_path: str | Path) -> Path:
    """
    @brief      Resolve the secret file used for an engine command.
    @details    Prefer `.env` beside the resolved config/profile. If it is not
                present, use cwd `.env`; `Orchestrator.from_config` still gives
                the process environment final precedence.
    @param[in]  config_path Resolved config path selected by `_load`.
    @return     Preferred existing path, or the cwd fallback path.
    """
    beside_config = Path(config_path).expanduser().resolve().parent / ".env"
    cwd_fallback = Path.cwd() / ".env"
    return beside_config if beside_config.is_file() else cwd_fallback


_DELETABLE_RUN_LIFECYCLES = {"done", "failed", "cancelled", "handed-off", "handoff-pending"}


@contextlib.contextmanager
def _operator_lock(store: StateStore) -> Iterator[None]:
    """
    @brief      Hold the single-conductor lock around an operator mutation.
    @param[in]  store State store whose lock protects the selected profile.
    @exception  LockHeldError When a live or unknown holder owns the lock.
    """
    if not store.acquire_lock():
        info = store.lock_info()
        pid = info.get("pid") if info else None
        holder = f"pid {pid}" if isinstance(pid, int) else "an unknown holder"
        raise LockHeldError(
            f"the poller or another operator holds the lock ({holder}); "
            "stop it or wait for it to finish before mutating run state"
        )
    try:
        yield
    finally:
        store.release_lock()


# COMMAND HANDLERS


def _toml_scalar_literal(value: str) -> str:
    """
    @brief      Render a CLI value string as a TOML scalar literal.
    @details    Inference order: `true`/`false` -> bool; an integer -> int; a
                number with a decimal point or exponent -> float; anything else
                -> a quoted basic string (so version-like `1.2.3` stays a
                string). Callers document that the type is inferred from the
                value text.
    @param[in]  value Raw value from the command line.
    @return     A TOML literal safe to splice into the config text.
    """
    text = value.strip()
    if text in ("true", "false"):
        return text
    if re.fullmatch(r"[+-]?\d+", text):
        return str(int(text))
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?", text) and (
        "." in text or "e" in text.lower()
    ):
        return repr(float(text))
    escaped = (
        value.replace("\\", "\\\\").replace('"', '\\"')
        .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    )
    return f'"{escaped}"'


def _inline_comment(line: str) -> str:
    """
    @brief      Return a line's trailing `# ...` comment, or "" if none.
    @details    Quote-aware so a `#` inside a string value is not mistaken for a
                comment. Basic heuristic (enough for scalar config lines); it
                never splits inside single- or double-quoted text.
    @param[in]  line A config line.
    @return     The comment substring starting at `#`, or "".
    """
    quote = ""
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = ""
        elif char in ('"', "'"):
            quote = char
        elif char == "#":
            return line[index:]
    return ""


def _newline(text: str) -> str:
    """@brief A config text's line ending: CR LF when it has one, else LF."""
    return "\r\n" if "\r\n" in text else "\n"


def _set_toml_scalar(text: str, dotted_key: str, value: str) -> str:
    """
    @brief      Set one scalar key in TOML text, preserving comments/other lines.
    @details    `dotted_key` is `<table...>.<name>` (for example
                `budgets.max_iterations` or `labels.lifecycle.ready`). An
                existing key's value is replaced in place (its indentation
                kept); a key absent from an existing table is inserted just
                after the table header; an absent table is appended at the end.
                Everything else - comments, blank lines, other keys - is left
                untouched, byte for byte. A replaced line keeps its own line
                ending and an added line takes the text's (see _newline). Only
                scalars are supported.
    @param[in]  text Current config file text.
    @param[in]  dotted_key Dotted table+key path.
    @param[in]  value Raw value (type inferred by _toml_scalar_literal).
    @return     The updated config text.
    @exception  ValueError When the key is not a `<table>.<name>` path.
    """
    parts = [part for part in dotted_key.split(".") if part]
    if len(parts) < 2:
        raise ValueError(
            f"key must be <section...>.<name> (e.g. budgets.max_iterations): "
            f"{dotted_key!r}"
        )
    *table_parts, key = parts
    header = "[" + ".".join(table_parts) + "]"
    new_line = f"{key} = {_toml_scalar_literal(value)}"
    newline = _newline(text)
    # Split on LF only: each line keeps its own CR, so joining with LF gives
    # every untouched line back byte for byte.
    lines = text.split("\n")

    header_idx = next(
        (i for i, line in enumerate(lines) if line.strip() == header), None
    )
    if header_idx is None:
        prefix = "" if text == "" or text.endswith("\n") else newline
        return f"{text}{prefix}{newline}{header}{newline}{new_line}{newline}"

    block_end = len(lines)
    for j in range(header_idx + 1, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            block_end = j
            break
    key_re = re.compile(rf"^(\s*){re.escape(key)}\s*=")
    for k in range(header_idx + 1, block_end):
        body = lines[k].removesuffix("\r")
        match = key_re.match(body)
        if match:
            comment = _inline_comment(body)
            suffix = f"  {comment}" if comment else ""
            lines[k] = f"{match.group(1)}{new_line}{suffix}{lines[k][len(body):]}"
            return "\n".join(lines)
    if header_idx == len(lines) - 1:  # unterminated header: the new line ends the file
        lines[header_idx] += newline.removesuffix("\n")
        lines.append(new_line)
    else:
        lines.insert(header_idx + 1, new_line + newline.removesuffix("\n"))
    return "\n".join(lines)


def _config_set(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore config set <section.key> <value>`.
    @details    Resolves the config file with the same precedence as every other
                command (explicit -c > --profile > active profile > ./config.toml),
                refuses secret-looking keys (they belong in .env), edits one
                scalar preserving comments, then writes ONLY when the whole
                resulting config still loads and validates. The write is atomic.
    @param[in]  args Parsed arguments (key, value, config, profile).
    @return     Process exit code.
    """
    if not args.key or args.value is None:
        print("usage: adore config set <section.key> <value>")
        return EXIT_ERROR
    if _is_secret_key(args.key):
        print("error: secrets never go in config.toml; put the value in .env and "
              "reference its NAME via [executor] env_keys")
        return EXIT_ERROR
    try:
        path, _profile = resolve_config_path(
            getattr(args, "config", None), getattr(args, "profile", None),
            store=ProfileStore(),
        )
    except ProfileError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR
    try:
        with config_edit_lock(path):
            return _config_set_locked(args, path)
    except ConfigEditLockedError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR


def _config_set_locked(args: argparse.Namespace, path: Path) -> int:
    """@brief Validate and atomically write one scalar under the edit lock."""
    args.config = str(path)
    try:
        original = path.read_bytes().decode("utf-8")  # bytes: keep line endings
    except FileNotFoundError:
        print(f"error: config file not found: {path}")
        return EXIT_ERROR
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}")
        return EXIT_ERROR
    try:
        updated = _set_toml_scalar(original, args.key, args.value)
    except ValueError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR
    # Validate by loading the candidate from a temp file first; only replace the
    # real config when it still parses AND validates. tmp + replace is atomic.
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(updated.encode("utf-8"))
    except OSError as exc:
        print(f"error: cannot write {tmp}: {exc}")
        return EXIT_ERROR
    try:
        try:
            candidate = load_config(tmp)
            issues = validate_config(candidate)
        except tomllib.TOMLDecodeError as exc:
            print(f"error: the edit produced invalid TOML: {exc}")
            return EXIT_ERROR
        except Exception as exc:  # noqa: BLE001 - any load failure => reject
            print(f"error: the edit produced an unusable config: {exc}")
            return EXIT_ERROR
        if issues:
            print(f"refusing to write {args.key}: {len(issues)} config issue(s):")
            for issue in issues:
                print(f"  - {issue}")
            return EXIT_ERROR
        if candidate.execution.preparation or candidate.execution.backend == "local":
            try:
                preview_plan(candidate, runner=run_command)
            except PreparationError as exc:
                print(f"refusing execution selection: {exc}")
                return EXIT_ERROR
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"{path}: set {args.key} = {args.value.strip()}")
    return EXIT_OK


def _cmd_config(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore config show|validate|set`.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    if args.action == "set":
        return _config_set(args)
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    if args.action == "show":
        print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
        return EXIT_OK
    issues = validate_config(config)
    if issues:
        print(f"{args.config}: {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue}")
        return EXIT_ERROR
    if args.action == "plan" or config.execution.preparation:
        try:
            plan = preview_plan(config, runner=run_command)
        except PreparationError as exc:
            print(f"error: {exc}")
            return EXIT_ERROR
        if args.action == "plan":
            print(json.dumps(public_plan(plan), indent=2, ensure_ascii=False))
            return EXIT_OK
    print(f"{args.config}: OK")
    return EXIT_OK


def _cmd_status(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore status`: config health, lock, pause, run counts.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    issues = validate_config(config)
    store = _store(config)
    runs = store.list_runs()
    invalid = store.invalid_runs()
    by_lifecycle: dict[str, int] = {}
    for run in runs:
        by_lifecycle[run.lifecycle] = by_lifecycle.get(run.lifecycle, 0) + 1
    lock = store.lock_info()

    print(f"{config.agent.name} status")
    print(f"  config : {args.config} ({'OK' if not issues else f'{len(issues)} issue(s)'})")
    print(f"  store  : {store.root}")
    print(f"  paused : {'yes' if store.is_paused() else 'no'}")
    print(f"  lock   : {'held (pid ' + str(lock.get('pid', '?')) + ')' if lock else 'free'}")
    breakdown = ", ".join(f"{count} {name}" for name, count in sorted(by_lifecycle.items()))
    print(f"  runs   : {len(runs)} total" + (f" ({breakdown})" if breakdown else ""))
    if invalid:
        print(f"  CORRUPT: {len(invalid)} run(s) with unreadable state: {', '.join(invalid)}")
        print("           these runs are skipped; inspect or remove them manually")
    return EXIT_OK


def _cmd_runs(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore runs`: list persisted runs as a table.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    store = _store(config)
    runs = store.list_runs()
    invalid = store.invalid_runs()
    if not runs and not invalid:
        print("no runs")
        return EXIT_OK
    if runs:
        header = f"{'RUN-ID':<40} {'TICKET':>6} {'STAGE':<14} {'LIFECYCLE':<10} UPDATED"
        print(header)
        for run in runs:
            print(
                f"{run.run_id:<40} {run.ticket_iid:>6} {run.stage:<14} "
                f"{run.lifecycle:<10} {run.updated_at}"
            )
    for run_id in invalid:
        print(f"{run_id:<40} {'?':>6} {'?':<14} {'CORRUPT':<10} state.json unreadable")
    return EXIT_OK


def _cmd_pause(args: argparse.Namespace, *, paused: bool) -> int:
    """
    @brief      Handle `adore pause` / `adore resume`.
    @param[in]  args Parsed arguments.
    @param[in]  paused True to pause, False to resume.
    @return     Process exit code.
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    store = _store(config)
    if paused:
        store.pause()
        print("paused: no new tickets will be picked (in-flight runs continue)")
    else:
        store.resume()
        print("resumed: ticket pickup is allowed again")
    return EXIT_OK


def _engine(args: argparse.Namespace) -> tuple[Config, Orchestrator] | None:
    """
    @brief      Load + validate config, then build the engine.
    @details    Engine commands refuse to start on an invalid config -
                `validate at startup` is the design contract (12a).
    @param[in]  args Parsed arguments.
    @return     (config, orchestrator), or None after a printed error.
    """
    config = _load(args)
    if config is None:
        return None
    issues = validate_config(config)
    if issues:
        print(f"error: {args.config} has {len(issues)} issue(s); "
              "run `adore config validate`")
        return None
    return config, Orchestrator.from_config(
        config,
        env_file=_env_file_for_config(args.config),
    )


def _cmd_run(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore run [--loop|--once|--dry-run]`.
    @details    Default mode comes from [polling] mode; flags override.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    profile_store = ProfileStore()
    try:
        _path, profile_name = resolve_config_path(
            getattr(args, "config", None), getattr(args, "profile", None),
            store=profile_store,
        )
        if profile_name and profile_store.load(profile_name).archived:
            print(f"error: profile {profile_name!r} is archived; restore it before pickup")
            return EXIT_ERROR
    except ProfileError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR
    built = _engine(args)
    if built is None:
        return EXIT_ERROR
    config, engine = built
    if args.ticket is not None and (args.ticket < 1 or not args.once or args.loop):
        print("error: --ticket requires a positive IID and --once")
        return EXIT_ERROR
    logger = ProcessLogger(process_log_path(config.state.store_root))
    engine.log = logger.emit
    poll_options = {"ticket_iid": args.ticket} if args.ticket is not None else {}
    if args.dry_run:
        summary = engine.poll_once(dry_run=True, **poll_options)
        logger.emit(json.dumps(summary))
        return EXIT_OK
    loop = args.loop or (config.polling.mode == "loop" and not args.once)
    if loop:
        return engine.run_loop()
    try:
        summary = engine.poll_once(**poll_options)
    except LockHeldError as exc:
        store = _store(config)
        logger.emit(f"error: {exc} ({store.lock_path})")
        logger.emit("hint: stop or wait for a live holder; `adore cleanup` reclaims "
                    "only a provably stale local lock")
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - one pass must not traceback
        # `run --loop` survives an unexpected fault and keeps polling, so a
        # single pass must not be noisier than the daemon for the same cause:
        # `--once` is what cron and Task Scheduler call, where a traceback is
        # just a nonzero exit with an ugly log. The run itself is already
        # failed and journaled by the engine.
        logger.emit(f"error: {exc}")
        return EXIT_ERROR
    logger.emit(json.dumps(summary))
    return EXIT_ERROR if args.ticket is not None and summary["picked"] is None else EXIT_OK


def _cmd_run_op(args: argparse.Namespace) -> int:
    """
    @brief      Handle per-run operations: cancel, retry, logs, delete.
    @param[in]  args Parsed arguments (args.run_id set).
    @return     Process exit code.
    """
    built = _engine(args)
    if built is None:
        return EXIT_ERROR
    config, engine = built
    store = _store(config)
    if args.command == "handoff":
        try:
            store.request_handoff(args.run_id)
            with _operator_lock(store):
                ok = engine.handoff(args.run_id)
                print("handed off; inspect remote checkpoint and local evidence"
                      if ok else "handoff pending; ownership has not transferred")
                return EXIT_OK if ok else EXIT_ERROR
        except LockHeldError:
            print("handoff queued; current bounded session must finish before human editing")
            return EXIT_OK
        except (StateError, OSError) as exc:
            print(f"error: cannot request handoff: {exc}")
            return EXIT_ERROR
    if args.command == "logs":
        events = store.read_journal(args.run_id)
        if not events:
            print(f"no journal for run {args.run_id}")
            return EXIT_ERROR
        for event in events:
            details = {k: v for k, v in event.items() if k not in ("ts", "event")}
            suffix = f" {json.dumps(details, ensure_ascii=False)}" if details else ""
            print(f"{event.get('ts', '?')} {event.get('event', '?')}{suffix}")
        return EXIT_OK
    # delete: destructive - confirm via --force (design 8c guardrail)
    if args.command == "delete":
        if not store.exists(args.run_id):
            print(f"no such run: {args.run_id}")
            return EXIT_ERROR
        if not args.force:
            print("delete removes ALL run state irrecoverably; re-run with --force")
            return EXIT_ERROR
    try:
        with _operator_lock(store):
            if args.command == "cancel":
                ok = engine.cancel(args.run_id)
                print("cancelled" if ok else f"no such run: {args.run_id}")
                return EXIT_OK if ok else EXIT_ERROR
            if args.command == "retry":
                ok = (engine.retry(args.run_id, reprepare=True) if args.reprepare
                      else engine.retry(args.run_id))
                print("retried" if ok else f"cannot retry: {args.run_id}")
                return EXIT_OK if ok else EXIT_ERROR
            engine.cancel(args.run_id, outcome="deleted")
            store.delete_run(args.run_id)
            print(f"deleted {args.run_id}")
            return EXIT_OK
    except LockHeldError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR


def _cmd_stats(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore stats [--since] [--by] [--html] [--rebuild]`.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    store = _store(config)
    if args.rebuild:
        try:
            rebuilt = [metrics.summarize_run(store, run.run_id)
                       for run in store.list_runs()
                       if metrics.is_terminal(run.lifecycle)]
        except metrics.MetricsError as exc:
            print(f"error: metrics evidence corrupt: {exc}")
            return EXIT_ERROR
        for summary in rebuilt:
            metrics.record_summary(config.metrics.db_path, summary,
                                   config.metrics.export_jsonl)
        print(f"rebuilt {len(rebuilt)} run summarie(s)")
    since = None
    if args.since:
        try:
            since = parse_duration(args.since)
        except ValueError:
            print(f'error: invalid --since window: {args.since!r} (use e.g. "30d")')
            return EXIT_ERROR
    summaries = metrics.load_summaries(config.metrics.db_path, since)
    if args.html:
        path = metrics.render_html(summaries, config.metrics.html_out)
        print(f"wrote {path} ({len(summaries)} run(s))")
        return EXIT_OK
    if not summaries:
        print("no recorded runs (try `adore stats --rebuild`)")
        return EXIT_OK
    groups = metrics.aggregate(summaries, args.by or "")
    header = (f"{'GROUP':<14} {'RUNS':>4} {'MERGED':>6} {'FAILED':>6} "
              f"{'AVG-SPAN':>9} {'LAUNCHES':>8} {'TOK-IN':>9} {'TOK-OUT':>8} "
              f"{'COST':>8}")
    print(header)
    for name, row in groups.items():
        print(f"{name:<14} {row['runs']:>4} {row['merged']:>6} "
              f"{row['failed']:>6} {row['avg_span_s']:>8}s {row['launches']:>8} "
              f"{row['tokens_in']:>9} {row['tokens_out']:>8} "
              f"{row['cost_usd']:>8}")
    return EXIT_OK


def _cmd_report(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore report <run-id>`: live summary from the journal.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    store = _store(config)
    if not store.exists(args.run_id):
        print(f"no such run: {args.run_id}")
        return EXIT_ERROR
    try:
        summary = metrics.summarize_run(store, args.run_id)
    except metrics.MetricsError as exc:
        print(f"error: metrics evidence corrupt: {exc}")
        return EXIT_ERROR
    print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
    return EXIT_OK


def _cmd_export(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore export --csv`: CSV of all summaries to stdout.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    config = _load(args)
    if config is None:
        return EXIT_ERROR
    summaries = metrics.load_summaries(config.metrics.db_path)
    print(metrics.export_csv(summaries), end="")
    return EXIT_OK


def _cmd_init(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore init [name] [--force] [--answers FILE]`.
    @details    Runs the assisted-config wizard (interactive by default, or
                non-interactive from a TOML answers file) and saves a validated
                runtime-project profile under the ADORE config home.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    store = ProfileStore()
    if args.answers:
        try:
            with open(args.answers, "rb") as handle:
                answers = tomllib.load(handle)
        except FileNotFoundError:
            print(f"error: --answers file not found: {args.answers}")
            return EXIT_ERROR
        except tomllib.TOMLDecodeError as exc:
            print(f"error: --answers file is not valid TOML: {exc}")
            return EXIT_ERROR
        asker: ConsoleAsker | ScriptedAsker = ScriptedAsker(answers, interactive=False)
    else:
        asker = ConsoleAsker()
    try:
        run_wizard(store, asker=asker, name=args.name, force=args.force)
    except WizardError as exc:
        print(f"init failed: {exc}")
        return EXIT_ERROR
    return EXIT_OK


def _cmd_profile(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore profile list|show|use|rename|delete|path`.
    @param[in]  args Parsed arguments (args.profile_action + operands).
    @return     Process exit code.
    """
    store = ProfileStore()
    action = args.profile_action
    if action == "list":
        return _profile_list(store)
    if action == "show":
        return _profile_show(store, args.name)
    if action == "use":
        try:
            store.set_active(args.name)
        except ProfileError as exc:
            print(f"error: {exc}")
            return EXIT_ERROR
        print(f"active profile: {args.name}")
        return EXIT_OK
    if action == "rename":
        try:
            store.rename(args.old, args.new)
        except ProfileError as exc:
            print(f"error: {exc}")
            return EXIT_ERROR
        print(f"renamed {args.old} -> {args.new}")
        return EXIT_OK
    if action == "delete":
        if not store.exists(args.name):
            print(f"no such profile: {args.name}")
            return EXIT_ERROR
        if not args.force:
            print("delete removes the profile and its state irrecoverably; "
                  "re-run with --force")
            return EXIT_ERROR
        if getattr(args, "remove_resources", False):
            return _delete_profile_with_resources(store, args)
        store.delete(args.name)
        print(f"deleted profile {args.name}")
        return EXIT_OK
    # path
    name = args.name or store.get_active()
    if not name:
        print("no profile given and no active profile (`adore profile use <name>`)")
        return EXIT_ERROR
    if not store.exists(name):
        print(f"no such profile: {name}")
        return EXIT_ERROR
    print(store.config_path(name))
    return EXIT_OK


def _delete_profile_with_resources(store: ProfileStore, args: argparse.Namespace) -> int:
    """
    @brief      Remove a project's ADORE resources, then delete its profile.
    @details    Human-owned worktrees/containers and a state folder outside the
                profile directory are kept and reported. Nothing is deleted when
                the configuration is invalid, the conductor lock is held, run
                state is corrupt or any run is unfinished.
    @param[in]  store Profile store holding the profile.
    @param[in]  args Parsed `profile delete` arguments.
    @return     Process exit code.
    """
    engine_args = argparse.Namespace(**{**vars(args), "config": None, "profile": args.name})
    built = _engine(engine_args)
    if built is None:
        return EXIT_ERROR
    _config, engine = built
    try:
        with _operator_lock(engine.store):
            if engine.store.invalid_runs():
                print("error: corrupt run state; inspect it before deleting the project")
                return EXIT_ERROR
            unfinished = [run.run_id for run in engine.store.list_runs()
                          if run.lifecycle not in _DELETABLE_RUN_LIFECYCLES]
            if unfinished:
                print(f"error: unfinished runs block deletion: {', '.join(sorted(unfinished))}")
                return EXIT_ERROR
            report = engine.purge_resources()
    except LockHeldError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR
    profile_dir = store.profile_dir(args.name).resolve()
    state_root = Path(engine.store.root).resolve()
    retained = None if state_root.is_relative_to(profile_dir) else str(state_root)
    try:
        store.delete(args.name)
    except OSError as exc:
        print(json.dumps({"deleted": None, **report, "state_retained": retained,
                          "error": f"profile removal failed: {exc}"},
                         indent=2, ensure_ascii=False))
        return EXIT_ERROR
    print(json.dumps({"deleted": args.name, **report, "state_retained": retained},
                     indent=2, ensure_ascii=False))
    return EXIT_OK


def _profile_metrics(profile) -> dict:
    """
    @brief      One profile's run statistics from its metrics DB.
    @details    Honors a custom `[metrics] db_path`; falls back to
                `<store_root>/metrics.db`. A missing DB or an unreadable config
                yields zero-stats (never an error) so `list`/`show` stay robust.
    @param[in]  profile The Profile.
    @return     The stats mapping from `metrics.profile_stats`.
    """
    db_path = ""
    try:
        db_path = load_config(profile.config_path).metrics.db_path
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError, ValueError):
        db_path = ""
    if not db_path and profile.store_root:
        db_path = str(Path(profile.store_root) / "metrics.db")
    return metrics.profile_stats(db_path)


def _profile_list(store: ProfileStore) -> int:
    """
    @brief      Handle `adore profile list`: a table of profiles + run stats.
    @param[in]  store The profile store.
    @return     Process exit code.
    """
    profiles = store.list_profiles()
    invalid = store.invalid_profiles()
    if not profiles and not invalid:
        print("no profiles (create one with `adore init <name>`)")
        return EXIT_OK
    active = store.get_active()
    header = (f"{'':1} {'NAME':<18} {'PLATFORM':<8} {'REPO':<28} {'RUNTIME':<20} "
              f"{'RUNS':>4} {'MERGED':>6} {'LAST-USED':<10} USES")
    print(header)
    for profile in profiles:
        mark = "*" if profile.name == active else " "
        stats = _profile_metrics(profile)
        print(f"{mark} {profile.name:<18} {profile.platform:<8} {profile.repo[:28]:<28} "
              f"{profile.runtime[:20]:<20} {stats['runs']:>4} {stats['merged']:>6} "
              f"{(profile.last_used_at[:10] or '-'):<10} {profile.use_count}")
    for name in invalid:
        print(f"  {name:<18} {'?':<8} {'CORRUPT profile.json':<28}")
    return EXIT_OK


def _profile_show(store: ProfileStore, name: str) -> int:
    """
    @brief      Handle `adore profile show <name>`: metadata + config path.
    @param[in]  store The profile store.
    @param[in]  name Profile name.
    @return     Process exit code.
    """
    try:
        profile = store.load(name)
    except ProfileError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR
    active = store.get_active()
    print(json.dumps(asdict(profile), indent=2, ensure_ascii=False))
    print(f"active : {'yes' if active == name else 'no'}")
    print(f"config : {store.config_path(name)}")
    stats = _profile_metrics(profile)
    print("stats  :")
    print(f"  runs={stats['runs']} merged={stats['merged']} failed={stats['failed']} "
          f"success_rate={stats['success_rate']}% launches={stats['launches']}")
    print(f"  tokens_in={stats['tokens_in']} tokens_out={stats['tokens_out']} "
          f"cost_usd={stats['cost_usd']} avg_span_s={stats['avg_span_s']}")
    print(f"  last_run={stats['last_run'] or '-'}")
    return EXIT_OK


def _cmd_reset(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore reset <run-id> --to <stage> --force`.
    @details    Destructive (re-runs completed work), so it requires --force
                per the design 8c guardrail. The run is left retry-able. It
                moves ADORE's own pointer only: AEGIS still owns the governed
                run's stage, and conduction re-reads the active task journal.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    if not args.force:
        print("reset discards progress and re-runs completed work "
              "(executor cost, ticket churn); re-run with --force")
        return EXIT_ERROR
    built = _engine(args)
    if built is None:
        return EXIT_ERROR
    config, engine = built
    store = _store(config)
    try:
        with _operator_lock(store):
            if not engine.reset(args.run_id, args.to):
                print(f"cannot reset {args.run_id} to {args.to!r} "
                      "(unknown run or invalid stage)")
                return EXIT_ERROR
    except LockHeldError as exc:
        print(f"error: {exc}")
        return EXIT_ERROR
    print(f"{args.run_id}: stage set to {args.to}; run `adore retry "
          f"{args.run_id}` to continue from there")
    return EXIT_OK


def _cmd_cleanup(args: argparse.Namespace) -> int:
    """
    @brief      Handle `adore cleanup`: stale lock + this project's run resources.
    @details    Works only on the selected project's runs. Active and failed
                runs stay for resume/retry, human-owned runs stay with their
                owner, and corrupt runs keep their resources and are reported,
                never deleted. Done, cancelled, stale and state-less runs of
                this project lose their containers, proxies, networks and
                worktrees.
    @param[in]  args Parsed arguments.
    @return     Process exit code.
    """
    built = _engine(args)
    if built is None:
        return EXIT_ERROR
    _, engine = built
    report = engine.cleanup()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["corrupt_runs"]:
        print("note: corrupt run state is never auto-deleted; inspect it, "
              "then use `adore delete <run-id> --force`")
    return EXIT_OK


# PUBLIC API


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Program entry point for the `adore` command.
    @param[in]  argv Optional argument vector (defaults to sys.argv).
    @return     Process exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "config":
        return _cmd_config(args)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "runs":
        return _cmd_runs(args)
    if args.command == "pause":
        return _cmd_pause(args, paused=True)
    if args.command == "resume":
        return _cmd_pause(args, paused=False)
    if args.command == "run":
        return _cmd_run(args)
    if args.command in ("cancel", "retry", "logs", "delete", "handoff"):
        return _cmd_run_op(args)
    if args.command == "stats":
        return _cmd_stats(args)
    if args.command == "report":
        return _cmd_report(args)
    if args.command == "export":
        return _cmd_export(args)
    if args.command == "reset":
        return _cmd_reset(args)
    if args.command == "cleanup":
        return _cmd_cleanup(args)
    if args.command == "init":
        return _cmd_init(args)
    if args.command == "profile":
        return _cmd_profile(args)
    parser.error(f"unknown command: {args.command}")
    return EXIT_ERROR  # pragma: no cover - parser.error exits


# END OF FILE
