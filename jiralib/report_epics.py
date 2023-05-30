from __future__ import annotations
from typing import Dict, List, Tuple
import sys
import re
from .jira_ext import JiraServer, JiraEpic, JiraIssue


class EpicReport:
    def __init__(self: EpicReport, opts: Dict[object], jira: JiraServer):
        self.verbose: bool = opts.verbose
        statuses: Dict[str, str] = opts.jira_config.statuses
        self.status_order: Dict[str, int] = {status["name"]: index for index, status in enumerate(statuses)}
        self.status_display: Dict[str, str] = {status["name"]: status["display"] for index, status in enumerate(statuses)}
        self.project_label: str = opts.project_config.project_label
        self.jira = jira

    def run(self: EpicReport, subject: str) -> None:
        epics = self.find_epics(subject)
        self.print_epics_and_stories(epics)

    def find_epics(self: EpicReport, subject: str) -> List[JiraEpic]:
        try:
            if re.match("[A-Z]{2}-[0-9]{4}", subject):
                # if a specific epic is provided
                return [self.jira.jira_epic(subject)]
            elif subject:
                # if project specified
                return self.jira.query_project_epics(self.project_label)
            else:
                return self.jira.query_open_epics()
        except Exception:
            sys.exit("Epic does not exist or is not formatted correctly, eg. DS-1000.")

    def print_epics_and_stories(self: EpicReport, epics: List[JiraEpic]) -> None:
        for epic in epics:
            print("{}: {}".format(epic.key, epic.summary))
            issues: List[JiraIssue] = self.jira.query_issues_in_epic(epic.key)
            for issue in sorted(issues, key=lambda s: self.sort_by_status_then_key(s)):
                print("\t[{}] {}: {}".format(self.status_display[issue.status], issue.key, issue.summary))
                if issue.duration:
                    print(f"\t\tworking duration: {issue.duration:.2f} days")

    def sort_by_status_then_key(self, issue) -> Tuple[int, str]:
        return self.status_order[issue.status], issue.key
