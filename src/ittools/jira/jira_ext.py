from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import dateutil.parser
from dotenv import dotenv_values
from jira import JIRA
from jira import Issue as AtlassianIssue
from jira.client import ResultList

from ittools.config import JiraConfig
from ittools.domain.dateutils import business_days, calendar_days
from ittools.domain.epic import Epic
from ittools.domain.issue import Issue, IssueState
from ittools.domain.issue_counts import IssueCounts
from ittools.domain.issue_provider import IssueProvider


class JiraServer(IssueProvider, JIRA):
    def __init__(self, verbose: bool, jira_config: JiraConfig):
        super().__init__(**_build_jira_args(jira_config))
        self._verbose = verbose
        self._config = jira_config
        self._custom_fields = self._find_custom_fields()
        self._project_query = f"project IN ({','.join(jira_config.project_keys)})"

    def load_project_epics(self, project_key: str) -> List[JiraEpic]:
        return self.query_project_epics(project_key)

    @property
    def custom_fields(self) -> Dict[str, str]:
        return self._custom_fields

    def _find_custom_fields(self) -> Dict[str, str]:
        all_fields = self.fields()
        return {
            "Epic Link": self._find_custom_field(all_fields, "Epic Link"),
            "Epic Status": self._find_custom_field(all_fields, "Epic Status"),
            "Rank": self._find_custom_field(all_fields, "Rank"),
        }

    def _find_custom_field(
        self, all_fields: List[Dict[str, Any]], name: str
    ) -> str:
        field = next(filter(lambda f: f["name"] == name, all_fields))
        if self._verbose:
            print(f"Field '{name}' has id '{field['id']}' on this server")
        return field["id"]

    def _create_issue(self, raw_issue: AtlassianIssue):
        return JiraIssue(raw_issue, self._custom_fields)

    def _create_epic(self, raw_issue: AtlassianIssue):
        return JiraEpic(raw_issue, self)

    def query_jql_raw(self, jql: str) -> ResultList[AtlassianIssue]:
        if self._verbose:
            print(f"running jql: {jql}")
        result = self.search_issues(jql, expand="changelog", maxResults=1000)
        assert isinstance(result, ResultList)
        return result

    def query_jql_issues(self, jql: str) -> List[JiraIssue]:
        return list(map(self._create_issue, self.query_jql_raw(jql)))

    def query_jql_epics(self, jql: str) -> List[JiraEpic]:
        return list(map(self._create_epic, self.query_jql_raw(jql)))

    def query_project_epics(self, project_label: str) -> List[JiraEpic]:
        return self.query_jql_epics(
            f"{self._project_query} AND issuetype = Epic and labels = {project_label} ORDER BY rank"
        )

    def query_open_epics(self) -> List[JiraEpic]:
        return self.query_jql_epics(
            f"{self._project_query} and issueType = Epic and 'Epic Status' != Done order by rank"
        )

    def query_fix_version(self, fix_version: str) -> List[JiraIssue]:
        return self.query_jql_issues(f"{self._project_query} AND fixVersion = {fix_version}")

    def query_issue_keys(self, issue_keys: List[str]) -> List[JiraIssue]:
        return self.query_jql_issues(f"key in ({', '.join(issue_keys)})")

    def jira_issue(self, issue_key: str) -> JiraIssue:
        issue = self.issue(issue_key, expand="changelog")
        return JiraIssue(issue, self._custom_fields)

    def jira_epic(self, epic_key: str) -> JiraEpic:
        issue = self.issue(epic_key, expand="changelog")
        return JiraEpic(issue, self)

    def query_resolved_issues(
        self, from_date: str, to_date: str
    ) -> List[JiraIssue]:
        jql = (f"{self._project_query}"
               f" and 'Epic Link' is not null"
               f" and status in ('Done', 'Awaiting Demo')"
               f" and resolved >= '{from_date}'"
               f" and resolved < '{to_date}'"
               f" order by resolved")

        return self.query_jql_issues(jql)

    def query_issues_in_epic(self, epic_key: str) -> List[JiraIssue]:
        return self.query_jql_issues(f"'Epic Link' = {epic_key} order by Status")

    def query_working_issues(self) -> List[JiraIssue]:
        jql = f"{self._project_query} and issuetype in ('Story', 'Task', 'Bug') and \
               status in ('In Progress', 'In Review', 'Under Test') \
               ORDER BY created ASC"
        return self.query_jql_issues(jql)


