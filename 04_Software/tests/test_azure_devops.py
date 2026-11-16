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
@file       test_azure_devops.py
@brief      Offline Azure Services contracts at the injected CLI boundary.
@details    Covers scoping, pagination, corrupt output, signaling, replay and delivery.
"""

# IMPORTS
import json
from pathlib import Path

from adore.config import default_config, validate_config
from adore.doctor import auth_status, detect_platform_cli
from adore.forge import ForgeError, ForgeResponseError, build_forge
from adore.forge.azure_devops import AzureDevOpsForge
from adore.forge_labels import ensure_labels, project_labels
from adore.selection import ineligibility
from adore.util import CommandResult
from adore.web.repository_source import RepositorySourceError, origin_matches, parse_repository_url
import pytest

# CONSTANTS
SCOPE = dict(organization="https://dev.azure.com/contoso", project="Payments",
             area_path="Payments\\Backend")
USER = {"uniqueName": "developer@example.invalid"}
STAMP = "2026-11-01T10:00:00Z"


# LOCAL HELPERS
def work_item(iid=25, **fields):
    """@brief Build a representative REST Work Item, not a lossy CLI table."""
    return {"id": iid, "rev": 3, "fields": {
        "System.TeamProject": "Payments", "System.AreaPath": "Payments\\Backend",
        "System.WorkItemType": "Bug", "System.State": "Active", "System.Title": "Repair",
        "System.Tags": "human-owned; agent-ready; P2", "System.CreatedBy": USER,
        "System.CreatedDate": STAMP, "System.ChangedDate": STAMP,
        "System.Description": "<div>Hello &amp; welcome</div><script>hidden</script>",
        "Microsoft.VSTS.Common.AcceptanceCriteria": "<ul><li>It works</li></ul>", **fields}}


def pull(**changes):
    return {"pullRequestId": 7, "repository": {"name": "backend", "id": "repo-guid",
            "project": {"name": "Payments", "id": "project-guid"}},
            "status": "active", "isDraft": True, "sourceRefName": "refs/heads/adore/25",
            "targetRefName": "refs/heads/main",
            "reviewers": [{"id": "01234567-0123-0123-0123-012345678901"}],
            **changes}


def comment(iid=1, **changes):
    return {"id": iid, "text": "<!--adore:status-->Status", "createdBy": USER,
            "createdDate": STAMP, **changes}


class Runner:
    """@brief Validate requests while capturing ephemeral body files before removal."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, argv, **kwargs):
        body = None
        if "--in-file" in argv:
            path = Path(argv[argv.index("--in-file") + 1])
            assert path.stat().st_mode & 0o077 == 0
            body = json.loads(path.read_text(encoding="utf-8"))
        self.calls.append((argv, body))
        assert kwargs.get("timeout") in (None, 8, 60)
        assert argv[0] == "az"
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, CommandResult):
            return response
        return CommandResult(argv=argv, exit_code=0, stdout=json.dumps(response))


def forge(runner):
    return build_forge("azure_devops", "backend", runner, **SCOPE)


# PUBLIC API / TESTS
def test_scoped_pickup_normalizes_html_acceptance_and_preserves_native_priority():
    runner = Runner({"workItems": [{"id": 25}]}, work_item(
        **{"Microsoft.VSTS.Common.Priority": 1}))
    adapter = forge(runner)
    ticket, = adapter.list_ready("agent-ready")
    assert ticket.iid == 25 and ticket.state == "opened"
    assert "Hello & welcome" in ticket.description and "hidden" not in ticket.description
    assert "Acceptance criteria\n- It works" in ticket.description
    assert "informational): 1" in ticket.description
    assert ticket.labels == ["human-owned", "agent-ready", "P2"]
    assert ticket.web_url == "https://dev.azure.com/contoso/Payments/_workitems/edit/25"
    config = default_config()
    assert ineligibility(ticket, config, has_run=False) is None
    ticket.labels.append(config.labels.control.hold)
    assert ineligibility(ticket, config, has_run=False) == "held"
    wiql = runner.calls[0][1]["query"]
    assert "[System.AreaPath] = 'Payments\\Backend'" in wiql
    assert "[System.TeamProject] = 'Payments'" in wiql
    for argv, _ in runner.calls:
        assert argv[argv.index("--organization") + 1] == SCOPE["organization"]
        assert "project=Payments" in argv


