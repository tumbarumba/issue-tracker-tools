from __future__ import annotations
from typing import Dict, List, Tuple
import sys
import re
from .jira_builder import JiraQueries
from .jira_issue import JiraIssue
from jira import JIRAError, Issue


class EpicReport:
    def __init__(self: EpicReport, opts: Dict[object], query: JiraQueries):
        self.verbose: bool = opts.verbose
        statuses: Dict[str, str] = opts.jira_config.statuses
        self.status_order: Dict[str, int] = {status["name"]: index for index, status in enumerate(statuses)}
        self.status_display: Dict[str, str] = {status["name"]: status["display"] for index, status in enumerate(statuses)}
        self.project_label: str = opts.project_config.project_label
        self.query: JiraQueries = query

    def run(self: EpicReport, subject: str) -> None:
        epics = self.find_epics(subject)
        self.print_epics_and_stories(epics)

    def find_epics(self: EpicReport, subject: str) -> List[Issue]:
        try:
            if re.match("[A-Z]{2}-[0-9]{4}", subject):
                # if a specific epic is provided
                return list(self.query.get_single_issue(subject))
            elif subject:
                # if project specified
                return self.query.get_project_epics(self.project_label)
            else:
                return self.query.get_all_open_epics()
        except JIRAError:
            sys.exit("Epic does not exist or is not formatted correctly, eg. DS-1000.")

    def print_epics_and_stories(self: EpicReport, epics: List[Issue]) -> None:
        for epic in epics:
            print("{}: {}".format(epic.key, epic.fields.summary))
            stories: List[Issue] = self.query.get_epic_stories(epic.key)
            for story in sorted(stories, key=lambda s: self.sort_by_status_then_key(s)):
                issue = JiraIssue(story)
                print("\t[{}] {}: {}".format(self.status_display[issue.status], issue.key, issue.summary))
                if issue.duration:
                    print(f"\t\tworking duration: {issue.duration:.2f} days")

    def sort_by_status_then_key(self, story) -> Tuple[int, str]:
        return (self.status_order[story.fields.status.name], story.key)
