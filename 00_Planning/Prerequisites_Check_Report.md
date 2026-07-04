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

## 11. GitLab Adapter Live Verification - 2026-07-03 (read-only)

Phase-2 step 1: the implemented `GitLabForge` adapter's CLI assumptions were
verified against the live instance (glab 1.105.0, authenticated as
`dan.pasare`). All probes were read-only; nothing was created or modified.

| Check | Result |
|---|---|
| `glab issue list --repo <path> --output json --per-page N` | PASS - all mapped fields present: `iid`, `state`, `title`, `description`, `labels` (plain strings), `author.username`, `web_url`, `created_at`, `updated_at` |
| `glab issue list --label <label>` filter | PASS - returns `[]` for a label with no matches (no `agent-ready` tickets exist yet) |
| `glab issue view <iid> --output json` | PASS - single JSON object, same field shape |
| `glab api projects/<url-encoded>/issues/<iid>/notes?order_by=created_at&sort=asc` | PASS - `id`, `body`, `author.username`, `created_at`, `system` (system notes correctly `true`) |
| Not-found behavior | PASS - `glab issue view 99999` exits 1 with `404 Not Found` in output; the adapter maps this to `None` |
| `glab issue note` flags | PASS - `-m/--message`, `--repo` exist |
| `glab issue update` flags | PASS - `--label` (add) / `--unlabel` (remove) exist |
| `glab mr create` flags | PASS - `--draft`, `--yes`, `--reviewer`, `--remove-source-branch`, `--source-branch`, `--target-branch`, `--title`, `--description` all exist |
| `glab api` field flags | **FINDING** - `-f` is `--raw-field` (string), `-F` is `--field` (type-inferred). The adapter initially used `--field`; switched to `--raw-field` for comment bodies so a body is never type-coerced. Fixed in `gitlab.py` and `github.py` (gh has the same semantics) in the same change. |

**Not verifiable read-only:** whether `glab issue note` prints the
`#note_<id>` URL the adapter parses. The adapter has a fallback (match the
newest note with the same body), so the first mutating test will confirm it.

**Also noted:** `glab mr create --auto-merge` exists; ADOR never passes it
(the delivery boundary stays draft-only).

## 12. Executor Image Build + Isolation E2E - 2026-07-03 (Docker in WSL2)

Host change since section 2: Docker Desktop was replaced by **Docker Engine
29.6.1 inside WSL2 (Ubuntu-24.04)**; the daemon is reached as
`wsl -d Ubuntu-24.04 -- docker ...`. ADOR supports this via
`[container] runtime = "wsl -d Ubuntu-24.04 -- docker"` (wrapped runtime,
auto-detected WSL mode: mount paths translated to `/mnt/<drive>/`, container
env values propagated across the WSL boundary via `WSLENV`). Plain
`runtime = "docker"` (Docker Desktop / native Linux) remains the other
supported path; both are unit-tested.

**Image build (`ador-executor:latest`, 1.62 GB): PASS.** The glab .deb release
URL pattern worked as written. Contents verified: user `ador`, Node v20.20.2,
uv 0.11.26, git 2.34.1, glab 1.55.0, opencode 1.17.13.

- **Finding (fixed):** Ubuntu 22.04's `python3.11` apt package is stuck at
  **3.11.0rc1**. The image now bakes a uv-managed CPython (3.11.15) and sets
  `UV_PYTHON=3.11`, so all uv-driven tooling gets a release interpreter;
  the raw `python` binary remains rc1 (unused by the workflow).

**Isolation end-to-end (scratch repo; nothing real touched): PASS, 19/19.**
Worktree create -> container provision -> tooling checks -> secret across
WSLENV -> `git status`/`git commit` **inside** the container via the
GIT_DIR/GIT_WORK_TREE model -> commit visible on the **host** with bot
authorship (`ADOR <ador-bot@local>`) -> park (stop) -> resume (start, state
intact) -> teardown (container, worktree, branch).

- **Caution for the executor-launcher phase:** `wsl.exe` re-joins arguments
  before the WSL shell re-parses them, so argv elements containing spaces
  (e.g. prompts) may be split. The e2e avoided spaces deliberately; the
  launcher must pass prompts via a file (already the plan for output capture)
  rather than argv when the runtime is WSL-wrapped.

## 13. Executor Launcher Gate Protocol - 2026-07-03 (live, no model key)

The launcher's file-based gate protocol was verified against the real
container (Docker in WSL2) using trivial shell commands as the "executor",
so no model credentials were involved: **PASS, 8/8.**

- The gate command (prompt shell-quoted inside) is written to
  `.ador/runs/<run-id>/io/gate.sh` and executed as `sh /ador/io/gate.sh` -
  two space-free argv tokens, immune to the wsl.exe splitting above.
