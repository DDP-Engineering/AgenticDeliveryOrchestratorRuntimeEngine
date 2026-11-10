<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Repositories without AEGIS: the direct workflow

Date: 2026-11-10. Status: proposed for owner review; tickets published on Gitea
(see [Gitea_Issues/README.md](Gitea_Issues/README.md)).
Baseline: `master` at `b2e6442`. Line numbers refer to that commit and will drift.
Implementation: by ADORE on this repository, with Pi on `gpt-6.1-sol` at thinking
level `high` (section 6).

## 1. Decision

ADORE conducts tickets in repositories that have no AEGIS through a second,
smaller path: the **direct workflow**. ADORE picks the workflow per ticket from
what the repository contains:

| The run's worktree has | Workflow |
|---|---|
| `.agentic/aegis.py`, supported version | AEGIS workflow, unchanged |
| no `.agentic/aegis.py` | direct workflow |
| `.agentic/aegis.py`, unsupported or broken | refused as today; never a silent fallback |

In the direct workflow Pi implements the ticket in one bounded session. ADORE
checks that the session ended with changes and no open questions, runs one
optional verification command, and hands the candidate to the same human
approval, publication and review loop as today.

ADORE does not install, upgrade or edit AEGIS in a target repository.

## 2. Why

Today ADORE refuses every repository without AEGIS:

- the run probe accepts only AEGIS 0.15.0 or later over schema 1, with "no
  alternate-contract fallback" (`adore/aegis.py:18`, `:46`);
- web enrollment answers 409 `repository_aegis_missing` and removes the clone it
  made (`adore/web/app.py:1404-1414`);
- polling claims no ticket and records `payload_error` (`orchestrator.py:377-385`).

Installing AEGIS during a run was considered and rejected:

1. **It does not configure the repository.** `aegis init` writes the same defaults
   for every repository (`test = "pytest -q"`, `source = ["src/"]`). Nothing in
   AEGIS detects folders or test commands, and its adoption step does not set
   them. ADORE's completion gate needs at least one configured command that runs
   and passes, so someone still has to find the test command. Once it is known,
   AEGIS adds nothing the ticket needs.
2. **It puts unrelated files into another team's pull request:** `.agentic/`,
   managed blocks in `AGENTS.md`, `CLAUDE.md`, `QWEN.md` and `.gitignore`, and the
   task journal (ADORE commits with `git add -A`).
3. **It reverses ADORE's documented boundary.** ADORE never upgrades a target's
   payload (`01_Documentation/AEGIS_Compatibility.md:43`), and AEGIS itself has no
   upgrade command.

What keeps the direct workflow small: everything after approval is already
independent of AEGIS. Push, MR/PR and merge tracking run no AEGIS command
(`orchestrator.py:2030-2049`); publication needs only `stage == "done"` plus a
recorded `validation_evidence` and `candidate_fingerprint` (`:1800`). ADORE
already owns the other signals a direct run needs: Pi's exit and settle event,
the questions file, the worktree progress fingerprint, budgets and timeouts.

## 3. What the user sees

- **Enrollment.** The AEGIS files check becomes an information row, *Workflow*:
  "AEGIS, stage by stage" or "Direct, no AEGIS found". It never blocks. One new
  optional field, *Verification command*, pre-filled with a suggestion read from
  the repository (for example `npm test`). The user chooses no mode.
- **Settings → Implementation.** The same *Verification command* field.
- **Jobs.** A direct job shows *Implementation* and *Validation* only, the attempt
  number and the verification result. AEGIS jobs look as today.
- **Ticket and MR/PR.** The approval comment and the MR/PR body carry Pi's summary
  and the verification result; without a command they say plainly that the
  candidate is unverified. Labels, approval and review work as today.
- **The target repository receives only the ticket's own changes.**

## 4. Target design

### 4.1 Choosing the workflow

- At claim, ADORE checks the run's worktree for `.agentic/aegis.py`. The pre-pick
  check (`orchestrator.py:377-385`, `:945-954`) applies the same test to the clone
  and probes AEGIS only when the file exists.
