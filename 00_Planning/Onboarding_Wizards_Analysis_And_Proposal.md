<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Analysis & Proposal: Guided Onboarding Wizards for ADORE + Agentic Development Workflow

> Status: **analysis only — nothing here is implemented.** This document
> analyzes how the two workflows are deployed today and proposes a design
> direction for two guided onboarding wizards (new project / existing project)
> aimed at operators with **no repo-setup knowledge**.
>
> Inputs analyzed: this repository (ADORE 1.0.0) and
> `2026_AgenticDevelopmentWorkflowTemplate` (template 0.4.0).
>
> Historical note: this repository was renamed from Agentic Delivery Orchestrator (ADOR) to ADORE for the 1.0.0 hard cut.

---

## 0. Problem statement (one paragraph)

Onboarding one runtime project today means deploying **two products in the
right order with cross-referencing configuration**: the executor-side agentic
workflow (template copied into the target repo, `.agentic/workflow.toml`
hand-edited) and the orchestrator (ADORE runtime bundle unpacked, `uv sync`,
`adore init` profile wizard, secrets, container images hand-built, forge labels
hand-created, optional service install). Each product has good local tooling,
but the **end-to-end chain is manual, per-repo personalized, and assumes an
operator who already understands git, forges, tokens, containers, and WSL**.
The goal is a single guided wizard suite (**WAEGIS** + **WADORE**, naming in
§2.0) with *new project* and *adopt existing project* journeys, that detects
the machine and environment, performs
every automatable step itself, guides the human through the inherently manual
steps (e.g. GitLab token creation), and **verifies after every step**, so a
person without repo-setup knowledge can reach a working, supervised first run.

---

## 1. Current state analysis

### 1.1 The full manual chain today (what an operator actually does)

Onboarding one repo end-to-end currently spans **both products and ~20 manual
decision points**. Consolidated from `01_Documentation/Step_By_Step_Setup.md`,
`01_Documentation/Onboarding_New_Project.md`, and the template's
`How_To_Start_A_New_Project.md`:

| # | Step | Owner today | Automated? | Verified today? |
|---|---|---|---|---|
| 1 | Install git, uv, Python, forge CLI (glab/gh) | Human | No (guidance text only) | Only if wizard is run |
| 2 | Enable WSL2 + distro (Windows), install docker/podman | Human | No | Partially (doctor probes presence) |
| 3 | Create forge PAT (browser), `glab/gh auth login` | Human | Inherently manual | `auth status` probe exists |
| 4 | Create/locate the forge repo, clone it locally | Human | No | No |
| 5 | Create forge labels (`agent-ready`, `agent-hold`, `no-agent`, `agent-revise`) | Human | No | No |
| 6 | Copy template into repo (`create_project_from_template.py`) | Script | Yes (copy only) | No post-copy check |
| 7 | Edit `.agentic/workflow.toml` (roots, gates, write_zones) | Human | No | Only via "sanity-check prompt" pasted into an agent |
| 8 | Keep `write_zones` aligned with roots (the documented gotcha) | Human | No | No |
| 9 | Commit the adoption, verify `.agentic/tools/run` works | Human | No | Manual |
| 10 | Unpack ADORE bundle, `uv sync --frozen`, `adore --version` | Human | Scripted commands | Manual eyeball |
| 11 | `adore init` profile wizard (phases A–I) | **Wizard exists** | Yes | Yes (write-then-validate guard) |
| 12 | `.env` secrets (provider keys, token env names) | Human | No | No probe that keys actually work |
| 13 | Build `adore-executor-base`, egress proxy, project image | Human | No (documented docker commands) | `docker image inspect` by hand |
| 14 | Author the runtime-project Dockerfile (project toolchain) | Human | No (open TODO item) | No |
| 15 | Egress posture decision (`open`/`allowlist-proxy`/`none`) | Human | No | Install-script guardrails only |
| 16 | `config validate`, `run --dry-run`, `run --once` | Human | Commands exist | Human reads JSON output |
| 17 | Service install (Task Scheduler / systemd) | Scripts exist | Yes | Fail-fast scripts |
| 18 | Host quirks (UID 1000 mismatch → ACL/chmod, silk04 case) | Human | No (TODO documents it) | No |

Observations:

- The **only genuinely wizard-shaped piece today is `adore init`** (steps 11)
  plus its doctor probes. Everything before and after it is documentation.