- A hostile prompt (double quotes, `$`, backticks, `%`, embedded newline)
  **round-tripped byte-exact** host -> script -> WSL -> container -> output
  file -> host.
- Questions-file detection, stale-questions clearing before launch, exit-code
  passthrough (a failing gate is data, not an exception), and gate-artifact
  persistence in the io dir all verified.
- **Fix found during the test:** the gate script must not `exec` the
  command - templates can be compound commands; `exec` broke them with 127.

**Still open (needs a model API key in `.env`):** the mutating opencode spike
from section 8 - a real model-backed gate run in the container confirming it
drives the `.agentic` CLI, records evidence, and fails closed on a denied
push. The launcher protocol underneath it is now proven.
(Update: done - see section 14.)

## 14. Mutating opencode Spike - 2026-07-03 (CLOSED: all assertions proven)

The behavioral spike left open since section 8 ran to completion inside the
executor container: a real `openai/gpt-5.5` opencode session on a scratch
worktree/branch (`ador/spike-exec-1`) of the real target repo, launched
through ADOR's own isolation + launcher stack. Host opencode auth was staged
into the container for the run (never baked into the image). **PASS.**

| Assertion | Result |
|---|---|
| (a) opencode executes the `.agentic` CLI non-interactively | **PASS** - `run.sh status` executed via its bash tool; the run-state JSON landed in the committed evidence file. It also loaded the `agentic-development` skill unprompted (workflow awareness confirmed). |
| (b) stops cleanly | **PASS** - exit 0, bounded prompt followed step by step, replied DONE. |
| (c) fails closed on a denied push | **PASS** - `git push --dry-run origin HEAD` was auto-rejected headless by the repo's `opencode.json` (`git push*` = ask): `permission requested: bash (git push ...); auto-rejecting`. No `--auto` involved; `git ls-remote` confirmed the scratch branch never reached the remote. |
| Commit authorship via container env | **PASS** - the evidence commit shows `ADOR` (GIT_AUTHOR/COMMITTER from `build_container_env`). |
| Session id / event schema | **PASS** - NDJSON events (`step_start` / `tool_use` / `step_finish`), top-level `sessionID` (launcher extraction worked), full tool inputs/outputs/exit codes, and `step_finish` carries `tokens` (input/output/reasoning/cache) + `cost` - the metrics phase can read usage straight from the stream. |

**Findings fixed during the spike (image + spike-order):**

1. `python3` in the container resolved to Ubuntu's 3.10, so the `.agentic`
   CLI refused to run ("Python 3.11 or newer is required"). The image now
   links `python3`/`python` to the uv-managed CPython 3.11.15.
2. An auto-rejected permission ends the opencode run at that point; the
   first attempt ordered the push check before the evidence write and lost
   the later steps. Conductor consequence: treat a permission rejection as
   end-of-gate, and never put required work after an expected rejection.

**Section 8 status:** the behavioral spike is closed. Remaining open items
there are organizational, not technical: service account for production,
branch-protection confirmation, security sign-off.

## 15. Crawl-Phase Pilot - 2026-07-03 (PASS, end to end)

First full supervised run: real ticket #45 ("PILOT: add a Last updated line
to README.md") on the real repo, conducted by `ador run --once` through the
complete stack (selection -> claim -> worktree -> container -> OAuth staging
-> gpt-5.5 gates -> invariants verification per gate). Wall clock ~25 min
including two fix cycles. Result: run `validated-delivery-pending` with one
clean commit by `ADOR` (README line + traceable test + red-before-green
evidence: 4 fail -> 20 pass), clean tree, ticket status comment updated in
place per gate. Zero clarification parks; every gate passed invariants
first try.

**Findings, all fixed + regression-tested during the pilot:**

1. **Worktree path bug:** `git -C <repo>` resolves relative paths against
   the REPO, so the worktree landed inside the target repository. Fail-closed
   worked (escalated in 1s). Fix: WorktreeManager resolves paths to absolute;
   ditto container mount sources (a bare relative source would be read by
   docker as a named volume).
2. **Uncommitted-work gap:** the executor did all the work but committed
   nothing, and validation passed over a dirty tree. Fix: a deterministic
   conductor check after validation (clean tree + commits over base,
   relaunching validation with commit instructions, budget-bounded) plus a
   hardened gate-prompt rule.
3. **Gate sequence:** the workflow CLI's canonical STAGES include
   `alignment` between intake and requirement; ADOR's GATES now matches.
4. Housekeeping: pytest collection scoped away from `worktrees/` (live run
   checkouts of the target repo).

