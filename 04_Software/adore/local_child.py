"""Trusted native launcher with a durable-ownership release barrier."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main(path: str, *, streaming: bool = False) -> int:
    """
    Start one native argv command only after the parent's ownership receipt.
    path: Parent-owned immutable launch envelope.
    streaming: Forward the parent's stdin pipe for RPC.
    Returns: Authoritative command exit status.
    Raises ValueError: Invalid trusted transport.
    """
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(envelope) != {"argv", "cwd", "release", "scope"}:
        raise ValueError("invalid native launch envelope")
    if (
        not isinstance(envelope["argv"], list)
        or not envelope["argv"]
        or any(not isinstance(arg, str) or "\x00" in arg for arg in envelope["argv"])
    ):
        raise ValueError("invalid native argv")
    scope = envelope["scope"]
    if scope["kind"] == "linux-cgroup":
        (Path(scope["path"]) / "cgroup.procs").write_text(str(os.getpid()), encoding="ascii")
    elif scope["kind"] != "windows-job":
        raise ValueError("unsupported native scope")
    release = Path(envelope["release"])
    deadline = time.monotonic() + 30
    while True:
        if (Path(path).parent / "cancel").exists():
            return 125
        if release.is_file():
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("native launch was never released")
        time.sleep(0.02)
    if scope["kind"] == "linux-cgroup":
        os.chdir(envelope["cwd"])
        os.execve(envelope["argv"][0], envelope["argv"], dict(os.environ))
    # The Windows supervisor remains a member of the non-breakaway Job.
    # This standalone -I launcher cannot import ADORE's package helpers.
    # Windows CREATE_NO_WINDOW needs explicit standard handles: implicit
    # inheritance can exit cleanly while discarding both captured streams.
    # These are the supervisor's parent-owned pipes, drained by its controller.
    result = subprocess.run(  # noqa: S603 - native argv resolved by the parent
        envelope["argv"], cwd=envelope["cwd"], check=False, creationflags=0x08000000,
        stdin=sys.stdin if streaming else subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], streaming=sys.argv[2:] == ["rpc"]))
