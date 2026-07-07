<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Implementation Plan: Assisted Per-Project Configuration & Runtime Project Profiles

> Status: PLAN (not yet implemented). Author: assisted by Claude. Date: 2026-07-05.
> Target codebase: `04_Software/` (ador package). Runs on Windows 11 and Ubuntu 22+.
> To be implemented with Claude Code, task by task. Each task names the AI model
> and reasoning level to use, with rationale.

---

## 0. Goal (one paragraph)

Onboarding a new runtime project to ADOR today means hand-writing a `config.toml`
with ~8 project-specific fields (and knowing which of the 15 sections actually
matter), plus setting up non-ADOR prerequisites (a platform CLI, an auth token, a
container runtime) with no in-tool guidance. This plan adds a **detection-first,
fully-explicit interactive `ador init` wizard** that produces a named **runtime
project profile**, and a **profile-management CLI** (`ador profile list|show|
delete|rename|use|path`) with creation date and run statistics. It works across
different target projects (not just cockpit-gcp) and on both Windows and Ubuntu.
It stays CLI-first and standard-library-only — no GUI, no hosted server —
consistent with design decision 12a, which explicitly permits `ador config`
helpers while ruling out a settings GUI.

---

## 1. Analysis of the current ADOR structure (what we build on)

### 1.1 Configuration system (`ador/config.py`)
- **15 typed dataclass sections** (`KNOWN_SECTIONS`): `agent, platform, state,
  polling, readiness, labels, executor, clarification, container, worktree,
  budgets, delivery, review, reconcile, metrics`. Nested: `labels.{lifecycle,
  selection,control,executor}`, `executor.<name>` command tables.
- `load_config(path)` -> `Config` via `tomllib`; **lenient** (unknown keys
  dropped, missing keys default) so a minimal file is valid.
- `validate_config(config) -> list[str]`: returns human-readable issues; run at
  startup by the engine and by `ador config validate`.
- `_derive_names(config)`: fills slug/email/store_root/metrics paths from `agent`.
- **Required, project-specific fields** (everything else has a working default):
  | Field | Section | Validation |
  |---|---|---|
  | `repo` | `[platform]` | non-empty |
  | `kind` | `[platform]` | `gitlab`\|`github` |
  | `repo_path` | `[worktree]` | non-empty (local clone) |
  | `command` + `model` | `[executor.<default>]` | non-empty; `{prompt}` present; no `--auto` |
  | `reviewers` | `[delivery]` | non-empty for delivery |
  | `runtime` | `[container]` | last token `docker`\|`podman` |
  | `image` | `[container]` | non-empty |
  | `branch_template` (+ optional `branch_rule`) | `[worktree]` | contains `{run_id}`/`{iid}`; template must satisfy the rule |
- **Everything else defaults**: budgets, polling, TTLs, labels, readiness, review,
  reconcile, metrics, clarification. The wizard therefore only needs to *ask/detect
  the ~8 required fields* and offer to customize the rest — and it writes a
  **minimal** profile (only non-default keys), not a 200-line copy of the example.

### 1.2 CLI (`ador/cli.py`)
- stdlib `argparse`; `-c/--config` (default `config.toml`); subparsers with
  `dest="command"`. Handlers `_cmd_*`; `_load(args)` reads config;
  `_store(config)` builds the state store; `_engine(args)` loads+validates+builds.
- Exit codes: `EXIT_OK=0`, `EXIT_ERROR=1`, `EXIT_NOT_IMPLEMENTED=2`.
- Existing commands: `run, status, runs, pause, resume, cleanup, retry, cancel,
  logs, delete, reset, stats, report, export, config {show,validate,set}`
  (`config set` is the only stub).
- **Extension points we use**: add `init` and `profile` subparsers; add a global
  `--profile NAME`; extend the config-path resolution in `_load`/`_engine`.

### 1.3 State & identity
- `StateStore(store_root, slug)`: per-deployment runs/lock/pause/journal under
  `store_root` (default `.<slug>` in CWD). Per-store lock already allows multiple
  ADOR instances to coexist — the multi-project foundation is present.
- `metrics.py`: `load_summaries(db_path)` / `summarize_run` give per-project run
  statistics (merged/failed/span/launches/tokens) — the source for profile stats.
- `identity.py`: `AgentIdentity` derives all names from `name`/`slug`.

### 1.4 Cross-platform facts already handled
- Container runtime may be a wrapped command (`wsl -d Ubuntu-24.04 -- docker`);
  WSL mount translation + WSLENV handled in `isolation.py`.
