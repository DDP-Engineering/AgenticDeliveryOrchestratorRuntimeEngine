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
@file    test_verification_hint.py
@brief   Offline contract tests for repository-derived verification suggestions.
@details Table rows, deterministic provenance, child ambiguity and untrusted file
         boundaries are exercised only through the public reader.
"""

# IMPORTS
import errno
import json
from pathlib import Path
import socket
import subprocess

from adore.verification_hint import suggest_verification_command as suggest
import pytest

# CONSTANTS
LIMIT = 1024 * 1024
ROWS = [
    ("package.json", '{"scripts":{"test":"vitest run"}}', "npm test"),
    ("pyproject.toml", "", "python -m pytest -q"),
    ("go.mod", "", "go test ./..."),
    ("Cargo.toml", "", "cargo test"),
    ("pom.xml", "", "mvn -q test"),
    ("build.gradle", "", "gradle test"),
    ("app.sln", "", "dotnet test"),
    ("Makefile", "test:\n\techo passed\n", "make test"),
]

# HELPER FUNCTIONS


def put(root, name, text=""):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path

# PUBLIC API / TESTS


@pytest.mark.parametrize("name,text,command", ROWS)
@pytest.mark.parametrize("child", ["", "service"])
def test_table_rows(tmp_path, name, text, command, child):
    """@brief Each table row supplies the exact root or sole-child pair."""
    put(tmp_path / child, name, text)
    prefix = f"cd {child} && " if child else ""
    source = f"{child}/{name}" if child else name
    assert suggest(tmp_path) == (prefix + command, source)


@pytest.mark.parametrize("locks,command", [
    ([], "npm test"), (["pnpm-lock.yaml"], "pnpm test"),
    (["yarn.lock"], "yarn test"), (["yarn.lock", "pnpm-lock.yaml"], "pnpm test"),
])
def test_javascript_lock_variants(tmp_path, locks, command):
    put(tmp_path, "package.json", ROWS[0][1])
    for lock in locks:
        put(tmp_path, lock)
    assert suggest(tmp_path) == (command, "package.json")


@pytest.mark.parametrize("name", ["pyproject.toml", "pytest.ini", "tox.ini"])
@pytest.mark.parametrize("locked", [False, True])
def test_python_variants(tmp_path, name, locked):
    put(tmp_path, name)
    if locked:
        put(tmp_path, "uv.lock")
    command = "uv run pytest -q" if locked else "python -m pytest -q"
    assert suggest(tmp_path) == (command, name)


@pytest.mark.parametrize("name", ["build.gradle", "build.gradle.kts"])
@pytest.mark.parametrize("wrapper", [False, True])
def test_gradle_variants(tmp_path, name, wrapper):
    put(tmp_path, name)
    if wrapper:
        put(tmp_path, "gradlew")
    assert suggest(tmp_path) == ("./gradlew test" if wrapper else "gradle test", name)


@pytest.mark.parametrize("names,source,command", [
    (["tox.ini", "pytest.ini", "pyproject.toml"], "pyproject.toml", "python -m pytest -q"),
    (["tox.ini", "pytest.ini"], "pytest.ini", "python -m pytest -q"),
    (["build.gradle.kts", "build.gradle"], "build.gradle", "gradle test"),
    (["a.csproj", "z.sln", "a.sln"], "a.sln", "dotnet test"),
    (["z.csproj", "a.csproj"], "a.csproj", "dotnet test"),
])
def test_source_ties(tmp_path, names, source, command):
    for name in names:
        put(tmp_path, name)
    assert suggest(tmp_path) == (command, source)


@pytest.mark.parametrize("index", range(len(ROWS) - 1))
def test_row_precedence_and_root_suppresses_children(tmp_path, index):
    """@brief Adjacent rows prove the table order; any root row beats a child."""
    name, text, command = ROWS[index]
    later, later_text, _ = ROWS[index + 1]
    put(tmp_path, name, text)
    put(tmp_path, later, later_text)
    put(tmp_path / "child", "package.json", ROWS[0][1])
    assert suggest(tmp_path) == (command, name)


@pytest.mark.parametrize("text", ["{bad", "[]", "null", '{"scripts":[]}',
    '{"scripts":{"test":42}}', '{"scripts":{"test":null}}',
    '{"scripts":null}', '{}', '{"scripts":{"test":""}}',
    json.dumps({"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}),
])
def test_non_tests_are_not_suggestions(tmp_path, text):
    put(tmp_path, "package.json", text)
    assert suggest(tmp_path) is None
    put(tmp_path, "package.json", ROWS[0][1])
    assert suggest(tmp_path) == ("npm test", "package.json")


@pytest.mark.parametrize("text", ["all:\n\techo test:\n", "# test:\n", "testing:\n", "\ttest:\n"])
def test_make_requires_a_target(tmp_path, text):
    put(tmp_path, "Makefile", text)
    assert suggest(tmp_path) is None


@pytest.mark.parametrize("name,eligible", [
    ("api", True), ("a.b-c_2", True), ("_api", True), ("2api", True),
    ("api worker", False), ("api&worker", False), ("-api", False),
    (".api", False), ("équipe", False), ("api;echo", False),
])
def test_child_name_boundary(tmp_path, name, eligible):
    put(tmp_path / name, "go.mod")
    expected = (f"cd {name} && go test ./...", f"{name}/go.mod") if eligible else None
    assert suggest(tmp_path) == expected


@pytest.mark.parametrize("names", [("api", "ui"), ("ui", "api"),
    ("api", "unsafe child"), ("unsafe child", "api")])
def test_ambiguous_children_count_before_name_filter(tmp_path, names):
    for name in names:
        put(tmp_path / name, "go.mod")
    assert suggest(tmp_path) is None
    put(tmp_path, "Cargo.toml")
    assert suggest(tmp_path) == ("cargo test", "Cargo.toml")
    (tmp_path / "Cargo.toml").unlink()
    (tmp_path / "api" / "go.mod").unlink()
    remaining = names[0] if names[1] == "api" else names[1]
    expected = (None if " " in remaining else
                (f"cd {remaining} && go test ./...", f"{remaining}/go.mod"))
    assert suggest(tmp_path) == expected


def test_no_match_or_deep_recursion(tmp_path):
    assert suggest(tmp_path) is None
    put(tmp_path, "README.md", "Run tests with an arbitrary command")
    put(tmp_path / "child" / "deep", "go.mod")
    assert suggest(tmp_path) is None
    put(tmp_path, "go.mod")
    assert suggest(tmp_path) == ("go test ./...", "go.mod")


@pytest.mark.parametrize("kind", ["manifest", "lock", "directory", "wrapper"])
def test_external_links_ignored_without_reads(tmp_path, monkeypatch, kind):
    """@brief External links cannot supply either a match or command variant."""
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    external = put(outside, "package.json", ROWS[0][1])
    if kind == "manifest":
        (root / "package.json").symlink_to(external)
        expected = None
    elif kind == "directory":
        (root / "child").symlink_to(outside, target_is_directory=True)
        expected = None
    elif kind == "lock":
        put(root, "package.json", ROWS[0][1])
        (root / "pnpm-lock.yaml").symlink_to(external)
        expected = ("npm test", "package.json")
    else:
        put(root, "build.gradle")
        (root / "gradlew").symlink_to(external)
        expected = ("gradle test", "build.gradle")
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert not path.resolve().is_relative_to(outside), "external evidence was opened"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    assert suggest(root) == expected


def test_contained_symlink_and_source(tmp_path):
    put(tmp_path, "manifest", ROWS[0][1])
    (tmp_path / "package.json").symlink_to(tmp_path / "manifest")
    assert suggest(tmp_path) == ("npm test", "package.json")


@pytest.mark.parametrize("size", [LIMIT, LIMIT + 1])
@pytest.mark.parametrize("name", ["package.json", "go.mod", "Makefile", "pnpm-lock.yaml"])
def test_size_boundary_without_oversized_content_access(tmp_path, monkeypatch, name, size):
    """@brief Size eligibility covers content, presence and command-selection files."""
    text = ROWS[0][1] if name == "package.json" else "test:\n" if name == "Makefile" else ""
    path = put(tmp_path, name, text + " " * (size - len(text)))
    if name == "pnpm-lock.yaml":
        put(tmp_path, "package.json", ROWS[0][1])
    original = Path.open

    def guarded(candidate, *args, **kwargs):
        assert candidate != path or size <= LIMIT, "oversized evidence was opened"
        return original(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    if name == "pnpm-lock.yaml":
        expected = ("pnpm test" if size <= LIMIT else "npm test", "package.json")
    else:
        command = {row[0]: row[2] for row in ROWS}[name]
        expected = (command, name) if size <= LIMIT else None
    assert suggest(tmp_path) == expected


@pytest.mark.parametrize("matching", [False, True])
def test_reader_is_repeatable_and_has_no_process_network_or_write(tmp_path, monkeypatch, matching):
    """@brief Files remain byte-identical; external execution and sockets are forbidden."""
    put(tmp_path, "package.json" if matching else "README.md", ROWS[0][1])
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("reader attempted a side effect")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    expected = ("npm test", "package.json") if matching else None
    assert suggest(tmp_path) == suggest(tmp_path) == expected
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize("text", [
    "[" * 2000,
    '{"scripts":{"test":' + "1" * 5000 + "}}",
    '{"unused":' + "[" * 2000 + "0" + "]" * 2000 + "}",
], ids=["truncated-deep-json", "oversized-integer", "deep-json"])
@pytest.mark.parametrize("child", ["", "service"])
def test_package_decoder_limits_are_misses_with_later_row_fallback(tmp_path, text, child):
    """@brief Decoder resource limits are optional package misses, not scan failures."""
    directory = tmp_path / child
    put(directory, "package.json", text)
    assert suggest(tmp_path) is None
    put(directory, "go.mod")
    prefix = f"cd {child} && " if child else ""
    source = f"{child}/go.mod" if child else "go.mod"
    assert suggest(tmp_path) == (prefix + "go test ./...", source)


@pytest.mark.parametrize("kind", ["manifest", "lock", "directory", "wrapper", "root"])
def test_symlink_loops_are_filesystem_errors(tmp_path, kind):
    """@brief Static link loops fail as filesystem errors, never a partial suggestion."""
    root = tmp_path / "repo"
    root.mkdir()
    name = {"manifest": "package.json", "lock": "pnpm-lock.yaml",
            "directory": "child", "wrapper": "gradlew", "root": "root-link"}[kind]
    if kind == "lock":
        put(root, "package.json", ROWS[0][1])
    elif kind == "wrapper":
        put(root, "build.gradle")
    link = root / name
    link.symlink_to(link, target_is_directory=kind in {"directory", "root"})
    with pytest.raises(OSError) as error:
        suggest(link if kind == "root" else root)
    assert error.value.errno == errno.ELOOP


def test_access_errors_are_not_empty_repository_evidence(tmp_path, monkeypatch):
    """@brief An inaccessible directory cannot silently produce a partial suggestion."""
    original = Path.iterdir

    def denied(path):
        if path == tmp_path:
            raise PermissionError("fixture denied")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", denied)
    with pytest.raises(PermissionError, match="fixture denied"):
        suggest(tmp_path)

# END OF FILE