@pytest.mark.parametrize("field,value", [
    ("System.TeamProject", "Other"), ("System.AreaPath", "Payments\\OtherRepo"),
    ("System.Title", None), ("System.Tags", []), ("System.WorkItemType", {}),
    ("System.State", None), ("System.Description", 7), ("System.CreatedBy", []),
    ("Microsoft.VSTS.Common.AcceptanceCriteria", []), ("System.CreatedDate", 1),
    ("Microsoft.VSTS.Common.Priority", True),
])
def test_work_item_boundary_refuses_malformed_or_out_of_scope_records(field, value):
    with pytest.raises(ForgeResponseError):
        forge(Runner(work_item(**{field: value}))).get_ticket(25)


@pytest.mark.parametrize("response", [None, [], {"error": {}}, {"id": True, "fields": {}},
                                     {"fields": {}}])
def test_invalid_records_never_become_new_tickets(response):
    with pytest.raises(ForgeError):
        forge(Runner(response)).get_ticket(25)


@pytest.mark.parametrize("result", [
    CommandResult(argv=["az"], exit_code=1, stderr="PAT-DO-NOT-LOG expired"),
    CommandResult(argv=["az"], exit_code=0, stdout="not-json PAT-DO-NOT-LOG"),
    CommandResult(argv=["az"], exit_code=0, stdout='{"id":1,"id":2}'),
    CommandResult(argv=["az"], exit_code=0, stdout="{}", timed_out=True),
    OSError("PAT-DO-NOT-LOG"),
])
def test_cli_failures_are_typed_and_value_free(result):
    with pytest.raises(ForgeError) as error:
        forge(Runner(result)).get_ticket(25)
    assert "PAT-DO-NOT-LOG" not in str(error.value)


@pytest.mark.parametrize("state,kind,expected", [("Closed", "Bug", "closed"),
    ("Done", "Task", "closed"), ("Removed", "Bug", "closed"),
    ("Active", "Epic", "closed"), ("CustomActive", "Bug", "opened")])
def test_native_state_and_type_mapping_is_explicit(state, kind, expected):
    ticket = forge(Runner(work_item(**{"System.State": state,
        "System.WorkItemType": kind}))).get_ticket(25)
    assert ticket.state == expected


def test_custom_process_names_and_false_positive_ready_query_are_postfiltered():
    runner = Runner(work_item(**{"System.State": "Released", "System.WorkItemType": "Story"}),
                    {"workItems": [{"id": 25}]}, work_item(**{"System.Tags": "not-agent-ready"}))
    adapter = AzureDevOpsForge("backend", runner, **SCOPE, work_item_types=["Story"],
                               closed_states=["Released"])
    assert adapter.get_ticket(25).state == "closed"
    assert adapter.list_ready("agent-ready") == []


def test_query_pages_use_monotonic_ids_and_never_return_partial_overflow(monkeypatch):
    monkeypatch.setattr("adore.forge.azure_devops.PAGE_SIZE", 1)
    runner = Runner({"workItems": [{"id": 25}]}, work_item(),
                    {"workItems": [{"id": 26}]}, work_item(26), {"workItems": []})
    assert [t.iid for t in forge(runner).list_ready("agent-ready")] == [25, 26]
    assert "[System.Id] > 25" in runner.calls[2][1]["query"]
    runner = Runner({"workItems": [{"id": 25}]}, work_item(), {"workItems": [{"id": 25}]})
    with pytest.raises(ForgeResponseError, match="advance"):
        forge(runner).list_ready("agent-ready")
    monkeypatch.setattr("adore.forge.azure_devops.MAX_PAGES", 1)
    with pytest.raises(ForgeResponseError, match="safety limit"):
        forge(Runner({"workItems": [{"id": 25}]}, work_item())).list_ready("agent-ready")


def test_status_comments_paginate_keep_markers_and_edit_existing_id():
    runner = Runner(work_item(), {"comments": [comment()], "continuationToken": "next"},
                    {"comments": [comment(2)]}, work_item(), {"id": 3}, work_item(), {"id": 3})
    adapter = forge(runner)
    assert [c.id for c in adapter.list_comments(25)] == [1, 2]
    assert "continuationToken=next" in runner.calls[2][0]
    assert adapter.post_comment(25, "<!--marker-->status") == 3
    # A fresh adapter is the restart boundary: no transient comment-id map.
    forge(runner).edit_comment(25, 3, "<!--marker-->new status")
    assert "commentId=3" in runner.calls[-1][0]
    assert runner.calls[-1][1] == {"text": "<!--marker-->new status"}