- Rootless podman needs `run_args=["--userns=keep-id"]` (verified).
- `util.run_command` captures output cross-platform; `force_rmtree` handles
  Windows reparse points.
- **Gap this plan fills**: there is no global, cross-platform ADOR config home,
  no notion of a named profile, and no onboarding/prereq guidance in-tool.

---

## 2. Feature overview

Three cooperating pieces, all stdlib-only:

1. **Profile store** — a global, cross-platform ADOR config home holding named
   profiles; each profile = a `config.toml` + a `profile.json` metadata sidecar.
2. **`ador init` wizard** — detection-first, every prompt explicit (label,
   description, example, validation, default/detected value), inline guidance for
   non-ADOR prerequisites (install a platform CLI, create a token, pick a
   runtime), branching questions (GitLab vs GitHub; public vs corporate/
   self-hosted; private vs public repo). Ends by writing a profile and running
   `validate_config`.
3. **Profile CLI** — `list / show / delete / rename / use / path`, with created
   date, last-used, use count, and run statistics; plus a global `--profile`.

---

## 3. Key design decisions (ratify in Task 1)

- **D1 — Profile home (cross-platform).** Resolve an ADOR config home:
  - Windows: `%APPDATA%\ador` (fallback `%LOCALAPPDATA%\ador`).
  - Linux/Ubuntu: `$XDG_CONFIG_HOME/ador` (default `~/.config/ador`).
  - Override: `ADOR_HOME` env var (both OSes; used by tests).
  Profiles live at `<home>/profiles/<name>/` containing `config.toml` +
  `profile.json`. The active-profile pointer is `<home>/active_profile`.
- **D2 — Profile owns its data.** Set the profile's `[state] store_root` to
  `<home>/profiles/<name>/state` so each project's runs/metrics/lock are isolated
  and statistics are trivially findable. (Alternative — a project-local `.ador` —
  is offered as a wizard choice for users who prefer co-locating state with the
  clone.)
