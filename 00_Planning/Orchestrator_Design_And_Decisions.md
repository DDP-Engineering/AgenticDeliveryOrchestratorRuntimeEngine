<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Delivery Orchestrator - Design and Decisions

> **Status**: Planning notes. Captures the ideas and decisions agreed so far.
> **Scope**: The orchestrator that pulls a Git platform ticket, guides an executor
> agent through the agentic development workflow, and opens a draft MR/PR for a
> human to review and merge.

## 1. Purpose

Automate the routine path from an approved ticket to a review-ready change. A
human tags a ticket as ready; the orchestrator picks it, isolates the work,
guides an executor agent through the existing agentic workflow gates, and â€” only
when every gate is green â€” opens a **draft** merge/pull request. A human still
reviews and merges. The goal is throughput and consistency, not removing the
human from the final decision.

## 2. High-Level Flow

```text
Git platform ticket (label: agent-ready)
  -> orchestrator picks highest priority + passes readiness filter
  -> isolate (git worktree + container)
  -> thick conductor drives gates one at a time:
       intake -> requirement -> check -> implementation -> validation
       (checks invariants / exit codes between each gate)
  -> on ambiguity: post questions to the ticket, park, take next ticket
       (resume when the human answers and re-labels)
  -> delivery: run delivery-preflight (objective "done" signal)
  -> green: push branch + open DRAFT MR/PR, assign human reviewer
human reviewer -> approves and merges
```

## 3. Locked v1 Decisions

| Area | Decision | Rationale |
|---|---|---|
| Git platform support | GitLab **and** GitHub, behind one adapter | Repo is on GitLab today; GitHub kept portable from day one. |
| Autonomy mode | Thick conductor (drive one gate at a time) | Matches the workflow's stop-after-each-gate design; better recovery. |
| Clarification | Included in v1 | Handles ambiguity found during intake, not just at selection. |
| Executor | Configurable launcher (opencode / pi / codex) | Avoid lock-in; one is chosen per run via config. |
| Delivery | Draft MR/PR only; never merge | Merge stays a human decision; draft cannot be merged accidentally. |
| Orchestrator intelligence | Deterministic Python, no LLM in v1 | All judgment lives in the executor; orchestrator decisions are `if`s. |
| Runtime | Ubuntu 22 (production), Windows 11 (first tests) | Portable Python + container = same artifact on both. |

## 4. Domain: Git Platform Integration

- **Git platforms:** GitLab and GitHub. **CLI access is required** on the host:
  `glab` (GitLab) and `gh` (GitHub), both authenticated. `git` is also required.
- **One adapter interface**, so the orchestrator never calls a CLI directly:
  `list_ready()`, `claim()`, `post_comment()`, `open_mr()`, `set_state()`.
  Two implementations sit behind it: `gitlab.py` (glab) and `github.py` (gh).
- **Structured output:** prefer `--output json`; fall back to `glab api` /
  `gh api` for guaranteed clean JSON.
- **Dependency to verify:** exact JSON flags for the installed CLI versions.

## 5. Domain: Ticket Selection and Lifecycle

- **Eligibility is a label, priority is a label â€” keep them separate.**
  `agent-ready` is the human's deliberate opt-in ("safe to hand over").
  Priority ordering uses the existing `P1` / `P2` / `P3` labels.
- **Readiness filter** applied after eligibility: has acceptance criteria, has a
  priority label, touches a known component, small estimated scope. Tickets that
  fail stay for a human.
- **Run states** (taken / working / parked / in-review / failed). The
  authoritative state lives in local `.<slug>/` storage; it can be **reflected**
  to the ticket as labels, comments, or both (configurable â€” see 5c). Default
  names when labels are used:

  ```text
  agent-ready    -> eligible, not yet picked
  agent-working  -> claimed (the lock; prevents double pickup)
  agent-clarify  -> parked, waiting on a human clarification answer
  agent-mr       -> draft MR/PR opened, waiting on review
  agent-failed   -> gave up after N retries, needs a human
  ```

- **Trigger = polling in v1.** No inbound service; identical on Windows and
  Ubuntu. Webhook / `@agent` mention is a later upgrade for near-instant
  reaction. See section 5a for the polling mechanism.

### 5a. Polling Mechanism

- **How it works:** a loop wakes on a fixed interval, calls the Git-platform adapter's
  `list_ready()` (open issues labelled `agent-ready`), orders by priority,
  applies the readiness filter, and dispatches the top eligible ticket. It also
  re-checks `agent-clarify` (parked) tickets for a resume signal: a **new human
  comment** on the ticket, or the manual `agent-answered` override label
  (see section 9).
- **Configurable period â€” required.** The poll interval is a config value, not a
  hard-coded constant, e.g. `poll_interval_seconds` in `config.toml`
  (default suggested: 60s). It can be tuned per environment without code changes.
- **Two ways to run the loop, both driven by the same config:**
  - *Internal loop* â€” the orchestrator process sleeps `poll_interval_seconds`
    between cycles (long-running service; the natural mode on Ubuntu 22).
  - *External scheduler* â€” a single pass per invocation, triggered by `cron`
    (Linux) or Task Scheduler (Windows); the interval is set by the schedule.
    Run mode is itself a config/CLI choice (`--once` vs `--loop`).
