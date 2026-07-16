<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Implementation Plan: OpenAI Codex as a Config-Selectable Executor

> Status: PLAN (not yet implemented). Date: 2026-07-05.
> Target: `04_Software/` (adore package). Companion to the Pi
> (`Assisted_...`/launcher work) and Qwen (`Qwen_Code_Executor_Plan.md`)
> integrations. To be implemented with Claude Code, task by task; each task
> names the AI model and reasoning level.

---

## 0. Goal

Add **OpenAI Codex** (`@openai/codex`, https://github.com/openai/codex - the
Rust CLI) as a config-selectable executor (`[executor] default = "codex"`),
alongside `opencode`, `pi`, and (planned) `qwen`. The launcher already has a
shared `FileProtocolExecutor` base, so Codex is another subclass - but with two
real differences from Pi/opencode that shape the base refactor:

1. **Session continuation is a subcommand, not an appended flag.** Codex resumes
   with `codex exec resume [--last | <session-id>]`, so the command *structure*
   changes between a new session and a continuation - the base's "append
   `--session <id>`" cannot express it.
2. **Approval/sandbox model is inverted.** opencode BANS its auto-approve flag
   (`--auto`); Codex REQUIRES a non-interactive approval setting so it does not
   block headless (`--ask-for-approval never` / `--full-auto`), while BANNING
   the sandbox-bypass flag (`--dangerously-bypass-approvals-and-sandbox`).

Everything else maps cleanly and Codex is arguably the best-instrumented of the
alternatives (real `--json` token usage; native AGENTS.md; dual auth).

---

## 1. What we build on (current state)

- `adore/executor/launcher.py`: `FileProtocolExecutor(Executor)` (shared WSL-safe
  gate protocol, command build + `--session` append, dead-session self-heal),
  thin `OpencodeExecutor`/`PiExecutor`, and `build_executor(kind, ...)` (the
  config selection point). Config selection needs NO engine change.
- The target repo ships a `.codex/` adapter (section 2).

---

## 2. Findings - the `.codex/` adapter and the Codex CLI

### 2.1 The repo's `.codex/` adapter (guardrails + sandbox come with the repo)
- `.codex/config.toml`: a named permission profile `agentic-workspace`
  (`extends = ":workspace"`) with root-relative filesystem grants (`.` = write,
  `.git`/`.codex` = read, `.agentic` = write) and **secret-file denies**
  (`**/*.env`, `**/*.pem`, `**/*_rsa`). **Network `enabled = false` by default.**
- `.codex/hooks.json`: native `PreToolUse`/`PostToolUse` hooks reusing the SAME
  `.agentic/hooks/*.py` guards byte-for-byte (matchers `apply_patch|Edit|Write`
  and `Bash`), with `commandWindows` variants. Push/PR/merge are gated by
  `delivery_preflight.py` and require human approval.
- Codex reads `AGENTS.md` natively (the gate contract).
- **Trust:** Codex loads `.codex/config.toml` + `hooks.json` from the project
  dir; it does NOT appear to require the interactive project-trust step that Pi
  and Qwen do (verify in the spike).

### 2.2 Codex CLI - to be pinned in the spike
- **Headless:** `codex exec "<prompt>"` (single prompt, no UI).
- **Structured output:** `codex exec --json` (JSONL events; includes token
  usage - so `_extract_usage` can be real, unlike Pi/Qwen).
- **Session resume:** `codex exec resume --last` (most recent session in this
  cwd) or `codex exec resume <session-id>`. Since each run has its OWN container
  and gates run in the same cwd, **`resume --last` naturally continues the
  previous gate** without ADORE tracking an id.
- **Model:** `-m/--model`.
- **Sandbox:** `--sandbox`/`-s` = `read-only` | `workspace-write` |
  `danger-full-access`. **Approval:** `--ask-for-approval`/`-a` (e.g. `never`),
  `--full-auto`, `--dangerously-bypass-approvals-and-sandbox`.
