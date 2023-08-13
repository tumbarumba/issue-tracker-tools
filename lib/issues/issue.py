from __future__ import annotations
from typing import Any
import abc

from .issue_counts import IssueCounts


class Issue:
    def __init__(self: Issue, key: str, summary: str):
        self.key = key
        self.summary = summary

    def __eq__(self: Issue, other: Any) -> bool:
        return self.key == other.key

    def __repr__(self: Issue) -> str:
        return f"{self.__class__.__name__}({self.key})"


class Epic(Issue, metaclass=abc.ABCMeta):
    def __init__(self: Epic, key: str, summary: str):
        super().__init__(key, summary)

    @property
    @abc.abstractmethod
    def issue_counts(self: Epic) -> IssueCounts:
        pass
