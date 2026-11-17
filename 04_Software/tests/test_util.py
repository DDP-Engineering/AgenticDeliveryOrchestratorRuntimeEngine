"""Tests for the shared low-level helpers (runner, durations, timestamps)."""

from __future__ import annotations

import os
import re
import sys

from adore.util import (
    UnsafeFileError,
    in_quiet_hours,
    iso_to_datetime,
    load_env_file,
    parse_duration,
    process_alive,
    read_agent_file,
    run_command,
    utc_now_iso,
    write_agent_file,
)
import pytest

# PUBLIC API / TESTS


def test_process_alive_current_and_invalid_pids() -> None:
    """
    The liveness probe reports the running test process alive and
             rejects non-positive pids, on both POSIX and Windows.
    """
    assert process_alive(os.getpid()) is True
    assert process_alive(0) is False
    assert process_alive(-1) is False


def test_parse_duration_units() -> None:
    """Durations parse for every documented unit and bare numbers."""
    assert parse_duration("90s") == 90
    assert parse_duration("30m") == 1800
    assert parse_duration("24h") == 86400
    assert parse_duration("2d") == 172800
    assert parse_duration("60") == 60
    assert parse_duration(60) == 60
    assert parse_duration("24H") == 86400


def test_parse_duration_rejects_garbage() -> None:
    """Invalid durations raise ValueError."""
    for bad in ("", "h", "12x", "-5s", "1.5h"):
        with pytest.raises(ValueError):
            parse_duration(bad)


def test_run_command_captures_output() -> None:
    """The runner captures stdout and the exit code without a shell."""
    result = run_command([sys.executable, "-c", "print('hello adore')"])
    assert result.ok
    assert result.exit_code == 0
    assert "hello adore" in result.stdout


def test_run_command_missing_binary_reports_127() -> None:
    """A missing executable becomes exit code 127, never an exception."""
    result = run_command(["definitely-not-a-real-binary-adore"])
    assert not result.ok
    assert result.exit_code == 127


