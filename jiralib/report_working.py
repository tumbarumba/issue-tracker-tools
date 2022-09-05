from .jira_builder import JiraQueries
from .jira_issue import JiraIssue


class WorkingReport:
    def __init__(self, opts):
        self.verbose = opts.verbose
        self.jira = opts.jira
        self.query = JiraQueries(opts.jira)
        self.type_display = {
            issuetype["name"]: issuetype["display"] for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }

    def run(self):
        report_issues = list(map(JiraIssue, self.query.get_working_issues()))
        if not report_issues:
            print("No working issues")
            return

        for issue in sorted(report_issues, key=lambda issue: issue.duration):
            typeicon = self.type_display[issue.jira_issue.fields.issuetype.name]
            assignee = issue.jira_issue.fields.assignee
            print(f"{issue.duration:5.2f} {typeicon} {issue.key}: {issue.summary} ({assignee})")