- **Related tunables (all config-driven):**
  - `poll_interval_seconds` - base wait between polls.
  - `poll_jitter_seconds` - optional random jitter to avoid a fixed cadence.
  - `poll_backoff` - lengthen the interval after Git platform errors / rate limits.
  - `max_concurrent_runs` - how many tickets may be in flight at once.
  - `quiet_hours` (optional) - windows where polling is paused.
- **Idempotency:** each pass claims a ticket by flipping `agent-ready ->
  agent-working` before work starts, so overlapping or restarted passes never
  double-pick the same ticket.

### 5b. Configurable Labels

- **All labels are configurable** in `config.toml`, grouped by category. The
  orchestrator refers to labels only by their role, never by a hard-coded string,
  so a team can rename any label without code changes.
- **Categories:**
  - **Lifecycle** - the run state machine; the orchestrator sets/removes these.
  - **Selection** - read by the orchestrator to decide eligibility and order;
    normally managed by humans and often reusing existing repo labels.
  - **Control** - human overrides that pause or exclude a ticket.
  - **Executor** (optional) - force a specific executor for a ticket.
- **Proposed defaults:**

  ```toml
  [labels.lifecycle]        # managed by the orchestrator
  ready    = "agent-ready"      # eligible, not yet picked
  working  = "agent-working"    # claimed (the lock)
  clarify  = "agent-clarify"    # parked, waiting on a human answer
  answered = "agent-answered"   # human answered -> resume the parked run
  review   = "agent-mr"         # draft MR/PR opened, awaiting human review
  failed   = "agent-failed"     # gave up after retries, needs a human
  done     = "agent-done"       # optional: set after the human merges

  [labels.selection]        # read by the orchestrator (human-managed)
  priority_high   = "P1"
  priority_medium = "P2"
  priority_low    = "P3"
  type_feature    = "feature"
  type_bug        = "bug"

  [labels.control]          # human overrides
  hold    = "agent-hold"       # never pick, even if marked ready
  exclude = "no-agent"         # permanently human-only, ignore always

  [labels.executor]         # optional: pin an executor per ticket
  prefix  = "agent-exec:"      # e.g. "agent-exec:opencode", "agent-exec:pi"
  ```

- **Notes:**
  - `ready` + `answered` are the two labels a **human** applies to move a ticket
    into or back into the flow; the rest are driven by the orchestrator.
  - `hold` / `exclude` are checked **before** eligibility, so they always win.
  - Priority mapping is a list so teams can add tiers (e.g. `P0`) via config.
  - The `executor` category is optional; if unset, the config's default executor
    is used for every ticket.

### 5c. Agent Identity and Signaling

- **A configurable bot name drives all derived identifiers**, so renaming the bot
  is a single change:
  - `agent.name` - display/brand (default `"ADOR"`, for **A**gentic **D**elivery
    **O**rchestrator by **R**andstad), shown in comment tags, MR/PR titles, and the
    git commit author name.
  - `agent.slug` - lowercase token (default `"ador"`; derived from `name` if
    empty) used to build the local state dir (`.<slug>/runs/...`), the branch
    prefix (`<slug>/<run-id>`), the container name (`<slug>-run-<run-id>`), the
    questions file (`<SLUG>_QUESTIONS.md`), and the comment marker.

  ```toml
  [agent]
  name = "ADOR"     # display/brand: comment tags, MR titles, commit author
  slug = "ador"     # derived names: .ador/ state dir, branch, container, marker
  ```

- **No dedicated Git platform account required (marker-based identity).** The corporate
  repo may not allow creating a separate bot user, so the orchestrator does
  **not** rely on comment authorship. It stamps every comment it posts with a
  marker and treats any comment **without** the marker as human:
  - a visible tag (e.g. `[ADOR]`) plus a hidden Markdown marker line
    `<!-- ador:run=<run-id> kind=<kind> -->` (invisible when rendered on GitLab and
    GitHub);
  - it also records the IDs of the comments it posts in `state.json`.
  A resume trigger (section 9) is then a comment whose ID it did not post and
  that lacks the marker. The tag and marker strings derive from `name` / `slug`.

- **State signaling is a configurable channel** to avoid noisy label churn:
  - `state.channel = "comments" | "labels" | "both"` (default `"comments"`).
  - In comment mode the orchestrator maintains a **single status comment edited
    in place** (both `glab` and `gh` can edit a note), not a new comment per
    change; its ID is stored in `state.json`.

  ```toml
  [state]
  channel        = "comments"       # "comments" | "labels" | "both"
  status_comment = "single-edited"  # "single-edited" | "new-per-change"
  ```

- **The claim lock lives in local state.** Because labels are now optional, the
  authoritative run state and the claim/lock are the orchestrator's `.<slug>/`
  store, not labels. This assumes a **single orchestrator instance** (the current
  case); multiple instances would need a shared lock. Labels/comments are only
  the human-facing reflection of that internal truth.

### 5d. Ticket Marking (status on the ticket)

- **The orchestrator marks a ticket's current status on the ticket itself**, via
  the configured channel (`state.channel`, default `comments`). Labels are
  optional; comments are the default to avoid noisy label churn for humans.
- **Comment mode = one status comment, edited in place.** The orchestrator posts
  a single status comment per ticket and edits it on each state change (both
  `glab` and `gh` can edit a note); it does not add a new comment per change. The
  comment id is stored in `state.json`.
