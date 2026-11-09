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
@file    test_host_folders.py
@brief   Host directory browsing contracts and administrator boundaries.
@details Uses temporary local directories only; no external tools or network.
"""

# IMPORTS
import os
from pathlib import Path

from adore.web.app import create_app
from fastapi.testclient import TestClient
import pytest


# PUBLIC CONTRACT TESTS
def test_admin_lists_only_directories_without_writes(tmp_path):
    """@brief Host navigation returns paths, parents and folders without creating a clone."""
    root = tmp_path / "choices"
    (root / "Folder with spaces").mkdir(parents=True)
    (root / "Alpha").mkdir()
    (root / "private-file.txt").write_text("not returned", encoding="utf-8")
    app = create_app(tmp_path / "adore")
    with TestClient(app) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/host-folders", params={"path": str(root)})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["path"] == str(root.resolve())
        assert data["parent"] == str(root.parent.resolve())
        assert data["system"] in {"Windows", "Linux"}
        assert [row["name"] for row in data["folders"]] == ["Alpha", "Folder with spaces"]
        assert data["folders"][1]["path"] == str(root / "Folder with spaces")
        assert data["roots"] and data["truncated"] is False
        assert response.headers["cache-control"] == "no-store"
        assert not (root / "new-repository").exists()
        assert "not returned" not in response.text


def test_host_folder_paths_require_administrator(tmp_path, monkeypatch):
    """@brief Anonymous users and developers cannot enumerate host directories."""
    app = create_app(tmp_path / "adore")
    app.state.web_store.create_user("developer", "long-password", "developer")
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Unauthenticated directory reads are forbidden")
    monkeypatch.setattr("adore.web.host_folders.list_host_folders", forbidden)
    with TestClient(app) as client:
        assert client.get("/api/v1/host-folders").status_code == 401
        client.post("/api/v1/session", json={"username": "developer", "password": "long-password"})
        assert client.get("/api/v1/host-folders").status_code == 403


@pytest.mark.parametrize("path", ["relative", "../outside", "//server/share", "\\\\server\\share",
                                   "bad\x00path", "x" * 4097])
def test_malformed_host_folder_paths_fail_closed(tmp_path, path):
    """@brief Malformed external directory input is refused without listing another folder."""
    with TestClient(create_app(tmp_path / "adore")) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        response = client.get("/api/v1/host-folders", params={"path": path})
        assert response.status_code in {400, 422}
        assert "folders" not in response.json()


def test_missing_file_and_inaccessible_folders_return_explicit_errors(tmp_path, monkeypatch):
    """@brief Missing/file/permission cases return typed errors and disclose no OS diagnostic."""
    from adore.web import host_folders

    data_file = tmp_path / "a-file"
    data_file.write_text("private", encoding="utf-8")
    with TestClient(create_app(tmp_path / "adore")) as client:
        client.post("/api/v1/session", json={"username": "admin", "password": "admin"})
        for path in [data_file, tmp_path / "missing"]:
            response = client.get("/api/v1/host-folders", params={"path": str(path)})
            assert response.status_code == 400
        def denied(_path):
            raise PermissionError("private OS error")
        monkeypatch.setattr(host_folders.os, "scandir", denied)
        response = client.get("/api/v1/host-folders", params={"path": str(tmp_path)})
        assert response.status_code == 400
        assert "private OS error" not in response.text


def test_folder_listing_is_bounded_and_default_is_account_home(tmp_path, monkeypatch):
    """@brief Large directories return a limited list and no-path navigation uses OS home."""
    from adore.web import host_folders

    for index in range(220):
        (tmp_path / f"folder-{index:03d}").mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    result = host_folders.list_host_folders()
    assert result["path"] == str(tmp_path.resolve())
    assert len(result["folders"]) == 200
    assert result["truncated"] is True


def test_file_heavy_directories_have_a_scan_limit(tmp_path):
    """@brief Even a directory with no subfolders cannot cause an unbounded scan."""
    from adore.web.host_folders import list_host_folders

    for index in range(2010):
        (tmp_path / f"file-{index:04d}").touch()
    result = list_host_folders(str(tmp_path))
    assert result["folders"] == []
    assert result["truncated"] is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX links verified natively on Linux")
def test_links_are_not_followed_during_host_navigation(tmp_path):
    """@brief Directory symlinks are omitted and linked paths fail closed."""
    from adore.web.host_folders import HostFolderError, list_host_folders

    (tmp_path / "actual").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "actual", target_is_directory=True)
    assert [row["name"] for row in list_host_folders(str(tmp_path))["folders"]] == ["actual"]
    with pytest.raises(HostFolderError):
        list_host_folders(str(tmp_path / "link"))


@pytest.mark.skipif(os.name != "nt", reason="Windows mapped-drive boundary")
def test_mapped_network_drive_is_refused_before_listing(tmp_path, monkeypatch):
    """@brief A mapped remote drive cannot bypass the UNC navigation refusal."""
    import ctypes

    from adore.web.host_folders import HostFolderError, list_host_folders

    monkeypatch.setattr(ctypes.windll.kernel32, "GetDriveTypeW", lambda _root: 4)
    with pytest.raises(HostFolderError):
        list_host_folders(str(tmp_path))


# END OF FILE
