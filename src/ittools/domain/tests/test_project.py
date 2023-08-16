from __future__ import annotations

from typing import List

from ittools.domain.epic import Epic
from ittools.domain.issue import Issue
from ittools.domain.issue_counts import IssueCounts
from ittools.domain.issue_provider import IssueProvider
from ittools.domain.project import Project


class StubIssueProvider(IssueProvider):
    def __init__(self: StubIssueProvider, epics: List[Epic]):
        self.epics = epics

    def load_project_epics(self: StubIssueProvider, project_key: str) -> List[Epic]:
        return self.epics


class StubEpic(Epic):
    def __init__(self: StubEpic, key: str, summary: str, issues: List[Issue]):
        super().__init__(key, summary)
        self.issues = issues

    @property
    def issue_counts(self: Epic) -> IssueCounts:
        return IssueCounts.zero()


def test_project_load():
    epics = [StubEpic("ID-1", "Epic 1", []), StubEpic("ID-2", "Epic 2", [])]
    provider = StubIssueProvider(epics)

    project = Project.load(provider, "test_project")

    assert project.key == "test_project"
    assert project.epics == epics
