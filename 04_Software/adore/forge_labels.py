"""Create the project's missing ADORE labels in its repository."""

from __future__ import annotations

from dataclasses import dataclass

from adore.config import Config
from adore.forge.base import Forge, ForgeError

_LIFECYCLE = "1D76DB"
_CONTROL = "5319E7"
_PRIORITY = {"priority_high": "B60205", "priority_medium": "FBCA04", "priority_low": "0E8A16"}
_REVIEW = "C5DEF5"
_TYPE = "D4C5F9"


@dataclass(frozen=True)
class LabelSpec:
    """One label ADORE needs: name, colour (hex without #) and description."""

    name: str
    color: str
    description: str


def project_labels(config: Config) -> list[LabelSpec]:
    """
    The labels the project's settings name, once each (case-insensitive).
    config: Effective project configuration.
    Returns: Label specifications in a stable order.
    """
    labels = config.labels
    lifecycle = labels.lifecycle
    entries = [
        (lifecycle.ready, _LIFECYCLE, "ADORE: ready for an agent to pick up"),
        (lifecycle.working, _LIFECYCLE, "ADORE: an agent is working on it"),
        (lifecycle.clarify, _LIFECYCLE, "ADORE: the agent asked a question"),
        (lifecycle.answered, _LIFECYCLE, "ADORE: a person answered the question"),
        (lifecycle.review, _LIFECYCLE, "ADORE: a merge request is open for review"),
        (lifecycle.failed, _LIFECYCLE, "ADORE: the job failed"),
        (lifecycle.done, _LIFECYCLE, "ADORE: the job is done"),
        (labels.control.hold, _CONTROL, "ADORE: on hold, not picked up"),
        (labels.control.exclude, _CONTROL, "ADORE: never picked up"),
        (labels.selection.priority_high, _PRIORITY["priority_high"], "Priority: high"),
        (labels.selection.priority_medium, _PRIORITY["priority_medium"], "Priority: medium"),
        (labels.selection.priority_low, _PRIORITY["priority_low"], "Priority: low"),
        (labels.selection.type_bug, _TYPE, "Type: bug fix"),
        (config.delivery.approval_label, _REVIEW, "ADORE: a person approved publication"),
        (config.review.revise_label, _REVIEW, "ADORE: revise the merge request"),
        *(
            (name, _TYPE, f"ADORE task type: {kind}")
            for name, kind in sorted(config.workflow.kind_labels.items())
        ),
    ]
    seen: set[str] = set()
    specs: list[LabelSpec] = []
    for name, color, description in entries:
        name = str(name).strip()
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            specs.append(LabelSpec(name, color, description))
    return specs


def failure_reason(exc: ForgeError) -> str:
    """
    The forge's own reason for a refused label, without the command line.
    The error text also carries the whole argv (name, colour,
                description), which would push the cause out of a short reason.
    """
    summary = str(exc).split(" | ", 1)[0].strip()  # the message, without argv or stderr
    cause = " ".join(exc.stderr.split())
    return (f"{summary}: {cause}" if cause else summary)[:200]


def ensure_labels(forge: Forge, specs: list[LabelSpec]) -> dict:
    """
    Create the missing labels; report created, existing and failed ones.
    forge: Credential-scoped forge adapter of the project.
    specs: Labels the project needs.
    Returns: {"created": [...], "existing": [...], "failed": [{"name", "reason"}]}.
    Raises ForgeError: When the existing labels cannot be read (nothing is created).
    """
    from adore.forge.azure_devops import AzureDevOpsForge

    if isinstance(forge, AzureDevOpsForge):
        forge.verify_access()
        return {"created": [], "existing": [], "failed": [],
                "mode": "azure_on_attachment", "verified": [s.name for s in specs]}
    present = {name.casefold() for name in forge.list_labels()}
    report: dict = {"created": [], "existing": [], "failed": []}
    for spec in specs:
        if spec.name.casefold() in present:
            report["existing"].append(spec.name)
            continue
        try:
            forge.create_label(spec.name, spec.color, spec.description)
        except ForgeError as exc:
            report["failed"].append({"name": spec.name, "reason": failure_reason(exc)})
            continue
        present.add(spec.name.casefold())
        report["created"].append(spec.name)
    return report
