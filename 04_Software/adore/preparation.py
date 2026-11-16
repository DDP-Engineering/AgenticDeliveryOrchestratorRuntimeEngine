"""Closed, versioned preparation grammar and reviewed execution plans."""

from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import TYPE_CHECKING

from adore.branding import EXECUTOR_BASE_IMAGE
from adore.util import CommandRunner, run_command

if TYPE_CHECKING:
    from adore.config import Config

PLAN_SCHEMA = 1
MAX_RECIPE_BYTES = 65536
MAX_STEPS = 32
MAX_SCRIPT_BYTES = 8192
MAX_SCRIPT_LINES = 256
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_JOB = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,63}\Z")
_IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:@-]{0,255}\Z")
_COERCIBLE = re.compile(r"(?i)(?:true|false|yes|no|on|off|null|~|[-+]?\d.*|\.inf|\.nan)\Z")



class PreparationError(RuntimeError):
    """Recipe/source/plan input cannot safely authorize execution."""




def _digest(value: dict) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class _RecipeReader:
    """Fixed-depth reader; each schema node admits only named children."""

    def __init__(self, source: str) -> None:
        self.lines = source.splitlines()
        self.index = 0

    def peek(self) -> tuple[int, str] | None:
        """Skip structural comments/blank lines and inspect indentation."""
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if not line.strip() or line.lstrip().startswith("#"):
                self.index += 1
                continue
            return len(line) - len(line.lstrip(" ")), line.lstrip(" ")
        return None

    def scalar(self, raw: str, field: str, indent: int) -> str:
        """Decode explicit text, with literal blocks only for run bodies."""
        if raw in {"|", "|-"} and field.endswith(".run"):
            lines = []
            while self.index < len(self.lines):
                line = self.lines[self.index]
                if line.strip() and len(line) - len(line.lstrip(" ")) < indent + 2:
                    break
                if line.strip() and not line.startswith(" " * (indent + 2)):
                    raise PreparationError(f"{field}: invalid literal indentation")
                lines.append(line[indent + 2 :] if line.strip() else "")
                self.index += 1
            value = "\n".join(lines).rstrip("\n")
            return value + ("\n" if raw == "|" else "")
        try:
            if raw.startswith('"'):
                value, end = json.JSONDecoder().raw_decode(raw)
                if (
                    not isinstance(value, str)
                    or raw[end:].strip()
                    and not raw[end:].lstrip().startswith("#")
                ):
                    raise ValueError
            elif raw.startswith("'"):
                match = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", raw)
                if not match:
                    raise ValueError
                value = match[1].replace("''", "'")
            else:
                value = re.split(r"\s+#", raw, maxsplit=1)[0].rstrip()
                if (
                    not value
                    or value[0] in "!&*[{>|%@`"
                    or value in {"---", "..."}
                    or ": " in value
                    or _COERCIBLE.fullmatch(value)
                ):
                    raise ValueError
            if not value.strip() or any(ord(c) < 32 and c not in "\n\t" for c in value):
                raise ValueError
            value.encode("utf-8")
            return value
        except (ValueError, TypeError, UnicodeError) as exc:
            raise PreparationError(f"{field}: expected unambiguous text") from exc

    def mapping(self, indent: int, field: str, kind: str, first: str | None = None) -> dict:
        """Read only root/jobs/job/container/step schema mappings."""
        result: dict = {}
        allowed = {
            "root": {"name", "jobs"},
            "job": {"container", "steps"},
            "container": {"image"},
            "step": {"name", "run"},
        }
        while first is not None or (item := self.peek()) is not None:
            if first is not None:
                text = first
                first = None
            else:
                if item[0] < indent:
                    break
                if item[0] != indent:
                    raise PreparationError(
                        f"{field}: unsupported indentation at line {self.index + 1}"
                    )
                text = item[1]
                self.index += 1
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?", text)
            if not match:
                raise PreparationError(f"{field}: expected field at line {self.index}")
            key, raw = match[1], (match[2] or "").strip()
            if raw.startswith("#"):
                raw = ""
            child = f"{field}.{key}"
            if key in result:
                raise PreparationError(f"{child}: duplicate field")
            if kind != "jobs" and key not in allowed[kind]:
                raise PreparationError(f"{child}: unsupported field")
            if kind == "jobs" and not _JOB.fullmatch(key):
                raise PreparationError(f"{child}: invalid job ID")
            if kind == "jobs" or key in {"jobs", "container", "steps"}:
                if raw:
                    raise PreparationError(f"{child}: expected block structure")
                if key == "steps" and kind == "job":
                    result[key] = self.steps(indent + 2, child)
                else:
                    child_kind = "job" if kind == "jobs" else key
                    result[key] = self.mapping(indent + 2, child, child_kind)
            else:
                result[key] = self.scalar(raw, child, indent)
        required = {
            "root": {"jobs"},
            "jobs": set(),
            "job": {"container", "steps"},
            "container": {"image"},
            "step": {"run"},
        }[kind]
        if not result or required - result.keys():
            raise PreparationError(
                f"{field}: missing required fields {sorted(required - result.keys())}"
            )
        if kind == "jobs" and len(result) > 16:
            raise PreparationError(f"{field}: too many jobs (maximum 16)")
        return result

    def steps(self, indent: int, field: str) -> list[dict]:
        """Read sequential steps with optional name and required run."""
        result = []
        while (item := self.peek()) is not None and item[0] >= indent:
            if item[0] != indent or not item[1].startswith("- "):
                raise PreparationError(f"{field}: expected step list")
            self.index += 1
            result.append(self.mapping(indent + 2, f"{field}[{len(result)}]", "step", item[1][2:]))
            if len(result) > MAX_STEPS:
                raise PreparationError(f"{field}: too many steps")
        if not result:
            raise PreparationError(f"{field}: steps must be nonempty")
        return result




