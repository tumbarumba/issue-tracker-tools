from __future__ import annotations
from typing import Dict, List
from .jira_ext import JiraServer
from .report_issue_summary import IssueSummaryReport


class ReleaseNotesReport:
    def __init__(self: ReleaseNotesReport, opts: Dict[object], jira: JiraServer, no_tasks: bool):
        self.opts = opts
        self.jira = jira
        self.no_tasks = no_tasks

    def run(self: ReleaseNotesReport, issue_keys: List[str]) -> None:
        report_issues = self.jira.query_issue_keys(issue_keys)
        if self.no_tasks:
            report_issues = list(filter(lambda issue: issue.issue_type != "Task", report_issues))
        IssueSummaryReport(self.opts, self.jira, False).run(report_issues)
