<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Implementation Plan: Qwen Code as a Config-Selectable Executor

> Status: PLAN (not yet implemented). Date: 2026-07-05.
> Target: `04_Software/` (adore package). Mirrors the Pi integration
> (Component_Executor_Launcher.md, TODO "Create interface for PI Agent and
> Qwen Code"). To be implemented with Claude Code, task by task; each task
> names the AI model and reasoning level.

---

## 0. Goal

Add **Qwen Code** (`@qwen-code/qwen-code`, https://github.com/QwenLM/qwen-code -
a fork of Google's Gemini CLI) as a third executor selectable from config
(`[executor] default = "qwen"`), alongside `opencode` and `pi`. Because the Pi
work already refactored the launcher into a shared `FileProtocolExecutor` base,
Qwen is mostly a thin subclass. The one genuine complication is that **Qwen has
no `--session <id>` continuation** (opencode and pi both do), so the shared base
must be made session-strategy-configurable first.

---

## 1. What we build on (current state, post-Pi)

- `adore/executor/base.py` - `Executor` ABC, `ExecTarget`, `GateRun`.
- `adore/executor/launcher.py`:
  - `FileProtocolExecutor(Executor)` - the shared, WSL-safe file-based gate
    protocol (write `gate.sh`, exec `sh /adore/io/gate.sh`, read output/stderr/
    questions from files), `--session <id>` continuation, dead-session
    self-heal. Subclasses supply only two parsers: `_extract_session_id` and
    `_extract_usage` (default zeros), plus `forbidden_flags` and
    `session_reset_markers` class attributes.
  - `OpencodeExecutor` / `PiExecutor` - thin subclasses.
  - `build_executor(kind, command_template, model, questions_file)` - the config
    selection point (`opencode | pi`).
- Config selection needs NO engine change: the orchestrator already does
  `build_executor(config.executor.default, entry.command, entry.model, ...)`.
- The target repo ships a `.qwen/` adapter (see section 2) exactly like
  `.opencode/` and `.pi/`.

---

## 2. Findings - the `.qwen/` adapter and the Qwen Code CLI

### 2.1 The repo's `.qwen/` adapter (guardrails come with the worktree)
- `.qwen/settings.json` wires the SAME `.agentic/hooks/*.py` guards to Qwen's
  **native** `PreToolUse` / `PostToolUse` hooks (no bridge - Qwen's JSON-on-stdin
  hook protocol matches the hooks byte-for-byte, same as Codex/Claude):
  - `WriteFile`/`Edit`/`MultiEdit`/`write_file`/`replace`/`apply_patch` ->
    `guard_write_zone.py`.
  - `Bash` -> `secret_scan.py` then `delivery_preflight.py`.
  - PostToolUse -> `post_tool_evidence.py`.
- Plus a `permissions.deny` list: `Bash(git push*)`, `Bash(gh pr create*)`,
  `Bash(git merge*)`, and read/write denies for `.env`/keys.
- `context.fileName = ["AGENTS.md", "QWEN.md"]` - Qwen loads **AGENTS.md first**
  (the canonical gate contract), QWEN.md is only the adapter note.
- **Project trust:** Qwen loads project-local settings/hooks/skills/commands
  only after the workspace is trusted (same caveat as Pi).

### 2.2 Qwen Code CLI (Gemini-CLI fork) - to be pinned in the spike
- **Headless:** `qwen -p "<prompt>"` ("Scripts, CI/CD, batch processing - no UI").
- **Model:** `-m/--model` flag, or `OPENAI_MODEL` env (Gemini-CLI inheritance).
- **Auth (OpenAI-compatible):** `OPENAI_API_KEY`, `OPENAI_BASE_URL` (endpoint
  override, e.g. Dashscope), `OPENAI_MODEL`; also `ANTHROPIC_API_KEY` /
  `GEMINI_API_KEY`; or the Qwen OAuth free tier. Selection can be pinned in
  `~/.qwen/settings.json` (`security.auth.selectedType`, `model.name`) to avoid
  interactive `/auth`.
- **Structured output:** `--output-format json` (Gemini CLI emits
  `{"response": ..., "stats": {...}}`; the `stats` block MAY carry token usage -
  potentially better than Pi, which reports none). Schema to be pinned live.
- **NO `--session <id>` continuation.** Gemini/Qwen has `--checkpointing`
  (tool-state snapshots) and an experimental `qwen serve` daemon, but not
  opencode/pi-style session resume. **This is the key divergence.**
- **Auto-approve flags:** `--yolo` and `--approval-mode` (`default|auto_edit|
  yolo`). `yolo` auto-approves tool calls; whether it bypasses the deny-hooks
  must be verified, but ADORE should forbid it regardless (the `--auto` analog).

---

## 3. Key design decisions (ratify in Task 1)

- **D1 - Session strategy is per-executor.** Make `FileProtocolExecutor`'s
  `--session` append configurable instead of hard-coded. opencode/pi keep
  `--session <id>`; Qwen runs **stateless per gate** (no session flag). This is
  viable because the workflow's state lives in files (`.agentic/`, git, the
  ticket thread) and AGENTS.md reloads each gate - the in-agent session is an
  optimization, not a requirement. Clarification resume already re-sends the
  full thread (`_render_thread`), so no in-agent memory is needed there either.
  Mechanism: a class attribute like `session_arg_template: str | None`
  (opencode/pi = `"--session {session}"`; qwen = `None`), and
  `_extract_session_id` returns `""` for qwen (GateRun.session_id stays empty;
  the conductor simply never passes one back).
- **D2 - Safety flag ban.** Qwen's `forbidden_flags = ("--yolo",)` and reject
  `--approval-mode yolo` (the auto-approve analog of opencode's `--auto`). Real
  guardrail remains the repo `.qwen` deny-hooks + container isolation (no remote
  credentials in the container).
- **D3 - Auth env.** Qwen typically needs `OPENAI_BASE_URL` (+ optionally
  `OPENAI_MODEL`) alongside `OPENAI_API_KEY`. The wizard/`env_keys` guidance must
  include `OPENAI_BASE_URL` for the Qwen/Dashscope endpoint (a new injected key
  name; still a NAME only, never a value - design D5 of the profiles work).
- **D4 - Trust provisioning.** Same as Pi: headless runs need the worktree
  pre-trusted so `.qwen` settings/hooks load. Shared spike item with Pi.
- **D5 - Usage metrics.** If `--output-format json` `stats` carries tokens, wire
  `_extract_usage`; else zeros (metrics tolerate it, like Pi).

---

## 4. What needs to change (concrete)

1. **`FileProtocolExecutor` (base) - session strategy configurable (D1).**
   Replace the hard-coded `if session: command += f" --session ..."` with a
   `session_arg_template` class attribute; `None` => never append. Keep
   opencode/pi behavior byte-identical (their tests must stay green).
2. **`QwenExecutor(FileProtocolExecutor)`** - new subclass:
   - `session_arg_template = None` (stateless), `forbidden_flags = ("--yolo",)`.
   - `_extract_session_id` -> `""` (no session concept).
   - `_extract_usage` -> parse the `--output-format json` `stats` tokens if
     present, else zeros (pin in spike).
3. **`build_executor`** - add `if kind == "qwen": return QwenExecutor(...)`.
4. **Config** - no schema change; `[executor] default = "qwen"` +
   `[executor.qwen]` command/model. Example template (pin in spike):
   `qwen -p --model {model} --output-format json {prompt}`.
5. **Wizard** - add `qwen` to `_KNOWN_EXECUTORS` and a `_QWEN_COMMAND` template
   in `_command_for`; note the `OPENAI_BASE_URL` env need for Qwen.
6. **Dockerfile** - add the Qwen npm package (`@qwen-code/qwen-code`) as an
   isolated layer (mirror the pi layer); requires Node 20+ (already present).
7. **Tests** - `test_executor.py`: factory selects Qwen; stateless gate (NO
   `--session` in gate.sh even when a session id is passed); `--yolo` rejected;
   questions/failure inherited; usage parsing (once schema pinned).
8. **Docs** - Component_Executor_Launcher.md (three executors + session-strategy
   note), Configuration_Reference.md + Setup_And_Credentials.md (`qwen` option +
   OPENAI_BASE_URL + trust caveat), config.example.toml commented `[executor.qwen]`,
   TODO.md (mark Qwen code-done, spike pending).

---

## 5. The behavioral spike (the real work - like Pi's)

Cannot be done from the code alone; run once on a real host with Qwen installed:
1. Pin the exact headless flags on the installed version: `-p`, `-m/--model`,
   `--output-format json`, `--yolo`/`--approval-mode`.
2. Confirm `qwen -p` runs the `.agentic` CLI non-interactively and **commits**.
3. Pin the `--output-format json` schema; find a token-usage field (`stats`).
4. Verify **stateless-per-gate** actually drives the gate sequence correctly
   (no cross-gate agent memory needed) - this is the design assumption in D1.
5. Verify the deny-hooks fire in headless mode and that `--yolo` (if ever set)
   does/does not bypass them - lock the forbidden-flag list accordingly.
6. Verify/provision **project trust** for headless (shared with Pi).
7. Confirm the executor image builds with `@qwen-code/qwen-code`.

---

## 6. Task breakdown (model + reasoning per task)

> Keep the suite green (`uv run --group dev pytest`, `ruff check`) and follow the
> Doxygen/license/`@version`/Testing conventions in AGENTS.md throughout.

### Task 1 - Base: make session continuation executor-configurable (D1)
- **STATUS: DONE (2026-07-05) - via the Codex work.** The overridable
  `FileProtocolExecutor._build_command` seam (Codex plan Task 1) already covers
  the stateless case; QwenExecutor overrides it to ignore `session`. No
  separate base change was needed.
- **Model: Claude Sonnet 5 - Reasoning: Medium-High.**
- **Why:** touches the live-proven `FileProtocolExecutor`; must keep opencode/pi
  byte-identical while adding the `None`-session path. Small but load-bearing.
- **Deliverables:** `session_arg_template` attribute + the conditional append;
  opencode/pi set `"--session {session}"`. Existing executor tests unchanged
  and green.

### Task 2 - QwenExecutor + factory + config + wizard + Dockerfile
- **STATUS: DONE (2026-07-05).** `QwenExecutor` (stateless `_build_command`
  ignoring `session`; `_extract_session_id` -> ""; inherits zero usage -
  `--output-format json` stats schema deferred to the spike);
  `build_executor("qwen")`; config validation bans `--yolo` /
  `--approval-mode yolo`; wizard `_QWEN_COMMAND` + `_KNOWN_EXECUTORS`;
  config.example `[executor.qwen]` (with the OPENAI_BASE_URL auth note);
  Dockerfile `@qwen-code/qwen-code` layer. Verified: a `default = "qwen"`
  config validates and the factory returns QwenExecutor; the command stays
  stateless even when a session id is passed.
- **Model: Claude Sonnet 5 - Reasoning: Medium.**
- **Why:** mechanical, mirrors PiExecutor; the parsers are thin.
- **Deliverables:** `QwenExecutor`, `build_executor("qwen", ...)`, wizard
  `_QWEN_COMMAND` + `_KNOWN_EXECUTORS`, config.example `[executor.qwen]`,
  Dockerfile qwen layer.

### Task 3 - Tests
- **STATUS: DONE (2026-07-05).** `test_executor.py` (+3: factory + --yolo ban,
  stateless command with no --session/resume even when a session is passed,
  questions/failure inherited); `test_config.py` (+1: --yolo / --approval-mode
  yolo banned, plain qwen accepted). Suite 228 passing, ruff clean. **Tasks 4
  (live spike) and 5 (full docs) intentionally NOT started (stopped here per
  request).**
- **Model: Claude Sonnet 5 - Reasoning: Medium-High.**
- **Why:** the stateless-session path and the `--yolo` ban are new negative
  cases; breadth + fail-closed rigor per the Testing Rules.
- **Deliverables:** `test_executor.py` Qwen cases (factory, stateless gate.sh,
  `--yolo` rejected, questions/failure inherited, usage parse stub).

### Task 4 - Live spike (Qwen; shared trust step with Pi)
- **Model: Claude Opus 4.8 - Reasoning: High.**
- **Why:** the genuine unknowns (flags, json schema, stateless viability, trust,
  deny-hook behavior) need judgment on a real host; highest-value verification.
- **Deliverables:** findings recorded in Prerequisites_Check_Report.md; the
  command template, usage parser, and forbidden-flags finalized from evidence;
  a disposable-ticket pilot with `default = "qwen"`.

### Task 5 - Documentation
- **Model: Claude Haiku 4.5 - Reasoning: Low** (Sonnet 5 / Medium for the
  session-strategy + auth/trust narrative).
- **Deliverables:** Component_Executor_Launcher.md, Configuration_Reference.md,
  Setup_And_Credentials.md, config.example.toml, TODO.md, and (optionally) the
  Onboarding guide - all reflecting three executors and the Qwen specifics.

| Task | Model | Reasoning |
|---|---|---|
| 1 Base session strategy | Claude Sonnet 5 | Medium-High |
| 2 QwenExecutor + wiring | Claude Sonnet 5 | Medium |
| 3 Tests | Claude Sonnet 5 | Medium-High |
| 4 Live spike | Claude Opus 4.8 | High |
| 5 Docs | Claude Haiku 4.5 (Sonnet 5 for judgment) | Low/Medium |

---

## 7. Risks & open decisions

- **R1 - Stateless-per-gate (D1) unproven.** The design assumption is that the
  file-based workflow state makes in-agent sessions unnecessary. If cross-gate
  context loss degrades quality, fall back to `--checkpointing` or `qwen serve`
  (a bigger change) - decide from the Task 4 spike, not up front.
- **R2 - `--yolo` vs deny-hooks.** Must confirm the deny-hooks block push/merge
  even under any auto-approve mode; keep `--yolo` forbidden regardless.
- **R3 - Auth surface (`OPENAI_BASE_URL`).** Qwen's OpenAI-compatible endpoint
  needs the base-URL injected; ensure `env_keys` + wizard cover it. Qwen OAuth
  free tier is an alternative (its own headless caveats).
- **R4 - Project trust for headless** (shared with Pi) - the safety-critical
  provisioning step.
- **R5 - JSON schema drift.** Gemini-CLI-fork output format may change across
  versions; pin against the image's installed version and re-verify on bumps.

## 8. Definition of done

1. `[executor] default = "qwen"` selects `QwenExecutor`; a qwen config validates
   and `build_executor` returns it (offline-verifiable, like Pi).
2. Qwen runs stateless-per-gate through the shared file protocol; `--yolo`
   rejected; opencode/pi behavior unchanged (their tests green).
3. Suite green (happy + negative) offline; ruff clean; conventions followed.
4. Live spike passed: real `qwen -p` drives `.agentic`, commits, guardrails
   hold, trust provisioned; command/parser/forbidden-flags finalized from
   evidence; a disposable-ticket pilot reaches a draft MR.
5. Docs updated in the same changes; TODO Qwen item closed.

<!-- END OF FILE -->
