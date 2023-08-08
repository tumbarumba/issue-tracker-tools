from __future__ import annotations
from typing import Any, List


class Issue:
    def __init__(self: Issue, key: str, summary: str):
        self.key = key
        self.summary = summary

    def __eq__(self: Issue, other: Any) -> bool:
        return self.key == other.key

    def __repr__(self: Issue) -> str:
        return f"Issue({self.key})"


class Epic(Issue):
    def __init__(self: Epic, key: str, summary: str, issues: List[Issue]):
        super().__init__(key, summary)
        self.issues = issues
