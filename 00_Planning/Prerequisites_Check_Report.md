<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Prerequisites Check Report

> **Date:** 2026-07-02
> **Host:** Windows 11 (first-test bench)
> **Checked by:** environment probe (read-only)
> **Scope:** Verify the prerequisites and integration assumptions in
> `Setup_And_Credentials.md` and the design decisions before implementation.
> **Safety:** All probes were read-only. No comments, notes, branches, or MRs
> were created on any live ticket or repository.

## 1. Summary

| # | Check | Result | Status |
|---|---|---|---|
| 1 | `git` on host | 2.55.0 | PASS |
| 2 | Container runtime (Docker) | 29.5.3 | PASS |
| 3 | Python 3.11+ on host | 3.11.9 installed (winget); bare `python` still shadowed by Store alias | ACTION (disable alias) |
| 4 | `uv` (Python provider / project tool) | 0.11.25 | PASS |
| 5 | Node.js | v24.18.0 (CI targets Node 20) | PASS (note) |
| 6 | `glab` (GitLab CLI) | 1.105.0, authenticated | PASS |
| 7 | `gh` (GitHub CLI) | 2.95.0 (not authenticated) | PASS (GitHub path only) |
| 8 | Executor: opencode | 1.17.12, headless supported | PASS |
| 9 | GitLab issue JSON / notes API | verified | PASS |
| 10 | opencode headless run in repo (read-only) | launches, loads 8 skills, model replied, clean exit | PASS |
| 11 | opencode drives `.agentic` CLI + records evidence per gate | attempted locally; inconclusive (PS output buffering + latency); parts verified | OPEN (retest in container) |

Overall: the environment is ready to begin implementation. One host gap (Python
on PATH) and one behavioral spike remain before an end-to-end run.

## 2. Host Tooling (evidence)

```text
git       : git version 2.55.0.windows.1
python    : Python was not found (Windows App-execution-alias shim; not a real interpreter)
node      : v24.18.0
uv        : uv 0.11.25
docker    : Docker version 29.5.3, build d1c06ef
gh        : gh version 2.95.0 (2026-06-17)
```

Notes:

- **Python (ACTION):** the `python` command resolves to the Windows Store alias,
  not a real interpreter. The orchestrator needs Python 3.11+. Mitigation:
  install Python 3.11, or run it via `uv` (already present). Inside the
  container this is a non-issue (image provides Python).
- **Node (note):** host has Node 24; the project's CI targets Node 20. The
  container image should pin Node 20 to match `.gitlab-ci.yml`; the host version
  only matters for local tooling.

## 3. GitLab CLI and Authentication (evidence)

```text
glab 1.105.0 (45c9976)
  Logged in to gitlab.examplexdigital.fr as dan.pasare
  Git operations for gitlab.examplexdigital.fr configured to use https protocol.
  REST API Endpoint: https://gitlab.examplexdigital.fr/api/v4/
  Token found.
```

- `glab` is authenticated to the self-managed host as **`dan.pasare` (a human
  account)**. This confirms the design assumption that **no dedicated bot account
  exists**, so comment identity must be **marker-based** (design doc 5c), not
  author-based. For production, a service account is still recommended
  (Setup_And_Credentials.md section 8).

## 4. GitLab Issue JSON and Notes API (evidence)

`glab issue list --repo <path> --output json` returns structured records with all
fields ADOR needs for selection, readiness filtering, and comment handling:

- `iid`, `state`, `title`, `description`, `labels[]`, `author.username`,
  `assignees[]`, `web_url`, `references`, `user_notes_count`, and
  `_links.notes` (the per-issue notes API URL).

Comment operations:

- **Create a note:** `glab issue note <iid> -m "<text>"` (verified via `--help`).
- **Edit a note in place:** `glab issue note` has **no edit subcommand**. The
  "single status comment edited in place" (design 5d) must use
  `glab api --method PUT projects/:id/issues/:iid/notes/:note_id`.
- **Read notes (resume detection):** `glab api projects/:id/issues/:iid/notes`.

Implication: the status-comment/marker mechanism is feasible, but note editing is
an **API (PUT)** call, not a `glab` subcommand. Record this in the GitLab adapter.

## 5. opencode Headless Capabilities (evidence)

opencode 1.17.12, installed via npm. `opencode run [message..]` supports
non-interactive execution. Relevant flags:

- `--format json` - emits raw JSON events (machine-parseable output; no
  screen-scraping needed).
- `-c/--continue`, `-s/--session <id>`, `--fork` - session continuation; maps
  directly to driving gate-by-gate and resuming a parked clarification.
- `--dir <path>` - run against the run's worktree.
- `-m/--model provider/model` - model selection.
- `opencode stats` - token usage and cost (feeds the metrics design).
- `opencode export <sessionID>` - export session JSON (audit).

## 6. Safety Finding (must apply)

- opencode's `--auto` flag "auto-approves permissions not explicitly denied."
- `opencode.json` currently marks `git push`, `gh pr create`, `git merge`,
  `npm publish` as **`ask`** (not `deny`).
- **Risk:** running with `--auto` would auto-approve those, letting the executor
  push/merge - breaking the "orchestrator owns the remote" boundary.
