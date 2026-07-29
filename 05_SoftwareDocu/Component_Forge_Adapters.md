<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Forge Adapters (`adore/forge/`)

> Component documentation per `component_documentation_template.md`.
> Sources: `04_Software/adore/forge/{__init__,base,gitlab,github,gitea}.py` -
> file versions 0.1.0 (`gitlab`/`github` adapters at method version 0.1.1,
> `gitea` at 0.1.0, factory `build_forge` at 0.2.0).
> Design: Orchestrator_Design_And_Decisions.md section 4;
> Host forge authentication: `01_Documentation/Security_And_Credentials.md`.

## 1. Purpose

The single boundary between ADORE and the Git platform. The orchestrator never
calls `glab`, `gh` or `tea` directly; it talks to the `Forge` interface, and
one of three adapters translates to the platform CLI. This keeps ADORE portable
between the GitLab instance it runs on today, GitHub, and a self-hosted Gitea.

## 2. Responsibilities

- `Forge` (ABC in `base.py`) - the full remote surface ADORE needs:
  - selection: `list_ready(label)`, `get_ticket(iid)`;
  - signaling: `list_comments(iid)`, `post_comment(iid, body)`,
    `edit_comment(iid, comment_id, body)`, `add_labels` / `remove_labels`;
  - delivery: `open_merge_request(source, target, title, body, draft=True,
    reviewers, remove_source_branch, cwd)` and `get_merge_request(ref)` (by
    iid/number or source branch; branch lookup finds only OPEN MRs, so the
    post-MR poll uses the stored iid). `MergeRequest` carries the normalized
    state (opened/merged/closed) and the labels (the revise trigger reads
    them);
  - review loop: `list_mr_comments(mr_iid)` (the review thread fed to the
    executor; GitHub v1 covers conversation comments, inline review threads
    are a refinement) and `remove_mr_labels(mr_iid, labels)` (clears the
    revise trigger; GitLab via API PUT remove_labels, GitHub via
    `gh pr edit --remove-label`).
- `GitLabForge` (`gitlab.py`, over `glab`), `GitHubForge` (`github.py`, over
  `gh`) and `GiteaForge` (`gitea.py`, over `tea`) implement it;
  `build_forge(kind, repo, runner, login=...)` selects one from `[platform]`
  config (`login` is the tea login name, gitea-only; the factory rejects it
  for other kinds).
- Normalization of platform differences into shared `Ticket` / `Comment`
  dataclasses.

Explicitly not owned - and deliberately absent from the interface:
**merging**. There is no merge method; the boundary "ADORE opens a draft and
stops" is structural, not a convention (design 11). Plain git operations
(fetch/push/worktree) are also not here; they belong to the isolation layer.

## 3. Implementation Overview

- Every call goes through an injected `CommandRunner` (default
  `adore.util.run_command`), so both adapters are unit-tested offline with a
  fake runner replaying canned CLI output.
- Failure model: non-zero exit -> `ForgeError` carrying the argv and stderr
  (journal-ready). `get_ticket` maps not-found/404 to `None` - a deleted
  ticket is a reconciliation signal, not an error.
- Fail-closed parsing: non-JSON output, JSON of the wrong shape, an MR/PR
  created without a printed URL, or an unrecoverable comment id all raise
  `ForgeError` instead of guessing.
- GitLab specifics (from the prerequisites check):
  - `glab issue list/view --output json` for structured records;
  - notes read via `glab api projects/:enc/issues/:iid/notes` (oldest-first,
    `system` flagged so resume detection can skip system notes);
  - **note editing has no glab subcommand** - it is
    `glab api --method PUT projects/:enc/issues/:iid/notes/:id`, with the
    body as `--raw-field` (guaranteed string; `--field` would type-infer);
  - the project path is percent-encoded for API endpoints;
  - created note id parsed from the `#note_<id>` URL glab prints, with a
    fallback that matches the newest note body;
  - `glab mr create --draft --yes` with `--reviewer`/`--remove-source-branch`.