@pytest.mark.parametrize("payload", [{"comments": None}, {"comments": [comment(id=True)]},
    {"comments": [comment(createdBy=None)]}, {"comments": [comment(text=None)]}])
def test_comment_read_fails_closed(payload):
    with pytest.raises(ForgeError):
        forge(Runner(work_item(), payload)).list_comments(25)


def test_tag_edits_preserve_human_tags_and_use_revision_compare_and_swap():
    updated = work_item(**{"System.Tags": "human-owned; agent-ready; P2; agent-working"})
    runner = Runner(work_item(), updated, updated, work_item())
    adapter = forge(runner)
    adapter.add_labels(25, ["agent-working"])
    adapter.remove_labels(25, ["agent-working"])
    assert runner.calls[1][1][0] == {"op": "test", "path": "/rev", "value": 3}
    assert runner.calls[1][1][1]["value"] == "human-owned; agent-ready; P2; agent-working"
    assert runner.calls[-1][1][1]["value"] == "human-owned; agent-ready; P2"


def test_tag_acknowledgement_accepts_server_order_but_not_another_work_item():
    """@brief Tags are a set, while the updated resource identity must stay exact."""
    confirmed = work_item(**{"System.Tags": "agent-working; P2; human-owned; agent-ready"})
    forge(Runner(work_item(), confirmed)).add_labels(25, ["agent-working"])
    confirmed["id"] = 26
    with pytest.raises(ForgeError):
        forge(Runner(work_item(), confirmed)).add_labels(25, ["agent-working"])


def test_tag_conflicts_and_bad_names_never_overwrite_or_retry_blindly():
    runner = Runner(work_item(), CommandResult(argv=["az"], exit_code=1))
    with pytest.raises(ForgeError):
        forge(runner).add_labels(25, ["agent-working"])
    assert len(runner.calls) == 2
    with pytest.raises(ForgeError):
        forge(Runner()).add_labels(25, ["one;two"])


@pytest.mark.parametrize("status,expected", [("active", "opened"), ("completed", "merged"),
                                            ("abandoned", "closed")])
def test_pr_state_and_labels_are_not_work_item_tags(status, expected):
    adapter = forge(Runner(pull(status=status), {"value": [{"name": "agent-revise"}]}))
    pr = adapter.get_merge_request(7)
    assert pr.state == expected and pr.labels == ["agent-revise"]
    assert pr.web_url.endswith("/Payments/_git/backend/pullrequest/7")


@pytest.mark.parametrize("changes", [{"status": "unknown"}, {"isDraft": "true"},
    {"pullRequestId": False}, {"repository": {"name": "other", "project": {"name": "Payments"}}}])
def test_pr_scope_and_terminal_state_fail_closed(changes):
    with pytest.raises(ForgeError):
        forge(Runner(pull(**changes))).get_merge_request(7)


@pytest.mark.parametrize("draft", [True, False])
def test_pr_creation_never_sets_completion_merge_or_bypass_options(draft):
    runner = Runner(pull(isDraft=draft), {"value": []})
    url = forge(runner).open_merge_request("adore/25", "main", "Repair", "evidence",
        draft=draft, reviewers=["01234567-0123-0123-0123-012345678901"])
    assert url.endswith("/pullrequest/7")
    body = runner.calls[0][1]
    assert set(body) == {"sourceRefName", "targetRefName", "title", "description", "isDraft",
                         "reviewers"}
    assert body["isDraft"] is draft
    with pytest.raises(ForgeError):
        forge(Runner()).open_merge_request("x", "main", "t", "b", reviewers=["not-a-guid"])


def test_pr_threads_composite_comment_ids_survive_restart_and_inline_review():
    pr_comment = {"id": 2, "content": "<!--status-->fix this", "author": USER,
                  "publishedDate": STAMP, "commentType": "text"}
    runner = Runner({"value": [{"id": 9, "comments": [pr_comment]}]},
        {"id": 9, "comments": [pr_comment]}, {"id": 2, "content": "updated"})
    adapter = forge(runner)
    comments = adapter.list_mr_comments(7)
    comment_id = adapter.post_mr_comment(7, "<!--status-->fix this")
    assert comment_id == comments[0].id == (9 << 32) | 2
    forge(runner).edit_mr_comment(7, comment_id, "updated")
    assert "threadId=9" in runner.calls[-1][0] and "commentId=2" in runner.calls[-1][0]


