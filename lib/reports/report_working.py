from __future__ import annotations
from typing import Dict, List
from itertools import groupby

from lib.jira.jira_ext import JiraServer, JiraEpic, JiraIssue
from lib.config import ReportOptions


class WorkingReport:
    def __init__(self: WorkingReport, opts: ReportOptions, jira: JiraServer):
        self.verbose = opts.verbose
        self.jira = jira
        self.type_display = {
            issuetype["name"]: issuetype["display"] for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }

    def run(self: WorkingReport, group: bool) -> None:
        report_issues = self.jira.query_working_issues()
        print(f"Working issue count: {len(report_issues)}\n")

        if group:
            self.report_issues_grouped_by_epic(report_issues)
        else:
            self.report_issues(report_issues)

    def report_issues(self: WorkingReport, issues: List[JiraIssue]) -> None:
        for issue in sorted(issues, key=lambda i: i.duration):
            self.print_issue(issue)

    def report_issues_grouped_by_epic(self: WorkingReport, issues: List[JiraIssue]) -> None:
        epics = self.epics_for(issues)
        sorted_issues = sorted(issues, key=lambda i: self.rank_for(i.epic_key, epics))
        for epic_key, epic_issues in groupby(sorted_issues, lambda issue: issue.epic_key or ""):
            if epic_key:
                epic = epics[epic_key]
                print(f"{epic.key}: {epic.summary}")
            else:
                print("No Epic:")
            for issue in epic_issues:
                self.print_issue(issue)
            print()

    def epics_for(self: WorkingReport, issues: List[JiraIssue]) -> Dict[str, JiraEpic]:
        epics: Dict[str, JiraEpic] = {}
        for issue in issues:
            if issue.epic_key and issue.epic_key not in epics:
                epic = self.jira.jira_epic(issue.epic_key)
                epics[epic.key] = epic

        return epics

    def rank_for(self: WorkingReport, epic_key: str, epics: Dict[str, JiraEpic]) -> str:
        if epic_key in epics:
            return epics[epic_key].rank
        else:
            return "Ω"  # Omega should sort last alphabetically

    def print_issue(self: WorkingReport, issue: JiraIssue):
        type_icon = self.type_display[issue.issue_type]
        assignee = issue.raw_issue.fields.assignee
        print(f"{issue.duration:5.2f} {type_icon} {issue.key}: {issue.summary} ({assignee})")