- GitHub specifics:
  - `gh issue list/view --json <fields>`; label objects and `OPEN`/`CLOSED`
    states normalized to the GitLab shape;
  - `gh` returns only the fields named in `--json`, so `get_merge_request`
    **must** include `labels` in its field set - it does, and a regression test
    pins the selection. Omitting it made every MR read back with no labels,
    which silently disabled the revise-label trigger on GitHub;
  - comments via the REST API (`gh api repos/.../issues/N/comments`), edits
    via `PATCH repos/.../issues/comments/<id>` (comment ids are repo-global);
  - created comment id parsed from the `#issuecomment-<id>` URL;
  - `gh pr create --draft --head --base`; `remove_source_branch` is ignored
    (a repository setting on GitHub).
- Gitea specifics (live-verified against tea 0.15.0 / Gitea 1.25.4 on
  2026-07-29):
  - **Reads and comment/PR writes go through `tea api`** (the raw Gitea REST
    API), NOT tea's native `--output json`: the native output is lossy - the
    issue index comes back as a string, labels as one joined string, the
    author as the display name, and an empty comment list prints
    "No comments found" instead of `[]`. The REST payload has the real types
    (`number`, `user.login`, label objects, `html_url`).
  - **`tea api` exits 0 even on HTTP 4xx/5xx.** Every call therefore runs
    `tea api -i` and the adapter parses the `HTTP/1.1 <code>` status line
    (written to stderr) itself: missing status or >= 400 raises `ForgeError`;
    404 maps to `None` only where the contract allows. The exit code only
    reports tea-level failures (no login, network down).
  - **Endpoints never start with `/`** - a leading slash breaks tea's
    `/api/v1` prefixing and lands on the web router (a text 404 with HTTP
    status 200-path confusion).
  - Draft is the `WIP: ` title prefix (Gitea's convention; also what
    `tea pulls create --draft` does); the adapter prepends it only when
    missing. On read, `draft` is native on Gitea >= 1.22 with the WIP-title
    fallback for older payloads; merged PRs report state "closed" plus a
    `merged` boolean, normalized to "merged".
  - The created comment id and PR `html_url`/`number` come straight from the
    POST response JSON - no URL scraping, no fallback needed.
  - Label add/remove uses `tea issues edit --add-labels/--remove-labels` and
    `tea pulls edit --remove-labels` (tea resolves label NAMES to the ids the
    raw API wants). tea subcommands DO exit non-zero on errors, so the plain
    exit-code contract applies there.
  - Reviewer requests are a separate Gitea endpoint and are best-effort: a
    rejected reviewer must not lose the already-created draft PR.
  - `list_ready` must pass `type=issues` - the Gitea issues endpoint returns
    PRs too without it. Issues and PRs share one index space, so
    `list_mr_comments` is the issues comments endpoint (system events live
    elsewhere; `system` is always False, like GitHub).
  - **`list_ready` post-filters on the label**: when the label NAME does not
    exist in the repository, Gitea silently drops the `labels=` filter and
    returns every open issue (live finding on the pilot repo) - without the
    client-side filter a typo'd ready label would select the entire backlog
    for conduction.
  - `[platform] login` selects the tea login (`tea logins list`) and is
    appended as `--login` to every call; without it tea uses its default
    login (set one with `tea logins default <name>`).
  - The repo slug must be exactly `OWNER/REPO` (Gitea has no subgroups);
    the adapter fails closed at construction otherwise. `cwd` is ignored -
    pure API calls need no local checkout, so the glab/gh "No git remotes
    found" workaround does not apply.
- Selection reads the full ready pool, not the first page: `GitLabForge`
  paginates `glab issue list` (GitLab caps `--per-page` at 100, bounded by
  `_MAX_LIST_PAGES`) and `GitHubForge` reads up to `--limit 500`, so a
  high-priority ticket beyond the first 100 is still ranked. `GiteaForge`
  paginates at 50 (the server's `MAX_RESPONSE_ITEMS` floor, confirmed via
  `settings/api`) guided by the `X-Total-Count` response header, so the walk
  stays correct even when a stricter server clamps pages below the requested
  size; a short page is the fallback stop when the header is absent, bounded
  by `_MAX_LIST_PAGES`.

## 4. Dependencies

- Internal: `adore.util` (`CommandRunner`, `CommandResult`, `run_command`).
- External: the authenticated `glab` (>= 1.105 verified), `gh` (>= 2.95) or
  `tea` (>= 0.15 required - older tea lacks `tea api`; 0.15.0 verified
  against Gitea 1.25.4) CLI on the host; Python standard library otherwise.