def test_pr_review_label_removal_uses_pr_resource_only():
    runner = Runner({"value": [{"name": "human"}, {"name": "agent-revise"}]}, None)
    forge(runner).remove_mr_labels(7, ["agent-revise"])
    assert runner.calls[-1][0][:5] == ["az", "repos", "pr", "label", "remove"]
    assert "human" not in runner.calls[-1][0]


def test_pr_association_is_idempotent_after_replay():
    runner = Runner(work_item(), {"value": []}, [work_item()],
                    work_item(), {"value": [{"id": "25"}]})
    forge(runner).link_ticket(7, 25)
    forge(runner).link_ticket(7, 25)
    assert sum(argv[:5] == ["az", "repos", "pr", "work-item", "add"]
               for argv, _ in runner.calls) == 1


@pytest.mark.parametrize("state,expected", [("succeeded", "success"), ("failed", "failed"),
    ("error", "failed"), ("pending", "running"), ("notApplicable", "none"),
    ("invented", "unknown")])
def test_ci_is_advisory_and_never_invents_success(state, expected):
    runner = Runner({"value": [{"id": 2}]},
                    {"value": [{"context": {"genre": "pipeline", "name": "build"},
                                "updatedDate": STAMP, "state": state}]})
    assert forge(runner).pipeline_status(7) == expected
    assert forge(Runner({"value": [{"id": 2}]}, {"value": []})).pipeline_status(7) == "none"
    assert "iterationId=2" in runner.calls[-1][0]
    assert forge(Runner({})).pipeline_status(7) == "unknown"
    assert forge(Runner(CommandResult(argv=["az"], exit_code=1))).pipeline_status(7) == "unknown"


@pytest.mark.parametrize("change", [{"organization": "https://server/tfs"},
    {"organization": "https://token@dev.azure.com/org"}, {"area_path": "Payments"},
    {"area_path": "Other\\Backend"}, {"work_item_types": []}, {"closed_states": []},
    {"work_item_types": [" Bug"]}])
def test_factory_and_config_refuse_missing_or_unsafe_cloud_scope(change):
    scope = {**SCOPE, **change}
    with pytest.raises(ValueError):
        build_forge("azure_devops", "backend", Runner(), **scope)
    config = default_config()
    config.platform.kind, config.platform.repo = "azure_devops", "backend"
    for key, value in scope.items():
        setattr(config.platform, key, value)
    assert any("[platform]" in issue for issue in validate_config(config))


def test_dependency_access_and_label_helper_verify_scope_without_provisioning():
    node = {"id": 3, "path": "\\Payments\\Area\\Backend", "structureType": "area"}
    runner = Runner({"name": "backend", "project": {"name": "Payments"}},
                    node, {"workItems": []})
    config = default_config()
    report = ensure_labels(forge(runner), project_labels(config))
    assert report["mode"] == "azure_on_attachment" and report["created"] == []
    assert "agent-ready" in report["verified"]
    assert all("--http-method" not in argv or argv[argv.index("--http-method") + 1]
               in {"GET", "POST"} for argv, _ in runner.calls)
    config.platform.kind, config.platform.repo = "azure_devops", "backend"
    for key, value in SCOPE.items():
        setattr(config.platform, key, value)
    runner = Runner({"name": "backend", "project": {"name": "Payments"}},
                    node, {"workItems": []})
    assert auth_status("azure_devops", runner, platform=config.platform).authenticated
    assert not auth_status("azure_devops", Runner(), platform=None).authenticated
    runner = Runner(CommandResult(argv=["az"], exit_code=0, stdout='{"azure-cli":"2.80"}'),
                    {"name": "azure-devops"})
    assert detect_platform_cli("azure_devops", runner).present


def test_azure_repository_urls_keep_organization_project_identity():
    value = parse_repository_url("https://dev.azure.com/contoso/Payments/_git/backend")
    assert value.organization == SCOPE["organization"] and value.project == "Payments"
    assert value.repo == "backend"
    ssh = parse_repository_url("git@ssh.dev.azure.com:v3/contoso/Payments/backend")
    assert (ssh.organization, ssh.project, ssh.repo) == (
        value.organization, value.project, value.repo)
    with pytest.raises(RepositorySourceError):
        parse_repository_url("https://ssh.dev.azure.com/v3/contoso/Payments/backend")
    assert not origin_matches(value.url, "https://dev.azure.com/other/Payments/_git/backend")
    assert not origin_matches(value.url, "https://dev.azure.com/contoso/Other/_git/backend")
    with pytest.raises(RepositorySourceError):
        parse_repository_url("http://dev.azure.com/contoso/Payments/_git/backend")


