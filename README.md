<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE - Agentic Delivery Orchestrator & Runtime Engine

ADORE turns an opt-in forge ticket into a governed, isolated, human-approved
draft merge request. It selects a ticket from GitHub, GitLab or Gitea, runs a
coding executor through the repository's installed AEGIS workflow one stage at
a time inside a dedicated branch, worktree and container, verifies the result
independently, and publishes only a draft MR/PR after a fresh human approval.
It never merges.

Current release: **ADORE 0.13.0**.

## How it works

```text
eligible ticket
  -> ADORE run state (schema 1)
  -> isolated branch + worktree + container
  -> AEGIS task journal
  -> one fresh executor session per stage
  -> local checkpoint after each successful transition
  -> target integration + strict independent verification
  -> candidate fingerprint + fresh human approval label
  -> push + draft MR/PR + AEGIS close-out
  -> human review and merge
```

A full task runs `frame -> specify -> design -> build -> validate -> deliver`;
a small fix or change may take the quick path without `specify` and `design`.
The executor decides and justifies the path in the AEGIS journal; the ticket
label is only a hint.

## What you get

- **Bounded, loud failure.** A stage gets a configurable number of attempts,
  three by default; the last one stops with durable JSONL evidence and a
  visible incident comment. Questions park the run without consuming attempts.
- **A real approval gate.** After strict verification ADORE presents the
  candidate and waits for a fresh `agent-approved` label bound to the exact
  candidate fingerprint and target commit. Drift or mutation invalidates it.
- **Executors stay off the remote.** They run in a container with no forge
  credentials and never commit, push, open or merge. ADORE owns checkpoints,
  push and draft creation, and has no merge operation at all.
- **Truthful state.** One conductor per state root, a persisted notification
  outbox, typed failures instead of guesses, and retained evidence for
  explicit recovery.
- **Four executors, three forges.** OpenCode, Pi, Codex and Qwen Code as
  executors; `gh`, `glab` and `tea` as the forge CLIs.
- **Optional web interface.** A local React/FastAPI dashboard adds project and
  job visibility, account/project permissions, reported usage, administrator
  costs, and a durable worker. See
  [Web_Interface.md](01_Documentation/Web_Interface.md) for the offline bundle
  and operating limits.

## Requirements

- Python 3.11 or newer and `uv` on the host; the runtime itself is
  standard-library only.
- Git with a target clone whose `origin` the run-as account can push to.
- Docker or rootless Podman, natively or as Docker Engine inside WSL2.
- An authenticated `gh`, `glab` or `tea` for the target forge.
- A target repository that carries AEGIS as `.agentic/aegis.py` at 0.5.0 or
  later on the major-0 line, reporting JSON schema 1.
- A model-provider key for the chosen executor, kept in the environment or a
  gitignored `.env`.

## Quick start

From `04_Software`:

```bash
uv sync
adore init my-project
adore --profile my-project config validate
adore --profile my-project run --dry-run
adore --profile my-project run --once
```

`adore init` is a guided setup that probes the host tools and the target
repository's AEGIS payload and writes a validated profile. Label a small ticket
`agent-ready` with a priority such as `P2`, run one supervised poll, review the
presented evidence, add `agent-approved`, and poll again to see the draft MR/PR
open. Unattended operation on Ubuntu (systemd) or Windows 11 (Task Scheduler)
is set up by the scripts in `04_Software/deploy/`.

## Documentation

| Read | For |
| --- | --- |
| [Getting Started](01_Documentation/Getting_Started.md) | host setup, first profile, first safe poll |
| [Security and Credentials](01_Documentation/Security_And_Credentials.md) | where every credential lives and the human merge boundary |
| [Integrating a Runtime Project](01_Documentation/Integrating_A_Runtime_Project.md) | the target-repository contract and the AEGIS ownership boundary |
| [Operations Guide](01_Documentation/Operations_Guide.md) | states, approval, review and failure interpretation |
| [Recovery and Maintenance](01_Documentation/Recovery_And_Maintenance.md) | retry, reset, cancel, delete and cleanup |
| [Configuration Reference](01_Documentation/Configuration_Reference.md) | every `config.toml` key |
| [CLI Reference](01_Documentation/CLI_Reference.md) | every command and exit code |
| [Operator Cheat Sheets](01_Documentation/Operator_Cheat_Sheets/README.md) | one-page reminders and slide decks |
| [System Overview](00_Planning/ADORE_System_Overview.md) | design, components, known limits and open work |

## Repository layout

| Path | Contents |
| --- | --- |
| `00_Planning/` | system overview and design position |
| `01_Documentation/` | operator and administrator guides |
| `02_Tools/` | release-identity checker and runtime-bundle packagers |
| `04_Software/` | the `adore` package, offline tests, deploy scripts and container images |
| `05_SoftwareDocu/` | one implementation contract per component |
| `07_Delivery/` | generated runtime bundles |
| `.agentic/` | this repository's own AEGIS workflow, requirements and task journals |

## Development

```bash
cd 04_Software
uv sync
python -m pytest -q
python -m ruff check adore tests
```

The suite is fully offline. ADORE's own development follows the AEGIS
workflow installed in `.agentic/`; read `AGENTS.md` before contributing. A
release additionally passes `python 02_Tools/check_release_consistency.py
--require-artifacts` and is packaged with `02_Tools/package_runtime.ps1` or
`package_runtime.sh`.

## Versioning and AEGIS compatibility

AEGIS is a separate project with its own repository. ADORE consumes its
companion CLI and never edits the payload. The supported range, major 0 from
0.5.0 upward over JSON schema 1, is declared once in
`04_Software/adore/aegis.py`, so a new AEGIS minor needs no ADORE change. Each
AEGIS release is still re-verified surface by surface, and the ADORE release
number names the AEGIS release the contract was last re-proven on. Run state
is schema 1 and is never migrated from earlier lines. See
[CHANGELOG.md](CHANGELOG.md).

## License

PolyForm Noncommercial License 1.0.0. Commercial use requires a separate
commercial license from DDP Engineering.
