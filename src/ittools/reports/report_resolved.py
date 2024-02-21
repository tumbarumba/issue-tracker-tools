from __future__ import annotations
from typing import List
import sys
import datetime

from ittools.jira.jira_ext import JiraServer, JiraIssue
from ittools.config import ReportOptions
from .report_issue_summary import IssueSummaryReport


this = sys.modules[__name__]
this.date_source = datetime.date


class ResolvedReport:
    def __init__(self, opts: ReportOptions, jira: JiraServer):
        self.opts = opts
        self.jira = jira

    def run(
        self,
        days: int,
        user_from_date: str,
        user_to_date: str,
        epic_label: str,
        team: str,
        team_members: List[str],
    ) -> None:
        from_date = user_from_date or jira_from_date_days_ago(days)
        to_date = user_to_date or jira_to_date()
        print("Resolved Issues Report")
        print(f"  date range: {from_date} (inclusive) to {to_date} (exclusive)")
        if epic_label:
            print(f"  filter: including only issues in epics labelled with '{epic_label}'")
        if team:
            print(f"  team: including only issues in completed by members of team '{team}'")
            names = sorted([name.partition(" ")[0] for name in team_members])
            print(f"        ({', '.join(names)})")
        print("")
        resolved_issues = self.jira.query_resolved_issues(from_date, to_date)
        labelled_issues = self.filter_labelled_issues(resolved_issues, epic_label)
        report_issues = self.filter_team_issues(labelled_issues, team_members)

        IssueSummaryReport(self.opts, self.jira, True, False).run(report_issues)

    def filter_labelled_issues(self, all_issues: List[JiraIssue], epic_label: str) -> List[JiraIssue]:
        if not epic_label:
            return all_issues

        matching_epic_keys = self.find_epics_with_label(all_issues, epic_label)
        filtered_issues = [issue for issue in all_issues if issue.epic_key in matching_epic_keys]
        return filtered_issues

    def filter_team_issues(self, all_issues: List[JiraIssue], team_members: List[str]) -> List[JiraIssue]:
        if not team_members:
            return all_issues

        team_issues = [issue for issue in all_issues if issue.assignee in team_members]
        return team_issues

    def find_epics_with_label(self, resolved_issues: List[JiraIssue], epic_label: str):
        all_epic_keys = {issue.epic_key for issue in resolved_issues}
        epics = [self.jira.jira_epic(key) for key in all_epic_keys]
        matching_epic_keys = [epic.key for epic in epics if epic_label in epic.labels]
        return matching_epic_keys


def jira_from_date_days_ago(days_ago: int) -> str:
    today = this.date_source.today()
    from_date = today - datetime.timedelta(days=days_ago)
    return str(from_date)


def jira_to_date() -> str:
    today = this.date_source.today()
    to_date = today + datetime.timedelta(days=1)
    return str(to_date)