def parse_selection(selection: str) -> tuple[str, str, str]:
    """
    Decode a reviewed path#job@full-commit profile selection.
    selection: Operator-selected text.
    Returns: Relative path, job ID and exact commit.
    Raises PreparationError: For unsafe or incomplete selection.
    """
    if not isinstance(selection, str) or len(selection) > 512:
        raise PreparationError("selection: expected bounded text")
    path, marker, target = selection.partition("#")
    job, at, revision = target.partition("@")
    parts = PurePosixPath(path).parts
    if (
        not marker
        or not at
        or not _JOB.fullmatch(job)
        or not _COMMIT.fullmatch(revision)
        or not path
        or path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(ord(c) < 32 for c in path)
        or any(p in {"", ".", "..", ".git", ".adore", ".agentic"} for p in path.split("/"))
        or not parts
        or not path.endswith((".yml", ".yaml"))
    ):
        raise PreparationError("selection: requires safe relative .yml/.yaml path#job@full commit")
    return path, job, revision


def parse_recipe(source: str, job: str) -> dict:
    """
    Normalize a complete version-1 recipe, validating every job.
    source: UTF-8 recipe text with original newlines.
    job: Explicit selected job ID.
    Returns: Name, image and ordered normalized steps.
    Raises PreparationError: For malformed or unsupported input.
    """
    if not isinstance(source, str):
        raise PreparationError("recipe: expected UTF-8 text")
    try:
        source_size = len(source.encode("utf-8"))
    except UnicodeError as exc:
        raise PreparationError("recipe: expected UTF-8 text") from exc
    if (
        source_size > MAX_RECIPE_BYTES
        or "\ufffd" in source
        or "${{" in source
        or any(ord(c) < 32 and c not in "\r\n" for c in source)
    ):
        raise PreparationError("recipe: invalid text, size, controls or expressions")
    reader = _RecipeReader(source)
    data = reader.mapping(0, "recipe", "root")
    count = 0
    lines = 0
    for key, definition in data["jobs"].items():
        if not _IMAGE.fullmatch(definition["container"]["image"]):
            raise PreparationError(f"jobs.{key}.container.image: invalid image reference")
        for index, step in enumerate(definition["steps"]):
            script = step["run"]
            if not script.strip() or len(script.encode()) > MAX_SCRIPT_BYTES:
                raise PreparationError(f"jobs.{key}.steps[{index}].run: empty or too large")
            count += 1
            lines += len(script.splitlines())
    if count > MAX_STEPS or lines > MAX_SCRIPT_LINES:
        raise PreparationError("recipe.steps: exceeds step or script-line bound")
    if job not in data["jobs"]:
        raise PreparationError(f"jobs.{job}: selected job is absent")
    selected = data["jobs"][job]
    return {
        "name": data.get("name", ""),
        "image": selected["container"]["image"],
        "steps": [
            {"name": s.get("name", f"Step {i + 1}"), "run": s["run"]}
            for i, s in enumerate(selected["steps"])
        ],
    }


