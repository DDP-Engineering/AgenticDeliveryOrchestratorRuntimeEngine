#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file       azure_devops.py
@brief      Azure DevOps Services adapter over az and the azure-devops extension.
@details    Every request explicitly binds organization and project. Boards access
            is restricted to an exact Area Path; Git requests bind repository too.
            Writes never complete PRs, enable auto-complete or bypass policies.
"""

from __future__ import annotations

# IMPORTS
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote

from adore import azure_cli
from adore.forge.base import Comment, Forge, ForgeError, ForgeResponseError, MergeRequest, Ticket
from adore.util import CommandRunner, run_command, strict_json_loads

# CONSTANTS
PAGE_SIZE = 200
MAX_PAGES = 50
DEFAULT_TYPES = ("Bug", "Task", "Issue", "User Story", "Product Backlog Item", "Requirement")
DEFAULT_CLOSED_STATES = ("Closed", "Done", "Removed")

# LOCAL HELPERS


def validate_azure_scope(organization: str, project: str, repo: str, area_path: str,
                         work_item_types: list[str], closed_states: list[str]) -> None:
    """@brief Validate cloud-only scope before any CLI request.
    @exception ValueError On unsafe, incomplete or on-premises scope.
    """
    if (not isinstance(organization, str) or not re.fullmatch(
            r"https://dev\.azure\.com/[A-Za-z0-9][A-Za-z0-9-]{0,49}", organization)):
        raise ValueError("organization must be https://dev.azure.com/ORGANIZATION (Services only)")
    for name, value in (("project", project), ("repo", repo), ("area_path", area_path)):
        if (not isinstance(value, str) or not value.strip() or value != value.strip()
                or len(value) > 256 or any(ord(c) < 32 for c in value)
                or value.startswith("-") or any(c in value for c in "/?#%")):
            raise ValueError(f"{name} must be an explicit Azure resource name")
    if ("\\" in repo or "\\" in project or not area_path.startswith(project + "\\")
            or any(part in {"", ".", ".."} for part in area_path.split("\\"))):
        raise ValueError("area_path must name a repository-owned area below PROJECT\\")
    for name, values in (("work_item_types", work_item_types), ("closed_states", closed_states)):
        if (not isinstance(values, list) or not 1 <= len(values) <= 32
                or any(not isinstance(v, str) or not v.strip() or v != v.strip() or len(v) > 128
                       or any(ord(c) < 32 for c in v) for v in values)
                or len(set(values)) != len(values)):
            raise ValueError(f"{name} must be a nonempty unique list of process names")


class _HtmlText(HTMLParser):
    """@brief Normalize Boards HTML without executing or retaining active content."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"} and not self.hidden:
            self.parts.append("\n- " if tag == "li" else "\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "li", "tr"} and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ForgeResponseError("Azure text field is malformed")
    parser = _HtmlText()
    parser.feed(value)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def _id(value: object) -> int:
    if type(value) is not int or value < 1:
        raise ForgeResponseError("Azure resource id is malformed")
    return value


def _dict(value: object) -> dict:
    if not isinstance(value, dict):
        raise ForgeResponseError("Azure object is malformed")
    return value


def _string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ForgeResponseError("Azure required text field is missing")
    return value


def _items(data: dict, key: str = "value") -> list[dict]:
    values = data.get(key)
    if not isinstance(values, list) or not all(isinstance(v, dict) for v in values):
        raise ForgeResponseError("Azure collection is malformed")
    return values


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# PUBLIC API
class AzureDevOpsForge(Forge):
    """@brief Scoped Azure Boards and Azure Repos implementation of Forge."""

    def __init__(self, repo: str, runner: CommandRunner = run_command, *, organization: str,
                 project: str, area_path: str, work_item_types: list[str] | None = None,
                 closed_states: list[str] | None = None):
        """@brief Bind explicit cloud, project, repository and Boards scope.
        @param[in] repo Azure repository name (not a URL or GUID).
        @param[in] runner Injectable offline command boundary.
        @param[in] organization Canonical Services organization URL.
        @param[in] project Exact Azure project name.
        @param[in] area_path Exact repository-owned child area.
        @param[in] work_item_types Allowed native process type names.
        @param[in] closed_states Native terminal-state names.
        @exception ValueError On invalid or incomplete scope.
        """
        self.work_item_types = list(DEFAULT_TYPES) if work_item_types is None else work_item_types
        self.closed_states = (list(DEFAULT_CLOSED_STATES)
                              if closed_states is None else closed_states)
        validate_azure_scope(organization, project, repo, area_path,
                             self.work_item_types, self.closed_states)
        self.repo, self.runner = repo, runner
        self.organization, self.project, self.area_path = organization, project, area_path
        self.base_url = f"{organization}/{quote(project, safe='')}"

    def _api(self, area: str, resource: str, *, method: str = "GET", route: dict | None = None,
             query: dict | None = None, body: object = None, version: str = "7.1",
             patch: bool = False, allow_continuation: bool = False) -> dict:
        """@brief Invoke an exact REST location with bounded, strict JSON validation.
        @details Payload files are private and ephemeral. Errors deliberately omit
                 CLI streams/argv, which may echo credentials or human content.
        @exception ForgeError On command, authentication, permission or API failure.
        """
        routes = {"project": self.project, **(route or {})}
        if area == "git":
            routes["repositoryId"] = self.repo
        # az devops invoke cannot select a location ID, and its name resolver
        # ignores route parameters. Use the extension SDK in Azure CLI's own
        # runtime, with fixed Microsoft IDs, preserving its authentication path.
        spec = {"organization": self.organization, "area": area, "resource": resource,
                "route": routes, "query": query or {}, "body": body, "method": method,
                "version": version,
                "media_type": "application/json-patch+json" if patch else "application/json"}
        try:
            with tempfile.TemporaryDirectory(prefix="adore-azure-") as temp:
                path = Path(temp) / "request.json"
                path.write_text(json.dumps(spec), encoding="utf-8")
                path.chmod(0o600)
                argv = [sys.executable, "-I", "-B", str(Path(azure_cli.__file__).absolute()),
                        "request", str(path)]
                result = self.runner(argv, timeout=60)
            if not result.ok or result.timed_out:
                raise ForgeError("Azure request failed; check az + azure-devops, service-account "
                                 "sign-in/PAT expiry, project/area and Code/Work Items permissions")
            if len(result.stdout) > 16 * 1024 * 1024:
                raise ForgeResponseError("Azure response exceeds the safety limit")
            data = strict_json_loads(result.stdout)
        except (OSError, TimeoutError) as exc:
            raise ForgeError(
                "Azure CLI unavailable or timed out; check host prerequisites") from exc
        except (ValueError, TypeError) as exc:
            raise ForgeResponseError("Azure returned invalid JSON") from exc
        data = _dict(data)
        if "error" in data or "errorCode" in data or "typeKey" in data:
            raise ForgeError("Azure API refused the request; check resource scope and permissions")
        # The bridge preserves the response-header token under this snake-case key.
        # Never accept a truncated resource that does not expose a paging contract.
        token = data.get("continuation_token")
        if token not in (None, "") and not allow_continuation:
            raise ForgeResponseError("Azure resource returned an unsupported continuation page")
        return data

    def _wi(self, iid: int) -> dict:
        data = self._api("wit", "workItems", route={"id": _id(iid)})
        self._ticket(data)
        if data["id"] != iid:
            raise ForgeResponseError("Azure returned a different Work Item")
        return data

    def _ticket(self, data: dict) -> Ticket:
        """@brief Normalize a strictly scoped Work Item, including HTML acceptance text."""
        fields = _dict(data.get("fields"))
        if (fields.get("System.TeamProject") != self.project
                or fields.get("System.AreaPath") != self.area_path):
            raise ForgeResponseError("Azure Work Item is outside the configured project/Area Path")
        kind = _string(fields.get("System.WorkItemType"))
        state = _string(fields.get("System.State"))
        tags = fields.get("System.Tags", "")
        if not isinstance(tags, str):
            raise ForgeResponseError("Azure Work Item tags are malformed")
        description = _text(fields.get("System.Description", ""))
        acceptance = _text(fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", ""))
        if acceptance:
            description += "\n\nAcceptance criteria\n" + acceptance
        description += f"\n\nAzure Work Item type: {kind}\nAzure state: {state}"
        if "Microsoft.VSTS.Common.Priority" in fields:
            priority = fields["Microsoft.VSTS.Common.Priority"]
            if type(priority) is not int:
                raise ForgeResponseError("Azure native priority is malformed")
            description += f"\nAzure native priority (informational): {priority}"
        author = fields.get("System.CreatedBy", {})
        if isinstance(author, dict):
            author = author.get("uniqueName", author.get("displayName", ""))
        if not isinstance(author, str):
            raise ForgeResponseError("Azure author is malformed")
        iid = _id(data.get("id"))
        dates = [fields.get(k, "") for k in ("System.CreatedDate", "System.ChangedDate")]
        if not all(isinstance(v, str) for v in dates):
            raise ForgeResponseError("Azure dates are malformed")
        return Ticket(iid, _string(fields.get("System.Title")), description,
                      [tag.strip() for tag in tags.split(";") if tag.strip()], author,
                      "closed" if state in self.closed_states or kind not in self.work_item_types
                      else "opened", f"{self.base_url}/_workitems/edit/{iid}", *dates)

    def _query(self, extra: str = "", limit: int | None = None) -> list[Ticket]:
        """@brief Read ID-keyset pages without partial results at the safety bound."""
        found: list[Ticket] = []
        last = 0
        for _ in range(MAX_PAGES):
            size = min(PAGE_SIZE, limit - len(found)) if limit else PAGE_SIZE
            wiql = ("SELECT [System.Id] FROM WorkItems WHERE "
                    f"[System.TeamProject] = {_literal(self.project)} AND "
                    f"[System.AreaPath] = {_literal(self.area_path)} AND "
                    "[System.WorkItemType] IN ("
                    f"{','.join(map(_literal, self.work_item_types))}) AND "
                    f"[System.State] NOT IN ({','.join(map(_literal, self.closed_states))}) AND "
                    f"[System.Id] > {last} {extra} ORDER BY [System.Id]")
            data = self._api("wit", "wiql", method="POST", query={"$top": size},
                             body={"query": wiql})
            rows = _items(data, "workItems")
            if len(rows) > size:
                raise ForgeResponseError("Azure query exceeded its requested bound")
            for row in rows:
                iid = _id(row.get("id"))
                if iid <= last:
                    raise ForgeResponseError("Azure query pagination did not advance")
                last = iid
                ticket = self._ticket(self._wi(iid))
                if ticket.state == "opened":
                    found.append(ticket)
            if len(rows) < size or limit and len(found) >= limit:
                return found
        raise ForgeResponseError("Azure Work Item pagination exceeded the safety limit")

    def list_ready(self, ready_label: str) -> list[Ticket]:
        """@brief List opted-in Work Items; shared selection enforces hold/exclude/readiness.
        @param[in] ready_label Human opt-in tag.
        @return Scoped, open tickets carrying the exact tag.
        @exception ForgeError On CLI, API or response-contract failure.
        """
        return [t for t in self._query(f"AND [System.Tags] CONTAINS {_literal(ready_label)}")
                if ready_label in t.labels]

    def list_open(self, limit: int) -> list[Ticket]:
        """@brief Browse at most limit open scoped Work Items.
        @param[in] limit Positive maximum number of tickets.
        @return Normalized tickets; no partial results on failure.
        """
        if type(limit) is not int or limit < 1:
            raise ForgeError("Azure browse limit must be positive")
        return self._query(limit=limit)

    def get_ticket(self, iid: int) -> Ticket | None:
        """@brief Read a scoped Work Item; inaccessible/deleted items fail explicitly.
        @param[in] iid Organization-wide Work Item ID.
        @return The scoped ticket.
        @exception ForgeError If access/deletion cannot be distinguished safely.
        """
        return self._ticket(self._wi(iid))

    def _comment(self, item: dict, *, comment_id: int | None = None, pr: bool = False) -> Comment:
        author = _dict(item.get("author" if pr else "createdBy"))
        date = _string(item.get("publishedDate" if pr else "createdDate"))
        body = item.get("content" if pr else "text")
        if not isinstance(body, str):
            raise ForgeResponseError("Azure comment text is malformed")
        return Comment(comment_id or _id(item.get("id")), body,
                       _string(author.get("uniqueName", author.get("displayName"))), date,
                       pr and item.get("commentType") == "system")

    def list_comments(self, iid: int) -> list[Comment]:
        """@brief Read every Boards comment page, oldest first, retaining hidden markers.
        @param[in] iid Scoped Work Item ID.
        @return Comments ordered by creation date and ID.
        @exception ForgeError On malformed/incomplete pagination or CLI failure.
        """
        self._wi(iid)
        comments = []
        token = None
        seen = set()
        for _ in range(MAX_PAGES):
            query = {"$top": PAGE_SIZE, "order": "asc"}
            if token is not None:
                query["continuationToken"] = token
            data = self._api("wit", "comments", route={"workItemId": iid}, query=query,
                             version="7.1-preview.4", allow_continuation=True)
            comments.extend(self._comment(item) for item in _items(data, "comments"))
            body_token, header_token = data.get("continuationToken"), data.get("continuation_token")
            if (body_token not in (None, "") and header_token not in (None, "")
                    and str(body_token) != str(header_token)):
                raise ForgeResponseError("Azure comment continuation tokens disagree")
            token = body_token if body_token not in (None, "") else header_token
            if token is None or token == "":
                ids = [c.id for c in comments]
                if len(set(ids)) != len(ids):
                    raise ForgeResponseError("Azure returned duplicate comments")
                return sorted(comments, key=lambda c: (c.created_at, c.id))
            if type(token) not in (str, int) or str(token) in seen:
                raise ForgeResponseError("Azure comment pagination did not advance")
            seen.add(str(token))
        raise ForgeResponseError("Azure comments exceeded the safety limit")

    def post_comment(self, iid: int, body: str) -> int:
        """@brief Post a Markdown Boards status/clarification/approval comment.
        @param[in] iid Scoped Work Item ID.
        @param[in] body Literal marker-bearing Markdown.
        @return Positive created comment ID for durable replay.
        """
        self._wi(iid)
        data = self._api("wit", "comments", method="POST", route={"workItemId": iid},
                         query={"format": "markdown"}, body={"text": body},
                         version="7.1-preview.4")
        return _id(data.get("id"))

    def edit_comment(self, iid: int, comment_id: int, body: str) -> None:
        """@brief Update the exact persisted Boards comment without adding a duplicate.
        @param[in] iid Scoped Work Item ID.
        @param[in] comment_id Durable native comment ID.
        @param[in] body Replacement marker-bearing Markdown.
        @exception ForgeError On unconfirmed acknowledgement.
        """
        self._wi(iid)
        data = self._api("wit", "comments", method="PATCH",
                         route={"workItemId": iid, "commentId": _id(comment_id)},
                         body={"text": body}, version="7.1-preview.4")
        if _id(data.get("id")) != comment_id:
            raise ForgeResponseError("Azure updated a different comment")

    def _tags(self, iid: int, labels: list[str], remove: bool = False) -> None:
        """@brief Preserve human tags with optimistic Work Item revision protection."""
        if not labels:
            return
        if any(not isinstance(v, str) or not v.strip() or ";" in v for v in labels):
            raise ForgeError("Azure tag names must be nonempty and cannot contain semicolons")
        data = self._wi(iid)
        current = self._ticket(data).labels
        updated = ([v for v in current if v not in labels] if remove else
                   current + [v for v in labels if v not in current])
        if current == updated:
            return
        result = self._api("wit", "workItems", method="PATCH", route={"id": iid}, patch=True,
                           body=[{"op": "test", "path": "/rev", "value": _id(data.get("rev"))},
                                 {"op": "add", "path": "/fields/System.Tags",
                                  "value": "; ".join(updated)}])
        confirmed = self._ticket(result)
        if confirmed.iid != iid or set(confirmed.labels) != set(updated):
            raise ForgeResponseError("Azure did not acknowledge the requested tag update")

    def add_labels(self, iid: int, labels: list[str]) -> None:
        """@brief Add Work Item tags with revision protection; preserve human tags.
        @param[in] iid Scoped Work Item ID.
        @param[in] labels Exact tag names to attach.
        """
        self._tags(iid, labels)

    def remove_labels(self, iid: int, labels: list[str]) -> None:
        """@brief Remove only named Work Item tags with revision protection.
        @param[in] iid Scoped Work Item ID.
        @param[in] labels Exact tag names to remove.
        """
        self._tags(iid, labels, remove=True)

    def _pull(self, data: dict) -> MergeRequest:
        repo = _dict(data.get("repository"))
        project = _dict(repo.get("project"))
        if repo.get("name") != self.repo or project.get("name") != self.project:
            raise ForgeResponseError("Azure PR belongs to another project/repository")
        states = {"active": "opened", "completed": "merged", "abandoned": "closed"}
        if (not isinstance(data.get("status"), str) or data["status"] not in states
                or type(data.get("isDraft")) is not bool):
            raise ForgeResponseError("Azure PR state/draft flag is malformed")
        iid = _id(data.get("pullRequestId"))
        labels = self._api("git", "pullRequestLabels", route={"pullRequestId": iid})
        return MergeRequest(iid, states[data["status"]],
                            f"{self.base_url}/_git/{quote(self.repo, safe='')}/pullrequest/{iid}",
                            data["isDraft"], [_string(v.get("name")) for v in _items(labels)])

    def get_merge_request(self, ref: int | str) -> MergeRequest | None:
        """@brief Find an active source branch or read a stored PR's terminal state.
        @param[in] ref Stored PR ID or short source branch.
        @return Scoped PR, or None when a branch has no active PR.
        @exception ForgeError On denied/malformed/ambiguous resource data.
        """
        if type(ref) is int:
            data = self._api("git", "pullRequests", route={"pullRequestId": _id(ref)})
            if _id(data.get("pullRequestId")) != ref:
                raise ForgeResponseError("Azure returned a different PR")
            return self._pull(data)
        for page in range(MAX_PAGES):
            rows = _items(self._api("git", "pullRequests", query={
                "searchCriteria.status": "active",
                "searchCriteria.sourceRefName": f"refs/heads/{ref}",
                "$top": PAGE_SIZE, "$skip": page * PAGE_SIZE}))
            matches = [row for row in rows if row.get("sourceRefName") == f"refs/heads/{ref}"]
            if len(matches) > 1:
                raise ForgeResponseError("Azure returned ambiguous active PRs for the branch")
            if matches:
                return self._pull(matches[0])
            if len(rows) < PAGE_SIZE:
                return None
        raise ForgeResponseError("Azure PR pagination exceeded the safety limit")

    def open_merge_request(self, source: str, target: str, title: str, body: str, *,
                           draft: bool = True, reviewers: list[str] | None = None,
                           remove_source_branch: bool = True, cwd: str | None = None) -> str:
        """@brief Create a draft/ready PR, with explicit reviewers; never merge.
        @details Reviewers are Azure identity GUIDs. Branch cleanup is conductor-owned.
        @param[in] source Short source branch.
        @param[in] target Short integration branch.
        @param[in] title Literal PR title.
        @param[in] body Approved candidate evidence.
        @param[in] draft Requested draft state.
        @param[in] reviewers Optional Azure identity GUIDs.
        @param[in] remove_source_branch Conductor cleanup setting; no completion option is sent.
        @param[in] cwd Unused: API calls never infer a Git remote.
        @return Validated PR web URL.
        @exception ForgeError On unconfirmed scope, reviewers or publication settings.
        """
        if any(not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", v)
               for v in reviewers or []):
            raise ForgeError("Azure reviewers must be identity GUIDs")
        data = self._api("git", "pullRequests", method="POST", body={
            "sourceRefName": f"refs/heads/{source}", "targetRefName": f"refs/heads/{target}",
            "title": title, "description": body, "isDraft": draft,
            "reviewers": [{"id": v} for v in reviewers or []]})
        if (data.get("sourceRefName") != f"refs/heads/{source}"
                or data.get("targetRefName") != f"refs/heads/{target}"
                or data.get("isDraft") is not draft):
            raise ForgeResponseError("Azure did not acknowledge the requested PR settings")
        actual_reviewers = {_string(v.get("id")).casefold()
                            for v in _items(data, "reviewers")}
        if not {v.casefold() for v in reviewers or []} <= actual_reviewers:
            raise ForgeResponseError("Azure did not acknowledge the requested reviewers")
        return self._pull(data).web_url

    def link_ticket(self, mr_iid: int, ticket_iid: int) -> None:
        """@brief Idempotently associate the source Work Item with the PR on replay.
        @param[in] mr_iid Repository-scoped PR ID.
        @param[in] ticket_iid Scoped Work Item ID.
        @exception ForgeError On invalid references or unconfirmed write.
        """
        self._wi(ticket_iid)
        links = _items(self._api("git", "pullRequestWorkItems", route={"pullRequestId": mr_iid}))
        ids = []
        for item in links:
            value = item.get("id")
            if not isinstance(value, str) or not value.isdecimal():
                raise ForgeResponseError("Azure PR Work Item link is malformed")
            ids.append(int(value))
        if ticket_iid in ids:
            return
        # The dedicated command creates the ArtifactLink on the Work Item.
        argv = ["az", "repos", "pr", "work-item", "add", "--id", str(mr_iid), "--work-items",
                str(ticket_iid), "--organization", self.organization, "--detect", "false",
                "--output", "json", "--only-show-errors"]
        try:
            result = self.runner(argv, timeout=60)
            data = strict_json_loads(result.stdout) if result.ok and not result.timed_out else None
            if not isinstance(data, list) or not any(
                isinstance(v, dict) and str(v.get("id")) == str(ticket_iid) for v in data
            ):
                raise ForgeError("Azure could not confirm the Work Item/PR association")
        except (OSError, TimeoutError, ValueError) as exc:
            raise ForgeError("Azure Work Item association failed") from exc

    def update_merge_request_body(self, mr_iid: int, body: str) -> None:
        """@brief Refresh approved evidence without changing PR settings.
        @param[in] mr_iid Repository-scoped PR ID.
        @param[in] body Current approved candidate evidence.
        @exception ForgeError On failed or mismatched acknowledgement.
        """
        data = self._api("git", "pullRequests", method="PATCH",
                         route={"pullRequestId": mr_iid}, body={"description": body})
        if _id(data.get("pullRequestId")) != mr_iid or data.get("description") != body:
            raise ForgeResponseError("Azure did not acknowledge the PR description update")

    def list_mr_comments(self, mr_iid: int) -> list[Comment]:
        """@brief Read all review threads including inline comments, with stable composite IDs.
        @param[in] mr_iid Repository-scoped PR ID.
        @return Nondeleted comments, oldest first; system notes remain flagged.
        """
        threads = _items(self._api("git", "pullRequestThreads", route={"pullRequestId": mr_iid}))
        comments = []
        for thread in threads:
            tid = _id(thread.get("id"))
            for item in _items(thread, "comments"):
                cid = _id(item.get("id"))
                if cid >= 2**32 or tid >= 2**31:
                    raise ForgeResponseError("Azure thread/comment id exceeds the supported range")
                if item.get("isDeleted") is True:
                    continue
                comments.append(self._comment(item, comment_id=(tid << 32) | cid, pr=True))
        if len({c.id for c in comments}) != len(comments):
            raise ForgeResponseError("Azure returned duplicate PR comments")
        return sorted(comments, key=lambda c: (c.created_at, c.id))

    def post_mr_comment(self, mr_iid: int, body: str) -> int:
        """@brief Create one PR status thread; encode thread and comment IDs durably.
        @param[in] mr_iid Repository-scoped PR ID.
        @param[in] body Literal marker-bearing status text.
        @return Composite thread/comment ID, independent of process memory.
        """
        data = self._api("git", "pullRequestThreads", method="POST",
                         route={"pullRequestId": mr_iid}, body={"status": "active", "comments": [
                             {"parentCommentId": 0, "content": body, "commentType": "text"}]})
        rows = _items(data, "comments")
        if len(rows) != 1:
            raise ForgeResponseError("Azure did not return one created PR comment")
        tid, cid = _id(data.get("id")), _id(rows[0].get("id"))
        if cid >= 2**32 or tid >= 2**31:
            raise ForgeResponseError("Azure thread/comment id exceeds the supported range")
        return (tid << 32) | cid

    def edit_mr_comment(self, mr_iid: int, comment_id: int, body: str) -> None:
        """@brief Edit the exact thread/comment recorded before restart.
        @param[in] mr_iid Repository-scoped PR ID.
        @param[in] comment_id Composite durable thread/comment ID.
        @param[in] body Replacement marker-bearing text.
        """
        tid, cid = divmod(_id(comment_id), 2**32)
        _id(tid)
        _id(cid)
        data = self._api("git", "pullRequestThreadComments", method="PATCH",
                         route={"pullRequestId": mr_iid, "threadId": tid, "commentId": cid},
                         body={"content": body})
        if _id(data.get("id")) != cid or data.get("content") != body:
            raise ForgeResponseError("Azure did not acknowledge the PR comment edit")

    def remove_mr_labels(self, mr_iid: int, labels: list[str]) -> None:
        """@brief Clear PR revise labels, never Work Item tags.
        @param[in] mr_iid Repository-scoped PR ID.
        @param[in] labels Exact PR label names to remove.
        @exception ForgeError On failed label removal.
        """
        rows = _items(self._api("git", "pullRequestLabels", route={"pullRequestId": mr_iid}))
        for item in rows:
            if _string(item.get("name")) in labels:
                # DELETE returns JSON null; the CLI's dedicated command validates HTTP status.
                argv = ["az", "repos", "pr", "label", "remove", "--id", str(mr_iid),
                        "--name", item["name"], "--organization", self.organization,
                        "--detect", "false", "--output", "json", "--only-show-errors"]
                try:
                    result = self.runner(argv, timeout=60)
                except (OSError, TimeoutError) as exc:
                    raise ForgeError("Azure PR label removal failed") from exc
                if not result.ok or result.timed_out:
                    raise ForgeError("Azure PR label removal failed; check Code permissions")

    def pipeline_status(self, mr_iid: int) -> str:
        """@brief Report advisory PR statuses; unreadable/unsupported CI is unknown.
        @param[in] mr_iid Repository-scoped PR ID.
        @return Common pipeline vocabulary; this method never raises.
        """
        try:
            iterations = _items(self._api("git", "pullRequestIterations",
                                          route={"pullRequestId": mr_iid}))
            if not iterations:
                return "unknown"
            iteration = max(_id(v.get("id")) for v in iterations)
            rows = _items(self._api("git", "pullRequestIterationStatuses",
                                   route={"pullRequestId": mr_iid, "iterationId": iteration}))
            if not rows:
                return "none"
            latest = {}
            for row in rows:
                context = _dict(row.get("context"))
                genre = context.get("genre", "")
                if not isinstance(genre, str):
                    return "unknown"
                key = (genre, _string(context.get("name")))
                stamp = _string(row.get("updatedDate"))
                if key not in latest or stamp > latest[key][0]:
                    latest[key] = (stamp, row.get("state"))
            states = [v[1] for v in latest.values()]
            if any(s not in {"succeeded", "failed", "error", "pending", "notApplicable"}
                   for s in states):
                return "unknown"
            if any(s in {"failed", "error"} for s in states):
                return "failed"
            if "pending" in states:
                return "running"
            return "success" if "succeeded" in states else "none"
        except (ForgeError, TypeError, ValueError):
            return "unknown"

    def list_labels(self) -> list[str]:
        """@brief Azure has no repository label catalog to provision."""
        return []

    def create_label(self, name: str, color: str, description: str) -> None:
        """@brief Refuse catalog creation: tags and PR labels are attached on demand."""
        raise ForgeError("Azure tags/PR labels are created on attachment, not in a label catalog")

    def verify_access(self) -> None:
        """@brief Read the exact repository and Boards scope without writing resources."""
        data = self._api("git", "repositories", route={"repositoryId": self.repo})
        if data.get("name") != self.repo or _dict(data.get("project")).get("name") != self.project:
            raise ForgeResponseError("Azure repository scope does not match configuration")
        area = self.area_path[len(self.project) + 1:]
        node = self._api("wit", "classificationNodes", route={
            "structureGroup": "Areas", "path": area.replace("\\", "/")})
        expected = f"\\{self.project}\\Area\\{area}"
        if node.get("path") != expected or node.get("structureType") != "area":
            raise ForgeResponseError("Azure Area Path does not match configuration")
        _id(node.get("id"))
        self._query(limit=1)


# END OF FILE