- The template side has **no interactivity at all**: a copy script plus a
  "read this and edit one file" guide. The single most error-prone step
  (workflow.toml roots vs write_zones) is guarded only by a paragraph titled
  "the one gotcha".
- **Cross-product coupling is invisible**: the ADORE profile's branch template
  must satisfy the forge push rule; the executor image must contain the target
  project's toolchain *and* be able to run the repo's `.agentic` CLI; labels
  configured in ADORE must exist on the forge; the reviewer username must be a
  real forge user. No tool checks any of these ends-to-ends today.
- Verification is **front-loaded, not per-step**: `adore init` validates its own
  output, but a mistake at step 5 (labels) or 13 (image) surfaces only at the
  first real run, deep in the poll loop, with an error message written for the
  ADORE author, not for a novice.

### 1.2 Assets to build on — ADORE side

Strong foundations already exist and should be **reused, not reimplemented**:

- **`adore/wizard.py`** — the prompt primitive (`FieldSpec` + `ask()`:
  description, example, default, validate, re-prompt), `ConsoleAsker` /
  `ScriptedAsker`, minimal-config emission, and the *never-save-invalid* guard.
  Crucially, **`adore init --answers FILE` is a machine-drivable seam**: an
  outer tool can compute the answers and run the existing wizard
  non-interactively.
- **`adore/doctor.py`** — injectable, offline-testable detection
  (`detect_os/git/runtimes/platform_cli/auth_status/executor`, `detect_all`)
  plus curated OS-keyed guidance text. Explicitly designed so "a future
  `adore doctor` command can render the same aggregate" — that command still
  does not exist.
- **`adore/profiles.py`** — config home (`%APPDATA%`/`~/.config/adore`/
  `ADORE_HOME`), one install serving many projects, per-profile stats.
- **Versioned runtime bundles** (`02_Tools/package_runtime.*` →
  `07_Delivery/adore-runtime-x.y.z.{zip,tar.gz}`) — a clean payload format the
  wizard suite can download/unpack/upgrade.
- **Deployment scripts** (`04_Software/deploy/`) — fail-fast, idempotent,
  secrets-never-in-argv; already the right building block for the final phase.

Known gaps (from component docs and `TODO.md`):

- Doctor reports **presence, not versions-vs-requirements**; no WSL-internal
  runtime probing; no `adore doctor` CLI.
- No image scaffolding (`Runtime-Project Image Scaffolding` TODO): the operator
  authors a project Dockerfile by hand.
- `adore config set` is a stub — there is no safe post-init config editing.
- No self-contained distribution (`Native App / Executable Packaging` TODO):
  Python 3.11 + uv are themselves prerequisites the operator installs.
- Executor container UID alignment (TODO) still needs per-host manual ACL
  remediation on mismatched-UID hosts.

### 1.3 Assets to build on — template side

- **`02_Tools/create_project_from_template.py`** — safe copy with `--dry-run`,
  `--force`, `--existing-repo`; refuses overwrites by default. Good primitive,
  no intelligence.
- **The delivered `.agentic/` payload** — self-contained CLI (stdlib-only,
  Python 3.11+), tools (`run.ps1/sh`, `install.ps1/sh`), hooks, skills, agent
  adapters (`.codex/`, `.claude/`, `.pi/`, `.opencode/`, `.qwen/`), and the
  **adoption workflow stages** (`adoption-intake → … → adoption-delivery`)
  with `components.toml` and baseline reports — i.e. the *in-repo* half of
  "adopt an existing project" already exists as an agent-driven workflow.
- **`workflow.toml` is the single configuration surface** — everything the
  new-project wizard must generate for the executor side lives in one file.

Known gaps:

- **No installed-version manifest.** A repo that adopted template 0.3.0 has no
  machine-readable record of which template version its `.agentic/` came from
  or which files were locally edited. Upgrading is therefore blunt
  (`--force` = overwrite everything, or manual diffing). This blocks any
  serious `doctor`/`upgrade` story and is the most important structural gap on
  the template side.
- No detection of the target repo's actual layout/language to prefill
  `workflow.toml`; no post-copy validation (the "sanity check" is a prompt the
  human pastes into an agent).
- `[gates] test/lint` start empty and silently do nothing until filled.

