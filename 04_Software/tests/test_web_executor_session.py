"""Offline authenticated archived-session contracts."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from tests.test_web_jobs import _fixture, _login


def _archive(store, name="build-attempt-2-attempt1", records=None):
    """Write one physical launch in the current archive format."""
    folder = store.run_dir("same") / "io" / "archive" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.json").write_text(json.dumps({
        "created_at": "2026-11-14T10:00:00Z", "archive_stem": name.split("-attempt1")[0],
        "exit_code": 0, "timed_out": False, "argv": ["ignored"], "timeout": 300,
        "output_file_present": True, "stderr_file_present": True,
    }), encoding="utf-8")
    if records is None:
        fixture = Path(__file__).parent / "fixtures/pi_rpc/run_tool_calls_chatgpt.jsonl"
        records = [item["record"] for line in fixture.read_text(encoding="utf-8").splitlines()
                   if (item := json.loads(line))["dir"] == "stdout"]
    (folder / "output.jsonl").write_bytes(b"".join(
        (json.dumps(record, ensure_ascii=False) + "\n").encode() for record in records))
    return folder


def _url(item, suffix=""):
    return f"/api/v1/jobs/{item.project_id}/same/sessions{suffix}"


# LIVE SESSION CONTRACTS
@pytest.mark.parametrize("package", [False, True])
def test_rpc_producer_keeps_literal_live_and_archive_but_masks_operations(tmp_path, package):
    """Known binding/package secrets and generic credential shapes reach sessions only."""
    from adore.executor.launcher import PiExecutor

    from tests.test_pi_rpc import FAKE, FakePi, SpawnTarget
    _, items, stores, app = _fixture(tmp_path)
    run = stores[0].run_dir("same")
    io, worktree = run / "io", tmp_path / "work"
    worktree.mkdir()
    text = "binding-only-token sk-inval****0000 Bearer abcdefghijklmnop"
    if package:
        text += " package-known-token"
    fixture = tmp_path / "raw-session.jsonl"
    fixture.write_text("".join(json.dumps(row) + "\n" for row in [
        {"dir": "stdin", "record": {"type": "prompt"}},
        {"dir": "stderr", "record": text},
        {"dir": "stdout", "record": {"type": "message_end", "message": {
            "role": "user", "content": text}}},
    ]), encoding="utf-8")
    fake = FakePi(tmp_path, "run_tool_calls_chatgpt")
    # The fake writes its durable session beside this job's exchange directory.
    fake.record = run / "rpc-commands.log"
    fake.command[3:] = [str(fixture), "--hang"]
    assert fake.command[2] == str(FAKE)
    target = SpawnTarget(fake)
    target.redact = lambda value: value.replace("binding-only-token", "[REDACTED]")
    observed = []
    with TestClient(app) as client:
        _login(client)

        def cancel_after_live():
            """Read an actual in-flight producer record before the fake settles."""
            if not (io / "output.jsonl").exists() or not (io / "output.jsonl").stat().st_size:
                return False
            row = client.get(_url(items[0])).json()["sessions"][0]
            response = client.get(_url(items[0], "/" + row["id"]))
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "no-store"
            observed.extend(item["text"] for item in response.json()["items"])
            return text in observed

        options = {"package_secrets": {"KEY": "package-known-token"}} if package else {}
        result = PiExecutor("m").run_gate(target, worktree, io, text, timeout=10,
            archive_stem="build-attempt-1", cancel=cancel_after_live, **options)
        assert result.exit_code == 130 and observed == [text]
        archive = Path(result.artifact_dirs[0])
        assert text in (io / "output.jsonl").read_text(encoding="utf-8")
        assert text in (archive / "output.jsonl").read_text(encoding="utf-8")
        response = client.get(_url(items[0], "/" + archive.name))
        assert response.status_code == 200, response.text
        assert response.json()["items"][0]["text"] == text
        operations = result.output + result.stderr + str(result.diagnostics)
        for value in ["binding-only-token", "sk-inval", "abcdefghijklmnop"] + (
                ["package-known-token"] if package else []):
            assert value not in operations
            assert value not in (io / "stderr.log").read_text(encoding="utf-8")
            assert value not in (archive / "stderr.log").read_text(encoding="utf-8")
    assert fake.all_exited()


def _live(request, store, launch="a" * 32, records=b""):
    """Seed the current launch marker and its owned output."""
    from adore.state import StateStore
    io = store.run_dir("same") / "io"
    if not hasattr(store, "_test_live_owner"):
        owner = StateStore(io).run_lock("agent-session")
        owner.__enter__()
        request.addfinalizer(lambda: owner.__exit__(None, None, None))
        store._test_live_owner = owner
    io.mkdir(exist_ok=True)
    marker = {"schema": 1, "id": "live-" + launch,
              "archive_id": "build-attempt-3-attempt1", "start_at": "2026-11-14T11:00:00Z"}
    (io / "live.json").write_text(json.dumps(marker), encoding="utf-8")
    (io / "output.jsonl").write_bytes(records)
    return marker, io / "output.jsonl"


def test_live_complete_line_cursor_growth_and_visibility(tmp_path, request):
    """Live pages keep partial records, exact text and role restrictions."""
    _, items, stores, app = _fixture(tmp_path)
    _archive(stores[0], records=[])
    first = b'{"type":"message_end","message":{"role":"user","content":"raw KEY=fake"}}\n'
    tail = b'{"type":"message_end","message":{"role":"assistant","content":"finished"}}'
    marker, source = _live(request, stores[0], records=first + tail)
    with TestClient(app) as client:
        _login(client)
        rows = client.get(_url(items[0])).json()["sessions"]
        assert rows[0]["id"] == marker["id"] and rows[0]["live"] is True
        endpoint = _url(items[0], "/" + marker["id"])
        response = client.get(endpoint)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        page = response.json()
        assert [x["text"] for x in page["items"]] == ["raw KEY=fake"]
        assert page["next_cursor"] == len(first)
        query = {"cursor": page["next_cursor"], "continuity": page["continuity"]}
        assert client.get(endpoint, params=query).json()["items"] == []
        with source.open("ab") as handle:
            handle.write(b"\n")
        page = client.get(endpoint, params=query).json()
        assert [x["text"] for x in page["items"]] == ["finished"]
        assert page["next_cursor"] == source.stat().st_size
        assert page["session_ended"] is False


@pytest.mark.parametrize("change", ["replace", "truncate", "regrow", "no-newline",
                                    "marker", "finish", "missing", "abandoned"])
def test_live_discontinuity_ends_without_mixing_attempts(tmp_path, request, change):
    """Replacement and same-inode equal-length rewrites cannot reuse a cursor."""
    from tests.test_web_jobs import _state
    _, items, stores, app = _fixture(tmp_path)
    record = b'{"type":"message_end","message":{"role":"user","content":"first"}}\n'
    marker, source = _live(request, stores[0], records=record)
    with TestClient(app) as client:
        _login(client)
        endpoint = _url(items[0], "/" + marker["id"])
        page = client.get(endpoint).json()
        if change == "replace":
            source.rename(source.with_suffix(".old"))
            source.write_bytes(record)
        elif change == "truncate":
            source.write_bytes(b"")
        elif change == "regrow":
            source.write_bytes(record.replace(b"first", b"other"))
        elif change == "no-newline":
            source.write_bytes(b"x" * len(record))
        elif change == "abandoned":
            stores[0]._test_live_owner.__exit__(None, None, None)
            assert client.get(_url(items[0])).json()["sessions"] == []
        elif change == "marker":
            _live(request, stores[0], "b" * 32, record)
        elif change == "finish":
            _state(stores[0], "same", lifecycle="done", stage="done")
        else:
            (source.parent / "live.json").unlink()
        response = client.get(endpoint, params={"cursor": page["next_cursor"],
            "continuity": page["continuity"], "archive_id": marker["archive_id"]})
        assert response.status_code == 200, response.text
        assert response.json()["session_ended"] is True
        assert response.json()["items"] == []
        assert response.json()["archive_id"] == marker["archive_id"]


def test_live_between_sessions_bad_cursors_and_project_denial(tmp_path, request):
    """Old output alone is history; inaccessible and invalid cursors fail closed."""
    _, items, stores, app = _fixture(tmp_path)
    marker, source = _live(request, stores[0], records=b'{}\n')
    user = app.state.web_store.create_user("dev", "test-password", "developer")
    app.state.web_store.set_memberships(user["id"], ["beta"])
    with TestClient(app) as client:
        _login(client, "dev", "test-password")
        assert client.get(_url(items[0])).status_code == 404
        assert client.get(_url(items[0], "/" + marker["id"])).status_code == 404
        _login(client)
        endpoint = _url(items[0], "/" + marker["id"])
        assert client.get(endpoint + "?cursor=9999").json()["session_ended"] is True
        assert client.get(endpoint + "?cursor=1").status_code in {400, 422, 503}
        (source.parent / "live.json").unlink()
        assert client.get(_url(items[0])).json()["sessions"] == []


def test_live_rewrite_during_first_read_discards_parsed_items(tmp_path, request, monkeypatch):
    """A same-inode rewrite cannot pair old parsed items with a new proof."""
    from adore.web.executor_session import read_session
    _, _, stores, _ = _fixture(tmp_path)
    old = b'{"type":"message_end","message":{"role":"user","content":"first"}}\n'
    old += b'{"type":"message_end","message":{"role":"user","content":"next"}}\n'
    marker, source = _live(request, stores[0], records=old)
    original = Path.open
    rewritten = False

    class RacingRead:
        """Inject an external rewrite immediately after a complete line read."""
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def readline(self, *args):
            nonlocal rewritten
            line = self.handle.readline(*args)
            if not rewritten:
                with original(source, "wb") as writer:
                    writer.write(old.replace(b"first", b"other"))
                rewritten = True
            return line

    def racing_open(path, *args, **kwargs):
        handle = original(path, *args, **kwargs)
        return RacingRead(handle) if path == source and args == ("rb",) else handle

    monkeypatch.setattr(Path, "open", racing_open)
    page = read_session(stores[0].run_dir("same"), marker["id"], limit=1)
    assert rewritten and page["session_ended"] is True
    assert page["items"] == []


def test_live_mid_record_truncation_ends_without_spinning(tmp_path, request, monkeypatch):
    """An EOF during an oversized/partial record terminates the bounded read."""
    from adore.web.executor_session import read_session
    _, _, stores, _ = _fixture(tmp_path)
    marker, source = _live(request, stores[0], records=b"x" * 10000)
    original = Path.open

    class TruncatingRead:
        """Model EOF before the captured size, with a finite no-progress guard."""
        def __init__(self, handle):
            self.handle, self.calls = handle, 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def readline(self, *args):
            self.calls += 1
            assert self.calls <= 2, "reader spun after truncation EOF"
            if self.calls == 1:
                value = self.handle.readline(16)
                with original(source, "wb"):
                    pass
                return value
            return b""

    def truncating_open(path, *args, **kwargs):
        handle = original(path, *args, **kwargs)
        return TruncatingRead(handle) if path == source and args == ("rb",) else handle

    monkeypatch.setattr(Path, "open", truncating_open)
    page = read_session(stores[0].run_dir("same"), marker["id"])
    assert page["session_ended"] is True and page["items"] == []


@pytest.mark.parametrize("role", ["admin", "developer"])
def test_live_completed_parts_thinking_costs_and_bad_records(tmp_path, request, role):
    """Live events retain source grouping, literal text and existing security."""
    _, items, stores, app = _fixture(tmp_path)
    records = [
        {"type": "message_start", "message": {"role": "assistant"}},
        {"type": "message_update", "assistantMessageEvent": {"delta": "DELTA_NEVER"}},
        {"type": "message_end", "message": {"role": "system", "content": "SYSTEM_NEVER"}},
        {"type": "message_end", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "answer"}, {"type": "thinking", "thinking": "readable"}],
            "usage": {"input": 1, "cost": {"total": .25}}}},
        {"type": "message_start", "message": {"role": "assistant"}},
    ]
    marker, source = _live(request, stores[0], records=b"not json\n" + b"".join(
        (json.dumps(record) + "\n").encode() for record in records))
    if role == "developer":
        user = app.state.web_store.create_user("dev", "test-password", role)
        app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        _login(client) if role == "admin" else _login(client, "dev", "test-password")
        page = client.get(_url(items[0], "/" + marker["id"])).json()
        assert len(page["items"]) == 2 and len(page["items"][1]["parts"]) == 3
        assert page["thinking"] is True
        assert ("cost" in json.dumps(page)) is (role == "admin")
        assert all(value not in json.dumps(page) for value in ["SYSTEM_NEVER", "DELTA_NEVER"])
        assert page["next_cursor"] == source.stat().st_size


@pytest.mark.parametrize("field,value", [("schema", 2), ("schema", True),
    ("id", "../outside"), ("archive_id", "../outside"), ("start_at", "")])
def test_live_marker_corruption_is_refused_without_rewriting(tmp_path, request, field, value):
    """A corrupt current marker never creates guessed session evidence."""
    _, items, stores, app = _fixture(tmp_path)
    marker, source = _live(request, stores[0])
    document = {**marker, field: value}
    path = source.parent / "live.json"
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    with TestClient(app) as client:
        _login(client)
        assert client.get(_url(items[0])).status_code == 503
        assert client.get(_url(items[0], "/" + marker["id"])).status_code == 503
    assert path.read_bytes() == raw


# PUBLIC CONTRACT TESTS
@pytest.mark.parametrize("role", ["admin", "developer"])
def test_recorded_session_replay_visibility_and_pagination(tmp_path, role):
    """Both authorized roles see recorded text without system or duplicates."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0])
    records = [
        {"type": "message_end", "message": {"role": "system", "content": "SYSTEM_NEVER"}},
        {"type": "message_end", "message": {"role": "user", "content": "literal prompt"}},
        {"type": "message_end", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "answer"}, {"type": "thinking", "thinking": "reason"}],
            "usage": {"input": 7, "output": 9, "cost": {"total": 1.23}}}},
        {"type": "tool_execution_start", "toolCallId": "x", "toolName": "bash",
         "args": {"command": "echo API_KEY=fake-key-EXACT"}},
        {"type": "tool_execution_end", "toolCallId": "x", "toolName": "bash", "isError": False,
         "result": {"content": [{"type": "text", "text": "API_KEY=fake-key-EXACT"}]}},
        {"type": "message_update", "assistantMessageEvent": {"delta": "DELTA_NEVER"}},
        {"type": "agent_end", "messages": [{"content": "DUPLICATE_NEVER"}]},
    ]
    with (folder / "output.jsonl").open("ab") as handle:
        handle.write(b"".join((json.dumps(x) + "\n").encode() for x in records))
    if role == "developer":
        user = app.state.web_store.create_user("dev", "test-password", "developer")
        app.state.web_store.set_memberships(user["id"], ["alpha"])
    with TestClient(app) as client:
        _login(client) if role == "admin" else _login(client, "dev", "test-password")
        response = client.get(_url(items[0]))
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        session = response.json()["sessions"][0]
        assert session["id"] == folder.name and session["stage"] == "build"
        assert session["attempt"] == 2 and session["start_at"] is None
        assert session["outcome"] == "succeeded"
        cursor, all_items = 0, []
        while True:
            response = client.get(_url(items[0], f"/{folder.name}?cursor={cursor}&limit=1"))
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "no-store"
            page = response.json()
            assert 0 <= len(page["items"]) <= 1
            all_items.extend(part for item in page["items"] for part in item.get("parts", [item]))
            if page["next_cursor"] is None:
                break
            assert page["next_cursor"] > cursor
            cursor = page["next_cursor"]
        rendered = json.dumps(all_items)
        assert all(kind in {x["kind"] for x in all_items} for kind in
                   ["prompt", "assistant", "reasoning", "tool_call", "tool_result",
                    "turn", "usage"])
        assert "fake-key-EXACT" in rendered
        assert all(value not in rendered for value in
                   ["SYSTEM_NEVER", "DELTA_NEVER", "DUPLICATE_NEVER"])
        assert ("cost" in json.dumps(all_items[-3:])) is (role == "admin")
        assert client.get(_url(items[1])).status_code == (200 if role == "admin" else 404)
        output = client.get(f"/api/v1/jobs/{items[0].project_id}/same/executor-output")
        assert output.status_code == 200