- **Marking format:** a human-readable line plus a hidden machine marker.

  ```text
  ADOR status: working - stage intake - run gitlab-cockpitgcp-14 - updated 2026-07-02 14:02
  <!-- ador:run=gitlab-cockpitgcp-14 kind=status state=working stage=intake -->
  ```

  The visible tag (`[ADOR]`) and the marker prefix (`ador:`) derive from
  `agent.name` / `agent.slug`. The hidden marker is invisible when rendered but
  lets the orchestrator find and update its own comment, and lets resume
  detection tell agent comments from human replies (section 9).
- **Comment kinds, all carrying the marker with a `kind` field:**
  - `kind=status` - the single edited status comment (working / parked /
    in-review / failed, plus current stage).
  - `kind=question` - a clarification post (section 9).
  - `kind=delivery` - the draft MR/PR notification.
- **When `state.channel = "labels"` or `"both"`**, the matching
  `[labels.lifecycle]` label is applied in addition to (or instead of) the
  status comment, for teams that prefer the label view.

## 6. Domain: Executor Agent

- **Configurable and swappable:** opencode, pi.dev, or codex, selected via a
  command template in config. The orchestrator launches it as a subprocess.
- **Already workflow-aware:** the target repo ships the adapters
  (`.opencode/`, `.pi/`, `AGENTS.md`) and the `agentic-development` skill, so a
  launched executor follows the gates and runs the `.agentic` CLI itself
  (records spec, checks, red-before-green evidence). This behavior is reused, not
  rebuilt.
- **Executor never touches the remote.** `opencode.json` already marks
  `git push`, `gh pr create`, `git merge`, `npm publish` as `ask`, which blocks
  them headless. The executor commits locally only; the orchestrator owns push
  and MR creation.
