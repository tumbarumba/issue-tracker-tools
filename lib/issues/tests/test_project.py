from __future__ import annotations
from typing import List

from lib.issues.issue import Epic, Issue
from lib.issues.project import Project
from lib.issues.issue_provider import IssueProvider


class StubIssueProvider(IssueProvider):
    def __init__(self: StubIssueProvider, epics: List[Epic]):
        self.epics = epics

    def load_project_epics(self: StubIssueProvider, project_key: str) -> List[Epic]:
        return self.epics


def test_project_load():
    epics = [stub_epic("ID-1", "Epic 1", []), stub_epic("ID-2", "Epic 2", [])]
    provider = StubIssueProvider(epics)

    project = Project.load(provider, "test_project")

    assert project.key == "test_project"
    assert project.epics == epics


def stub_epic(key: str, summary: str, issues: List[Issue]) -> Epic:
    return Epic(key, summary, issues)