def test_bad_lines_bounds_and_incomplete_tail_are_isolated(tmp_path):
    """Bad records are notices, retained text stays exact and unfinished data waits."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], records=[])
    source = folder / "output.jsonl"
    source.write_bytes(b'not json\n\xff\n' + b'x' * (300 * 1024) + b'\n' +
                       b'{"adore_omitted_bytes":100}\n{"adore_output_truncated":true}\n' +
                       b'{"type":"adore_malformed_record","bytes":13,"head":"bad"}\n' +
                       b'{"type":"message_end","message":{"role":"system",'
                       b'"role":"user","content":"DUPLICATE_SYSTEM_NEVER"}}\n' +
                       (json.dumps({"type": "message_end", "message": {"role": "user",
                        "content": "🙂" * 10000}}) + "\n").encode() + b'{"unfinished":')
    with TestClient(app) as client:
        _login(client)
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code == 200, response.text
        data = response.json()
        assert len([x for x in data["items"] if x["kind"] == "notice"]) == 6
        assert "DUPLICATE_SYSTEM_NEVER" not in response.text
        item = next(x for x in data["items"] if x["kind"] == "prompt")
        assert item["text"] == "🙂" * 10000
        assert "unfinished" not in response.text


def test_collision_suffix_ten_and_huge_physical_record_are_bounded(tmp_path):
    """Valid decimal collision suffixes survive and huge sources emit a notice."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], name="build-attempt-2-attempt1-10", records=[])
    with (folder / "output.jsonl").open("wb") as source:
        source.truncate(65 * 1024 * 1024)
    with TestClient(app) as client:
        _login(client)
        assert client.get(_url(items[0])).json()["sessions"][0]["id"] == folder.name
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code == 200
        assert response.json()["items"][0]["kind"] == "notice"
        assert response.json()["next_cursor"] is None


