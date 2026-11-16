"""Immutable repository input shared by isolated Python test fixtures."""

from functools import cache
from pathlib import Path


@cache
def example_config_text() -> str:
    """
    Read the checked-in example once per test worker.
    Returns: Immutable UTF-8 configuration text for independent fixture copies.
    """
    return (Path(__file__).resolve().parents[1] / "config.example.toml").read_text(encoding="utf-8")