- The run records `workflow = "aegis" | "direct"`. A resumed run keeps it; a
  repository that adopts AEGIS later gets the AEGIS workflow on its next ticket.
- No setting selects the workflow.

### 4.2 The direct run

- `_conduct` branches right after `_provision` (`orchestrator.py:1074-1091`) into a
  new `_conduct_direct`. There is no shared workflow interface: there are two
  paths, and the AEGIS loop is too stage-specific to share one cleanly (AGENTS.md:
  prefer simple changes over speculative abstraction).
- Stages: `build` (Pi works) → `validate` (ADORE verifies) → `done`. They reuse the
  existing stage names, limits (`per_gate_timeout_seconds`,
  `stage_timeout_overrides`), metrics and job display.
- One fresh Pi session per attempt, through the existing launcher, container,
  egress proxy and budgets.
- The prompt (new `_direct_prompt`) carries the ticket title and body and asks Pi
  to:
  - read the repository's own instructions when present (`AGENTS.md`,
    `CLAUDE.md`, `CONTRIBUTING.md`, `README`);
  - implement the ticket completely, with tests where the repository has tests;
  - run the verification command when one is set;
  - never commit, push, open or merge an MR/PR, or touch forge credentials;
  - ask blocking questions in the questions file;
  - finish by writing a short summary (what changed, how it was checked) to
    `ADORE_SUMMARY.md` at the worktree root.

  It reuses the container permission and network paragraphs of `_stage_prompt`.

### 4.3 When a direct run is done

1. The Pi session ended normally (exit 0, settle event without error).
2. No questions file exists. Otherwise the run parks as today, and
   `agent-answered` resumes it in a fresh session with the thread.
3. The worktree changed (progress fingerprint, `isolation.py:823-841`), not
   counting `ADORE_SUMMARY.md` and the questions file. Otherwise the run fails with
   `NO_CHANGES` and shows Pi's summary.
4. The verification command passed, or none is configured ("unverified").

ADORE then keeps the summary text, removes `ADORE_SUMMARY.md`, makes the
checkpoint commit, records `validation_evidence` and `candidate_fingerprint`, sets
`stage = "done"` and moves the run to `awaiting-approval`. Neither the summary
file nor the questions file is ever committed.

### 4.4 Verification command and fix attempts

- `[workflow] verify_command`: optional, one shell command line, run from the
  worktree root in the run's execution environment and bounded by the validate
  stage limit. AEGIS runs ignore it; they use the repository's AEGIS commands.
- Evidence: command, exit code, duration and the last 200 lines of output,
  sanitised.
- A failing or timed-out command sends the run back to `build`: a fresh Pi
  session gets the command, exit code and output tail. Attempts are bounded by
  `[recovery] max_stage_failures`; after that the run fails with
  `VERIFICATION_FAILED`, the evidence is kept, and `adore retry` works as today.

### 4.5 Suggested verification command

A pure function reads file names and manifest contents in the clone. It never runs
a command and never follows a link outside the repository. It returns a suggestion
or nothing. The first match at the repository root wins. When the root has none
and exactly one first-level directory matches, the suggestion is prefixed with
`cd <dir> && `. Several matching directories give no suggestion.

| Found | Suggestion |
|---|---|
| `package.json` with a real `scripts.test` | `npm test` (`pnpm test` or `yarn test` when that lockfile is present) |
| `pyproject.toml`, `pytest.ini` or `tox.ini` | `uv run pytest -q` with `uv.lock`, else `python -m pytest -q` |
| `go.mod` | `go test ./...` |
| `Cargo.toml` | `cargo test` |
| `pom.xml` / `build.gradle` or `build.gradle.kts` | `mvn -q test` / `./gradlew test` (`gradle test` without a wrapper) |
| `*.sln` or `*.csproj` | `dotnet test` |
| `Makefile` with a `test:` target | `make test` |

The suggestion only pre-fills the field; a human saves it.

### 4.6 Run state and configuration

- Run record: a new `workflow` field. A direct run carries no AEGIS task id.
- No migration (AGENTS.md "Stored data during development"): a run record without
  `workflow` is refused with a message naming what to delete, and one
  `CHANGELOG.md` line says the same.
