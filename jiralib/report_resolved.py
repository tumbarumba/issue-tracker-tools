import csv
import sys
import datetime
from .jira_builder import JiraQueries
from .jira_issue import JiraIssue
from .report_issue_summary import IssueSummaryReport


this = sys.modules[__name__]
this.date_source = datetime.date


class ResolvedReport:
    def __init__(self, opts, jira):
        self.opts = opts
        self.jira = jira
        self.query = JiraQueries(jira)

    def run(self, days, user_from_date, user_to_date, csv_file):
        from_date = user_from_date or jira_from_date_days_ago(days)
        to_date = user_to_date or jira_to_date()
        print(f"Resolved issues after {from_date} and before {to_date}\n")
        report_issues = list(map(JiraIssue, self.query.get_resolved_issues(from_date, to_date)))

        update_issue_store(report_issues, csv_file)

        IssueSummaryReport(self.opts, self.jira, False).run(report_issues)


def update_issue_store(all_issues, csv_file):
    new_issues = set()
    old_issues = load_old_issues(csv_file)

    for issue in all_issues:
        if issue.key not in old_issues:
            new_issues.add(issue)

    if new_issues:
        save_new_issues(csv_file, new_issues)


def load_old_issues(csv_file):
    issue_keys = set()
    with open(csv_file, 'r', encoding="UTF8") as f:
        csv_reader = csv.DictReader(f)
        for line in csv_reader:
            issue_keys.add(line["Key"])
    return issue_keys


def save_new_issues(csv_file, new_issues):
    with open(csv_file, 'a', encoding="UTF8") as f:
        field_names = ["Key", "Epic", "Status", "Summary", "Started", "Done", "Duration"]
        csv_writer = csv.DictWriter(f, fieldnames=field_names)
        for issue in new_issues:
            rowdata = {
                "Key":      issue.key,
                "Epic":     issue.epic_key(),
                "Status":   issue.status,
                "Summary":  issue.summary,
                "Started":  issue.start_time(),
                "Done":     issue.completed_time(),
                "Duration": issue.duration
            }
            csv_writer.writerow(rowdata)


def jira_from_date_days_ago(days_ago):
    today = this.date_source.today()
    from_date = today - datetime.timedelta(days=days_ago)
    return str(from_date)


def jira_to_date():
    today = this.date_source.today()
    to_date = today + datetime.timedelta(days=1)
    return str(to_date)
