<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration Reference

> **Status**: Planning. Consolidated list of every `config.toml` setting agreed
> so far, its meaning, default value, and examples. Keys are grouped by section.
> Defaults are proposals and may change during implementation.

## Full Example `config.toml`

```toml
# ----- Bot identity -----
[agent]
name = "ADOR"                 # display/brand: comment tags, MR titles, commit author
slug = "ador"                 # derived names: .ador/ state dir, branch, container, marker
email = "ador-bot@example.com"  # commit author email in the container (derived if empty)

# ----- Git platform -----
[platform]
kind = "gitlab"              # "gitlab" | "github"
repo = "rd/internal/france/delivery-tools/delivery-cockpit/cockpit-gcp"
# The Git-platform CLI (glab / gh) must be installed and authenticated on the host.

# ----- State signaling -----
[state]
channel        = "comments"  # "comments" | "labels" | "both"
store_root     = ".ador"      # local authoritative state dir (derived from slug)

# ----- Polling -----
[polling]
mode                  = "loop"   # "loop" (long-running) | "once" (cron/scheduler)
poll_interval_seconds = 60       # base wait between polls
poll_jitter_seconds   = 5        # random +/- jitter
poll_backoff          = true     # lengthen interval after Git platform errors/rate limits
max_concurrent_runs   = 1        # tickets in flight at once
quiet_hours           = []       # e.g. ["22:00-06:00"] windows where polling pauses

# ----- Readiness filter (selection) -----
[readiness]
require_acceptance_criteria = true
require_priority_label      = true
require_known_component     = true
max_scope_hint              = "small"   # skip tickets larger than this

# ----- Labels -----
[labels.lifecycle]           # orchestrator-managed (used when channel includes labels)
ready    = "agent-ready"
working  = "agent-working"
clarify  = "agent-clarify"
answered = "agent-answered"
review   = "agent-mr"
failed   = "agent-failed"
done     = "agent-done"

[labels.selection]           # human-managed, read for eligibility/order
priority_high   = "P1"
priority_medium = "P2"
priority_low    = "P3"
type_feature    = "feature"
type_bug        = "bug"

[labels.control]             # human overrides, checked before eligibility
hold    = "agent-hold"
exclude = "no-agent"

[labels.executor]            # optional: pin an executor per ticket
prefix = "agent-exec:"       # e.g. "agent-exec:opencode"

# ----- Executor -----
[executor]
default        = "opencode"  # "opencode" | "pi" | "codex"
mode           = "thick"     # "thick" (gate-by-gate) | "headless" (single-shot)
questions_file = "ADOR_QUESTIONS.md"
env_keys       = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]  # only these reach the container
stage_host_auth = false      # pilot-only OAuth bridge (see Setup_And_Credentials.md 3.1)

[executor.opencode]
command = "opencode run --model {model} \"{prompt}\""
model   = "<provider/model>"

# [executor.pi] / [executor.codex] follow the same command-template shape.

# ----- Clarification -----
[clarification]
max_rounds     = 3           # ask/answer cycles before escalating to failed
reminder_after = "24h"       # optional single nudge before timeout
answer_timeout = "72h"       # give up and release the ticket after this
timeout_state  = "failed"    # terminal state on timeout ("failed" | "stale")

# ----- Container / isolation -----
[container]
runtime            = "docker"   # "docker" | "podman"
image              = "ador-executor:latest"
keep_parked        = true       # keep (stopped) container after parking
parked_ttl_mode    = "polls"    # "seconds" | "polls"
parked_ttl_seconds = 7200       # used when mode = "seconds"
parked_ttl_polls   = 30         # used when mode = "polls"
parked_state       = "stopped"  # "stopped" (fast resume) | "removed" (free disk)
uv_cache_volume    = "ador-uv-cache"
npm_cache_volume   = "ador-npm-cache"
run_args           = []         # extra `run` options; rootless podman: ["--userns=keep-id"]

[worktree]
repo_path = "../cockpit-gcp" # local clone the run worktrees are created from (required)
root      = "worktrees"      # host dir holding per-run git worktrees
branch_template = "{slug}/{run_id}"  # run branch name; {slug}/{run_id}/{iid} placeholders
                                     # e.g. "feature/{slug}-{iid}" for feature/-prefix push rules
branch_rule = ""             # optional: the repo's branch push-rule regex; validation
                             # rejects a template the rule would reject, e.g.
                             # '^(feature|bugfix|release|hotfix)\/.*$' (cockpit-gcp)

# ----- Run budgets -----
[budgets]
max_iterations         = 20
max_wall_clock_seconds = 3600
max_cost_usd           = 5.0
max_files_touched      = 40

# ----- Delivery -----
[delivery]
target_branch        = "develop"
draft                = true      # open MR/PR as draft; never merge
reviewers            = ["dan.pasare"]
remove_source_branch = true

# ----- Post-MR review loop -----
[review]
trigger               = "label"        # "label" | "comment-marker" | "auto"
revise_label          = "agent-revise" # human applies this to request a revision
max_review_rounds     = 3
review_reminder_after = "48h"          # optional nudge if the MR sits undecided

# ----- Reconciliation (external ticket changes) -----
[reconcile]
on_ticket_deleted  = "abort-cleanup"   # abort + remove worktree/container
on_ticket_closed   = "cancel"          # graceful cancel
on_trigger_removed = "pause"           # "pause" | "abort" | "ignore"

# ----- Metrics / statistics (stdlib only; CLI + optional static HTML) -----
[metrics]
enabled          = true
db_path          = ".ador/metrics.db"
export_jsonl     = ".ador/metrics/runs.jsonl"
capture_tokens   = true
capture_resource = true                # docker stats / disk probes
html_out         = ".ador/metrics/stats.html"
```

