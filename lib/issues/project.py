from __future__ import annotations
from typing import List, Type, TypeVar

from .issue import Epic
from .issue_provider import IssueProvider


T = TypeVar("T", bound="Parent")  # noqa


class Project:
    def __init__(self: Project, project_key: str, epics: List[Epic]):
        self.project_key = project_key
        self.epics = epics

    @classmethod
    def load(cls: Type[T], issue_provider: IssueProvider, project_key: str) -> T:
        epics = issue_provider.load_project_epics(project_key)
        return cls(project_key, epics)

    @property
    def durations(self: Project) -> List[float]:
        durations = []
        # durations.extend(list(map(lambda issue: issue.duration, epic.issues)))
        return durations
