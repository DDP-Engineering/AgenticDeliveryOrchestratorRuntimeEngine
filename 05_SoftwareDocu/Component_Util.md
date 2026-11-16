# Component: Util (`adore/util.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/util.py`.

## 1. Purpose

Shared low-level helpers every other ADORE component builds on: running
external commands safely, parsing human-readable durations, and producing
consistent UTC timestamps. It supplies the common runner/error model and child process policy used by
forge, Git, runtime, worker and native executor launches.

## 2. Responsibilities

- Run external commands without a shell, capturing all output
  (`run_command`). Windows `az`/`az.cmd`/`az.bat` uses its selected installation's
  Python and `-IBm azure.cli`, bypassing cmd expansion. Original arguments and
  `CommandResult.argv` stay intact; missing or unsupported layouts fail closed.
  See [Azure CLI bridge](Component_Azure_CLI.md).
- Define the injectable `CommandRunner` protocol so every consumer can be
  unit-tested offline with a fake runner.
- Parse duration strings ("90s", "30m", "24h", "7d", bare seconds) to
  seconds (`parse_duration`).
- Produce compact UTC ISO-8601 timestamps (`utc_now_iso`) and parse them
  back to aware datetimes (`iso_to_datetime`).
- Evaluate `[polling] quiet_hours` windows, including windows crossing
  midnight (`in_quiet_hours`).
- Load dotenv-style secret files (`load_env_file`; missing file = `{}`).
- Remove directory trees that contain read-only entries
  (`force_rmtree` - Windows git objects are read-only and plain
  `shutil.rmtree` fails on them; missing paths are fine, so teardown and
  `adore cleanup` stay idempotent; uses `onexc` on Python 3.12+ and `onerror`
  below).
- Probe whether a process id is running (`process_alive`), cross-platform and
  fail-closed (any uncertainty reports alive), so the state store can reclaim
  only a provably-dead crashed lock owner. On Windows it uses an OpenProcess
  probe rather than `os.kill`, which there can terminate the target.

Explicitly not owned: interpreting command output (each caller parses its own
JSON/URLs) and retry/backoff policy (the orchestrator's concern).

## 3. Implementation Overview

- `CommandResult` (dataclass): argv, exit_code, stdout, stderr, timed_out,
  raw_stdout, `stdout_bytes` and `ok` properties. Raw stdout is omitted from repr.
- `CommandRunner` (Protocol): the callable contract; `run_command` is the
  concrete default, tests inject fakes.
- `run_command` never raises for command failure - errors are reported
  through the exit code so callers decide deterministically:
  - `127` - executable not found,
  - `124` - wall-clock timeout (subprocess killed),
  - otherwise the command's own exit code.
- `run_command` retains exact captured stdout bytes, including partial timeout
  output. Its separate display text is decoded as UTF-8 with replacement. Pi RPC uses a separate owned-pipe client with strict protocol
  decoding and bounded conversation/operational evidence.
- Default command timeout: 600 s (`DEFAULT_COMMAND_TIMEOUT`).

## 4. Dependencies

- Internal: `azure_cli.windows_azure_argv` (stdlib-only host launcher resolution).
- External: Python standard library only (`subprocess`, `re`, `datetime`,
  `shutil`, `os`, `sys`, and `ctypes` on Windows for `process_alive`).

## 5. Inputs And Outputs

- Inputs: an argv list (no shell), optional cwd/timeout/env; duration strings.
- Outputs: `CommandResult` values; integer seconds; timestamp strings like
  `2026-07-02T14:02:33Z`.

## 6. Data Contracts

- Exit-code convention (127 missing binary / 124 timeout / native otherwise)
  is relied upon by the forge adapters and, later, the executor launcher and
  isolation helpers.
- `parse_duration` raises `ValueError` on anything unparseable; config
  validation depends on that.

## 7. Workflow Integration

Bottom of the dependency graph: `config` uses `parse_duration`; `state` uses
`utc_now_iso`; the forge adapters (and later the executor launcher and
isolation) run everything through a `CommandRunner`.

## 8. Usage

```python
from adore.util import run_command, parse_duration

result = run_command(["glab", "issue", "list", "--output", "json"])
if result.ok:
    ...
seconds = parse_duration("24h")  # 86400
```

## 9. Validation And Tests

- `tests/test_util.py`: duration units and garbage rejection, output capture,
  missing binary -> 127, hung command -> 124, timestamp shape, and
  `process_alive` (current pid alive, non-positive pids rejected).
- Minimum validation after a change: `uv run --group dev pytest tests/test_util.py`.

## 10. Limitations

- `run_command` captures completed bounded process output. Streaming RPC uses
  the executor's separate owned pipe transport.
- Retry/backoff policy belongs to callers rather than the generic runner.

## Exact source decoding

`run_command` retains original stdout in `raw_stdout`; `stdout_bytes` exposes that exact capture, without decoding or newline conversion. Text-only injected results encode their fixture as UTF-8 with surrogateescape. The normal `stdout` remains display text decoded with replacement. Content fingerprints must use `stdout_bytes`, so different invalid UTF-8 sequences cannot collapse to the same replacement text. Raw capture is also retained on timeout. `strict_json_loads` rejects duplicate keys, non-finite constants and decoder nesting overflow. Callers own input-size limits and translate failures to their typed domain errors. Focused proof: `tests/test_util.py`.

## Automatic child process policy

`automatic_environment(env)` copies the explicit mapping, or the ambient
process environment when `env` is `None`, then forces `GIT_PAGER=cat` and
`PAGER=cat`. Conflicting case variants are removed; explicit empty mappings
stay isolated from ambient variables. Caller mappings and `os.environ` remain
unchanged. `background_process_options()` returns Windows `CREATE_NO_WINDOW`
options and an empty mapping on Linux.

`run_command` combines both policies with captured streams and closed stdin.
Worker engine launches, native supervisors and the bounded JSON-stdin regex
probe reuse these helpers. Exit codes 126/127/124, authoritative timeout
classification, exact CRLF decoding and argv execution remain unchanged.
Focused proof: `tests/test_automatic_processes.py` and runner cases in `tests/test_util.py`.