def resolve_plan(
    config: Config, *, runner: CommandRunner = run_command, expected_revision: str | None = None
) -> dict:
    """
    Resolve one complete non-secret execution plan without installing.
    config: Typed operator profile.
    runner: Injectable argv command runner for exact Git source reads.
    expected_revision: Optional run target commit for stale review checks.
    Returns: Versioned fingerprinted plan, including source text for immutable evidence.
    Raises PreparationError: For source, image, revision or backend conflicts.
    """
    if config.execution.backend not in {"container", "local"}:
        raise PreparationError("execution.backend: expected container/local")
    if config.execution.backend == "local" and config.execution.preparation:
        raise PreparationError("local execution cannot run a container preparation recipe")
    plan = {
        "schema": PLAN_SCHEMA,
        "backend": config.execution.backend,
        "selection": config.execution.preparation,
        "image": config.container.image if config.execution.backend == "container" else "",
        "image_source": "profile" if config.execution.backend == "container" else "local",
        "source_sha256": "",
        "source": "",
        "steps": [],
        "policy": execution_policy(config),
    }
    if config.execution.preparation:
        path, job, revision = parse_selection(config.execution.preparation)
        if expected_revision is not None and expected_revision != revision:
            raise PreparationError("execution.preparation: reviewed revision is stale for target")

        def git(*argv: str) -> str:
            """Read bounded Git source metadata through injected commands."""
            result = runner(["git", "-C", str(Path(config.worktree.repo_path)), *argv], timeout=30)
            if not result.ok or result.timed_out:
                raise PreparationError("execution.preparation: Git source read failed")
            return result.stdout

        commit = git("rev-parse", "--verify", f"{revision}^{{commit}}").strip()
        if commit != revision:
            raise PreparationError("execution.preparation: invalid commit response")
        tree = git("ls-tree", "-z", revision, "--", path)
        match = re.fullmatch(
            r"(100644|100755) blob ([0-9a-f]{40}|[0-9a-f]{64})\t" + re.escape(path) + r"\x00", tree
        )
        if not match:
            raise PreparationError("execution.preparation: source must be a regular owned Git blob")
        size = git("cat-file", "-s", match[2]).strip()
        if not size.isascii() or not size.isdigit() or not 0 < int(size) <= MAX_RECIPE_BYTES:
            raise PreparationError("execution.preparation: invalid source size")
        source = git("cat-file", "blob", match[2])
        if len(source.encode()) != int(size):
            raise PreparationError("execution.preparation: source bytes differ from Git size")
        recipe = parse_recipe(source, job)
        declared = config.raw.get("container", {})
        explicit_image = "image" in declared or config.container.image != EXECUTOR_BASE_IMAGE
        if explicit_image and config.container.image and config.container.image != recipe["image"]:
            raise PreparationError("container.image: conflicts with recipe image")
        plan.update(
            image=recipe["image"],
            image_source="recipe",
            steps=recipe["steps"],
            source=source,
            source_sha256=sha256(source.encode()).hexdigest(),
        )
    if plan["backend"] == "container" and (
        not isinstance(plan["image"], str) or not _IMAGE.fullmatch(plan["image"])
    ):
        raise PreparationError("container.image: invalid effective image")
    plan["fingerprint"] = _digest(plan)
    return plan


