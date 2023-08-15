from typing import List
import datetime
import pytz
import textwrap
from jira import Issue
from jira.resources import Comment
from unittest.mock import Mock

from lib.jira.jira_ext import JiraEpic, JiraServer, JiraIssue
from lib.domain.issue_counts import IssueCounts
from lib.reports.report_progress import store_project_counts


def assert_equal_counts(actual: IssueCounts, expected: IssueCounts):
    assert actual == expected, f"expected {expected}, got {actual}"


def test_epics_with_no_children_expect_10_stories_by_default():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server([], []))
    assert_equal_counts(epic.issue_counts, IssueCounts(10, 0, 0))


def test_epic_with_estimated_children_comment_but_no_children_uses_estimate_comment():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server([], [mock_comment("Expected size: 5")]))
    assert_equal_counts(epic.issue_counts, IssueCounts(5, 0, 0))


def test_epic_with_less_children_than_estimate_will_use_estimate():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server(
        [mock_story("Backlog")],
        [mock_comment("Expected size: 2")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(2, 0, 0))


def test_epic_with_more_children_than_estimate_will_use_child_count():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server(
        [mock_story("Backlog"), mock_story("Backlog"), mock_story("Backlog")],
        [mock_comment("Expected size: 2")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(3, 0, 0))


def test_epic_completed_stories():
    epic = JiraEpic(mock_raw_epic("Done"), mock_jira_server(
        [mock_story("Done"), mock_story("Done")],
        [mock_comment("Expected size: 3")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(0, 0, 2))


def test_epic_in_progress_stories():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server(
        [mock_story("In Progress"), mock_story("In Review"), mock_story("Awaiting Merge"), mock_story("Under Test")],
        [mock_comment("Expected size: 4")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(0, 4, 0))


def test_epic_done_stories():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server(
        [mock_story("Done"), mock_story("Done"), mock_story("Done"), mock_story("Awaiting Demo")],
        [mock_comment("Expected size: 3")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(0, 0, 4))


def test_epic_closed_duplicate_stories_are_ignored():
    epic = JiraEpic(mock_raw_epic(), mock_jira_server(
        [mock_story("Duplicate"), mock_story("Closed")],
        [mock_comment("Expected size: 3")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(3, 0, 0))


def test_epic_in_done_state_will_ignore_estimate():
    epic = JiraEpic(mock_raw_epic("Done"), mock_jira_server(
        [mock_story("Done")],
        [mock_comment("Expected size: 2")]
    ))
    assert_equal_counts(epic.issue_counts, IssueCounts(0, 0, 1))


def test_csv_created_when_missing(tmp_path):
    csv_path = tmp_path / "reports" / "Test Project" / "progress.csv"

    store_project_counts("2022-08-16", "Test Project", IssueCounts(1, 1, 1), str(csv_path))

    assert csv_path.exists()
    assert csv_path.read_text() == textwrap.dedent("""\
        date,project,pending,in_progress,done,total
        2022-08-16,Test Project,1,1,1,3
        """)


def test_csv_appended_when_already_present(tmp_path):
    csv_path = tmp_path / "reports" / "Test Project" / "progress.csv"
    setup_initial_csv(csv_path, textwrap.dedent("""\
        date,project,pending,in_progress,done,total
        2022-08-15,Test Project,1,2,0,3
        """))

    store_project_counts("2022-08-16", "Test Project", IssueCounts(1, 1, 1), str(csv_path))

    assert csv_path.read_text() == textwrap.dedent("""\
        date,project,pending,in_progress,done,total
        2022-08-15,Test Project,1,2,0,3
        2022-08-16,Test Project,1,1,1,3
        """)


def test_csv_fills_in_missing_dates(tmp_path):
    csv_path = tmp_path / "reports" / "Test Project" / "progress.csv"
    setup_initial_csv(csv_path, textwrap.dedent("""\
        date,project,pending,in_progress,done,total
        2022-08-13,Test Project,1,2,0,3
        """))

    store_project_counts("2022-08-16", "Test Project", IssueCounts(1, 1, 1), str(csv_path))

    assert csv_path.read_text() == textwrap.dedent("""\
        date,project,pending,in_progress,done,total
        2022-08-13,Test Project,1,2,0,3
        2022-08-14,Test Project,1,2,0,3
        2022-08-15,Test Project,1,2,0,3
        2022-08-16,Test Project,1,1,1,3
        """)


def setup_initial_csv(csv_path, content):
    csv_path.parent.mkdir(parents=True)
    with csv_path.open("w", encoding="UTF8") as f:
        f.write(content)


def mock_raw_epic(status="To Do") -> Issue:
    epic = Mock()
    epic.key = "dummy-key"
    epic.changelog.histories = []
    epic.epic_status = status
    epic.fields.created = datetime.datetime.now(tz=pytz.UTC).isoformat()
    epic.fields.resolutiondate = None
    epic.raw = {"fields": {"epic_status_field_id": {"value": status}}}
    return epic


def mock_jira_server(issues: List[JiraIssue] = (), comments: List[Comment] = ()) -> JiraServer:
    jira = Mock(spec=JiraServer)
    jira.custom_fields = {
        "Epic Link":    "epic_link_field_id",
        "Epic Status":  "epic_status_field_id",
        "Rank":         "rank_field_id"
    }
    jira.query_issues_in_epic.return_value = list(issues)
    jira.comments.return_value = list(comments)
    return jira


def mock_comment(comment_body: str) -> Comment:
    comment = Mock(spec=Comment)
    comment.body = comment_body
    return comment


def mock_story(status: str) -> JiraIssue:
    story = Mock(spec=JiraIssue)
    story.status = status
    story.created = datetime.datetime.now(tz=pytz.UTC).isoformat()
    return story
