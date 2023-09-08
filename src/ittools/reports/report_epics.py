from __future__ import annotations
from typing import Dict, List, Tuple

from ittools.config import ReportOptions
from ittools.jira.jira_ext import JiraServer, JiraEpic, JiraIssue


class EpicReport:
    def __init__(self: EpicReport, opts: ReportOptions, jira: JiraServer):
        self.verbose: bool = opts.verbose
        statuses: Dict[str, Dict[str, str]] = opts.jira_config.statuses
        self.status_order: Dict[str, int] = {
            status["name"]: index for index, status in enumerate(statuses)
        }
        self.status_display: Dict[str, str] = {
            status["name"]: status["display"] for index, status in enumerate(statuses)
        }
        self.jira = jira

    def run(self: EpicReport, epics: List[JiraEpic]) -> None:
        for epic in epics:
            print("{}: {}".format(epic.key, epic.summary))
            issues: List[JiraIssue] = self.jira.query_issues_in_epic(epic.key)
            for issue in sorted(issues, key=lambda s: self.sort_by_status_then_key(s)):
                print(
                    "\t[{}] {}: {}".format(
                        self.status_display[issue.status], issue.key, issue.summary
                    )
                )
                if issue.duration:
                    print(f"\t\tworking duration: {issue.duration:.2f} days")

    def sort_by_status_then_key(self, issue) -> Tuple[int, str]:
        return self.status_order[issue.status], issue.key