def execution_policy(config: Config) -> dict:
    """
    Snapshot non-secret settings that can change execution identity.
    config: Operator profile.
    Returns: Closed non-secret policy used for drift checks and future image apply.
    """
    policy = {
        "execution": asdict(config.execution),
        "worktree": asdict(config.worktree),
        "target_branch": config.delivery.target_branch,
        "aegis_python": config.workflow.aegis_python,
        "container": {
            key: value
            for key, value in asdict(config.container).items()
            if key
            not in {
                "image",
                "keep_parked",
                "parked_ttl_mode",
                "parked_ttl_seconds",
                "parked_ttl_polls",
            }
        },
        "executor": asdict(config.executor),
    }
    if config.container.system_packages is not True:
        policy["container"].pop("system_packages", None)
    if config.execution.backend == "local":
        from adore.local_execution import local_policy
        from adore.local_process import LocalExecutionError

        try:
            policy.pop("container")
            policy["local"] = local_policy(config)
        except (LocalExecutionError, OSError, ValueError, KeyError) as exc:
            raise PreparationError("local execution environment cannot be resolved") from exc
    return policy


def validate_plan(plan: object) -> dict:
    """
    Validate closed persisted plan and its complete fingerprint.
    plan: Untrusted persisted mapping.
    Returns: The trusted plan.
    Raises PreparationError: For corrupt, unknown or inconsistent data.
    """
    keys = {
        "schema",
        "backend",
        "selection",
        "image",
        "image_source",
        "source_sha256",
        "source",
        "steps",
        "policy",
        "fingerprint",
    }
    if not isinstance(plan, dict) or set(plan) != keys:
        raise PreparationError("plan: invalid closed structure")
    if (
        type(plan["schema"]) is not int
        or plan["schema"] != PLAN_SCHEMA
        or plan["backend"] not in {"container", "local"}
    ):
        raise PreparationError("plan: unsupported schema/backend")
    if not isinstance(plan["fingerprint"], str) or plan["fingerprint"] != _digest(
        {k: v for k, v in plan.items() if k != "fingerprint"}
    ):
        raise PreparationError("plan: fingerprint mismatch")
    if any(
        not isinstance(plan[key], str)
        for key in ("selection", "source", "source_sha256", "image_source")
    ):
        raise PreparationError("plan: text fields must be strings")
    from adore.config import Config

    template = execution_policy(Config())
    if (isinstance(plan.get("policy"), dict)
            and isinstance(plan["policy"].get("container"), dict)
            and "system_packages" in plan["policy"]["container"]):
        if plan["policy"]["container"]["system_packages"] is not True:
            raise PreparationError("plan.policy.container.system_packages: expected true")
        template["container"]["system_packages"] = True
    if plan["backend"] == "local":
        template.pop("container")
        template["local"] = {
            "settings": asdict(Config().local), "host": "", "account": "", "system": "",
            "environment_sha256": "", "executable": "", "executable_sha256": "",
        }

    def typed(value: object, example: object, field: str) -> None:
        """Check closed policy types before accepting crash-state authority."""
        if type(value) is not type(example):
            raise PreparationError(f"plan.policy.{field}: invalid type")
        if isinstance(example, dict):
            if field == "container.runtime_env":
                if any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
                    raise PreparationError("plan.policy: invalid environment")
            else:
                if set(value) != set(example):
                    raise PreparationError("plan.policy: unsupported fields")
                for key in example:
                    typed(value[key], example[key], f"{field}.{key}" if field else key)
        elif isinstance(example, list) and any(not isinstance(v, str) for v in value):
            raise PreparationError("plan.policy: invalid list")

    typed(plan["policy"], template, "")
    policy = plan["policy"]["execution"]
    if policy["backend"] != plan["backend"] or policy["preparation"] != plan["selection"]:
        raise PreparationError("plan.policy: selection/backend mismatch")
    for key, maximum in (
        ("preparation_step_timeout_seconds", 1800),
        ("preparation_total_timeout_seconds", 3600),
        ("preparation_max_attempts", 3),
    ):
        if not 1 <= policy[key] <= maximum:
            raise PreparationError("plan.policy: invalid preparation bound")
    if plan["selection"]:
        _, job, _ = parse_selection(plan["selection"])
        recipe = parse_recipe(plan["source"], job)
        if (
            recipe["steps"] != plan["steps"]
            or recipe["image"] != plan["image"]
            or sha256(plan["source"].encode()).hexdigest() != plan["source_sha256"]
            or plan["image_source"] != "recipe"
        ):
            raise PreparationError("plan: source/steps/image mismatch")
    elif (
        plan["steps"]
        or plan["source"]
        or plan["source_sha256"]
        or plan["image_source"] != ("local" if plan["backend"] == "local" else "profile")
    ):
        raise PreparationError("plan: source without a preparation recipe")
    if plan["backend"] == "local":
        local = plan["policy"]["local"]
        if (plan["selection"] or plan["image"] or local["system"] not in {"Windows", "Linux"}
                or not local["account"] or not local["executable"]
                or any(not re.fullmatch(r"[0-9a-f]{64}", local[key])
                       for key in ("host", "environment_sha256", "executable_sha256"))):
            raise PreparationError("plan: invalid native local identity")
    elif not isinstance(plan["image"], str) or not _IMAGE.fullmatch(plan["image"]):
        raise PreparationError("plan: invalid image")
    return plan


