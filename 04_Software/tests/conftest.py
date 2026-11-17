"""Shared pytest fixtures for the ADORE test suite."""

from __future__ import annotations

import errno
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Allow selected tests to retain production password hashing.
    parser: Pytest command-line option registry.
    """
    parser.addoption("--real-password-hashing", action="store_true",
                     help="Use production Argon2 parameters in every selected Python test.")


@pytest.fixture(scope="session")
def fast_password_hasher():
    """
    Create one low-cost real Argon2 hasher per pytest worker.
    Returns: Hasher preserving salt, verification and malformed-hash behavior.
    Note: Only this test fixture uses these parameters; product defaults are unchanged.
    """
    from argon2 import PasswordHasher

    return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


@pytest.fixture(autouse=True)
def isolated_password_hashing(request: pytest.FixtureRequest,
                             monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Reduce fixture hashing without bypassing account/session checks.
    request: Test marker, command-line option and worker fixture access.
    monkeypatch: Restore the production hasher after each test.
    Note: Pure core tests do not import the optional web dependency for this fixture.
    """
    if (request.config.getoption("--real-password-hashing")
            or request.node.get_closest_marker("real_password_hashing")):
        return
    try:
        # Imported here, so the first web test of a worker is fast as well.
        from adore.web import store
    except ImportError:
        return
    monkeypatch.setattr(store, "_HASHER", request.getfixturevalue("fast_password_hasher"))


@pytest.fixture
def symlink_support(tmp_path: Path) -> None:
    """
    Require real link support only for tests exercising filesystem links.
    tmp_path: Isolated location used for a capability probe.
    Note: Unsupported filesystems or accounts skip explicitly; other IO errors fail.
    """
    source, link = tmp_path / "symlink-probe-source", tmp_path / "symlink-probe-link"
    source.write_bytes(b"probe")
    try:
        link.symlink_to(source)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in {
            errno.EPERM, errno.EACCES, errno.ENOSYS, errno.EOPNOTSUPP,
        }:
            pytest.skip("The test account/filesystem cannot create symbolic links")
        raise
    finally:
        if link.is_symlink():
            link.unlink()
        source.unlink()


@pytest.fixture(scope="session")
def empty_git_config(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Create one empty Git configuration file per pytest worker.
    tmp_path_factory: Session-scoped temporary directory factory.
    Returns: Path of the empty file.
    """
    path = tmp_path_factory.mktemp("git-config") / "gitconfig"
    path.write_bytes(b"")
    return path


@pytest.fixture(autouse=True)
def isolated_git_config(empty_git_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Keep real `git` calls away from the developer's own Git settings.
    Tests that run `git` would otherwise inherit signing, hooks, line-ending
                and default-branch settings of the machine they run on.
    empty_git_config: Empty file used as the global configuration.
    monkeypatch: Restore the environment after each test.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_git_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture(autouse=True)
def adore_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    An isolated ADORE config home wired into the environment.
    Sets ADORE_HOME so any `ProfileStore()` built inside `main()` /
                the CLI resolves to a throwaway per-test directory, never the
                developer's real home.
    tmp_path: pytest tmp dir.
    monkeypatch: Fixture used to set ADORE_HOME.
    Returns: The home directory path.
    """
    home = tmp_path / "adore-home"
    monkeypatch.setenv("ADORE_HOME", str(home))
    return home
