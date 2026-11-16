"""Durable instruction inbox and acknowledgement trust-boundary contracts."""

import importlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

from tests.execution_records import execution_record


def api():
    """Require the inbox surface before importing the implementation."""
    assert importlib.util.find_spec("adore.instructions") is not None, (
        "durable instruction inbox missing"
    )
    return importlib.import_module("adore.instructions")


def inbox(tmp_path):
    """Construct an inbox inside an existing isolated run directory."""
    root = tmp_path / "runs" / "run-one"
    root.mkdir(parents=True)
    return api().InstructionInbox(root)


def test_atomic_inbox_reopens_literal_text_and_ack_receipt(tmp_path):
    """Enqueue and acknowledgement survive process-local object replacement."""
    box = inbox(tmp_path)
    text = "  $name\n<script>password=SYNTHETIC</script> 🙂\n"
    row = box.enqueue({"id": 7, "username": "operator"}, text, "now")
    reopened = api().InstructionInbox(box.run_dir)
    rows, notices = reopened.read()
    assert not notices and rows == [row]
    assert row["text"] == text and row["delivery"] is None
    delivered = reopened.acknowledge(row["id"], "steer")
    assert delivered["delivery"]["how"] == "steer"
    before = (box.directory / (row["id"] + ".json")).read_bytes()
    assert reopened.acknowledge(row["id"], "steer") == delivered
    assert (box.directory / (row["id"] + ".json")).read_bytes() == before
    assert not list(box.directory.glob("*.tmp"))


@pytest.mark.parametrize(
    "text,mode",
    [
        ("", "now"),
        ("x" * 4001, "now"),
        ("a\0b", "after"),
        (1, "now"),
        ("ok", "later"),
        ("\ud800", "now"),
    ],
)
def test_invalid_instruction_never_writes(tmp_path, text, mode):
    """Bad human text is rejected without an inbox side effect."""
    box = inbox(tmp_path)
    with pytest.raises(api().InstructionError):
        box.enqueue({"id": 7, "username": "operator"}, text, mode)
    assert box.read() == ([], [])


@pytest.mark.parametrize(
    "mutation",
    ["json", "schema", "id", "oversize", "hardlink", "author-surrogate", "duplicate-key"],
)
def test_corrupt_record_is_preserved_and_valid_neighbor_remains_sendable(tmp_path, mutation):
    """Untrusted files produce value-free notices and never pending commands."""
    box = inbox(tmp_path)
    row = box.enqueue({"id": 7, "username": "operator"}, "PRIVATE_INVALID", "now")
    path = box.directory / (row["id"] + ".json")
    value = json.loads(path.read_text())
    if mutation == "json":
        path.write_text("{PRIVATE_INVALID")
    elif mutation == "schema":
        value["schema"] = 9
        path.write_text(json.dumps(value))
    elif mutation == "id":
        value["id"] = "f" * 32
        path.write_text(json.dumps(value))
    elif mutation == "oversize":
        path.write_bytes(b"PRIVATE_INVALID" * 5000)
    elif mutation == "hardlink":
        os.link(path, tmp_path / "linked.json")
    elif mutation == "author-surrogate":
        value["user"]["username"] = "\ud800"
        path.write_text(json.dumps(value))
    else:
        path.write_text(json.dumps(value).replace('"schema": 1', '"schema": 2, "schema": 1'))
    before = path.read_bytes()
    good = box.enqueue({"id": 7, "username": "operator"}, "valid", "after")
    rows, notices = box.read()
    assert rows == [good] and notices
    assert "PRIVATE_INVALID" not in str(notices)
    assert path.read_bytes() == before


def test_inbox_capacity_and_atomic_write_failure_preserve_records(tmp_path, monkeypatch):
    """Capacity and replacement failure never publish a partial instruction."""
    box = inbox(tmp_path)
    monkeypatch.setattr(api(), "MAX_INSTRUCTIONS", 1)
    row = box.enqueue({"id": 7, "username": "operator"}, "one", "now")
    with pytest.raises(api().InstructionError, match="instruction_limit"):
        box.enqueue({"id": 7, "username": "operator"}, "two", "now")
    monkeypatch.setattr(api(), "MAX_INSTRUCTIONS", 256)

    def refused(*args):
        raise PermissionError("replace refused")

    monkeypatch.setattr(api().os, "replace", refused)
    with pytest.raises(api().InstructionError):
        box.enqueue({"id": 7, "username": "operator"}, "two", "now")
    assert box.read() == ([row], [])


