from __future__ import annotations

import abc
from datetime import datetime
from typing import Any, List


class IssueState:
    """The state of an issue"""

    def __init__(self: IssueState, state: str, start_time: datetime, end_time: datetime):
        self.state = state
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self: IssueState) -> str:
        return f"{self.__class__.__name__}({self.state})"


class Issue(metaclass=abc.ABCMeta):
    """An Issue represents a unit of work"""

    def __init__(self: Issue, key: str, summary: str):
        self.key = key
        self.summary = summary

    def __eq__(self: Issue, other: Any) -> bool:
        return self.key == other.key

    def __repr__(self: Issue) -> str:
        return f"{self.__class__.__name__}({self.key})"

    @property
    @abc.abstractmethod
    def states(self: Issue) -> List[IssueState]:
        pass