## `[agent]` - Bot Identity

| Key | Meaning | Default |
|---|---|---|
| `name` | Display/brand string; appears in comment tags, MR/PR titles, commit author. `ADOR` = Agentic Delivery Orchestrator by examplex. | `"ADOR"` |
| `slug` | Lowercase token that derives the state dir (`.<slug>/`), branch prefix, container name, questions file, and comment marker. Derived from `name` if empty. | `"ador"` |
| `email` | Git commit author email inside the executor container (`name` is the author name). Derived as `<slug>-bot@local` if empty. | (derived) |

## `[platform]` - Git Platform Selection

| Key | Meaning | Default |
|---|---|---|
| `kind` | Which Git-platform adapter to use. | `"gitlab"` |
| `repo` | Repository path/slug passed to the Git-platform CLI. | (required) |

Note: `glab` (GitLab) or `gh` (GitHub) must be installed and authenticated on
the host. No separate bot account is required (identity is marker-based).

## `[state]` - State Signaling

| Key | Meaning | Default |
|---|---|---|
| `channel` | How run state is reflected on the ticket: `comments`, `labels`, or `both`. Authoritative state always lives locally. In comment mode ADOR keeps one status comment and edits it in place. | `"comments"` |
| `store_root` | Local authoritative state directory. | `".ador"` |

## `[polling]` - Polling

| Key | Meaning | Default |
|---|---|---|
| `mode` | `loop` = long-running service; `once` = single pass for cron/Task Scheduler. | `"loop"` |
| `poll_interval_seconds` | Base wait between polls (configurable period). | `60` |
| `poll_jitter_seconds` | Random jitter added to the interval. | `5` |
| `poll_backoff` | Lengthen the interval after Git platform errors / rate limits. | `true` |
| `max_concurrent_runs` | Tickets allowed in flight at once. | `1` |
| `quiet_hours` | Windows where polling pauses. | `[]` |

## `[readiness]` - Readiness Filter

| Key | Meaning | Default |
|---|---|---|
| `require_acceptance_criteria` | Skip tickets with no acceptance criteria. | `true` |
| `require_priority_label` | Require a P-label to be eligible. | `true` |
| `require_known_component` | Require the ticket to map to a known component. | `true` |
| `max_scope_hint` | Skip tickets estimated larger than this. | `"small"` |

## `[labels.*]` - Labels

