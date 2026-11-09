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
@file test_release_notes.py
@brief Tests for the checked four-locale release notes and their About exposure.
@details CLI contract fixtures use injected read-only Git responses; no real
         Git initialization, index changes or commits occur in unit tests.
"""

from __future__ import annotations

# IMPORTS
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys

from adore import __version__ as RELEASE_VERSION
from adore.release_notes import ReleaseNotesError, parse_release_notes
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

# CONSTANTS

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "02_Tools" / "internal" / "check_release_notes.py"
NOTES = "04_Software/adore/release_notes.toml"
LOCALES = ("en", "fr", "de", "ro")


# HELPER FUNCTIONS

def _entry(category: str = "new", topic: str = "Statistics",
           text: str = "GitHub and GitLab drafts show each MR/PR figure once.",
           skip: str = "") -> str:
    """
    @brief      Render one release entry with every locale except @p skip.
    @return     TOML text for one `[[release.entry]]`.
    """
    def table(value: str) -> str:
        pairs = (f'{locale} = "{value}"' for locale in LOCALES if locale != skip)
        return "{ " + ", ".join(pairs) + " }"
    return (f'[[release.entry]]\ncategory = "{category}"\n'
            f'topic = {table(topic)}\ntext = {table(text)}\n')


def _release(version: str, entries: list[str], date: str = "") -> str:
    """
    @brief      Render one release with its entries.
    @return     TOML text for one `[[release]]`.
    """
    head = f'[[release]]\nversion = "{version}"\n' + (f'date = "{date}"\n' if date else "")
    return head + "".join(entries)


def _notes(*releases: str) -> str:
    """@brief Render a complete release notes document."""
    return "schema = 1\n\n" + "\n".join(releases)


# The current release date as written in the real changelog, so a release cut needs no test edit.
_CURRENT = re.search(rf"^## \[{re.escape(RELEASE_VERSION)}\] - (\d{{4}}-\d{{2}}-\d{{2}})",
                     (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
assert _CURRENT, f"CHANGELOG.md needs a dated '## [{RELEASE_VERSION}] - <date>' heading"
DATE = _CURRENT.group(1)
OTHER_DATE = "2000-01-01"
VALID = _notes(
    _release("Unreleased", [_entry(), _entry("fixed", "Jobs", "Jobs keep their sort order.")]),
    _release(RELEASE_VERSION, [_entry("improved", "AEGIS", "Works with newer AEGIS.")], DATE))


def _case(*entries: str, released: str = "") -> str:
    """@brief Notes with the given unreleased entries followed by @p released or a valid release."""
    return _notes(_release("Unreleased", list(entries)),
                  released or _release(RELEASE_VERSION, [_entry()], DATE))


def _fixture(root: Path, notes: str) -> Path:
    """
    @brief      Build a minimal repository holding the files the checker reads.
    @param[in]  root Fixture repository root.
    @param[in]  notes Release notes TOML text.
    @return     Fixture root.
    """
    for relative in ("CHANGELOG.md", "04_Software/adore/__init__.py"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, target)
    (root / NOTES).write_bytes(notes.encode())
    return root


def _run(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """@brief Run the public release notes check against a repository root."""
    return subprocess.run([sys.executable, str(CHECKER), "--repo-root", str(root), *extra],
                          check=False, capture_output=True, text=True, encoding="utf-8")


def _offline_checker(monkeypatch, root: Path, changed: list[str], untracked: list[str]):
    """@brief Load the public checker with injected read-only Git responses.
    @param[in] monkeypatch Restore the subprocess boundary after each test.
    @param[in] root Fixture repository root.
    @param[in] changed Tracked paths returned by the fake diff query.
    @param[in] untracked Paths returned by the fake untracked query.
    @return Loaded checker module with the bounded query double.
    """
    spec = importlib.util.spec_from_file_location("offline_release_notes_checker", CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)

    def git(argv, **kwargs):
        """@brief Admit only the two exact read-only query shapes the checker owns."""
        assert argv[:3] == ["git", "-C", str(root)]
        if argv[3:] == ["diff", "--name-only", "--end-of-options", "HEAD", "--"]:
            values = changed
        else:
            assert argv[3:] == ["ls-files", "--others", "--exclude-standard"]
            values = untracked
        return subprocess.CompletedProcess(argv, 0, "\n".join(values), "")

    monkeypatch.setattr(checker.subprocess, "run", git)
    return checker


# PUBLIC API / TESTS

def test_repository_release_notes_meet_the_contract() -> None:
    """@brief The shipped release notes pass the public check."""
    result = _run(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_valid_notes_pass_with_product_names_and_short_pairs(tmp_path) -> None:
    """@brief Product names such as GitHub and pairs such as MR/PR are plain language."""
    result = _run(_fixture(tmp_path, VALID))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("notes", "expected"), [
    (_case(_entry(skip="ro")), "missing locale ro"),
    (_case(_entry(category="added")), "category"),
    (_case(_entry(text="x" * 101)), "longer than 100"),
    (_case(_entry(text="Edit App.tsx to see it.")), "technical reference"),
    (_case(_entry(text="/api/v1/about returns notes.")), "technical reference"),
    (_case(_entry(text="Done in REQ-UX-2cace5dd.")), "technical reference"),
    (_case(_entry(text="JobWorkspace shows rows.")), "technical reference"),
    (_case(*[_entry() for _ in range(11)]), "more than 10"),
    (_notes(_release(RELEASE_VERSION, [_entry()], DATE), _release("Unreleased", [_entry()])),
     "order"),
    (_case(_entry(), released=_release("9.9.9", [_entry()], "2026-12-01")
           + _release(RELEASE_VERSION, [_entry()], DATE)), "CHANGELOG"),
    (_case(_entry(), released=_release(RELEASE_VERSION, [_entry()], OTHER_DATE)), "date"),
    (_case(_entry(text="Run `adore` now.")), "technical reference"),
    (_case(_entry(text="Set capture_tokens to true.")), "technical reference"),
    (_case(_entry(text="Set ADORE_HOME first.")), "technical reference"),
    (_case(_entry(text="Open web/src/views to see it.")), "technical reference"),
    (_case(_entry(text="See https://example.invalid for more.")), "technical reference"),
    (_case(_entry(topic="t" * 41)), "longer than 40"),
    (_case(_entry().replace("ro = ", "it = \"Ciao\", ro = ", 1)), "unknown locale it"),
    (_notes(_release("Unreleased", [_entry()], OTHER_DATE),
            _release(RELEASE_VERSION, [_entry()], DATE)), "no date"),
    (_case(_entry(), released=_release(RELEASE_VERSION, [_entry()], DATE) * 2), "repeats"),
    (_case(_entry(), released=_release("1.0", [_entry()], DATE)
           + _release(RELEASE_VERSION, [_entry()], DATE)), "x.y.z"),
    (_notes(_release("Unreleased", [_entry()])), f"current version {RELEASE_VERSION}"),
])
def test_contract_failures_are_reported(tmp_path, notes: str, expected: str) -> None:
    """@brief Each authoring-contract breach fails the check with a clear message."""
    result = _run(_fixture(tmp_path, notes))
    assert result.returncode == 1
    assert expected in result.stdout


def test_since_warns_when_changelog_changes_without_release_notes(tmp_path, monkeypatch, capsys):
    """@brief The --since mode warns, without failing, about a changelog-only change."""
    root = _fixture(tmp_path, VALID)
    changed = ["CHANGELOG.md"]
    checker = _offline_checker(monkeypatch, root, changed, [])
    assert checker.main(["--repo-root", str(root), "--since", "HEAD"]) == 0
    assert "WARN" in capsys.readouterr().out
    changed.append(NOTES)
    assert checker.main(["--repo-root", str(root), "--since", "HEAD"]) == 0
    assert "WARN" not in capsys.readouterr().out


def test_since_counts_new_untracked_release_notes(tmp_path, monkeypatch, capsys):
    """@brief A release notes file not yet added to git counts as changed."""
    root = _fixture(tmp_path, VALID)
    checker = _offline_checker(monkeypatch, root, ["CHANGELOG.md"], [NOTES])
    assert checker.main(["--repo-root", str(root), "--since", "HEAD"]) == 0
    assert "WARN" not in capsys.readouterr().out


def test_parse_rejects_malformed_shape() -> None:
    """@brief The runtime parser refuses a document whose shape is wrong."""
    with pytest.raises(ReleaseNotesError):
        parse_release_notes('schema = 1\n[[release]]\nversion = 3\n')
    with pytest.raises(ReleaseNotesError):
        parse_release_notes('schema = 2\n')
    with pytest.raises(ReleaseNotesError):
        parse_release_notes('schema = true\n')


def test_about_stays_available_without_readable_release_notes(tmp_path, monkeypatch) -> None:
    """@brief A broken packaged file leaves About working with no release notes."""
    def broken() -> list[dict]:
        raise ReleaseNotesError("broken")
    monkeypatch.setattr("adore.web.app.load_release_notes", broken)
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/api/v1/about")
    assert response.status_code == 200
    assert response.json()["release_notes"] == []


def test_about_returns_release_notes_with_every_locale(tmp_path) -> None:
    """@brief About carries the packaged release notes for the What's new window."""
    with TestClient(create_app(tmp_path)) as client:
        value = client.get("/api/v1/about").json()
    releases = value["release_notes"]
    assert any(release["version"] == RELEASE_VERSION and release["date"] for release in releases)
    entries = [entry for release in releases for entry in release["entries"]]
    assert entries
    assert all(set(entry["topic"]) == set(LOCALES) == set(entry["text"]) for entry in entries)
    assert {entry["category"] for entry in entries} <= {"new", "improved", "fixed"}
