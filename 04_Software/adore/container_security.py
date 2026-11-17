"""Common runtime policy for containers with agent environment administration."""

from collections.abc import Callable, Sequence
import json
from pathlib import Path

from adore.util import CommandRunner

ASSETS = Path(__file__).parent / "container_assets"


def environment_security_args(
    runtime: Sequence[str], command: str, runner: CommandRunner,
    source_path: Callable[[Path], str], run_args: Sequence[str],
) -> list[str]:
    """Keep seccomp/AppArmor active while allowing nested application sandboxes.

    AppArmor hosts must have the bundled adore-executor policy installed by an
    administrator. Missing policies fail at container creation; never fall back
    to unconfined execution. Only newly created agent containers use this policy.
    """
    from adore.isolation import IsolationError

    expression = "{{json .Host.Security}}" if command in {"podman", "podman-remote"} else (
        "{{json .SecurityOptions}}")
    result = runner([*runtime, "info", "--format", expression], timeout=15)
    if not result.ok or result.timed_out:
        raise IsolationError("cannot inspect container runtime security",
                             result.argv, result.stderr)
    try:
        security = json.loads(result.stdout)
        if command in {"podman", "podman-remote"}:
            if not isinstance(security, dict) or any(
                type(security.get(key)) is not bool for key in ("apparmorEnabled", "seccompEnabled")
            ):
                raise ValueError("invalid Podman security information")
            apparmor, seccomp = security["apparmorEnabled"], security["seccompEnabled"]
        else:
            if not isinstance(security, list) or not all(isinstance(x, str) for x in security):
                raise ValueError("invalid Docker security information")
            apparmor = any(x.split(",")[0] == "name=apparmor" for x in security)
            seccomp = any(x.split(",")[0] == "name=seccomp" for x in security)
        if not seccomp:
            raise ValueError("runtime has no active seccomp support")
    except (ValueError, TypeError) as exc:
        raise IsolationError(f"container environment security unavailable: {exc}") from exc
    policy = ASSETS / "executor-seccomp.json"
    if not policy.is_file():
        raise IsolationError("executor seccomp policy missing; reinstall ADORE")
    args = [f"--security-opt=seccomp={source_path(policy)}"]
    if apparmor:
        args.append("--security-opt=apparmor=adore-executor")
    if not any(x.split("=", 1)[0] == "--shm-size" for x in run_args):
        args.append("--shm-size=512m")
    return args