- **Auth (dual, like opencode):** `OPENAI_API_KEY` env, OR ChatGPT login
  (`codex login`, stored in `~/.codex/auth.json`). The existing
  `stage_host_auth` OAuth-bridge pattern (used for opencode's auth.json) applies
  directly to Codex's `~/.codex/auth.json`.

---

## 3. Key design decisions (ratify in Task 1)

- **D1 - Command build is fully overridable (generalizes session strategy).**
  Replace the base's hard-coded `template.format(...) + "--session <id>"` with an
  overridable `_build_command(*, prompt_q, model_q, worktree, session) -> str`.
  Defaults reproduce today's behavior (append `--session` when set). This one
  seam covers all four executors:
  - opencode/pi: append `--session <id>`.
  - qwen: no session (stateless).
  - **codex:** first gate `codex exec ... {prompt}`; continuation
    `codex exec resume --last ... {prompt}` (structure change). ADORE passes a
    truthy `session` sentinel after gate 1; Codex maps "session set" ->
    `resume --last`. No id parsing needed (but `_extract_session_id` may still
    read the id from `--json` for the audit trail).
- **D2 - Approval/sandbox: required non-blocking + banned bypass (inverted).**
  Codex's command MUST include a non-interactive approval so it never blocks
  headless (recommend `--ask-for-approval never --sandbox workspace-write`, or
  `--full-auto`). `forbidden_flags` for Codex = the sandbox/approval BYPASS:
  `--dangerously-bypass-approvals-and-sandbox` (and reject
  `--sandbox danger-full-access`). Validation should also REQUIRE a
  non-interactive approval token in the template (a positive check, new). Real
  guardrail remains the repo `.codex` sandbox + deny-hooks + ADORE container
  isolation (no remote credentials in the container).
- **D3 - Network vs offline sandbox.** The gates resolve dependencies at runtime
  (`uv sync` / `npm ci` / `tflint --init`) which need network, but `.codex`
  config sets `network.enabled = false`. ADORE must run Codex with network
  enabled inside the container (Codex sandbox `workspace-write` allows it when
  configured), and lean on the container + the pending **egress allowlist**
  (TODO.md) for network safety - the same posture the other executors already
  rely on. Decide the exact codex network setting in the spike.
- **D4 - Auth (dual).** API key: inject `OPENAI_API_KEY` via `env_keys`
  (already supported). OAuth (ChatGPT): reuse `stage_host_auth` to stage the
  host `~/.codex/auth.json` into the container (generalize the existing bridge,
  which currently targets opencode's auth.json path, to a per-executor path).
- **D5 - Usage metrics.** Parse token usage from `codex exec --json` (pin the
  field names in the spike); Codex should give real per-launch tokens/cost.

---

## 4. What needs to change (concrete)

1. **`FileProtocolExecutor` (base) - overridable `_build_command` (D1).** Keep
   opencode/pi/qwen behavior identical (their tests green); the default builds
   the current string.
2. **`CodexExecutor(FileProtocolExecutor)`:**
   - `_build_command`: `codex exec` (new) vs `codex exec resume --last` (cont.),
     from the `[executor.codex]` template + a resume variant.
   - `forbidden_flags = ("--dangerously-bypass-approvals-and-sandbox",)`.
   - `_extract_session_id`: from `--json` (audit only; optional).
   - `_extract_usage`: parse the `--json` token-usage fields.
3. **`build_executor`** - add `if kind == "codex"`.
4. **Config validation** - a positive check that a Codex template carries a
   non-interactive approval (`--ask-for-approval never` or `--full-auto`) and no
   bypass flag. (opencode's `--auto` ban stays opencode-specific.)
5. **`stage_host_auth` generalization (D4)** - make the staged auth path
   per-executor (opencode: `~/.local/share/opencode/auth.json`; codex:
   `~/.codex/auth.json`) instead of hard-coded to opencode.
6. **Wizard** - add `codex` to `_KNOWN_EXECUTORS` + a `_CODEX_COMMAND` template
   (`codex exec --json --model {model} --ask-for-approval never --sandbox workspace-write {prompt}`);
   note the OAuth-vs-key auth choice already exists (auth_mode).
7. **Dockerfile** - install Codex (the install script targets Linux; pin a
   version) as an isolated layer.
8. **Tests** - factory selects Codex; first-gate vs resume command structure;
   bypass flag rejected + required-approval enforced; usage parsed from `--json`;
   questions/failure inherited.
9. **Docs** - Component_Executor_Launcher.md, Configuration_Reference.md,
   Setup_And_Credentials.md (Codex dual auth + sandbox/network + no-trust-step),
   config.example.toml `[executor.codex]`, TODO.md.

---

## 5. The behavioral spike (the real work)

Run once on a real host with Codex installed:
1. Pin the exact flags on the installed version: `exec`, `--json`,
   `exec resume --last`/id, `-m/--model`, `--ask-for-approval`, `--sandbox`,
   the bypass flag name.
2. Confirm `codex exec` runs the `.agentic` CLI non-interactively and **commits**
   without blocking on approvals (with `--ask-for-approval never`).
3. **Session:** confirm `resume --last` continues the previous gate in the same
   container/cwd (the D1 assumption). If not, fall back to id-based resume.
4. **Network:** confirm the gates' `uv sync`/`npm ci` run under
   `--sandbox workspace-write` with network enabled; reconcile with `.codex`
   `network.enabled=false` and the egress-allowlist plan.
5. Pin the `--json` schema; wire real token/cost usage.
6. **Auth:** verify both paths - `OPENAI_API_KEY` and the staged
   `~/.codex/auth.json` OAuth bridge.
7. Confirm the deny-hooks + sandbox block push/merge headless; lock
   `forbidden_flags`.
8. Confirm the image builds with Codex; a disposable-ticket pilot reaches a
   draft MR.

---

## 6. Task breakdown (model + reasoning per task)

### Task 1 - Base: overridable command build (D1)
- **STATUS: DONE (2026-07-05).** `FileProtocolExecutor._build_command` seam
  added (default = format + append `--session`); opencode/pi/qwen behavior
  unchanged and green. This base refactor also unblocks Qwen's stateless case
  (its plan Task 1 is now subsumed).
- **Model: Claude Sonnet 5 - Reasoning: High.**
- **Why:** touches the live-proven base and must express three session
  strategies (append / none / resume-subcommand) without changing
  opencode/pi/qwen behavior. The most delicate step.
- **Deliverables:** `_build_command` seam; opencode/pi/qwen defaults unchanged
  and green.

### Task 2 - CodexExecutor + approval/sandbox + auth + factory + wiring
- **STATUS: DONE (2026-07-05).** `CodexExecutor` (`exec` vs `exec resume
  --last` via `{resume}`, `--json` usage/session best-effort parsers,
  `forbidden_flags` = the sandbox-bypass); `build_executor("codex")`; config
  validation enforces a non-interactive approval + bans the bypass flag;
  `stage_host_auth` path generalized per executor (`_HOST_AUTH_PATHS`:
  opencode/codex); wizard `_CODEX_COMMAND` + `_KNOWN_EXECUTORS`;
  config.example `[executor.codex]`; Dockerfile `@openai/codex` layer.
  Verified: a `default = "codex"` config validates and the factory returns
  CodexExecutor; new/resume command shapes correct.
- **Model: Claude Sonnet 5 - Reasoning: Medium-High.**
- **Why:** the inverted approval model (D2), the network posture (D3), and the
  per-executor auth path (D4) need care, though each change is small.
- **Deliverables:** `CodexExecutor`, `build_executor("codex", ...)`, the
  non-interactive-approval config check, `stage_host_auth` path generalization,
  wizard/config.example/Dockerfile.

### Task 3 - Tests
- **STATUS: DONE (2026-07-05).** `test_executor.py` (+4: factory + bypass ban,
  new-vs-resume command structure, `--json` usage/session parse, questions/
  failure inherited); `test_config.py` (+2: required non-interactive approval,
  sandbox-bypass rejected); `test_orchestrator.py` (+1: per-executor
  host-auth path). Suite 224 passing, ruff clean. **Tasks 4 (live spike) and 5
  (full docs) intentionally NOT started (stopped here per request).**
- **Model: Claude Sonnet 5 - Reasoning: Medium-High.**
- **Why:** new negative cases (bypass-flag ban, required-approval check) and the
  first-gate-vs-resume command shapes; fail-closed rigor.
- **Deliverables:** `test_executor.py` Codex cases + a `test_config.py` case for
  the required-approval validation.

### Task 4 - Live spike
- **Model: Claude Opus 4.8 - Reasoning: High.**
- **Why:** the genuine unknowns (resume viability, sandbox+network, non-blocking
  approval, json/usage schema, dual auth, deny-hook behavior) need judgment on a
  real host. Highest-value verification.
- **Deliverables:** findings in Prerequisites_Check_Report.md; command template,
  usage parser, forbidden flags, and network/auth posture finalized from
  evidence; a `default = "codex"` disposable-ticket pilot.

### Task 5 - Documentation
- **Model: Claude Haiku 4.5 - Reasoning: Low** (Sonnet 5 / Medium for the
  approval/sandbox/network + auth narrative).
- **Deliverables:** the docs in section 4.9.

| Task | Model | Reasoning |
|---|---|---|
| 1 Base overridable command build | Claude Sonnet 5 | High |
| 2 CodexExecutor + approval/auth/wiring | Claude Sonnet 5 | Medium-High |
| 3 Tests | Claude Sonnet 5 | Medium-High |
| 4 Live spike | Claude Opus 4.8 | High |
| 5 Docs | Claude Haiku 4.5 (Sonnet 5 for judgment) | Low/Medium |

---

## 7. Risks & open decisions

- **R1 - `resume --last` correctness (D1).** Relies on one session per container
  cwd. If a gate spawns sub-sessions or `--last` is ambiguous, switch to
  id-based resume (parse the id from `--json`). Decide from the spike.
- **R2 - Approval must be non-blocking BUT sandbox-safe (D2).** The wrong flag
  either hangs headless (interactive approval) or removes Codex's own sandbox
  (`--dangerously-bypass...`). The target is `--ask-for-approval never
  --sandbox workspace-write`. Enforce via config validation.
- **R3 - Network vs offline sandbox (D3).** Gate dependency resolution needs
  network; `.codex` defaults offline. Couple this with the pending egress
  allowlist (TODO.md) rather than opening the container wide.
- **R4 - Auth bridge generalization (D4).** `stage_host_auth` is currently
  opencode-specific (path hard-coded); Codex needs `~/.codex/auth.json`. Keep it
  pilot-only; production prefers `OPENAI_API_KEY`.
- **R5 - Codex is fast-moving** (Rust CLI, frequent releases); pin the version
  in the image and re-verify flags/schema on bumps.

## 8. Definition of done

1. `[executor] default = "codex"` selects `CodexExecutor`; a codex config
   validates (incl. the required-approval check) and `build_executor` returns it
   (offline-verifiable).
2. First gate uses `codex exec`; continuation uses `codex exec resume --last`;
   the bypass flag is rejected; opencode/pi/qwen behavior unchanged (green).
3. Suite green (happy + negative) offline; ruff clean; conventions followed.
4. Live spike passed: real `codex exec` drives `.agentic`, commits without
   blocking, resumes across gates, guardrails + sandbox hold, both auth paths
   work; usage parsed; a disposable-ticket pilot reaches a draft MR.
5. Docs updated in the same changes; TODO Codex item closed.

<!-- END OF FILE -->