def test_huge_usage_integer_is_a_notice_and_later_text_survives(tmp_path):
    """An untrusted cost cannot overflow float conversion or stop the page."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], records=[
        {"type": "message_end", "message": {"role": "assistant", "content": [],
         "usage": {"input": 1, "cost": {"total": 10**400}}}},
        {"type": "message_end", "message": {"role": "user", "content": "after corruption"}},
    ])
    with TestClient(app) as client:
        _login(client)
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code == 200
        assert [x["kind"] for x in response.json()["items"]] == ["notice", "prompt"]
        assert response.json()["items"][1]["text"] == "after corruption"


@pytest.mark.parametrize("field,value", [("created_at", ""), ("exit_code", True),
    ("archive_stem", "../outside"), ("timed_out", "false")])
def test_corrupt_archive_metadata_fails_closed(tmp_path, field, value):
    """Metadata corruption is refused, never guessed or automatically repaired."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0], records=[])
    path = folder / "meta.json"
    meta = json.loads(path.read_text())
    meta[field] = value
    raw = json.dumps(meta).encode()
    path.write_bytes(raw)
    with TestClient(app) as client:
        _login(client)
        assert client.get(_url(items[0])).status_code == 503
        assert client.get(_url(items[0], f"/{folder.name}")).status_code == 503
    assert path.read_bytes() == raw


