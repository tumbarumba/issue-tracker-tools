from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List

import dateutil.parser
import numpy as np
import pytz
from dotenv import dotenv_values
from jira import JIRA, Issue
from jira.client import ResultList

from ittools.config import JiraConfig
from ittools.domain.epic import Epic
from ittools.domain.issue_counts import IssueCounts
from ittools.domain.issue_provider import IssueProvider


class JiraServer(IssueProvider, JIRA):
    def __init__(self: JiraServer, verbose: bool, jira_config: JiraConfig):
        super().__init__(
            token_auth=_load_jira_token(), options={"server": jira_config.url}
        )
        self._verbose = verbose
        self._config = jira_config
        self._custom_fields = self._find_custom_fields()

    def load_project_epics(self: JiraServer, project_key: str) -> List[Epic]:
        return self.query_project_epics(project_key)

    @property
    def custom_fields(self) -> Dict[str, str]:
        return self._custom_fields

    def _find_custom_fields(self: JiraServer) -> Dict[str, str]:
        all_fields = self.fields()
        return {
            "Epic Link": self._find_custom_field(all_fields, "Epic Link"),
            "Epic Status": self._find_custom_field(all_fields, "Epic Status"),
            "Rank": self._find_custom_field(all_fields, "Rank"),
        }

    def _find_custom_field(
        self: JiraServer, all_fields: List[Dict[str, Any]], name: str
    ) -> str:
        field = next(filter(lambda f: f["name"] == name, all_fields))
        if self._verbose:
            print(f"Field '{name}' has id '{field['id']}' on this server")
        return field["id"]

    def _create_issue(self: JiraServer, raw_issue: Issue):
        return JiraIssue(raw_issue, self._custom_fields)

    def _create_epic(self: JiraServer, raw_issue: Issue):
        return JiraEpic(raw_issue, self)

    def query_jql_raw(self: JiraServer, jql: str) -> ResultList[Issue]:
        if self._verbose:
            print(f"running jql: {jql}")
        return self.search_issues(jql, expand="changelog", maxResults=1000)

    def query_jql_issues(self: JiraServer, jql: str) -> List[JiraIssue]:
        return list(map(self._create_issue, self.query_jql_raw(jql)))

    def query_jql_epics(self: JiraServer, jql: str) -> List[JiraEpic]:
        return list(map(self._create_epic, self.query_jql_raw(jql)))

    def query_project_epics(self: JiraServer, project_label: str) -> List[JiraEpic]:
        return self.query_jql_epics(
            f"project = DS AND issuetype = Epic and labels = {project_label} ORDER BY rank"
        )

    def query_open_epics(self: JiraServer) -> List[JiraEpic]:
        return self.query_jql_epics(
            "project = DS and issueType = Epic and 'Epic Status' != Done order by rank"
        )

    def query_fix_version(self: JiraServer, fix_version: str) -> List[JiraIssue]:
        return self.query_jql_issues(f"project = DS AND fixVersion = {fix_version}")

    def query_issue_keys(self: JiraServer, issue_keys: List[str]) -> List[JiraIssue]:
        return self.query_jql_issues(f"key in ({', '.join(issue_keys)})")

    def jira_issue(self: JiraServer, issue_key: str) -> JiraIssue:
        issue = self.issue(issue_key, expand="changelog")
        return JiraIssue(issue, self._custom_fields)

    def jira_epic(self: JiraServer, epic_key: str) -> JiraEpic:
        issue = self.issue(epic_key, expand="changelog")
        return JiraEpic(issue, self)

    def query_resolved_issues(
        self: JiraServer, from_date: str, to_date: str
    ) -> List[JiraIssue]:
        jql = (
            f"project = DS and 'Epic Link' is not null and \
                status in ('Done', 'Awaiting Demo') and \
                resolved >= '{from_date}' and resolved < '{to_date}' \
                order by resolved",
        )
        return self.query_jql_issues(jql)

    def query_issues_in_epic(self: JiraServer, epic_key: str) -> List[JiraIssue]:
        return self.query_jql_issues(f"'Epic Link' = {epic_key} order by Status")

    def query_working_issues(self: JiraServer) -> List[JiraIssue]:
        jql = "project = DS and issuetype in ('Story', 'Task', 'Bug') and \
               status in ('In Progress', 'In Review', 'Awaiting Merge') \
               ORDER BY created ASC"
        return self.query_jql_issues(jql)


