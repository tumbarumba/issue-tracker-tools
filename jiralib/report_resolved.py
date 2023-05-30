from __future__ import annotations
from typing import Dict, List, Set
import csv
import sys
import datetime

from .jira_ext import JiraServer, JiraIssue
from .report_issue_summary import IssueSummaryReport


this = sys.modules[__name__]
this.date_source = datetime.date


class ResolvedReport:
    def __init__(self: ResolvedReport, opts: Dict[object], jira: JiraServer):
        self.opts = opts
        self.jira = jira

    def run(self: ResolvedReport, days: int, user_from_date: str, user_to_date: str, csv_file: str) -> None:
        from_date = user_from_date or jira_from_date_days_ago(days)
        to_date = user_to_date or jira_to_date()
        print(f"Resolved issues after {from_date} and before {to_date}\n")
        report_issues = self.jira.query_resolved_issues(from_date, to_date)

        update_issue_store(report_issues, csv_file)

        IssueSummaryReport(self.opts, self.jira, True).run(report_issues)


def update_issue_store(all_issues: List[JiraIssue], csv_file: str) -> None:
    new_issues: Set[JiraIssue] = set()
    old_issue_keys: Set[str] = load_old_issues(csv_file)

    for issue in all_issues:
        if issue.key not in old_issue_keys:
            new_issues.add(issue)

    if new_issues:
        save_new_issues(csv_file, new_issues)


def load_old_issues(csv_file: str) -> Set[str]:
    issue_keys = set()
    with open(csv_file, 'r', encoding="UTF8") as f:
        csv_reader = csv.DictReader(f)
        for line in csv_reader:
            issue_keys.add(line["Key"])
    return issue_keys


def save_new_issues(csv_file: str, new_issues: List[JiraIssue]) -> None:
    with open(csv_file, 'a', encoding="UTF8") as f:
        field_names = ["Key", "Epic", "Status", "Summary", "Started", "Done", "Duration"]
        csv_writer = csv.DictWriter(f, fieldnames=field_names)
        for issue in new_issues:
            rowdata = {
                "Key":      issue.key,
                "Epic":     issue.epic_key,
                "Status":   issue.status,
                "Summary":  issue.summary,
                "Started":  issue.start_time(),
                "Done":     issue.completed_time(),
                "Duration": issue.duration
            }
            csv_writer.writerow(rowdata)


def jira_from_date_days_ago(days_ago: int) -> str:
    today = this.date_source.today()
    from_date = today - datetime.timedelta(days=days_ago)
    return str(from_date)


def jira_to_date() -> str:
    today = this.date_source.today()
    to_date = today + datetime.timedelta(days=1)
    return str(to_date)