@pytest.mark.parametrize("suffix", ["unknown", "build-attempt-2-attempt1?cursor=1",
    "build-attempt-2-attempt1?cursor=-1", "build-attempt-2-attempt1?cursor=9999999",
    "build-attempt-2-attempt1?limit=201", "build-attempt-2-attempt1?limit=0",
    "%2E%2E", "build-attempt-2-attempt1?cursor=abc"])
def test_invalid_session_requests_fail_closed(tmp_path, suffix):
    """Untrusted identities and non-line cursors never expose raw files."""
    _, items, stores, app = _fixture(tmp_path)
    _archive(stores[0])
    with TestClient(app) as client:
        assert client.get(_url(items[0])).status_code == 401
        _login(client)
        response = client.get(_url(items[0], "/" + suffix))
        assert response.status_code in {400, 404, 422, 503}, response.text


@pytest.mark.parametrize("target", ["archive", "attempt", "output", "meta", "hardlink"])
def test_linked_session_sources_fail_closed(tmp_path, target):
    """Session reads share the existing no-link identity boundary."""
    _, items, stores, app = _fixture(tmp_path)
    folder = _archive(stores[0])
    path = {"archive": folder.parent, "attempt": folder, "output": folder / "output.jsonl",
            "meta": folder / "meta.json", "hardlink": folder / "output.jsonl"}[target]
    external = tmp_path / "external"
    path.rename(external)
    try:
        if target == "hardlink":
            path.hardlink_to(external)
        else:
            path.symlink_to(external, target_is_directory=external.is_dir())
    except OSError:
        pytest.skip("host does not permit symlinks")
    with TestClient(app) as client:
        _login(client)
        response = client.get(_url(items[0], f"/{folder.name}"))
        assert response.status_code in {404, 503}, response.text