class JiraIssue(Issue):
    def __init__(self, raw_issue: AtlassianIssue, custom_fields: Dict[str, str]):
        super().__init__(raw_issue.key, raw_issue.fields.summary)
        self.raw_issue = raw_issue
        self.custom_fields = custom_fields
        self._duration = None
        self._calendar_duration = None
        self._history = None

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
        self.raw_issue.update(update={"fixVersions": [{"add": {"name": new_fix_version}}]})

    @property
    def assignee(self) -> str:
        assignee = "None"
        if "assignee" in self.raw_issue.raw["fields"]:
            assignee_field = self.raw_issue.raw["fields"]["assignee"]
            if isinstance(assignee_field, dict) and "displayName" in assignee_field:
                assignee = assignee_field["displayName"]
        return assignee

    @property
    def status(self) -> str:
        return self.raw_issue.fields.status.name

    @property
    def issue_type(self) -> str:
        return self.raw_issue.fields.issuetype.name

    @property
    def duration(self) -> float | None:
        if not self._duration:
            self._init_durations()
        return self._duration

    @property
    def calendar_duration(self) -> float | None:
        if not self._calendar_duration:
            self._init_durations()
        return self._calendar_duration

    def _init_durations(self) -> None:
        duration_end = self.completed_time() or datetime.now()
        self._duration = business_days(self.start_time(), duration_end)
        self._calendar_duration = calendar_days(self.start_time(), duration_end)

    @property
    def epic_key(self) -> str:
        return self.raw_issue.raw["fields"][self.custom_fields["Epic Link"]]

    @property
    def labels(self) -> List[str]:
        return self.raw_issue.fields.labels

    @property
    def has_release_notes(self) -> bool:
        return "ReleaseNotes" in self.labels

    @property
    def rank(self) -> str:
        return self.raw_issue.raw["fields"][self.custom_fields["Rank"]]

    @property
    def url(self) -> str:
        return self.raw_issue.permalink()

    @property
    def description(self) -> str:
        return self.raw_issue.fields.description

    @property
    def history(self) -> List[IssueState]:
        if not self._history:
            self._init_history()
        return self._history

    def _init_history(self) -> None:
        self._history = []
        self._history.append(IssueState("Selected for Development", self.created_time()))
        for history in self.raw_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    self._history.append(IssueState(item.toString, dateutil.parser.isoparse(history.created)))


class JiraEpic(Epic):
    def __init__(self, raw_issue: AtlassianIssue, jira: JiraServer):
        super().__init__(raw_issue.key, raw_issue.fields.summary)
        self._raw_issue = raw_issue
        self._jira = jira
        self._issue_counts = None

    @property
    def issue_counts(self) -> IssueCounts:
        if not self._issue_counts:
            self._issue_counts = _load_issue_counts(self, self._jira)

        return self._issue_counts

    @property
    def epic_status(self) -> str:
        return self._raw_issue.raw["fields"][self._jira.custom_fields["Epic Status"]]["value"]

    @property
    def epic_summary(self) -> str:
        return self._raw_issue.raw["fields"][self._jira.custom_fields["Epic Status"]][
            "summary"
        ]

    @property
    def labels(self) -> List[str]:
        return self._raw_issue.fields.labels

    @property
    def url(self) -> str:
        return self._raw_issue.permalink()


IN_PROGRESS_STATES = ["In Progress", "In Review", "Under Test"]
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


def _build_jira_args(jira_config: JiraConfig) -> Dict[str, Any]:
    jira_args = {
        "options": {"server": jira_config.url},
        "validate": True,
    }
    env = _load_env()
    if "jiraToken" in env:
        jira_args["token_auth"] = env["jiraToken"]
    elif "jiraUser" in env:
        if "jiraApiToken" not in env:
            raise ValueError("'jiraUser' authentication requires 'jiraApiToken'")
        jira_args["basic_auth"] = (env["jiraUser"], env["jiraApiToken"])
    else:
        raise ValueError("Authentication required (define 'jiraToken' or 'jiraUser' in environment")

    return jira_args


def _load_env() -> Dict[str, Optional[str]]:
    return {
        **dotenv_values(".env"),  # Load env file from current directory
        **dotenv_values(
            os.path.expanduser("~/.env")
        ),  # Override with env file from home directory
        **os.environ,  # Override with environment variables
    }
