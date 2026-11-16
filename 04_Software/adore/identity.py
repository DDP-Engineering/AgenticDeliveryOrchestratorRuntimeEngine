"""Marker-based agent identity and derived naming (design doc 5c/5d)."""

from __future__ import annotations

from dataclasses import dataclass
import re

from adore.branding import PRODUCT_ACRONYM, PRODUCT_SLUG

_TOKEN_RE = re.compile(r"([A-Za-z0-9_-]+)=(\S+)")


@dataclass(frozen=True)
class AgentIdentity:
    """
    The configured bot identity plus every name derived from it.
    Renaming the bot is a single config change; all derived
             identifiers (5c) flow from name/slug through this class.
    """

    name: str = PRODUCT_ACRONYM
    slug: str = PRODUCT_SLUG

    @property
    def tag(self) -> str:
        """
        Visible comment tag, for example "[ADORE]".
        Returns: The bracketed display tag.
        """
        return f"[{self.name}]"

    @property
    def store_root(self) -> str:
        """
        Default local state directory name (".adore").
        Returns: The dot-prefixed store root.
        """
        return f".{self.slug}"

    @property
    def questions_file(self) -> str:
        """
        Clarification questions filename ("ADORE_QUESTIONS.md").
        Returns: The uppercase slug questions filename.
        """
        return f"{self.slug.upper()}_QUESTIONS.md"

    def branch(self, run_id: str) -> str:
        """
        Run branch name ("adore/<run-id>").
        run_id: Stable run identifier.
        Returns: The branch name.
        """
        return f"{self.slug}/{run_id}"

    def container_name(self, run_id: str) -> str:
        """
        Executor container name ("adore-run-<run-id>").
        run_id: Stable run identifier.
        Returns: The container name.
        """
        return f"{self.slug}-run-{run_id}"

    def make_marker(self, run_id: str, kind: str, **extra: str) -> str:
        """
        Build the hidden machine marker line for a comment.
        Rendered invisibly on GitLab and GitHub, for example:
                    `<!-- adore:run=gitlab-x-14 kind=status state=working -->`.
        run_id: Stable run identifier.
        kind: Comment kind (status | question | delivery |
                        escalation).
        extra: Additional key=value fields (state, stage, ...).
        Returns: The marker line.
        """
        parts = [f"run={run_id}", f"kind={kind}"]
        parts.extend(f"{key}={value}" for key, value in extra.items())
        return f"<!-- {self.slug}:{' '.join(parts)} -->"

    def parse_marker(self, body: str) -> dict[str, str] | None:
        """
        Extract this agent's marker fields from a comment body.
        A marker found ONLY inside a quoted line (a Markdown
                    blockquote, leading ">") is ignored: when a human uses
                    "Reply"/"Quote" they carry ADORE's hidden marker into their
                    own comment, and counting that as ours would make resume
                    detection miss their answer. The agent always writes its
                    own marker on an unquoted line, so this never hides a
                    genuine ADORE comment.
        body: Full comment text.
        Returns: Mapping of marker fields (run, kind, ...), or None when the
                    comment carries no unquoted marker (that is, it is human).
        """
        pattern = re.compile(rf"<!--\s*{re.escape(self.slug)}:(.*?)-->", re.DOTALL)
        # Drop blockquote lines before matching, then search the remainder with
        # DOTALL so a legitimately multi-line marker still parses. A marker that
        # survives only inside quoted lines is gone, so a quoted reply is human.
        unquoted = "\n".join(
            line for line in (body or "").splitlines()
            if not line.lstrip().startswith(">")
        )
        match = pattern.search(unquoted)
        if not match:
            return None
        return dict(_TOKEN_RE.findall(match.group(1)))

    def is_own_comment(self, body: str) -> bool:
        """
        True when a comment body carries this agent's marker.
        Comments without the marker are treated as human (resume
                    detection, section 9).
        body: Full comment text.
        Returns: Ownership flag.
        """
        return self.parse_marker(body) is not None

    def status_comment(self, run_id: str, state: str, stage: str, updated: str) -> str:
        """
        Format the single edited status comment (design doc 5d).
        Leads with the visible tag ("[ADORE]") like every other
                    comment the agent posts, so all ADORE comments share one
                    prefix on the ticket.
        run_id: Stable run identifier.
        state: Run state (working | parked | in-review | failed...).
        stage: Current gate (intake | requirement | ...).
        updated: Human-readable UTC timestamp.
        Returns: The full comment body (visible line + hidden marker).
        """
        visible = (
            f"{self.tag} status: {state} - stage {stage} - run {run_id} - updated {updated}"
        )
        marker = self.make_marker(run_id, "status", state=state, stage=stage)
        return f"{visible}\n{marker}"


def identity_from_config(name: str, slug: str) -> AgentIdentity:
    """
    Build the AgentIdentity from the [agent] config values.
    name: Display/brand name.
    slug: Lowercase token (already derived by config loading).
    Returns: A frozen AgentIdentity.
    """
    return AgentIdentity(name=name, slug=slug)