def test_delivery_snapshot_and_live_commands_require_matching_acknowledgements(tmp_path):
    """Prompt snapshot and live arrivals use literal wrappers and real receipts."""
    from adore.prompts import PromptCatalog

    box = inbox(tmp_path)
    first = box.enqueue({"id": 7, "username": "operator"}, "  $text\n🙂", "after")
    received = []
    delivery = api().InstructionDelivery(
        box, PromptCatalog(), on_delivery=lambda: received.append(True)
    )
    assert first["text"] in delivery.suffix and "operator" in delivery.suffix
    assert box.read()[0][0]["delivery"] is None
    now = box.enqueue({"id": 7, "username": "operator"}, "now", "now")
    after = box.enqueue({"id": 7, "username": "operator"}, "after", "after")
    commands = delivery.poll()
    assert [c["type"] for c in commands] == ["steer", "follow_up"]
    assert delivery.poll() == []
    delivery.command_response(commands[0]["id"], "follow_up", True)
    delivery.command_response(commands[0]["id"], "steer", False)
    assert box.read()[0][1]["delivery"] is None
    delivery.command_response(commands[1]["id"], "follow_up", True)
    delivery.prompt_accepted()
    rows = {row["id"]: row for row in box.read()[0]}
    assert rows[first["id"]]["delivery"]["how"] == "prompt"
    assert rows[after["id"]]["delivery"]["how"] == "follow_up"
    assert rows[now["id"]]["delivery"] is None
    assert rows[now["id"]]["last_error"] == "pi_rejected"
    assert len(received) == 2


@pytest.mark.parametrize("location", ["ancestor", "inbox", "lock-directory", "lock-file"])
def test_inbox_refuses_reparse_ancestors_and_lock_paths(tmp_path, monkeypatch, location):
    """Public writes refuse reparse points before publishing instruction files."""
    box = inbox(tmp_path)
    box.directory.mkdir()
    box.store.locks_root.mkdir()
    lock = box.store.locks_root / "run-instruction-inbox.lock"
    lock.touch()
    target = {"ancestor": tmp_path.parent, "inbox": box.directory,
              "lock-directory": box.store.locks_root, "lock-file": lock}[location]
    original = Path.lstat
    class Reparse:
        """Inject the Windows reparse attribute at the filesystem boundary."""
        st_file_attributes = 0x400
        def __init__(self, info):
            self.info = info
        def __getattr__(self, name):
            return getattr(self.info, name)
    def inspected(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        return Reparse(info) if path.absolute() == target.absolute() else info
    monkeypatch.setattr(Path, "lstat", inspected)
    with pytest.raises(api().InstructionError, match="unsafe_instruction_path"):
        box.enqueue({"id": 7, "username": "operator"}, "never sent", "now")
    assert not list(box.directory.glob("*.json"))


def test_inbox_refuses_hardlinked_lock_without_mutating_it(tmp_path):
    """A foreign lock inode cannot be used as an instruction writer lock."""
    box = inbox(tmp_path)
    box.store.locks_root.mkdir()
    lock = box.store.locks_root / "run-instruction-inbox.lock"
    lock.write_bytes(b"FOREIGN")
    os.link(lock, tmp_path / "foreign.lock")
    with pytest.raises(api().InstructionError):
        box.enqueue({"id": 7, "username": "operator"}, "never sent", "after")
    assert lock.read_bytes() == b"FOREIGN"


def test_profile_owned_inbox_uses_shared_lock_directory_with_all_ancestors(tmp_path):
    """The normal profile layout creates guarded external lock storage without setup."""
    from adore.profiles import ProfileStore
    from adore.state import RunState, StateStore

    profiles = ProfileStore(tmp_path / "home")
    item = profiles.create("alpha")
    store = StateStore(profiles.default_store_root(item.name))
    run = RunState(run_id="one", ticket_iid=1, lifecycle="working", execution=execution_record())
    store.save(run)
    box = api().InstructionInbox(store.run_dir(run.run_id))
    row = box.enqueue({"id": 7, "username": "operator"}, "Profile instruction", "now")
    assert box.read()[0] == [row]
    assert box.store.locks_root.is_dir()
    assert box.store.locks_root != box.run_dir / "locks"
