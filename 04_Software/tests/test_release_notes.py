"""Runtime release-note parsing and localized About responses."""

from __future__ import annotations

from adore import __version__ as RELEASE_VERSION
from adore.release_notes import ReleaseNotesError, parse_release_notes
from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest

LOCALES = ("en", "fr", "de", "ro")

# PUBLIC API / TESTS

def test_parse_rejects_malformed_shape() -> None:
    """The runtime parser refuses a document whose shape is wrong."""
    with pytest.raises(ReleaseNotesError):
        parse_release_notes('schema = 1\n[[release]]\nversion = 3\n')
    with pytest.raises(ReleaseNotesError):
        parse_release_notes('schema = 2\n')
    with pytest.raises(ReleaseNotesError):
        parse_release_notes('schema = true\n')


def test_about_stays_available_without_readable_release_notes(tmp_path, monkeypatch) -> None:
    """A broken packaged file leaves About working with no release notes."""
    def broken() -> list[dict]:
        raise ReleaseNotesError("broken")
    monkeypatch.setattr("adore.web.app.load_release_notes", broken)
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/api/v1/about")
    assert response.status_code == 200
    assert response.json()["release_notes"] == []


def test_about_returns_release_notes_with_every_locale(tmp_path) -> None:
    """About carries the packaged release notes for the What's new window."""
    with TestClient(create_app(tmp_path)) as client:
        value = client.get("/api/v1/about").json()
    releases = value["release_notes"]
    assert any(release["version"] == RELEASE_VERSION and release["date"] for release in releases)
    entries = [entry for release in releases for entry in release["entries"]]
    assert entries
    assert all(set(entry["topic"]) == set(LOCALES) == set(entry["text"]) for entry in entries)
    assert {entry["category"] for entry in entries} <= {"new", "improved", "fixed"}