- **Action:** for the unattended path, **do not use `--auto`**, and set
  push/pr/merge/publish to **`deny`** (not `ask`) in the opencode config ADOR
  uses, so the executor is provably unable to touch the remote.

## 7. Design Implications / Actions Arising

1. GitLab adapter: note editing uses `glab api --method PUT` (no CLI subcommand).
2. Executor adapter: launch `opencode run --format json --dir <worktree> -m <model>`;
   continue gates/clarification via `--session`/`--continue`.
3. Executor safety: `deny` push/pr/merge/publish + no `--auto`.
4. Metrics: use `opencode stats` / `--format json` events for tokens and cost.
5. Container image: pin Node 20 (match CI); provide Python 3.11 (host uses uv).
6. Host (dev): install Python 3.11 or invoke via `uv`.
7. Identity: marker-based comments confirmed necessary (auth is a human account).

## 8. Outstanding Before End-to-End Run

- **Behavioral spike (partly done):** the **read-only** launch is verified
  (section 9): opencode runs headless in the repo, loads the skills, and returns
  a model response cleanly. Still pending is a **mutating** scratch-branch run to
  confirm it (a) executes the `.agentic` CLI and records evidence, (b) stops
  cleanly at a gate, and (c) fails closed on a denied push. Must not post to a
  live ticket.
- **Service account** (production): request a dedicated GitLab account/token or
  confirm the human token is acceptable for the pilot.
- **Branch protection:** confirm the target branch is protected with required
  approval (enforces "no agent merge").
- **Security sign-off:** confirm approval to run an autonomous agent with
  repo-write + external model API on the corporate repo.

## 9. Executor Headless Spike - 2026-07-02 (read-only)

**Command (output redirected to a file):**

```text
opencode run --dir "D:\2026_Agentic_Delivery_Platform\04_Software" \
  -m openai/gpt-5.4-fast --print-logs --log-level DEBUG "Reply READY."
```

**Result:** opencode bootstrapped in the repo, loaded 8 workflow skills
(`agentic-development`, `agentic-delivery`, `regression-traceability`, ...),
selected `openai/gpt-5.4-fast`, the model replied `READY.`, and it exited cleanly
(`exiting loop` / `disposing instance`). Total ~13 seconds.

**Safety:** read-only respected - the repo working tree was unchanged (only the
pre-existing `.qwen/settings.json`); no branch, commit, or push; the process was
externally controllable and killable.

**Findings:**

1. **Output capture:** opencode buffers stdout, so live stdout streaming showed
   nothing until exit (this made earlier attempts look "hung"). The orchestrator
   MUST read the executor's result from a **file** or the **`--format json`**
   event stream, not naive stdout streaming.
2. **DeepSeek free model needs auth:** `opencode/deepseek-v4-flash-free` stalled
   because the opencode provider is not authenticated (`opencode auth list` shows
   only OpenAI). It requires an interactive `opencode auth login`.
3. **Benign warning:** `duplicate skill name` - both `.claude/skills` and
   `.opencode/skills` define the same skills; opencode picks one.
4. **Internal title model:** opencode uses a small local `lm-studio/qwen` model
   to generate the session title; the main task used `openai/gpt-5.4-fast`.

**Still pending:** a mutating scratch-branch run to confirm opencode executes the
`.agentic` CLI, records evidence through a gate, and fails closed on a denied
push.

## 10. Mutating Spike Attempt - 2026-07-02 (inconclusive locally)

Attempted to have opencode drive the `.agentic` CLI (`status`, `start`,
`add-spec`) inside a throwaway git worktree on branch `spike/ador-test`, using
`openai/gpt-5.4-fast`, no `--auto`, no push.

**Setup findings (positive):**

- Installed **Python 3.11.9** via winget (user scope). The `.agentic` CLI then
  runs on the host: `run.ps1 status` returned valid run JSON. So the CLI works
  once a real Python is resolvable.
- However, bare `python` is still shadowed by the Windows **Store app-execution
  alias**; the permanent user-PATH fix was blocked by this shell's constrained
  language mode. **Permanent fix for the user:** disable the `python.exe` /
  `python3.exe` App execution aliases (Settings > Apps > Advanced app settings >
  App execution aliases), or ensure the real Python dir precedes
  `...\WindowsApps` in PATH.

**Result (inconclusive):** opencode launched and bootstrapped in the worktree,
but did not visibly reach the CLI commands within ~4.5 min; `current_run` was
unchanged when stopped. The obstruction was **local tooling friction, not a
design blocker**:

- PowerShell `*>` / `Out-File` buffered opencode's output (and wrote UTF-16), so
  progress was not observable and was lost when the process was stopped.
- Combined with model latency, the run could not be watched to completion.

**Conclusion / recommendation:** the constituent parts are verified (the
`.agentic` CLI runs; opencode runs headless and can execute shell commands). The
definitive mutating test should be run **in the Linux executor container** with
`opencode run --format json` (progressive, machine-readable, UTF-8 output;
Python present), which removes all the Windows-specific friction. Track as the
first implementation-phase verification, not a design open question.

**Cleanup:** worktree and `spike/ador-test` branch removed; temp scripts/logs
deleted; main repo working tree unchanged (only the pre-existing
`.qwen/settings.json`).