### 1.4 Gap summary (what the wizards must add)

1. **Machine/environment audit** before anything else: OS + version, arch,
   disk space, RAM, admin rights, virtualization/WSL2 availability, network
   reachability, proxy/TLS posture, package-manager availability.
2. **Acting, not only guiding**, wherever safe: installing CLIs, creating
   labels, generating configs, building images — with human confirmation.
3. **Guided manual steps with verification**: token creation cannot be
   automated, but the wizard can open the right URL, explain the exact scopes,
   and then *prove* the result (`glab auth status`, then an API call that
   actually requires the `api` scope).
4. **A check after every step** (explicit user requirement) with resumability.
5. **Cross-product end-to-end verification**: the chain is only "done" when a
   synthetic ticket flows label → gates → draft MR under supervision.
6. **Corporate-restriction detection** with extensive, novice-readable
   blocking-point reports.
7. **Lifecycle commands** for an already-onboarded repo: analyze, doctor,
   upgrade.

---

## 2. Proposal: one wizard suite (WAEGIS + WADORE), one step engine

### 2.0 Naming (DECIDED 2026-07-11 — closes D1)

| Component | Full name | Acronym | CLI |
|---|---|---|---|
| Executor-side system (today "Agentic Development Workflow Template") | Agentic Engineering Governance & Integrity System | **AEGIS** | **`aegis`** (renamed from `agentic-workflow`) |
| Orchestrator (today "ADORE") | Agentic Delivery Orchestrator & Runtime Engine | **ADORE** | `adore` (renamed from `adore`) |
| Repo wizard | Wizard for AEGIS | **WAEGIS** ("way-jis") | `waegis` |
| Host/orchestrator wizard | Wizard for ADORE | **WADORE** | `wadore` |

