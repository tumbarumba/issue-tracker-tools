from typing import Any, List
from dateutil.parser import isoparse
from unittest.mock import Mock

from jira import Issue as AtlassianIssue

from ittools.domain.issue import IssueState
from ittools.jira.jira_ext import JiraIssue


def test_status_from_story_history():
    created_time = "2023-10-12T13:40:47.000+1100"
    ready = mock_history_item("2023-10-12T14:28:46.290+1100", "B C", "Selected for Development", "Ready for Development")
    in_progress = mock_history_item("2023-10-12T16:40:03.688+1100", "C D", "Ready for Development", "In Progress")
    in_review = mock_history_item("2023-10-23T09:20:21.589+1100", "D E", "In Progress", "In Review")
    under_test = mock_history_item("2023-10-24T09:09:52.163+1100", "E F", "In Review", "Under Test")
    raw_story = mock_story(created_time, [ready, in_progress, in_review, under_test])

    story = JiraIssue(raw_story, {})

    assert story.history == [
        IssueState("Selected for Development", isoparse(created_time)),
        IssueState("Ready for Development", isoparse(ready.created)),
        IssueState("In Progress", isoparse(in_progress.created)),
        IssueState("In Review", isoparse(in_review.created)),
        IssueState("Under Test", isoparse(under_test.created)),
    ]


def test_time_in_status():
    created_time = "2023-10-12T09:00:00.000+1100"
    ready       = mock_history_item("2023-10-12T10:00:00.000+1100", "B C", "Selected for Development", "Ready for Development")  # noqa
    in_progress = mock_history_item("2023-10-12T11:00:00.000+1100", "C D", "Ready for Development", "In Progress")  # noqa
    in_review   = mock_history_item("2023-10-12T13:00:00.000+1100", "D E", "In Progress", "In Review")  # noqa
    under_test  = mock_history_item("2023-10-12T16:00:00.000+1100", "E F", "In Review", "Under Test")  # noqa
    done        = mock_history_item("2023-10-12T17:00:00.000+1100", "F G", "Under Test", "Done")  # noqa
    raw_story = mock_story(created_time, [ready, in_progress, in_review, under_test, done])

    story = JiraIssue(raw_story, {})

    assert story.time_in_state("Selected for Development") == 1.0 / 8.0     # 9am -> 10am
    assert story.time_in_state("Ready for Development") == 1.0 / 8.0        # 10am -> 11am
    assert story.time_in_state("In Progress") == 2.0 / 8.0                  # 11am -> 1pm
    assert story.time_in_state("In Review") == 3.0 / 8.0                    # 1pm -> 4pm
    assert story.time_in_state("Under Test") == 1.0 / 8.0                   # 4pm -> 5pm
    assert story.time_in_state("Done") == 0.0


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


def mock_story(created_time, history: List[Any]) -> AtlassianIssue:
    story = Mock()
    story.fields.created = created_time
    story.status = history[-1].toString
    story.changelog.histories = history
    return story
