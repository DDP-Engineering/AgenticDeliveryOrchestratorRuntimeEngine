"""Apply a job's validated execution settings without changing project defaults."""

from copy import deepcopy
from dataclasses import is_dataclass

from adore.config import Config
from adore.preparation import validate_plan


def job_execution_config(project: Config, plan: dict) -> Config:
    """Restore saved execution authority; live approval, identity and budgets stay current.

    Unknown raw project keys are retained for boundary validation. No stored
    format is upgraded, inferred or rewritten by this projection.
    """
    plan = validate_plan(plan)
    config = deepcopy(project)
    policy = plan["policy"]

    def assign(owner, values):
        for key, value in values.items():
            child = getattr(owner, key)
            if is_dataclass(child):
                assign(child, value)
            else:
                if type(child) is not type(value):
                    raise TypeError("invalid project execution setting type: " + key)
                setattr(owner, key, deepcopy(value))

    def overlay(raw, values):
        for key, value in values.items():
            if isinstance(value, dict):
                if not isinstance(raw.get(key), dict):
                    raw[key] = {}
                overlay(raw[key], value)
            else:
                raw[key] = deepcopy(value)

    sections = {key: policy[key] for key in ("execution", "worktree", "executor")}
    if plan["backend"] == "container":
        sections["container"] = {
            **policy["container"], "image": plan["image"],
            "system_packages": policy["container"].get("system_packages", False),
        }
    else:
        sections["local"] = policy["local"]["settings"]
    sections["delivery"] = {"target_branch": policy["target_branch"]}
    sections["workflow"] = {"aegis_python": policy["aegis_python"]}
    for section, values in sections.items():
        assign(getattr(config, section), values)
    overlay(config.raw, sections)
    return config
