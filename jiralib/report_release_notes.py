from .jira_builder import JiraQueries
from .jira_issue import JiraIssue
from .report_issue_summary import IssueSummaryReport


class ReleaseNotesReport:
    def __init__(self, opts, jira, no_tasks):
        self.opts = opts
        self.jira = jira
        self.no_tasks = no_tasks
        self.query = JiraQueries(jira)

    def run(self, issue_keys):
        report_issues = list(map(JiraIssue, self.query.get_issues(issue_keys)))
        if self.no_tasks:
            report_issues = list(filter(lambda issue: issue.jira_issue.fields.issuetype.name != "Task", report_issues))
        IssueSummaryReport(self.opts, self.jira, False).run(report_issues)
