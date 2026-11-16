"""Current execution evidence for isolated persisted-state test fixtures."""

from adore.config import Config
from adore.preparation import resolve_plan


def execution_record() -> dict:
    """
    Return independent current-format container execution evidence.
    Returns: Complete record without preparation or allocated resources.
    """
    return {
        "plan": resolve_plan(Config()), "resource": {}, "status": "not-required",
        "attempts": 0, "steps": [], "history": [], "reprepare": False,
    }