- Configuration: one new key, `[workflow] verify_command`, empty by default.

### 4.7 What does not change

The AEGIS workflow, ticket selection and labels, isolation, egress, budgets,
approval, publication, the review loop, and Pi as the only coding agent.

## 5. Delivery plan

| ID | Ticket | Depends on | Priority | Labels |
|---|---|---|---|---|
| EPIC | Run tickets in repositories without AEGIS | DW-00 to DW-07 | P1 | `P1`, `no-agent` |
| DW-01 | `adore init` probes AEGIS with the configured Python (smoke ticket) | - | P1 | `P1`, `fix` |
| DW-00 | Read the agent prompts from files shipped with ADORE | DW-01 | P1 | `P1`, `change` |
| DW-02 | Direct workflow in the orchestrator, unverified candidates | DW-00 | P1 | `P1` |
| DW-03 | Verification command and bounded fix attempts | DW-02 | P1 | `P1` |
| DW-04 | Enroll repositories without AEGIS in the web interface | DW-03 | P1 | `P1` |
| DW-05 | Suggest the verification command from repository files | DW-04 | P2 | `P2` |
| DW-06 | Show direct jobs clearly in Jobs | DW-04 | P2 | `P2` |
| DW-07 | Live acceptance and documentation audit (owner) | DW-00 to DW-06 | P1 | `P1`, `no-agent` |

Tickets without a type label run as features (`[workflow] default_kind`). DW-05
and DW-06 may run in either order; everything else is sequential, one ticket at a
time.

Where the "only repositories with AEGIS" statements go:

- product identity texts (`AGENTS.md` Status, `.agentic/context/project.md`,
  `00_Planning/ADORE_System_Overview.md`) were rewritten with this plan;
- behaviour descriptions change with the behaviour: README, Getting Started and the
  runtime-project contract in DW-02; web interface, help and error copy in DW-04;
- a final audit runs in DW-07.

## 6. Running ADORE on this repository

This repository has AEGIS, so ADORE builds the direct workflow through its existing
AEGIS workflow: one AEGIS task per ticket.

### 6.1 Before the first ticket (owner)

- **P1 Portable AEGIS commands. Done on `task/direct-workflow` (2026-11-10).**
  `.agentic/aegis.toml` `[commands]` used Windows paths
  (`.\\.venv\\Scripts\\python.exe -m pytest -q`,
  `.\\.venv\\Scripts\\ruff.exe check adore tests`). ADORE runs
  `check --strict --run` inside its Linux container, where those cannot run, so no
  ticket could finish. AEGIS 0.15.0 has one string per command and no per-OS
  variant (it runs each through the platform shell), so the commands are now
  OS-neutral:
  - `test = "uv run --frozen --extra web python -m pytest -q"`
  - `lint = "uv run --frozen ruff check adore tests"`
  - `frontend` and `workdir` are unchanged.

  `python -m pytest`, not `pytest`: uv's Windows script launcher fails on this
  drive ("uv trampoline failed to canonicalize script path"). The change was
  verified on Windows and in `adore-executor-base:1.0.0` with targeted tests.
  This is an owner change, because the executor must not edit `.agentic/` files.
- **P1b Clean lint baseline.** `ruff check adore tests` reports one E501 at
  `04_Software/tests/test_web_settings_batch.py:97` (from `4ec497f`). Every strict
  check fails on it, so fix it on the integration branch before DW-01.
- **P2 Project image.** The base image has Python 3.11, uv and Node 22 but no
  browser, and `frontend` runs the Playwright suite. Derive an image from
  `adore-executor-base` with Chromium for `@playwright/test` 1.63.0
  (`npx playwright@1.63.0 install --with-deps chromium`), select it for the
  project, and set `required_tool_checks = ["uv --version", "node --version",
  "npx playwright --version"]`. See `01_Documentation/Project_Executor_Images.md`.
