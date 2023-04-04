from .jira_builder import JiraQueries
from .jira_issue import JiraIssue
from .report_issue_summary import IssueSummaryReport


class ReleaseNotesReport:
    def __init__(self, opts, jira, is_html):
        self.opts = opts
        self.jira = jira
        self.is_html = is_html
        self.query = JiraQueries(jira)

    def run(self, issue_keys):
        report_issues = list(map(JiraIssue, self.query.get_issues(issue_keys)))
        IssueSummaryReport(self.opts, self.jira, self.is_html).run(report_issues)
