from __future__ import annotations

import re
from datetime import datetime
from itertools import groupby
from typing import Dict, List

from ittools.config import ReportOptions
from ittools.jira.jira_ext import JiraServer, JiraEpic, JiraIssue


class InProgressReport:
    def __init__(self, opts: ReportOptions, jira: JiraServer):
        self.verbose = opts.verbose
        self.jira = jira
        self.type_display = {
            issuetype["name"]: issuetype["display"]
            for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }
        self.status_display = {
            status["name"]: status["display"] for index, status in enumerate(opts.jira_config.statuses)
        }

    def run(self, group_by_epic: bool, group_by_team: bool) -> None:
        print("In progress report")
        print(f"  time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_issues = self.jira.query_working_issues()
        print(f"  issue count: {len(report_issues)}\n")

        if group_by_epic:
            self.report_issues_grouped_by_epic(report_issues)
        elif group_by_team:
            self.report_issues_grouped_by_team(report_issues)
        else:
            self.report_issues(report_issues)

    def report_issues(self, issues: List[JiraIssue]) -> None:
        for issue in sorted(issues, key=lambda i: i.duration):
            self.print_issue(issue)

    def report_issues_grouped_by_epic(
        self, issues: List[JiraIssue]
    ) -> None:
        epics = self.epics_for(issues)
        sorted_issues = sorted(issues, key=lambda i: self.rank_for(i.epic_key, epics))
        for epic_key, epic_issues in groupby(
            sorted_issues, lambda issue: issue.epic_key or ""
        ):
            if epic_key:
                epic = epics[epic_key]
                print(f"{epic.key}: {epic.summary}")
            else:
                print("No Epic:")
            self.report_issues(epic_issues)
            print()

    def report_issues_grouped_by_team(
        self, issues: List[JiraIssue]
    ) -> None:
        epics = self.epics_for(issues)
        sorted_issues = sorted(issues, key=lambda i: _team_for(i.epic_key, epics))
        for team, team_issues in groupby(
            sorted_issues, lambda issue: _team_for(issue.epic_key, epics) or ""
        ):
            if team:
                print(f"Team: {team}")
            else:
                print("No Team:")
            self.report_issues(team_issues)
            print()

    def epics_for(self, issues: List[JiraIssue]) -> Dict[str, JiraEpic]:
        epics: Dict[str, JiraEpic] = {}
        for issue in issues:
            if issue.epic_key and issue.epic_key not in epics:
                epic = self.jira.jira_epic(issue.epic_key)
                epics[epic.key] = epic

        return epics

    def rank_for(self, epic_key: str, epics: Dict[str, JiraEpic]) -> str:
        if epic_key in epics:
            return epics[epic_key].rank
        else:
            return "Ω"  # Omega should sort last alphabetically

    def print_issue(self, issue: JiraIssue):
        type_icon = self.type_display[issue.issue_type]
        status_icon = self.status_display[issue.status]
        print(f"{issue.duration:5.2f} {type_icon}{status_icon} {issue.key}: {issue.summary} ({issue.assignee})")


def _team_for(epic_key: str, epics: Dict[str, JiraEpic]) -> str:
    if epic_key in epics:
        labels = epics[epic_key].labels
        return _team_from_labels(labels)
    else:
        return "Ω"  # Omega should sort last alphabetically


def _team_from_labels(labels: List[str]):
    team_pattern = re.compile(r"^Team(\w+)(_.*)?$")
    for label in labels:
        match = team_pattern.match(label)
        if match:
            return match.group(1)
    return ""