- **P3 Dependencies.** The tests need `uv sync --frozen --extra web` in
  `04_Software` and `npm ci` in `04_Software/web`. The simplest option is to let Pi
  install them (`01_Documentation/Agent_Dependency_Installation.md`) and add
  `pypi.org`, `files.pythonhosted.org` and `registry.npmjs.org` to
  `[container.egress] allowlist`, so internet access stays off. A reviewed
  preparation recipe is stricter, but it must be selected again after every merge,
  because it is pinned to the target branch's commit
  (`01_Documentation/Container_Preparation.md`).
- **P4 Project settings,** below.
- **P5 Dry run.** In the project image, on the target branch,
  `python .agentic/aegis.py check --strict --run` passes. Record how long it takes:
  it must fit the validate stage limit.

### 6.2 Project settings

```toml
[executor]
provider = "openai"        # API key; or "chatgpt": container only, stage limits <= 3000 s
model = "gpt-6.1-sol"
thinking = "high"          # Pi catalog levels for this model: low, medium, high, xhigh, max

[polling]
max_concurrent_runs = 1

[delivery]
target_branch = "task/direct-workflow"   # integration branch cut from master
draft = true
```

The default budgets (3600 s per run, 1800 s per launch, 5 USD) are sized for small
tickets. A full AEGIS path on this repository, with `high` reasoning and review
enabled (`[review] max_fix_cycles = 5`), needs more:

- `per_gate_timeout_seconds`: the measured strict-check time plus working margin
  (at most 3000 with `chatgpt`);
- `max_wall_clock_seconds`: at least five stage limits;
- `max_cost_usd`: set for your provider (0 disables the cap).

Calibrate all three on DW-01.

### 6.3 Operating procedure

1. Create the integration branch and finish P1 to P5.
2. Add `agent-ready` to DW-01 only. ADORE does not read Gitea dependencies, so the
   ready label is the sequencer.
3. Review the draft PR; add `agent-revise` to request changes; merge it into the
   integration branch yourself.
4. Tick the ticket in the epic's Progress list and add `agent-ready` to the next
   one.
5. After DW-06, run DW-07 yourself, then merge the integration branch into
   `master`.

## 7. Rules for every ticket

- ADORE runs the ticket as one AEGIS task; `AGENTS.md` is authoritative.
- A conflict between a ticket and this plan, or code that moved so a decision no
  longer fits, is a question in the questions file, not a decision.
- `04_Software/adore/aegis.py` is ADORE's own AEGIS client and may be edited when
  a ticket needs it. The AEGIS payload under `.agentic/` (`aegis.py`, `steps/`,
  `templates/`, `aegis.toml`) is not edited.
- No migrations or compatibility with earlier builds.
- User-visible change: `CHANGELOG.md` and a four-locale release note; interface or
  workflow change: help in all four locales; component pages in
  `05_SoftwareDocu/` in the same change.
- Every public behaviour gets one happy test and negative tests at its trust
  boundaries, offline, with the existing fakes for Pi, forge, git and container.
- Targeted tests while building; the full suite runs once, in validate, through the
  AEGIS strict check.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A direct run hands over an unverified candidate | The approval comment says "unverified"; human approval stays mandatory; the suggested command makes verification the usual case |
| Pi changes more than the ticket asks | Same worktree isolation, `max_files_touched` and human PR review as today |
| ADORE implementing ADORE disturbs the running instance | Runs work on branches in worktrees; the deployed instance changes only when you deploy |
| Regression in the AEGIS workflow | Every ticket keeps the existing AEGIS tests green; DW-07 checks it live |
| The strict check is too slow for the stage limit | P5 measures it; raise the validate stage limit, or use an API-key provider instead of `chatgpt` |
| A ticket is too large for one run | Each ticket says when to ask for a split |

## 9. Defaults taken (owner may change them before the ticket starts)

- No verification command: the run proceeds and is marked unverified (DW-03).
- AEGIS present but unsupported or broken: refused, as today (DW-02).
- PRs target the integration branch `task/direct-workflow` (section 6.2).

## 10. Later, outside this plan

An **Adopt AEGIS** action that opens one separate MR in a target repository with
`.agentic/` and an `aegis.toml` pre-filled from section 4.5. The repository owners
review and merge it; from then on ADORE uses the AEGIS workflow for that repository
by itself.