def preview_plan(config: Config, *, runner: CommandRunner = run_command) -> dict:
    """
    Resolve a plan against the currently selected local target revision.
    config: Validated operator profile.
    runner: Injectable Git command boundary, without setup or fetch.
    Returns: Complete reviewed plan for CLI, GUI and image-apply integration.
    Raises PreparationError: For stale review or malformed target output.
    """
    target = None
    if config.execution.preparation:
        result = runner(
            [
                "git",
                "-C",
                str(Path(config.worktree.repo_path)),
                "rev-parse",
                "--verify",
                f"origin/{config.delivery.target_branch}^{{commit}}",
            ],
            timeout=30,
        )
        target = result.stdout.strip()
        if not result.ok or result.timed_out or not _COMMIT.fullmatch(target):
            raise PreparationError("execution.preparation: target revision unavailable or corrupt")
    return resolve_plan(config, runner=runner, expected_revision=target)


def effective_probe_config(config: Config, *, runner: CommandRunner = run_command) -> Config:
    """
    Bind read-only readiness to the same reviewed effective image.
    config: Typed project snapshot.
    runner: Bounded injectable Git runner.
    Returns: Snapshot with normalized image; no preparation commands execute.
    Raises PreparationError: For stale or unsupported source.
    """
    if not config.execution.preparation:
        return config
    plan = preview_plan(config, runner=runner)
    return replace(config, container=replace(config.container, image=plan["image"]))


def public_plan(plan: dict) -> dict:
    """
    Return one closed review projection without raw source/configuration.
    plan: Complete validated immutable plan.
    Returns: Normalized image/source/step review shared by CLI and GUI.
    """
    return {
        key: plan[key]
        for key in (
            "schema",
            "backend",
            "selection",
            "image",
            "image_source",
            "source_sha256",
            "fingerprint",
            "steps",
        )
    }