def test_utc_now_iso_shape() -> None:
    """Timestamps are compact UTC ISO-8601 with a Z suffix."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", utc_now_iso())


def test_run_command_timeout_reports_124() -> None:
    """
    A hung command becomes exit code 124, never a raised exception,
             and is flagged `timed_out=True` - ADORE's OWN wrapper killed it
             (ADORE-ARCH-010).
    """
    result = run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
    assert not result.ok
    assert result.exit_code == 124
    assert result.timed_out is True


def test_run_command_inner_exit_124_is_not_flagged_as_a_timeout() -> None:
    """
    A command that exits 124 ON ITS OWN, well within its bound, is
             NOT a wrapper timeout: `timed_out` stays False so a genuine
             inner exit 124 (for example the payload's own `timeout(1)`
             inside a container) is never misreported as ADORE's timeout
             (ADORE-ARCH-010).
    """
    result = run_command([sys.executable, "-c", "import sys; sys.exit(124)"], timeout=30)
    assert result.exit_code == 124
    assert result.timed_out is False


def test_iso_to_datetime_round_trip_and_garbage() -> None:
    """Z-form timestamps parse to aware UTC; garbage yields None."""
    parsed = iso_to_datetime("2026-07-03T10:00:00Z")
    assert parsed is not None and parsed.utcoffset().total_seconds() == 0
    assert iso_to_datetime("") is None
    assert iso_to_datetime("not-a-date") is None


def test_in_quiet_hours_windows() -> None:
    """
    Plain and midnight-crossing windows match; malformed windows are
             ignored.
    """
    from datetime import datetime

    night = datetime(2026, 7, 3, 23, 30)
    morning = datetime(2026, 7, 3, 5, 0)
    noon = datetime(2026, 7, 3, 12, 0)
    windows = ["22:00-06:00"]
    assert in_quiet_hours(windows, night)
    assert in_quiet_hours(windows, morning)
    assert not in_quiet_hours(windows, noon)
    assert not in_quiet_hours(["garbage", ""], night)
    assert in_quiet_hours(["11:00-13:00"], noon)


def test_load_env_file(tmp_path) -> None:
    """
    KEY=VALUE lines load; comments/blank/quotes handled; a missing
             file is empty, not an error.
    """
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\nOPENAI_API_KEY=sk-test\nQUOTED='v a l'\nBROKEN\n",
        encoding="utf-8",
    )
    values = load_env_file(env)
    assert values == {"OPENAI_API_KEY": "sk-test", "QUOTED": "v a l"}
    assert load_env_file(tmp_path / "missing.env") == {}


@pytest.mark.parametrize("payload", [b"first\r\nsecond\n", b"\xef\xbf\xbd", b"\xff\xfe\x00\r\n"])
def test_command_preserves_crlf_bytes(monkeypatch, payload):
    """Raw output preserves newlines, literal replacement characters and binary bytes."""
    from types import SimpleNamespace

    from adore.util import run_command

    def execute(*args, **kwargs):
        assert not kwargs.get("text")
        return SimpleNamespace(returncode=0, stdout=payload, stderr=b"")

    monkeypatch.setattr("adore.util.subprocess.run", execute)
    result = run_command(["git", "cat-file"])
    assert result.stdout == payload.decode("utf-8", "replace")
    assert result.stdout_bytes == payload


@pytest.mark.parametrize("source", ['{"key":1,"key":2}', '{"key":NaN}', '[' * 2000])
def test_strict_json_rejects_ambiguous_external_data(source):
    """Duplicate, non-finite and excessive nesting fail closed."""
    from adore.util import strict_json_loads

    with pytest.raises(ValueError):
        strict_json_loads(source)


def test_run_command_preserves_unicode_argument_through_child() -> None:
    """A local child receives and returns Unicode independently of console encoding."""
    text = "Question — țară / Grüße"
    child = "import sys; sys.stdout.buffer.write(sys.argv[1].encode('utf-8'))"
    result = run_command([sys.executable, "-c", child, text])
    assert result.exit_code == 0
    assert result.stdout == text


def test_read_agent_file_reads_a_plain_file_and_reports_absence(tmp_path) -> None:
    """A plain file is returned whole; a missing one is None, not an error."""
    path = tmp_path / "handoff.md"
    assert read_agent_file(path, 16) is None
    path.write_bytes(b"question")
    assert read_agent_file(path, 16) == b"question"


@pytest.mark.parametrize("shape", ["hard-link", "directory", "oversized"])
def test_read_agent_file_refuses_anything_but_a_bounded_plain_file(tmp_path, shape) -> None:
    """Another file's name, a non-file and an oversized file are refused unread."""
    private = tmp_path / "private.txt"
    private.write_bytes(b"PRIVATE")
    path = tmp_path / "handoff.md"
    if shape == "hard-link":
        os.link(private, path)
    elif shape == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"x" * 17)
    with pytest.raises(UnsafeFileError) as refused:
        read_agent_file(path, 16)
    assert "PRIVATE" not in str(refused.value) and "private" not in str(refused.value)


def test_write_agent_file_creates_and_replaces_a_plain_file(tmp_path) -> None:
    """A host-authored file is created, then replaced whole on the next write."""
    path = tmp_path / "gate.sh"
    write_agent_file(path, b"first version")
    write_agent_file(path, b"second")
    assert path.read_bytes() == b"second"


def test_write_agent_file_never_overwrites_another_files_name(tmp_path) -> None:
    """A planted second name of a host file is refused and the host file is intact."""
    private = tmp_path / "private.txt"
    private.write_bytes(b"PRIVATE")
    path = tmp_path / "gate.sh"
    os.link(private, path)
    with pytest.raises(UnsafeFileError):
        write_agent_file(path, b"host content")
    assert private.read_bytes() == b"PRIVATE"


def test_write_agent_file_never_follows_a_link(tmp_path, symlink_support) -> None:
    """A planted link is refused and its target is intact."""
    private = tmp_path / "private.txt"
    private.write_bytes(b"PRIVATE")
    path = tmp_path / "gate.sh"
    path.symlink_to(private)
    with pytest.raises(UnsafeFileError):
        write_agent_file(path, b"host content")
    assert private.read_bytes() == b"PRIVATE"


def test_read_agent_file_never_follows_a_link(tmp_path, symlink_support) -> None:
    """A link to a file of the ADORE account is refused, and the target is not named."""
    private = tmp_path / "private.txt"
    private.write_bytes(b"PRIVATE")
    path = tmp_path / "handoff.md"
    path.symlink_to(private)
    with pytest.raises(UnsafeFileError) as refused:
        read_agent_file(path, 16)
    assert "private" not in str(refused.value)
