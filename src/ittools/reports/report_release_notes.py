from __future__ import annotations
from typing import List

from ittools.jira.jira_ext import JiraServer
from ittools.config import ReportOptions
from .report_issue_summary import IssueSummaryReport


class ReleaseNotesReport:
    def __init__(
        self,
        opts: ReportOptions,
        jira: JiraServer,
        no_tasks: bool,
        markdown: bool,
    ):
        self.opts = opts
        self.jira = jira
        self.no_tasks = no_tasks
        self.markdown = markdown

    def run(self, issue_keys: List[str]) -> None:
        report_issues = self.jira.query_issue_keys(issue_keys)
        if self.no_tasks:
            report_issues = list(
                filter(lambda issue: issue.issue_type != "Task", report_issues)
            )
        IssueSummaryReport(self.opts, self.jira, False, self.markdown).run(
            report_issues
        )