def test_browse_and_pr_branch_lookup_are_bounded_and_postfiltered():
    """@brief Public browsing/search honor bounds and reject malformed collections."""
    assert forge(Runner({"workItems": [{"id": 25}]}, work_item())).list_open(2)[0].iid == 25
    with pytest.raises(ForgeError):
        forge(Runner()).list_open(0)
    assert forge(Runner({"value": []})).get_merge_request("adore/25") is None
    runner = Runner({"value": [pull()]}, {"value": []})
    assert forge(runner).get_merge_request("adore/25").iid == 7
    with pytest.raises(ForgeError):
        forge(Runner({"value": [pull(), pull()]})).get_merge_request("adore/25")
    with pytest.raises(ForgeError):
        forge(Runner(pull(pullRequestId=8))).get_merge_request(7)
    with pytest.raises(ForgeError):
        forge(Runner(pull(status=[]))).get_merge_request(7)


def test_comment_continuation_headers_and_cli_preview_version_are_supported():
    """@brief az invoke's header token is not confused with the REST body token.
    @note The extension accepts numeric-preview, not numeric-preview.revision.
    """
    runner = Runner(work_item(), {"comments": [comment()], "continuation_token": "next"},
                    {"comments": [comment(2)], "continuation_token": None})
    assert len(forge(runner).list_comments(25)) == 2
    assert runner.calls[1][0][runner.calls[1][0].index("--api-version") + 1] == "7.1-preview"
    assert "continuationToken=next" in runner.calls[2][0]
    with pytest.raises(ForgeError, match="disagree"):
        forge(Runner(work_item(), {"comments": [], "continuationToken": "a",
                                  "continuation_token": "b"})).list_comments(25)
    with pytest.raises(ForgeError, match="advance"):
        forge(Runner(work_item(), {"comments": [], "continuationToken": "a"},
                     {"comments": [], "continuationToken": "a"})).list_comments(25)
    with pytest.raises(ForgeError, match="unsupported continuation"):
        forge(Runner({"value": [], "continuation_token": "next"})).list_mr_comments(7)


@pytest.mark.parametrize("bad", [{}, {"id": 9, "comments": None},
    {"id": 9, "comments": [{"id": 0}]},
    {"id": 9, "comments": [{"id": 2, "content": []}]}])
def test_pr_thread_creation_refuses_corrupt_acknowledgement(bad):
    """@brief Corrupt thread responses cannot establish durable comment identity."""
    # The returned text is not required for identity, but IDs/list shape are.
    if bad == {"id": 9, "comments": [{"id": 2, "content": []}]}:
        with pytest.raises(ForgeError):
            forge(Runner({"value": [bad]})).list_mr_comments(7)
    else:
        with pytest.raises(ForgeError):
            forge(Runner(bad)).post_mr_comment(7, "status")


def test_description_update_acknowledges_only_the_approved_body():
    """@brief Existing PR evidence updates touch no review or completion settings."""
    runner = Runner({"pullRequestId": 7, "description": "current evidence"})
    forge(runner).update_merge_request_body(7, "current evidence")
    assert runner.calls[0][1] == {"description": "current evidence"}
    with pytest.raises(ForgeError):
        forge(Runner({"pullRequestId": 8, "description": "body"})).update_merge_request_body(
            7, "body")


def test_missing_area_and_failed_association_are_not_reported_as_success():
    """@brief Prerequisites and publication fail closed at scope/write boundaries."""
    runner = Runner({"name": "backend", "project": {"name": "Payments"}},
                    {"id": 3, "path": "wrong", "structureType": "area"})
    with pytest.raises(ForgeError):
        ensure_labels(forge(runner), [])
    with pytest.raises(ForgeError):
        forge(Runner(work_item(), {"value": []}, [])).link_ticket(7, 25)
    with pytest.raises(ForgeError):
        forge(Runner({"value": [{"name": "agent-revise"}]},
                     CommandResult(argv=["az"], exit_code=1))).remove_mr_labels(7, ["agent-revise"])


# END OF FILE