class JiraIssue:
    def __init__(self: JiraIssue, raw_issue: Issue, custom_fields: Dict[str, str]):
        self.raw_issue = raw_issue
        self.custom_fields = custom_fields
        self._duration = None
        self._calendar_duration = None

    def start_time(self) -> datetime:
        return self.in_progress_time() or self.created_time()

    def created_time(self) -> datetime:
        return dateutil.parser.isoparse(self.raw_issue.fields.created)

    def in_progress_time(self) -> datetime | None:
        for history in self.raw_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    if item.toString == "In Progress":
                        return dateutil.parser.isoparse(history.created)
        return None

    def completed_time(self) -> datetime | None:
        return self.done_time() or self.resolution_time()

    def resolution_time(self) -> datetime | None:
        if self.raw_issue.fields.resolutiondate:
            return dateutil.parser.isoparse(self.raw_issue.fields.resolutiondate)
        return None

    def done_time(self) -> datetime | None:
        result = None
        for history in self.raw_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    if item.toString in ["Awaiting Demo", "Done"]:
                        return dateutil.parser.isoparse(history.created)
        return result

    def fix_versions(self) -> List[str]:
        versions = []
        if "fixVersions" in self.raw_issue.raw["fields"]:
            versions = self.raw_issue.raw["fields"]["fixVersions"]
        return list(map(lambda version: version["name"], versions))

    def add_fix_version(self, new_fix_version) -> None:
        self.raw_issue.add_field_value("fixVersions", {"name": new_fix_version})

    @property
    def key(self: JiraIssue) -> str:
        return self.raw_issue.key

    @property
    def summary(self: JiraIssue) -> str:
        return self.raw_issue.fields.summary

    @property
    def status(self: JiraIssue) -> str:
        return self.raw_issue.fields.status.name

    @property
    def issue_type(self: JiraIssue) -> str:
        return self.raw_issue.fields.issuetype.name

    @property
    def duration(self: JiraIssue) -> float | None:
        if not self._duration:
            self._init_durations()
        return self._duration

    @property
    def calendar_duration(self: JiraIssue) -> float | None:
        if not self._calendar_duration:
            self._init_durations()
        return self._calendar_duration

    def _init_durations(self: JiraIssue) -> None:
        duration_end = self.completed_time() or datetime.now()
        self._duration = _business_days(self.start_time(), duration_end)
        self._calendar_duration = _calendar_days(self.start_time(), duration_end)

    @property
    def epic_key(self) -> str:
        return self.raw_issue.raw["fields"][self.custom_fields["Epic Link"]]

    @property
    def epic_status(self) -> str:
        return self.raw_issue.raw["fields"][self.custom_fields["Epic Status"]]["value"]

    @property
    def epic_summary(self) -> str:
        return self.raw_issue.raw["fields"][self.custom_fields["Epic Status"]][
            "summary"
        ]

    @property
    def rank(self) -> str:
        return self.raw_issue.raw["fields"][self.custom_fields["Rank"]]

    @property
    def url(self) -> str:
        return self.raw_issue.permalink()


class JiraEpic(JiraIssue, Epic):
    def __init__(self: JiraEpic, jira_issue: Issue, jira: JiraServer):
        super().__init__(jira_issue, jira.custom_fields)
        self._jira = jira
        self._issue_counts = None

    @property
    def issue_counts(self: JiraEpic) -> IssueCounts:
        if not self._issue_counts:
            self._issue_counts = _load_issue_counts(self, self._jira)

        return self._issue_counts


IN_PROGRESS_STATES = ["In Progress", "In Review", "Awaiting Merge", "Under Test"]
DONE_STATES = ["Awaiting Demo", "Done"]
EXCLUDE_STATES = ["Closed", "Duplicate"]


def _load_issue_counts(epic: JiraEpic, jira: JiraServer) -> IssueCounts:
    estimated_count = _load_epic_estimated_issues(epic, jira)
    all_epic_issues = jira.query_issues_in_epic(epic.key)
    if len(all_epic_issues) == 0:
        return IssueCounts(estimated_count, 0, 0)

    countable_issues = list(
        filter(lambda issue: issue.status not in EXCLUDE_STATES, all_epic_issues)
    )

    actual_total_count = len(countable_issues)
    reported_total_count = max(estimated_count, actual_total_count)

    done_count = len(_filter_by_state(countable_issues, DONE_STATES))
    in_progress_count = len(_filter_by_state(countable_issues, IN_PROGRESS_STATES))
    pending_count = reported_total_count - in_progress_count - done_count
    if epic.epic_status == "Done":
        pending_count = 0
    return IssueCounts(pending_count, in_progress_count, done_count)


def _load_epic_estimated_issues(epic: JiraEpic, jira: JiraServer) -> int:
    estimated_issues = 10
    issue_estimate_pattern = re.compile(r"^Expected size: (\d+)")
    for comment in jira.comments(epic.key):
        match = issue_estimate_pattern.match(comment.body)
        if match:
            estimated_issues = int(match.group(1))

    return estimated_issues


def _filter_by_state(
    issues: List[JiraIssue], states_to_check: List[str]
) -> List[JiraIssue]:
    return list(filter(lambda issue: issue.status in states_to_check, issues))


BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 17


def _business_days(start_time: datetime, end_time: datetime) -> float | None:
    if not (start_time and end_time):
        return None
    bus_days = np.busday_count(start_time.date(), end_time.date())
    bus_hours = _hours_in_working_day(start_time, end_time)
    return bus_days + (bus_hours / 8)


def _hours_in_working_day(start_time: datetime, end_time: datetime) -> float:
    bus_hours = _end_hours(end_time) - _start_hours(start_time)
    if bus_hours < -8:
        bus_hours = (bus_hours + 24) * -1
    if bus_hours > 8:
        bus_hours = 8
    return bus_hours


def _start_hours(start_time) -> float:
    start_hours = start_time.hour + start_time.minute / 60
    return min(start_hours, BUSINESS_HOURS_END)


def _end_hours(end_time) -> float:
    end_hours = end_time.hour + end_time.minute / 60
    return max(end_hours, BUSINESS_HOURS_START)


def _calendar_days(start_time, end_time) -> float | None:
    if not (start_time and end_time):
        return None
    return (
        (
            end_time.astimezone(pytz.UTC) - start_time.astimezone(pytz.UTC)
        ).total_seconds()
        / 60
        / 60
        / 24
    )


def _load_jira_token() -> str:
    env_values = {
        **dotenv_values(".env"),  # Load env file from current directory
        **dotenv_values(
            os.path.expanduser("~/.env")
        ),  # Override with env file from home directory
        **os.environ,  # Override with environment variables
    }
    return env_values.get("jiraToken")