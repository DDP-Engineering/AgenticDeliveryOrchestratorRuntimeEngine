"""Shared automatic polling cadence for CLI and web."""

from __future__ import annotations

import random

from adore.config import PollingConfig


class PollCadence:
    """Retain bounded error backoff between automatic polling rounds."""

    def __init__(self) -> None:
        self.multiplier = 1

    def next_delay(self, config: PollingConfig, *, failed: bool | None) -> float:
        """
        Calculate the wait after a completed or quiet round.
        config: Validated positive interval/nonnegative jitter settings.
        failed: False on success, True on error, None on quiet skip.
        Returns: Interval times multiplier plus uniform nonnegative jitter.
        Raises ValueError: If cadence values have invalid types or bounds.
        Note: Disabling backoff resets the multiplier immediately.
        """
        self.validate(config)
        if failed is not None and type(failed) is not bool:
            raise ValueError("invalid polling outcome")
        if not config.poll_backoff or failed is False:
            self.multiplier = 1
        elif failed is True:
            self.multiplier = min(self.multiplier * 2, 8)
        return (config.poll_interval_seconds * self.multiplier
                + random.uniform(0, config.poll_jitter_seconds))

    @staticmethod
    def validate(config: PollingConfig) -> None:
        """
        Validate cadence before any scheduled external invocation.
        config: Parsed polling settings.
        Raises ValueError: If types or bounds are invalid.
        """
        if (type(config.poll_interval_seconds) is not int or config.poll_interval_seconds <= 0
                or type(config.poll_jitter_seconds) is not int or config.poll_jitter_seconds < 0
                or type(config.poll_backoff) is not bool):
            raise ValueError("invalid polling cadence")
