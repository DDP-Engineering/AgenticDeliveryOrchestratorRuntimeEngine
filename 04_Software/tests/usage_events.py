"""Usage journal records in the shape the current orchestrator writes."""

from __future__ import annotations

from typing import Any


def versioned_usage(run_id: str, attempt: int, **fields: Any) -> dict[str, Any]:
    """
    Build one usage record with its launch identity and every field.
    A nonzero cost counts as reported unless the caller says
                otherwise; a zero cost leaves pricing to the price table.
    run_id: Run owning the record.
    attempt: Launch attempt; the event ID is `<run_id>:<attempt>`.
    fields: Values that replace the defaults (tokens, cost, ts, ...).
    Returns: Keyword arguments for `StateStore.journal(run_id, "usage", ...)`.
    """
    event: dict[str, Any] = {
        "event_id": f"{run_id}:{attempt}", "attempt": attempt, "context": "build",
        "executor": "codex", "model": "example", "review_round": 0,
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0, "cost_reported": False,
    }
    if fields.get("cost_usd") and "cost_reported" not in fields:
        event["cost_reported"] = True
    event.update(fields)
    return event
