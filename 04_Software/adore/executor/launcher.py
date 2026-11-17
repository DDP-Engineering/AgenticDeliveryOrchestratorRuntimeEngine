"""Pi executor launcher (ADORE's only coding agent) and its factory."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from adore.branding import (
    CONTAINER_PI_AGENT_DIR,
    CONTAINER_PI_CLI,
    CONTAINER_PI_GUARD,
    CONTAINER_PI_WEB_ACCESS,
    DEFAULT_QUESTIONS_FILE,
)
from adore.execution import SHELL_HEADER, ExecutionPaths, redact_output
from adore.executor import pi_rpc
from adore.executor.base import ExecTarget, Executor, GateRun
from adore.executor.conversation import PiConversation
from adore.instructions import InstructionDelivery
from adore.isolation import IsolationError
from adore.pi_installation import GUARD, ManagedPi
from adore.pi_providers import pi_provider
from adore.prompts import PromptCatalog
from adore.state import StateStore
from adore.util import CommandResult, read_agent_file, utc_now_iso, write_agent_file

_MAX_RESULT_BYTES = 1024 * 1024

GATE_SCRIPT = "gate.sh"
OUTPUT_FILE = "output.jsonl"
STDERR_FILE = "stderr.log"
ARCHIVE_DIR = "archive"
#: io-dir file holding the endpoint models.json before it is copied into Pi's
#: agent directory (outside the worktree, so the executor never commits it).
MODELS_FILE = "pi-models.json"
#: io-dir file holding pi-web-access's web-search.json before it is copied into
#: Pi's agent directory; it names the search provider and never a key.
WEB_SEARCH_FILE = "pi-web-search.json"
_ARCHIVE_STEM_RE = re.compile(r"[^A-Za-z0-9_.-]+")

#: Pi RPC launch flags: RPC mode, no session file, no project trust, and none
#: of the account's personal skills, extensions, templates, themes or MCP.
PI_RPC_FLAGS = (
    "--mode", "rpc", "--no-session", "--no-approve", "--no-skills", "--no-extensions",
    "--no-prompt-templates", "--no-themes", "--no-mcp",
)
#: Pi environment for a container launch: the ADORE-owned agent directory
#: replaces the personal ~/.pi/agent; no network calls of Pi's own.
PI_RPC_ENV = {
    "PI_CODING_AGENT_DIR": CONTAINER_PI_AGENT_DIR,
    "PI_OFFLINE": "1",
    "PI_TELEMETRY": "0",
    "PI_SKIP_VERSION_CHECK": "1",
}
#: Seconds a cancelled Pi gate needs to abort and end before the conductor
#: stops the container instead.
PI_CANCEL_GRACE_SECONDS = (
    pi_rpc.ABORT_GRACE_SECONDS + pi_rpc.EXIT_GRACE_SECONDS + pi_rpc.KILL_GRACE_SECONDS + 5.0
)


def _archive_directories(path: Path) -> None:
    """Refuse linked/reparse archive destinations before any archive write."""
    for parent in (path, *path.parents):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISDIR(info.st_mode) or parent.is_symlink()
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise IsolationError("archive destination is linked or not a directory")


def _archive_recording(source: Path, destination: Path) -> None:
    """
    Copy one quiescent literal RPC recording within its producer bound.
    source: Run-owned recording after RPC shutdown.
    destination: New immutable archive output file.
    Raises IsolationError: Linked, oversized or changing recording.
    """
    def identity(path: Path):
        """Refuse linked/reparse files and parents before inspecting bytes."""
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise IsolationError("RPC recording is linked or not a regular file")
        for parent in path.parents:
            if (parent.is_symlink()
                    or getattr(parent.lstat(), "st_file_attributes", 0) & 0x400):
                raise IsolationError("RPC recording parent is linked")
        return info

    def signature(info):
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

    _archive_directories(destination.parent)
    before = identity(source)
    # The producer may add its small truncation notice after reaching the cap.
    bound = pi_rpc.PERSIST_TOTAL_BYTES + 128
    if before.st_size > bound:
        raise IsolationError("RPC recording exceeds its byte bound")
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        if signature(os.fstat(incoming.fileno())) != signature(before):
            raise IsolationError("RPC recording identity changed")
        remaining = before.st_size
        while remaining:
            data = incoming.read(min(65536, remaining))
            if not data:
                raise IsolationError("RPC recording changed while archiving")
            outgoing.write(data)
            remaining -= len(data)
        if (signature(os.fstat(incoming.fileno())) != signature(before)
                or signature(identity(source)) != signature(before)):
            raise IsolationError("RPC recording changed while archiving")


class PiExecutor(Executor):
    """
    Pi (@earendil-works/pi-coding-agent) executor launcher.
    On a container target (one with a `spawn` seam) every gate runs
             one bounded `pi --mode rpc` process from the image's
             pinned installation, driven by `pi_rpc`: fixed argv, prompt over
             stdin, `abort` on the stage timeout or a cancel. The account's
             personal Pi resources are off (`PI_RPC_FLAGS`, an ADORE-owned
             agent directory) and ADORE's guard extension is loaded with `-e`,
             so it blocks `git push` and forge CLIs without project trust; the
             boundary stays that no forge credential is in the container. The
             process command is fixed by ADORE.

             `--provider` names the Pi provider (`openai` for a ChatGPT
             subscription, `adore-endpoint` for an OpenAI-compatible
             endpoint) and `--model` the model id. For an endpoint the
             generated models.json is written to the io dir and copied into
             the ADORE-owned agent directory through the exec seam before Pi
             starts; a failed copy fails the gate without starting Pi.

             With internet access on and a web search chosen, the pinned
             pi-web-access extension is loaded with `-e` and its
             web-search.json (provider, no curator, tools always active; keys
             only from the environment) is placed the same way. With internet
             access off nothing web-related is loaded and the system prompt
             says that only the model provider is reachable.

             A native target lends owned process pipes from its managed Node
             and Pi installation and writes generated configuration to its
             fresh agent directory.

             Usage is summed over the assistant turns, cached prompt tokens
             included in input. Pi's cost is an executor estimate, not
             provider-billed cost, so no cost is reported; administrator price
             rules may estimate from the captured tokens.
    """

    def __init__(
        self,
        model: str,
        questions_file: str = DEFAULT_QUESTIONS_FILE,
        *,
        provider: str = "",
        models: dict | None = None,
        internet: bool = False,
        web_search: str = "exa",
        thinking: str = "",
        prompts: PromptCatalog | None = None,
    ) -> None:
        """
        Configure Pi from the [executor] section.
        model: Model id within the provider.
        questions_file: Clarification questions filename.
        provider: `[executor] provider` ("" keeps a bare `--model`).
        models: Endpoint models.json document, or None.
        internet: `[executor] internet`.
        web_search: `[executor.web] search` (used while internet is on).
        thinking: Optional validated Pi thinking level.
        prompts: Shared eager catalog, or load all shipped prompts here.
        Raises PromptError: A shipped prompt resource is invalid or unavailable.
        """
        self.prompts = prompts if prompts is not None else PromptCatalog()
        self.provider = pi_provider(provider) if provider else ""
        self.model_id = model
        self.models = models
        self.internet = internet
        self.web_search = web_search
        self.thinking = thinking
        self.questions_file = questions_file

    def run_gate(
        self,
        execute: ExecTarget,
        worktree: str | Path,
        io_dir: str | Path,
        prompt: str,
        *,
        timeout: float | None = None,
        archive_stem: str = "",
        cancel: Callable[[], bool] | None = None,
        instructions: InstructionDelivery | None = None,
        context_key: str = "",
        package_secrets: dict[str, str] | None = None,
    ) -> GateRun:
        """
        Run one gate through Pi's RPC mode in a container or on the server.
        Clears stale questions and streams, writes a descriptive
                    gate.sh (no shell runs; the prompt never enters it), runs
                    `pi_rpc`, archives the bounded evidence and reads the
                    questions file. Targets without an RPC process seam are refused before
                    writing files or running commands.
        execute: Exec seam bound to the run's target.
        worktree: HOST path of the run's worktree.
        io_dir: HOST path of the run's io exchange dir.
        prompt: Gate instruction, sent over stdin.
        timeout: Stage wall-clock bound.
        archive_stem: Optional immutable archive name stem.
        instructions: Optional acknowledgement-bound instruction handoff.
        context_key: Current ticket fingerprint, saved only on prompt receipt.
        cancel: Cancellation check polled during the run.
        package_secrets: Known credentials for bounded package-job retention.
        Returns: A GateRun: exit 0 completed, 1 failed, 124 timed out,
                    130 cancelled, otherwise a protocol failure.
        """
        spawn = getattr(execute, "spawn", None)
        native = getattr(execute, "pi_session", None)
        if spawn is None and native is None:
            return GateRun(exit_code=126, stderr="Pi requires an RPC process target")
        worktree = Path(worktree)
        io_dir = Path(io_dir)
        io_dir.mkdir(parents=True, exist_ok=True)
        job_gate = re.fullmatch(
            r"(frame|specify|design|build|validate)-attempt-[1-9][0-9]*", archive_stem)
        conversation = (PiConversation(io_dir, worktree,
                                       getattr(execute, "paths", ExecutionPaths()),
                                       context_key=context_key)
                        if job_gate else None)
        questions_path = worktree / self.questions_file
        questions_path.unlink(missing_ok=True)
        output_path = io_dir / OUTPUT_FILE
        stderr_path = io_dir / STDERR_FILE
        output_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)
        web = self.internet and self.web_search != "none"
        argv_builder = execute.pi_argv if native is not None else pi_rpc_argv
        notice = (self.prompts.render("system/server-internet.md")
                  if native is not None else "" if self.internet else
                  self.prompts.render("system/internet-off.md"))
        argv = argv_builder(self.model_id, self.provider, web=web, notice=notice,
                            thinking=self.thinking)
        if conversation is not None:
            argv.remove("--no-session")
            argv.extend(["--session", conversation.backend_file,
                         "--session-dir", conversation.backend_file.rsplit("/", 1)[0]])
        placements = []
        if self.models is not None:
            placements.append((MODELS_FILE, "models.json", self.models,
                               "Pi models.json could not be placed in the agent directory: "))
        if web:
            placements.append((WEB_SEARCH_FILE, "web-search.json", web_search_json(self.web_search),
                               "The web search configuration could not be placed in Pi's "
                               "agent directory: "))
        for source, target, document, reason in placements if native is None else ():
            placed = self._place_file(execute, io_dir, source, target, document, reason)
            if placed is not None:
                return placed
        # The agent can write this directory: every host write here refuses a
        # planted link instead of overwriting whatever it points at.
        write_agent_file(io_dir / GATE_SCRIPT, (
            SHELL_HEADER
            + "# Pi RPC launch; no shell is executed.\n"
            + "# The stage prompt is sent over stdin.\n"
            + "# argv: " + json.dumps(argv, ensure_ascii=True) + "\n"
            + ("# env: " + json.dumps(PI_RPC_ENV) + "\n" if native is None else "")
        ).encode("utf-8"))
        target_redact = getattr(execute, "redact", lambda text: text)
        def redact(text: str) -> str:
            """Mask binding credentials and package-job secrets before persistence."""
            return redact_output(target_redact(text), package_secrets or {})

        with ExitStack() as stack:
            # Publish ownership only after stale output is gone; keep it through
            # archive completion so the web can resolve the exact handoff.
            live_path = io_dir / "live.json"
            live_path.unlink(missing_ok=True)
            if job_gate:
                stack.enter_context(StateStore(io_dir).run_lock("agent-session"))
                base = f"{archive_stem}-attempt1"
                archive_id, suffix = base, 2
                while (io_dir / ARCHIVE_DIR / archive_id).exists():
                    archive_id, suffix = f"{base}-{suffix}", suffix + 1
                write_agent_file(output_path, b"")
                marker = {"schema": 1, "id": "live-" + uuid4().hex,
                          "archive_id": archive_id, "start_at": utc_now_iso()}
                temporary = io_dir / (marker["id"] + ".tmp")
                stack.callback(temporary.unlink, missing_ok=True)
                stack.callback(live_path.unlink, missing_ok=True)
                temporary.write_text(json.dumps(marker) + "\n", encoding="utf-8")
                temporary.replace(live_path)
            def spawn_rpc(command, env):
                """Use the native scope or container exec for the same RPC client."""
                if native is not None:
                    return stack.enter_context(native(command, placements))
                return spawn(command, env=env)

            result = pi_rpc.run_pi_rpc(
                spawn_rpc, argv, dict(PI_RPC_ENV), prompt,
                timeout=timeout, cancelled=cancel, instructions=instructions,
                output_path=output_path, stderr_path=stderr_path,
                redact=redact,
                conversation=conversation,
            )
            if result.timed_out:
                settle = getattr(execute, "settle_timeout", None)
                if settle is not None:
                    settle()
            # Session stdout is the bounded literal RPC recording. Package
            # retention continues to sanitize operational tails and stderr,
            # but must never rewrite the transcript that live readers consume.
            output = result.output
            if package_secrets is not None:
                output = pi_rpc.bounded_text(redact(output))
                self._retain_package_output(stderr_path, package_secrets)
            evidence = pi_rpc.bounded_text("\n".join(
                redact(part) for part in (result.message, *result.notes, result.stderr) if part))
            artifacts: list[str] = []
            if archive_stem:
                launch = CommandResult(argv=argv, exit_code=result.exit_code,
                                       timed_out=result.timed_out)
                try:
                    artifacts.append(str(self._archive_launch(
                        io_dir, archive_stem, launch, evidence, timeout,
                        output_path.is_file(), stderr_path.is_file(),
                        output_file=output_path)))
                except OSError as exc:
                    return GateRun(exit_code=result.exit_code or 1, output=output,
                                   stderr=(evidence + f"\narchive write failed: {exc}").strip(),
                                   timed_out=result.timed_out)
            if native is not None:
                questions = execute.read_output(questions_path, optional=True)
            elif package_secrets is not None:
                questions = self._retain_package_output(
                    questions_path, package_secrets, redact=target_redact)
            else:
                questions = target_redact(self._read(questions_path))
            usage = result.usage
            reported = usage.complete and usage.turns > 0
            return GateRun(
                exit_code=result.exit_code,
                has_questions=questions_path.is_file(),
                questions=questions,
                output=output,
                stderr=evidence,
                timed_out=result.timed_out,
                tokens_in=usage.tokens_in if reported else 0,
                tokens_out=usage.tokens_out if reported else 0,
                cache_read_tokens=usage.cache_read if reported else None,
                cache_write_tokens=usage.cache_write if reported else None,
                tokens_reported=reported,
                cost_usd=0.0,
                cost_reported=False,
                artifact_dirs=artifacts,
                diagnostics=result.diagnostics,
            )

    def _place_file(self, execute: ExecTarget, io_dir: Path, source: str, target: str,
                    document: dict, reason: str) -> GateRun | None:
        """
        Put a generated Pi configuration file into Pi's agent directory.
        The endpoint models.json and pi-web-access's web-search.json
                    hold no key (only `$ADORE_ENDPOINT_API_KEY`, a placeholder or
                    a provider name); each is written host-side into the io dir
                    and copied inside the container, so a kept-warm container
                    gets the current file for every gate.
        execute: Exec seam bound to the run's target.
        io_dir: HOST path of the run's io exchange dir.
        source: File name in the io dir.
        target: File name in the agent directory.
        document: JSON document to write.
        reason: Evidence prefix when the copy fails.
        Returns: None when placed; a failed GateRun otherwise.
        """
        paths = getattr(execute, "paths", ExecutionPaths())
        write_agent_file(
            io_dir / source,
            (json.dumps(document, ensure_ascii=True, indent=1) + "\n").encode("utf-8"))
        result = execute(["cp", f"{paths.io}/{source}",
                          f"{CONTAINER_PI_AGENT_DIR}/{target}"], timeout=60)
        if result.ok:
            return None
        detail = (result.stderr or result.stdout or "").strip()[:500]
        return GateRun(exit_code=result.exit_code or 1, timed_out=result.timed_out,
                       stderr=(reason + detail).strip())

    def cancel_grace_seconds(self, execute: ExecTarget) -> float | None:
        """
        An owned Pi RPC launch aborts itself on cancellation.
        execute: Backend target whose RPC process is controlled.
        Returns: Shared native/container abort-and-exit grace.
        """
        return PI_CANCEL_GRACE_SECONDS

    def _archive_launch(
        self,
        io_dir: Path,
        archive_stem: str,
        result,
        stderr: str,
        timeout: float | None,
        output_present: bool,
        stderr_present: bool,
        *,
        output_file: Path,
    ) -> Path:
        """
        Copy one completed launch's live exchange files to archive.
        Creates a unique directory under `io/archive`. Empty
                    output/stderr files are still written so absence is visible
                    in meta.json without making operators guess whether a file
                    was skipped.
        io_dir: Host io exchange directory.
        archive_stem: Base name supplied by the orchestrator.
        result: Container exec result.
        stderr: Captured stderr stream or fallback stderr.
        timeout: Launch timeout.
        output_present: Whether live output.jsonl existed.
        stderr_present: Whether live stderr.log existed.
        output_file: Mandatory bounded literal RPC recording.
        Returns: Archive directory path.
        Raises OSError: When any archive write fails.
        Raises IsolationError: Unsafe or changing literal RPC recording.
        """
        archive_root = io_dir / ARCHIVE_DIR
        _archive_directories(archive_root)
        archive_root.mkdir(parents=True, exist_ok=True)
        # One physical launch per gate now that nothing relaunches, so the
        # suffix is constant; the collision loop below still disambiguates a
        # reused stem.
        base_name = f"{self._safe_archive_stem(archive_stem)}-attempt1"
        archive_dir = archive_root / base_name
        suffix = 2
        while archive_dir.exists():
            archive_dir = archive_root / f"{base_name}-{suffix}"
            suffix += 1
        archive_dir.mkdir()
        _archive_directories(archive_dir)
        # Read as an agent-writable file: a planted link must not copy its target.
        script = read_agent_file(io_dir / GATE_SCRIPT, _MAX_RESULT_BYTES)
        (archive_dir / GATE_SCRIPT).write_bytes(script or b"")
        _archive_recording(output_file, archive_dir / OUTPUT_FILE)
        (archive_dir / STDERR_FILE).write_bytes(stderr.encode("utf-8"))
        meta = {
            "created_at": utc_now_iso(),
            "archive_stem": archive_stem,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "argv": result.argv,
            "timeout": timeout,
            "output_file_present": output_present,
            "stderr_file_present": stderr_present,
        }
        (archive_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return archive_dir


    @staticmethod
    def _safe_archive_stem(value: str) -> str:
        """
        Make an archive stem safe as one directory name segment.
        value: Raw stem.
        Returns: Filesystem-safe non-empty stem.
        """
        safe = _ARCHIVE_STEM_RE.sub("-", value.strip()).strip(".-")
        return safe or "launch"


    def _retain_package_output(
        self, path: Path, secrets: dict[str, str], *,
        redact: Callable[[str], str] | None = None,
    ) -> str:
        """
        Bound/redact retained package output without following linked files.
        path: Owned gate output file.
        secrets: Known model credential values, retained in memory only.
        redact: Optional binding redactor applied before the byte cap and write.
        Returns: Bounded sanitized operational text; RPC owns usage accounting.
        Raises IsolationError: Linked, changed or unreadable output.
        Note: Live writes during a gate still use the existing gate transport.
        """
        try:
            before = path.lstat()
        except FileNotFoundError:
            return ""
        if not stat.S_ISREG(before.st_mode) or any(p.is_symlink() for p in path.parents):
            raise IsolationError("package output is linked or not a regular file")
        try:
            with path.open("r+b") as handle:
                opened = os.fstat(handle.fileno())
                if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                    raise IsolationError("package output identity changed")
                limit = 65536
                # Read beyond the boundary to redact a credential crossing it.
                overlap = max((len(value.encode()) for value in secrets.values()), default=0)
                raw = handle.read(limit + overlap + 1)
                truncated = opened.st_size > limit
                decoded = raw.decode("utf-8", errors="replace")
                output = redact_output(decoded, secrets)
                if redact is not None:
                    output = redact_output(redact(output), secrets)
                if truncated:
                    output = output.encode()[:limit - 32].decode("utf-8", errors="ignore")
                    output += "\n[ADORE output truncated]\n"
                handle.seek(0)
                handle.write(output.encode())
                handle.truncate()
            return output
        except (OSError, ValueError, TypeError, AttributeError, OverflowError) as exc:
            raise IsolationError("package output retention failed") from exc


    @staticmethod
    def _read(path: Path) -> str:
        """
        Read a result file, tolerating its absence.
        path: File written by the gate script (or the executor).
        Returns: The content, or "" when missing, unreadable or not a plain
                    regular file. A link is never followed: the conductor reads
                    the same file again and reports it as unusable.
        """
        try:
            content = read_agent_file(path, _MAX_RESULT_BYTES)
        except OSError:
            return ""
        return "" if content is None else content.decode("utf-8", errors="replace")


def web_search_json(search: str) -> dict:
    """
    pi-web-access's web-search.json for an internet-on run.
    The provider is fixed (no automatic fallback chain), the
                curator workflow is off for a headless run and the tools are
                always active. Brave and Tavily read their key from
                BRAVE_API_KEY / TAVILY_API_KEY in the environment.
    search: `[executor.web] search` (exa, brave or tavily).
    Returns: The document.
    """
    return {"provider": search, "workflow": "none", "toolActivation": "eager"}


def pi_rpc_argv(model: str, provider: str = "", *, web: bool = False, thinking: str = "",
                notice: str = "", installation: ManagedPi | None = None,
                windows: bool = False) -> list[str]:
    """
    Fixed command line of a managed Pi RPC launch.
    model: Model id within the provider.
    provider: Pi provider id ("" passes only `--model`).
    thinking: Optional validated Pi thinking level.
    web: Load the pinned pi-web-access extension (internet on only).
    notice: Text appended to Pi's system prompt ("" appends nothing);
                a stage with internet off passes the loaded offline notice.
    Returns: `node <cli.js> --mode rpc ... -e <guard> [-e <pi-web-access>]
                [--append-system-prompt <notice>] [--provider <p>] --model <model>`.
    """
    if installation is None:
        node, cli, guard, extension = (
            "node", CONTAINER_PI_CLI, CONTAINER_PI_GUARD, CONTAINER_PI_WEB_ACCESS
        )
    else:
        node, cli, guard, extension = map(
            str, (installation.node, installation.cli, GUARD, installation.web)
        )
    return [node, cli, *PI_RPC_FLAGS, "-e", guard,
            *(["--tools", "read,powershell,edit,write"] if windows else []),
            *(["-e", extension] if web else []),
            *(["--append-system-prompt", notice] if notice else []),
            *(["--provider", provider] if provider else []), "--model", model,
            *(["--thinking", thinking] if thinking else [])]


def build_executor(
    model: str,
    questions_file: str = DEFAULT_QUESTIONS_FILE,
    *,
    provider: str = "",
    models: dict | None = None,
    internet: bool = False,
    web_search: str = "exa",
    thinking: str = "",
    prompts: PromptCatalog | None = None,
) -> Executor:
    """
    Construct the Pi launcher (config selection point).
    Pi is the only implementation of the executor interface.
    model: Model id within the provider.
    questions_file: Clarification questions filename.
    provider: `[executor] provider`.
    models: Endpoint models.json for `provider = "custom"`, else None.
    internet: `[executor] internet`.
    web_search: `[executor.web] search`.
    thinking: Optional validated Pi thinking level.
    prompts: Optional conductor-owned catalog shared with the launcher.
    Returns: A PiExecutor.
    """
    return PiExecutor(model, questions_file,
                      provider=provider, models=models, internet=internet,
                      web_search=web_search, thinking=thinking, prompts=prompts)