Decision trail (kept so the reasoning is not lost): "Companion" was only a
placeholder. Rejected candidates: *ASES* (misreads badly in English), *AGED*
(reads as "old"), plain *ADO* (universally means Azure DevOps in corporate
settings), *ADORE* kept as-is (risks being parsed as "ADO + R(andstad)"; the
product must not be linkable to examplex). AEGIS was chosen because "under
the aegis of" = under the protection and authority of — exactly the
governance + integrity role; "Integrity" names the traceability/fail-closed
half that "governance" alone misses. ADORE honestly names the product's two
halves: the thick conductor (Orchestrator) and the isolation/execution layer
(Runtime Engine). Accepted trade-off: AEGIS is a popular name elsewhere (US
Navy combat system, a 2FA app) — no collision in the agentic/devtools niche,
but docs should always pair it as "AEGIS workflow" / "the AEGIS system" for
searchability. The `agentic-workflow` → `aegis` CLI rename is a **breaking
CLI-contract change → MAJOR AEGIS release** per the template repo's SemVer
rules (wrappers `run.ps1/sh`, `install.ps1/sh`, hooks, agent adapters, and
ADORE's gate-protocol invocations must move in the same change).

**The mythology hook (keep for stakeholder presentations):** in Greek
mythology the *aegis* is the shield of Zeus and Athena — "under the aegis of"
survives in modern English as *under the protection and authority of*. The
story maps onto the products one-to-one and is deck-ready:

- **AEGIS is the shield**: every change an agent makes happens *under the
  aegis* — gates, write zones, guardrails, requirement traceability,
  integrity checks. Athena, who bears the aegis, is the goddess of wisdom
  **and of skilled craft** — the patron of engineering work.
- **ADORE bears the shield**: the orchestrator carries the aegis while it
  conducts the work and delivers the result (the draft MR) — but it is never
  the final authority; the human who merges is.
- **WAEGIS / WADORE play Hephaestus**, the smith god who (in several
  tellings) forged the aegis itself: the wizards forge and fit the armor —
  per repo and per host — before any work begins.

The two wizards are **two entry points over one shared step engine, shipped
as one self-contained artifact** (one thing to package, version, and update):

- **WAEGIS** owns the repo-side journey — phases P0–P4 below, in both the
  new-project and existing-project variants — plus repo-level
  doctor/analyze/upgrade via the install manifest (§2.5).
- **WADORE** owns the host/orchestrator journey (P5–P8) and therefore the
  full end-to-end chain; pointed at a repo without an AEGIS install manifest,
  it **delegates to the WAEGIS journey inline**, then continues with labels,
  image, profile, synthetic ticket, and service.

The suite is a separate small product that treats the ADORE runtime bundle
and the AEGIS payload as **versioned payloads it installs and upgrades**, and
drives their existing entry points (`adore init --answers`,
`create_project_from_template.py` semantics, `deploy/install-*`) rather than
reimplementing them. (Sections below still use today's command names `adore`
and `agentic-workflow` when referring to the currently implemented seams.)

### 2.1 The step engine (the core idea)

Both wizards are **data: an ordered catalog of steps executed by one engine**.
Every step declares the same contract:

```text
Step
  id             stable key, e.g. "forge.token", "image.project-build"
  title + why    novice-readable: what this is and why it is needed
  preconditions  step ids that must be green first
  automation     auto | assisted (wizard acts, human confirms) | manual (human acts, wizard guides + verifies)
  detect()       is it already satisfied? (idempotent, read-only)
  act()          perform / guide the step
  verify()       machine-checkable postcondition — REQUIRED, never optional
  on_fail        novice-readable diagnosis + remediation + "ask IT" text where relevant
  record         result journaled to the run checkpoint file
```

Engine behaviors:

- **detect → skip**: re-running a wizard on a half-configured machine is safe
  and fast; already-green steps show as ✓ and are skipped. This single
  property gives us *resume after abort*, *idempotent re-run*, and *"adopt a
  partially set-up repo"* for free.
- **verify after every act** — the user's core requirement. A step is never
  green because the operator *said* they did it; only because the probe passed.
- **Checkpoint journal** per wizard run (JSON in the wizard-suite home):
  auditable record of what was detected, chosen, done, and verified — also the
  input for `doctor` later.
- **Plan preview** ("terraform plan" style): before mutating anything, show
  the full list of steps with what each will change; the operator approves the
  plan, then approves destructive/outward-facing steps individually.
- **Every prompt** keeps the proven `adore init` shape: description, example,
  detected default, validation, re-prompt. Novice mode adds the "why".

### 2.2 Wizard N — new project

Phases (each phase = several steps under the contract above):

- **P0 Machine audit** — OS/version (Win 11 / Ubuntu 22+ supported matrix),
  arch, **free disk space** (images + worktrees + venvs need a stated minimum,
  e.g. ≥ 20 GB), RAM (containers), admin rights, virtualization flag / WSL2
  state, terminal capabilities. Output: environment report + go/no-go with
  reasons.
- **P1 Network & corporate posture** — reachability matrix (forge host, model
  provider endpoints, container registry, PyPI, template/ADORE update source),
  proxy detection, TLS-interception detection, package-manager probe
  (`winget`/`apt` actually usable?). See §4.
- **P2 Prerequisites** — git, forge CLI, uv, container runtime (incl.
  WSL2-distro-internal probing — closes a documented doctor gap). Each:
  detect → offer install (assisted, via winget/apt where allowed) → verify by
  running the tool.
- **P3 Forge setup** — choose GitLab/GitHub + host; **token creation as a
  first-class guided manual step** (open browser at the right page, state the
  exact scope/role, explain `glpat-` format, never echo the value); verify
  auth *and effective scope* with a real API probe; **create the repo**
  (assisted, via `glab/gh repo create`) or select an existing one; **create
  the four labels**; detect push rules/protected branches via API and record
  them for P6.
- **P4 Repo bootstrap (executor workflow)** — clone; copy the template payload
  (with the new **install manifest**, §2.5); generate `workflow.toml` from
  answers ("where will your code live?") with **write_zones kept aligned
  automatically** — the gotcha becomes impossible; run `.agentic/tools/run
  --help` and a `gates run` smoke test as the verify; commit.
- **P5 Executor & image** — choose executor CLI + model + auth mode; write
  `.env` keys (names guided, values typed by the human, never echoed);
  **generate the runtime-project Dockerfile** from the declared/detected
  toolchain (direct implementation of the existing `Runtime-Project Image
  Scaffolding` TODO); build base + egress-proxy + project images; verify by
  running the project's `.agentic` CLI *inside* the container and running
  `[container] required_tool_checks`.
- **P6 ADORE profile** — WADORE computes an `adore init --answers` file from
  everything already collected (no re-asking!) and drives the existing wizard;
  `config validate`; UID-alignment check (detect host UID vs image UID and
  apply the ratified fix from the TODO).
- **P7 Supervised first run (the end-to-end proof)** — create a **synthetic
  hello-world ticket**, label it `agent-ready`, run `adore run --once`, watch
  it produce a draft MR, walk the human through reviewing and closing it,
  clean up. Only after this does the wizard call the onboarding *done*.
- **P8 Optional service** — egress posture decision (recorded per the
  `Production Security Sign-Off` TODO checklist), then
  `deploy/install-windows.ps1` / `install-ubuntu.sh`.

### 2.3 Wizard E — existing project adoption

Same engine and phases P0–P3, then diverges:

- **P4a Repo analysis** — read-only: repo type (languages, build systems,
  source/test layout, mono-repo vs single package, submodules, LFS, existing
  CI, `.gitattributes`/line endings, size), plus detection of a **prior or
  partial adoption** (existing `.agentic/`, its manifest/version, local
  drift). Deterministic heuristics first; optional AI assist (§3.2) to
  propose `workflow.toml` values (roots, language, gate commands) — always
  shown as a proposal the human confirms.
- **P4b Safe adoption copy** — never-overwrite copy with a **conflict report**
  (which files exist locally, diff summary, per-file keep/replace decision);
  write the install manifest; generate `workflow.toml` from the *analysis*
  rather than from questions where possible.
- **P4c Hand-off to the in-repo adoption workflow** — the template already
  ships `adoption-intake → … → adoption-delivery` and the `agentic-adoption`
  skill; WAEGIS's job ends at "the repo is ready and the operator knows
  the exact prompt to start component mapping", not at re-doing that workflow.
- **P5–P8** identical to Wizard N (image, profile, supervised run, service) —
  with P5 seeded by the toolchain the analysis detected.

### 2.4 Lifecycle commands (beyond the two wizards)

- **`waegis doctor --repo PATH` / `wadore doctor [--profile NAME]`** (both
  entry points expose `doctor`; WAEGIS scopes machine + repo, WADORE scopes
  machine + host + profile + service + the full chain) — machine checks
  (P0–P2 probes), repo checks (manifest present? template version? local
  drift? workflow.toml roots still match reality? write_zones aligned?),
  ADORE checks (profile validates? images exist and match Dockerfiles? forge
  auth alive? labels exist? service state? state-store health), each with
  novice-readable fix-its. Human + JSON output, meaningful exit codes. This
  also finally delivers the `adore doctor` command the doctor component
  anticipated.
- **`waegis analyze --repo PATH`** — read-only inventory: which of the two
  workflows are installed, at which versions, with what drift. (Doctor =
  analyze + health verdicts.)
- **`waegis upgrade --repo` + `wadore upgrade`** — per-repo template upgrade using the install
  manifest (§2.5) and ADORE-runtime upgrade by installing bundle x.y.z+1
  side-by-side, re-running `uv sync --frozen`, migrating/re-validating
  profiles, and swapping only after self-test passes.

### 2.5 The enabling structural change: an install manifest

For `doctor`/`analyze`/`upgrade` to work, the template copy step must start
stamping the target repo, e.g. `.agentic/install-manifest.json`:

```json
{
  "template_version": "0.4.0",
  "installed_at": "2026-07-11",
  "installed_by": "waegis 0.1.0",
  "files": { ".agentic/cli/...": "sha256:...", "AGENTS.md": "sha256:..." }
}
```

With original-hash records, upgrades become **three-way aware**: for each file
the tool knows *shipped-original*, *current-local*, and *new-template*, so it
can auto-apply unmodified files, keep local-only edits, and surface true
conflicts only. This is the same model as package managers' conffile handling
and is the single highest-leverage change for the "update the versions of the
implementations for that repo" requirement. It is a small, backward-compatible
addition to the template product.

---

## 3. Design questions the user asked

### 3.1 GUI vs TUI vs CLI

Recommendation: **one headless step engine + two thin frontends** — an
interactive console flow and a local-browser GUI — and *skip a TUI framework*.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Console prompts** (extend the proven `adore init` style) | Works everywhere incl. SSH/headless servers (the silk04 case); stdlib-only; scriptable via answers files; already field-tested | Least discoverable for novices; long flows feel endless; no progress overview | **Keep — mandatory baseline** and the CI/automation surface |
| **TUI** (Textual/urwid checklists, panes) | Nicer progress view in the same terminal | Third-party dependency (both repos are deliberately stdlib-only); Windows-terminal quirks; serves neither audience better than the other two options | **Skip** (revisit only if the GUI is rejected) |
| **Local-web GUI** (the wizard serves a single-page UI on `http://127.0.0.1:<port>` from the bundled runtime — stdlib `http.server`, no external assets) | Best for the stated audience ("no repo-setup knowledge"): step list with ✓/✗/current, rich explanations, copyable commands, links that open the forge token page; zero install, works on Win 11 and Ubuntu 22 desktop; no framework needed if kept deliberately simple | Needs a browser + desktop session (not for headless — console covers that); modest extra code for the JSON step API | **Add as the novice frontend** |

Both frontends drive the same engine and the same answers-file format, so
every flow is testable offline and automatable, and the GUI can display the
exact console commands it runs (teaching instead of hiding).

### 3.2 Deterministic vs AI-assisted

Recommendation: **deterministic core, optional AI advisor — AI proposes,
deterministic code validates, human confirms.**

- Everything that mutates state (copies, config emission, label creation,
  image builds, service install) and everything that verifies must be
  **deterministic and offline-testable** — this also matches both repos'
  testing rules (offline, fail-closed, injectable runners).
- AI adds value in exactly the fuzzy spots:
  1. **Repo analysis prefill** (Wizard E): propose source/test roots, language,
     and real `gates` commands from README/CI files when heuristics are
     ambiguous.
  2. **Dockerfile drafting** for the runtime-project image from the detected
     toolchain.
  3. **Failure explanation**: translate a raw probe failure (proxy 407, TLS
     chain error, `winget` policy block) into a novice-readable explanation
     and a ready-to-send IT request.
  4. **"Explain this step"** free-form help inside either frontend.
- **Backends**: one OpenAI-compatible HTTP client covers online APIs and local
  Ollama / LM Studio endpoints; provider/endpoint/model configurable.
- **Hard rules**: the wizard suite must be **fully functional with AI disabled**
  (deterministic fallbacks everywhere — corporate hosts may allow no egress
  and no local model); AI never writes a file directly — its output enters the
  same validate-then-confirm path as human answers; **explicit consent step
  before any repo content is sent to an online endpoint**, with a
  "local-model-or-off" default in corporate mode; never send secrets or `.env`
  content to any model.

### 3.3 Self-contained distribution (Windows 11 + Ubuntu 22)

The wizard suite must not itself have prerequisites — otherwise it inherits the
problem it solves. Options:

| Option | Notes | Verdict |
|---|---|---|
| `zipapp`/scripts | Needs host Python 3.11+ — the very prerequisite novices lack | Rejected as primary |
| PyInstaller/Nuitka onefile | Single file, but AV/SmartScreen false positives are common on corporate Windows; slow unpack-on-start | Fallback option |
| **App directory with embedded CPython** (python-build-standalone; zip for Windows, tar.gz for Linux built against Ubuntu 22's glibc 2.35 or older) | No admin rights needed, no install, AV-friendlier, transparent contents, trivially side-by-side versionable (enables §3.4 staged updates) | **Recommended** |

This directly overlaps the existing `Native App / Executable Packaging` TODO —
solving it once for the wizard suite can solve it for ADORE too (the suite's
embedded Python can also run ADORE's venv bootstrap, removing the "install
Python + uv first" steps entirely). Same security properties as that TODO: no
secrets in the package, version derived from one source, contents verified by
the release script. Code signing for Windows is an open decision (§7).

### 3.4 Auto-update (if configured)

- **Opt-in only**, off by default; configured update source = a URL or an
  internal mirror/file share (corporate offline path).
- Three independently versioned artifacts: the **wizard suite itself**, the
  **ADORE runtime bundle**, the **AEGIS payload**. The suite checks a
  small signed release manifest (versions + sha256 + ed25519/minisign
  signature) and reports "updates available" in `doctor`.
- **Staged self-update**: download new app dir side-by-side → run its
  self-test → atomically swap a junction/symlink → keep the previous version
  for rollback. Never patch in place.
- **Payload updates are never silently applied to repos or hosts**: a new
  template version only enables `waegis upgrade --repo` (manifest-driven,
  §2.5, with plan preview); a new ADORE bundle only enables the guided runtime
  upgrade. Auto-update *checks and downloads*; a human applies.

### 3.5 Doctor / analyze / upgrade

Covered in §2.4–2.5; the key dependencies are the install manifest (template
side) and version-aware probes (extend `adore/doctor.py`'s `_probe` to compare
versions against requirements — already flagged there as future work).

---

## 4. Corporate environments and restriction detection

Principle: **probe, don't assume; and when blocked, produce a report a novice
can forward to IT verbatim.**

Probe matrix (P1 of both wizards, rerun by `doctor`):

| Probe | Method | If blocked → report contains |
|---|---|---|
| Proxy required | env vars + OS proxy settings + direct-vs-proxy connect test | Detected proxy, whether auth is required (407), which tools need proxy config (git, docker, glab, uv) and the exact per-tool settings |
| TLS interception | connect to a known host, compare presented chain to expected public CA | The intercepting CA's name; which trust stores need the corporate CA (git, Python/uv, container runtime, WSL distro); where to get the CA file (IT) |
| Forge reachability | HTTPS + API ping against the chosen host | Hostname/port to allowlist; note for self-hosted GitLab with custom CA |
| Model endpoint reachability | HTTPS ping per configured provider | Endpoint to allowlist, or "choose a local model / pre-provisioned image" alternative |
| Registry + PyPI reachability | pull/index probe | Mirror configuration option; "pre-provisioned no-network image" alternative (`egress mode none`) |
| Package manager usable | `winget --version` + a search; `apt-get update` dry probe | Policy block vs missing; portable-install alternatives that need no admin |
| Admin rights | elevation check | Which steps need elevation (WSL enable) vs which have no-admin paths |
| WSL2 available/allowed | `wsl --status`, virtualization flag | If disabled by policy: exact feature names IT must enable, or "use a Linux host instead" |
| Disk space / RAM | free space at chosen roots; total RAM | Stated minimums and what consumes them |
| Time skew | TLS handshake vs local clock | Auth failures explanation |

Every blocking-point message states: *what was attempted (exact command), what
happened (exact error), why the wizard needs it, what to ask IT for (copyable
request text), and which alternative path exists* (offline bundle, internal
mirror, allowlist-proxy, pre-provisioned image, different host). The optional
AI advisor (§3.2) can enrich these, but a deterministic template for each probe
must exist.

---

## 5. Operator-error detection and recovery

The wizards must assume answers will sometimes be wrong and catch them at the
step, not at the first real run:

- **Validate-and-probe every answer**, not just its format: a repo path must
  actually be a git repo with the expected remote; a WSL distro name must
  appear in `wsl -l -q`; a reviewer username must resolve via the forge API; a
  token must pass a call that *requires* the claimed scope; a branch template
  must satisfy the detected push rule (already proven in `adore init`); an
  image must contain the `required_tool_checks` and run the `.agentic` CLI.
- **Detect wrong selections after installs**: e.g. operator installed Docker
  Desktop instead of engine-in-WSL, or picked the wrong distro — the P2/P5
  verify probes fail with a "this is what I found instead" message and
  re-offer the detected choices.
- **Plan preview + per-step confirmation** for mutating steps; **read-only
  detect** for everything else, so a nervous operator can re-run safely.
- **Resume + undo notes**: the checkpoint journal records what was created
  (labels, repo, images, service) so an aborted onboarding can be resumed or
  cleanly rolled back (`wadore cleanup` mirroring `adore cleanup`'s
  philosophy: report corrupt/ambiguous state, never silently delete).
- **The synthetic-ticket supervised run (P7) is the ultimate error catcher**:
  it exercises labels, readiness, isolation, image, executor auth, gates,
  push rules, and reviewer assignment in one observable pass before any real
  ticket is touched.

---

## 6. Where the wizard suite lives, and reuse

Options considered:

1. **Extend ADORE** (`adore onboard ...`) — pro: doctor/wizard/profiles reuse is
   direct; con: ADORE then owns template deployment and forge repo creation,
   breaking its clean "orchestrate tickets" scope, and the wizard must run
   *before* ADORE is installed — a bootstrapping contradiction.
2. **Extend the template repo** — same contradiction mirrored (it would own
   ADORE install), plus the template payload should stay lean.
3. **A third, small product** that pins compatible payload versions
   (template ≥ 0.4.0, ADORE ≥ 0.5.1) and drives their public entry points —
   **recommended**. It can start life as a folder in this repo and split out
   later if needed.

Reuse plan: extract/depend on the proven primitives rather than fork them —
`FieldSpec`/`ask()` prompt shape, `doctor` probe+guidance model with the
injectable `CommandRunner`, the answers-file convention, and the
`create_project_from_template.py` copy semantics (extended with the manifest).
Contributions flow back: `adore doctor` CLI, version-aware probes, Dockerfile
scaffolding, UID-alignment fix, install manifest in the template.

---

## 7. Risks and open decisions

| # | Decision / risk | Notes |
|---|---|---|
| D1 | Product name + repo placement | **Naming DECIDED 2026-07-11 (§2.0): AEGIS / ADORE / WAEGIS / WADORE, CLIs `aegis` / `adore` / `waegis` / `wadore`.** Repo placement still open |
| D2 | Frontend set | Recommended: console + local-web GUI, no TUI — ratify |
| D3 | AI provider policy | Which endpoints are allowed by default; consent wording; corporate default = off/local |
| D4 | Windows code signing | Unsigned zips trip SmartScreen in some orgs; signing needs a cert and a release process |
| D5 | Forge repo creation rights | Some orgs forbid API repo creation; Wizard N needs a "repo was created for me by IT" branch |
| D6 | Install-manifest format | Belongs to the template product; must be added there (backward-compatible) before `upgrade` can exist |
| D7 | Compatibility matrix ownership | The wizard suite pins which AEGIS/ADORE versions it can install — where is that recorded and tested? |
| D8 | Scope creep risk | The step catalog will grow; the engine contract (§2.1) is the guardrail — new needs become new steps, not new mechanisms |
| D9 | Secrets handling in the GUI | Token values typed into a browser page must go only to 127.0.0.1 and never be journaled; ratify the exact mechanism |
| D10 | Ubuntu 22 floor | Embedded CPython build must target glibc ≤ 2.35; verify on a clean Ubuntu 22.04 VM early |
| D11 | Rename migration (AEGIS/ADORE) | `adore` → `adore` binary + package, `ADORE_HOME` → `ADORE_HOME` + config-home fallback or migration (live silk04 deploy!), service names, `package_runtime.*` bundle names, docs/PDFs; `agentic-workflow` → `aegis` CLI is a breaking contract change → MAJOR AEGIS release (wrappers, hooks, adapters, ADORE gate invocations move together). Repo folder names may stay — separate decision |

---

## 8. Suggested phasing (sequencing only — not an implementation plan)

1. **Foundations**: step-engine contract + checkpoint journal; machine/network
   probe set (P0–P2) as a standalone `doctor` (console output) — immediately
   useful on its own.
2. **Install manifest** in the template product + `analyze` for existing repos.
3. **Wizard N, console frontend**, driving existing seams
   (`create_project_from_template` semantics, generated `--answers` →
   `adore init`, `deploy/*`), including image scaffolding and the synthetic
   ticket run.
4. **Wizard E** (repo analysis + safe adoption + hand-off to the in-repo
   adoption workflow).
5. **Local-web GUI** over the same engine.
6. **Self-contained packaging** (embedded runtime) + **upgrade** command.
7. **AI advisor layer** (optional, last — everything must already work
   without it).

Each phase ends human-verified end-to-end on both Windows 11 and Ubuntu 22,
mirroring the E2E discipline used for the profiles feature (prereq report §17).

---

## 9. Definition of "good enough for a non-expert" (acceptance vision)

A person who has never set up a repository, on a fresh corporate Windows 11
laptop or Ubuntu 22 machine, can:

1. unzip one folder and start one program (no Python, no admin, no manual
   installs first);
2. answer plain-language questions, perform at most the irreducible manual
   steps (token creation, IT requests) with exact guidance, and watch every
   step turn green with a verified check;
3. when blocked by corporate policy, receive a complete report they can
   forward to IT without understanding it themselves;
4. finish with: a repo running the agentic development workflow, an ADORE
   profile that validates, a project image that passes its tool checks, and a
   supervised synthetic ticket that became a draft MR they reviewed;
5. later, run one `doctor` command to learn whether anything drifted and one
   `upgrade` command to move that repo to newer workflow/ADORE versions without
   losing local changes.
