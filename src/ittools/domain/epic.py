from __future__ import annotations

import abc
from typing import List

from .issue import Issue, IssueState
from .issue_counts import IssueCounts


class Epic(Issue, metaclass=abc.ABCMeta):
    """An Epic is an Issue that represents a large unit of work

    An epic can be split up into smaller Issues.
    """

    def __init__(self, key: str, summary: str):
        super().__init__(key, summary)

    @property
    @abc.abstractmethod
    def issue_counts(self) -> IssueCounts:
        pass

    @property
    def history(self) -> List[IssueState]:
        return []