## 5. Inputs And Outputs

- Inputs: label names and ticket ids from the orchestrator; comment bodies
  already stamped with the identity marker by the caller.
- Outputs: normalized `Ticket` / `Comment` lists, created comment ids
  (recorded in `state.json` for idempotency), and the MR/PR web URL.

## 6. Data Contracts

- `Ticket`: iid, title, description, labels (plain strings), author, state
  (`opened`/`closed`), web_url, created_at, updated_at.
- `Comment`: id, body, author, created_at, `system` flag (GitLab system notes;
  always `False` on GitHub, where events are a separate API).
- `open_merge_request` returns the web URL and is always called with
  `draft=True` by ADORE (config validation rejects `draft = false`).

## 7. Workflow Integration

Called by the orchestrator (later phases) at every remote touchpoint: polling
(`list_ready`), reconciliation (`get_ticket`), status marking and
clarification (`post_comment`/`edit_comment`/labels), resume detection
(`list_comments`), and delivery (`open_merge_request`). The executor never
receives forge access - "who posts: the orchestrator, never the executor"
(design 9).

## 8. Usage

```python
from adore.forge import build_forge

forge = build_forge("gitlab", "grp/proj")
forge = build_forge("gitea", "owner/repo", login="home")  # tea login name
tickets = forge.list_ready("agent-ready")
note_id = forge.post_comment(14, "[ADORE] status ...\n<!-- adore:... -->")
forge.edit_comment(14, note_id, "updated body")
url = forge.open_merge_request("adore/run-14", "develop", "Draft: ...", body,
                               reviewers=["reviewer.one"])
```

## 9. Validation And Tests

- `tests/test_forge.py` (fake runner, fully offline): factory selection (incl.
  gitea + the login-for-non-gitea rejection), JSON-to-Ticket mapping for all
  three platforms, note/comment id parsing plus fallback, the GitLab PUT edit
  endpoint, system-note flagging, label argv construction, draft MR/PR
  creation and URL parsing, 404 -> `None`, and the hostile-output suite
  (non-JSON, wrong shape, missing URLs, unrecoverable ids, error context in
  `ForgeError`). The Gitea suite additionally pins the tea-specific hazards:
  HTTP-status-line enforcement despite exit 0 (404/500/missing status), the
  no-leading-slash endpoint rule, X-Total-Count pagination (incl. the
  clamped-short-page case and the lying-header runaway guard), the WIP title
  prefix edges, comment id from response JSON, best-effort reviewers, and the
  OWNER/REPO constructor guard.
- Minimum validation after a change: `uv run --group dev pytest tests/test_forge.py`.
- **Live read-only verification done 2026-07-03** against glab 1.105.0 on the
  real instance: issue list/view
  JSON shapes, label filter, notes API, 404 handling, and all mutating-command
  flags confirmed. One finding fixed: comment-body edits now use
  `--raw-field` (string) instead of `--field` (type-inferred). Still not
  verifiable read-only: the `#note_<id>` URL in `glab issue note` output
  (fallback exists; first mutating test confirms it).

## 10. Limitations And Future Work

- GitLab selection paginates in 100-item pages up to `_MAX_LIST_PAGES` (50);
  GitHub reads up to 500 in one call; Gitea paginates in 50-item pages up to
  the same bound. Beyond those bounds the pool is still capped - large enough
  for realistic ready queues.
- MR review-thread reading (post-MR revise loop, design 11b) and CI-status
  reading are not yet part of the interface; they arrive with that phase.
- Label names containing a comma cannot be addressed on GitHub/Gitea (both
  adapters comma-join label lists for their CLIs).
- Gitea permits several repo labels with the SAME name (live finding); a
  ticket carrying such duplicates maps to a repeated name in `Ticket.labels`.
  Harmless for ADORE (all label logic is membership-based), but keep repo
  label names unique for sane output.
- Gitea reviewer requests are best-effort (see section 3); a failed request
  is currently silent beyond the missing reviewer on the PR itself.
- GitLab flags are verified live (read-only, 2026-07-03); GitHub flags are
  verified offline only - `gh` is not authenticated on this host, so the gh
  path gets its live check when a GitHub pilot repo exists. The Gitea adapter
  is live-verified read-only against Gitea 1.25.4 (2026-07-29); the mutating
  path gets its live check on a scratch repository.
