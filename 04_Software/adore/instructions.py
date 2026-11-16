"""Bounded durable instructions shared by the web process and Pi owner."""

from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from uuid import uuid4

from adore.prompts import PromptCatalog
from adore.state import LockHeldError, StateError, StateStore
from adore.util import utc_now_iso

MAX_INSTRUCTIONS = 256
MAX_RECORD_BYTES = 32 * 1024
_ID = re.compile(r"[0-9a-f]{32}")
_FIELDS = {"schema", "id", "user", "created_at", "mode", "text", "delivery", "last_error"}


class InstructionError(StateError):
    """A bounded inbox operation cannot be completed safely."""


def validate_instruction(text: object, mode: object) -> None:
    """
    Refuse invalid human text/mode without normalizing literal data.
    text: Unicode text containing 1..4000 characters without NUL.
    mode: Exactly now or after.
    Raises InstructionError: Invalid or non-UTF-8-encodable input.
    """
    if not isinstance(text, str) or not 1 <= len(text) <= 4000 or "\0" in text:
        raise InstructionError("invalid_instruction")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise InstructionError("invalid_instruction") from exc
    if mode not in ("now", "after"):
        raise InstructionError("invalid_instruction")


def _physical(path: Path, *, directory: bool) -> os.stat_result:
    """Inspect one physical directory or single-link regular file."""
    info = path.lstat()
    if (
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & 0x400
        or (
            not stat.S_ISDIR(info.st_mode)
            if directory
            else not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
        )
    ):
        raise InstructionError("unsafe_instruction_path")
    return info


def _directories(path: Path, *, create: bool = False) -> None:
    """Inspect every ancestor before optionally creating the next physical directory."""
    for ancestor in reversed((path.absolute(), *path.absolute().parents)):
        try:
            _physical(ancestor, directory=True)
        except FileNotFoundError:
            if not create:
                raise
            ancestor.mkdir(exist_ok=True)
            _physical(ancestor, directory=True)