| Group | Meaning | Managed by |
|---|---|---|
| `labels.lifecycle` | Run-state labels (`ready`/`working`/`clarify`/`answered`/`review`/`failed`/`done`). Used only when `state.channel` includes labels. | orchestrator |
| `labels.selection` | Eligibility/priority/type labels read at pickup (`P1`..`P3`, `feature`, `bug`). | humans |
| `labels.control` | Overrides checked before eligibility (`hold`, `exclude`). | humans |
| `labels.executor` | Optional prefix to pin an executor per ticket (`agent-exec:opencode`). | humans |

Defaults are listed in the example above. Every label string is configurable so
teams can rename without code changes; the orchestrator refers to labels by role.

## `[executor]` - Executor

| Key | Meaning | Default |
|---|---|---|
| `default` | Which executor to launch (`opencode` / `pi` / `codex`). | `"opencode"` |
| `mode` | `thick` = orchestrator drives gate-by-gate; `headless` = single-shot. | `"thick"` |
| `questions_file` | File the executor writes clarification questions to. | `"ADOR_QUESTIONS.md"` |
| `env_keys` | The only environment variables (from host env / `.env`) injected into the executor container. | `["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]` |
| `stage_host_auth` | Pilot-only: copy the host's opencode `auth.json` (OAuth session) into the run container at provision (see Setup_And_Credentials.md 3.1). | `false` |
| `[executor.<name>].command` | Command template for that executor; `{prompt}` (shell-quoted), `{model}`, and `{worktree}` (container path `/ador/work`) substituted. `--auto` is forbidden (it would auto-approve the executor's own push/merge). | per executor |
| `[executor.<name>].model` | Model/provider string for that executor. | (required) |

## `[clarification]` - Clarification

| Key | Meaning | Default |
|---|---|---|
| `max_rounds` | Ask/answer cycles before escalating the ticket to `failed`. | `3` |
| `reminder_after` | Optional single nudge (mentions assignee) before the timeout, measured from `parked_at`. | `"24h"` |
| `answer_timeout` | Give up and release the ticket if no human reply within this window. | `"72h"` |
| `timeout_state` | Terminal state applied on timeout (`failed` or a dedicated `stale`). | `"failed"` |

## `[container]` - Container / Isolation

| Key | Meaning | Default |
|---|---|---|
| `runtime` | Container runtime command: `docker` / `podman`, optionally wrapped, e.g. `"wsl -d Ubuntu-24.04 -- docker"` for Docker Engine inside WSL2 (ADOR then translates mount paths and propagates env via WSLENV). | `"docker"` |
| `image` | Executor image (base tooling baked in). | `"ador-executor:latest"` |
| `keep_parked` | Keep (stopped) the container after parking instead of removing. | `true` |
| `parked_ttl_mode` | Grace period unit: `seconds` or `polls`. | `"polls"` |
| `parked_ttl_seconds` | Reap idle parked container after N seconds (mode=seconds). | `7200` |
| `parked_ttl_polls` | Reap idle parked container after N poll cycles (mode=polls). | `30` |
| `parked_state` | On park: `stopped` (fast resume) or `removed` (free disk now). | `"stopped"` |
| `uv_cache_volume` | Persistent uv cache volume for fast `uv sync`. | `"ador-uv-cache"` |
| `npm_cache_volume` | Persistent npm cache volume for fast `npm ci`. | `"ador-npm-cache"` |
| `run_args` | Extra option tokens for `<runtime> run` (one option per entry, no spaces; validated). ROOTLESS PODMAN REQUIRES `["--userns=keep-id"]` (verified 2026-07-04: without it container uid 1000 maps to a subuid that cannot write the bind-mounted worktree). Also the seam for future resource limits (`"--memory=2g"`). | `[]` |

## `[worktree]` - Worktree

| Key | Meaning | Default |
|---|---|---|
| `repo_path` | Local clone of the target repository that per-run worktrees are created from; mounted (with the worktree) into the executor container. | (required) |
| `root` | Host directory holding per-run git worktrees (`<root>/<run-id>`). | `"worktrees"` |
| `branch_template` | Run branch name; `{slug}`, `{run_id}`, `{iid}` placeholders (must keep `{run_id}` or `{iid}` for uniqueness). Set e.g. `"feature/{slug}-{iid}"` for repos whose push rules require a `feature/` prefix. | `"{slug}/{run_id}"` |
| `branch_rule` | Optional regex mirroring the repo's branch-name push rule (cockpit-gcp: `^(feature\|bugfix\|release\|hotfix)\/.*$`); validation rejects a template the rule would reject. | `""` |

## `[budgets]` - Run Budgets

| Key | Meaning | Default |
|---|---|---|
| `max_iterations` | Max **executor launches** per run before failing closed. What counts: one launch per gate (6 for a clean pass) plus one per fix launch (merge-conflict resolution or a failing-gate fix during delivery) and per revise round. Clean delivery (no conflicts, gates green) launches the executor **zero** extra times - merge/preflight/push/MR are deterministic orchestrator actions. Sizing: `6` = clean pass only, zero fix headroom (crawl pilots); `12`-`15` = supervised operation with fix headroom; `20` (default) = unattended headroom. Tripping the budget never loses work: the run fails with the reason journaled and posted, and `ador retry` re-arms the counters and continues from the stored stage. | `20` |
| `max_wall_clock_seconds` | Max wall-clock of **active work** per run; the clock restarts on `ador retry` and on resume-from-park (parked waiting time is bounded by `[clarification] answer_timeout` instead). | `3600` |
| `max_cost_usd` | Max model spend per run. | `5.0` |
| `max_files_touched` | Max files a run may change. | `40` |

## `[delivery]` - Delivery Boundary

| Key | Meaning | Default |
|---|---|---|
| `target_branch` | Branch the MR/PR targets. | `"develop"` |
| `draft` | Open as draft; the orchestrator never merges. | `true` |
| `reviewers` | Human reviewers assigned to the MR/PR. | (required) |
| `remove_source_branch` | Remove the source branch on merge. | `true` |

## `[review]` - Post-MR Review Loop

| Key | Meaning | Default |
|---|---|---|
| `trigger` | How a revise cycle starts: `label` (explicit; implemented), `comment-marker`, or `auto` (both currently treated as `label`). | `"label"` |
| `revise_label` | Label a reviewer applies to request an agent revision. | `"agent-revise"` |
| `max_review_rounds` | Revise cycles before escalating the run to `failed`. | `3` |
| `review_reminder_after` | Optional nudge if the MR sits undecided. | `"48h"` |

Note: approval and merge are always human actions; the revise cycle only updates
the branch (the MR stays a draft).

## `[reconcile]` - Reconciliation

| Key | Meaning | Default |
|---|---|---|
| `on_ticket_deleted` | Action when a run's ticket is deleted. | `"abort-cleanup"` |
| `on_ticket_closed` | Action when a run's ticket is closed by a human. | `"cancel"` |
| `on_trigger_removed` | Action when the trigger label is removed / `agent-hold` added mid-run (`pause`/`abort`/`ignore`). | `"pause"` |

Manual overrides (`ador cancel/delete/reset/retry/cleanup`, `ador pause/resume`)
are CLI commands, not config; see design doc section 8c.

## `[metrics]` - Statistics

| Key | Meaning | Default |
|---|---|---|
| `enabled` | Turn statistics capture on/off. | `true` |
| `db_path` | SQLite database of run summaries (stdlib `sqlite3`). | `".ador/metrics.db"` |
| `export_jsonl` | Mirrored append-only export of run summaries. | `".ador/metrics/runs.jsonl"` |
| `capture_tokens` | Record executor token usage per run/gate. | `true` |
| `capture_resource` | Probe container/disk resource stats. | `true` |
| `html_out` | Output path for `ador stats --html` static dashboard. | `".ador/metrics/stats.html"` |

Access is CLI-first (`ador stats`, `ador report`, `ador export`) plus the
optional static HTML; there is no Prometheus endpoint or hosted service.

## Notes

- Every value above is a proposed default and may be tuned per environment.
- Related but non-`config.toml` inputs (kept as environment variables / secrets,
  not in this file): the Git-platform token used by `glab` / `gh`, and the executor's
  model-provider credentials.
- Cross-references: polling (design doc section 5a), labels (5b), identity and
  signaling (5c), run identity and local state (8a), container TTL (8b),
  clarification (9), isolation and dependencies (10a), delivery (11).
