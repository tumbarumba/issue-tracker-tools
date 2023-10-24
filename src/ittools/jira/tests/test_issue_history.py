from typing import Any, List
from dateutil.parser import isoparse
from unittest.mock import Mock

from jira import Issue as AtlassianIssue

from ittools.domain.issue import IssueState
from ittools.jira.jira_ext import JiraIssue


def test_status_from_story_history():
    created = mock_history_item("2023-10-12T13:40:47.000+1100", "A B", None, "Selected for Development")
    ready = mock_history_item("2023-10-12T14:28:46.290+1100", "B C", "Selected for Development", "Ready for Development")
    in_progress = mock_history_item("2023-10-12T16:40:03.688+1100", "C D", "Ready for Development", "In Progress")
    in_review = mock_history_item("2023-10-23T09:20:21.589+1100", "D E", "In Progress", "In Review")
    under_test = mock_history_item("2023-10-24T09:09:52.163+1100", "E F", "In Review", "Under Test")
    raw_story = mock_story([created, ready, in_progress, in_review, under_test])

    story = JiraIssue(raw_story, {})

    assert story.history == [
        IssueState("Selected for Development", isoparse(created.created)),
        IssueState("Ready for Development", isoparse(ready.created)),
        IssueState("In Progress", isoparse(in_progress.created)),
        IssueState("In Review", isoparse(in_review.created)),
        IssueState("Under Test", isoparse(under_test.created)),
    ]


def mock_history_item(time: str, author: str, old_state: str | None, new_state: str) -> object:
    status_item = Mock()
    status_item.field = "status"
    status_item.fromString = old_state
    status_item.toString = new_state

    history = Mock()
    history.created = time
    history.author.displayName = author
    history.items = [status_item]
    return history


def mock_story(history: List[Any]) -> AtlassianIssue:
    story = Mock()
    story.created = history[0].created
    story.status = history[-1].toString
    story.changelog.histories = history
    return story