- **D3 — Config-path resolution order** (in `_load`): explicit `-c FILE` >
  `--profile NAME` > active-profile pointer > `./config.toml` (today's default).
  Existing behavior is preserved when no profile is used.
- **D4 — Minimal profile output.** The wizard writes only keys that differ from
  dataclass defaults, plus a header comment naming the profile and creation date.
  Re-running `validate_config` must pass before the profile is saved.
- **D5 — Never store secrets in the profile.** Tokens/keys go to a project `.env`
  (or OS keyring / CLI host-auth); the wizard only writes `env_keys` names and
  prints setup guidance. `profile.json` never contains secret values.
- **D6 — Design 12a reconciliation.** `ador init`/`ador profile` are CLI "config
  helpers" (explicitly allowed by 12a); they are one-shot generators, not a
  hosted GUI/server. Add a clarifying sentence to 12a rather than contradicting
  it. No new runtime dependencies (stdlib `input()` prompts; no curses/textual).
- **D7 — Non-interactive escape hatch.** `ador init --non-interactive --answers
  answers.toml` applies a pre-filled answer file (for automation/tests and for
  Ubuntu servers without a TTY). The interactive path is the default.

---

## 4. THE PROMPT CATALOG (explicit wizard specification)

Every prompt below is specified as: **Prompt text** — *description shown to the
user* — `example` — validation — default/detected. Prompts marked (auto) are
detected and only shown for confirmation. Guidance blocks (non-ADOR setup) are
printed when a check fails; both Windows and Ubuntu instructions are given.

### Phase A — Environment & prerequisites (detect, then guide)

- **A1 (auto) Host OS** — detected via `platform.system()`. Shown: "Detected host:
  Windows 11" / "Ubuntu 22.04". Drives which install commands are printed.
- **A2 Git present?** — runs `git --version`.
  - Guidance if missing:
    - Windows: `winget install Git.Git` (or https://git-scm.com/download/win).
    - Ubuntu: `sudo apt-get update && sudo apt-get install -y git`.
- **A3 Container runtime** — probe `docker`, `podman`, and (Windows) `wsl -l -q`
  for a distro with docker/podman. Prompt: **"Which container runtime should this
  project use?"** — *ADOR runs each ticket in an isolated container; pick what is
  installed* — options: `docker`, `podman`, `wsl -d <distro> -- docker`,
  `wsl -d <distro> -- podman`, `host (no container — advanced, not isolated)` —
  default = first detected.
  - Guidance if none:
    - Ubuntu: install Docker Engine (`https://docs.docker.com/engine/install/ubuntu/`)
      or `sudo apt-get install -y podman uidmap slirp4netns`.
    - Windows: enable WSL2 (`wsl --install`), then install Docker Engine or podman
      *inside* the distro (no Docker Desktop required); set runtime to
      `wsl -d <distro> -- docker`.
  - If `podman` (rootless) chosen: auto-set `run_args=["--userns=keep-id"]` and
    tell the user why (bind-mount write permission).
- **A4 Platform CLI** — probe `glab` (GitLab) / `gh` (GitHub) based on the platform
  chosen in C1. Prompt only appears as guidance if missing.
  - Guidance (GitLab / `glab`):
    - Windows: `winget install GLab.GLab` (or `scoop install glab`).
    - Ubuntu: download the `.deb` from the glab releases page and
      `sudo apt-get install ./glab_*.deb` (or `sudo apt-get install glab` where packaged).
  - Guidance (GitHub / `gh`):
    - Windows: `winget install GitHub.cli`.
    - Ubuntu: follow `https://github.com/cli/cli/blob/trunk/docs/install_linux.md`.
- **A5 Platform CLI authenticated?** — run `glab auth status` / `gh auth status`.
  - Guidance if not authenticated:
    - **How to create a GitLab Personal Access Token**: GitLab → your avatar →
      *Preferences* → *Access Tokens* → *Add new token*; scope **`api`**; role
      **Developer** (Developer cannot merge protected branches — intended, ADOR
      never merges); copy the token now (shown once). *A GitLab PAT looks like*
      `glpat-XXXXXXXXXXXXXXXXXXXX` *(the literal prefix* `glpat-` *followed by 20
      characters).*
    - **Authenticate the CLI**: `glab auth login` (choose the host; for a corporate
      instance enter the hostname, e.g. `gitlab.mycorp.fr`; paste the token). For
      GitHub: `gh auth login`.
    - Alternatively put the token in the project `.env` as `GITLAB_TOKEN=` /
      `GITHUB_TOKEN=` (the wizard records the key name, never the value).
- **A6 Executor CLI** — probe `opencode` (default executor). Guidance if missing:
  install per `docker/README.md` (baked into the executor image; only needed on
  the host for the `host` runtime).

### Phase B — Project identity

- **B1 Profile name** — *a short, filesystem-safe name for THIS project profile;
  you'll reference it as* `--profile <name>` — `cockpit-gcp` — validation:
  matches `^[a-z0-9][a-z0-9._-]{0,63}$`, not already taken (unless `--force`).
- **B2 Project description** *(optional)* — *one line shown in* `ador profile list`
  — `GCP analytics platform — Terraform + Python + TS` — any text or empty.
- **B3 Agent name / slug** *(auto, confirm)* — *the bot's display name and the
  lowercase slug that names branches/containers/state* — `ADOR` / `ador` —
  slug must match `^[a-z0-9-]+$`; default keep `ADOR`/`ador`.

### Phase C — Platform & repository

- **C1 GitLab or GitHub?** — *which Git platform hosts this project* —
  `gitlab` — one of `gitlab`\|`github` — default detected from `git remote -v` host
  if run inside a clone. -> `[platform] kind`.
- **C2 Public service or corporate/self-hosted?** — *gitlab.com/github.com, or a
  private company instance* — `corporate` — one of `public`\|`corporate`. If
  `corporate`: **C2a Host URL** — `https://gitlab.examplexdigital.fr` — must be a
  URL; the wizard notes the CLI must be authenticated against this host
  (`glab auth login --hostname <host>` or `GITLAB_HOST`).
- **C3 Repository visibility** — *is the repo public or private/corporate?* —
  `private` — one of `public`\|`private`. If `private`: a token/CLI auth is
  required (loop back to A5 guidance if not satisfied).
- **C4 Repository path** — *the project path in* `group/subgroup/project` *form
  (NOT a URL)* — `rd/internal/france/delivery-tools/delivery-cockpit/cockpit-gcp`
  — non-empty; if run inside a clone, detect from `git remote get-url origin` and
  offer it for confirmation. -> `[platform] repo`.

### Phase D — Local clone & worktree

- **D1 Local clone path** — *absolute path to the local clone ADOR creates
  worktrees from (it is mounted into the container)* —
  Windows `D:/projects/cockpit-gcp` / Ubuntu `/home/you/projects/cockpit-gcp` —
  validation: path exists, is a git work-tree, `origin` remote matches C4 host.
  Default: current directory if it qualifies. -> `[worktree] repo_path`.
- **D2 Worktree root** *(confirm default)* — *host directory that holds per-run
  worktrees* — `worktrees` — non-empty; default `worktrees`. -> `[worktree] root`.
- **D3 Target/base branch** — *the branch MRs target and runs merge before
  delivery* — `develop` (or `main`) — detect the repo's default branch via
  `git symbolic-ref refs/remotes/origin/HEAD`; confirm. -> `[delivery] target_branch`.

### Phase E — Branch conventions (the fiddly, error-prone part)

- **E1 Does the repo enforce a branch-name push rule?** — *some repos reject
  branches that don't match a pattern (e.g. must start with* `feature/`*)* —
  `yes` — `yes`\|`no`. If `yes`:
  - **E1a Push-rule regex** — *the required pattern; the wizard can fetch it from
    GitLab if your token allows* — `^(feature|bugfix|release|hotfix)/.*$` — must
    compile as a regex. Auto-fetch attempt: `glab api projects/:id/push_rule`
    (field `branch_name_regex`) when a token is present; otherwise ask.
    -> `[worktree] branch_rule`.
- **E2 Branch template** — *how run branches are named;* `{slug}`*,* `{run_id}`*,*
  `{iid}` *placeholders* — default `{slug}/{run_id}`; if E1 requires a prefix,
  suggest `feature/{slug}-{iid}` — must contain `{run_id}` or `{iid}`. The wizard
  renders a sample and, if E1a set, checks it matches the rule (reusing
  `validate_config` logic) and re-prompts on mismatch. -> `[worktree] branch_template`.

### Phase F — Runtime & executor

- **F1 (from A3) Runtime string** — assembled from the A3 choice + distro; e.g.
  `wsl -d Ubuntu-24.04 -- podman`. -> `[container] runtime` (+ `run_args`).
- **F2 Executor image** *(confirm default)* — *the built image name; build it per*
  `docker/README.md` *before the first run* —
  `ador-executor-base:0.2.0` for executor-only validation, or a runtime-project
  image such as `ador-executor-cockpit-gcp:latest` — non-empty; offer to check
  presence (`<runtime> image inspect`) and warn if absent.
  -> `[container] image`.
- **F3 Executor CLI + model** — **F3a** *which executor* — `opencode` — one of the
  known executors; **F3b Model** — *provider/model id* — `openai/gpt-5.5` —
  non-empty. -> `[executor] default` + `[executor.opencode] command`+`model`
  (command from a known template so `{prompt}` is present and `--auto` is absent).
- **F4 Executor auth mode** — *how the executor authenticates to its model
  provider* — options: `api-key` (recommended for production: set
  `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` in `.env`) or `host-auth` (pilot-only OAuth
  bridge, `stage_host_auth=true`). -> `env_keys` and/or `stage_host_auth`, plus
  printed `.env` guidance. *An OpenAI key looks like* `sk-...`*; an Anthropic key
  looks like* `sk-ant-...` *— store it in* `.env`*, never in the profile.*

### Phase G — Delivery & reviewers

- **G1 Reviewers** — *platform usernames assigned to the draft MR (comma-
  separated)* — `dan.pasare` — at least one for delivery. -> `[delivery] reviewers`.
- **G2 (auto, informational) Draft-only** — the MR is always opened as a draft and
  ADOR never merges; shown, not asked. `draft=false` is rejected by validation.

### Phase H — Budgets & policy (offer recommended defaults)

- **H1 Budgets** — **"Use recommended supervised budgets, or customize?"** —
  recommended: `max_iterations=12, max_wall_clock_seconds=5400, max_cost_usd=5.0,
  max_files_touched=40`. If customize, ask each with the sizing ladder as guidance:
  *iterations = 6 (crawl, no fix headroom) / 12–15 (supervised) / 20 (unattended)*.
  -> `[budgets]`.
- **H2 Polling** — **"Run mode?"** — `once` (cron/Task Scheduler, single pass) or
  `loop` (long-running service) — default `once` for first setup. If `loop`, offer
  interval (default 60s) and optional quiet hours (`HH:MM-HH:MM`). -> `[polling]`.
- **H3 State location** — **"Where should this project's ADOR state live?"** —
  `profile` (`<home>/profiles/<name>/state`, recommended) or `project` (a `.ador`
  beside the clone). -> `[state] store_root` (D2).

### Phase I — Review, write, validate, next steps

- **I1** Print a summary table: every resolved value, flagged (detected) vs
  (entered) vs (default).
- **I2** **"Write this profile?"** — `yes`\|`no`. On `no`, offer to revise any phase.
- **I3** Write `<home>/profiles/<name>/config.toml` (minimal) + `profile.json`
  (metadata). Run `validate_config`; on issues, show them and loop back to the
  relevant prompt (never save an invalid profile).
- **I4** Print **next steps**, OS-aware: create `.env` with the named keys; build
  the image (`docker/README.md`); `ador --profile <name> config validate`;
  `ador --profile <name> run --dry-run`; `ador profile use <name>` to make it
  active.

---

## 5. CLI surface additions

```
ador init [--profile NAME] [--force] [--non-interactive --answers FILE]
ador profile list                 # table: NAME, PLATFORM, REPO, RUNTIME, CREATED, LAST-USED, RUNS, MERGED
ador profile show NAME            # full resolved config + metadata + stats
ador profile use NAME             # set the active profile (writes <home>/active_profile)
ador profile rename OLD NEW
ador profile delete NAME --force  # remove profile dir (guardrail: needs --force)
ador profile path [NAME]          # print the config.toml path (scripting)
ador --profile NAME <any command> # global flag; resolves config for run/status/etc.
```
- `ador profile delete` removes the profile directory (config + metadata + its
  state if profile-owned) — `--force` required (design 8c guardrail parity).
- All existing commands gain `--profile` via a global argument; `-c FILE` still
  wins if both are given (D3).

### `profile.json` schema (metadata sidecar)
```json
{
  "name": "cockpit-gcp",
  "description": "GCP analytics platform — Terraform + Python + TS",
  "created_at": "2026-07-05T09:00:00Z",
  "updated_at": "2026-07-05T09:00:00Z",
  "last_used_at": "2026-07-05T10:12:00Z",
  "use_count": 4,
  "platform": "gitlab",
  "host": "gitlab.examplexdigital.fr",
  "repo": "rd/.../cockpit-gcp",
  "runtime": "wsl -d Ubuntu-24.04 -- podman",
  "host_os": "Windows",
  "ador_version": "0.x.y",
  "config_path": "<home>/profiles/cockpit-gcp/config.toml",
  "store_root": "<home>/profiles/cockpit-gcp/state"
}
```
- `use_count`/`last_used_at` are bumped whenever a command resolves this profile.
- Live run statistics (runs/merged/failed/success-rate/last-run) are computed on
  demand from the profile's metrics DB (`metrics.load_summaries`) — not duplicated
  into `profile.json`, keeping one source of truth.

---

## 6. Task breakdown

> Ordering: T1 first (foundation). T2 and the T4 skeleton can proceed in parallel
> after T1. T3 depends on T1+T2. T5 depends on T1+T4. T6 runs alongside and then a
> consolidated pass after T1–T5. T7 after T3+T4. T8 last (docs mirror final
> behavior). Every task keeps the suite green (`uv run --group dev pytest`,
> `ruff check`) and follows the Testing Rules (happy + negative per boundary) and
> Doxygen/license/`@version` conventions in `AGENTS.md`.

### Task 1 — Foundation: config home + profile store
- **STATUS: DONE (2026-07-05).** `ador/profiles.py` + `tests/test_profiles.py`
  (13 tests, all green; suite 175 passing) + `05_SoftwareDocu/Component_Profiles.md`.
  Note: the OS branch was extracted into a pure `_home_for(os_name, environ)` so
  tests exercise Windows/POSIX shapes without monkeypatching `os.name` (which
  breaks pathlib process-wide). All of D1/D2/D3 + fail-closed corrupt handling
  implemented.
- **Model: Claude Opus 4.8 — Reasoning: High.**
- **Why this model/level:** cross-platform path semantics (APPDATA/XDG/ADOR_HOME),
  the profile schema, and the resolution order are load-bearing; every later task
  depends on getting them right, and mistakes here cascade. High-judgment, low
  code volume.
- **Deliverables:** `ador/profiles.py` — `ador_home()` resolver (Windows/Linux +
  `ADOR_HOME` override), `Profile` dataclass + `profile.json` read/write,
  `ProfileStore` (list/load/save/delete/rename, active-profile pointer), and
  `resolve_config_path(explicit, profile, cwd)` implementing D3. No CLI yet.
- **Acceptance:** unit tests for home resolution on both OS env shapes (monkeypatch
  `os.name`/env), CRUD round-trip in a tmp `ADOR_HOME`, resolution-order matrix,
  and fail-closed on a corrupt `profile.json`.

### Task 2 — Environment detection & prerequisite guidance
- **STATUS: DONE (2026-07-05).** `ador/doctor.py` + `tests/test_doctor.py`
  (11 tests, all green; suite 186 passing) + `05_SoftwareDocu/Component_Doctor.md`.
  Pure detection through the injectable runner (`detect_os/git/runtimes/
  platform_cli/executor`, `auth_status`, `detect_all`) + OS-specific
  `guidance_for` and `auth_component_for_kind`. WSL UTF-16 output scrubbed;
  token guidance states the format but never a value.
- **Model: Claude Sonnet 5 — Reasoning: Medium.**
- **Why:** well-bounded probing + curated OS-specific text; mechanical but must be
  read-only/non-destructive and correct per OS. Not high-ambiguity.
- **Deliverables:** `ador/doctor.py` — pure detection via the injectable command
  runner: `detect_os()`, `detect_runtimes()` (docker/podman/wsl distros),
  `detect_platform_cli(kind)` + `auth_status`, `detect_executor()`. A
  `guidance_for(component, os)` returning the exact Windows/Ubuntu install/setup
  text from the Prompt Catalog (Phase A). No prompting here (that's T3); this is
  the data/text layer the wizard and a future `ador doctor` command reuse.
- **Acceptance:** tests with a fake runner for present/absent/unauthenticated
  permutations; guidance text asserted per OS; no real network/CLI calls.

### Task 3 — The `ador init` wizard
- **STATUS: DONE (2026-07-05).** `ador/wizard.py` + `ador init` in `cli.py` +
  `tests/test_wizard.py` (8 tests, all green; suite 194 passing) +
  `05_SoftwareDocu/Component_Wizard.md`. Full Phase A-I flow; injectable asker/
  runner/OS-key; stdlib TOML emitter (literal strings for regex/paths, no
  tomli_w); write-then-validate guard (never saves invalid); non-interactive
  `--answers` fail-fast + reproducible. LIVE-VERIFIED on Windows: `ador init
  cockpit-gcp --answers answers.toml` produced a minimal config that
  `config validate` accepts. The golden test asserts every emitted config
  passes validate_config.
- **Model: Claude Opus 4.8 — Reasoning: High (use maximum thinking budget).**
- **Why:** the UX-critical core — branching flow (Phases A–I), per-field
  validation with friendly re-prompting, detection-vs-ask logic, and writing a
  minimal, valid profile. Highest judgment density in the plan; correctness and
  tone both matter. Worth the strongest model at the deepest reasoning.
- **Deliverables:** `ador/wizard.py` — an injectable prompt primitive
  (`ask(field_spec, ask_fn=input)`) supporting description/example/default/
  validate/choices/re-prompt; the full Phase A–I flow assembling a `Config`;
  a summary renderer; write-through to `ProfileStore` + `validate_config` loop;
  the `--non-interactive --answers FILE` path (D7). CLI: `ador init`.
- **Acceptance:** drive the whole flow with a scripted `ask_fn` (list of answers)
  + a fake detector; assert the emitted `config.toml` **passes `validate_config`**;
  negative tests (invalid repo path re-prompts; bad regex re-prompts; branch
  template not matching the rule re-prompts; refusing to save an invalid profile);
  `--answers` file reproduces a known profile byte-for-byte (minus timestamps).

### Task 4 — Profile management CLI + `--profile` integration
- **STATUS: DONE (2026-07-05).** `profile` subparser + `_cmd_profile` in
  `cli.py`, global `--profile`, `_load` refactored to `resolve_config_path`
  (touches the resolved profile) + `tests/test_profile_cli.py` (8 tests; suite
  202 passing) + Component_CLI.md updated. LIVE-VERIFIED: `profile list/use/
  path` + `--profile cockpit-gcp config validate` resolve correctly and bump
  use_count/last_used_at; explicit `-c` still wins (regression-tested).
- **Model: Claude Sonnet 5 — Reasoning: Medium-High.**
- **Why:** mostly mechanical CRUD handlers, but the `--profile`/`-c` resolution
  must integrate into `_load`/`_engine`/`_build_parser` **without breaking any
  existing command** — that integration is the part needing care.
- **Deliverables:** `profile` subparser (`list/show/use/rename/delete/path`) +
  handlers in `cli.py`; global `--profile`; wire `resolve_config_path` (T1) into
  `_load`; bump `use_count`/`last_used_at` on resolution. `delete` needs `--force`.
- **Acceptance:** smoke tests through `main()` for each subcommand against a tmp
  `ADOR_HOME`; existing-command regression (a bare `ador status -c file` behaves
  exactly as before); `delete` without `--force` refuses; `list` on empty home is
  clean.

### Task 5 — Profile statistics
- **STATUS: DONE (2026-07-05).** `metrics.profile_stats(db_path)` (zeros on a
  missing DB) + wired into `_profile_metrics`/`_profile_list`/`_profile_show`
  in cli.py; `tests/test_metrics.py` (+1) and `tests/test_profile_cli.py` (+1);
  suite 204 passing. LIVE-VERIFIED: seeded the cockpit-gcp metrics DB -> `list`
  shows RUNS/MERGED, `show` shows runs/merged/failed/success_rate/launches/
  tokens/avg_span/last_run. Honors a custom `[metrics] db_path`, else
  `<store_root>/metrics.db`.
- **Model: Claude Sonnet 5 — Reasoning: Medium.**
- **Why:** bounded join of `metrics.load_summaries` (existing) to a profile;
  straightforward once T1/T4 exist.
- **Deliverables:** stats surfaced in `profile list` (RUNS, MERGED) and
  `profile show` (runs, merged, failed, success rate, last-run, avg span, tokens,
  created/last-used/use_count). Computed from the profile's metrics DB; empty-DB
  case renders zeros, not errors.
- **Acceptance:** tests seeding a tiny metrics DB in a profile and asserting the
  rendered rows; empty-store renders cleanly.

### Task 6 — Test suite (consolidation) & edge cases
- **STATUS: DONE (2026-07-05).** Shared `tests/conftest.py` `ador_home`
  fixture; `test_smoke.py` extended with `ador init` via main() (happy +
  missing/invalid answers + wizard-error paths); `test_wizard.py` extended
  with the previously-uncovered branches (corporate host, custom budgets,
  custom agent-name/slug, non-interactive missing-required fail-fast) and the
  interactive `ConsoleAsker` + `ask()` re-prompt. Suite 213 passing, ruff
  clean. Coverage across T1-T6: corrupt profile, name/rename collisions,
  resolution precedence, re-prompt loops, non-interactive answers, cross-OS
  home resolution, and every new public surface (happy + negative).
- **Model: Claude Sonnet 5 — Reasoning: Medium-High.**
- **Why:** thorough offline test design (injection of `ask_fn`, detector, runner,
  clock) per the Testing Rules; needs breadth and negative-path rigor.
- **Deliverables:** `tests/test_profiles.py`, `tests/test_wizard.py`,
  `tests/test_doctor.py`; extend `test_smoke.py` for the new CLI; a fixture for a
  tmp `ADOR_HOME`. Cover corrupt profile, name collisions, resolution precedence,
  re-prompt loops, non-interactive answers, cross-OS home resolution.
- **Acceptance:** whole suite green on Windows and Ubuntu runners; coverage of both
  happy and negative paths for each new public surface.

### Task 7 — Cross-platform verification (manual E2E)
- **STATUS: DONE (2026-07-05).** Both hosts green; recorded in
  Prerequisites_Check_Report.md section 17. Windows 11 (native `ador`, %APPDATA%
  home) live throughout T3-T5. Ubuntu 24.04/WSL2 (POSIX, `python3 -m ador` -
  stdlib-only, no venv): `~/.config/ador` + XDG home resolution, native
  docker/podman detection (WSL not probed), `ador init` -> validated POSIX
  profile, `--profile`/`profile`/`status` resolution all clean. Guidance text
  confirmed live on a host genuinely lacking glab (Linux .deb/apt + token
  guidance shown correctly); no drift requiring a code change.
- **Model: Claude Sonnet 5 — Reasoning: Medium.**
- **Why:** execution + observation across OSes; judgment on OS-specific behavior
  (paths, WSL runtime string, glab install differences), not deep design.
- **Deliverables:** run `ador init` end-to-end on Windows 11 (WSL-wrapped runtime)
  and Ubuntu 22+ (native docker/podman); confirm the profile validates, resolves,
  and a `--dry-run` picks work; record findings in the prereq report. Verify the
  guidance text matches reality (install commands current).
- **Acceptance:** a short verification section added to
  `Prerequisites_Check_Report.md` with both OSes green; any drift fixed.

### Task 8 — Documentation
- **STATUS: DONE (2026-07-05). FEATURE COMPLETE - all 8 tasks done.**
  Design 12a reconciled (init/profile are CLI config helpers, not a GUI);
  Configuration_Reference.md "Profiles & assisted setup" section;
  `00_Planning/Onboarding_New_Project.md` (new - prerequisites for Windows +
  Ubuntu, the prompt list, the answers-file format, the use flow); README
  package layout + phase 8; Component_Profiles scope note updated (cross-refs
  Wizard/Doctor/CLI docs); AGENTS.md status. Suite 213 passing, ruff clean.
- **Model: Claude Haiku 4.5 — Reasoning: Low** for the template-driven component
  docs and reference mirroring; **escalate the design-12a reconciliation + the
  onboarding guide to Claude Sonnet 5 — Reasoning: Medium** (those need judgment).
- **Why:** most of this is writing to a known template and mirroring decided
  behavior (cheap model is right); only the 12a wording and the onboarding
  narrative need more care.
- **Deliverables:** `05_SoftwareDocu/Component_Profiles.md` (new);
  update `Component_CLI.md` (new commands, `--profile`); a "Profiles & assisted
  setup" section in `Configuration_Reference.md`; a new
  `01_Documentation`/`00_Planning` **Onboarding a New Project** guide that captures
  the Phase-A prerequisite text (install glab/gh, create a token, pick a runtime)
  for Windows and Ubuntu; a one-sentence 12a note that CLI init/profile helpers are
  in-scope (not a GUI); README package-layout + phases update; `AGENTS.md` status.
- **Acceptance:** docs match final behavior; `ador init`/`ador profile` examples
  runnable as written; license headers + `@version` bumps present.

---

## 7. Testing strategy (cross-cutting)

- **Everything offline & injected.** The wizard takes an `ask_fn` (default
  `input`), the detector takes the existing injectable command runner, and a clock/
  timestamp function is injectable for deterministic `profile.json`. No real
  glab/gh/git/docker in unit tests (Testing Rules).
- **Prove each contract twice** — happy path + a negative at the trust boundary
  (human-entered fields, detected CLI output, corrupt `profile.json`).
- **The golden assertion for the wizard:** any profile it writes must pass
  `validate_config` — this ties the new surface to the existing safety net.

## 8. Cross-platform matrix (must all pass)

| Concern | Windows 11 | Ubuntu 22+ |
|---|---|---|
| Config home | `%APPDATA%\ador` | `~/.config/ador` (XDG) |
| Runtime string | `wsl -d <distro> -- docker\|podman` | `docker` / `podman` |
| glab install text | winget/scoop | `.deb`/apt |
| Path entry/validation | `D:/...` accepted, normalized | `/home/...` |
| Non-interactive (no TTY) | supported via `--answers` | supported via `--answers` |

## 9. Risks & open decisions (resolve in Task 1)

- **R1 — Secrets discipline.** The wizard must never echo or persist token values;
  only key *names* and setup guidance. (Mitigation: D5; review in T3.)
- **R2 — Push-rule auto-fetch needs a token/scope.** If unavailable, fall back to
  asking (E1a). Never block setup on it.
- **R3 — `host` runtime.** Offer it but print a loud "no isolation" warning
  (ties to the runtime discussion; keep it opt-in, not default).
- **R4 — Existing single-`config.toml` users.** Resolution order (D3) must keep
  today's behavior when no profile exists — regression-tested in T4.
- **R5 — Windows Constrained Language Mode / no-TTY servers.** Interactive prompts
  use plain `input()`; the `--answers` path covers headless/automated setup.

## 10. Model & reasoning summary

| Task | Model | Reasoning | Rationale |
|---|---|---|---|
| 1 Foundation (home + store) | Claude Opus 4.8 | High | Cross-platform + schema; everything depends on it |
| 2 Detection & guidance | Claude Sonnet 5 | Medium | Bounded probing + curated OS text |
| 3 `ador init` wizard | Claude Opus 4.8 | High (max) | Highest-judgment UX/branching/validation core |
| 4 Profile CLI + `--profile` | Claude Sonnet 5 | Medium-High | CRUD + careful non-breaking integration |
| 5 Statistics | Claude Sonnet 5 | Medium | Bounded join to existing metrics |
| 6 Tests (consolidation) | Claude Sonnet 5 | Medium-High | Breadth + negative-path rigor |
| 7 Cross-platform E2E | Claude Sonnet 5 | Medium | Execution/observation across OSes |
| 8 Documentation | Claude Haiku 4.5 (Sonnet 5 for 12a/onboarding) | Low (Medium for judgment parts) | Template mirroring vs. narrative judgment |

> Reasoning-level guide for the implementer: **High** = deliberate step-by-step
> design, weigh alternatives before coding (use the largest thinking budget for
> Task 3). **Medium** = plan the change, then implement against the spec.
> **Low** = execute the specified change directly.

## 11. Definition of done (whole feature)

1. `ador init` produces a valid, minimal profile on Windows and Ubuntu, guiding the
   user through every non-ADOR prerequisite with explicit examples.
2. `ador profile list/show/use/rename/delete/path` work with dates + statistics.
3. `--profile NAME` resolves config for all existing commands; `-c FILE` still wins;
   no regression for single-`config.toml` users.
4. Suite green (happy + negative) offline on both OSes; ruff clean; Doxygen/license/
   `@version` conventions followed; docs updated in the same changes.
5. No secrets ever written to a profile; design 12a reconciled (CLI helper, not GUI).

<!-- END OF FILE -->
