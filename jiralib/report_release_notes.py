from __future__ import annotations
from typing import Dict, List
from .jira_builder import JiraQueries
from .jira_issue import JiraIssue
from .report_issue_summary import IssueSummaryReport
from jira import JIRA


class ReleaseNotesReport:
    def __init__(self: ReleaseNotesReport, opts: Dict[object], jira: JIRA, no_tasks: bool):
        self.opts = opts
        self.jira = jira
        self.no_tasks = no_tasks
        self.query = JiraQueries(jira)

    def run(self: ReleaseNotesReport, issue_keys: List[str]) -> None:
        report_issues: List[JiraIssue] = list(map(JiraIssue, self.query.get_issues(issue_keys)))
        if self.no_tasks:
            report_issues = list(filter(lambda issue: issue.jira_issue.fields.issuetype.name != "Task", report_issues))
        IssueSummaryReport(self.opts, self.jira, False).run(report_issues)