def _unique(pairs: list[tuple[str, object]]) -> dict:
    """Refuse duplicate JSON keys rather than guessing which value is authoritative."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise InstructionError("duplicate_instruction_key")
        result[key] = value
    return result


def _time(value: object) -> bool:
    """Validate a timezone-aware persisted timestamp."""
    if not isinstance(value, str) or len(value) > 50:
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def _validate(row: object, identity: str) -> dict:
    """Validate the one current record shape before any text is sent."""
    if not isinstance(row, dict) or set(row) != _FIELDS:
        raise InstructionError("instruction_schema; delete the affected instruction file")
    if type(row["schema"]) is not int or row["schema"] != 1 or row["id"] != identity:
        raise InstructionError("instruction_schema; delete the affected instruction file")
    user = row["user"]
    if (
        not isinstance(user, dict)
        or set(user) != {"id", "username"}
        or type(user["id"]) is not int
        or user["id"] < 1
        or not isinstance(user["username"], str)
        or not 1 <= len(user["username"]) <= 200
        or any(ord(c) < 32 for c in user["username"])
    ):
        raise InstructionError("invalid_instruction_user")
    try:
        user["username"].encode("utf-8")
    except UnicodeEncodeError as exc:
        raise InstructionError("invalid_instruction_user") from exc
    validate_instruction(row["text"], row["mode"])
    if not _time(row["created_at"]) or row["last_error"] not in ("", "pi_rejected"):
        raise InstructionError("invalid_instruction_metadata")
    delivery = row["delivery"]
    if delivery is not None and (
        not isinstance(delivery, dict)
        or set(delivery) != {"at", "how"}
        or not _time(delivery["at"])
        or delivery["how"] not in ("prompt", "steer", "follow_up")
    ):
        raise InstructionError("invalid_instruction_delivery")
    return row


class InstructionInbox:
    """Store at most 256 physical instruction files in an existing run."""

    def __init__(self, run_dir: Path) -> None:
        """Bind the run directory without creating or resetting stored data."""
        self.run_dir = Path(run_dir)
        self.directory = self.run_dir / "instructions"
        self.store = StateStore(self.run_dir)

    def _directory(self, *, create: bool = False) -> bool:
        """Validate containment before opening or creating the inbox."""
        _directories(self.run_dir)
        if create:
            self.directory.mkdir(exist_ok=True)
        try:
            _physical(self.directory, directory=True)
        except FileNotFoundError:
            return False
        return True

    @contextmanager
    def _locked(self):
        """Serialize short atomic mutations without taking the conductor lock."""
        try:
            self._directory()
            _directories(self.store.locks_root, create=True)
            lock_path = self.store.locks_root / "run-instruction-inbox.lock"
            if lock_path.exists() or lock_path.is_symlink():
                _physical(lock_path, directory=False)
            with self.store.run_lock("instruction-inbox"):
                self._directory()
                _directories(self.store.locks_root)
                _physical(lock_path, directory=False)
                yield
        except LockHeldError as exc:
            raise InstructionError("instruction_busy") from exc
        except OSError as exc:
            raise InstructionError("instruction_storage_unavailable") from exc

    def _paths(self) -> list[Path]:
        """Bound enumeration, including unexpected and crash-retained files."""
        paths = []
        with os.scandir(self.directory) as entries:
            for entry in entries:
                if len(paths) >= MAX_INSTRUCTIONS:
                    raise InstructionError("instruction_limit")
                paths.append(Path(entry.path))
        return paths

    def _read(self, path: Path) -> dict:
        """Read one bounded immutable snapshot with link/identity checks."""
        if not _ID.fullmatch(path.stem) or path.suffix != ".json":
            raise InstructionError("invalid_instruction_filename")
        before = _physical(path, directory=False)
        if before.st_size > MAX_RECORD_BYTES:
            raise InstructionError("instruction_record_oversize")
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        )
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(MAX_RECORD_BYTES + 1)
            after = os.fstat(handle.fileno())
        current = _physical(path, directory=False)
        if (
            opened.st_nlink != 1
            or len(raw) > MAX_RECORD_BYTES
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            or (opened.st_ino, opened.st_size, opened.st_mtime_ns)
            != (after.st_ino, after.st_size, after.st_mtime_ns)
            or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise InstructionError("instruction_file_changed")
        return _validate(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique), path.stem)

    def read(self) -> tuple[list[dict], list[str]]:
        """
        Return valid records and value-free refusals; never repair files.
        Returns: Sorted literal records and notices for unreadable neighbors.
        Raises InstructionError: Unavailable/unsafe directory or capacity violation.
        """
        rows, notices = [], []
        try:
            if not self._directory():
                return rows, notices
            for path in self._paths():
                try:
                    rows.append(self._read(path))
                except (OSError, ValueError, RecursionError, InstructionError):
                    name = (
                        path.name
                        if re.fullmatch(r"[0-9a-f]{32}\.json", path.name)
                        else "unknown file"
                    )
                    notices.append(f"{name}: instruction refused; delete this file to remove it")
        except OSError as exc:
            raise InstructionError("instruction_storage_unavailable") from exc
        return sorted(rows, key=lambda row: (row["created_at"], row["id"])), notices

    def _write(self, row: dict) -> None:
        """Flush a complete same-directory temporary before atomic replacement."""
        self._directory(create=True)
        raw = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        if len(raw) > MAX_RECORD_BYTES:
            raise InstructionError("instruction_record_oversize")
        descriptor, temporary = tempfile.mkstemp(
            prefix=".instruction-", suffix=".tmp", dir=self.directory
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            self._directory()
            os.replace(temporary, self.directory / (row["id"] + ".json"))
        finally:
            Path(temporary).unlink(missing_ok=True)

    def enqueue(self, user: dict, text: str, mode: str) -> dict:
        """
        Atomically enqueue literal validated text with its authenticated author.
        user: Authenticated id and username (extra principal fields ignored).
        text: Exact instruction, 1..4000 characters without NUL.
        mode: now or after.
        Returns: Complete queued record.
        Raises InstructionError: Invalid input, full inbox or unavailable storage.
        """
        validate_instruction(text, mode)
        identity = uuid4().hex
        row = _validate(
            {
                "schema": 1,
                "id": identity,
                "user": {"id": user.get("id"), "username": user.get("username")},
                "created_at": datetime.now(UTC).isoformat(),
                "mode": mode,
                "text": text,
                "delivery": None,
                "last_error": "",
            },
            identity,
        )
        with self._locked():
            if self._directory() and len(self._paths()) >= MAX_INSTRUCTIONS:
                raise InstructionError("instruction_limit")
            self._write(row)
        return row

    def acknowledge(self, identity: str, how: str) -> dict:
        """
        Persist an idempotent receipt only after a matching Pi success.
        identity: Exact UUID-hex instruction identity.
        how: prompt, steer or follow_up.
        Returns: Existing or newly delivered record.
        Raises InstructionError: Invalid identity, receipt or unreadable source.
        """
        return self._update(identity, how=how)

    def reject(self, identity: str) -> None:
        """Keep rejected text queued with a closed value failure reason."""
        self._update(identity)

    def _update(self, identity: str, *, how: str = "") -> dict:
        """Refuse corrupt data rather than overwriting it during receipt updates."""
        if (
            not isinstance(identity, str)
            or not _ID.fullmatch(identity)
            or how not in ("", "prompt", "steer", "follow_up")
        ):
            raise InstructionError("invalid_instruction_receipt")
        with self._locked():
            try:
                row = self._read(self.directory / (identity + ".json"))
            except (ValueError, RecursionError) as exc:
                raise InstructionError("invalid_instruction_record") from exc
            if row["delivery"] is None:
                row["last_error"] = "" if how else "pi_rejected"
                if how:
                    row["delivery"] = {"at": utc_now_iso(), "how": how}
                self._write(row)
            return row


class InstructionDelivery:
    """Snapshot fallback instructions and match live commands to acknowledgements."""

    def __init__(
        self,
        inbox: InstructionInbox,
        prompts: PromptCatalog,
        *,
        on_delivery: Callable[[], None] = lambda: None,
        report: Callable[[str], None] = lambda text: None,
    ) -> None:
        """Capture pending prompt text; construction never acknowledges delivery."""
        self.inbox, self.prompts = inbox, prompts
        self.on_delivery, self.report = on_delivery, report
        self.reported: set[str] = set()
        self.sent: dict[str, tuple[str, str]] = {}
        self.initial = [row for row in self._rows() if row["delivery"] is None]

    def _rows(self) -> list[dict]:
        """Report each local refusal once per launch without leaking stored values."""
        try:
            rows, notices = self.inbox.read()
        except InstructionError as exc:
            rows, notices = [], [str(exc)]
        for notice in notices:
            if notice not in self.reported:
                self.reported.add(notice)
                self.report(notice)
        return rows

    def _wrapped(self, row: dict) -> str:
        """Insert authorized literal text once through the shipped prompt loader."""
        return self.prompts.render(
            "live/instruction.md", user=row["user"]["username"], text=row["text"]
        )

    @property
    def suffix(self) -> str:
        """Literal wrappers for insertion after the human thread."""
        return "\n\n".join(self._wrapped(row) for row in self.initial)

    def _receipt(self, identity: str, how: str) -> None:
        """Persist receipt before notifying the conductor; preserve failures."""
        try:
            self.inbox.acknowledge(identity, how)
        except InstructionError as exc:
            self.report(f"instruction receipt not saved: {exc}")
            return
        self.on_delivery()

    def prompt_accepted(self) -> None:
        """Acknowledge only the snapshot actually included in the accepted prompt."""
        for row in self.initial:
            self._receipt(row["id"], "prompt")

    def poll(self) -> list[dict]:
        """Produce each new live command once, for the existing stdin owner only."""
        initial = {row["id"] for row in self.initial}
        commands = []
        for row in self._rows():
            identity = row["id"]
            key = "adore-instruction-" + identity
            if row["delivery"] is not None or identity in initial or key in self.sent:
                continue
            command = "steer" if row["mode"] == "now" else "follow_up"
            self.sent[key] = identity, command
            commands.append({"id": key, "type": command, "message": self._wrapped(row)})
        return commands

    def command_response(self, identity: str, command: str, success: bool) -> None:
        """Accept only exact id/command responses; rejected text remains queued."""
        pending = self.sent.get(identity) if isinstance(identity, str) else None
        if pending is None or pending[1] != command:
            return
        row_id, _ = pending
        if success:
            self._receipt(row_id, command)
        else:
            try:
                self.inbox.reject(row_id)
            except InstructionError as exc:
                self.report(f"instruction rejection not saved: {exc}")