**Crawl-phase boundary respected:** ADOR never pushed and never opened an
MR; branch review, push, and MR creation stay with the human until phase 4.

## 16. Delivery Live Pilot - 2026-07-03/04 (phase 4 on the real repo)

Continuation of section 15: the same run (#45) driven through the automated
delivery sequence (merge target, retest, preflight, push, draft MR) against
the real repository. Every failure was caught deterministically (budget,
park, escalate - never a hang) and each fix landed with a regression test.

| # | Finding | Fix |
|---|---|---|
| 1 | The target repo's gates (`make lint` / `make test`) hard-require system tools the image lacked: `make`, `shellcheck`, `terraform`, and `tflint` (found one gate-failure at a time). | All baked into the executor image; per-project images + a fail-fast `required_tools` provision check are the planned generalization. |
| 2 | With a weak fix prompt and a missing binary, the model started **hacking around the gap** (modified `workflow.toml`, wrote a make-fallback script) before being stopped; with the tool provided and firmer prompts it instead **asked** (parked) - the wanted behavior. | Worktree litter reverted; prompts already hardened (commit rule); observation recorded for prompt design. |
| 3 | opencode **sessions live inside the container**: recreating the container (image rebuild, TTL reap) killed the stored session and every relaunch failed instantly with "Session not found" until the budget stopped it. | `provision` now reports created/started/running and the orchestrator resets the stored session on "created"; the launcher additionally self-heals a dead session by relaunching once fresh. |
| 4 | The **files-touched budget** counted upstream files staged by an in-progress target merge (13 of them) as the run's own scope and escalated before conflict resolution could start. | The files check is skipped while a merge is in progress. |
| 5 | The **wall-clock budget** kept ticking through an 8-hour park and escalated instantly on resume. | Resume (like retry) restarts the active-work clock and iteration counter; parked time is bounded by answer_timeout, not the work budget. |
| 6 | `retry`/`resume` of a delivery-stage run **restarted the gates from intake**; the aborted attempt also regressed the stored stage. | Both route to the delivery sequence now, and `_conduct` fails closed on any stage outside the gate list instead of silently starting over. |
| 7 | A killed poller left a **stale instance lock**; the next `--once` refused (correct) but with a traceback (ugly). | Graceful CLI error with a removal hint; automatic stale-lock handling belongs to the pending `ador cleanup`. |
| 8 | The executor **trusted the workflow's recorded blocker note over re-checking the environment** (repeated a stale "tflint missing" question after tflint was installed). | Handled via the clarification answer (instruct to verify and supersede); systematic answer: deterministic checks run before any model consultation in the delivery loop, which is already the design. |

| 9 | **HOME inside the container was wrong** for exec'd processes (this WSL2 docker setup), breaking tflint's HOME-keyed plugin handshake and threatening every HOME-based cache (uv, npm, opencode auth). A first fix passing HOME as a bare `--env` key made it WORSE: the WSL login shell resets HOME, so docker read the host user's home and overrode the image's correct ENV. | `ENV HOME=/home/ador` baked in the image AND passed inline (`--env HOME=/home/ador`) at provision; bare env keys stay reserved for secrets. Lesson: verify with `printenv`, never `echo $HOME`, through wsl.exe (shell expansion lies). |
| 10 | `glab mr create` requires a local git checkout to resolve remotes even with `--repo` ("No git remotes found") - the push succeeded but MR creation failed from ADOR's own directory. | MR creation runs with cwd = the run's worktree (forge `open_merge_request` takes cwd). |

Real conflict resolution was also exercised: `develop` moved mid-pilot and
the executor resolved a genuine `.agentic/current_run` merge conflict and
committed the merge (design 11a step 2 proven live).

**OUTCOME (2026-07-04 04:53 UTC): PASS end to end.** Ticket #45 went from
the `agent-ready` label to **draft MR !29** on the real repository, fully
conducted by ADOR: all six development gates, clarification park/answer/
resume with a human reply, target-branch integration with executor-resolved
conflicts, `gates run` + `delivery-preflight` green, push of
`feature/ador-45` (push rule respected), draft MR with reviewer assigned and
evidence-bearing description, environment retained for review. The remaining
11b leg (human merges -> run `done` + teardown) triggers on the poll after
the human merge.

**Executor-credential finding (open decision):** the host's opencode auth is
**OAuth (ChatGPT account)**, not an API key - there is no `sk-...` value to
put in `.env`, so the designed `OPENAI_API_KEY` injection has nothing to
inject on this host. The spike staged the host `auth.json` into the
container manually (works, but refresh tokens rotate and subscription
accounts are not meant for unattended use). Options and recommendation are
documented in `Setup_And_Credentials.md` section 3.1; production needs a
real API key (or another provider's key).
