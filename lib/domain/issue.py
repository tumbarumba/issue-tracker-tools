from __future__ import annotations
from typing import Any


class Issue:
    """An Issue represents a unit of work"""

    def __init__(self: Issue, key: str, summary: str):
        self.key = key
        self.summary = summary

    def __eq__(self: Issue, other: Any) -> bool:
        return self.key == other.key

    def __repr__(self: Issue) -> str:
        return f"{self.__class__.__name__}({self.key})"
