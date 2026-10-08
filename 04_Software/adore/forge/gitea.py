#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file gitea.py
@brief Gitea adapter implemented over the `tea` CLI (>= 0.15).
@details Reads and writes go through `tea api` (the raw Gitea REST API) because
         tea's native `--output json` is lossy: indexes come back as strings,
         labels as a joined string, authors as display names, and an empty
         comment list prints "No comments found" instead of JSON (verified
         live against tea 0.15.0 / Gitea 1.25.4, 2026-07-29). Two tea quirks
         shape every call:
         - `tea api` exits 0 even on HTTP 4xx/5xx, so each call runs with
           `-i` and the HTTP status line (written to stderr) is parsed and
           enforced here;
         - an endpoint starting with "/" breaks tea's `/api/v1` prefixing and
           hits the web router (a text 404), so endpoints are always built
           without a leading slash.
         Label add/remove goes through `tea issues edit` / `tea pulls edit`,
         which resolve label NAMES to ids (the raw API wants label ids). The
         command runner is injected so the adapter is unit-testable without
         tea. `_run` and `_parse_json` moved to the shared `Forge` base
         (ADORE-PY-004); `_api`'s HTTP-status-based not-found handling stays
         local, not force-fit into the marker-based heuristic glab/gh share.
"""

from __future__ import annotations

# IMPORTS
import contextlib
import json
import re
from typing import Any
import urllib.parse

from adore.forge.base import Comment, Forge, ForgeError, MergeRequest, Ticket
from adore.util import CommandResult, CommandRunner, run_command

# CONSTANTS

# `tea api -i` writes "HTTP/1.1 200 OK" plus headers to stderr; take the LAST
# status line so a proxy/redirect preamble can never shadow the final verdict.
_HTTP_STATUS_RE = re.compile(r"^HTTP/[\d.]+\s+(\d{3})", re.MULTILINE)
_TOTAL_COUNT_RE = re.compile(r"^X-Total-Count:\s*(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
# Gitea treats WIP-prefixed titles as draft PRs (default WORK_IN_PROGRESS_PREFIXES).
_WIP_RE = re.compile(r"(?i)^\s*(?:wip:|\[wip\])")
# Gitea clamps list pages at [api] MAX_RESPONSE_ITEMS (default 50; confirmed
# via `settings/api` on the live instance). Request exactly that floor and walk
# pages - guided by X-Total-Count where the server sends it - so a ready pool
# beyond one page is still ranked; bounded so a runaway never loops.
_PAGE_SIZE = 50
_MAX_LIST_PAGES = 50
# Gitea CombinedStatus `state` -> the normalized PIPELINE_STATES vocabulary.
# "warning" is Gitea's non-blocking verdict, so it is not a failure.
_PIPELINE_STATES = {
    "success": "success",
    "failure": "failed",
    "error": "failed",
    "pending": "running",
    "running": "running",
    "warning": "none",
}

# PUBLIC API


class GiteaForge(Forge):
    """
    @brief   Gitea implementation of the Forge interface (via `tea`).
    """

    def __init__(self, repo: str, runner: CommandRunner = run_command, *,
                 login: str = "") -> None:
        """
        @brief      Bind the adapter to a Gitea repository.
        @details    Gitea has no subgroups, so the slug is exactly OWNER/REPO;
                    anything else fails closed here rather than producing
                    malformed API endpoints later.
        @param[in]  repo Gitea repository (OWNER/REPO).
        @param[in]  runner Command runner (injectable for tests).
        @param[in]  login tea login name (`tea logins list`) appended as
                          `--login` to every call; empty uses tea's default
                          login. Set it whenever more than one login exists or
                          the wanted login is not the default.
        @exception  ValueError When repo is not OWNER/REPO.
        """
        parts = repo.split("/")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError(f"gitea repo must be OWNER/REPO: {repo!r}")
        self.repo = repo
        self.runner = runner
        self.login = login

    # -- selection ----------------------------------------------------------------

    def list_ready(self, ready_label: str) -> list[Ticket]:
        """
        @brief      List open issues carrying the label via the issues API.
        @details    `type=issues` is mandatory: the Gitea issues endpoint
                    returns pull requests too without it, and a PR in the
                    selection pool would be conducted as a ticket. The result
                    is additionally POST-FILTERED on the label: when the label
                    NAME does not exist in the repository, Gitea silently
                    drops the `labels=` filter and returns every open issue
                    (live finding, Gitea 1.25.4, 2026-07-29) - without the
                    post-filter a typo'd ready label would select the entire
                    backlog.
        @param[in]  ready_label Eligibility label.
        @return     Eligible tickets, unordered (caller ranks by priority).
        @exception  ForgeError When tea fails or the response is malformed.
        """
        items = self._get_paged(
            f"repos/{self.repo}/issues",
            {"state": "open", "type": "issues", "labels": ready_label},
        )
        tickets = (self._to_ticket(item) for item in items)
        return [ticket for ticket in tickets if ready_label in ticket.labels]

    def get_ticket(self, iid: int) -> Ticket | None:
        """
        @brief      Fetch one issue; None when it was deleted.
        @param[in]  iid Issue index.
        @return     The ticket or None on HTTP 404.
        @exception  ForgeError When tea fails for another reason.
        """
        result = self._api("GET", f"repos/{self.repo}/issues/{iid}", allow_404=True)
        if result is None:
            return None
        return self._to_ticket(self._parse_json(result, dict))

    # -- comments -----------------------------------------------------------------

    def list_comments(self, iid: int) -> list[Comment]:
        """
        @brief      Read all issue comments oldest-first via the REST API.
        @details    Gitea keeps system events (label changes etc.) out of the
                    comments endpoint - like GitHub - so `system` is always
                    False here.
        @param[in]  iid Issue index.
        @return     All comments, oldest first.
        @exception  ForgeError When tea fails or the response is malformed.
        """
        items = self._get_paged(f"repos/{self.repo}/issues/{iid}/comments", {})
        return [self._to_comment(item) for item in items]

    def post_comment(self, iid: int, body: str) -> int:
        """
        @brief      Create a comment via the REST API (POST).
        @details    The created id comes straight from the response JSON -
                    stronger than the URL-scraping the glab/gh adapters need.
                    `--field` is tea's guaranteed-string field (`--Field` would
                    type-infer, the same trap as glab/gh `--field`).
        @param[in]  iid Issue index.
        @param[in]  body Comment body.
        @return     Created comment id.
        @exception  ForgeError When tea fails or the response carries no id.
        """
        result = self._api(
            "POST", f"repos/{self.repo}/issues/{iid}/comments", fields=[("body", body)]
        )
        data = self._parse_json(result, dict)
        comment_id = data.get("id")
        if comment_id is None:
            raise ForgeError("gitea comment response carries no id",
                             result.argv, result.stderr)
        return int(comment_id)

    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """
        @brief      Edit a comment in place via the REST API (PATCH).
        @param[in]  iid Issue index (unused; Gitea comment ids are repo-global).
        @param[in]  comment_id Comment id.
        @param[in]  body Replacement body.
        @exception  ForgeError When tea fails.
        """
        del iid  # comment ids are repo-global on Gitea
        self._api(
            "PATCH", f"repos/{self.repo}/issues/comments/{comment_id}",
            fields=[("body", body)],
        )

    # -- labels -------------------------------------------------------------------

    def add_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Add labels via `tea issues edit --add-labels`.
        @details    The subcommand resolves label NAMES to ids (the raw API
                    wants ids). Labels are comma-joined, so a label name
                    containing a comma cannot be addressed (same limitation as
                    the gh adapter).
        @param[in]  iid Issue index.
        @param[in]  labels Labels to add.
        @exception  ForgeError When tea fails.
        """
        if not labels:
            return
        self._run(
            ["tea", "issues", "edit", str(iid), "--repo", self.repo,
             "--add-labels", ",".join(labels), *self._login_argv()]
        )

    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """
        @brief      Remove labels via `tea issues edit --remove-labels`.
        @param[in]  iid Issue index.
        @param[in]  labels Labels to remove.
        @exception  ForgeError When tea fails.
        """
        if not labels:
            return
        self._run(
            ["tea", "issues", "edit", str(iid), "--repo", self.repo,
             "--remove-labels", ",".join(labels), *self._login_argv()]
        )

    # -- delivery -----------------------------------------------------------------

    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        """
        @brief      Fetch one PR by number or head branch via the pulls API.
        @details    Numbers hit `pulls/{n}` directly; a branch name scans the
                    OPEN pulls for a matching head ref (matching the interface
                    contract: branch lookup finds only open MRs, terminal-state
                    polling must use the stored number).
        @param[in]  ref PR number, or the head branch name (open PRs only).
        @return     The MergeRequest (state normalized), or None.
        @exception  ForgeError When tea fails for another reason.
        """
        if isinstance(ref, int) or str(ref).isdigit():
            result = self._api("GET", f"repos/{self.repo}/pulls/{ref}", allow_404=True)
            if result is None:
                return None
            return self._to_merge_request(self._parse_json(result, dict))
        pulls = self._get_paged(f"repos/{self.repo}/pulls", {"state": "open"})
        for item in pulls:
            if (item.get("head") or {}).get("ref") == ref:
                return self._to_merge_request(item)
        return None

    def pipeline_status(self, mr_iid: int) -> str:
        """
        @brief      The PR head commit's combined status; never raises.
        @details    Gitea keys commit status by SHA, not by PR, so this reads
                    the pull to learn `head.sha` and then its combined status.
                    An empty `state` means no CI reported on that commit, which
                    is "none" rather than a pass. Actions and external CI both
                    land on this endpoint.
        @param[in]  mr_iid PR number.
        @return     A PIPELINE_STATES value.
        """
        try:
            pull = self._api("GET", f"repos/{self.repo}/pulls/{mr_iid}", allow_404=True)
            if pull is None:
                return "unknown"
            head = self._parse_json(pull, dict).get("head") or {}
            sha = head.get("sha") if isinstance(head, dict) else None
            if not sha:
                return "unknown"
            combined = self._api(
                "GET", f"repos/{self.repo}/commits/{sha}/status", allow_404=True
            )
            if combined is None:
                return "none"
            payload = self._parse_json(combined, dict)
        except ForgeError:
            return "unknown"
        # Gitea answers `state: "pending"` with an EMPTY status list when
        # NOTHING has reported on the commit, so a repository with no CI at all
        # would read as a pipeline forever in progress (live finding, Gitea
        # 1.27.2). The count decides before the state does.
        if not payload.get("total_count") and not payload.get("statuses"):
            return "none"
        state = str(payload.get("state") or "").lower()
        if not state:
            return "none"
        return _PIPELINE_STATES.get(state, "unknown")

    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      Read the whole PR review thread oldest-first (REST API).
        @details    Issues and PRs share one index space, so the issues
                    comments endpoint covers the conversation - but a
                    submitted review's own text and its inline diff comments
                    live under `pulls/<n>/reviews`. The revise loop needs
                    those: without them a reviewer who requested changes from
                    the diff view left the revision executor an EMPTY thread,
                    spending a review round on a blind revision.
        @param[in]  mr_iid PR number.
        @return     Conversation, review-body and inline comments, oldest first.
        @exception  ForgeError When tea fails.
        """
        comments = self.list_comments(mr_iid)
        comments.extend(self._review_comments(mr_iid))
        comments.sort(key=lambda item: (item.created_at, item.id))
        return comments

    def _review_comments(self, mr_iid: int) -> list[Comment]:
        """
        @brief      Submitted review bodies plus their inline diff comments.
        @details    Gitea keeps a review's inline comments behind a per-review
                    endpoint, so each review with an id costs one extra call.
                    A bodyless review is a bare approve/close event carrying no
                    instruction, so it is dropped rather than padding the
                    thread the executor reads.
        @param[in]  mr_iid PR number.
        @return     Review-surface comments (empty when the PR has none).
        @exception  ForgeError When tea fails.
        """
        found: list[Comment] = []
        reviews = self._get_paged(f"repos/{self.repo}/pulls/{mr_iid}/reviews", {})
        for review in reviews:
            if str(review.get("body") or "").strip():
                found.append(self._to_comment(review))
            review_id = review.get("id")
            if review_id is None:
                continue
            inline = self._get_paged(
                f"repos/{self.repo}/pulls/{mr_iid}/reviews/{review_id}/comments", {}
            )
            found.extend(
                self._to_comment(item) for item in inline
                if str(item.get("body") or "").strip()
            )
        return found

    def post_mr_comment(self, mr_iid: int, body: str) -> int:
        """@brief Post a PR conversation comment through the issues surface."""
        return self.post_comment(mr_iid, body)

    def edit_mr_comment(self, mr_iid: int, comment_id: int, body: str) -> None:
        """@brief Edit a PR conversation comment through the issues surface."""
        self.edit_comment(mr_iid, comment_id, body)

    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """
        @brief      Remove PR labels via `tea pulls edit --remove-labels`.
        @param[in]  mr_iid PR number.
        @param[in]  labels Labels to remove.
        @exception  ForgeError When tea fails.
        """
        if not labels:
            return
        self._run(
            ["tea", "pulls", "edit", str(mr_iid), "--repo", self.repo,
             "--remove-labels", ",".join(labels), *self._login_argv()]
        )

    def open_merge_request(
        self,
        source: str,
        target: str,
        title: str,
        body: str,
        *,
        draft: bool = True,
        reviewers: list[str] | None = None,
        remove_source_branch: bool = True,
        cwd: str | None = None,
    ) -> str:
        """
        @brief      Open a draft or ready pull request via the REST API. Never merges.
        @details    Draft on Gitea is the `WIP: ` title prefix (tea's own
                    `--draft` does the same); the prefix is added only when the
                    title has none. The response JSON carries `html_url` and
                    `number` directly, so nothing is scraped from CLI text.
                    Reviewer requests are a SEPARATE endpoint on Gitea and are
                    best-effort: a rejected reviewer (for example no repo
                    access) must not lose the already-created PR, so that
                    follow-up failure is swallowed - the created PR itself is the
                    delivery. `remove_source_branch` is ignored (a repository
                    setting on Gitea) and `cwd` is not needed (pure API call,
                    no local remote resolution).
        @param[in]  source Head branch.
        @param[in]  target Base branch.
        @param[in]  title PR title.
        @param[in]  body PR description.
        @param[in]  draft Open as draft when true, otherwise ready for review.
        @param[in]  reviewers Reviewer usernames (best-effort on Gitea).
        @param[in]  remove_source_branch Ignored (a repo setting on Gitea).
        @param[in]  cwd Ignored (tea resolves everything from --repo/--login).
        @return     PR web URL.
        @exception  ForgeError When tea fails or the response has no html_url.
        """
        del remove_source_branch  # branch deletion is a repo setting on Gitea
        del cwd  # pure API call; no local checkout involved
        wip_title = title if not draft or _WIP_RE.match(title) else f"WIP: {title}"
        result = self._api(
            "POST", f"repos/{self.repo}/pulls",
            fields=[("title", wip_title), ("body", body),
                    ("head", source), ("base", target)],
        )
        data = self._parse_json(result, dict)
        url = data.get("html_url", "")
        if not url:
            raise ForgeError("gitea pull-request response carries no html_url",
                             result.argv, result.stdout)
        number = data.get("number")
        if reviewers and number is not None:
            # best-effort: the draft PR exists; reviewers are a courtesy
            with contextlib.suppress(ForgeError):
                self._api(
                    "POST", f"repos/{self.repo}/pulls/{number}/requested_reviewers",
                    data=json.dumps({"reviewers": list(reviewers)}),
                )
        return url

    # -- internals ------------------------------------------------------------------

    def _login_argv(self) -> list[str]:
        """
        @brief   The `--login` argv fragment when a login is configured.
        @return  ["--login", name] or [].
        """
        return ["--login", self.login] if self.login else []

    def _api(
        self,
        method: str,
        endpoint: str,
        fields: list[tuple[str, str]] | None = None,
        data: str | None = None,
        *,
        allow_404: bool = False,
    ) -> CommandResult | None:
        """
        @brief      Run `tea api -i`, enforcing the HTTP status ourselves.
        @details    tea 0.15 exits 0 even on HTTP 4xx/5xx (verified live), so
                    the exit code only reports tea-level failures (no login,
                    network down). The real verdict is the status line `-i`
                    writes to stderr: missing status or >= 400 fails closed.
                    The endpoint must not start with "/" - that breaks tea's
                    `/api/v1` prefixing and hits the web router instead.
        @param[in]  method HTTP method (GET/POST/PATCH/DELETE).
        @param[in]  endpoint API endpoint relative to /api/v1 (no leading /).
        @param[in]  fields String body fields, sent via `--field` (guaranteed
                          string, never type-inferred).
        @param[in]  data Raw JSON body, sent via `--data` (for non-string
                         payloads such as arrays).
        @param[in]  allow_404 Map HTTP 404 to None (deleted resource) instead
                              of raising.
        @return     The successful CommandResult, or None on an allowed 404.
        @exception  ForgeError When tea fails, the status line is missing, or
                    the HTTP status is >= 400 (except an allowed 404).
        """
        argv = ["tea", "api", "-i", "--method", method, *self._login_argv()]
        for key, value in fields or []:
            argv += ["--field", f"{key}={value}"]
        if data is not None:
            argv += ["--data", data]
        argv.append(endpoint.lstrip("/"))
        result = self.runner(argv)
        if not result.ok:
            raise ForgeError("tea api failed", result.argv, result.stderr)
        statuses = _HTTP_STATUS_RE.findall(result.stderr)
        if not statuses:
            raise ForgeError("tea api printed no HTTP status (need tea >= 0.15)",
                             result.argv, result.stderr)
        status = int(statuses[-1])
        if status == 404 and allow_404:
            return None
        if status >= 400:
            raise ForgeError(f"tea api {method} {endpoint} returned HTTP {status}",
                             result.argv, result.stdout or result.stderr)
        return result

    def _get_paged(self, path: str, query: dict[str, str]) -> list[dict[str, Any]]:
        """
        @brief      GET a list endpoint page by page until it is exhausted.
        @details    Pages are `_PAGE_SIZE` (the Gitea MAX_RESPONSE_ITEMS floor).
                    The stop condition prefers the X-Total-Count header - it
                    stays correct even when a stricter server clamps pages
                    below the requested size; a short page is the fallback when
                    the header is absent, and `_MAX_LIST_PAGES` bounds runaways.
        @param[in]  path Endpoint path (no query string, no leading /).
        @param[in]  query Extra query parameters (page/limit are added here).
        @return     The concatenated item list.
        @exception  ForgeError When tea fails or a page is malformed.
        """
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            params = {**query, "limit": str(_PAGE_SIZE), "page": str(page)}
            result = self._api("GET", f"{path}?{urllib.parse.urlencode(params)}")
            batch = self._parse_json(result, list)
            items.extend(batch)
            if not batch or page >= _MAX_LIST_PAGES:
                return items
            total_match = _TOTAL_COUNT_RE.search(result.stderr)
            if total_match is not None:
                if len(items) >= int(total_match.group(1)):
                    return items
            elif len(batch) < _PAGE_SIZE:
                return items
            page += 1

    # `_run` (tea subcommands, non-API) and `_parse_json` moved to the shared
    # `Forge` base (ADORE-PY-004); `_api`'s HTTP-status not-found handling is
    # deliberately left as-is, not unified with the marker-based heuristic
    # `_is_not_found` uses for glab/gh - see forge/base.py's docstring.

    @staticmethod
    def _username(user: Any) -> str:
        """
        @brief      Extract the login name from a Gitea user object.
        @details    `login` is the canonical field; `username` is its alias in
                    newer payloads. Never the display name - callers expect
                    the account handle, as on GitLab/GitHub.
        @param[in]  user Raw user mapping (or None).
        @return     The login, or "" when absent.
        """
        if not isinstance(user, dict):
            return ""
        return user.get("login") or user.get("username") or ""

    @classmethod
    def _to_comment(cls, item: dict[str, Any]) -> Comment:
        """
        @brief      Map one Gitea comment or review record to a Comment.
        @details    A submitted review timestamps itself with `submitted_at`
                    rather than `created_at`; falling back keeps every review
                    surface on one sortable timeline instead of pinning
                    reviews to the start of the thread. Gitea keeps system
                    events out of these endpoints, so `system` is always False.
        @param[in]  item Raw comment/review mapping.
        @return     The normalized Comment.
        """
        return Comment(
            id=int(item["id"]),
            body=item.get("body", ""),
            author=cls._username(item.get("user")),
            created_at=item.get("created_at") or item.get("submitted_at", ""),
            system=False,
        )

    @classmethod
    def _to_ticket(cls, item: dict[str, Any]) -> Ticket:
        """
        @brief      Map one Gitea issue JSON record to a Ticket.
        @details    Gitea returns labels as objects with a name field and
                    states as open/closed; both are normalized to the shared
                    shape ("opened" like GitLab).
        @param[in]  item Raw issue mapping.
        @return     The normalized Ticket.
        @exception  ForgeError When the record misses the issue number.
        """
        state = str(item.get("state", "open")).lower()
        return Ticket(
            iid=int(item["number"]),
            title=item.get("title", ""),
            description=item.get("body") or "",
            labels=[label["name"] for label in item.get("labels") or []],
            author=cls._username(item.get("user")),
            state="opened" if state == "open" else state,
            web_url=item.get("html_url", ""),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )

    @staticmethod
    def _to_merge_request(data: dict[str, Any]) -> MergeRequest:
        """
        @brief      Map one Gitea pull JSON record to a MergeRequest.
        @details    Gitea reports merged PRs as state "closed" with a separate
                    `merged` boolean, so merged wins the normalization. `draft`
                    is native on Gitea >= 1.22; the WIP title prefix is the
                    fallback for older payloads.
        @param[in]  data Raw pull mapping.
        @return     The normalized MergeRequest.
        @exception  ForgeError When the record misses the pull number.
        """
        state = str(data.get("state", "open")).lower()
        if data.get("merged"):
            state = "merged"
        elif state == "open":
            state = "opened"
        return MergeRequest(
            iid=int(data["number"]),
            state=state,
            web_url=data.get("html_url", ""),
            draft=bool(data.get("draft", False))
            or bool(_WIP_RE.match(data.get("title", ""))),
            labels=[label["name"] for label in data.get("labels") or []],
        )


# END OF FILE
