"""Forge adapters (GitLab, GitHub, Gitea, Azure DevOps Services) behind one interface."""

from __future__ import annotations

from adore.forge.azure_devops import AzureDevOpsForge
from adore.forge.base import Comment, Forge, ForgeError, ForgeResponseError, MergeRequest, Ticket
from adore.forge.gitea import GiteaForge
from adore.forge.github import GitHubForge
from adore.forge.gitlab import GitLabForge
from adore.util import CommandRunner, run_command

__all__ = [
    "AzureDevOpsForge",
    "Comment",
    "Forge",
    "ForgeError",
    "ForgeResponseError",
    "GiteaForge",
    "GitHubForge",
    "GitLabForge",
    "MergeRequest",
    "Ticket",
    "build_forge",
]


def build_forge(
    kind: str, repo: str, runner: CommandRunner = run_command, *, login: str = "",
    organization: str = "", project: str = "", area_path: str = "",
    work_item_types: list[str] | None = None, closed_states: list[str] | None = None,
) -> Forge:
    """
    Construct the configured Git-platform adapter.
    kind: Platform kind ("gitlab" | "github" | "gitea" | "azure_devops").
    repo: Repository path/slug for the platform CLI.
    runner: Command runner (injectable for tests).
    login: tea login name ([platform] login); gitea only.
    Returns: A concrete Forge.
    Raises ValueError: When the kind is unknown, or login is set for a
                kind that has no login concept.
    """
    if login and kind != "gitea":
        raise ValueError(f"platform login is only supported for gitea, not {kind!r}")
    if kind == "azure_devops":
        return AzureDevOpsForge(repo, runner, organization=organization, project=project,
                                area_path=area_path, work_item_types=work_item_types,
                                closed_states=closed_states)
    if kind == "gitlab":
        return GitLabForge(repo, runner)
    if kind == "github":
        return GitHubForge(repo, runner)
    if kind == "gitea":
        return GiteaForge(repo, runner, login=login)
    raise ValueError(f"unsupported platform kind: {kind}")
