<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Forge Adapters (`ador/forge/`)

> Component documentation per `component_documentation_template.md`.
> Sources: `04_Software/ador/forge/{__init__,base,gitlab,github}.py` -
> file versions 0.1.0.
> Design: Orchestrator_Design_And_Decisions.md section 4;
> Prerequisites_Check_Report.md sections 3-4.

## 1. Purpose

The single boundary between ADOR and the Git platform. The orchestrator never
calls `glab` or `gh` directly; it talks to the `Forge` interface, and one of
two adapters translates to the platform CLI. This keeps ADOR portable between
the GitLab instance it runs on today and GitHub.

## 2. Responsibilities

- `Forge` (ABC in `base.py`) - the full remote surface ADOR needs:
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
- `GitLabForge` (`gitlab.py`, over `glab`) and `GitHubForge` (`github.py`,
  over `gh`) implement it; `build_forge(kind, repo, runner)` selects one from
  `[platform]` config.
- Normalization of platform differences into shared `Ticket` / `Comment`
  dataclasses.

Explicitly not owned - and deliberately absent from the interface:
**merging**. There is no merge method; the boundary "ADOR opens a draft and
stops" is structural, not a convention (design 11). Plain git operations
(fetch/push/worktree) are also not here; they belong to the isolation layer.

## 3. Implementation Overview

- Every call goes through an injected `CommandRunner` (default
  `ador.util.run_command`), so both adapters are unit-tested offline with a
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
  - comments via the REST API (`gh api repos/.../issues/N/comments`), edits
    via `PATCH repos/.../issues/comments/<id>` (comment ids are repo-global);
  - created comment id parsed from the `#issuecomment-<id>` URL;
  - `gh pr create --draft --head --base`; `remove_source_branch` is ignored
    (a repository setting on GitHub).

## 4. Dependencies

- Internal: `ador.util` (`CommandRunner`, `CommandResult`, `run_command`).
- External: the authenticated `glab` (>= 1.105 verified) or `gh` (>= 2.95)
  CLI on the host; Python standard library otherwise.

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
  `draft=True` by ADOR (config validation rejects `draft = false`).

## 7. Workflow Integration

Called by the orchestrator (later phases) at every remote touchpoint: polling
(`list_ready`), reconciliation (`get_ticket`), status marking and
clarification (`post_comment`/`edit_comment`/labels), resume detection
(`list_comments`), and delivery (`open_merge_request`). The executor never
receives forge access - "who posts: the orchestrator, never the executor"
(design 9).

## 8. Usage

```python
from ador.forge import build_forge

forge = build_forge("gitlab", "grp/proj")
tickets = forge.list_ready("agent-ready")
note_id = forge.post_comment(14, "[ADOR] status ...\n<!-- ador:... -->")
forge.edit_comment(14, note_id, "updated body")
url = forge.open_merge_request("ador/run-14", "develop", "Draft: ...", body,
                               reviewers=["dan.pasare"])
```

## 9. Validation And Tests

- `tests/test_forge.py` (fake runner, fully offline): factory selection,
  JSON-to-Ticket mapping for both platforms, note/comment id parsing plus
  fallback, the GitLab PUT edit endpoint, system-note flagging, label argv
  construction, draft MR/PR creation and URL parsing, 404 -> `None`, and the
  hostile-output suite (non-JSON, wrong shape, missing URLs, unrecoverable
  ids, error context in `ForgeError`).
- Minimum validation after a change: `uv run --group dev pytest tests/test_forge.py`.
- **Live read-only verification done 2026-07-03** against glab 1.105.0 on the
  real instance (Prerequisites_Check_Report.md section 11): issue list/view
  JSON shapes, label filter, notes API, 404 handling, and all mutating-command
  flags confirmed. One finding fixed: comment-body edits now use
  `--raw-field` (string) instead of `--field` (type-inferred). Still not
  verifiable read-only: the `#note_<id>` URL in `glab issue note` output
  (fallback exists; first mutating test confirms it).

## 10. Limitations And Future Work

- Pagination is capped at 100 items per call; enough for the pilot queue.
- MR review-thread reading (post-MR revise loop, design 11b) and CI-status
  reading are not yet part of the interface; they arrive with that phase.
- GitLab flags are verified live (read-only, 2026-07-03); GitHub flags are
  verified offline only - `gh` is not authenticated on this host, so the gh
  path gets its live check when a GitHub pilot repo exists.