- **Clarification signal convention:** when blocked, the executor writes its
  questions to a known file (e.g. `ADOR_QUESTIONS.md`) in the worktree and stops.
  The orchestrator's check is deterministic â€” does the file exist after intake
  returns â€” regardless of how it was written.
  - **How the file gets written â€” start soft, allow deterministic.** The writing
    itself is done by the executor using its normal file-write tool; it is not a
    built-in feature.
    - **Soft (v1):** the prompt / headless skill mandates it ("if you have
      blocking questions, write `ADOR_QUESTIONS.md` and stop"). Simplest, but
      LLM-dependent â€” the agent may occasionally not comply.
    - **Firmer:** as a fallback, parse the executor's returned output for a
      questions marker if the file is missing.
    - **Deterministic (upgrade):** give the executor a dedicated command/tool
      (e.g. an `.opencode/command` or plugin `ador-ask "<question>"`) that writes
      the file in a guaranteed format, so "asking" is a defined tool call rather
      than free-form editing, and can be enforced with a hook.
  - Promote from soft to deterministic only if compliance proves flaky; the
    orchestrator-side detection (file presence) is unchanged either way.
- **To verify:** the exact headless invocation flag per executor, and that it
  runs the `.agentic` CLI (records evidence) when run non-interactively.

## 7. Domain: Agentic Workflow Integration

- **The target repo's `.agentic` layer is the ground truth for "done."** Gates,
  invariants, and `delivery-preflight` decide readiness â€” not the agent's word.
- **Gates:** `intake -> requirement -> check -> implementation -> validation ->
  delivery`. The `agentic-development` skill covers stages 1-5;
  `agentic-delivery` covers delivery.
- **Between gates**, the orchestrator runs `invariants` / reads exit codes and
  decides advance, retry, or escalate.
- **Objective stop condition:** loop until `delivery-preflight` exits 0 (and CI
  is green). This is the project's key advantage â€” most autonomous setups lack a
  machine-checkable definition of done.

### 7a. Per-Gate Conductor Loop

Every gate follows the **same loop** — this is what makes the orchestrator a
thick conductor rather than a single-shot launcher:

1. **Mark status** `working - <gate>` (edit the status comment).
2. **Launch the executor for only this gate** (via the `agentic-development`
   skill). The executor runs the `.agentic` CLI itself and stops at the end of
   the gate.
3. **Inspect the result:** check the exit status, and check the worktree for
   `ADOR_QUESTIONS.md`.
4. **Verify (the conductor check):** run `invariants` / read exit codes to confirm
   the gate is coherent before advancing.
5. **Branch:**
   - questions -> park (clarification flow, section 9);
   - failure or budget exceeded -> relaunch the executor for the *same* gate with
     the failure context, bounded by run budgets; persistent failure ->
     escalate to `failed`;
   - clean -> advance to the next gate.

**Gate specifics** (`agentic-development` covers 1-5; `agentic-delivery` covers
delivery):

- **intake** - classify the request, `start`, `impact`, understand scope.
- **requirement** - `add-spec`; create durable requirement rows (as `Planned`);
  `invariants`.
- **check** - `add-check` citing spec ids; write the failing tests; record
  **red** evidence (`record-evidence --result fail`). Red-before-green enforced.
- **implementation** - edit only source roots; make the checks pass; record
  **green** evidence; `record-change`; `requirement activate` when a linked check
  is green; update component docs.
- **validation** - `invariants`, `audit traceability`, `audit coverage`,
  `impact`, `gates run`; inspect the diff for scope creep, weakened assertions,
  and secrets.

After validation passes, the run proceeds to the **delivery** gate (section 11):
`delivery-preflight`, then — if green — the orchestrator opens the draft MR/PR.

## 8. Domain: Orchestrator Engine

- **Plain Python state machine.** No LangGraph, no LLM inside the orchestrator in
  v1 â€” its decisions are deterministic (exit codes, preflight result).
- **AI is optional and deferred.** Add a single model call later only for a
  judgment task (smart retry/repair, queue ranking), not a framework.
- **Thick conductor:** invoke the executor per gate, verify between stages,
  advance/retry/escalate within run budgets.
- **Durable run state:** an orchestrator-side JSON store (branch, worktree, run
  id, stage, flags) plus the Git platform lifecycle labels as external state.
- **Idempotent recovery:** on restart, skip tickets already `agent-working` /
  `agent-mr`, and never re-post a question or re-open an MR.

### 8a. Run Identity and Local State

- **Independent from the agentic workflow session.** The orchestrator run/session
  and the target repo's `.agentic` workflow run are kept **fully separate**. The
  orchestrator does not link to, depend on, or record the `.agentic` run-id; each
  side manages its own state.
- **Local snapshot on pickup.** When polling picks a ticket, the orchestrator
  stores it locally so the run is durable, idempotent, and auditable without
  re-fetching:

  ```text
  .ador/runs/<run-id>/
    ticket.json      # title, body, labels, comments, timestamps + content hash
    state.json       # stage, lifecycle label, last_seen_comment_id, rounds
    journal.jsonl    # orchestrator events
  ```

- **Run/session identity â€” deterministic, not random.** The `run-id` is derived
  from the stable ticket reference (`<Git platform>-<project>-<issue>`, optionally a
  short hash of it). It must be stable across restart and resume so the same
  resources are reused rather than duplicated. It names:
  - worktree dir: `worktrees/<run-id>`
  - branch: `ador/<run-id>`
  - container/session: `ador-run-<run-id>`
  - run state dir: `.ador/runs/<run-id>`

  A random per-poll id would break resume (every poll would look new), so the
  identity is always derived from the ticket.
- **Content hash â€” change detection.** A separate hash of the ticket's meaningful
  content (title + body + acceptance criteria, and optionally key comments) is
  stored in `ticket.json`. On re-poll, a changed content hash means the spec
  moved while the run was parked or in progress; the orchestrator can then react
  (restart intake, warn on the MR, or re-park for clarification). Identity stays
  the same; only the content hash flags drift.
- **Concurrency lock.** The `agent-working` label remains the cross-process lock
  so two poll passes never grab the same ticket.

### 8b. Container Lifecycle and Parked-Run TTL

- **Container is ephemeral; worktree + state are durable.** The container is
  spawned per active work session and is disposable. The worktree and
  `.ador/runs/<run-id>` persist across parks and restarts, keyed by the stable
  run-id, so nothing is lost when a container goes away.
- **Keep-warm on park.** When a run parks for clarification, the container is
  **stopped** (not removed) by default: it uses no CPU/RAM but keeps its
  filesystem and resolved dependencies, so resume is a fast `docker start`.
- **Grace period (TTL), enforced by the poller.** Because the poller already runs
  on an interval, it checks each parked run against a TTL. The TTL can be
  expressed **two ways** (config choice):
  - **by time** - `parked_ttl_seconds` (e.g. 7200 = 2h), or
  - **by number of polls** - `parked_ttl_polls` (e.g. 30 cycles without an
    answer).
  Once the configured TTL is exceeded and the run is still unanswered, the poller
  **stops + removes** the container (reap). The worktree and state are kept.
- **Resume behavior:**
  - answered within TTL -> `docker start` the warm container (fast);
  - answered after reap -> recreate the container from the image + cache volumes;
    the durable worktree + state make this seamless (only the warm cache is lost).
- **Independent bounds.** `max_clarification_rounds` bounds the *conversation*;
  the TTL bounds the *resource*. Reaping a container never ends a run.
- **Optional early reap.** Under `max_concurrent_runs` pressure, a parked
  container may be reaped before its TTL to free a slot for active work.
- **Config:**

  ```toml
  [container]
  keep_parked      = true        # keep (stopped) the container after parking
  parked_ttl_mode  = "polls"     # "seconds" | "polls"
  parked_ttl_seconds = 7200      # used when mode = "seconds"
  parked_ttl_polls   = 30        # used when mode = "polls"
  parked_state     = "stopped"   # "stopped" (fast resume) | "removed" (free disk now)
  ```

### 8c. Reconciliation and Manual Overrides

**Automatic reconciliation.** Each poll, for active / parked / in-review runs, the
orchestrator re-checks the ticket and reconciles external changes so a deleted or
closed ticket never leaves a zombie run or an orphaned container:

- **Ticket deleted** (Git platform returns not-found) -> **abort**: stop + remove the
  container, remove the worktree, mark outcome `orphaned` (no comment possible),
  keep or purge `.ador/runs/<run-id>` state per policy.
- **Ticket closed by a human** while a run is active -> **cancel**: stop the run,
  post a comment if still accessible, clean up, mark `ticket-closed`.
- **Trigger removed / `agent-hold` added mid-run** -> **pause or abort** (default:
  honor the human's signal and stop).
- **Ticket content changed** -> content-hash drift (8a): restart intake or warn.
- **MR closed** -> handled by the review loop (11b): terminate + cleanup.

**Manual operator commands** (deliberate intervention; part of the CLI, 12a):

- `ador cancel <run-id>` - graceful stop: tear down container + worktree, mark
  `cancelled`, post a closing comment if the ticket exists, keep state.
- `ador delete <run-id> [--force]` - hard removal including `.ador` state
  (destructive; confirm or `--force`).
- `ador reset <run-id> --to <gate>` - force a run back to a stage.
- `ador retry <run-id>` - re-run from where it stopped.
- `ador pause` / `ador resume` - global stop/allow picking new tickets.
- `ador cleanup` - garbage-collect orphaned worktrees / containers / state and
  clear a stale `.ador/ador.lock`.
- **Guardrail:** destructive commands (`delete`, `reset`) confirm or need
  `--force`; `cancel` always attempts a clean container stop first.

```toml
[reconcile]
on_ticket_deleted  = "abort-cleanup"  # abort + remove worktree/container
on_ticket_closed   = "cancel"         # graceful cancel
on_trigger_removed = "pause"          # "pause" | "abort" | "ignore"
```

## 9. Domain: Clarification / Parked Runs

- **Park-on-ambiguity:** during intake (or any gate) the executor writes its
  questions to `ADOR_QUESTIONS.md` in the worktree and stops. The orchestrator
  reads that file (the executor never touches the Git platform) and parks the run.
- **Park sequence (exact order):**
  1. **Post the questions comment first** (`kind=question`, with the marker) and
     record its comment id and the current `last_seen_comment_id` in
     `state.json`. Posting first means a later crash still leaves the questions
     on the ticket.
  2. **Update the status marking** to `clarify / parked` (edit the status
     comment; also set the `agent-clarify` label if `state.channel` includes
     labels).
  3. **Increment the clarification round counter** and compare to
     `clarification.max_rounds`; if exceeded, escalate to `failed` instead of
     parking.
  4. **Record `parked_at`** (timestamp and/or poll count) to start the TTL clock
     (section 8b).
  5. **Stop the container** (kept per `parked_state = "stopped"`); the worktree,
     the executor's `.agentic` run, and `.ador/runs/<run-id>` state persist.
  6. **Return to polling** and pick the next ticket.
- **Resume detection (primary): a new human comment.** The orchestrator polls
  parked tickets and reads their comments/notes. If it finds a comment **newer
  than its own question**, that **lacks the agent marker** (i.e. not one the
  orchestrator posted, matched by marker and recorded comment id), and is **not a
  system note**, it treats the ticket as answered, resumes the run, and hands the
  executor the **full comment thread**. This means the human just replies
  normally â€” no re-labelling chore.
- **Resume detection (manual override): the `agent-answered` label.** A human can
  force an immediate resume by applying it, independent of comment parsing.
- **The executor re-decides on resume.** A new comment is not assumed to be a
  sufficient answer. On resume the executor re-evaluates intake with the thread;
  if it now has enough, it proceeds; if not, it asks again and re-parks. This
  tolerates non-answers (+1s, counter-questions) gracefully.
- **Bounded rounds.** A config value (`max_clarification_rounds`, e.g. 3) caps
  the ask/answer cycles; exceeding it escalates the ticket to `agent-failed` so a
  run can never loop forever.
- **Answer-wait timeout (no reply for too long).** Separate from the round cap
  (conversation) and the container TTL (resource), an answer-wait timeout bounds
  how long a parked run stays open with no human reply, measured from
  `parked_at`. Two-stage escalation:
  1. **Reminder (soft), after `reminder_after`:** post one nudge comment that
     `@`-mentions the ticket assignee/reporter. Optional.
  2. **Timeout (hard), after `answer_timeout`:** if still no reply, post a closing
     comment, move the run to a terminal state (`timeout_state`, e.g. `failed` or
     a dedicated `stale`), **clear the parked/working marking so the ticket
     returns to human hands**, remove the worktree (keep `.ador/runs/<run-id>`
     state for audit), and **leave the ticket open** so a human can re-tag
     `agent-ready` to restart later.
  - **Container reap != run timeout.** The container may already be reaped (8b)
    while the run is still validly parked and answerable, up until
    `answer_timeout`; only then does the *run* end.

  ```toml
  [clarification]
  max_rounds     = 3
  reminder_after = "24h"    # optional single nudge before timeout
  answer_timeout = "72h"    # give up and release the ticket after this
  timeout_state  = "failed" # terminal state on timeout ("failed" | "stale")
  ```
- **Resume sequence (exact order):**
  1. **Detect the answer** on a poll cycle (a comment newer than the question,
     lacking the marker, not a system note; or the `agent-answered` override) and
     update `last_seen_comment_id`.
  2. **Bring back the container:** `docker start` if it was kept warm (stopped),
     or recreate it from the image + cache volumes if it was reaped past TTL;
     re-mount the **same** worktree by run-id (same branch, same state).
  3. **Update the status marking** to `working` (clear `agent-clarify` / set the
     working label if labels are in use) and **reset the answer-wait timer**.
  4. **Relaunch the executor at the intake gate** with the **full comment thread**
     (its question + the human's answer) as context.
  5. **Executor re-decides:** it either completes intake and the run advances, or
     writes `ADOR_QUESTIONS.md` again and re-parks (round counter increments,
     bounded by `max_rounds`).
- **Marker-based identity (no dedicated account).** The orchestrator's own
  comments carry a hidden marker and their ids are recorded, so it distinguishes
  its own comments from human replies without needing a separate bot account
  (corporate repos often cannot create one). See section 5c.
- **Who posts:** the orchestrator, never the executor (single place for creds,
  formatting, threading, idempotency).
- **Idempotency:** store `last_seen_comment_id` (or timestamp) and the posted
  question id per parked run, so each poll only considers genuinely new comments
  and a restart never double-posts a question or re-triggers on an old reply.
- **Relationship to selection:** clarification complements the readiness filter.
  Filter rejects obviously under-specified tickets up front; clarification
  handles tickets that look fine but turn ambiguous mid-intake.

## 10. Domain: Isolation and Safety

- **Isolation is mandatory once the human leaves the loop** â€” not optional. The
  workflow's hooks are guardrails, not a sandbox.
- **Model:** one `git worktree` per ticket (isolated branch/dir) executed inside
  a **Docker container**. Escalate to ephemeral VM / CI runner later if needed.
- **Run budgets bound every run:** max iterations, wall-clock, token/cost, and
  files touched (write-zones already scope paths per gate). Exceeding a budget
  escalates (`agent-failed` + journal) instead of thrashing.
- **Secret protection** carried from the repo: `secret_scan` hook and the
  `opencode.json` read/edit denies for `.env`, keys, and certificates.

### 10a. Isolation Layers and Dependencies

- **Two layers per run:** a `git worktree` (code isolation: one folder + branch
  per ticket, sharing the repo object store) mounted into a **container**
  (execution isolation: the real safety sandbox bounding filesystem, network,
  CPU/RAM/time). One worktree + one container per `run-id`; both are torn down
  when the run ends.
- **Where dependencies live â€” three tiers:**
  - **Base tooling -> baked into the container image (built once).**
    Python 3.11 + `uv`, Node 20 + `npm`, `git`, the executor CLI
    (opencode / pi), `glab` / `gh`, and the build/test tools matching
    `.gitlab-ci.yml`. Reused by every run; never installed per run.
  - **Project dependencies -> installed at container runtime, NOT into the
    mounted worktree.** Resolve `uv` envs and `node_modules` into
    container-internal paths or a **cache volume**, keeping the worktree as
    source only. Writing `.venv` / `node_modules` into the bind-mounted worktree
    is slow cross-OS and broken (a Linux `.venv` has paths that do not work on a
    Windows host).
  - **Host machine -> only what the orchestrator needs:** `git`, a container
    runtime (Docker / Podman), `glab` / `gh`, and Python 3.11 for the
    orchestrator. The host never builds or tests the project; the container does.
- **Performance:** mount persistent `uv` and `npm` cache volumes so per-run
  dependency resolution (`uv sync`, `npm ci`) is fast without reinstalling the
  toolchain.
- **Portability fallout:** because all real dependencies live in the Linux
  container image, "works on Windows 11" and "works on Ubuntu 22" are the same
  image; the host OS only has to run the container runtime.

## 11. Domain: Delivery Boundary

- **Orchestrator opens a DRAFT MR/PR** after `delivery-preflight` is green, and
  assigns a human reviewer. A draft **cannot be merged** until a human marks it
  ready â€” the hard stop for "no auto-merge."
- **Never merges, never passes a merge flag**, never calls `glab mr merge` /
  `gh pr merge`.
- **Backstop:** target branch (`main` / `develop`) is protected with required
  approval, so the agent lacks merge permission even if something tried.
- **Description** comes from the run's `report.md` (invariants, evidence,
  traceability). Use "Related to #N", not an auto-close keyword â€” let the human
  decide closure at review.

### 11a. Delivery Sequence (exact order)

Runs after validation passes; turns a green branch into a review-ready draft MR.
The change is integrated with the latest target branch and re-tested **before**
the MR is opened, so the MR is never stale or silently broken.

1. **Mark status** `working - delivery`.
2. **Sync with the target branch (deterministic first, reasoning on demand).**
   The **orchestrator** runs the merge plumbing: `git fetch origin`, then
   `git merge origin/develop` into the run branch (`ador/<run-id>`). Remote/git
   operations stay with the orchestrator; the executor only touches local files.
   - **Clean merge (no conflicts)** -> the orchestrator proceeds directly; the
     executor is not involved.
   - **Conflicts** -> the orchestrator relaunches the **executor** to resolve
     them (a code-reasoning task on local files, inside the gate loop, bounded by
     run budgets); the executor completes the merge, then the run continues.
   - **Unresolvable** -> escalate to `failed` for a human.
3. **Re-run the tests/gates on the merged result** (`gates run` / configured
   tests). Integrating `develop` can break a change that passed in isolation, so
   validation is repeated here.
   - Not green -> fix (relaunch) or escalate.
4. **Run `delivery-preflight` (authoritative)** and produce `report.md`
   (`registry sync`, `report`).
   - Not green -> fix or escalate; green -> proceed.
5. **Push the run branch** (`git push -u origin ador/<run-id>`); the executor is
   blocked from pushing, so the orchestrator does it.
6. **Open the draft MR/PR** targeting `develop`, description from `report.md`,
   reviewer assigned, no merge flags, never `merge`.
7. **Mark status** `review` (`agent-mr`) and post a `kind=delivery` comment with
   the MR link.
8. **Hand off (keep the environment alive).** Do **not** delete the container or
   worktree at MR creation. The container is **retained** (kept, e.g. stopped to
   save resources) so review feedback / revise cycles can resume instantly
   without re-provisioning. `.ador/runs/<run-id>` state is kept. CI runs on the MR
   as the remote hard gate.
9. **Human reviews and merges.** A later poll detects the merge, marks the run
   `done`, and **only then tears down the container and worktree** (keeping
   `.ador/runs/<run-id>` state for audit). If the MR is closed without merging,
   the run is terminated the same way, with cleanup.

### 11b. Post-MR Review Loop

After the draft MR is open, the container and worktree are retained (11a step 8),
so the run can react to review without re-provisioning. Three outcomes:

- **Approve + merge -> done.** A poll (orchestrator) detects the merge, marks the
  run `done`, and tears down the container and worktree. Merge is always a human
  action; the agent never merges.
- **Comments / changes requested -> revise cycle** (below).
- **Closed without merge -> terminated.** The orchestrator marks the run
  `failed`, cleans up, and keeps `.ador/runs/<run-id>` state for audit.

**Do not auto-react to every comment.** Not every MR comment is a change request.
The revise trigger defaults to an explicit signal (`review.trigger = "label"`),
so a reviewer leaves normal comments and applies `agent-revise` (or `@ador`) only
when the agent should act. `auto` is available but not the default.

**Revise cycle — steps and owners:**

1. **Detect the trigger** (poll the MR for the revise label / marker) - orchestrator.
2. **Start the retained environment** (`docker start` the kept container) - orchestrator.
3. **Fetch the MR review threads and launch the executor with them; make the
   requested code changes** - orchestrator launches and passes context; executor
   edits.
4. **Re-run the gates/tests** - executor runs them in the container; orchestrator
   verifies (`invariants` / exit codes).
5. **Re-merge `origin/develop` + retest** - orchestrator runs the merge plumbing;
   executor resolves conflicts if any and re-runs tests; orchestrator runs
   `delivery-preflight` (authoritative).
6. **Push updates to the same branch** - orchestrator (executor is blocked from
   pushing); the MR updates automatically and stays a draft.
7. **Mark status `review` again + post a `kind=delivery` update comment** -
   orchestrator.
8. **Enforce `max_review_rounds`; escalate to `failed` if exceeded** - orchestrator.

**Division of labor:** the orchestrator owns everything deterministic and
everything touching the remote (triggers, container lifecycle, git plumbing,
push, MR/status, verification gates, budgets); the executor owns everything
requiring code reasoning (edits, conflict resolution, running the gates).

```toml
[review]
trigger               = "label"        # "label" | "comment-marker" | "auto"
revise_label          = "agent-revise" # human applies this to request a revision
max_review_rounds     = 3
review_reminder_after = "48h"          # optional nudge if the MR sits undecided
# approval + merge are always human; the agent only updates the branch
```

## 12. Domain: Runtime and Portability

- **Production:** Ubuntu 22 (run as a service or cron-driven loop).
- **First tests:** Windows 11.
- **Same artifact both places:** orchestrator in portable Python; executor and
  target-repo tooling run inside a container. Avoid OS-specific glue in the core
  loop.
- **Requirements:** Python 3.11+ for the orchestrator; `git`, `glab`/`gh`, a
  container runtime, and the chosen executor CLI available on the host or image;
  model/provider credentials for the executor.

### 12a. Interface and Startup

- **CLI-first over a library core.** A single `ador` command (stdlib `argparse`,
  no dependencies) calls a reusable `ador.core` library. Command surface:
  - **Lifecycle:** `ador run --loop` (the main poller), `ador run --once`
    (single pass for cron / Task Scheduler), `ador run --dry-run`.
  - **Operations:** `ador status`, `ador runs`, `ador pause` / `ador resume`,
    `ador retry <run-id>`, `ador cancel <run-id>`, `ador delete <run-id>`,
    `ador reset <run-id> --to <gate>`, `ador cleanup`, `ador logs <run-id>`.
    See section 8c for manual-override semantics.
  - **Statistics:** `ador stats`, `ador report <run-id>`, `ador export --csv`,
    `ador stats --html`.
  - **Config:** `ador config show | validate | set`.
- **Settings via TOML, no GUI.** `config.toml` is the source of truth; edit it by
  hand plus the `ador config` helpers. `ador config validate` at startup catches
  typos before the loop runs. A settings GUI is intentionally out of scope.
- **Startup / running as a service:**
  - Foreground (dev / Windows first tests): `ador run --loop`.
  - Ubuntu 22: a **systemd** unit running `ador run --loop` (auto-restart,
    journald logs).
  - Windows 11: **Task Scheduler** (or NSSM) running `ador run --loop` at boot,
    or `ador run --once` on a schedule.
  - **Single-instance lock** (`.ador/ador.lock`): since state is locally
    authoritative, prevents two pollers on the same repo.
- **No REST API / web UI in v1.** Avoids hosting a long-lived HTTP server (same
  objection as a Prometheus exporter). Reporting is the static HTML; control is
  the CLI.
- **Future seam:** because the core is a library, an optional **localhost-only,
  read-only** API using the stdlib `http.server` can be added later (off by
  default) without pulling in Flask/FastAPI.

### 12b. Secrets and Credentials

- **Secrets are kept out of `config.toml`.** They live in the environment or a
  gitignored `.env`, documented by a committed `.env.example` (the canonical
  "what secrets are required" list).
- **Two auth surfaces:**
  - **Git platform:** if `glab` / `gh` are already authenticated on the host, no token
    is needed - ADOR rides the CLI's auth. Optionally `GITLAB_TOKEN` /
    `GITHUB_TOKEN` for direct API calls or running the CLI inside the container.
  - **Executor model provider:** the required key(s) for the chosen executor
    (e.g. `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`), injected into the container.
- **Scope minimally.** The orchestrator reads its own secrets from the
  environment / `.env`; the container receives only the subset the executor needs,
  injected at `docker run` time. Never bake keys into the image.
- **On a server, prefer OS-level secret handling** - systemd `EnvironmentFile=`,
  an OS keyring, or CI/CD variables - over a flat `.env`; `.env.example` still
  documents what is required.

## 13. Domain: Observability and Metrics

**Design constraints (observations):**

- **Part of ADOR.** Statistics are a built-in feature of the orchestrator, not a
  separate service; they live under `.ador/` and use the same run-id.
- **Runs on Windows and Ubuntu with minimal dependencies.** Storage and queries
  use only the Python standard library (`sqlite3` + `json`). No database server,
  no message broker.
- **No Prometheus / external exporter.** Access is **CLI-first**, with an
  **optional static HTML** report. Nothing to host, no `/metrics` endpoint.

**Metric catalog:**

- **Outcome/throughput:** tickets picked, solved (merged), failed, timed-out,
  abandoned; success rate; counts by priority and type.
- **Timing:** time per gate, total wall-clock, queue wait, time-to-MR,
  time-in-review, clarification wait.
- **Executor/AI cost:** tokens in/out per run and per gate, model, executor
  launches, retries, clarification rounds, review rounds.
- **Code size:** files changed, lines added/removed, commits, branch/diff size.
- **Resource:** container uptime and count, peak CPU/RAM, disk used by worktrees
  and caches.
- **Quality/reliability:** gates passed first try, invariant failures,
  `delivery-preflight` result, CI result on the MR, human edits before merge,
  escalations, budget-exceeded counts.

**Data sources:** `journal.jsonl` events (timings, states, rounds);
`git diff --numstat` / `git rev-list --count` (code size); executor CLI usage
output (tokens/model); `docker stats` / `docker system df` (resource); the Git platform
adapter (merge/close time, CI result).

**Storage (local, stdlib only):**

- `journal.jsonl` per run stays the append-only raw source of truth.
- At each run's terminal state, a **run summary record** is computed and appended
  to a queryable **SQLite** DB (`.ador/metrics.db`), with a mirrored
  `runs.jsonl` for export. SQLite ships with Python and is portable across
  Windows and Ubuntu.

**Access:**

- **CLI:** `ador stats`, `ador stats --since 30d --by priority`,
  `ador report <run-id>`, `ador export --csv`.
- **Optional static HTML:** `ador stats --html` writes a self-contained dashboard
  file (no server, opened directly in a browser).

**Purpose:** this data is the promotion signal for moving crawl -> walk -> run,
and the honest answer to "is this actually helping?"

```toml
[metrics]
enabled          = true
db_path          = ".ador/metrics.db"
export_jsonl     = ".ador/metrics/runs.jsonl"
capture_tokens   = true
capture_resource = true            # docker stats / disk probes
html_out         = ".ador/metrics/stats.html"
```

## 14. Roadmap: Crawl -> Walk -> Run

- **Crawl (Windows 11):** manual/label trigger, human at every gate, one ticket,
  local worktree. Prove ticket -> gates -> draft MR on 2-3 small, well-specified
  tickets (e.g. #14 Global Refresh button, #13 staleness warning).
- **Walk:** thick conductor running in a container, `agent-ready` label poll on
  Ubuntu 22, clarification flow live, run budgets and metrics on. Stops at the
  draft MR.
- **Run:** parallel tickets in isolated containers, agent-proposed ranked queue
  with human confirm, dashboard, success-rate gating. Evaluate a CI-native
  executor. Consider auto-merge only for a proven low-risk change class.

## 15. Open Questions / Pending Decisions

- Exact `glab` / `gh` JSON flags for the installed versions (verify live).
- Exact headless invocation for each executor, and confirmation it runs the
  `.agentic` CLI (records evidence) non-interactively.
- Container runtime on Ubuntu 22 (Docker vs Podman) and the executor image
  contents.
- Default target branch for MRs (`develop` vs `main`).
- Whether to also keep a fully-headless skill variant (single-shot) alongside the
  thick conductor for high-confidence tickets.
- Model/provider selection and credential handling for the executor.
- `LICENSE.txt` contents (currently referenced but not yet added).

## 16. Reference

- Broader options analysis and trade-offs: see the initial proposal,
  `Agentic_Automation_Proposal.md` (to be filed alongside this document).
- Target-repo workflow contract: `.agentic/documents/CLI_API_REFERENCE.md` and
  `AGENTS.md` in the delivery-platform repository.
