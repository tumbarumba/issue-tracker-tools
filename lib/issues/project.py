from __future__ import annotations

from functools import reduce
from typing import List, Type, TypeVar

from .issue import Epic
from .issue_counts import IssueCounts
from .issue_provider import IssueProvider

T = TypeVar("T", bound="Parent")  # noqa


class Project:
    def __init__(self: Project, project_key: str, epics: List[Epic]):
        self.key = project_key
        self.epics = epics
        self._issue_counts = None

    @classmethod
    def load(cls: Type[T], issue_provider: IssueProvider, project_key: str) -> T:
        epics = issue_provider.load_project_epics(project_key)
        return cls(project_key, epics)

    @property
    def durations(self: Project) -> List[float]:
        durations = []
        # durations.extend(list(map(lambda issue: issue.duration, epic.issues)))
        return durations

    @property
    def issue_counts(self: Project) -> IssueCounts:
        if not self._issue_counts:
            self._issue_counts = reduce(
                lambda accumulation, epic: accumulation + epic.issue_counts,
                self.epics,
                IssueCounts.zero(),
            )
        return self._issue_counts
