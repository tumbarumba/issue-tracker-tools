from typing import List

from lib.issues.issue import Epic
from lib.issues.project import Project
from lib.issues.issue_provider import IssueProvider


class TestIssueProvider(IssueProvider):
    def load_project_epics(self: IssueProvider, project_key: str) -> List[Epic]:
        return []


def test_project():
    test_provider = TestIssueProvider()
    project = Project.load(test_provider, "test_project")
    assert project.project_key == "test_project"
