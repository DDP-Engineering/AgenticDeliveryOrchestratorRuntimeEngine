<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE - Agentic Delivery Orchestrator & Runtime Engine

ADORE turns an opt-in GitHub, GitLab or Gitea ticket into an isolated,
human-approved merge or pull request. Pi works in a dedicated branch and
worktree using container or native local execution. A repository with AEGIS
runs stage by stage with agent-owned checks; a repository without
AEGIS runs a bounded direct implementation session and presents an explicitly
unverified candidate. Both require fresh human approval before ADORE publishes
a draft or ready MR/PR according to `delivery.draft`. It never merges.

Current release: **ADORE 0.15.0**.

## How it works

```text
eligible ticket
  -> ADORE run state (schema 1)
  -> isolated branch + worktree + container
  -> workflow selected from the worktree and recorded at claim:
       AEGIS present: task journal + fresh sessions per stage + agent-reported checks
       AEGIS absent: fresh direct implementation session + unverified evidence
  -> host-owned checkpoints + target integration
  -> candidate fingerprint + fresh human approval label
  -> push + draft MR/PR
  -> human review and merge
```

An AEGIS task runs `frame -> specify -> design -> build -> validate -> done`;
a small fix or change may take its quick path without `specify` and `design`.
The executor decides and justifies that path in the AEGIS journal.

A direct run uses `build -> validate -> done`. Pi implements the whole ticket
in one fresh bounded session per attempt, reads the project's own instructions
and reports its changes/checks in `ADORE_SUMMARY.md`. ADORE retains the summary,
removes that exchange file, excludes it and the questions file from checkpoints,
and presents the changed candidate with its agent-reported checks. Questions park either workflow; `agent-answered` resumes fresh
with the discussion. Summary-only work fails with `NO_CHANGES`.

Only payload absence selects direct. A present unsupported or broken AEGIS
payload is refused, not bypassed. A run keeps its recorded workflow on Retry,
clarification and review; later repository adoption affects new tickets only.
ADORE never installs or edits the target's AEGIS payload.

## What you get

- **Bounded, loud failure.** A stage gets a configurable number of attempts,
  three by default; the last one stops with durable JSONL evidence and a
  visible incident comment. Questions park the run without consuming attempts.
- **A real approval gate.** ADORE presents the agent-reported result and waits for a fresh `agent-approved` label bound
  to the exact candidate fingerprint and target commit. Drift invalidates it.
- **The executor stays off the remote.** Pi runs in a container with no forge
  credentials and never commits, pushes, opens or merges. ADORE owns checkpoints,
  push and draft creation, and has no merge operation at all.
- **Truthful state.** One conductor per state root, a persisted notification
  outbox, typed failures instead of guesses, and retained evidence for
  explicit recovery.
- **One coding agent, three forges.** Pi as the executor, driven through its
  RPC mode in the container; `gh`, `glab` and `tea` as the forge CLIs.
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
- A target repository with documented build/test instructions and ignored
  generated artifacts. AEGIS is optional for CLI/configured projects. When
  `.agentic/aegis.py` is present, it must meet the supported version/schema
  contract declared in `04_Software/adore/aegis.py`.
- A model-provider key for the Pi model, kept in the environment or a
  gitignored `.env`.

## Quick start

For the packaged web application, extract the platform-specific archive from
`07_Delivery/`: `adore-<version>-windows-x64.zip` or
`adore-<version>-linux-x64.tar.gz`. Double-click `Start-ADORE.cmd` on Windows
or run `./start-adore.sh` on Linux. Python and the web dependencies are included;
the launcher starts both services and opens the ready interface. See the
package README for first sign-in, stopping, data and logs. Project tools and
credentials are configured separately through the interface.

For source/CLI operation:

From `04_Software`:

```bash
uv sync
adore init my-project
adore --profile my-project config validate
adore --profile my-project run --dry-run
adore --profile my-project run --once
```

`adore init` is a guided setup that probes the host tools and the target
repository's AEGIS payload when present and writes a validated profile. Without
it, setup reports: "No AEGIS found: tickets run in the direct workflow".
Web enrollment still requires AEGIS in this build; enroll AEGIS-free projects
through CLI/configuration. Label a small ticket
`agent-ready` with a priority such as `P2`, run one supervised poll, review the
presented evidence, add `agent-approved`, and poll again to see the draft MR/PR
open. Unattended operation on Ubuntu (systemd) or Windows 11 (Task Scheduler)
is set up by the scripts in `02_Tools/deploy/`.

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
| `07_Delivery/` | final user archives and optional SHA-256 files only |
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
release additionally passes `python 02_Tools/internal/check_release_consistency.py
--require-artifacts`. End-user Windows/Linux archives are built with
`python 02_Tools/create_package.py`; `07_Delivery/` contains only the two
archives and their optional adjacent hashes. Temporary build/verification work
is removed automatically and results are printed without saved reports.
The three public repository tools are `setup_environment.py`, `create_package.py`
and `verify_package.py` under `02_Tools/`. Internal release/license helpers are
called automatically. Setup/deployment scripts do not require automated tests.

## Versioning and AEGIS compatibility

AEGIS is a separate project with its own repository. ADORE consumes its companion
CLI; supported version and schema policy is declared once in
`04_Software/adore/aegis.py`. The AEGIS 0.15 contract is covered by
captured offline regression evidence; see [AEGIS compatibility](01_Documentation/AEGIS_Compatibility.md).
ADORE keeps its own Semantic Versioning and preserves saved job progress across
compatible companion updates. Run state remains schema 1.

## License

PolyForm Noncommercial License 1.0.0. Commercial use requires a separate
commercial license from DDP Engineering.

## Native local executor

Explicit local profiles run an installed, signed-in Pi under the ADORE machine
and service account with dedicated worktrees and verified Windows Job/Linux cgroup
process ownership. Project tools remain user-owned. See [Local execution](01_Documentation/Local_Execution.md).
